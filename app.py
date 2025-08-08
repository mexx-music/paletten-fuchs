
import streamlit as st
from math import ceil

st.set_page_config(page_title="🦊 Paletten Fuchs 7 – Fixraster", layout="wide")
st.title("📦 Paletten Fuchs 7 – Sattelzug Ladeplan (Fixmaßstab)")

TRAILER_L, TRAILER_W = 1360, 245  # cm

# Anzeige-Optionen (nur Optik)
col1, col2 = st.columns(2)
with col1:
    preset = st.selectbox("Preset", ["– manuell –", "Euro 30", "Euro 24 (schwer)", "Industrie 26", "Mix 21 Euro + 6 Industrie"], index=0)
with col2:
    cell_cm_view = st.slider("Anzeige‑Raster (cm/Zelle)", 10, 40, 20, 5)
    cell_px = st.slider("Zellpixel (Zoom)", 6, 18, 10, 1)

st.caption(f"Anzeige: {TRAILER_W//cell_cm_view} × {TRAILER_L//cell_cm_view} Zellen • 1 Zelle = {cell_cm_view} cm")

ICON = {
    ("Euro","l"): "icons/euro_l.png",
    ("Euro","q"): "icons/euro_q.png",
    ("Industrie","q"): "icons/ind_q.png",
    ("Blume","l"): "icons/flower_l.png",
    ("Blume","q"): "icons/flower_q.png",
}

# Fixes Berechnungsraster
CALC_CELL_CM = 20
GX, GY = TRAILER_L // CALC_CELL_CM, TRAILER_W // CALC_CELL_CM

occ = [[False]*GX for _ in range(GY)]
items = []
placed = {"Euro":0, "Industrie":0, "Blume":0}

def reset_board():
    global occ, items, placed
    occ = [[False]*GX for _ in range(GY)]
    items = []
    placed = {"Euro":0, "Industrie":0, "Blume":0}

def span_int(name, ori):
    if name == "Euro":        L,B = 120, 80
    elif name == "Industrie": L,B = 120, 100
    else:                     L,B = 135, 55
    if name == "Industrie":
        ori = "q"
    depth_cm, width_cm = (B, L) if ori == "q" else (L, B)
    dx = ceil(depth_cm / CALC_CELL_CM)
    dy = ceil(width_cm  / CALC_CELL_CM)
    return dx, dy

def free_int(x,y,dx,dy):
    if x<0 or y<0 or x+dx>GX or y+dy>GY: return False
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            if occ[yy][xx]: return False
    return True

def place_int(x,y,dx,dy,icon,typ):
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            occ[yy][xx] = True
    items.append((x,y,dx,dy,icon,typ))
    placed[typ] += 1

def center_y_int(dy): return max(0,(GY-dy)//2)
def first_free_x_int():
    for xx in range(GX):
        if any(not occ[yy][xx] for yy in range(GY)): return xx
    return GX

def used_length_cm():
    if not items: return 0
    x_end = max(x+dx for (x,y,dx,dy,icon,typ) in items)
    return x_end * CALC_CELL_CM

# Layout-Funktionen wie in deiner Version (gekürzt hier für Übersicht)
# … (Hier würden alle Euro-/Industrie-/Mix-Funktionen analog zu v7 bleiben, nur mit *_int-Varianten)

# Beispiel Renderer
disp_cols = TRAILER_L // cell_cm_view
disp_rows = TRAILER_W // cell_cm_view
def map_cells(n_calc): return max(1, round(n_calc * CALC_CELL_CM / cell_cm_view))

html = f"""
<div style="display:grid; grid-template-columns: repeat({disp_cols}, {cell_px}px);
            grid-auto-rows:{cell_px}px; gap:1px; background:#ddd; padding:4px;
            border:2px solid #333; width:fit-content;">
"""
for (x,y,dx,dy,icon,typ) in items:
    gx, gy = map_cells(x), map_cells(y)
    gsx, gsy = map_cells(dx), map_cells(dy)
    html += f"""
    <div style="grid-column:{gx+1}/span {gsx}; grid-row:{gy+1}/span {gsy};
                background:url('{icon}') center/contain no-repeat, #fafafa;
                border:1px solid #777;"></div>
    """
html += "</div>"
st.components.v1.html(html, height=min(560, (cell_px+1)*disp_rows+40), scrolling=False)
