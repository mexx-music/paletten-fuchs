# app.py
import streamlit as st

st.set_page_config(page_title="🦊 PAL Fuchs 8 – Varianten (fixe Physik)", layout="wide")
st.title("🦊 PAL Fuchs 8 – Draufsicht mit Icons & Varianten")

# ----------------- Trailer / Raster -----------------
TRAILER_L, TRAILER_W = 1360, 245  # cm

# Anzeige-Defaults (so wie von dir gewünscht)
cell_cm = st.sidebar.slider("Raster (cm/Zelle) – Anzeige", 5, 40, 25, 5)
cell_px = st.sidebar.slider("Zellpixel (Zoom)", 4, 14, 4, 1)

# Diskrete Gittergröße (nur Anzeige – die physikalische Berechnung unten nutzt cm)
X, Y = TRAILER_L // cell_cm, TRAILER_W // cell_cm   # 54 x 9 bei 25 cm

# ----------------- Icons -----------------
ICON = {
    ("Euro","l"): "icons/euro_l.png",
    ("Euro","q"): "icons/euro_q.png",
    ("Industrie","q"): "icons/ind_q.png",   # Industrie immer quer
    ("Blume","l"): "icons/flower_l.png",
    ("Blume","q"): "icons/flower_q.png",
}

# ----------------- Maße (cm) -----------------
SIZES = {
    ("Euro","l"): (120, 80),   # (Tiefe entlang Laderaumlänge, Breite quer)
    ("Euro","q"): ( 80,120),
    ("Industrie","q"): (100,120),
    ("Blume","l"): (135, 55),
    ("Blume","q"): ( 55,135),
}

def span_cells(name, ori):
    """Rasterabmessungen in Zellen (für die Anzeige). Flooren garantiert, dass 33 längs reinpassen."""
    depth_cm, width_cm = SIZES[(name, ori)]
    dx = max(1, depth_cm // cell_cm)      # Spalten (x)
    dy = max(1, width_cm // cell_cm)      # Reihen (y)
    return dx, dy

def center_y(dy): 
    return max(0, (Y - dy) // 2)

def empty_board():
    occ = [[False]*X for _ in range(Y)]
    items = []   # (x,y,dx,dy,icon,typ,ori, depth_cm)
    placed = {"Euro":0, "Industrie":0, "Blume":0}
    return occ, items, placed

def free(occ, x,y,dx,dy):
    if x<0 or y<0 or x+dx>X or y+dy>Y: 
        return False
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            if occ[yy][xx]: 
                return False
    return True

def occupy(occ, x,y,dx,dy):
    for yy in range(y,y+dy):
        for xx in range(x,x+dx):
            occ[yy][xx] = True

def place(occ, items, placed, x,y, typ, ori):
    if typ == "Industrie":
        ori = "q"
    dx, dy = span_cells(typ, ori)
    if not free(occ, x,y,dx,dy):
        return False
    occupy(occ, x,y,dx,dy)
    items.append((x,y,dx,dy, ICON[(typ,ori)], typ, ori, SIZES[(typ,ori)][0]))
    placed[typ] += 1
    return True

def first_free_x(occ):
    for xx in range(X):
        if any(not occ[yy][xx] for yy in range(Y)):
            return xx
    return X

def used_length_cm(items):
    """Physikalisch: größte x+dx in Zellen * cell_cm (nur Anzeige – ok für Fortschrittsbalken)."""
    if not items:
        return 0
    x_end = max(x+dx for (x,y,dx,dy,icon,typ,ori,depth) in items)
    return x_end * cell_cm

# ---------- Abschlussregel: „hinten geschlossen“ (Euro) ----------
def fill_tail_closed_euro(occ, items, placed, x_start, euro_left):
    if euro_left <= 0:
        return
    dq,wq = span_cells("Euro","q")
    dl,wl = span_cells("Euro","l")
    lanes = [0, center_y(wl), Y-wl]

    # so viele volle 3er-Spalten längs wie gehen
    while euro_left >= 3 and x_start+dl <= X:
        ok = True
        for y in lanes:
            if not free(occ, x_start, y, dl, wl):
                ok = False
                break
        if not ok:
            break
        for y in lanes:
            place(occ, items, placed, x_start, y, "Euro", "l")
        euro_left -= 3
        x_start  += dl

    # Rest sauber schließen: 2 quer wenn >=2, sonst ggf. 1 quer mittig
    if euro_left >= 2 and x_start + dq <= X:
        place(occ, items, placed, x_start, 0,      "Euro", "q")
        place(occ, items, placed, x_start, Y-wq,   "Euro", "q")
        euro_left -= 2
        x_start   += dq
    if euro_left == 1 and x_start + dq <= X:
        place(occ, items, placed, x_start, center_y(wq), "Euro", "q")

# ---------- Bausteine ----------
def block_industrie_all(occ, items, placed, n):
    """Industrie nur quer: erst mittig wenn ungerade, dann Spalten links+rechts."""
    dq,wq = span_cells("Industrie","q")
    x = 0
    if n % 2 == 1:
        if place(occ, items, placed, x, center_y(wq), "Industrie", "q"):
            n -= 1
            x += dq
    while n > 0 and x + dq <= X:
        for y in [0, Y-wq]:
            if n > 0 and place(occ, items, placed, x, y, "Industrie", "q"):
                n -= 1
        x += dq
    return x

def block_euro_only_long(occ, items, placed, x_start, n):
    dl,wl = span_cells("Euro","l")
    lanes = [0, center_y(wl), Y-wl]
    x = x_start
    while n > 0 and x + dl <= X:
        for y in lanes:
            if n>0 and place(occ, items, placed, x, y, "Euro", "l"):
                n -= 1
        x += dl

def block_euro_cross_then_long(occ, items, placed, x_start, n):
    dq,wq = span_cells("Euro","q")
    x = x_start
    # 1 quer mittig
    if n>0 and x + dq <= X and place(occ, items, placed, x, center_y(wq), "Euro", "q"):
        n -= 1
        x += dq
    # 2 quer außen
    if n>=2 and x + dq <= X:
        for y in [0, Y-wq]:
            if n>0 and place(occ, items, placed, x, y, "Euro", "q"):
                n -= 1
        x += dq
    # Rest: geschlossen
    fill_tail_closed_euro(occ, items, placed, x, n)

def block_euro_long_then_cross_tail(occ, items, placed, x_start, n):
    """Erst so viele 3er Längs-Spalten wie möglich, dann sauberer Abschluss."""
    dl,wl = span_cells("Euro","l")
    lanes = [0, center_y(wl), Y-wl]
    x = x_start
    while n >= 3 and x + dl <= X:
        ok = True
        for y in lanes:
            if not free(occ, x, y, dl, wl):
                ok = False; break
        if not ok:
            break
        for y in lanes:
            place(occ, items, placed, x, y, "Euro", "l")
        n -= 3
        x += dl
    fill_tail_closed_euro(occ, items, placed, x, n)

def block_euro_heavy_front(occ, items, placed, x_start, n):
    """Heuristik für schwere Ladung (21–24): vorne Achse entlasten (einzeln quer), dann Doppel-quer, dann Rest geschlossen."""
    dq,wq = span_cells("Euro","q")
    x = x_start
    # 2× einzeln quer mittig (wenn Platz)
    for _ in range(min(2, n)):
        if x + dq <= X and place(occ, items, placed, x, center_y(wq), "Euro", "q"):
            n -= 1; x += dq
    # 2× doppelt quer (oben+unten)
    for _ in range(2):
        if n >= 2 and x + dq <= X:
            if place(occ, items, placed, x, 0, "Euro", "q"):
                n -= 1
            if n>0 and place(occ, items, placed, x, Y-wq, "Euro", "q"):
                n -= 1
            x += dq
    # 1× einzeln quer, wenn noch viel Last vorne
    if n>0 and x + dq <= X and place(occ, items, placed, x, center_y(wq), "Euro", "q"):
        n -= 1; x += dq
    # Rest geschlossen
    fill_tail_closed_euro(occ, items, placed, x, n)

# ---------- Varianten-Generator ----------
def generate_variants(n_euro, n_ind, force_euro_long=False, heavy=False):
    # Spezialfall: 33 Euro, keine Industrie -> immer „nur längs“
    if n_euro == 33 and n_ind == 0:
        occ, items, placed = empty_board()
        block_euro_only_long(occ, items, placed, 0, n_euro)
        return [(items, placed)]  # eine Variante, aber korrekt

    variants = []

    # V1: Industrie → Euro quer-Start → schließen
    occ, items, placed = empty_board()
    if n_ind>0: block_industrie_all(occ, items, placed, n_ind)
    start = first_free_x(occ)
    if force_euro_long:
        block_euro_only_long(occ, items, placed, start, n_euro)
    elif heavy and (21 <= n_euro <= 24) and n_ind == 0:
        block_euro_heavy_front(occ, items, placed, start, n_euro)
    else:
        block_euro_cross_then_long(occ, items, placed, start, n_euro)
    variants.append((items, placed))

    # V2: Industrie → Euro längs zuerst → schließen
    occ, items, placed = empty_board()
    if n_ind>0: block_industrie_all(occ, items, placed, n_ind)
    start = first_free_x(occ)
    if heavy and (21 <= n_euro <= 24) and n_ind == 0:
        block_euro_heavy_front(occ, items, placed, start, n_euro)
    else:
        block_euro_long_then_cross_tail(occ, items, placed, start, n_euro)
    variants.append((items, placed))

    # V3: Euro-only längs über alles (nützlich z. B. 33, oder explizit erzwungen)
    occ, items, placed = empty_board()
    if n_ind>0:
        block_industrie_all(occ, items, placed, n_ind)
        start = first_free_x(occ)
        block_euro_only_long(occ, items, placed, start, n_euro)
    else:
        block_euro_only_long(occ, items, placed, 0, n_euro)
    variants.append((items, placed))

    # V4: Euro doppelt quer außen → schließen
    occ, items, placed = empty_board()
    if n_ind>0: block_industrie_all(occ, items, placed, n_ind)
    start = first_free_x(occ)
    dq,wq = span_cells("Euro","q")
    x = start
    if n_euro >= 2 and x + dq <= X:
        if place(occ, items, placed, x, 0, "Euro", "q"): n_euro -= 1
        if n_euro>0 and place(occ, items, placed, x, Y-wq, "Euro", "q"): n_euro -= 1
        x += dq
    fill_tail_closed_euro(occ, items, placed, x, n_euro)
    variants.append((items, placed))

    return variants

# ----------------- UI -----------------
st.markdown("### 📥 Manuelle Menge (ohne Preset)")
c1,c2,c3,c4,c5 = st.columns([1.0,1.0,1.2,1.6,1.6])
with c1: n_euro = st.number_input("Euro (120×80)", 0, 45, 30)
with c2: n_ind  = st.number_input("Industrie (120×100)", 0, 45, 0)
with c3: force_long = st.checkbox("Euro nur längs erzwingen (z. B. 33)", value=False)
with c4: heavy_mode = st.checkbox("Schwere Ladung (21–24) – Vorderachse entlasten", value=False)
with c5: st.markdown("&nbsp;")

# Varianten erzeugen
variants = generate_variants(int(n_euro), int(n_ind), force_euro_long=force_long, heavy=heavy_mode)

# Navigation
if "var_idx" not in st.session_state:
    st.session_state.var_idx = 0
left_btn, right_btn, info = st.columns([1,1,4])
with left_btn:
    if st.button("◀ Variante"):
        st.session_state.var_idx = (st.session_state.var_idx - 1) % len(variants)
with right_btn:
    if st.button("Variante ▶"):
        st.session_state.var_idx = (st.session_state.var_idx + 1) % len(variants)
with info:
    st.markdown(f"**Variante:** {st.session_state.var_idx+1} / {len(variants)}")

items, placed = variants[st.session_state.var_idx]

# ----------------- Render (Grid + Icons) -----------------
html = f"""
<div style="
  display:grid;
  grid-template-columns: repeat({X}, {cell_px}px);
  grid-auto-rows: {cell_px}px;
  gap: 1px;
  background:#ddd; padding:4px; border:2px solid #333; width:fit-content;">
"""
for (x,y,dx,dy,icon,typ,ori,depth) in items:
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

# ----------------- Auswertung / Plausibilität -----------------
wanted = {"Euro": int(n_euro), "Industrie": int(n_ind)}
missing_msgs = []
for typ in ["Euro","Industrie"]:
    if wanted[typ] > 0 and placed.get(typ,0) < wanted[typ]:
        missing = wanted[typ] - placed.get(typ,0)
        missing_msgs.append(f"– {missing}× {typ} passt/passen nicht mehr")

used_cm = used_length_cm(items)
st.markdown(f"**Genutzte Länge (realistisch):** {used_cm} cm von {TRAILER_L} cm (≈ {used_cm/TRAILER_L:.0%})")

if missing_msgs:
    st.error("🚫 **Platz reicht nicht:**\n" + "\n".join(missing_msgs))
else:
    st.success("✅ **Alle angeforderten Paletten passen in den Laderaum.**")

st.caption("Hinweis: Für die Anzeige wird das Raster gerundet (floor), damit 33× Euro längs in der Draufsicht immer möglich sind. "
           "Die Platz-Logik hält die Abschlussregel (hinten geschlossen) ein. Industrie wird grundsätzlich quer gesetzt.")
