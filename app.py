import streamlit as st

st.set_page_config(page_title="🦊 Paletten Fuchs – Auto‑Layouts (Unicode)", layout="centered")
st.title("🦊 Paletten Fuchs – Auto‑Layouts (Unicode)")

# ---------- Trailer & Raster ----------
TRAILER_L = 1360  # cm
TRAILER_W = 245   # cm
cm_per_cell = st.sidebar.slider("Raster (cm/Zelle)", 10, 60, 20, 5)
X = TRAILER_L // cm_per_cell  # Länge in Zellen
Y = TRAILER_W // cm_per_cell  # Breite in Zellen
EM = " "  # \u2003 em-space

st.caption(f"Raster: {X} × {Y} Zellen (je {cm_per_cell} cm)")

# ---------- Paletten ----------
PAL = {
    "Euro":       {"L":120, "B":80,  "sym_q":"▭", "sym_l":"▮"},
    "Industrie":  {"L":120, "B":100, "sym_q":"⬜", "sym_l":"⬜"},  # immer quer
    "Blumenwagen":{"L":135, "B":55,  "sym_q":"▣", "sym_l":"▣"},
}

def size_cells(name, ori):
    L,B = PAL[name]["L"], PAL[name]["B"]
    if name == "Industrie":
        ori = "quer"
    if ori == "quer":
        depth = max(1, B // cm_per_cell)   # Tiefe entlang Trailer-Länge
        width = max(1, L // cm_per_cell)   # Breite quer im Trailer
        sym   = PAL[name]["sym_q"]
    else:
        depth = max(1, L // cm_per_cell)
        width = max(1, B // cm_per_cell)
        sym   = PAL[name]["sym_l"]
    return depth, width, sym

def blank_grid(): return [[EM for _ in range(X)] for _ in range(Y)]
def stamp(grid, x, y, sym):
    if 0 <= x < X and 0 <= y < Y: grid[y][x] = sym
def center_y(width_cells): return max(0, (Y - width_cells)//2)

def render(grid, title):
    st.markdown(f"#### {title}")
    for row in grid:
        st.markdown(f"<pre style='font-size:22px;line-height:100%;margin:0'>{''.join(row)}</pre>", unsafe_allow_html=True)

# ---------- Varianten mit x-Start ----------
def variant_euro_30(n, x0=0):
    g = blank_grid()
    d_q, w_q, s_q = size_cells("Euro","quer")
    d_l, w_l, s_l = size_cells("Euro","längs")
    x = x0
    # 1 quer mittig
    y = center_y(w_q)
    if x + d_q <= X: stamp(g, x, y, s_q); x += d_q; n -= 1
    # 2 quer links/rechts
    if n > 0 and x + d_q <= X:
        stamp(g, x, 0,   s_q); n -= 1
        if n > 0: stamp(g, x, Y-1, s_q); n -= 1
        x += d_q
    # Rest 3er-Reihen längs
    lanes = [0, center_y(w_l), Y-1]
    while n > 0 and x + d_l <= X:
        for y in lanes:
            if n > 0: stamp(g, x, y, s_l); n -= 1
        x += d_l
    return g

def variant_euro_24(n, x0=0):
    g = blank_grid()
    d_q,w_q,s_q = size_cells("Euro","quer")
    d_l,w_l,s_l = size_cells("Euro","längs")
    x = x0
    yC = center_y(w_q)
    # 2× einzeln quer mittig hintereinander
    for _ in range(min(2, n)):
        if x + d_q <= X: stamp(g, x, yC, s_q); x += d_q; n -= 1
    # 2× doppelt quer (links+rechts)
    for _ in range(2):
        if n <= 0 or x + d_q > X: break
        stamp(g, x, 0, s_q); n -= 1
        if n > 0: stamp(g, x, Y-1, s_q); n -= 1
        x += d_q
    # 1× quer mittig
    if n > 0 and x + d_q <= X:
        stamp(g, x, yC, s_q); x += d_q; n -= 1
    # Rest längs 3-spurig
    lanes = [0, center_y(w_l), Y-1]
    while n > 0 and x + d_l <= X:
        for y in lanes:
            if n > 0: stamp(g, x, y, s_l); n -= 1
        x += d_l
    return g

def variant_industrie(n, x0=0):
    g = blank_grid()
    d_q,w_q,s_q = size_cells("Industrie","quer")
    x = x0
    # ungerade → 1 vorn mittig
    if n % 2 == 1 and x + d_q <= X:
        stamp(g, x, center_y(w_q), s_q)
        x += d_q; n -= 1
    while n > 0 and x + d_q <= X:
        stamp(g, x, 0,   s_q); n -= 1
        if n > 0: stamp(g, x, Y-1, s_q); n -= 1
        x += d_q
    return g

def merge_at_offset(dst, src, offx):
    for y in range(Y):
        for x in range(X):
            if src[y][x] != EM:
                xx = x + offx
                if 0 <= xx < X and dst[y][xx] == EM:
                    dst[y][xx] = src[y][x]

def first_free_x(grid):
    for xx in range(X):
        if any(grid[y][xx] == EM for y in range(Y)):
            return xx
    return X

def variant_mix(n_euro, n_ind):
    grid = blank_grid()
    # 1) Industrie vorne
    g_ind = variant_industrie(n_ind, x0=0) if n_ind > 0 else blank_grid()
    merge_at_offset(grid, g_ind, 0)
    # 2) Euro ab erster freier Spalte
    start_x = first_free_x(grid)
    if n_euro >= 30:
        g_e = variant_euro_30(n_euro, x0=0)
    elif n_euro >= 24:
        g_e = variant_euro_24(n_euro, x0=0)
    else:
        # einfache 3er-Reihen längs ab 0, später versetzt gemerged
        g_e = variant_euro_24(n_euro, x0=0)
    merge_at_offset(grid, g_e, start_x)
    return grid

# ---------- PRESETS ----------
st.markdown("### ⚡ Presets")
b1, b2, b3, b4 = st.columns(4)
if "n_euro" not in st.session_state: st.session_state.n_euro = 30
if "n_ind"  not in st.session_state: st.session_state.n_ind  = 0
if "n_flow" not in st.session_state: st.session_state.n_flow = 0
if b1.button("Euro 30"):
    st.session_state.n_euro, st.session_state.n_ind, st.session_state.n_flow = 30, 0, 0
if b2.button("Euro 24 (schwer)"):
    st.session_state.n_euro, st.session_state.n_ind, st.session_state.n_flow = 24, 0, 0
if b3.button("Industrie voll 26"):
    st.session_state.n_euro, st.session_state.n_ind, st.session_state.n_flow = 0, 26, 0
if b4.button("Mix 21 Euro + 6 Industrie"):
    st.session_state.n_euro, st.session_state.n_ind, st.session_state.n_flow = 21, 6, 0

# ---------- UI: nur Art + Anzahl ----------
st.markdown("### 📥 Ladung")
c1,c2,c3,c4 = st.columns([1.2,1.2,1.2,1.6])
with c1:
    n_euro = st.number_input("Euro (120×80)", 0, 40, st.session_state.n_euro, key="inp_euro")
with c2:
    n_ind  = st.number_input("Industrie (120×100)", 0, 40, st.session_state.n_ind, key="inp_ind")
with c3:
    show_flowers = st.checkbox("Blumenwagen einblenden", value=False)
with c4:
    n_flow = st.number_input("Blumenwagen (135×55)", 0, 60, st.session_state.n_flow, key="inp_flow", disabled=not show_flowers)

# Gewicht optional & ausblendbar
with st.expander("⚖️ Gewicht eingeben (optional)"):
    st.number_input("kg/Euro", 0, 2000, 0)
    st.number_input("kg/Industrie", 0, 2000, 0)
    st.number_input("kg/Blumenwagen", 0, 2000, 0)

# ---------- Varianten erzeugen ----------
tabs = st.tabs(["Variante A", "Variante B", "Variante C"])

# A
if n_euro >= 30 and n_ind == 0:
    gA = variant_euro_30(n_euro, x0=0)
    tabs[0].markdown("**A:** Euro-30 (1 quer mittig, 2 quer, Rest 3er längs)")
elif n_euro >= 24 and n_ind == 0:
    gA = variant_euro_24(n_euro, x0=0)
    tabs[0].markdown("**A:** Euro-24 (schwer): 2× einzeln quer, 2× doppelt quer, 1× quer, Rest längs")
elif n_ind > 0 and n_euro == 0:
    gA = variant_industrie(n_ind, x0=0)
    tabs[0].markdown("**A:** Industrie – alles quer, Einzel vorn mittig (ungerade)")
else:
    gA = variant_mix(n_euro, n_ind)
    tabs[0].markdown("**A:** Mix – Industrie zuerst, Euro dahinter")
render(gA, "Ladeplan A")

# B: Alternative
with tabs[1]:
    if n_ind > 0 and n_euro > 0:
        gB = variant_mix(n_euro, n_ind)  # (kann später zweite Heuristik werden)
        st.markdown("**B:** Mix (alternative Heuristik – gleicher Start, anderes Muster geplant)")
        render(gB, "Ladeplan B")
    else:
        st.markdown("_Keine Alternative nötig_")

# C: Reserve
with tabs[2]:
    if n_ind > 0 and n_euro == 0:
        gC = variant_industrie(n_ind, x0=0)
        st.markdown("**C:** Industrie (Alternative)")
        render(gC, "Ladeplan C")
    elif n_euro > 0 and n_ind == 0:
        gC = variant_euro_24(n_euro, x0=0)
        st.markdown("**C:** Euro (Alternative schwer)")
        render(gC, "Ladeplan C")
    else:
        st.markdown("_Reserve für weitere Muster_")
