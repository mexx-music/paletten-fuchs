import math
import streamlit as st

st.set_page_config(page_title="🦊 PAL Fuchs 8 – Varianten (Real-Logik)", layout="wide")
st.title("🦊 PAL Fuchs – Draufsicht mit Icons & Varianten")

# ---------- Trailer ----------
TRAILER_L, TRAILER_W = 1360, 245  # cm

# ---------- Sidebar: Raster & Zoom ----------
st.sidebar.markdown("### ⚙️ Anzeige")
cell_cm = st.sidebar.slider("Raster (cm/Zelle)", 20, 50, 40, 5)  # 40 cm empfohlen (120=3, 80=2)
auto_zoom = st.sidebar.checkbox("Auto‑Zoom auf konstante Breite", True)
manual_px = st.sidebar.slider("Zell‑Pixel (nur wenn Auto‑Zoom aus)", 4, 20, 8, 1)

# Grid-Auflösung (Zellen)
X = max(1, TRAILER_L // cell_cm)
Y = max(1, TRAILER_W // cell_cm)

# Auto‑Zoom: halte Trailerbreite stabil
cell_px = max(4, min(20, round(820 / X))) if auto_zoom else manual_px

# ---------- Icons ----------
ICON = {
    ("Euro","l"): "icons/euro_l.png",
    ("Euro","q"): "icons/euro_q.png",
    ("Industrie","q"): "icons/ind_q.png",
}

# ---------- Maße ----------
def euro_dims(ori):      # depth_cm (entlang L), width_cm (quer)
    return (80, 120) if ori == "q" else (120, 80)

def ind_dims():          # Industrie immer quer
    return 100, 120

# ---------- Raster-Span (CEIL) ----------
def span_cm_to_cells(depth_cm, width_cm):
    dx = max(1, math.ceil(depth_cm / cell_cm))
    dy = max(1, math.ceil(width_cm / cell_cm))
    return dx, dy

def center_y(dy): 
    return max(0, (Y - dy) // 2)

# ---------- Board ----------
def empty_board():
    occ = [[False]*X for _ in range(Y)]
    # items: (x,y,dx,dy,icon,typ,depth_cm_real)
    return occ, [], {"Euro": 0, "Industrie": 0}

def free(occ, x, y, dx, dy):
    if x < 0 or y < 0 or x + dx > X or y + dy > Y:
        return False
    for yy in range(y, y + dy):
        for xx in range(x, x + dx):
            if occ[yy][xx]: return False
    return True

def place(occ, items, placed, x, y, dx, dy, icon, typ, depth_cm_real):
    for yy in range(y, y + dy):
        for xx in range(x, x + dx):
            occ[yy][xx] = True
    items.append((x, y, dx, dy, icon, typ, depth_cm_real))
    placed[typ] += 1

def used_length_cm_true(items):
    if not items: return 0
    x_end = 0
    for (x, y, dx, dy, icon, typ, depth_cm) in items:
        x_end = max(x_end, x * cell_cm + depth_cm)
    return min(x_end, TRAILER_L)

# ---------- Bausteine ----------
def place_euro_row_q(occ, items, placed, x, want=2):
    """Setzt bis zu 2 quer (links+rechts). Gibt (gesetzt, next_x) zurück."""
    depth_cm, width_cm = euro_dims("q")  # 80, 120
    dx, dy = span_cm_to_cells(depth_cm, width_cm)
    set_count = 0
    for y in (0, Y - dy):
        if set_count < want and free(occ, x, y, dx, dy):
            place(occ, items, placed, x, y, dx, dy, ICON[("Euro","q")], "Euro", depth_cm)
            set_count += 1
    return set_count, x + dx

def place_euro_col_l(occ, items, placed, x, want=3):
    """Setzt bis zu 3 längs (links, Mitte, rechts)."""
    depth_cm, width_cm = euro_dims("l")  # 120, 80
    dx, dy = span_cm_to_cells(depth_cm, width_cm)
    set_count = 0
    for y in (0, center_y(dy), Y - dy):
        if set_count < want and free(occ, x, y, dx, dy):
            place(occ, items, placed, x, y, dx, dy, ICON[("Euro","l")], "Euro", depth_cm)
            set_count += 1
    return set_count, x + dx

def place_ind_q(occ, items, placed, x, count):
    depth_cm, width_cm = ind_dims()
    dx, dy = span_cm_to_cells(depth_cm, width_cm)
    if count % 2 == 1:
        y = center_y(dy)
        if free(occ, x, y, dx, dy):
            place(occ, items, placed, x, y, dx, dy, ICON[("Industrie","q")], "Industrie", depth_cm)
            count -= 1; x += dx
    while count > 0 and x + dx <= X:
        for y in (0, Y - dy):
            if count > 0 and free(occ, x, y, dx, dy):
                place(occ, items, placed, x, y, dx, dy, ICON[("Industrie","q")], "Industrie", depth_cm)
                count -= 1
        x += dx
    return x

# ---------- Euro-Varianten (optimierend) ----------
def euro_variant_max_q_then_l(occ, items, placed, x_start, n):
    """Quer-lastig: maximal sinnvolle Querreihen, Rest längs – exakt n Stück."""
    best = None
    for q_rows in range(min(n // 2, TRAILER_L // 80), -1, -1):
        used_q = 2 * q_rows
        rem = n - used_q
        rem_len = TRAILER_L - q_rows * 80
        need_l = math.ceil(rem / 3) if rem > 0 else 0
        if need_l * 120 <= rem_len:
            best = (q_rows, need_l); break
    if best is None: best = (0, math.ceil(n / 3))
    q_rows, l_cols = best

    x = x_start
    # Querreihen
    placed_total = 0
    for _ in range(q_rows):
        can = min(2, n - placed_total)
        got, x = place_euro_row_q(occ, items, placed, x, want=can)
        placed_total += got
    # Längsspalten
    for _ in range(l_cols):
        if placed_total >= n: break
        can = min(3, n - placed_total)
        got, nx = place_euro_col_l(occ, items, placed, x, want=can)
        placed_total += got; x = nx
    # kleiner Rest <120 cm → noch eine Querreihe versuchen
    if placed_total < n:
        can = min(2, n - placed_total)
        got, x = place_euro_row_q(occ, items, placed, x, want=can)
        placed_total += got

def euro_variant_max_l_then_q(occ, items, placed, x_start, n):
    """Längs-lastig: maximal sinnvolle Längsspalten, Rest quer – exakt n Stück."""
    best = None
    for l_cols in range(min(math.ceil(n/3), TRAILER_L // 120), -1, -1):
        used_l = 3 * l_cols
        rem = n - used_l
        rem_len = TRAILER_L - l_cols * 120
        need_q = math.ceil(rem / 2) if rem > 0 else 0
        if need_q * 80 <= rem_len:
            best = (l_cols, need_q); break
    if best is None: best = (0, math.ceil(n / 2))
    l_cols, q_rows = best

    x = x_start
    placed_total = 0
    # Längs
    for _ in range(l_cols):
        if placed_total >= n: break
        can = min(3, n - placed_total)
        got, nx = place_euro_col_l(occ, items, placed, x, want=can)
        placed_total += got; x = nx
    # Quer
    for _ in range(q_rows):
        if placed_total >= n: break
        can = min(2, n - placed_total)
        got, x = place_euro_row_q(occ, items, placed, x, want=can)
        placed_total += got

def euro_variant_all_long(occ, items, placed, x_start, n):
    x = x_start
    left = n
    while left > 0:
        can = min(3, left)
        got, nx = place_euro_col_l(occ, items, placed, x, want=can)
        left -= got; x = nx
        if got == 0: break

def euro_variant_all_cross_with_tail(occ, items, placed, x_start, n):
    x = x_start
    left = n
    # erst maximale Querreihen
    max_q = min(TRAILER_L // 80, math.ceil(n/2))
    for _ in range(max_q):
        if left <= 0: break
        can = min(2, left)
        got, x = place_euro_row_q(occ, items, placed, x, want=can)
        left -= got
    # falls noch Stücke fehlen → Längs-Tail
    while left > 0:
        can = min(3, left)
        got, nx = place_euro_col_l(occ, items, placed, x, want=can)
        left -= got; x = nx
        if got == 0: break

# ---------- Varianten-Generator ----------
def generate_variants(n_euro, n_ind):
    variants = []

    # V1: Industrie → Euro (max quer, dann längs)
    occ, items, placed = empty_board()
    x = place_ind_q(occ, items, placed, 0, n_ind) if n_ind > 0 else 0
    euro_variant_max_q_then_l(occ, items, placed, x, n_euro)
    variants.append((items, placed))

    # V2: Industrie → Euro (max längs, dann quer)
    occ, items, placed = empty_board()
    x = place_ind_q(occ, items, placed, 0, n_ind) if n_ind > 0 else 0
    euro_variant_max_l_then_q(occ, items, placed, x, n_euro)
    variants.append((items, placed))

    # V3: Euro nur längs
    occ, items, placed = empty_board()
    x = place_ind_q(occ, items, placed, 0, n_ind) if n_ind > 0 else 0
    euro_variant_all_long(occ, items, placed, x, n_euro)
    variants.append((items, placed))

    # V4: Euro nur quer (mit längs‑Tail falls nötig)
    occ, items, placed = empty_board()
    x = place_ind_q(occ, items, placed, 0, n_ind) if n_ind > 0 else 0
    euro_variant_all_cross_with_tail(occ, items, placed, x, n_euro)
    variants.append((items, placed))

    return variants

# ---------- UI ----------
st.markdown("### 📥 Manuelle Menge")
c1, c2 = st.columns([1.2, 1.2])
with c1: n_euro = st.number_input("Euro (120×80)", 0, 45, 29)
with c2: n_ind  = st.number_input("Industrie (120×100)", 0, 45, 0)

variants = generate_variants(int(n_euro), int(n_ind))

# ---------- Navigation ----------
if "var_idx" not in st.session_state:
    st.session_state.var_idx = 0
nav1, nav2, nav3 = st.columns([1, 1, 3])
with nav1:
    if st.button("◀ Variante"):
        st.session_state.var_idx = (st.session_state.var_idx - 1) % len(variants)
with nav2:
    if st.button("Variante ▶"):
        st.session_state.var_idx = (st.session_state.var_idx + 1) % len(variants)
with nav3:
    st.markdown(f"**Variante:** {st.session_state.var_idx + 1} / {len(variants)}")

items, placed = variants[st.session_state.var_idx]

# ---------- Render ----------
html = f"""
<div style="
  display:grid;
  grid-template-columns: repeat({X}, {cell_px}px);
  grid-auto-rows: {cell_px}px;
  gap: 1px;
  background:#ddd; padding:6px; border:2px solid #333; width:fit-content;">
"""
for (x, y, dx, dy, icon, typ, depth_cm) in items:
    html += f"""
    <div style="
      grid-column:{x+1}/span {dx};
      grid-row:{y+1}/span {dy};
      background: url('{icon}') center/contain no-repeat, #fafafa;
      border:1px solid #777;"></div>
    """
html += "</div>"
height_px = (cell_px + 1) * Y + 28
height_px = min(680, max(240, height_px))
st.components.v1.html(html, height=height_px, scrolling=False)

# ---------- Auswertung ----------
wanted = {"Euro": int(n_euro), "Industrie": int(n_ind)}
missing_msgs = []
for typ in ("Euro", "Industrie"):
    if wanted[typ] > 0 and placed.get(typ, 0) < wanted[typ]:
        missing = wanted[typ] - placed.get(typ, 0)
        missing_msgs.append(f"– {missing}× {typ} passt/passen nicht mehr")

used_cm = used_length_cm_true(items)
st.markdown(f"**Genutzte Länge (realistisch):** {used_cm} cm von {TRAILER_L} cm (≈ {used_cm/TRAILER_L:.0%})")

if missing_msgs:
    st.error("🚫 **Platz reicht nicht:**\n" + "\n".join(missing_msgs))
else:
    st.success("✅ **Alle angeforderten Paletten passen in den Laderaum.**")

st.caption("Empfehlung: Raster **40 cm** + Auto‑Zoom für stabile, maßhaltige Darstellung.")
