# app.py
# Paletten Fuchs – Grafik ONLY (keine Unicode-Zeilen)
# - Clean-Ansicht mit Preset-Auswahl
# - Vergleich (Tabs) 33 / 32 / 31 / 24
# - Rechteck-Draufsicht im echten Maßstab (1360 x 240 cm)

from typing import List, Dict
import streamlit as st

st.set_page_config(page_title="Paletten Fuchs – Grafik", layout="centered")

# ---- Geometrie ----
TRAILER_LEN_CM = 1360
TRAILER_W_CM   = 240
EURO_L_CM, EURO_W_CM = 120, 80

# ---- Datenbausteine (wie Clean) ----
def euro_row_long() -> Dict:
    return {"type":"EURO_3_LONG","len_cm":EURO_L_CM,"pallets":3}

def euro_row_trans2() -> Dict:
    return {"type":"EURO_2_TRANS","len_cm":EURO_W_CM,"pallets":2}

def euro_row_trans1() -> Dict:
    return {"type":"EURO_1_TRANS","len_cm":EURO_W_CM,"pallets":1}

def cap_to_trailer(rows: List[Dict]) -> List[Dict]:
    out, s = [], 0
    for r in rows:
        if s + r["len_cm"] > TRAILER_LEN_CM: break
        out.append(r); s += r["len_cm"]
    return out

def layout_for_preset_euro(n: int, singles_front: int = 0) -> List[Dict]:
    rows: List[Dict] = []
    remaining = n

    # 1) 0/1/2 Einzel-quer vorne
    for _ in range(min(singles_front, remaining)):
        rows.append(euro_row_trans1()); remaining -= 1

    # 2) 2-quer, falls (rest-2)%3==0
    if remaining >= 2 and (remaining - 2) % 3 == 0:
        rows.append(euro_row_trans2()); remaining -= 2

    # 3) wenn Rest nicht teilbar, Singles zurücknehmen bis teilbar
    while remaining % 3 != 0 and any(r["type"]=="EURO_1_TRANS" for r in rows):
        for i, r in enumerate(rows):
            if r["type"]=="EURO_1_TRANS":
                rows.pop(i); remaining += 1; break

    # 4) Rest mit 3-längs
    if remaining > 0:
        rows += [euro_row_long() for _ in range(remaining // 3)]

    # 5) Absicherung
    if sum(r["pallets"] for r in rows) != n:
        if n >= 2 and (n - 2) % 3 == 0:
            rows = [euro_row_trans2()] + [euro_row_long() for _ in range((n-2)//3)]
        else:
            rows = [euro_row_long() for _ in range(n // 3)]
            rest = n % 3
            if rest == 2: rows.insert(0, euro_row_trans2())
            elif rest == 1: rows.insert(0, euro_row_trans1())
    return rows

# ---- Grafik (matplotlib) ----
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

COLOR_LONG = "#d9f2d9"   # Euro längs (hellgrün)
COLOR_TRANS = "#cfe8ff"  # Euro quer (hellblau)
EDGE = "#4a4a4a"

def _rows_to_rects(rows: List[Dict]) -> list:
    rects = []
    x = 0
    for r in rows:
        t = r["type"]
        if t == "EURO_3_LONG":
            w, h = 120, 80
            for lane in range(3):     # y = 0, 80, 160
                rects.append((x, lane*80, w, h, COLOR_LONG))
            x += 120
        elif t == "EURO_2_TRANS":
            w, h = 80, 120
            for lane in range(2):     # y = 0, 120
                rects.append((x, lane*120, w, h, COLOR_TRANS))
            x += 80
        elif t == "EURO_1_TRANS":
            w, h = 80, 120
            rects.append((x, 60, w, h, COLOR_TRANS))  # mittig
            x += 80
    return rects

def draw_graph(title: str, rows: List[Dict], figsize=(8,1.7)):
    rects = _rows_to_rects(rows)
    fig, ax = plt.subplots(figsize=figsize)

    # Trailer
    ax.add_patch(Rectangle((0, 0), TRAILER_LEN_CM, TRAILER_W_CM,
                           fill=False, linewidth=2, edgecolor="#333333"))

    # Paletten
    for (x, y, w, h, c) in rects:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=c, edgecolor=EDGE, linewidth=0.8))

    ax.set_xlim(0, TRAILER_LEN_CM)
    ax.set_ylim(0, TRAILER_W_CM)
    ax.set_aspect('equal'); ax.axis('off')
    ax.set_title(title, fontsize=12, pad=6)
    st.pyplot(fig); plt.close(fig)

# ---- UI ----
st.title("🦊 Paletten Fuchs – Grafik")

mode = st.sidebar.radio("Ansicht wählen", ["Normaler Modus (Clean)", "Vergleich (Tabs)"], index=0)

if mode == "Normaler Modus (Clean)":
    st.subheader("Clean-Ansicht (Grafik)")

    preset = st.radio(
        "Preset",
        ["33 Euro", "32 Euro (2× Einzel quer vorne)", "31 Euro (1× Einzel quer vorne)",
         "30 Euro", "29 Euro", "28 Euro", "27 Euro", "26 Euro", "25 Euro", "24 Euro",
         "Benutzerdefiniert"],
        index=0
    )

    if preset == "Benutzerdefiniert":
        target_n = st.number_input("Ziel: Anzahl Euro-Paletten", min_value=1, max_value=40, value=33, step=1)
        singles_front = st.slider("Einzel-quer vorne (0/1/2)", 0, 2, 0)
        rows = cap_to_trailer(layout_for_preset_euro(target_n, singles_front=singles_front))
        title = f"{target_n} Euro (Singles vorne: {singles_front})"
    elif preset == "24 Euro":
        rows = cap_to_trailer([euro_row_trans2() for _ in range(6)] + [euro_row_long() for _ in range(5)])
        title = "24 Euro (6× 2 quer + 5× 3 längs)"
    else:
        mapping = {
            "33 Euro": (33, 0),
            "32 Euro (2× Einzel quer vorne)": (32, 2),
            "31 Euro (1× Einzel quer vorne)": (31, 1),
            "30 Euro": (30, 0),
            "29 Euro": (29, 0),
            "28 Euro": (28, 0),
            "27 Euro": (27, 0),
            "26 Euro": (26, 0),
            "25 Euro": (25, 0),
        }
        n, s = mapping[preset]
        rows = cap_to_trailer(layout_for_preset_euro(n, singles_front=s))
        title = preset

    draw_graph(title, rows)

else:
    st.subheader("Vergleich (Tabs) – reine Grafik")

    tab33, tab32, tab31, tab24 = st.tabs(
        ["33 Euro", "32 Euro (2× Einzel quer)", "31 Euro (1× Einzel quer)", "24 Euro"]
    )

    with tab33:
        rows_33 = cap_to_trailer(layout_for_preset_euro(33, singles_front=0))
        draw_graph("33 Euro", rows_33)

    with tab32:
        rows_32 = cap_to_trailer(layout_for_preset_euro(32, singles_front=2))
        draw_graph("32 Euro (2× Einzel quer vorne)", rows_32)

    with tab31:
        rows_31 = cap_to_trailer(layout_for_preset_euro(31, singles_front=1))
        draw_graph("31 Euro (1× Einzel quer vorne)", rows_31)

    with tab24:
        rows_24 = cap_to_trailer([euro_row_trans2() for _ in range(6)] + [euro_row_long() for _ in range(5)])
        draw_graph("24 Euro (6× 2 quer + 5× 3 längs)", rows_24)

st.caption("Grafische Draufsicht im Maßstab 1360×240 cm. Grün = 3× Euro längs, Blau = Euro quer (2er/Einzel).")
