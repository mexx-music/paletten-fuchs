import math
import streamlit as st

st.set_page_config(page_title="🦊 PAL Fuchs 8 – Varianten (Real-Logik)", layout="wide")
st.title("🦊 PAL Fuchs – Draufsicht mit Icons & Varianten (Real-Logik)")

# ---------- Trailer & Grid ----------
TRAILER_L, TRAILER_W = 1360, 245  # cm

# Empfohlen: Raster 40 cm (120=3 Zellen, 80=2 Zellen → exakte Darstellung)
cell_cm = st.sidebar.slider("Raster (cm/Zelle)", 20, 50, 40, 5)
cell_px = st.sidebar.slider("Zellpixel (Zoom)", 4, 16, 4, 1)

X, Y = TRAILER_L // cell_cm, TRAILER_W // cell_cm

# ---------- Icons ----------
ICON = {
    ("Euro","l"): "icons/euro_l.png",
    ("Euro","q"): "icons/euro_q.png",
    ("Industrie","q"): "icons/ind_q.png",
}

# ---------- Maße & Raster-Span ----------
def euro_dims(ori):
    # Rückgabe: (depth_cm_along_length, width_cm_across_trailer)
    if ori == "q":   # quer: 80 Tiefe, 120 Breite
        return 80, 120
    else:            # längs: 120 Tiefe, 80 Breite
        return 120, 80

def ind_dims():      # Industrie immer quer
    return 100, 120   # 100 Tiefe, 120 Breite (120x100)

def span_cm_to_cells(depth_cm, width_cm):
    # Ceil-Rasterung (nichts wird zu klein gerendert)
    dx = max(1, math.ceil(depth_cm / cell_cm))
    dy = max(1, math.ceil(width_cm / cell_cm))
    return dx, dy

def center_y(dy): 
    return max(0, (Y - dy) // 2)

# ---------- Board ----------
def empty_board():
    occupied = [[False]*X for _ in range(Y)]
    # items: (x, y, dx, dy, icon, typ, depth_cm_real)
    items = []
    placed = {"Euro": 0, "Industrie": 0}
    return occupied, items, placed

def free(occ, x, y, dx, dy):
    if x < 0 or y < 0 or x + dx > X or y + dy > Y:
        return False
    for yy in range(y, y + dy):
        for xx in range(x, x + dx):
            if occ[yy][xx]:
                return False
    return True

def place(occ, items, placed, x, y, dx, dy, icon, typ, depth_cm_real):
    for yy in range(y, y + dy):
        for xx in range(x, x + dx):
            occ[yy][xx] = True
    items.append((x, y, dx, dy, icon, typ, depth_cm_real))
    placed[typ] += 1

def used_length_cm_true(items):
    """Maximale reale Ausdehnung in cm (Start in Zellen * Raster + reale Tiefe)."""
    if not items:
        return 0
    x_end_cm = 0
    for (x, y, dx, dy, icon, typ, depth_cm) in items:
        right = x * cell_cm + depth_cm
        if right > x_end_cm:
            x_end_cm = right
    return min(x_end_cm, TRAILER_L)

# ---------- Bausteine: Euro quer / längs & Industrie quer ----------
def place_euro_row_q(occ, items, placed, x):
    depth_cm, width_cm = euro_dims("q")  # 80, 120
    dx, dy = span_cm_to_cells(depth_cm, width_cm)
    y_left = 0
    y_right = Y - dy
    ok = True
    for y in [y_left, y_right]:
        if free(occ, x, y, dx, dy):
            place(occ, items, placed, x, y, dx, dy, ICON[("Euro","q")], "Euro", depth_cm)
        else:
            ok = False
    return ok, x + dx  # neue x-Position (nächste Querreihe)

def place_euro_col_l(occ, items, placed, x):
    depth_cm, width_cm = euro_dims("l")  # 120, 80
    dx, dy = span_cm_to_cells(depth_cm, width_cm)
    lanes = [0, center_y(dy), Y - dy]
    ok = True
    for y in lanes:
        if free(occ, x, y, dx, dy):
            place(occ, items, placed, x, y, dx, dy, ICON[("Euro","l")], "Euro", depth_cm)
        else:
            ok = False
    return ok, x + dx

def place_ind_q(occ, items, placed, x, count):
    depth_cm, width_cm = ind_dims()     # 100, 120
    dx, dy = span_cm_to_cells(depth_cm, width_cm)
    # ungerade: 1 mittig vorne
    if count % 2 == 1:
        y = center_y(dy)
        if free(occ, x, y, dx, dy):
            place(occ, items, placed, x, y, dx, dy, ICON[("Industrie","q")], "Industrie", depth_cm)
            count -= 1
            x += dx
    # Paare links/rechts
    while count > 0 and x + dx <= X:
        for y in [0, Y - dy]:
            if count > 0 and free(occ, x, y, dx, dy):
                place(occ, items, placed, x, y, dx, dy, ICON[("Industrie","q")], "Industrie", depth_cm)
                count -= 1
        x += dx
    return x

# ---------- Euro-Varianten: echte Logik ----------
def euro_variant_auto_max_q_then_l(occ, items, placed, x_start, n):
    """Maximiere Querreihen (2 Pal/80cm) unter der Nebenbedingung,
       dass der Rest als Längsspalten (3 Pal/120cm) noch reinpasst."""
    # Kapazitäten in der Länge (cm)
    max_q_by_len = TRAILER_L // 80
    # Wir probieren von oben nach unten (so viele Querreihen wie möglich)
    best = None
    for q_rows in range(min(n // 2, max_q_by_len), -1, -1):
        used_pals_q = 2 * q_rows
        rem_pals = n - used_pals_q
        rem_len = TRAILER_L - q_rows * 80
        need_l_cols = math.ceil(rem_pals / 3) if rem_pals > 0 else 0
        if need_l_cols * 120 <= rem_len:
            best = (q_rows, need_l_cols)
            break
    if best is None:
        best = (0, math.ceil(n / 3))
    q_rows, l_cols = best

    x = x_start
    # Querreihen setzen
    for _ in range(q_rows):
        ok, x = place_euro_row_q(occ, items, placed, x)

    # Längsspalten setzen
    remaining = n - 2 * q_rows
    for _ in range(l_cols):
        if remaining <= 0:
            break
        ok, nx = place_euro_col_l(occ, items, placed, x)
        placed_now = min(3, remaining)
        remaining -= placed_now
        x = nx

    # Falls kleiner Rest (<120 cm) und noch 2 Pal fehlen → eine Querreihe versuchen
    if remaining > 0:
        ok, x = place_euro_row_q(occ, items, placed, x)

def euro_variant_auto_max_l_then_q(occ, items, placed, x_start, n):
    """Erst möglichst viele Längsspalten, Rest mit Querreihen auffüllen."""
    max_l_by_len = TRAILER_L // 120
    best = None
    for l_cols in range(min(math.ceil(n/3), max_l_by_len), -1, -1):
        used_pals_l = 3 * l_cols
        rem_pals = n - used_pals_l
        rem_len = TRAILER_L - l_cols * 120
        need_q_rows = math.ceil(rem_pals / 2) if rem_pals > 0 else 0
        if need_q_rows * 80 <= rem_len:
            best = (l_cols, need_q_rows)
            break
    if best is None:
        best = (0, math.ceil(n / 2))
    l_cols, q_rows = best

    x = x_start
    remaining = n
    # Längs zuerst
    for _ in range(l_cols):
        if remaining <= 0: break
        ok, nx = place_euro_col_l(occ, items, placed, x)
        placed_now = min(3, remaining); remaining -= placed_now
        x = nx
    # Quer danach
    for _ in range(q_rows):
        if remaining <= 0: break
        ok, x = place_euro_row_q(occ, items, placed, x)
        placed_now = min(2, remaining); remaining -= placed_now

def euro_variant_all_long(occ, items, placed, x_start, n):
    x = x_start
    remaining = n
    while remaining > 0:
        ok, nx = place_euro_col_l(occ, items, placed, x)
        placed_now = min(3, remaining)
        remaining -= placed_now
        x = nx

def euro_variant_all_cross_with_tail(occ, items, placed, x_start, n):
    # so viele Querreihen wie möglich, evtl. 1–2 Längsspalten am Ende, falls 1–3 Stück übrig
    x = x_start
    full_q = min(n // 2, TRAILER_L // 80)
    for _ in range(full_q):
        ok, x = place_euro_row_q(occ, items, placed, x)
    remaining = n - 2 * full_q
    while remaining > 0:
        ok, nx = place_euro_col_l(occ, items, placed, x)
        placed_now = min(3, remaining); remaining -= placed_now
        x = nx

# ---------- Varianten-Generator ----------
def generate_variants(n_euro, n_ind):
    variants = []

    # Variante 1: Industrie → Euro (max quer, dann längs)
    occ, items, placed = empty_board()
    x = 0
    if n_ind > 0:
        x = place_ind_q(occ, items, placed, x, n_ind)
    euro_variant_auto_max_q_then_l(occ, items, placed, x, n_euro)
    variants.append((items, placed))

    # Variante 2: Industrie → Euro (max längs, dann quer)
    occ, items, placed = empty_board()
    x = 0
    if n_ind > 0:
        x = place_ind_q(occ, items, placed, x, n_ind)
    euro_variant_auto_max_l_then_q(occ, items, placed, x, n_euro)
    variants.append((items, placed))

    # Variante 3: Euro-only längs
    occ, items, placed = empty_board()
    x = 0
    if n_ind > 0:
        x = place_ind_q(occ, items, placed, x, n_ind)
    euro_variant_all_long(occ, items, placed, x, n_euro)
    variants.append((items, placed))

    # Variante 4: Euro-only quer (mit Längs-Tail falls nötig)
    occ, items, placed = empty_board()
    x = 0
    if n_ind > 0:
        x = place_ind_q(occ, items, placed, x, n_ind)
    euro_variant_all_cross_with_tail(occ, items, placed, x, n_euro)
    variants.append((items, placed))

    return variants

# ---------- UI ----------
st.markdown("### 📥 Manuelle Menge")
c1, c2 = st.columns([1.2, 1.2])
with c1: n_euro = st.number_input("Euro (120×80)", 0, 45, 33)
with c2: n_ind  = st.number_input("Industrie (120×100)", 0, 45, 0)

variants = generate_variants(int(n_euro), int(n_ind))

# Navigation
if "var_idx" not in st.session_state: st.session_state.var_idx = 0
nav1, nav2, nav3 = st.columns([1, 1, 3])
with nav1:
    if st.button("◀ Variante"):
        st.session_state.var_idx = (st.session_state.var_idx - 1) % len(variants)
with nav2:
    if st.button("Variante ▶"):
        st.session_state.var_idx = (st.session_state.var_idx + 1) % len(variants)
with nav3:
    st.markdown(f"**Variante:** {st.session_state.var_idx+1} / {len(variants)}")

items, placed = variants[st.session_state.var_idx]

# ---------- Render ----------
html = f"""
<div style="
  display:grid;
  grid-template-columns: repeat({X}, {cell_px}px);
  grid-auto-rows: {cell_px}px;
  gap: 1px;
  background:#ddd; padding:4px; border:2px solid #333; width:fit-content;">
"""
for (x,y,dx,dy,icon,typ,depth_cm) in items:
    html += f"""
    <div style="
      grid-column:{x+1}/span {dx};
      grid-row:{y+1}/span {dy};
      background: url('{icon}') center/contain no-repeat, #fafafa;
      border:1px solid #777;"></div>
    """
html += "</div>"
height = min(560, (cell_px+1)*Y + 40)
st.components.v1.html(html, height=height, scrolling=False)

# ---------- Kapazitätsprüfung & echte Nutzlänge ----------
wanted = {"Euro": int(n_euro), "Industrie": int(n_ind)}
missing_msgs = []
for typ in ["Euro","Industrie"]:
    if wanted[typ] > 0 and placed.get(typ, 0) < wanted[typ]:
        missing = wanted[typ] - placed.get(typ, 0)
        missing_msgs.append(f"– {missing}× {typ} passt/passen nicht mehr")

used_cm = used_length_cm_true(items)
st.markdown(f"**Genutzte Länge (realistisch):** {used_cm} cm von {TRAILER_L} cm (≈ {used_cm/TRAILER_L:.0%})")

if missing_msgs:
    st.error("🚫 **Platz reicht nicht:**\n" + "\n".join(missing_msgs))
else:
    st.success("✅ **Alle angeforderten Paletten passen in den Laderaum.**")

st.info("Empfehlung: Raster **40 cm** verwenden – dann sind 120/80 cm exakt darstellbar (3/2 Zellen).")
