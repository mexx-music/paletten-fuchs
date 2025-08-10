# app.py
# Paletten Fuchs – Clean + Vergleich (Tabs)
# - Clean-Ansicht mit Preset-Auswahl (Euro)
# - Vergleichsfenster mit Tabs: 33 / 32 / 31 / 24
# - Unicode: ▮ (längs), ▬ (quer 2er), ▭ (Einzel quer), ⬜ (Industrie Platzhalter)
# - Raster: 25 Blöcke über 13,60 m, Blockbreite = 1 Zeichen

from typing import List, Dict, Tuple
import streamlit as st

st.set_page_config(page_title="Paletten Fuchs – Clean & Vergleich", layout="centered")

# --- Geometrie / Raster ---
TRAILER_LEN_CM = 1360
EURO_L_CM, EURO_W_CM = 120, 80
LENGTH_RASTER = 25
CHARS_PER_BLOCK = 1
CM_PER_RASTER = TRAILER_LEN_CM / LENGTH_RASTER  # ≈54.4 cm/Block

# --- Unicode-Symbole ---
SYM_EURO_LONG   = "▮"   # 3 Euro längs (120 cm)
SYM_EURO_TRANS2 = "▬"   # 2 Euro quer  (80 cm)
SYM_EURO_TRANS1 = "▭"   # 1 Euro quer  (80 cm, Einzel)
SYM_INDUSTRY    = "⬜"   # Industrie (Platzhalter)

# ---------- Bausteine ----------
def blocks(n: int, symbol: str) -> str:
    return symbol * (n * CHARS_PER_BLOCK)

def cm_to_raster(cm: int) -> int:
    if abs(cm - 80)  < 1e-6: return 1
    if abs(cm - 120) < 1e-6: return 2
    return max(1, round(cm / CM_PER_RASTER))

def euro_row_long() -> Dict:
    return {"type": "EURO_3_LONG", "len_cm": EURO_L_CM, "pallets": 3, "sym": SYM_EURO_LONG}

def euro_row_trans2() -> Dict:
    return {"type": "EURO_2_TRANS", "len_cm": EURO_W_CM, "pallets": 2, "sym": SYM_EURO_TRANS2}

def euro_row_trans1() -> Dict:
    return {"type": "EURO_1_TRANS", "len_cm": EURO_W_CM, "pallets": 1, "sym": SYM_EURO_TRANS1}

def cap_to_trailer(rows: List[Dict]) -> List[Dict]:
    out, s = [], 0
    for r in rows:
        if s + r['len_cm'] > TRAILER_LEN_CM: break
        out.append(r); s += r['len_cm']
    return out

def layout_for_preset_euro(n: int, singles_front: int = 0) -> List[Dict]:
    rows: List[Dict] = []
    remaining = n
    # 1) 1/2 Einzel-quer vorne
    for _ in range(min(singles_front, remaining)):
        rows.append(euro_row_trans1()); remaining -= 1
    # 2) 2-quer, wenn (rest-2)%3==0
    if remaining >= 2 and (remaining - 2) % 3 == 0:
        rows.append(euro_row_trans2()); remaining -= 2
    # 3) falls Rest nicht durch 3 teilbar, Singles wieder entfernen
    while remaining % 3 != 0 and any(r['type']=="EURO_1_TRANS" for r in rows):
        for i, r in enumerate(rows):
            if r['type']=="EURO_1_TRANS":
                rows.pop(i); remaining += 1; break
    # 4) mit 3-längs auffüllen
    rows += [euro_row_long() for _ in range(max(0, remaining)//3)]
    # 5) Fallback, falls Zählung nicht exakt passt
    if sum(r['pallets'] for r in rows) != n:
        if n >= 2 and (n - 2) % 3 == 0:
            rows = [euro_row_trans2()] + [euro_row_long() for _ in range((n-2)//3)]
        else:
            rows = [euro_row_long() for _ in range(n // 3)]
            rest = n % 3
            if rest == 2: rows.insert(0, euro_row_trans2())
            elif rest == 1: rows.insert(0, euro_row_trans1())
    return rows

def render_rows(rows: List[Dict], length_limit_cm: int = TRAILER_LEN_CM) -> Tuple[str, int]:
    out, used_cm = [], 0
    for r in rows:
        if used_cm + r['len_cm'] > length_limit_cm:
            break
        fill_blocks = cm_to_raster(r['len_cm'])
        line = blocks(fill_blocks, r['sym'])
        pad_blocks = LENGTH_RASTER - fill_blocks
        if pad_blocks > 0:
            line += " " * (pad_blocks * CHARS_PER_BLOCK)
        out.append(line)
        used_cm += r['len_cm']
    return "\n".join(out), used_cm

def render_variant(title: str, rows: List[Dict]):
    text, used = render_rows(rows)
    st.markdown(f"**{title}** — genutzte Länge: {used} cm / {TRAILER_LEN_CM} cm  |  Reihen: {len(rows)}")
    st.code(text, language=None)

# ---------- UI ----------
st.title("🦊 Paletten Fuchs – Clean & Vergleich")

mode = st.sidebar.radio("Ansicht wählen", ["Clean-Ansicht", "Vergleich (Tabs)"], index=0)

if mode == "Clean-Ansicht":
    st.subheader("Clean-Ansicht (Euro-Paletten)")

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
            "24 Euro": (24, 0),
        }
        target_n, singles_front = mapping[preset]

    if preset == "24 Euro":
        # Dein fixes Muster
        rows = cap_to_trailer([euro_row_trans2() for _ in range(6)] + [euro_row_long() for _ in range(5)])
    else:
        rows = cap_to_trailer(layout_for_preset_euro(target_n, singles_front=singles_front))

    render_variant(preset, rows)

else:
    st.subheader("Vergleichsfenster (Tabs)")
    tab33, tab32, tab31, tab24, tabAll = st.tabs(
        ["33 Euro", "32 Euro (2× Einzel quer)", "31 Euro (1× Einzel quer)", "24 Euro", "Alle untereinander"]
    )

    with tab33:
        rows_33 = cap_to_trailer(layout_for_preset_euro(33, singles_front=0))
        render_variant("33 Euro", rows_33)

    with tab32:
        rows_32 = cap_to_trailer(layout_for_preset_euro(32, singles_front=2))
        render_variant("32 Euro (2× Einzel quer vorne)", rows_32)

    with tab31:
        rows_31 = cap_to_trailer(layout_for_preset_euro(31, singles_front=1))
        render_variant("31 Euro (1× Einzel quer vorne)", rows_31)

    with tab24:
        rows_24 = cap_to_trailer([euro_row_trans2() for _ in range(6)] + [euro_row_long() for _ in range(5)])
        render_variant("24 Euro (6× 2 quer + 5× 3 längs)", rows_24)

    with tabAll:
        rows_33 = cap_to_trailer(layout_for_preset_euro(33, singles_front=0))
        rows_32 = cap_to_trailer(layout_for_preset_euro(32, singles_front=2))
        rows_31 = cap_to_trailer(layout_for_preset_euro(31, singles_front=1))
        rows_24 = cap_to_trailer([euro_row_trans2() for _ in range(6)] + [euro_row_long() for _ in range(5)])

        st.markdown("**33 Euro**"); st.code(render_rows(rows_33)[0], language=None)
        st.markdown("**32 Euro (2× Einzel quer vorne)**"); st.code(render_rows(rows_32)[0], language=None)
        st.markdown("**31 Euro (1× Einzel quer vorne)**"); st.code(render_rows(rows_31)[0], language=None)
        st.markdown("**24 Euro (6× 2 quer + 5× 3 längs)**"); st.code(render_rows(rows_24)[0], language=None)

st.caption("Zeichen: ▮ (längs), ▬ (quer 2er-Reihe), ▭ (Einzel quer), ⬜ (Industrie – später). Raster: 25, Blockbreite: 1.")
