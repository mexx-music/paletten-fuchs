import streamlit as st

st.set_page_config(page_title="🦊 PAL Fuchs 6 – Bilder (v2)", layout="wide")
st.title("🦊 PAL Fuchs 6 – Draufsicht mit Icons (v2)")

# ---------- Trailer & Grid ----------
TRAILER_L, TRAILER_W = 1360, 245  # cm
# Defaults as requested: Raster 25 cm, Pixel 4
cell_cm = st.sidebar.slider("Raster (cm/Zelle)", 5, 40, 25, 5)
X, Y = TRAILER_L // cell_cm, TRAILER_W // cell_cm

# Zoom klein halten, damit kein Scrollen nötig ist
cell_px = st.sidebar.slider("Zellpixel (Zoom)", 4, 14, 4, 1)

# ---------- Icons ----------
ICON = {
    ("Euro","l"): "icons/euro_l.png",
    ("Euro","q"): "icons/euro_q.png",
    ("Industrie","q"): "icons/ind_q.png",
    ("Blume","l"): "icons/flower_l.png",
    ("Blume","q"): "icons/flower_q.png",
}

# ---------- cm → Grid-Span ----------
def span(name, ori):
    if name == "Euro":        L,B = 120, 80
    elif name == "Industrie": L,B = 120,100
    else:                     L,B = 135, 55  # Blume
    if name == "Industrie":
        ori = "q"  # Regel
    if ori == "q":   depth_cm, width_cm = B, L
    else:            depth_cm, width_cm = L, B
    dx = max(1, depth_cm // cell_cm)   # entlang Trailer-Länge (x)
    dy = max(1, width_cm // cell_cm)   # quer im Trailer (y)
    return dx, dy

# ---------- Belegung & Zähler ----------
occupied = [[False]*X for _ in range(Y)]
items = []  # (x,y,dx,dy,icon,typ)
placed = {"Euro":0, "Industrie":0, "Blume":0}

def reset_board():
    global occupied, items, placed
    occupied = [[False]*X for _ in range(Y)]
    items.clear()
    placed = {"Euro":0, "Industrie":0, "Blume":0}

def free(x,y,dx,dy):
    if x<0 or y<0 or x+dx>X or y+dy>Y: return False
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            if occupied[yy][xx]: return False
    return True

def place(x,y,dx,dy,icon,typ):
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            occupied[yy][xx] = True
    items.append((x,y,dx,dy,icon,typ))
    placed[typ] += 1

def center_y(dy): return max(0,(Y-dy)//2)
def first_free_x():
    for xx in range(X):
        if any(not occupied[yy][xx] for yy in range(Y)): return xx
    return X

def used_length_cm():
    if not items: return 0
    x_end = max(x+dx for (x,y,dx,dy,icon,typ) in items)
    return x_end * cell_cm

# ---------- Heck-Abschluss-Logik (Euro) ----------
def fill_tail_closed_euro(x_start, euro_left):
    """Füllt ab x_start: bevorzugt 3er-Reihen längs; falls Rest!=0 -> 2× quer Abschluss."""
    if euro_left <= 0: return
    dq,wq = span("Euro","q")
    dl,wl = span("Euro","l")
    # Reserve ggf. 2 für Querabschluss
    if euro_left % 3 == 0 or euro_left < 2:
        cols_long = euro_left // 3
        need_tail_q = False
    else:
        cols_long = max(0, (euro_left - 2)//3)
        need_tail_q = True

    lanes = [0, center_y(wl), Y-wl]
    x = x_start
    # 3er Längsreihen
    for _ in range(cols_long):
        if x+dl > X: break
        for y in lanes:
            if free(x,y,dl,wl):
                place(x,y,dl,wl, ICON[("Euro","l")], "Euro")
        x += dl
    # 2× Querabschluss
    if need_tail_q and x+dq <= X:
        if free(x,0,dq,wq): place(x,0,dq,wq, ICON[("Euro","q")], "Euro")
        if free(x,Y-wq,dq,wq): place(x,Y-wq,dq,wq, ICON[("Euro","q")], "Euro")

# ---------- Layouts ----------
def euro_30(n):
    reset_board()
    dq,wq = span("Euro","q");  dl,wl = span("Euro","l")
    x=0
    # 1 quer mittig
    if n>0:
        y=center_y(wq)
        if free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Euro","q")], "Euro"); n-=1
    x += dq
    # 2 quer links+rechts
    for y in [0, Y-wq]:
        if n>0 and free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Euro","q")], "Euro"); n-=1
    x += dq
    # Rest mit geschlossenem Heck
    fill_tail_closed_euro(x, n)

def euro_24(n):
    reset_board()
    dq,wq = span("Euro","q");  dl,wl = span("Euro","l")
    x=0; yC = center_y(wq)
    # 2× einzeln quer mittig
    for _ in range(min(2,n)):
        if free(x,yC,dq,wq): place(x,yC,dq,wq, ICON[("Euro","q")], "Euro"); n-=1; x+=dq
    # 2× doppelt quer (links+rechts)
    for _ in range(2):
        if n<=0: break
        for y in [0, Y-wq]:
            if n>0 and free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Euro","q")], "Euro"); n-=1
        x += dq
    # 1× einzel quer mittig
    if n>0 and free(x,yC,dq,wq): place(x,yC,dq,wq, ICON[("Euro","q")], "Euro"); n-=1; x+=dq
    # Rest: geschlossen
    fill_tail_closed_euro(x, n)

def industrie_all(n):
    dq,wq = span("Industrie","q")
    x=0
    # ungerade → 1 mittig
    if n%2==1:
        y=center_y(wq)
        if free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Industrie","q")], "Industrie"); n-=1; x+=dq
    # Paare links+rechts
    while n>0 and x+dq<=X:
        for y in [0, Y-wq]:
            if n>0 and free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Industrie","q")], "Industrie"); n-=1
        x += dq

def euro_rows_from(x_start, n):
    dl,wl = span("Euro","l")
    x = x_start
    lanes=[0, center_y(wl), Y-wl]
    while n>0 and x+dl<=X:
        for y in lanes:
            if n>0 and free(x,y,dl,wl):
                place(x,y,dl,wl, ICON[("Euro","l")], "Euro"); n-=1
        x+=dl

def mix_21_6():
    reset_board()
    # Industrie zuerst
    industrie_all(6)
    # Euro ab erster freier Spalte (mit geschlossenem Heck)
    start = first_free_x()
    dq,wq = span("Euro","q")
    x = start
    rem = 21
    # 1 quer mittig
    if rem>0 and x+dq<=X and free(x,center_y(wq),dq,wq):
        place(x, center_y(wq), dq, wq, ICON[("Euro","q")], "Euro"); rem -= 1
        x += dq
    # 2 quer außen
    if rem >= 2 and x+dq<=X:
        for y in [0, Y-wq]:
            if rem>0 and free(x,y,dq,wq):
                place(x,y,dq,wq, ICON[("Euro","q")], "Euro"); rem -= 1
        x += dq
    # Rest geschlossen
    fill_tail_closed_euro(x, rem)

# ---------- UI ----------
st.markdown("### ⚡ Presets")
b1,b2,b3,b4 = st.columns(4)
if b1.button("Euro 30"):                 euro_30(30)
if b2.button("Euro 24 (schwer)"):        euro_24(24)
if b3.button("Industrie 26"):            reset_board(); industrie_all(26)
if b4.button("Mix 21 Euro + 6 Industrie"): mix_21_6()

st.markdown("### 📥 Manuelle Menge")
c1,c2,c3,c4 = st.columns([1.2,1.2,1.2,1.6])
with c1: n_euro = st.number_input("Euro (120×80)", 0, 45, 30)
with c2: n_ind  = st.number_input("Industrie (120×100)", 0, 45, 0)
with c3: flowers = st.checkbox("Blumenwagen", value=False)
with c4: n_flow = st.number_input("Blumenwagen (135×55)", 0, 60, 0, disabled=not flowers)

# Falls kein Preset gedrückt → simple Auto-Logik
if not items:
    reset_board()
    if n_ind>0 and n_euro>0:
        industrie_all(n_ind)
        start = first_free_x()
        dq,wq = span("Euro","q")
        x=start
        rem=n_euro
        # 1 quer mittig
        if rem>0 and x+dq<=X and free(x,center_y(wq),dq,wq):
            place(x,center_y(wq),dq,wq, ICON[("Euro","q")], "Euro"); rem-=1; x+=dq
        # 2 quer außen
        if rem>=2 and x+dq<=X:
            for y in [0, Y-wq]:
                if rem>0 and free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Euro","q")], "Euro"); rem-=1
            x+=dq
        # Rest geschlossen
        fill_tail_closed_euro(x, rem)
    elif n_euro>=30:
        euro_30(n_euro)
    elif n_euro>=24:
        euro_24(n_euro)
    elif n_euro>0:
        euro_rows_from(0, n_euro)
    elif n_ind>0:
        industrie_all(n_ind)

# Blumen (optional Demo 3 quer + 2 längs vorne)
if flowers and n_flow>0:
    dq,wq = span("Blume","q")
    dl,wl = span("Blume","l")
    x=0
    for i in range(min(3,n_flow)):
        y=[0, center_y(wq), Y-wq][i if i<3 else 2]
        if free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Blume","q")], "Blume")
    left=max(0,n_flow-3); x+=dq
    if left>0 and free(x,0,dl,wl): place(x,0,dl,wl, ICON[("Blume","l")], "Blume"); left-=1
    if left>0 and free(x,Y-wl,dl,wl): place(x,Y-wl,dl,wl, ICON[("Blume","l")], "Blume")

# ---------- Render ----------
html = f"""
<div style="
  display:grid;
  grid-template-columns: repeat({X}, {cell_px}px);
  grid-auto-rows: {cell_px}px;
  gap: 1px;
  background:#ddd; padding:4px; border:2px solid #333; width:fit-content;">
"""
for (x,y,dx,dy,icon,typ) in items:
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

# ---------- Kapazitätsprüfung & Nutzlänge ----------
wanted = {"Euro": n_euro, "Industrie": n_ind}
missing_msgs = []
for typ in ["Euro","Industrie"]:
    if wanted[typ] > 0 and placed[typ] < wanted[typ]:
        missing = wanted[typ] - placed[typ]
        missing_msgs.append(f"– {missing}× {typ} passt/passen nicht mehr")

used_cm = used_length_cm()
st.markdown(f"**Genutzte Länge:** {used_cm} cm von {TRAILER_L} cm  (≈ {used_cm/TRAILER_L:.0%})")

if missing_msgs:
    st.error("🚫 **Platz reicht nicht:**\n" + "\\n".join(missing_msgs))
else:
    st.success("✅ **Alle angeforderten Paletten passen in den Laderaum.**")
