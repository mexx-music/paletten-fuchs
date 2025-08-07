import streamlit as st

st.set_page_config(page_title="🦊 PAL Fuchs 6 – Auto-Layouts (Unicode)", layout="centered")
st.title("🦊 PAL Fuchs 6 – Auto-Layouts (Unicode)")

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
PAL = {
    "Euro":       {"L":120, "B":80,  "sym_q":"▭",   "sym_l":"▮"},
    "Industrie":  {"L":120, "B":100, "sym_q":"⬜⬜", "sym_l":"⬜⬜"},  # doppelt breit
    "Blumenwagen":{"L":135, "B":55,  "sym_q":"▣",   "sym_l":"▣"},
}

# ---------- UI ----------
st.markdown("### 📥 Ladung")
col1,col2,col3,col4 = st.columns([1.2,1.2,1.2,1.6])
with col1:
    n_euro = st.number_input("Euro (120×80)", 0, 45, 30, key="n_euro")
with col2:
    n_ind  = st.number_input("Industrie (120×100)", 0, 45, 0, key="n_ind")
with col3:
    show_flowers = st.checkbox("Blumenwagen einblenden", value=False)
with col4:
    n_flow = st.number_input("Blumenwagen (135×55)", 0, 60, 0, key="n_flow", disabled=not show_flowers)

with st.expander("⚖️ Gewicht eingeben (optional)"):
    w_euro = st.number_input("kg/Euro", 0, 2000, 0)
    w_ind  = st.number_input("kg/Industrie", 0, 2000, 0)
    w_flow = st.number_input("kg/Blumenwagen", 0, 2000, 0)

# ---------- Helpers ----------
def size_cells(name, ori):
    L,B = PAL[name]["L"], PAL[name]["B"]
    if name == "Industrie":
        ori = "quer"
    if ori == "quer":
        depth = max(1, B // cm_per_cell)
        width = max(1, L // cm_per_cell)
        sym   = PAL[name]["sym_q"]
    else:
        depth = max(1, L // cm_per_cell)
        width = max(1, B // cm_per_cell)
        sym   = PAL[name]["sym_l"]
    return depth, width, sym

def blank_grid():
    return [[EM for _ in range(X)] for _ in range(Y)]

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

# ---------- Heck-Abschluss ----------
def fill_tail_closed(grid, x_start, n_left, d_l, w_l, s_l, d_q, w_q, s_q):
    if n_left <= 0: return
    if n_left % 3 == 0 or n_left < 2:
        cols_long = n_left // 3
        need_tail_quer = False
    else:
        cols_long = max(0, (n_left - 2) // 3)
        need_tail_quer = True
    lanes = [0, center_y(w_l), Y - 1]
    x = x_start
    for _ in range(cols_long):
        if x + d_l > X: break
        for y in lanes:
            stamp_symbol(grid, x, y, s_l)
        x += d_l
    if need_tail_quer and x + d_q <= X:
        stamp_symbol(grid, x, 0, s_q)
        stamp_symbol(grid, x, Y - 1, s_q)

# ---------- Varianten ----------
def variant_euro_30(n):
    grid = blank_grid()
    d_q, w_q, s_q = size_cells("Euro","quer")
    x = 0
    y = center_y(w_q)
    stamp_symbol(grid, x, y, s_q); x += d_q
    stamp_symbol(grid, x, 0,   s_q)
    stamp_symbol(grid, x, Y-1, s_q); x += d_q
    d_l, w_l, s_l = size_cells("Euro","längs")
    fill_tail_closed(grid, x, n - 3, d_l, w_l, s_l, d_q, w_q, s_q)
    return grid

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
    fill_tail_closed(grid, x, n, d_l, w_l, s_l, d_q, w_q, s_q)
    return grid

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

def variant_mix(n_euro, n_ind):
    grid = blank_grid()
    if n_ind>0:
        g_ind = variant_industrie(n_ind)
        for y in range(Y):
            for x in range(X):
                if g_ind[y][x] != EM:
                    grid[y][x] = g_ind[y][x]
    def first_free_x():
        for xx in range(X):
            if any(grid[y][xx] == EM for y in range(Y)):
                return xx
        return X
    start_x = first_free_x()
    g_e = blank_grid()
    d_q,w_q,s_q = size_cells("Euro","quer")
    d_l,w_l,s_l = size_cells("Euro","längs")
    front_q = min(3, n_euro) if n_euro >= 3 else n_euro
    x_front = 0
    if front_q >= 1:
        stamp_symbol(g_e, x_front, center_y(w_q), s_q); x_front += d_q
    if front_q >= 3:
        stamp_symbol(g_e, x_front, 0, s_q)
        stamp_symbol(g_e, x_front, Y-1, s_q); x_front += d_q
    rest = max(0, n_euro - front_q)
    fill_tail_closed(g_e, x_front, rest, d_l, w_l, s_l, d_q, w_q, s_q)
    for y in range(Y):
        for x in range(X):
            if g_e[y][x] != EM:
                xx = x + start_x
                if 0 <= xx < X and grid[y][xx] == EM:
                    grid[y][xx] = g_e[y][x]
    return grid

# ---------- Presets ----------
st.markdown("### ⚡ Presets")
b1, b2, b3, b4 = st.columns(4)
if b1.button("Euro 30"):
    st.session_state.n_euro, st.session_state.n_ind = 30, 0
    n_euro, n_ind = 30, 0
if b2.button("Euro 24 (schwer)"):
    st.session_state.n_euro, st.session_state.n_ind = 24, 0
    n_euro, n_ind = 24, 0
if b3.button("Industrie 26"):
    st.session_state.n_euro, st.session_state.n_ind = 0, 26
    n_euro, n_ind = 0, 26
if b4.button("Mix 21 Euro + 6 Industrie"):
    st.session_state.n_euro, st.session_state.n_ind = 21, 6
    n_euro, n_ind = 21, 6

# ---------- Ausgabe ----------
tabs = st.tabs(["Variante A", "Variante B", "Variante C"])
if n_euro >= 30 and n_ind == 0:
    gA = variant_euro_30(n_euro)
elif n_euro >= 24 and n_ind == 0:
    gA = variant_euro_24(n_euro)
elif n_ind > 0 and n_euro == 0:
    gA = variant_industrie(n_ind)
else:
    gA = variant_mix(n_euro, n_ind)
render(gA, "Ladeplan A")
