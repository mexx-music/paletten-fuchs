# pal_fuchs_9_vergleichsfenster.py
# Ein Fenster mit Tabs: 33 / 32 / 31 / 24 – je Tab Monospace-Render (st.code)

import streamlit as st
from typing import List, Dict, Tuple

st.set_page_config(page_title="Paletten Fuchs – Vergleichsfenster", layout="centered")

# --- Geometrie / Raster ---
TRAILER_LEN_CM = 1360
EURO_L_CM, EURO_W_CM = 120, 80
LENGTH_RASTER = 25          # 25 Längs-Raster über 13,60 m
CHARS_PER_BLOCK = 1         # 1 Zeichen pro Rasterblock (dein Wunsch)
CM_PER_RASTER = TRAILER_LEN_CM / LENGTH_RASTER  # ≈54.4 cm

# --- Unicode-Symbole ---
SYM_EURO_LONG   = "▮"   # 3 Euro längs (120 cm)
SYM_EURO_TRANS2 = "▬"   # 2 Euro quer  (80 cm)
SYM_EURO_TRANS1 = "▭"   # 1 Euro quer  (80 cm, Einzel)
SYM_INDUSTRY    = "⬜"   # Industrie (für später)

# --- Bausteine ---
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
    # 5) Fallback
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
    st.markdown(f"**{title}**  —  genutzte Länge: {used} cm / {TRAILER_LEN_CM} cm  |  Reihen: {len(rows)}")
    st.code(text, language=None)  # Monospace-Fenster mit Scroll + Copy-Button

# --- UI: Fenster mit Tabs ---
st.title("🦊 Paletten Fuchs – Vergleichsfenster")
with st.container(border=True):
    st.write("Alle Varianten in einem Fenster. Wechsle die Tabs und mach deine Screenshots.")

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
        # Alle vier untereinander im selben Fenster (ein Scrollbereich)
        rows_33 = cap_to_trailer(layout_for_preset_euro(33, singles_front=0))
        rows_32 = cap_to_trailer(layout_for_preset_euro(32, singles_front=2))
        rows_31 = cap_to_trailer(layout_for_preset_euro(31, singles_front=1))
        rows_24 = cap_to_trailer([euro_row_trans2() for _ in range(6)] + [euro_row_long() for _ in range(5)])

        st.markdown("**33 Euro**")
        st.code(render_rows(rows_33)[0], language=None)

        st.markdown("**32 Euro (2× Einzel quer vorne)**")
        st.code(render_rows(rows_32)[0], language=None)

        st.markdown("**31 Euro (1× Einzel quer vorne)**")
        st.code(render_rows(rows_31)[0], language=None)

        st.markdown("**24 Euro (6× 2 quer + 5× 3 längs)**")
        st.code(render_rows(rows_24)[0], language=None)

st.caption("Zeichen: ▮ (längs), ▬ (quer 2er-Reihe), ▭ (Einzel quer), ⬜ (Industrie – später). Blockbreite = 1, Raster = 25.")
