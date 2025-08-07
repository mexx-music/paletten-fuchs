import streamlit as st

st.set_page_config(page_title="🦊 Paletten Fuchs – Auto‑Layouts (Unicode)", layout="centered")
st.title("🦊 Paletten Fuchs – Auto‑Layouts (Unicode)")

# ---------- Trailer & Raster ----------
TRAILER_L = 1360  # cm
TRAILER_W = 245   # cm
cm_per_cell = st.sidebar.slider("Raster (cm/Zelle)", 10, 60, 20, 5)
X = TRAILER_L // cm_per_cell  # Länge in Zellen
Y = TRAILER_W // cm_per_cell  # Breite in Zellen

# Kompaktere Darstellung
EM = " "  # U+2009 THIN SPACE – schmaler als EM-space
font_px = st.sidebar.slider("Text-Zoom", 12, 28, 18, 1)

st.caption(f"Raster: {X} × {Y} Zellen (je {cm_per_cell} cm)")

# ---------- Paletten ----------
# Industrie bekommt ein Doppelsymbol -> wirkt sichtbar breiter
PAL = {
    "Euro":       {"L":120, "B":80,  "sym_q":"▭",   "sym_l":"▮"},
    "Industrie":  {"L":120, "B":100, "sym_q":"⬜⬜", "sym_l":"⬜⬜"},  # immer quer, doppelt breit
    "Blumenwagen":{"L":135, "B":55,  "sym_q":"▣",   "sym_l":"▣"},
}

# ---------- UI: nur Paletten-Art + Anzahl ----------
st.markdown("### 📥 Ladung")
col1,col2,col3,col4 = st.columns([1.2,1.2,1.2,1.6])
with col1:
    n_euro = st.number_input("Euro (120×80)", 0, 40, 30)
with col2:
    n_ind  = st.number_input("Industrie (120×100)", 0, 40, 0)
with col3:
    show_flowers = st.checkbox("Blumenwagen einblenden", value=False)
with col4:
    n_flow = st.number_input("Blumenwagen (135×55)", 0, 60, 0, disabled=not show_flowers)

# Gewicht optional (ausgeblendet standard)
with st.expander("⚖️ Gewicht eingeben (optional)"):
    w_euro = st.number_input("kg/Euro", 0, 2000, 0)
    w_ind  = st.number_input("kg/Industrie", 0, 2000, 0)
    w_flow = st.number_input("kg/Blumenwagen", 0, 2000, 0)

# ---------- Helpers ----------
def size_cells(name, ori):
    L,B = PAL[name]["L"], PAL[name]["B"]
    if name == "Industrie":  # Regel: immer quer
        ori = "quer"
    if ori == "quer":
        depth = max(1, B // cm_per_cell)   # Tiefe entlang Trailer-Länge
        width = max(1, L // cm_per_cell)   # Breite quer im Trailer
        sym   = PAL[name]["sym_q"]
    else:  # längs
        depth = max(1, L // cm_per_cell)
        width = max(1, B // cm_per_cell)
        sym   = PAL[name]["sym_l"]
    return depth, width, sym

def blank_grid():
    return [[EM for _ in range(X)] for _ in range(Y)]

# ⬇️ Mehrzelliges Stempeln: setzt jedes Zeichen des Symbols in eine Zelle
def stamp_symbol(grid, x, y, sym):
    if 0 <= y < Y:
        for i, ch in enumerate(sym):
            xx = x + i
            if 0 <= xx < X:
                grid[y][xx] = ch

def center_y(width_cells):
    return max(0, (Y - width_cells)//2)

def render(grid, title):
    st.markdown(f"#### {title}")
    for row in grid:
        st.markdown(
            f"<pre style='font-size:{font_px}px; line-height:100%; margin:0'>{''.join(row)}</pre>",
            unsafe_allow_html=True
        )

# ---------- Varianten-Generatoren ----------
# V1: Euro-30 (1 quer mittig, 2 quer links/rechts, Rest 3er-Reihen längs)
def variant_euro_30(n):
    grid = blank_grid()
    d_q, w_q, s_q = size_cells("Euro","quer")
    x = 0
    y = center_y(w_q)
    stamp_symbol(grid, x, y, s_q); x += d_q
    stamp_symbol(grid, x, 0,   s_q)
    stamp_symbol(grid, x, Y-1, s_q); x += d_q
    d_l, w_l, s_l = size_cells("Euro","längs")
    rows_needed = max(0, (n - 3) // 3)
    yL, yM, yR = 0, center_y(w_l), Y-1
    for r in range(rows_needed):
        xr = x + r*d_l
        if xr + d_l >= X: break
        stamp_symbol(grid, xr, yL, s_l)
        stamp_symbol(grid, xr, yM, s_l)
        stamp_symbol(grid, xr, yR, s_l)
    return grid

# V2: Euro-24 (schwer) – 2× einzeln quer, 2× doppelt quer, 1× quer, Rest längs
def variant_euro_24(n):
    grid = blank_grid()
    d_q,w_q,s_q = size_cells("Euro","quer")
    d_l,w_l,s_l = size_cells("Euro","längs")
    x=0; yC = center_y(w_q)
    if n<=0: return grid
    stamp_symbol(grid,x,yC,s_q); x+=d_q; n-=1
    if n<=0: return grid
    stamp_symbol(grid,x,yC,s_q); x+=d_q; n-=1
    if n<=0: return grid
    stamp_symbol(grid,x,0,s_q)
    if n>1: stamp_symbol(grid,x,Y-1,s_q); n-=2; x+=d_q
    else:   n-=1; x+=d_q
    if n>0: stamp_symbol(grid,x,yC,s_q); x+=d_q; n-=1
    yL, yM, yR = 0, center_y(w_l), Y-1
    while n>0 and x < X:
        if n>0: stamp_symbol(grid,x,yL,s_l); n-=1
        if n>0: stamp_symbol(grid,x,yM,s_l); n-=1
        if n>0: stamp_symbol(grid,x,yR,s_l); n-=1
        x+=d_l
    return grid

# V3: Industrie – immer quer; ungerade → 1 vorn mittig
def variant_industrie(n):
    grid = blank_grid()
    d_q,w_q,s_q = size_cells("Industrie","quer")
    x=0
    if n%2==1:
        stamp_symbol(grid,x,center_y(w_q),s_q); x+=d_q; n-=1
    while n>0 and x < X:
        stamp_symbol(grid,x,0,s_q)
        if n>1: stamp_symbol(grid,x,Y-1,s_q); n-=2; x+=d_q
        else:   n-=1; x+=d_q
    return grid

# Blumenwagen: 3 quer, 2 längs (Demo)
def place_flowers(grid, n):
    if n<=0: return
    d_q,w_q,s_q = size_cells("Blumenwagen","quer")
    d_l,w_l,s_l = size_cells("Blumenwagen","längs")
    x=0
    for i in range(min(3,n)):
        y = int((i/(3-1))*(Y-1)) if Y
