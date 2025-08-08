

import streamlit as st
from math import ceil

st.set_page_config(page_title="🦊 Paletten Fuchs 7 – Fixraster (inline icons)", layout="wide")
st.title("📦 Paletten Fuchs 7 – Sattelzug Ladeplan (Fixmaßstab, Inline‑Icons)")

TRAILER_L, TRAILER_W = 1360, 245  # cm

col1, col2 = st.columns(2)
with col1:
    preset = st.selectbox(
        "Preset",
        ["Euro 30", "Euro 24 (schwer)", "Industrie 26", "Mix 21 Euro + 6 Industrie", "– manuell –"],
        index=0
    )
with col2:
    cell_cm_view = st.slider("Anzeige‑Raster (cm/Zelle)", 10, 40, 20, 5)
    cell_px = st.slider("Zellpixel (Zoom)", 6, 18, 10, 1)

st.caption(f"Anzeige: {TRAILER_W//cell_cm_view} × {TRAILER_L//cell_cm_view} Zellen • 1 Zelle = {cell_cm_view} cm")

# Inline Icons (Data‑URIs)
ICON = {
    ("Euro","l"): "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHgAAABQCAYAAADSm7GJAAABGUlEQVR4nO3aMW0DQRRF0XFkCEvBIEJgERiEOaRObSJhFArLIanWCNZa6c451ZRfupruXdZ1/RtkfZx9AO913R9f99uZd3Cw75/fMYYfnCdwnMBxAscJHCdwnMBxAscJHCdwnMBxAscJHCdwnMBxAsdd9snOtm1n38KBlmUZY/jBeQLHvTZZz8fnmXdwMJusSQgcJ3CcwHECxwkcJ3CcwHECxwkcJ3CcwHECxwkcJ3CcwHE2WVE2WZMQOM4mK8omaxICxwkcJ3CcwHECxwkcJ3CcwHECxwkcJ3CcwHECxwkcJ3CcTVaUTdYkBI6zyYqyyZqEwHECxwkcJ3CcwHECxwkcJ3CcwHECxwkcJ3CcwHECx70mOzT5wXH/YOIfbZ3tnoQAAAAASUVORK5CYII=",
    ("Euro","q"): "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAAB4CAYAAABl7nX2AAABWklEQVR4nO3aQU0EQRRF0RqChLaACAy0AkTggTVrjOAIC+1hWM0IqFtJp5NzVrX8uanlu+37fh9Mezn7gKt7fTy+Pt7OvONyvn//xhh+YCZgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgdHuMi47jOPuWS9m2bYzhB2YCRs911s/n+5l3XI511iICRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRtZZk6yzFhEwss6aZJ21iICRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRddYk66xFBIyssyZZZy0iYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGAkYCRgJGD0HBcxxw+M/gHGJh+9RcWn2gAAAABJRU5ErkJggg==",
    ("Industrie","q"): "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHgAAABkCAYAAABNcPQyAAABP0lEQVR4nO3asQ3CQBQFwQNRgmtyJRRBREARRJToHiCCCows7c1EF35pddk7rev6HmSdjz6A/7p8H9fH9cg72Nnr/hpj+MF5AscJHCdwnMBxAscJHCdwnMBxAscJHCdwnMBxAscJHCdwnMBxAscJHCdwnMBxp+8uetu2o29hR8uyjDH84DyB437D99vzduQd7MzwfRICxwkcJ3CcwHECxwkcJ3CcwHECxwkcJ3CcwHECxwkcJ3CcwHECxwkcJ3CcwHGG71GG75MQOM7wPcrwfRICxwkcJ3CcwHECxwkcJ3CcwHECxwkcJ3CcwHECxwkcJ3CcwHECxwkcJ3CcwHGG71GG75MQOM7wPcrwfRICxwkcJ3CcwHECxwkcJ3CcwHECxwkcJ3CcwHECxwkcJ3CcwHECxwkcJ3DcbxdNkx8c9wHXDh+VLqpqhQAAAABJRU5ErkJggg==",
    ("Blume","l"): "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIcAAAA3CAYAAAAmLVl/AAAA4ElEQVR4nO3dMXHDQBRF0VUmEIRJOIwgIAIhCAzCsMQhqexGud5SKs6pVP7izjav0LJt2++Af3ycfQDX9fn8uH/dTzyDK7n93MYYXg7eEAdJHCRxkMRBEgdJHCRxkMRBWp7byr7vZ9/CRazrOsbwcvCGOEiv4e3x/TjzDi7E8MaUOEjiIImDJA6SOEjiIImDJA6SOEhWWQ6sskyJg2SV5cAqy5Q4SOIgiYMkDpI4SOIgiYMkDpI4SFZZDqyyTImDZJXlwCrLlDhI4iCJgyQOkjhI4iCJgyQO0uIHgBQvB+kPk24fOzTbfe8AAAAASUVORK5CYII=",
    ("Blume","q"): "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADcAAACHCAYAAACyEcEzAAAA90lEQVR4nO3dMY3DQBRF0XEUCMZkHEGwIAJhEQREYJnDpnIQeGWd0T2Vy3815Su8bNv2NyZ1u/qA/3Q/Pl4/rwvPONfj9zHGmPzlilMVpypOVZyqOFVxquJUxamKUxWnKk5VnKo4VXGq5djn9n2/+pbTrOs6xpj85aaO+46P7+f7yjtO1fioK05VnKo4VXGq4lTFqYpTFacqTlWcqjhVcariVMWpWlZVU8e1rKqKUxWnKk5VnKo4VXGq4lTFqYpTFacqTlWcqjhVcaqp41pWVVPHtayqilMVpypOVZyqOFVxquJUxamKUxWnKk5VnKo4VXGqpR9aoj7+Ix/bBWCG0gAAAABJRU5ErkJggg==",
}

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
    elif name == "Industrie": L,B = 120,100
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

def euro_30(n):
    reset_board()
    dq,wq = span_int("Euro","q"); x=0
    if n>0:
        y=center_y_int(wq)
        if free_int(x,y,dq,wq): place_int(x,y,dq,wq, ICON[("Euro","q")], "Euro"); n-=1
    x += dq
    for y in [0, GY-wq]:
        if n>0 and free_int(x,y,dq,wq): place_int(x,y,dq,wq, ICON[("Euro","q")], "Euro"); n-=1
    x += dq
    fill_tail_closed_euro(x, n)

def euro_24(n):
    reset_board()
    dq,wq = span_int("Euro","q");  x=0; yC = center_y_int(wq)
    for _ in range(min(2,n)):
        if free_int(x,yC,dq,wq): place_int(x,yC,dq,wq, ICON[("Euro","q")], "Euro"); n-=1; x+=dq
    for _ in range(2):
        if n<=0: break
        for y in [0, GY-wq]:
            if n>0 and free_int(x,y,dq,wq): place_int(x,y,dq,wq, ICON[("Euro","q")], "Euro"); n-=1
        x += dq
    if n>0 and free_int(x,yC,dq,wq): place_int(x,yC,dq,wq, ICON[("Euro","q")], "Euro"); n-=1; x+=dq
    fill_tail_closed_euro(x, n)

def euro_rows_from(x_start, n):
    dl,wl = span_int("Euro","l"); x = x_start
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

# Eingabe
st.subheader("📥 Eingabe")
c1,c2,c3,c4 = st.columns([1.3,1.3,1.2,1.6])
with c1: n_euro = st.number_input("Euro‑Paletten (120×80)", 0, 45, 0)
with c2: n_ind  = st.number_input("Industrie‑Paletten (120×100)", 0, 45, 0)
with c3: flowers = st.checkbox("🌼 Blumenwagen anzeigen", value=False)
with c4: n_flow = st.number_input("Blumenwagen (135×55)", 0, 60, 0, disabled=not flowers)

# Preset / Auto
if preset == "Euro 30":
    euro_30(30)
elif preset == "Euro 24 (schwer)":
    euro_24(24)
elif preset == "Industrie 26":
    reset_board(); industrie_all(26)
elif preset == "Mix 21 Euro + 6 Industrie":
    mix_21_6()
else:
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

# Blumen (optional)
if flowers and n_flow>0:
    dq,wq = span_int("Blume","q")
    dl,wl = span_int("Blume","l")
    x=0
    for i in range(min(3,n_flow)):
        y=[0, center_y_int(wq), GY-wq][i if i<3 else 2]
        if free_int(x,y,dq,wq): place_int(x,y,dq,wq, ICON[("Blume","q")], "Blume")
    left=max(0,n_flow-3); x+=dq
    if left>0 and free_int(x,0,dl,wl): place_int(x,0,dl,wl, ICON[("Blume","l")], "Blume"); left-=1
    if left>0 and free_int(x,GY-wl,dl,wl): place_int(x,GY-wl,dl,wl, ICON[("Blume","l")], "Blume")

# Render
st.subheader("🗺️ Ladeplan (Draufsicht, hinten = unten)")
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

# Kapazitätsprüfung
used_cm = used_length_cm()
st.markdown(f"**Genutzte Länge (real):** {used_cm} cm von {TRAILER_L} cm  (≈ {used_cm/TRAILER_L:.0%})")
if used_cm > TRAILER_L:
    st.error("🚫 **Platz reicht nicht (Länge):** Reale Nutzlänge überschreitet 13,6 m.")
