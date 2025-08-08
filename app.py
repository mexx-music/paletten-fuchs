import streamlit as st
from math import ceil

# ==============================
#  PAL Fuchs v7.2  –  Icon-Version
#  - Interne Physik auf festem 5‑cm-Raster (modellunabhängig vom UI-Raster)
#  - Euro 120×80, Industrie 120×100 (immer quer), Blumen 135×55
#  - Heckabschluss: 3× längs bevorzugt, sonst 2× quer
#  - Reale Nutzlänge in cm + "passt/passt nicht"
# ==============================

st.set_page_config(page_title="🦊 Paletten Fuchs v7.2 (Icons, exakt)", layout="wide")
st.title("📦 Paletten Fuchs – Sattelzug Ladeplan (Icons) v7.2")

# ---------- Trailer ----------
TRAILER_L, TRAILER_W = 1360, 245  # cm (13,6 m, 2,45 m)

# ---------- Anzeige-UI (nur View, nicht Physik) ----------
left, right = st.columns([1,1])
with left:
    st.subheader("⚡ Presets")
    preset = st.selectbox(
        "Schnellwahl",
        ["– manuell –", "Euro 30", "Euro 24 (schwer)", "Industrie 26", "Mix 21 Euro + 6 Industrie"],
        index=0
    )
with right:
    st.subheader("🔎 Anzeige")
    cell_cm = st.slider("Anzeige‑Raster (cm/Zelle)", 10, 50, 25, 5)
    cell_px = st.slider("Zellpixel (Zoom)", 6, 18, 10, 1)

st.caption(f"Anzeige: Breite = {TRAILER_W//cell_cm} Zellen, Länge = {TRAILER_L//cell_cm} Zellen • 1 Zelle = {cell_cm} cm")

# ---------- Icons ----------
ICON = {
    ("Euro","l"): "icons/euro_l.png",
    ("Euro","q"): "icons/euro_q.png",
    ("Industrie","q"): "icons/ind_q.png",
    ("Blume","l"): "icons/flower_l.png",
    ("Blume","q"): "icons/flower_q.png",
}

# ---------- Feste interne Physik (5‑cm-Raster) ----------
INTERNAL_CM = 5                                     # 1 interne Zelle = 5 cm
GX, GY = TRAILER_L // INTERNAL_CM, TRAILER_W // INTERNAL_CM  # interne Zellen

# Interner Zustand
# occ: belegte interne Zellen; items: platzierte Objekte in internen Koordinaten
# items‑Eintrag: (x, y, dx, dy, icon, typ, depth_cm)
occ = [[False]*GX for _ in range(GY)]
items = []
placed = {"Euro": 0, "Industrie": 0, "Blume": 0}

def reset_board():
    global occ, items, placed
    occ = [[False]*GX for _ in range(GY)]
    items = []
    placed = {"Euro": 0, "Industrie": 0, "Blume": 0}

# Maße → interne Spans (ceil!)
def span_int(name, ori):
    if name == "Euro":        L, B = 120, 80
    elif name == "Industrie": L, B = 120, 100
    else:                     L, B = 135, 55  # Blumenwagen
    if name == "Industrie":
        ori = "q"  # Regel: Industrie immer quer
    depth_cm, width_cm = (B, L) if ori == "q" else (L, B)
    dx = ceil(depth_cm / INTERNAL_CM)   # interne Zellen entlang LÄNGE
    dy = ceil(width_cm  / INTERNAL_CM)  # interne Zellen quer (BREITE)
    return dx, dy, depth_cm, width_cm

def free_int(x, y, dx, dy):
    if x < 0 or y < 0 or x+dx > GX or y+dy > GY: return False
    for yy in range(y, y+dy):
        row = occ[yy]
        for xx in range(x, x+dx):
            if row[xx]:
                return False
    return True

def place_int(x, y, dx, dy, icon, typ, depth_cm):
    for yy in range(y, y+dy):
        row = occ[yy]
        for xx in range(x, x+dx):
            row[xx] = True
    items.append((x, y, dx, dy, icon, typ, depth_cm))
    placed[typ] += 1

def center_y_int(dy):
    return max(0, (GY - dy) // 2)

def first_free_x_int():
    for xx in range(GX):
        if any(not occ[yy][xx] for yy in range(GY)):
            return xx
    return GX

def used_length_cm():
    if not items: return 0
    x_end_int = max(x + dx for (x, y, dx, dy, icon, typ, dcm) in items)
    return x_end_int * INTERNAL_CM

# ---------- Heck-Abschluss (Euro): 3× längs bevorzugt, sonst 2× quer ----------
def fill_tail_closed_euro(x_start_int, euro_left):
    if euro_left <= 0: return
    dq, wq, depth_q, _ = span_int("Euro", "q")
    dl, wl, depth_l, _ = span_int("Euro", "l")

    if euro_left % 3 == 0 or euro_left < 2:
        cols_long = euro_left // 3
        need_tail_q = False
    else:
        cols_long = max(0, (euro_left - 2) // 3)
        need_tail_q = True

    lanes = [0, center_y_int(wl), GY - wl]
    x = x_start_int

    # 3er‑Längsreihen
    for _ in range(cols_long):
        if x + dl > GX: break
        for y in lanes:
            if free_int(x, y, dl, wl):
                place_int(x, y, dl, wl, ICON[("Euro", "l")], "Euro", depth_cm=120)
        x += dl

    # 2× Querabschluss (oben & unten)
    if need_tail_q and x + dq <= GX:
        if free_int(x, 0, dq, wq):
            place_int(x, 0, dq, wq, ICON[("Euro", "q")], "Euro", depth_cm=80)
        if free_int(x, GY - wq, dq, wq):
            place_int(x, GY - wq, dq, wq, ICON[("Euro", "q")], "Euro", depth_cm=80)

# ---------- Layouts (interne Physik verwenden) ----------
def industrie_all(n):
    dq, wq, depth_q, _ = span_int("Industrie", "q")
    x = 0
    # ungerade → 1 mittig
    if n % 2 == 1:
        y = center_y_int(wq)
        if free_int(x, y, dq, wq):
            place_int(x, y, dq, wq, ICON[("Industrie", "q")], "Industrie", depth_cm=100)
            n -= 1
            x += dq
    # Paare links+rechts
    while n > 0 and x + dq <= GX:
        for y in [0, GY - wq]:
            if n > 0 and free_int(x, y, dq, wq):
                place_int(x, y, dq, wq, ICON[("Industrie", "q")], "Industrie", depth_cm=100)
                n -= 1
        x += dq

def euro_30(n):
    reset_board()
    dq, wq, depth_q, _ = span_int("Euro", "q")
    x = 0
    # 1 quer mittig
    if n > 0:
        y = center_y_int(wq)
        if free_int(x, y, dq, wq):
            place_int(x, y, dq, wq, ICON[("Euro", "q")], "Euro", depth_cm=80)
            n -= 1
    x += dq
    # 2 quer außen
    for y in [0, GY - wq]:
        if n > 0 and free_int(x, y, dq, wq):
            place_int(x, y, dq, wq, ICON[("Euro", "q")], "Euro", depth_cm=80)
            n -= 1
    x += dq
    # Rest: geschlossenes Heck
    fill_tail_closed_euro(x, n)

def euro_24(n):
    reset_board()
    dq, wq, depth_q, _ = span_int("Euro", "q")
    x = 0
    yC = center_y_int(wq)
    # 2× einzeln quer mittig
    for _ in range(min(2, n)):
        if free_int(x, yC, dq, wq):
            place_int(x, yC, dq, wq, ICON[("Euro", "q")], "Euro", depth_cm=80)
            n -= 1
            x += dq
    # 2× doppelt quer (links+rechts)
    for _ in range(2):
        if n <= 0: break
        for y in [0, GY - wq]:
            if n > 0 and free_int(x, y, dq, wq):
                place_int(x, y, dq, wq, ICON[("Euro", "q")], "Euro", depth_cm=80)
                n -= 1
        x += dq
    # 1× einzel quer mittig
    if n > 0 and free_int(x, yC, dq, wq):
        place_int(x, yC, dq, wq, ICON[("Euro", "q")], "Euro", depth_cm=80)
        n -= 1
        x += dq
    # Rest: geschlossen
    fill_tail_closed_euro(x, n)

def euro_rows_from(x_start_int, n):
    dl, wl, depth_l, _ = span_int("Euro", "l")
    x = x_start_int
    lanes = [0, center_y_int(wl), GY - wl]
    while n > 0 and x + dl <= GX:
        for y in lanes:
            if n > 0 and free_int(x, y, dl, wl):
                place_int(x, y, dl, wl, ICON[("Euro", "l")], "Euro", depth_cm=120)
                n -= 1
        x += dl

def mix_21_6():
    reset_board()
    # Industrie zuerst
    industrie_all(6)
    # Euro mit Hecklogik hinter erster freier Spalte
    start = first_free_x_int()
    dq, wq, depth_q, _ = span_int("Euro", "q")
    x = start
    rem = 21
    # 1 quer mittig
    if rem > 0 and x + dq <= GX and free_int(x, center_y_int(wq), dq, wq):
        place_int(x, center_y_int(wq), dq, wq, ICON[("Euro", "q")], "Euro", depth_cm=80)
        rem -= 1
        x += dq
    # 2 quer außen
    if rem >= 2 and x + dq <= GX:
        for y in [0, GY - wq]:
            if rem > 0 and free_int(x, y, dq, wq):
                place_int(x, y, dq, wq, ICON[("Euro", "q")], "Euro", depth_cm=80)
                rem -= 1
        x += dq
    # Rest geschlossen
    fill_tail_closed_euro(x, rem)

# ---------- Eingabe (manuell) ----------
st.subheader("📥 Eingabe")
c1, c2, c3, c4 = st.columns([1.3, 1.3, 1.2, 1.6])
with c1: n_euro = st.number_input("Euro‑Paletten (120×80)", 0, 45, 0)
with c2: n_ind  = st.number_input("Industrie‑Paletten (120×100)", 0, 45, 0)
with c3: flowers = st.checkbox("🌼 Blumenwagen anzeigen", value=False)
with c4: n_flow = st.number_input("Blumenwagen (135×55)", 0, 60, 0, disabled=not flowers)

# ---------- Preset / Auto ----------
if preset != "– manuell –":
    if preset == "Euro 30": euro_30(30)
    elif preset == "Euro 24 (schwer)": euro_24(24)
    elif preset == "Industrie 26": reset_board(); industrie_all(26)
    elif preset == "Mix 21 Euro + 6 Industrie": mix_21_6()
else:
    reset_board()
    if n_ind > 0 and n_euro > 0:
        industrie_all(n_ind)
        start = first_free_x_int()
        dq, wq, _, _ = span_int("Euro", "q")
        x = start
        rem = n_euro
        # 1 quer mittig
        if rem > 0 and x + dq <= GX and free_int(x, center_y_int(wq), dq, wq):
            place_int(x, center_y_int(wq), dq, wq, ICON[("Euro", "q")], "Euro", depth_cm=80)
            rem -= 1
            x += dq
        # 2 quer außen
        if rem >= 2 and x + dq <= GX:
            for y in [0, GY - wq]:
                if rem > 0 and free_int(x, y, dq, wq):
                    place_int(x, y, dq, wq, ICON[("Euro", "q")], "Euro", depth_cm=80)
                    rem -= 1
            x += dq
        # Rest geschlossen
        fill_tail_closed_euro(x, rem)
    elif n_euro >= 30:
        euro_30(n_euro)
    elif n_euro >= 24:
        euro_24(n_euro)
    elif n_euro > 0:
        euro_rows_from(0, n_euro)
    elif n_ind > 0:
        industrie_all(n_ind)

# Blumen (Demo: 3 quer + 2 längs vorne)
if flowers and n_flow > 0:
    dq, wq, dq_cm, _ = span_int("Blume", "q")
    dl, wl, dl_cm, _ = span_int("Blume", "l")
    x = 0
    for i in range(min(3, n_flow)):
        y = [0, center_y_int(wq), GY - wq][i]
        if free_int(x, y, dq, wq):
            place_int(x, y, dq, wq, ICON[("Blume", "q")], "Blume", depth_cm=55)
    left = max(0, n_flow - 3); x += dq
    if left > 0 and free_int(x, 0, dl, wl):
        place_int(x, 0, dl, wl, ICON[("Blume", "l")], "Blume", depth_cm=135); left -= 1
    if left > 0 and free_int(x, GY - wl, dl, wl):
        place_int(x, GY - wl, dl, wl, ICON[("Blume", "l")], "Blume", depth_cm=135)

# ---------- Render (nur Mapping intern → Anzeige) ----------
st.subheader("🗺️ Ladeplan (Draufsicht, hinten = unten)")

def map_cells(n_int):  # interne 5‑cm‑Zellen → Anzeige‑Zellen
    return max(1, round(n_int * INTERNAL_CM / cell_cm))

disp_cols = TRAILER_L // cell_cm
disp_rows = TRAILER_W // cell_cm
html = f"""
<div style="
  display:grid;
  grid-template-columns: repeat({disp_cols}, {cell_px}px);
  grid-auto-rows:{cell_px}px;
  gap:1px;background:#ddd;padding:4px;border:2px solid #333;width:fit-content;">
"""
for (x,y,dx,dy,icon,typ,depth_cm) in items:
    gx = map_cells(x);    gsx = map_cells(dx)
    gy = map_cells(y);    gsy = map_cells(dy)
    html += f"""
    <div style="
      grid-column:{gx+1}/span {gsx};
      grid-row:{gy+1}/span {gsy};
      background:url('{icon}') center/contain no-repeat, #fafafa;
      border:1px solid #777;"></div>
    """
html += "</div>"
st.components.v1.html(html, height=min(560, (cell_px+1)*disp_rows+40), scrolling=False)

# ---------- Kapazitätsprüfung ----------
wanted_euro = n_euro if preset == "– manuell –" else {"Euro 30":30, "Euro 24 (schwer)":24, "Industrie 26":0, "Mix 21 Euro + 6 Industrie":21}[preset]
wanted_ind  = n_ind  if preset == "– manuell –" else {"Euro 30":0,  "Euro 24 (schwer)":0,  "Industrie 26":26, "Mix 21 Euro + 6 Industrie":6}[preset]

missing = []
if wanted_euro > placed["Euro"]:
    missing.append(f"– {wanted_euro - placed['Euro']}× Euro passen nicht")
if wanted_ind  > placed["Industrie"]:
    missing.append(f"– {wanted_ind  - placed['Industrie']}× Industrie passen nicht")

used_cm = used_length_cm()
st.markdown(f"**Genutzte Länge (real):** {used_cm} cm von {TRAILER_L} cm  (≈ {used_cm/TRAILER_L:.0%})")

if used_cm > TRAILER_L:
    st.error("🚫 **Platz reicht nicht (Länge):** Reale Nutzlänge überschreitet 13,6 m.")
elif missing:
    st.error("🚫 **Platz reicht nicht (Anzahl):**\n" + "\n".join(missing))
else:
    st.success("✅ **Alle angeforderten Paletten passen in den Laderaum.**")
