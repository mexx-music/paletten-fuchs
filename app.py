import streamlit as st
from math import ceil

st.set_page_config(page_title="🦊 PAL Fuchs 8 – Final (fixe Physik + 33 längs auto)", layout="wide")
st.title("🦊 PAL Fuchs 8 – Draufsicht (fixe Physik, Varianten, schwere Ladung, 33 längs auto)")

# ---------- Trailer ----------
TRAILER_L, TRAILER_W = 1360, 245  # cm

# ---------- Anzeige (nur Optik) ----------
cell_cm = st.sidebar.slider("Raster (cm/Zelle) – Anzeige", 10, 40, 25, 5)  # nur Darstellung
cell_px = st.sidebar.slider("Zellpixel (Zoom)", 4, 16, 4, 1)
st.caption(f"Anzeige: {TRAILER_W//cell_cm} × {TRAILER_L//cell_cm} Zellen • 1 Zelle = {cell_cm} cm")

# ---------- Icons ----------
ICON = {
    ("Euro","l"): "icons/euro_l.png",
    ("Euro","q"): "icons/euro_q.png",
    ("Industrie","q"): "icons/ind_q.png",
    ("Blume","l"): "icons/flower_l.png",
    ("Blume","q"): "icons/flower_q.png",
}

# ---------- Fixe Physik (immer 20 cm) ----------
CALC_CELL_CM = 20
GX, GY = TRAILER_L // CALC_CELL_CM, TRAILER_W // CALC_CELL_CM  # interne Zellen (x=Länge, y=Breite)

def span_int(name, ori):
    if name == "Euro":        L,B = 120, 80
    elif name == "Industrie": L,B = 120,100
    else:                     L,B = 135, 55  # Blumenwagen
    if name == "Industrie":   ori = "q"      # Industrie immer quer
    depth_cm, width_cm = (B, L) if ori == "q" else (L, B)
    dx = max(1, ceil(depth_cm / CALC_CELL_CM))   # entlang Länge
    dy = max(1, ceil(width_cm  / CALC_CELL_CM))  # quer
    return dx, dy

def empty_board():
    occ = [[False]*GX for _ in range(GY)]
    items = []  # (x,y,dx,dy,icon,typ)  -> x,y,dx,dy in 20-cm-Zellen
    placed = {"Euro":0, "Industrie":0, "Blume":0}
    return occ, items, placed

def center_y_int(dy): return max(0, (GY - dy)//2)

def free_int(occ, x,y,dx,dy):
    if x<0 or y<0 or x+dx>GX or y+dy>GY: return False
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            if occ[yy][xx]: return False
    return True

def place_int(occ, items, placed, x,y,dx,dy,icon,typ):
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            occ[yy][xx] = True
    items.append((x,y,dx,dy,icon,typ))
    placed[typ] += 1

def first_free_x_int(occ):
    for xx in range(GX):
        if any(not occ[yy][xx] for yy in range(GY)): return xx
    return GX

def used_length_cm(items):
    if not items: return 0
    x_end = max(x+dx for (x,y,dx,dy,icon,typ) in items)
    return x_end * CALC_CELL_CM

# ---------- Abschluss Euro: 3 längs, Rest 2 quer ----------
def fill_tail_closed_euro(occ, items, placed, x_start, euro_left):
    if euro_left <= 0: return
    dq,wq = span_int("Euro","q")
    dl,wl = span_int("Euro","l")

    if euro_left % 3 == 0 or euro_left < 2:
        cols_long = euro_left // 3; need_tail_q = False
    else:
        cols_long = max(0, (euro_left - 2)//3); need_tail_q = True

    lanes = [0, center_y_int(wl), GY-wl]
    x = x_start
    for _ in range(cols_long):
        if x + dl > GX: break
        for y in lanes:
            if free_int(occ, x,y,dl,wl):
                place_int(occ, items, placed, x,y,dl,wl, ICON[("Euro","l")], "Euro")
        x += dl

    if need_tail_q and x + dq <= GX:
        if free_int(occ, x,0,dq,wq):
            place_int(occ, items, placed, x,0,dq,wq, ICON[("Euro","q")], "Euro")
        if free_int(occ, x,GY-wq,dq,wq):
            place_int(occ, items, placed, x,GY-wq,dq,wq, ICON[("Euro","q")], "Euro")

# ---------- Bausteine ----------
def block_industrie_all(occ, items, placed, n):
    dq,wq = span_int("Industrie","q")
    x=0
    if n%2==1:
        y=center_y_int(wq)
        if free_int(occ, x,y,dq,wq):
            place_int(occ, items, placed, x,y,dq,wq, ICON[("Industrie","q")], "Industrie")
            n -= 1; x += dq
    while n>0 and x+dq<=GX:
        for y in [0, GY-wq]:
            if n>0 and free_int(occ, x,y,dq,wq):
                place_int(occ, items, placed, x,y,dq,wq, ICON[("Industrie","q")], "Industrie")
                n -= 1
        x += dq
    return x

def block_euro_only_long(occ, items, placed, x_start, n):
    dl,wl = span_int("Euro","l")
    lanes = [0, center_y_int(wl), GY-wl]
    x = x_start
    while n>0 and x+dl<=GX:
        for y in lanes:
            if n>0 and free_int(occ, x,y,dl,wl):
                place_int(occ, items, placed, x,y,dl,wl, ICON[("Euro","l")], "Euro")
                n -= 1
        x += dl

def block_euro_cross_then_long(occ, items, placed, x_start, n):
    dq,wq = span_int("Euro","q");  dl,wl = span_int("Euro","l")
    x = x_start
    if n>0 and x+dq<=GX and free_int(occ, x,center_y_int(wq),dq,wq):
        place_int(occ, items, placed, x,center_y_int(wq),dq,wq, ICON[("Euro","q")], "Euro")
        n -= 1; x += dq
    if n>=2 and x+dq<=GX:
        for y in [0, GY-wq]:
            if n>0 and free_int(occ, x,y,dq,wq):
                place_int(occ, items, placed, x,y,dq,wq, ICON[("Euro","q")], "Euro")
                n -= 1
        x += dq
    fill_tail_closed_euro(occ, items, placed, x, n)

def block_euro_long_then_cross_tail(occ, items, placed, x_start, n):
    dl,wl = span_int("Euro","l")
    lanes = [0, center_y_int(wl), GY-wl]
    x = x_start
    col_cap = 3
    while n >= col_cap and x+dl <= GX:
        for y in lanes:
            if free_int(occ, x,y,dl,wl):
                place_int(occ, items, placed, x,y,dl,wl, ICON[("Euro","l")], "Euro")
        n -= col_cap
        x += dl
    fill_tail_closed_euro(occ, items, placed, x, n)

# ---------- Schwere Ladung (21–24) ----------
def euro_heavy(occ, items, placed, n, x0=0):
    dq,wq = span_int("Euro","q");  dl,wl = span_int("Euro","l")
    yC = center_y_int(wq)
    x = x0

    singles_front = 2 if n >= 23 else 1
    for _ in range(min(singles_front, n)):
        if x+dq<=GX and free_int(occ, x,yC,dq,wq):
            place_int(occ, items, placed, x,yC,dq,wq, ICON[("Euro","q")], "Euro")
            n -= 1; x += dq

    pair_sets = 2 if n >= 22 else 1
    for _ in range(pair_sets):
        if n <= 0 or x+dq>GX: break
        for y in [0, GY-wq]:
            if n>0 and free_int(occ, x,y,dq,wq):
                place_int(occ, items, placed, x,y,dq,wq, ICON[("Euro","q")], "Euro")
                n -= 1
        x += dq

    if n>0 and x+dq<=GX and free_int(occ, x,yC,dq,wq):
        place_int(occ, items, placed, x,yC,dq,wq, ICON[("Euro","q")], "Euro")
        n -= 1; x += dq

    fill_tail_closed_euro(occ, items, placed, x, n)

# ---------- Varianten ----------
def generate_variants(n_euro, n_ind, force_euro_long=False, heavy=False):
    # 33 Euro immer nur längs
    if n_euro == 33:
        occ, items, placed = empty_board()
        if n_ind > 0:
            block_industrie_all(occ, items, placed, n_ind)
            start = first_free_x_int(occ)
            block_euro_only_long(occ, items, placed, start, n_euro)
        else:
            block_euro_only_long(occ, items, placed, 0, n_euro)
        return [(items, placed)]

    variants = []

    # Var A
    occ, items, placed = empty_board()
    if n_ind>0: block_industrie_all(occ, items, placed, n_ind)
    start = first_free_x_int(occ)
    if heavy and 21 <= n_euro <= 24:
        euro_heavy(occ, items, placed, n_euro, start)
    elif force_euro_long:
        block_euro_only_long(occ, items, placed, start, n_euro)
    else:
        block_euro_cross_then_long(occ, items, placed, start, n_euro)
    variants.append((items, placed))

    # Var B
    occ, items, placed = empty_board()
    if n_ind>0: block_industrie_all(occ, items, placed, n_ind)
    start = first_free_x_int(occ)
    if heavy and 21 <= n_euro <= 24:
        euro_heavy(occ, items, placed, n_euro, start)
    else:
        block_euro_long_then_cross_tail(occ, items, placed, start, n_euro)
    variants.append((items, placed))

    # Var C – Euro nur längs über alles
    occ, items, placed = empty_board()
    if n_ind>0:
        block_industrie_all(occ, items, placed, n_ind)
        start = first_free_x_int(occ)
        block_euro_only_long(occ, items, placed, start, n_euro)
    else:
        block_euro_only_long(occ, items, placed, 0, n_euro)
    variants.append((items, placed))

    # Var D – doppelt quer außen, dann Abschluss
    occ, items, placed = empty_board()
    if n_ind>0: block_industrie_all(occ, items, placed, n_ind)
    start = first_free_x_int(occ)
    if heavy and 21 <= n_euro <= 24:
        euro_heavy(occ, items, placed, n_euro, start)
    else:
        dq,wq = span_int("Euro","q")
        x = start; n = n_euro
        if n>=2 and x+dq<=GX:
            for y in [0, GY-wq]:
                if free_int(occ, x,y,dq,wq):
                    place_int(occ, items, placed, x,y,dq,wq, ICON[("Euro","q")], "Euro")
                    n -= 1
            x += dq
        fill_tail_closed_euro(occ, items, placed, x, n)
    variants.append((items, placed))

    return variants

# ---------- UI ----------
st.subheader("📥 Manuelle Menge")
c1,c2,c3,c4 = st.columns([1.2,1.2,1.2,1.6])
with c1: n_euro = st.number_input("Euro (120×80)", 0, 45, 30)
with c2: n_ind  = st.number_input("Industrie (120×100)", 0, 45, 0)
with c3: force_long = st.checkbox("Euro nur längs erzwingen", value=False, help="Für Spezialfälle außer 33 – bei 33 wird automatisch längs gesetzt.")
with c4: heavy = st.checkbox("Schwere Ladung (21–24) – Vorderachse entlasten", value=False)

variants = generate_variants(int(n_euro), int(n_ind), force_euro_long=force_long, heavy=heavy)

# ---------- Varianten-Navigation ----------
if "var_idx" not in st.session_state: st.session_state.var_idx = 0
colL,colR,colI = st.columns([1,1,3])
with colL:
    if st.button("◀ Variante"):
        st.session_state.var_idx = (st.session_state.var_idx - 1) % len(variants)
with colR:
    if st.button("Variante ▶"):
        st.session_state.var_idx = (st.session_state.var_idx + 1) % len(variants)
with colI:
    st.markdown(f"**Variante:** {st.session_state.var_idx+1} / {len(variants)}")

items, placed = variants[st.session_state.var_idx]

# ---------- Render (20 cm -> Anzeige-Raster) ----------
disp_cols = TRAILER_L // cell_cm
disp_rows = TRAILER_W // cell_cm
def map_cells(n_calc):  # 20‑cm‑Zellen -> Anzeige‑Zellen
    return max(1, round(n_calc * CALC_CELL_CM / cell_cm))

html = f"""
<div style="display:grid; grid-template-columns: repeat({disp_cols}, {cell_px}px);
            grid-auto-rows:{cell_px}px; gap: 1px; background:#ddd; padding:4px;
            border:2px solid #333; width:fit-content;">
"""
for (x,y,dx,dy,icon,typ) in items:
    gx, gy = map_cells(x), map_cells(y)
    gsx, gsy = map_cells(dx), map_cells(dy)
    html += f"""
    <div title='{typ}' style="
      grid-column:{gx+1}/span {gsx};
      grid-row:{gy+1}/span {gsy};
      background:url('{icon}') center/contain no-repeat, #fafafa;
      border:1px solid #777;"></div>
    """
html += "</div>"
st.components.v1.html(html, height=min(560, (cell_px+1)*disp_rows+40), scrolling=False)

# ---------- Kapazität (cm-basiert) ----------
wanted = {"Euro": int(n_euro), "Industrie": int(n_ind)}
missing_msgs = []
for typ in ["Euro","Industrie"]:
    if wanted[typ] > 0 and placed.get(typ,0) < wanted[typ]:
        missing = wanted[typ] - placed.get(typ,0)
        missing_msgs.append(f"– {missing}× {typ} passt/passen nicht mehr")

used_cm = used_length_cm(items)
st.markdown(f"**Genutzte Länge (real):** {used_cm} cm von {TRAILER_L} cm  (≈ {used_cm/TRAILER_L:.0%})")

if used_cm > TRAILER_L:
    st.error("🚫 **Platz reicht nicht (Länge):** Reale Nutzlänge überschreitet 13,6 m.")
elif missing_msgs:
    st.error("🚫 **Platz reicht nicht (Anzahl):**\n" + "\n".join(missing_msgs))
else:
    st.success("✅ **Alle angeforderten Paletten passen in den Laderaum.")
