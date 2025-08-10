# pal_fuchs_9_clean_side_by_side.py
# Vier Varianten sicher nebeneinander durch "Text-Zusammenführung" in Monospace-Blöcken.
# - Garantiert side-by-side (auch wenn Streamlit-Spalten stacken)
# - Zwei Reihen: [33 | 32] und [31 | 24]
# - Screenshot-Modus: kleine Schrift, keine Labels/Meta

import streamlit as st
from typing import List, Dict, Tuple

st.set_page_config(page_title="Paletten Fuchs – Side-by-Side Fix", layout="wide")

# --- Optionen ---
screenshot_mode = st.toggle("📸 Screenshot‑Modus (kompakt)", value=True,
                            help="Kleinere Schrift, keine Labels; ideal für Screenshots.")
layout_choice = st.radio("Layout", ["2×2 kompakt", "1×4 sehr breit"], index=0, horizontal=True)

# Kompakte Schrift im Screenshot-Modus
if screenshot_mode:
    st.markdown("""
    <style>
      .block-container {max-width: 1600px; padding-top: 0.5rem;}
      pre, code {font-size: 10px; line-height: 1.05;}
    </style>
    """, unsafe_allow_html=True)

# --- Geometrie / Raster ---
TRAILER_LEN_CM = 1360
EURO_L_CM, EURO_W_CM = 120, 80

LENGTH_RASTER = 25
CHARS_PER_BLOCK = 4
CM_PER_RASTER = TRAILER_LEN_CM / LENGTH_RASTER  # ≈54.4

SYM_EURO_LONG   = "▮"  # 3 Euro längs
SYM_EURO_TRANS2 = "▬"  # 2 Euro quer
SYM_EURO_TRANS1 = "▭"  # 1 Euro quer

def blocks(n: int, symbol: str) -> str:
    return (symbol * CHARS_PER_BLOCK) * n

def cm_to_raster(cm: int) -> int:
    if abs(cm - 80) < 1e-6:  return 1
    if abs(cm - 120) < 1e-6: return 2
    return max(1, round(cm / CM_PER_RASTER))

def euro_row_long() -> Dict:
    return {"type": "EURO_3_LONG", "len_cm": EURO_L_CM, "pallets": 3, "sym": SYM_EURO_LONG}

def euro_row_trans2() -> Dict:
    return {"type": "EURO_2_TRANS", "len_cm": EURO_W_CM, "pallets": 2, "sym": SYM_EURO_TRANS2}

def euro_row_trans1(label: str = "") -> Dict:
    return {"type": "EURO_1_TRANS", "len_cm": EURO_W_CM, "pallets": 1, "sym": SYM_EURO_TRANS1, "label": label}

def render_rows(rows: List[Dict], length_limit_cm: int = TRAILER_LEN_CM, include_labels: bool = False) -> Tuple[str, int]:
    """
    Rendert monospaced Zeilen. Jede Zeile hat exakt LENGTH_RASTER*CHARS_PER_BLOCK Zeichen.
    include_labels=False -> keine Labels am Zeilenende (wichtig für exakt gleiche Breite).
    """
    out, used_cm = [], 0
    line_width_chars = LENGTH_RASTER * CHARS_PER_BLOCK
    for r in rows:
        if used_cm + r['len_cm'] > length_limit_cm:
            break
        fill_raster = cm_to_raster(r['len_cm'])
        line = blocks(fill_raster, r['sym'])
        pad_raster = LENGTH_RASTER - fill_raster
        if pad_raster > 0:
            line += " " * (pad_raster * CHARS_PER_BLOCK)

        # Keine Labels im Screenshot-Modus – sonst unterschiedliche Längen
        if include_labels and r.get("label"):
            # Kürzen/Anfügen, aber wir halten die Gesamtbreite ein:
            label = f" | {r['label']}"
            # trim, falls zu lang:
            max_label_len = max(0, line_width_chars - len(line))
            line = line + label[:max_label_len]
            # ggf. noch auffüllen
            if len(line) < line_width_chars:
                line += " " * (line_width_chars - len(line))
        else:
            # Safety: exakt line_width_chars
            if len(line) < line_width_chars:
                line += " " * (line_width_chars - len(line))
            elif len(line) > line_width_chars:
                line = line[:line_width_chars]

        out.append(line)
        used_cm += r['len_cm']
    return "\n".join(out), used_cm

def layout_for_preset_euro(n: int, singles_front: int = 0) -> List[Dict]:
    rows: List[Dict] = []
    remaining = n

    # 1) 1/2 Einzel-quer vorne
    take = min(singles_front, remaining)
    for _ in range(take):
        rows.append(euro_row_trans1())
    remaining -= take

    # 2) eine 2-quer-Reihe, wenn (rest-2)%3==0
    if remaining >= 2 and (remaining - 2) % 3 == 0:
        rows.append(euro_row_trans2())
        remaining -= 2

    # 3) falls immer noch nicht teilbar: Singles entfernen, bis teilbar
    while remaining % 3 != 0 and any(r['type'] == "EURO_1_TRANS" for r in rows):
        for idx, r in enumerate(rows):
            if r['type'] == "EURO_1_TRANS":
                rows.pop(idx)
                remaining += 1
                break

    # 4) mit 3-längs auffüllen
    if remaining < 0:
        remaining = 0
    rows.extend(euro_row_long() for _ in range(remaining // 3))

    # Absicherung, falls Anzahl nicht exakt passt
    if sum(r['pallets'] for r in rows) != n:
        if n >= 2 and (n - 2) % 3 == 0:
            rows = [euro_row_trans2()] + [euro_row_long() for _ in range((n - 2)//3)]
        else:
            rows = [euro_row_long() for _ in range(n // 3)]
            rest = n % 3
            if rest == 2:
                rows.insert(0, euro_row_trans2())
            elif rest == 1:
                rows.insert(0, euro_row_trans1())
    return rows

def cap_to_trailer(rows: List[Dict]) -> List[Dict]:
    out, s = [], 0
    for r in rows:
        if s + r['len_cm'] > TRAILER_LEN_CM:
            break
        out.append(r)
        s += r['len_cm']
    return out

def side_by_side_block(text_a: str, text_b: str, sep: str = "   │   ") -> str:
    """
    Kombiniert zwei monospaced Blöcke Zeile für Zeile nebeneinander.
    Beide Blöcke werden vorab auf gleiche Zeilenzahl mit Leerzeilen (exakte Breite) gepolstert.
    """
    lines_a = text_a.split("\n") if text_a else []
    lines_b = text_b.split("\n") if text_b else []
    # Zeilen auf gleiche Anzahl bringen
    max_lines = max(len(lines_a), len(lines_b))
    line_width = LENGTH_RASTER * CHARS_PER_BLOCK
    blank = " " * line_width
    while len(lines_a) < max_lines:
        lines_a.append(blank)
    while len(lines_b) < max_lines:
        lines_b.append(blank)
    # Zusammenführen
    combined = [la + sep + lb for la, lb in zip(lines_a, lines_b)]
    return "\n".join(combined)

def length_bar(cm_used: int) -> str:
    used_raster = cm_to_raster(cm_used)
    bar = blocks(used_raster, "▆")
    pad = " " * ((LENGTH_RASTER - used_raster) * CHARS_PER_BLOCK)
    return bar + pad

# --- Varianten berechnen ---
rows_33 = cap_to_trailer(layout_for_preset_euro(33, singles_front=0))
rows_32 = cap_to_trailer(layout_for_preset_euro(32, singles_front=2))
rows_31 = cap_to_trailer(layout_for_preset_euro(31, singles_front=1))
rows_24 = cap_to_trailer([euro_row_trans2() for _ in range(6)] + [euro_row_long() for _ in range(5)])

# Renders als Text (ohne Labels im Screenshot-Modus)
include_labels = not screenshot_mode
txt_33, used_33 = render_rows(rows_33, include_labels=include_labels)
txt_32, used_32 = render_rows(rows_32, include_labels=include_labels)
txt_31, used_31 = render_rows(rows_31, include_labels=include_labels)
txt_24, used_24 = render_rows(rows_24, include_labels=include_labels)

# --- Ausgabe ---
st.title("🦊 Paletten Fuchs – Vier Varianten nebeneinander (robust)")

if layout_choice == "2×2 kompakt":
    # Reihe 1: 33 | 32
    top = side_by_side_block(txt_33, txt_32)
    st.markdown(f"```\n{top}\n```")
    if not screenshot_mode:
        top_bar = side_by_side_block(length_bar(used_33), length_bar(used_32))
        st.markdown(f"```\n{top_bar}\n```")

    # Reihe 2: 31 | 24
    bottom = side_by_side_block(txt_31, txt_24)
    st.markdown(f"```\n{bottom}\n```")
    if not screenshot_mode:
        bottom_bar = side_by_side_block(length_bar(used_31), length_bar(used_24))
        st.markdown(f"```\n{bottom_bar}\n```")
else:
    # 1×4 sehr breit – alles in EINEM Block nebeneinander
    left = side_by_side_block(txt_33, txt_32)
    right = side_by_side_block(txt_31, txt_24)
    one_wide = side_by_side_block(left, right, sep=" │ ")
    st.markdown(f"```\n{one_wide}\n```")
    if not screenshot_mode:
        left_bar  = side_by_side_block(length_bar(used_33), length_bar(used_32))
        right_bar = side_by_side_block(length_bar(used_31), length_bar(used_24))
        one_bar   = side_by_side_block(left_bar, right_bar, sep=" │ ")
        st.markdown(f"```\n{one_bar}\n```")

if not screenshot_mode:
    # Kurze Meta-Infos
    def meta(txt: str, used: int, title: str):
        st.write(f"**{title}** – Genutzte Länge: {used} cm / {TRAILER_LEN_CM} cm – Zeilen: {len(txt.splitlines())}")

    col = st.columns(4)
    with col[0]: meta(txt_33, used_33, "33 Euro")
    with col[1]: meta(txt_32, used_32, "32 Euro (2× Einzel quer)")
    with col[2]: meta(txt_31, used_31, "31 Euro (1× Einzel quer)")
    with col[3]: meta(txt_24, used_24, "24 Euro (6×2 quer + 5×3 längs)")

st.caption("Hinweis: Jede Zeile ist fest auf 25 Raster × 4 Zeichen. Die Side‑by‑Side‑Kombination ist ein einzelner Monospace‑Block, "
           "der horizontal scrollt – so bleibt es garantiert nebeneinander, auch auf iPad.")
