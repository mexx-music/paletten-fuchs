import math
import streamlit as st

st.set_page_config(page_title="🦊 PAL Fuchs 8 – Varianten (Fix: Ceil + echte Längen)", layout="wide")
st.title("🦊 PAL Fuchs – Draufsicht mit Icons & Varianten")

# ---------- Trailer & Grid ----------
TRAILER_L, TRAILER_W = 1360, 245  # cm

# Wunsch-Defaults: Raster 25 cm, Zoom 4 px
cell_cm = st.sidebar.slider("Raster (cm/Zelle)", 5, 40, 25, 5)
cell_px = st.sidebar.slider("Zellpixel (Zoom)", 4, 14, 4, 1)

X, Y = TRAILER_L // cell_cm, TRAILER_W // cell_cm

# ---------- Icons ----------
ICON = {
    ("Euro","l"): "icons/euro_l.png",
    ("Euro","q"): "icons/euro_q.png",
    ("Industrie","q"): "icons/ind_q.png",
    ("Blume","l"): "icons/flower_l.png",
    ("Blume","q"): "icons/flower_q.png",
}

# ---------- Hilfsfunktionen ----------
def dims_cm(name):
    if name == "Euro":        return 120, 80   # L x B
    elif name == "Industrie": return 120,100
    else:                     return 135, 55   # Blume (Demo)

def span(name, ori):
    L,B = dims_cm(name)
    # Industrie immer quer
    if name == "Industrie":
        ori = "q"
    # Tiefe (entlang Trailer-Länge), Breite (quer im Trailer)
    if ori == "q":
        depth_cm, width_cm = B, L
    else:
        depth_cm, width_cm = L, B
    # WICHTIG: ceil statt floor, damit nichts zu klein gerastert wird
    dx = max(1, math.ceil(depth_cm / cell_cm))   # entlang Länge (x)
    dy = max(1, math.ceil(width_cm / cell_cm))   # quer (y)
    return dx, dy, depth_cm, width_cm, ori

def center_y(dy): 
    return max(0, (Y - dy) // 2)

def empty_board():
    occupied = [[False]*X for _ in range(Y)]
    # Speichere reale Tiefe in cm & Orientierung für echte Nutzlänge
    # item: (x,y,dx,dy,icon,typ,depth_cm,ori)
    items = []
    placed = {"Euro":0, "Industrie":0, "Blume":0}
    return occupied, items, placed

def free(occ, x,y,dx,dy):
    if x<0 or y<0 or x+dx>X or y+dy>Y: 
        return False
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            if occ[yy][xx]: 
                return False
    return True

def place(occ, items, placed, x,y,dx,dy,icon,typ,depth_cm,ori):
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            occ[yy][xx] = True
    items.append((x,y,dx,dy,icon,typ,depth_cm,ori))
    placed[typ] += 1

def first_free_x(occ):
    for xx in range(X):
        if any(not occ[yy][xx] for yy in range(Y)): 
            return xx
    return X

def used_length_cm_true(items):
    """Echte Nutzlänge in cm (linke Kante x*cell_cm + reale Tiefe)"""
    if not items: 
        return 0
    x_end_cm = 0
    for (x,y,dx,dy,icon,typ,depth_cm,ori) in items:
        right_edge = x * cell_cm + depth_cm
        if right_edge > x_end_cm:
            x_end_cm = right_edge
    return min(x_end_cm, TRAILER_L)

# ---------- Heckabschluss Euro: 3 längs-Spuren, Rest=2 quer ----------
def fill_tail_closed_euro(occ, items, placed, x_start, euro_left):
    if euro_left <= 0: 
        return
    dq,wq,dq_cm,_,_ = span("Euro","q")
    dl,wl,dl_cm,_,_ = span("Euro","l")

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
        if x + dl > X: break
        for y in lanes:
            if free(occ, x,y,dl,wl):
                place(occ, items, placed, x,y,dl,wl, ICON[("Euro","l")], "Euro", dl_cm, "l")
        x += dl
    # 2× Querabschluss
    if need_tail_q and x + dq <= X:
        if free(occ, x,0,dq,wq):
            place(occ, items, placed, x,0,dq,wq, ICON[("Euro","q")], "Euro", dq_cm, "q")
        if free(occ, x,Y-wq,dq,wq):
            place(occ, items, placed, x,Y-wq,dq,wq, ICON[("Euro","q")], "Euro", dq_cm, "q")

# ---------- Bausteine ----------
def block_industrie_all(occ, items, placed, n):
    dq,wq,dq_cm,_,_ = span("Industrie","q")
    x=0
    # ungerade → 1 mittig zuerst
    if n%2==1:
        y=center_y(wq)
        if free(occ, x,y,dq,wq):
            place(occ, items, placed, x,y,dq,wq, ICON[("Industrie","q")], "Industrie", dq_cm, "q")
            n -= 1; x += dq
    # Paare links+rechts
    while n>0 and x+dq<=X:
        for y in [0, Y-wq]:
            if n>0 and free(occ, x,y,dq,wq):
                place(occ, items, placed, x,y,dq,wq, ICON[("Industrie","q")], "Industrie", dq_cm, "q")
                n -= 1
        x += dq
    return x  # nächste freie Spalte (ungefähr)

def block_euro_only_long(occ, items, placed, x_start, n):
    dl,wl,dl_cm,_,_ = span("Euro","l")
    lanes = [0, center_y(wl), Y-wl]
    x = x_start
    while n>0 and x+dl<=X:
        for y in lanes:
            if n>0 and free(occ, x,y,dl,wl):
                place(occ, items, placed, x,y,dl,wl, ICON[("Euro","l")], "Euro", dl_cm, "l")
                n -= 1
        x += dl

def block_euro_cross_then_long(occ, items, placed, x_start, n):
    dq,wq,dq_cm,_,_ = span("Euro","q")
    dl,wl,dl_cm,_,_ = span("Euro","l")
    x = x_start
    # 1 quer mittig
    if n>0 and x+dq<=X and free(occ, x,center_y(wq),dq,wq):
        place(occ, items, placed, x,center_y(wq),dq,wq, ICON[("Euro","q")], "Euro", dq_cm, "q")
        n -= 1; x += dq
    # 2 quer außen
    if n>=2 and x+dq<=X:
        for y in [0, Y-wq]:
            if n>0 and free(occ, x,y,dq,wq):
                place(occ, items, placed, x,y,dq,wq, ICON[("Euro","q")], "Euro", dq_cm, "q")
                n -= 1
        x += dq
    # Rest: geschlossen
    fill_tail_closed_euro(occ, items, placed, x, n)

def block_euro_long_then_cross_tail(occ, items, placed, x_start, n):
    # erst rein längs in 3er-Spuren, am Ende ggf. 2 quer (geschlossen)
    dl,wl,dl_cm,_,_ = span("Euro","l")
    lanes = [0, center_y(wl), Y-wl]
    x = x_start
    col_cap = 3
    while n >= col_cap and x+dl <= X:
        for y in lanes:
            if free(occ, x,y,dl,wl):
                place(occ, items, placed, x,y,dl,wl, ICON[("Euro","l")], "Euro", dl_cm, "l")
        n -= col_cap
        x += dl
    # Rest geschlossen
    fill_tail_closed_euro(occ, items, placed, x, n)

# ---------- Varianten-Generator ----------
def generate_variants(n_euro, n_ind, force_euro_long=False):
    variants = []

    # Variante 1: Industrie → Euro (quer+quer+geschlossen)
    occ, items, placed = empty_board()
    if n_ind>0:
        block_industrie_all(occ, items, placed, n_ind)
    start = first_free_x(occ)
    if force_euro_long:
        block_euro_only_long(occ, items, placed, start, n_euro)
    else:
        block_euro_cross_then_long(occ, items, placed, start, n_euro)
    variants.append((items, placed))

    # Variante 2: Industrie → Euro (längs zuerst, dann geschlossener Abschluss)
    occ, items, placed = empty_board()
    if n_ind>0:
        block_industrie_all(occ, items, placed, n_ind)
    start = first_free_x(occ)
    block_euro_long_then_cross_tail(occ, items, placed, start, n_euro)
    variants.append((items, placed))

    # Variante 3: Euro-only längs über alles (für z.B. 33 längs)
    occ, items, placed = empty_board()
    if n_ind>0:
        block_industrie_all(occ, items, placed, n_ind)
        start = first_free_x(occ)
        block_euro_only_long(occ, items, placed, start, n_euro)
    else:
        block_euro_only_long(occ, items, placed, 0, n_euro)
    variants.append((items, placed))

    # Variante 4: Euro quer-Start doppelt (außen), dann längs, dann Tail
    occ, items, placed = empty_board()
    if n_ind>0:
        block_industrie_all(occ, items, placed, n_ind)
    start = first_free_x(occ)
    dq,wq,dq_cm,_,_ = span("Euro","q")
    x = start
    if n_euro>=2 and x+dq<=X:
        for y in [0, Y-wq]:
            if n_euro>0 and free(occ, x,y,dq,wq):
                place(occ, items, placed, x,y,dq,wq, ICON[("Euro","q")], "Euro", dq_cm, "q")
                n_euro -= 1
        x += dq
    fill_tail_closed_euro(occ, items, placed, x, n_euro)
    variants.append((items, placed))

    return variants

# ---------- UI: Eingaben ----------
st.markdown("### 📥 Manuelle Menge")
c1,c2,c3,c4 = st.columns([1.2,1.2,1.2,1.6])
with c1: n_euro = st.number_input("Euro (120×80)", 0, 45, 30)
with c2: n_ind  = st.number_input("Industrie (120×100)", 0, 45, 0)
with c3: force_long = st.checkbox("Euro nur längs erzwingen (z. B. 33)", value=False)
with c4: _dummy = st.markdown("&nbsp;")

# Varianten erzeugen
variants = generate_variants(int(n_euro), int(n_ind), force_euro_long=force_long)

# Navigation
if "var_idx" not in st.session_state: st.session_state.var_idx = 0
nav1,nav2,nav3 = st.columns([1,1,3])
with nav1:
    if st.button("◀ Variante"):
        st.session_state.var_idx = (st.session_state.var_idx - 1) % len(variants)
with nav2:
    if st.button("Variante ▶"):
        st.session_state.var_idx = (st.session_state.var_idx + 1) % len(variants)
with nav3:
    st.markdown(f"**Variante:** {st.session_state.var_idx+1} / {len(variants)}")

items, placed = variants[st.session_state.var_idx]

# ---------- Render ----------
html = f"""
<div style="
  display:grid;
  grid-template-columns: repeat({X}, {cell_px}px);
  grid-auto-rows: {cell_px}px;
  gap: 1px;
  background:#ddd; padding:4px; border:2px solid #333; width:fit-content;">
"""
for (x,y,dx,dy,icon,typ,depth_cm,ori) in items:
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

# ---------- Kapazitätsprüfung & echte Nutzlänge ----------
wanted = {"Euro": int(n_euro), "Industrie": int(n_ind)}
missing_msgs = []
for typ in ["Euro","Industrie"]:
    if wanted[typ] > 0 and placed.get(typ,0) < wanted[typ]:
        missing = wanted[typ] - placed.get(typ,0)
        missing_msgs.append(f"– {missing}× {typ} passt/passen nicht mehr")

used_cm = used_length_cm_true(items)
st.markdown(f"**Genutzte Länge (realistisch):** {used_cm} cm von {TRAILER_L} cm  (≈ {used_cm/TRAILER_L:.0%})")

if missing_msgs:
    st.error("🚫 **Platz reicht nicht:**\n" + "\n".join(missing_msgs))
else:
    st.success("✅ **Alle angeforderten Paletten passen in den Laderaum.**")

st.info("Tipp: Raster 25 cm & Zoom 4 px sind die empfohlenen Grundwerte. (Jetzt mit Ceil‑Rasterung & echten cm‑Längen.)")
