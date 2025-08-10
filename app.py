# app.py
# Paletten Fuchs – Clean + Grafik + Vergleich (Tabs) + Inline 2×2 Grid
# - Standard: große Rechteck-Grafik (keine Unicode-Zeilen)
# - Clean-Logik für Euro + optionale Industrie
# - Vergleich: 4 frei konfigurierbare Varianten (Tabs)
# - Inline 2×2: vier Varianten direkt im oberen Bereich per Toggle

from typing import List, Dict, Tuple
import streamlit as st

st.set_page_config(page_title="Paletten Fuchs – Grafik & Vergleich", layout="centered")

# ------------------ Geometrie / Konstanten ------------------
TRAILER_LEN_CM = 1360
TRAILER_W_CM   = 240
EURO_L_CM, EURO_W_CM = 120, 80
IND_L_CM,  IND_W_CM  = 120, 100

# ------------------ Basis-Layoutfunktionen (Euro/Industrie) ------------------
# Euro-Reihen
def euro_row_long() -> Dict:
    return {"type": "EURO_3_LONG", "len_cm": EURO_L_CM, "pallets": 3}

def euro_row_trans2() -> Dict:
    return {"type": "EURO_2_TRANS", "len_cm": EURO_W_CM, "pallets": 2}

def euro_row_trans1() -> Dict:
    return {"type": "EURO_1_TRANS", "len_cm": EURO_W_CM, "pallets": 1}

# Industrie – einfache Standardisierung (2 nebeneinander in Breite)
def ind_row2_long() -> Dict:
    return {"type": "IND_ROW_2_LONG", "len_cm": IND_L_CM, "pallets": 2}

def ind_single() -> Dict:
    return {"type": "IND_SINGLE", "len_cm": IND_L_CM, "pallets": 1}

# Auf Trailerlänge kappen
def cap_to_trailer(rows: List[Dict]) -> List[Dict]:
    out, s = [], 0
    for r in rows:
        L = r.get("len_cm", EURO_L_CM)
        if s + L > TRAILER_LEN_CM:
            break
        out.append(r)
        s += L
    return out

# Euro: n Paletten mit 0/1/2 Einzel-quer vorne, optionale 2-quer, Rest 3-längs
def layout_for_preset_euro(n: int, singles_front: int = 0) -> List[Dict]:
    rows: List[Dict] = []
    remaining = n

    # 1) Einzel-quer vorne (0/1/2)
    take = min(max(0, singles_front), 2, remaining)
    for _ in range(take):
        rows.append(euro_row_trans1())
    remaining -= take

    # 2) Eine 2-quer-Reihe, wenn (rest-2)%3==0
    if remaining >= 2 and (remaining - 2) % 3 == 0:
        rows.append(euro_row_trans2())
        remaining -= 2

    # 3) Falls Rest nicht teilbar, Singles zurücknehmen bis teilbar
    while remaining % 3 != 0 and any(r["type"] == "EURO_1_TRANS" for r in rows):
        for i, r in enumerate(rows):
            if r["type"] == "EURO_1_TRANS":
                rows.pop(i)
                remaining += 1
                break

    # 4) Mit 3-längs auffüllen
    if remaining > 0:
        rows += [euro_row_long() for _ in range(remaining // 3)]

    # 5) Absicherung
    if sum(r.get("pallets", 0) for r in rows) != n:
        if n >= 2 and (n - 2) % 3 == 0:
            rows = [euro_row_trans2()] + [euro_row_long() for _ in range((n - 2) // 3)]
        else:
            rows = [euro_row_long() for _ in range(n // 3)]
            rest = n % 3
            if rest == 2:
                rows.insert(0, euro_row_trans2())
            elif rest == 1:
                rows.insert(0, euro_row_trans1())
    return rows

# Industrie: einfache Standard-Logik (2 pro Reihe, optional 1 vorne)
def layout_for_preset_industry(n: int) -> List[Dict]:
    if n <= 0:
        return []
    full = n // 2
    single = n % 2
    rows: List[Dict] = []
    if single:
        rows.append(ind_single())       # 1 vorne
    rows += [ind_row2_long() for _ in range(full)]
    return rows

# ------------------ Grafik (matplotlib) ------------------
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

COLOR_EURO_LONG = "#d9f2d9"   # hellgrün
COLOR_EURO_QUER = "#cfe8ff"   # hellblau
COLOR_IND      = "#ffe2b3"    # hellorange
EDGE           = "#4a4a4a"

def rows_to_rects(rows: List[Dict]) -> list:
    """Wandelt Reihen in Rechtecke (x,y,w,h,color) um, echte cm-Maße."""
    rects = []
    x = 0
    for r in rows:
        t = r["type"]
        L = r["len_cm"]
        if t == "EURO_3_LONG":
            w, h = 120, 80
            for lane in range(3):               # y = 0, 80, 160
                rects.append((x, lane*80, w, h, COLOR_EURO_LONG))
            x += L
        elif t == "EURO_2_TRANS":
            w, h = 80, 120
            for lane in range(2):               # y = 0, 120
                rects.append((x, lane*120, w, h, COLOR_EURO_QUER))
            x += L
        elif t == "EURO_1_TRANS":
            w, h = 80, 120
            rects.append((x, 60, w, h, COLOR_EURO_QUER))  # mittig
            x += L
        elif t == "IND_ROW_2_LONG":
            w, h = 120, 100
            rects.append((x, 20,  w, h, COLOR_IND))       # y = 20, 120 -> 20 cm Luft je Seite
            rects.append((x, 120, w, h, COLOR_IND))
            x += L
        elif t == "IND_SINGLE":
            w, h = 120, 100
            rects.append((x, 70, w, h, COLOR_IND))        # mittig
            x += L
        else:
            # generischer Fallback
            rects.append((x, 80, L, 80, "#ddd"))
            x += L
    return rects

def draw_graph(title: str, rows: List[Dict], figsize=(8, 1.7)):
    rects = rows_to_rects(cap_to_trailer(rows))
    fig, ax = plt.subplots(figsize=figsize)

    # Trailer-Rahmen
    ax.add_patch(Rectangle((0, 0), TRAILER_LEN_CM, TRAILER_W_CM,
                           fill=False, linewidth=2, edgecolor="#333"))

    # Paletten
    for (x, y, w, h, c) in rects:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=c, edgecolor=EDGE, linewidth=0.8))

    ax.set_xlim(0, TRAILER_LEN_CM)
    ax.set_ylim(0, TRAILER_W_CM)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=12, pad=6)
    st.pyplot(fig)
    plt.close(fig)

# ------------------ Sidebar-Schalter ------------------
st.title("🦊 Paletten Fuchs – Grafik & Vergleich")

# Darstellung: Grafik (Standard). Textausgabe lassen wir weg (dein Wunsch: keine kleinen Zeichen)
INLINE_GRID_ON = st.sidebar.toggle("Vier Varianten (2×2) direkt oben", value=False,
                                   help="Aktivieren, um vier frei konfigurierbare Varianten gleich unter der Clean-Ansicht zu sehen.")
SHOW_TABS = st.sidebar.toggle("Vergleich (Tabs) anzeigen", value=True,
                              help="Vier frei konfigurierbare Varianten in Tabs.")

# ------------------ Clean-Ansicht (oben) ------------------
st.subheader("Clean-Ansicht (Grafik) – Euro + Industrie")

# Eingaben wie in deiner Clean-Version (flexibel, nichts fest verdrahtet)
c1, c2, c3 = st.columns(3)
with c1:
    euro_n = st.number_input("Euro-Paletten", 0, 40, 33, step=1)
with c2:
    singles_front = st.slider("Einzel-quer vorne (0/1/2)", 0, 2, 0)
with c3:
    ind_n = st.number_input("Industrie-Paletten", 0, 40, 0, step=1)

rows_clean: List[Dict] = []
if euro_n > 0:
    rows_clean += layout_for_preset_euro(euro_n, singles_front=singles_front)
if ind_n > 0:
    rows_clean += layout_for_preset_industry(ind_n)

draw_graph(f"Clean: {euro_n} Euro (Singles {singles_front}) + {ind_n} Industrie", rows_clean)

# ------------------ Inline 2×2 Vergleich (per Toggle) ------------------
def inline_four_variants_grid():
    st.markdown("#### Vier Varianten (2×2, kompakt)")
    def controls(idx: int):
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            e = st.number_input(f"Euro V{idx}", 0, 40, 0 if idx > 1 else 33, step=1, key=f"iv_e{idx}")
        with cc2:
            s = st.slider(f"Einzel V{idx}", 0, 2, 0, key=f"iv_s{idx}")
        with cc3:
            i = st.number_input(f"Industrie V{idx}", 0, 40, 0, step=1, key=f"iv_i{idx}")

        r: List[Dict] = []
        if e > 0:
            r += layout_for_preset_euro(e, singles_front=s)
        if i > 0:
            r += layout_for_preset_industry(i)
        title = f"V{idx}: {e} Euro (S{s}) + {i} Ind."
        return r, title

    r1, t1 = controls(1)
    r2, t2 = controls(2)
    r3, t3 = controls(3)
    r4, t4 = controls(4)

    figsz = (6.6, 1.25)
    row1 = st.columns(2, gap="small")
    with row1[0]: draw_graph(t1, r1, figsize=figsz)
    with row1[1]: draw_graph(t2, r2, figsize=figsz)
    row2 = st.columns(2, gap="small")
    with row2[0]: draw_graph(t3, r3, figsize=figsz)
    with row2[1]: draw_graph(t4, r4, figsize=figsz)

if INLINE_GRID_ON:
    inline_four_variants_grid()

# ------------------ Vergleich (Tabs) – 4 frei konfigurierbare Varianten ------------------
def compare_tabs_four_variants():
    st.subheader("Vergleich (Tabs) – 4 Varianten (frei konfigurierbar)")

    tab1, tab2, tab3, tab4 = st.tabs(["Variante 1", "Variante 2", "Variante 3", "Variante 4"])

    def var_ui(tab, idx: int, defaults=(33,0,0)):
        with tab:
            e = st.number_input(f"Euro (V{idx})", 0, 40, defaults[0], step=1, key=f"tv_e{idx}")
            s = st.slider(f"Einzel (V{idx})", 0, 2, defaults[1], key=f"tv_s{idx}")
            i = st.number_input(f"Industrie (V{idx})", 0, 40, defaults[2], step=1, key=f"tv_i{idx}")
            r: List[Dict] = []
            if e > 0:
                r += layout_for_preset_euro(e, singles_front=s)
            if i > 0:
                r += layout_for_preset_industry(i)
            draw_graph(f"V{idx}: {e} Euro (S{s}) + {i} Ind.", r)

    var_ui(tab1, 1, (33, 0, 0))
    var_ui(tab2, 2, (32, 2, 0))
    var_ui(tab3, 3, (31, 1, 0))
    var_ui(tab4, 4, (24, 0, 0))

if SHOW_TABS:
    compare_tabs_four_variants()

st.caption("Grafische Draufsicht im Maßstab 1360×240 cm. Farben: Grün = Euro längs, Blau = Euro quer, Orange = Industrie. "
           "Oben Clean‑Ansicht (frei konfigurierbar), darunter optional Inline‑2×2 und/oder Tabs‑Vergleich.")
