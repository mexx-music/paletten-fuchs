import streamlit as st

st.set_page_config(page_title="🦊 Paletten Fuchs – Auto‑Layouts (Unicode‑Blöcke)", layout="centered")
st.title("🦊 Paletten Fuchs – Draufsicht (Unicode‑Blöcke)")

# ---------- Trailer & Raster ----------
TRAILER_L = 1360  # cm
TRAILER_W = 245   # cm
cm_per_cell = st.sidebar.slider("Raster (cm/Zelle)", 10, 60, 20, 5)
X = TRAILER_L // cm_per_cell  # Länge in Zellen (x)
Y = TRAILER_W // cm_per_cell  # Breite in Zellen (y)
EM = " "  # leer

st.caption(f"Raster: {X}×{Y} Zellen (je {cm_per_cell} cm)")

# ---------- Paletten / Symbole ----------
PAL = {
    "Euro":       {"L":120, "B":80,  "sym_q":"▭", "sym_l":"▮"},
    "Industrie":  {"L":120, "B":100, "sym_q":"⬜", "sym_l":"⬜"},   # immer quer
    "Blumenwagen":{"L":135, "B":55,  "sym_q":"▣", "sym_l":"▣"},
}

def size_cells(name, ori):
    """gibt (depth_x, width_y, symbol) in Zelleneinheiten zurück"""
    L, B = PAL[name]["L"], PAL[name]["B"]
    if name == "Industrie":  # Regel: immer quer
        ori = "quer"
    if ori == "quer":
        depth = max(1, B // cm_per_cell)   # Tiefe entlang x
        width = max(1, L // cm_per_cell)   # Breite quer (y)
        sym   = PAL[name]["sym_q"]
    else:  # längs
        depth = max(1, L // cm_per_cell)
        width = max(1, B // cm_per_cell)
        sym   = PAL[name]["sym_l"]
    return depth, width, sym

def blank_grid():
    return [[EM for _ in range(X)] for _ in range(Y)]

def can_place(grid, x, y, dx, dy):
    if x < 0 or y < 0 or x+dx > X or y+dy > Y: return False
    for yy in range(y, y+dy):
        for xx in range(x, x+dx):
            if grid[yy][xx] != EM: return False
    return True

def draw_block(grid, x, y, dx, dy, sym):
    """füllt den ganzen Paletten‑Block mit Unicode‑Zeichen; Rahmen leicht betont"""
    for yy in range(y, y+dy):
        for xx in range(x, x+dx):
            # Rand etwas markanter (wenn möglich)
            is_border = (yy==y or yy==y+dy-1 or xx==x or xx==x+dx-1)
            grid[yy][xx] = sym if is_border else (sym if dx<=2 or dy<=2 else "·")

def center_y(width_cells):
    return max(0, (Y - width_cells)//2)

def render(grid, title):
    st.markdown(f"#### {title}")
    for row in grid:
        st.markdown(f"<pre style='font-size:22px; line-height:100%; margin:0'>{''.join(row)}</pre>", unsafe_allow_html=True)

# ---------- Presets ----------
st.markdown("### ⚡ Presets")
b1, b2, b3, b4 = st.columns(4)
if "n_euro" not in st.session_state: st.session_state.n_euro = 30
if "n_ind"  not in st.session_state: st.session_state.n_ind  = 0
if "n_flow" not in st.session_state: st.session_state.n_flow = 0
if b1.button("Euro 30"):
    st.session_state.n_euro, st.session_state.n_ind, st.session_state.n_flow = 30, 0, 0
if b2.button("Euro 24 (schwer)"):
    st.session_state.n_euro, st.session_state.n_ind, st.session_state.n_flow = 24, 0, 0
if b3.button("Industrie 26"):
    st.session_state.n_euro, st.session_state.n_ind, st.session_state.n_flow = 0, 26, 0
if b4.button("Mix 21 Euro + 6 Industrie"):
    st.session_state.n_euro, st.session_state.n_ind, st.session_state.n_flow = 21, 6, 0

# ---------- UI: nur Art + Anzahl ----------
st.markdown("### 📥 Ladung")
c1,c2,c3,c4 = st.columns([1.2,1.2,1.2,1.6])
with c1:
    n_euro = st.number_input("Euro (120×80)", 0, 45, st.session_state.n_euro, key="inp_euro")
with c2:
    n_ind  = st.number_input("Industrie (120×100)", 0, 45, st.session_state.n_ind,  key="inp_ind")
with c3:
    show_flowers = st.checkbox("Blumenwagen einblenden", value=False)
with c4:
    n_flow = st.number_input("Blumenwagen (135×55)", 0, 60, st.session_state.n_flow, key="inp_flow", disabled=not show_flowers)

with st.expander("⚖️ Gewicht eingeben (optional)"):
    st.number_input("kg/Euro", 0, 2000, 0)
    st.number_input("kg/Industrie", 0, 2000, 0)
    st.number_input("kg/Blumenwagen", 0, 2000, 0)

# ---------- Varianten (zeichnen echte Blöcke) ----------
def euro_30_layout(grid, n, x0=0):
    dq,wq,_ = size_cells("Euro","quer")
    dl,wl,_ = size_cells("Euro","längs")
    x = x0
    # 1 quer mittig
    y = center_y(wq)
    if n>0 and can_place(grid, x, y, dq, wq):
        draw_block(grid, x, y, dq, wq, PAL["Euro"]["sym_q"]); n -= 1
    x += dq
    # 2 quer links + rechts
    for yy in [0, Y-wq]:
        if n>0 and can_place(grid, x, yy, dq, wq):
            draw_block(grid, x, yy, dq, wq, PAL["Euro"]["sym_q"]); n -= 1
    x += dq
    # Rest: 3‑Spur längs (links/mitte/rechts)
    lanes = [0, center_y(wl), Y-wl]
    while n>0 and x+dl <= X:
        for yy in lanes:
            if n>0 and can_place(grid, x, yy, dl, wl):
                draw_block(grid, x, yy, dl, wl, PAL["Euro"]["sym_l"]); n -= 1
        x += dl

def euro_24_layout(grid, n, x0=0):
    dq,wq,_ = size_cells("Euro","quer")
    dl,wl,_ = size_cells("Euro","längs")
    x = x0
    yC = center_y(wq)
    # 2× einzel quer mittig
    for _ in range(min(2,n)):
        if can_place(grid, x, yC, dq, wq):
            draw_block(grid, x, yC, dq, wq, PAL["Euro"]["sym_q"]); n -= 1; x += dq
    # 2× doppelt quer (links+rechts)
    for _ in range(2):
        if n<=0: break
        for yy in [0, Y-wq]:
            if n>0 and can_place(grid, x, yy, dq, wq):
                draw_block(grid, x, yy, dq, wq, PAL["Euro"]["sym_q"]); n -= 1
        x += dq
    # 1× einzel quer mittig (falls übrig)
    if n>0 and can_place(grid, x, yC, dq, wq):
        draw_block(grid, x, yC, dq, wq, PAL["Euro"]["sym_q"]); n -= 1; x += dq
    # Rest längs 3‑Spur
    lanes = [0, center_y(wl), Y-wl]
    while n>0 and x+dl <= X:
        for yy in lanes:
            if n>0 and can_place(grid, x, yy, dl, wl):
                draw_block(grid, x, yy, dl, wl, PAL["Euro"]["sym_l"]); n -= 1
        x += dl

def industrie_layout(grid, n, x0=0):
    dq,wq,_ = size_cells("Industrie","quer")
    x = x0
    # ungerade → 1 mittig vorne
    if n%2==1 and can_place(grid, x, center_y(wq), dq, wq):
        draw_block(grid, x, center_y(wq), dq, wq, PAL["Industrie"]["sym_q"]); n -= 1; x += dq
    while n>0 and x+dq <= X:
        for yy in [0, Y-wq]:
            if n>0 and can_place(grid, x, yy, dq, wq):
                draw_block(grid, x, yy, dq, wq, PAL["Industrie"]["sym_q"]); n -= 1
        x += dq

def first_free_x(grid):
    for xx in range(X):
        if any(grid[yy][xx] == EM for yy in range(Y)):
            return xx
    return X

def merge_from(grid_dst, grid_src, offx):
    for y in range(Y):
        for x in range(X):
            if grid_src[y][x] != EM:
                xx = x + offx
                if 0 <= xx < X and grid_dst[y][xx] == EM:
                    grid_dst[y][xx] = grid_src[y][x]

def euro_rows_simple(grid, n, x0=0):
    dl,wl,_ = size_cells("Euro","längs")
    x = x0
    lanes = [0, center_y(wl), Y-wl]
    while n>0 and x+dl <= X:
        for yy in lanes:
            if n>0 and can_place(grid, x, yy, dl, wl):
                draw_block(grid, x, yy, dl, wl, PAL["Euro"]["sym_l"]); n -= 1
        x += dl

def mix_variant(n_euro, n_ind):
    base = blank_grid()
    # 1) Industrie vorn
    gI = blank_grid()
    industrie_layout(gI, n_ind, x0=0)
    merge_from(base, gI, 0)
    # 2) Euro dahinter (ab erster freier Spalte)
    start = first_free_x(base)
    gE = blank_grid()
    if n_euro >= 30:
        euro_30_layout(gE, n_euro, x0=0)
    elif n_euro >= 24:
        euro_24_layout(gE, n_euro, x0=0)
    else:
        euro_rows_simple(gE, n_euro, x0=0)
    merge_from(base, gE, start)
    return base

# ---------- Varianten anzeigen ----------
tabs = st.tabs(["Variante A", "Variante B", "Variante C"])

# A
if n_ind>0 and n_euro>0:
    gA = mix_variant(n_euro, n_ind)
    tabs[0].markdown("**A:** Mix – Industrie zuerst (quer), Euro dahinter (30/24‑Regel)")
elif n_euro >= 30:
    gA = blank_grid(); euro_30_layout(gA, n_euro, x0=0)
    tabs[0].markdown("**A:** Euro‑30: 1 quer mittig, 2 quer außen, Rest 3er‑Reihen längs")
elif n_euro >= 24:
    gA = blank_grid(); euro_24_layout(gA, n_euro, x0=0)
    tabs[0].markdown("**A:** Euro‑24 (schwer): 2× einzeln quer, 2× doppelt quer, 1× quer, Rest längs")
elif n_ind > 0:
    gA = blank_grid(); industrie_layout(gA, n_ind, x0=0)
    tabs[0].markdown("**A:** Industrie nur quer (ungerade: 1 vorn mittig)")
else:
    gA = blank_grid()
render(gA, "Ladeplan A")

# B: Alternative (Euro‑Reihen oder Industrie‑Reihen separat)
with tabs[1]:
    gB = blank_grid()
    if n_euro and not n_ind:
        euro_rows_simple(gB, n_euro, x0=0)
        st.markdown("**B:** Euro – einfache 3er‑Reihen längs")
    elif n_ind and not n_euro:
        industrie_layout(gB, n_ind, x0=0)
        st.markdown("**B:** Industrie – Reihen nur quer")
    else:
        gB = mix_variant(n_euro, n_ind)
        st.markdown("**B:** Mix (gleicher Algorithmus) – zweite Ansicht")
    render(gB, "Ladeplan B")

# C: Reserve
with tabs[2]:
    gC = blank_grid()
    st.markdown("_Weitere Muster folgen (z. B. 26 Euro, 34 Euro, Mix‑Varianten mit Blumenwagen)._")
    render(gC, "Ladeplan C")
