import streamlit as st

st.set_page_config(page_title="Paletten Fuchs – Bilder", layout="wide")
st.title("🦊 Paletten Fuchs – Draufsicht mit Icons")

# Trailer / Raster
TRAILER_L, TRAILER_W = 1360, 245  # cm
cell = st.sidebar.slider("Raster (cm/Zelle)", 5, 40, 10, 5)  # Auflösung
X, Y = TRAILER_L // cell, TRAILER_W // cell                  # Grid-Spalten/-Zeilen

# Pfade zu Icons (einfach im Repo ablegen: /icons/…)
ICON = {
    ("Euro","l"): "icons/euro_l.png",   # 120x80
    ("Euro","q"): "icons/euro_q.png",   # 80x120
    ("Industrie","q"): "icons/ind_q.png", # 100x120 (Industrie immer quer)
    ("Blumen","l"): "icons/flower_l.png",# 135x55
    ("Blumen","q"): "icons/flower_q.png"
}

# cm -> Grid-Span
def span_cm(length_cm, width_cm, ori, typ):
    # Industrie immer quer
    if typ == "Industrie": ori = "q"
    if typ == "Euro":
        L, B = 120, 80
    elif typ == "Industrie":
        L, B = 120, 100
    else:
        L, B = 135, 55
    if ori == "q":  # quer: Tiefe = Breite(cm), Breite = Länge(cm)
        depth_cm, width_cm = B, L
    else:          # längs: Tiefe = Länge(cm), Breite = Breite(cm)
        depth_cm, width_cm = L, B
    return max(1, depth_cm // cell), max(1, width_cm // cell)

# Einfache Platzierungshilfen
occupied = [[False]*X for _ in range(Y)]
items = []  # (x, y, dx, dy, icon)

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

# --- Beispiel: Euro 30 Schema ---
def euro_30():
    dq, wq = span_cm(120,80,"q","Euro")  # ergibt Tiefe=80, Breite=120 → Spans
    dl, wl = span_cm(120,80,"l","Euro")  # ergibt Tiefe=120, Breite=80
    x=0
    # 1 quer mittig
    y = center_y(wq); 
    if free(x,y,dq,wq): place(x,y,dq,wq, ICON[("Euro","q")])
    x += dq
    # 2 quer links+rechts
    if free(x,0,dq,wq): place(x,0,dq,wq, ICON[("Euro","q")])
    if free(x,Y-wq,dq,wq): place(x,Y-wq,dq,wq, ICON[("Euro","q")])
    x += dq
    # Rest: 3er-Reihen längs
    lanes = [0, center_y(wl), Y-wl]
    while x+dl <= X:
        for y in lanes:
            if free(x,y,dl,wl):
                place(x,y,dl,wl, ICON[("Euro","l")])
        x += dl

# --- Render CSS Grid ---
def render():
    cell_px = 10  # visuelle Zellgröße
    html = f"""
    <div style="
      display:grid;
      grid-template-columns: repeat({X}, {cell_px}px);
      grid-auto-rows: {cell_px}px;
      gap: 1px;
      background:#ddd; padding:4px; border:2px solid #333; width: fit-content;">
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
    st.components.v1.html(html, height=min(800, (cell_px+1)*Y + 40), scrolling=True)

# Demo laufen lassen
st.subheader("Demo: Euro 30 (1 quer, 2 quer, Rest 3er-Reihen längs)")
euro_30()
render()
