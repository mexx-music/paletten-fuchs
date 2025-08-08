import streamlit as st
from math import ceil

st.set_page_config(page_title="🦊 PAL Fuchs 7 – Physik 20 cm, Anzeige 25/4", layout="wide")
st.title("🦊 PAL Fuchs 7 – Draufsicht (fixe Physik, freie Anzeige)")

# ---------- Trailer ----------
TRAILER_L, TRAILER_W = 1360, 245  # cm

# ---------- Anzeige (nur Optik) ----------
cell_cm_view = st.sidebar.slider("Raster (cm/Zelle) – Anzeige", 10, 40, 25, 5)
cell_px = st.sidebar.slider("Zellpixel (Zoom)", 4, 16, 4, 1)
st.caption(f"Anzeige: {TRAILER_W//cell_cm_view} × {TRAILER_L//cell_cm_view} Zellen • 1 Zelle = {cell_cm_view} cm")

# ---------- Icons ----------
ICON = {
    ("Euro","l"): "icons/euro_l.png",
    ("Euro","q"): "icons/euro_q.png",
    ("Industrie","q"): "icons/ind_q.png",
    ("Blume","l"): "icons/flower_l.png",
    ("Blume","q"): "icons/flower_q.png",
}

# ---------- Fixe Physik (20 cm) ----------
CALC_CELL_CM = 20
GX, GY = TRAILER_L // CALC_CELL_CM, TRAILER_W // CALC_CELL_CM  # interne Zellen (x = Länge, y = Breite)

# Board
occupied = [[False]*GX for _ in range(GY)]
items = []  # (x,y,dx,dy,icon,typ)
placed = {"Euro":0, "Industrie":0, "Blume":0}

def reset_board():
    global occupied, items, placed
    occupied = [[False]*GX for _ in range(GY)]
    items.clear()
    placed = {"Euro":0, "Industrie":0, "Blume":0}

def span_int(name, ori):
    # wie PF7, aber mit ceil auf 20‑cm Raster
    if name == "Euro":        L,B = 120, 80
    elif name == "Industrie": L,B = 120,100
    else:                     L,B = 135, 55  # Blumenwagen
    if name == "Industrie":
        ori = "q"  # Regel
    depth_cm, width_cm = (B, L) if ori == "q" else (L, B)
    dx = max(1, ceil(depth_cm / CALC_CELL_CM))   # entlang Länge
    dy = max(1, ceil(width_cm  / CALC_CELL_CM))  # quer
    return dx, dy

def free_int(x,y,dx,dy):
    if x<0 or y<0 or x+dx>GX or y+dy>GY: return False
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            if occupied[yy][xx]: return False
    return True

def place_int(x,y,dx,dy,icon,typ):
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            occupied[yy][xx] = True
    items.append((x,y,dx,dy,icon,typ))
    placed[typ] += 1

def center_y_int(dy): return max(0,(GY-dy)//2)
def first_free_x_int():
    for xx in range(GX):
        if any(not occupied[yy][xx] for yy in range(GY)): return xx
    return GX

def used_length_cm():
    if not items: return 0
    x_end = max(x+dx for (x,y,dx,dy,icon,typ) in items)
    return x_end * CALC_CELL_CM

# ---------- PF7-Logik auf interner Physik ----------
def fill_tail_closed_euro(x_start, euro_left):
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
        if x+dl > GX: break
        for y in lanes:
            if free_int(x,y,dl,wl):
                place_int(x,y,dl,wl, ICON[("Euro","l")], "Euro")
        x += dl
    if need_tail_q and x+dq <= GX:
        if free_int(x,0,dq,wq): place_int(x,0,dq,wq, ICON[("Euro","q")], "Euro")
        if free_int(x,GY-wq,dq,wq): place_int(x,GY-wq,dq,wq, ICON[("Euro","q")], "Euro")

def euro_30(n):
    reset_board()
    dq,wq = span_int("Euro","q")
    x=0
    if n>0 and free_int(x,center_y_int(wq),dq,wq):
        place_int(x,center_y_int(wq),dq,wq, ICON[("Euro","q")], "Euro"); n-=1
    x += dq
    for y in [0, GY-wq]:
        if n>0 and free_int(x,y,dq,wq): place_int(x,y,dq,wq, ICON[("Euro","q")], "Euro"); n-=1
    x += dq
    fill_tail_closed_euro(x, n)

def euro_24(n):
    reset_board()
    dq,wq = span_int("Euro","q"); x=0; yC=center_y_int(wq)
    for _ in range(min(2,n)):
        if free_int(x,yC,dq,wq): place_int(x,yC,dq,wq, ICON[("Euro","q")], "Euro"); n-=1; x+=dq
    for _ in range(2):
        if n<=0: break
        for y in [0, GY-wq]:
            if n>0 and free_int(x,y,dq,wq): place_int(x,y,dq,wq, ICON[("Euro","q")], "Euro"); n-=1
        x += dq
    if n>0 and free_int(x,yC,dq,wq): place_int(x,yC,dq,wq, ICON[("Euro","q")], "Euro"); n-=1; x+=dq
    fill_tail_closed_euro(x, n)

def industrie_all(n):
    dq,wq = span_int("Industrie","q")
    x=0
    if n%2==1:
        y=center_y_int(wq)
        if free_int(x,y,dq,wq): place_int(x,y,dq,wq, ICON[("Industrie","q")], "Industrie"); n-=1; x+=dq
    while n>0 and x+dq<=GX:
        for y in [0, GY-wq]:
            if n>0 and free_int(x,y,dq,wq): place_int(x,y,dq,wq, ICON[("Industrie","q")], "Industrie"); n-=1
        x += dq

def euro_rows_from(x_start, n):
    dl,wl = span_int("Euro","l")
    x = x_start
    lanes=[0, center_y_int(wl), GY-wl]
    while n>0 and x+dl<=GX:
        for y in lanes:
            if n>0 and free_int(x,y,dl,wl):
                place_int(x,y,dl,wl, ICON[("Euro","l")], "Euro"); n-=1
        x+=dl

def mix_21_6():
    reset_board()
    industrie_all(6)
    start = first_free_x_int()
    dq,wq = span_int("Euro","q"); x = start; rem = 21
    if rem>0 and x+dq<=GX and free_int(x,center_y_int(wq),dq,wq):
        place_int(x,center_y_int(wq),dq,wq, ICON[("Euro","q")], "Euro"); rem-=1; x+=dq
    if rem>=2 and x+dq<=GX:
        for y in [0, GY-wq]:
            if rem>0 and free_int(x,y,dq,wq): place_int(x,y,dq,wq, ICON[("Euro","q")], "Euro"); rem-=1
        x+=dq
    fill_tail_closed_euro(x, rem)

# ---------- UI ----------
st.markdown("### ⚡ Presets")
b1,b2,b3,b4 = st.columns(4)
if b1.button("Euro 30"): euro_30(30)
if b2.button("Euro 24 (schwer)"): euro_24(24)
if b3.button("Industrie 26"): reset_board(); industrie_all(26)
if b4.button("Mix 21 Euro + 6 Industrie"): mix_21_6()

st.markdown("### 📥 Manuelle Menge (ohne Preset)")
c1,c2,c3,c4 = st.columns([1.2,1.2,1.2,1.6])
with c1: n_euro = st.number_input("Euro (120×80)", 0, 45, 30)
with c2: n_ind  = st.number_input("Industrie (120×100)", 0, 45, 0)
with c3: flowers = st.checkbox("Blumenwagen", value=False)
with c4: n_flow = st.number_input("Blumenwagen (135×55)", 0, 60, 0, disabled=not flowers)

if not items:
    reset_board()
    if n_ind>0 and n_euro>0:
        industrie_all(n_ind)
        start = first_free_x_int()
        dq,wq = span_int("Euro","q")
        x=start; rem=n_euro
        if rem>0 and x+dq<=GX and free_int(x,center_y_int(wq),dq,wq):
            place_int(x,center_y_int(wq),dq,wq, ICON[("Euro","q")], "Euro"); rem-=1; x+=dq
        if rem>=2 and x+dq<=GX:
            for y in [0, GY-wq]:
                if rem>0 and free_int(x,y,dq,wq): place_int(x,y,dq,wq, ICON[("Euro","q")], "Euro"); rem-=1
            x+=dq
        fill_tail_closed_euro(x, rem)
    elif n_euro>=30:
        euro_30(n_euro)
    elif n_euro>=24:
        euro_24(n_euro)
    elif n_euro>0:
        euro_rows_from(0, n_euro)
    elif n_ind>0:
        industrie_all(n_ind)

# ---------- Render (interne 20 cm → Anzeige-Raster) ----------
st.subheader("🗺️ Ladeplan (Draufsicht, hinten = unten)")
disp_cols = TRAILER_L // cell_cm_view
disp_rows = TRAILER_W // cell_cm_view
def map_cells(n_calc):  # n_calc in 20‑cm‑Zellen
    return max(1, round(n_calc * CALC_CELL_CM / cell_cm_view))

html = f"""
<div style="
  display:grid;
  grid-template-columns: repeat({disp_cols}, {cell_px}px);
  grid-auto-rows: {cell_px}px;
  gap: 1px; background:#ddd; padding:4px; border:2px solid #333; width:fit-content;">
"""
for (x,y,dx,dy,icon,typ) in items:
    gx, gy = map_cells(x), map_cells(y)
    gsx, gsy = map_cells(dx), map_cells(dy)
    html += f"""
    <div style="grid-column:{gx+1}/span {gsx}; grid-row:{gy+1}/span {gsy};
                background: url('{icon}') center/contain no-repeat, #fafafa;
                border:1px solid #777;"></div>
    """
html += "</div>"
st.components.v1.html(html, height=min(560, (cell_px+1)*disp_rows+40), scrolling=False)

# ---------- Kapazität ----------
used_cm = used_length_cm()
st.markdown(f"**Genutzte Länge (real):** {used_cm} cm von {TRAILER_L} cm  (≈ {used_cm/TRAILER_L:.0%})")
if used_cm > TRAILER_L:
    st.error("🚫 **Platz reicht nicht (Länge):** Reale Nutzlänge überschreitet 13,6 m.")
