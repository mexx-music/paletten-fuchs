import streamlit as st

st.set_page_config(page_title="🦊 Paletten Fuchs – Auto‑Layouts (Unicode)", layout="centered")
st.title("🦊 Paletten Fuchs – Auto‑Layouts (Unicode)")

# ---------- Trailer & Raster ----------
TRAILER_L = 1360  # cm
TRAILER_W = 245   # cm
cm_per_cell = st.sidebar.slider("Raster (cm/Zelle)", 10, 60, 20, 5)
X = TRAILER_L // cm_per_cell  # Länge in Zellen
Y = TRAILER_W // cm_per_cell  # Breite in Zellen
EM = " "  # \u2003 em-space für saubere Abstände

st.caption(f"Raster: {X} × {Y} Zellen (je {cm_per_cell} cm)")

# ---------- Paletten ----------
PAL = {
    "Euro":       {"L":120, "B":80,  "sym_q":"▭", "sym_l":"▮"},
    "Industrie":  {"L":120, "B":100, "sym_q":"⬜", "sym_l":"⬜"},  # immer quer
    "Blumenwagen":{"L":135, "B":55,  "sym_q":"▣", "sym_l":"▣"},
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

# Hilfsfunktionen
def size_cells(name, ori):
    L,B = PAL[name]["L"], PAL[name]["B"]
    if name == "Industrie":  # immer quer
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

def stamp_symbol(grid, x, y, sym):
    if 0 <= x < X and 0 <= y < Y:
        grid[y][x] = sym

def center_y(width_cells):
    return max(0, (Y - width_cells)//2)

def render(grid, title):
    st.markdown(f"#### {title}")
    for row in grid:
        st.markdown(f"<pre style='font-size:22px;line-height:100%;margin:0'>{''.join(row)}</pre>", unsafe_allow_html=True)

# ---------- Varianten-Generatoren ----------

# V1: Euro-30 (fixe Regel) 1 quer mittig, 2 quer links/rechts, Rest 3er längs
def variant_euro_30(n):
    grid = blank_grid()
    # 1 quer mittig
    d_q, w_q, s_q = size_cells("Euro","quer")
    x = 0
    y = center_y(w_q)
    stamp_symbol(grid, x, y, s_q)
    x += d_q
    # 2 quer links/rechts
    stamp_symbol(grid, x, 0, s_q)                 # links
    stamp_symbol(grid, x, Y-1, s_q)               # rechts (Symbol-Anker)
    x += d_q
    # Rest längs in 3er-Reihen
    d_l, w_l, s_l = size_cells("Euro","längs")
    rows_needed = max(0, (n - 3) // 3)  # 3 schon vorn
    # drei Spuren quer (links/mitte/rechts)
    yL = 0
    yM = center_y(w_l)
    yR = Y-1
    for r in range(rows_needed):
        xr = x + r*d_l
        stamp_symbol(grid, xr, yL, s_l)
        stamp_symbol(grid, xr, yM, s_l)
        stamp_symbol(grid, xr, yR, s_l)
        if xr + d_l >= X: break
    return grid

# V2: Euro-24 (schwer, Getränke) – Beispielregel:
# 2× einzeln quer (hintereinander mittig), dann 2× Doppel-quer, dann 1× Einzel quer, dahinter 3er längs
def variant_euro_24(n):
    grid = blank_grid()
    d_q,w_q,s_q = size_cells("Euro","quer")
    d_l,w_l,s_l = size_cells("Euro","längs")
    x=0
    yC = center_y(w_q)
    # 2× einzeln quer mittig (hintereinander)
    if n<=0: return grid
    stamp_symbol(grid,x,yC,s_q); x+=d_q; n-=1
    if n<=0: return grid
    stamp_symbol(grid,x,yC,s_q); x+=d_q; n-=1
    # 2× Doppel-quer (links & rechts)
    if n<=0: return grid
    stamp_symbol(grid,x,0,s_q)
    if n>1:
        stamp_symbol(grid,x,Y-1,s_q); n-=2; x+=d_q
    else:
        n-=1; x+=d_q
    # 1× Einzel quer mittig (falls noch da)
    if n>0:
        stamp_symbol(grid,x,yC,s_q); x+=d_q; n-=1
    # Rest in 3er-Reihen längs
    yL=0; yM=center_y(w_l); yR=Y-1
    while n>0 and x < X:
        if n>0: stamp_symbol(grid,x,yL,s_l); n-=1
        if n>0: stamp_symbol(grid,x,yM,s_l); n-=1
        if n>0: stamp_symbol(grid,x,yR,s_l); n-=1
        x+=d_l
    return grid

# V3: Industrie auto (immer quer). Einzel mittig möglich, sonst Reihen links/rechts
def variant_industrie(n):
    grid = blank_grid()
    d_q,w_q,s_q = size_cells("Industrie","quer")  # erzwingt quer
    x=0
    # Falls ungerade: 1 vorn mittig
    if n%2==1:
        stamp_symbol(grid,x,center_y(w_q),s_q)
        x+=d_q; n-=1
    # Reihen mit 2 quer links+rechts
    while n>0 and x < X:
        stamp_symbol(grid,x,0,s_q)
        if n>1:
            stamp_symbol(grid,x,Y-1,s_q); n-=2; x+=d_q
        else:
            n-=1; x+=d_q
    return grid

# Blumenwagen-Kacheln (3 quer, 2 längs – wiederholt)
def place_flowers(grid, n):
    if n<=0: return
    d_q,w_q,s_q = size_cells("Blumenwagen","quer")
    d_l,w_l,s_l = size_cells("Blumenwagen","längs")
    x=0
    # 3 quer Reihe
    for i in range(min(3,n)):
        y = int((i/(3-1))*(Y-1)) if Y>1 else 0  # links/mitte/rechts
        stamp_symbol(grid,x,y,s_q)
    n -= min(3,n)
    x += d_q
    # 2 längs
    if n>0:
        stamp_symbol(grid,x,0,s_l); n-=1
    if n>0:
        stamp_symbol(grid,x,Y-1,s_l); n-=1

# V4: Mix – einfache Heuristik: zuerst Industrie quer blocken, danach Euro wie V1/V2
def variant_mix(n_euro, n_ind):
    grid = blank_grid()
    # Industrie zuerst
    if n_ind>0:
        g_ind = variant_industrie(n_ind)
        # merge
        for y in range(Y):
            for x in range(X):
                if g_ind[y][x] != EM:
                    grid[y][x] = g_ind[y][x]
    # Finde vorderste freie x-Spalte
    def first_free_x():
        for xx in range(X):
            col_free = any(grid[y][xx] == EM for y in range(Y))
            if col_free: return xx
        return X
    start_x = first_free_x()
    # Euro dahinter – wähle Template je nach Menge
    if n_euro >= 30:
        g_e = variant_euro_30(n_euro)
    elif n_euro >= 24:
        g_e = variant_euro_24(n_euro)
    else:
        # kleiner Bestand: einfache 3er-Reihen längs
        g_e = blank_grid()
        d_l,w_l,s_l = size_cells("Euro","längs")
        x = 0
        yL=0; yM=center_y(w_l); yR=Y-1
        nn = n_euro
        while nn>0 and x<X:
            if nn>0: stamp_symbol(g_e,x,yL,s_l); nn-=1
            if nn>0: stamp_symbol(g_e,x,yM,s_l); nn-=1
            if nn>0: stamp_symbol(g_e,x,yR,s_l); nn-=1
            x+=d_l
    # merge Euro hinter start_x
    for y in range(Y):
        row = g_e[y]
        for x in range(X):
            if row[x] != EM:
                xx = min(X-1, x + start_x)
                if grid[y][xx] == EM:
                    grid[y][xx] = row[x]
    return grid

# ---------- Varianten erzeugen ----------
tabs = st.tabs(["Variante A", "Variante B", "Variante C"])

# A: If Euro>=30 → Euro-30; elif Euro>=24 → Euro-24; elif Industrie>0 → Industrie-auto; else einfache 3er-Reihen
if n_euro >= 30:
    gA = variant_euro_30(n_euro)
    tabs[0].markdown("**A:** Euro-30 (1 quer mittig, 2 quer, Rest 3er längs)")
elif n_euro >= 24:
    gA = variant_euro_24(n_euro)
    tabs[0].markdown("**A:** Euro-24 (schwer) – 2× einzeln quer, 2× doppelt quer, 1× einzeln, Rest längs")
elif n_ind > 0:
    gA = variant_industrie(n_ind)
    tabs[0].markdown("**A:** Industrie – alles quer, Einzel vorn mittig erlaubt")
else:
    gA = variant_euro_24(n_euro) if n_euro else blank_grid()
    tabs[0].markdown("**A:** Euro – kompakte Reihen")

render(gA, "Ladeplan A")

# B: Mix-Heuristik (Industrie zuerst, Euro dahinter nach Regel)
gB = variant_mix(n_euro, n_ind)
with tabs[1]:
    st.markdown("**B:** Mix-Heuristik – Industrie zuerst (quer), Euro dahinter")
    render(gB, "Ladeplan B")

# C: Nur Industrie oder nur Euro alternative Darstellung
if n_ind > 0 and n_euro == 0:
    gC = variant_industrie(n_ind)
    c_text = "**C:** Industrie alternative Reihen (immer quer)"
else:
    gC = variant_euro_24(n_euro) if n_euro else blank_grid()
    c_text = "**C:** Euro alternative (schwer) / leer"
with tabs[2]:
    st.markdown(c_text)
    render(gC, "Ladeplan C")

# Blumenwagen optional drüber legen (nur Demo – einfache Kachel vorne)
if show_flowers and n_flow>0:
    st.info("Blumenwagen (Demo-Muster 3 quer + 2 längs) werden vorne eingeblendet.")
    gF = blank_grid()
    place_flowers(gF, n_flow)
    st.markdown("#### Blumenwagen-Overlay (vorne)")
    render(gF, "Blumenwagen")
