import streamlit as st

st.set_page_config(page_title="🦊 Paletten Fuchs – Icons (kompakt)", layout="wide")
st.title("🦊 Paletten Fuchs – Draufsicht mit Icons (kompakt)")

# ---------- Trailer & Raster ----------
TRAILER_L, TRAILER_W = 1360, 245  # cm
cell_cm = st.sidebar.slider("Raster (cm/Zelle)", 5, 40, 10, 5)
X, Y = TRAILER_L // cell_cm, TRAILER_W // cell_cm

# 👇 NEU: Zoom – kleinere Kacheln, damit kein Scrollen nötig ist
cell_px = st.sidebar.slider("Zellpixel (Zoom)", 4, 14, 5, 1)

# ---------- Icons (relativ zum App-Root /icons) ----------
ICON = {
    ("Euro","l"): "icons/euro_l.png",     # 120x80
    ("Euro","q"): "icons/euro_q.png",     # 80x120
    ("Industrie","q"): "icons/ind_q.png", # 100x120 (Industrie immer quer)
    ("Blumen","l"): "icons/flower_l.png", # 135x55
    ("Blumen","q"): "icons/flower_q.png",
}

# ---------- cm → Grid-Span ----------
def span(name, ori):
    if name == "Euro":       L,B = 120, 80
    elif name == "Industrie":L,B = 120,100
    else:                    L,B = 135, 55  # Blumen
    if name == "Industrie":  ori = "q"      # Regel
    if ori == "q":   depth_cm, width_cm = B, L
    else:            depth_cm, width_cm = L, B
    dx = max(1, depth_cm // cell_cm)   # entlang Länge (x)
    dy = max(1, width_cm // cell_cm)   # quer (y)
    return dx, dy

# ---------- Platzierungs-Helpers ----------
occupied = [[False]*X for _ in range(Y)]
items = []  # (x,y,dx,dy,icon)

def free(x,y,dx,dy):
    if x<0 or y<0 or x+dx>X or y+dy>Y: return False
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            if occupied[yy][xx]: return False
    return True

def place(x,y,dx,dy,icon):
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            occupied[yy][xx] = True
    items.append((x,y,dx,dy,icon))

def center_y(dy): return max(0,(Y-dy)//2)
def first_free_x():
    for xx in range(X):
        if any(not occupied[yy][xx] for yy in range(Y)): return xx
    return X

# ---------- Layouts ----------
def euro_30(n):
    dq,wq = span("Euro","q");  dl,wl = span("Euro","l")
    x=0
    # 1 quer mittig
    if n>0:
        y=center_y(wq)
        if free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Euro","q")]); n-=1
    x+=dq
    # 2 quer links + rechts
    for y in [0, Y-wq]:
        if n>0 and free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Euro","q")]); n-=1
    x+=dq
    # Rest längs in 3 Spuren
    lanes=[0, center_y(wl), Y-wl]
    while n>0 and x+dl<=X:
        for y in lanes:
            if n>0 and free(x,y,dl,wl):
                place(x,y,dl,wl, ICON[("Euro","l")]); n-=1
        x+=dl

def euro_24(n):
    dq,wq = span("Euro","q");  dl,wl = span("Euro","l")
    x=0; yC = center_y(wq)
    # 2× einzeln quer mittig
    for _ in range(min(2,n)):
        if free(x,yC,dq,wq): place(x,yC,dq,wq, ICON[("Euro","q")]); n-=1; x+=dq
    # 2× doppelt quer (links & rechts)
    for _ in range(2):
        if n<=0: break
        for y in [0, Y-wq]:
            if n>0 and free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Euro","q")]); n-=1
        x+=dq
    # 1× einzel quer mittig
    if n>0 and free(x,yC,dq,wq): place(x,yC,dq,wq, ICON[("Euro","q")]); n-=1; x+=dq
    # Rest längs
    lanes=[0, center_y(wl), Y-wl]
    while n>0 and x+dl<=X:
        for y in lanes:
            if n>0 and free(x,y,dl,wl): place(x,y,dl,wl, ICON[("Euro","l")]); n-=1
        x+=dl

def industrie_all(n):
    dq,wq = span("Industrie","q")
    x=0
    if n%2==1:  # ungerade → 1 mittig
        y=center_y(wq)
        if free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Industrie","q")]); n-=1; x+=dq
    while n>0 and x+dq<=X:
        for y in [0, Y-wq]:
            if n>0 and free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Industrie","q")]); n-=1
        x+=dq

def euro_rows_from(x_start, n):
    dl,wl = span("Euro","l")
    x = x_start
    lanes=[0, center_y(wl), Y-wl]
    while n>0 and x+dl<=X:
        for y in lanes:
            if n>0 and free(x,y,dl,wl): place(x,y,dl,wl, ICON[("Euro","l")]); n-=1
        x+=dl

def mix_21_6():
    # Industrie zuerst
    industrie_all(6)
    # Euro dahinter (Startspalte suchen)
    start = first_free_x()
    # Schema für 21 Euro: wie 24 – 3 → also 1 quer, 2 quer, Rest 3er längs
    # Einfach per Euro-30-Logik und weniger Stück:
    remaining = 21
    dq,wq = span("Euro","q");  dl,wl = span("Euro","l")
    x = start
    # 1 quer mittig
    if remaining>0 and x+dq<=X:
        y=center_y(wq); 
        if free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Euro","q")]); remaining-=1
    x+=dq
    # 2 quer außen
    for y in [0, Y-wq]:
        if remaining>0 and x+dq<=X and free(x,y,dq,wq):
            place(x,y,dq,wq, ICON[("Euro","q")]); remaining-=1
    x+=dq
    # Rest längs in 3 Spuren
    lanes=[0, center_y(wl), Y-wl]
    while remaining>0 and x+dl<=X:
        for y in lanes:
            if remaining>0 and free(x,y,dl,wl):
                place(x,y,dl,wl, ICON[("Euro","l")]); remaining-=1
        x+=dl

# ---------- UI ----------
st.markdown("### 📥 Ladung")
c1,c2,c3,c4 = st.columns([1.2,1.2,1.2,1.6])
with c1:
    n_euro = st.number_input("Euro (120×80)", 0, 45, 30)
with c2:
    n_ind  = st.number_input("Industrie (120×100)", 0, 40, 0)
with c3:
    flowers = st.checkbox("Blumenwagen", value=False)
with c4:
    n_flow = st.number_input("Blumenwagen (135×55)", 0, 60, 0, disabled=not flowers)

st.markdown("### ⚡ Presets")
b1,b2,b3 = st.columns(3)
if b1.button("Euro 30"):
    occupied[:] = [[False]*X for _ in range(Y)]; items.clear(); euro_30(30)
if b2.button("Euro 24 (schwer)"):
    occupied[:] = [[False]*X for _ in range(Y)]; items.clear(); euro_24(24)
if b3.button("Mix 21 Euro + 6 Industrie"):
    occupied[:] = [[False]*X for _ in range(Y)]; items.clear(); mix_21_6()

# Falls kein Preset gedrückt wurde → generiere aus Eingaben (einfach)
if not items:
    if n_ind>0 and n_euro>0:
        industrie_all(n_ind); start = first_free_x(); euro_rows_from(start, n_euro)
    elif n_euro>=30:
        euro_30(n_euro)
    elif n_euro>=24:
        euro_24(n_euro)
    elif n_euro>0:
        euro_rows_from(0, n_euro)
    elif n_ind>0:
        industrie_all(n_ind)

# ---------- Render ohne Scroll ----------
html = f"""
<div style="
  display:grid;
  grid-template-columns: repeat({X}, {cell_px}px);
  grid-auto-rows: {cell_px}px;
  gap: 1px;
  background:#ddd; padding:4px; border:2px solid #333; width:fit-content;">
"""
for (x,y,dx,dy,icon) in items:
    html += f"""
    <div style="
      grid-column:{x+1}/span {dx};
      grid-row:{y+1}/span {dy};
      background: url('{icon}') center/contain no-repeat, #fafafa;
      border:1px solid #777;"></div>
    """
html += "</div>"

# Höhe so klein wie möglich halten (kein Scrollen)
height = min(520, (cell_px+1)*Y + 30)
st.components.v1.html(html, height=height, scrolling=False)
