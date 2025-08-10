# pal_fuchs_9_clean.py
# Paletten Fuchs – Vier Varianten nebeneinander (33 / 32 / 31 / 24)
# - Unicode/Monospace-Rendering
# - Feste Rasterung: 25 Längsblöcke, 4 Zeichen je Block
# - Presets fix parallel sichtbar: 33, 32 (2x Einzel quer), 31 (1x Einzel quer), 24
# - Sauberer Abschluss & stabile Darstellung

import streamlit as st
from typing import List, Dict

# -----------------------------
# Konstanten & Grundeinstellungen
# -----------------------------
st.set_page_config(page_title="Paletten Fuchs – 4 Varianten", layout="wide")

TRAILER_LEN_CM = 1360         # Kühlsattel Standard
TRAILER_WIDTH_CM = 240
EURO_L_CM, EURO_W_CM = 120, 80

LENGTH_RASTER = 25            # 25 Rasterspalten über 13,60 m
CHARS_PER_BLOCK = 4           # 4 Zeichen je Rasterblock
CM_PER_RASTER = TRAILER_LEN_CM / LENGTH_RASTER  # ≈54.4 cm

# Unicode-Symbole (monospace-tauglich)
SYM_EURO_LONG   = "▮"  # 3 Euro längs (Reihenlänge 120 cm)
SYM_EURO_TRANS2 = "▬"  # 2 Euro quer (Reihenlänge 80 cm)
SYM_EURO_TRANS1 = "▭"  # 1 Euro quer (Einzel, 80 cm)

# -----------------------------
# Hilfsfunktionen
# -----------------------------
def blocks(n: int, symbol: str) -> str:
    return (symbol * CHARS_PER_BLOCK) * n

def cm_to_raster(cm: int) -> int:
    # Visuelle Rasterung: 80 cm -> ~1 Block, 120 cm -> ~2 Blöcke
    # Für stabile Optik runden wir: 80 cm -> 1, 120 cm -> 2
    # Allgemein:
    ratio = cm / CM_PER_RASTER
    if abs(cm - 80) < 1e-6:
        return 1
    if abs(cm - 120) < 1e-6:
        return 2
    return max(1, round(ratio))

def render_rows(rows: List[Dict], length_limit_cm: int = TRAILER_LEN_CM) -> (str, int):
    out = []
    used_cm = 0
    for r in rows:
        if used_cm + r['len_cm'] > length_limit_cm:
            break
        fill_raster = cm_to_raster(r['len_cm'])
        line = blocks(fill_raster, r['sym'])
        # rechts auffüllen, damit jede Zeile exakt gleich breit ist
        pad_raster = LENGTH_RASTER - fill_raster
        if pad_raster > 0:
            line += " " * (pad_raster * CHARS_PER_BLOCK)
        if r.get('label'):
            line += f"   | {r['label']}"
        out.append(line)
        used_cm += r['len_cm']
    return "\n".join(out), used_cm

def euro_row_long() -> Dict:
    return {"type": "EURO_3_LONG", "len_cm": EURO_L_CM, "pallets": 3, "sym": SYM_EURO_LONG}

def euro_row_trans2() -> Dict:
    return {"type": "EURO_2_TRANS", "len_cm": EURO_W_CM, "pallets": 2, "sym": SYM_EURO_TRANS2}

def euro_row_trans1(label: str = "Mitte") -> Dict:
    return {"type": "EURO_1_TRANS", "len_cm": EURO_W_CM, "pallets": 1, "sym": SYM_EURO_TRANS1, "label": f"Einzel quer: {label}"}

def layout_for_preset_euro(n: int, singles_front: int = 0) -> List[Dict]:
    """
    Erzeuge Reihen für N Euro-Paletten.
    - singles_front: 0/1/2 Einzel-quer vorne (je 1 Palette, 80 cm)
    - danach ggf. eine 2-quer-Reihe (2 Paletten), falls (rest-2)%3==0
    - Rest mit 3-längs-Reihen (3 Paletten, 120 cm)
    """
    rows: List[Dict] = []
    remaining = n

    # 1) 1/2 Einzel-quer vorne
    take = min(singles_front, remaining)
    for _ in range(take):
        rows.append(euro_row_trans1("Mitte"))
    remaining -= take

    # 2) Versuche 2-quer einzubauen, damit Rest durch 3 teilbar wird
    used_two = False
    if remaining >= 2 and (remaining - 2) % 3 == 0:
        rows.append(euro_row_trans2())
        remaining -= 2
        used_two = True

    # 3) Falls trotzdem nicht teilbar, Singles zurücknehmen
    while remaining % 3 != 0 and any(r['type'] == "EURO_1_TRANS" for r in rows):
        # entferne ein Single (von vorne)
        for idx, r in enumerate(rows):
            if r['type'] == "EURO_1_TRANS":
                rows.pop(idx)
                remaining += 1
                break

    # 4) Rest mit 3-längs-Reihen
    if remaining < 0:
        remaining = 0
    rows.extend(euro_row_long() for _ in range(remaining // 3))

    # 5) Sicherheits-Alternative, falls Palettenzahl nicht exakt passt
    if sum(r['pallets'] for r in rows) != n:
        if n >= 2 and (n - 2) % 3 == 0:
            rows = [euro_row_trans2()] + [euro_row_long() for _ in range((n - 2)//3)]
        else:
            # pure long fallback (wird in der Praxis für unsere Presets nicht gebraucht)
            rows = [euro_row_long() for _ in range(n // 3)]
            rest = n % 3
            if rest == 2:
                rows.insert(0, euro_row_trans2())
            elif rest == 1:
                rows.insert(0, euro_row_trans1("Mitte"))

    return rows

def total_used_length_cm(rows: List[Dict]) -> int:
    return sum(r['len_cm'] for r in rows)

def total_pallets(rows: List[Dict]) -> int:
    return sum(r['pallets'] for r in rows)

def render_variant(title: str, rows: List[Dict]):
    st.markdown(f"### {title}")
    text, used_cm = render_rows(rows, length_limit_cm=TRAILER_LEN_CM)
    st.markdown(f"```\n{text}\n```")
    # Längenbalken
    used_raster = cm_to_raster(used_cm)
    bar = blocks(used_raster, "▆")
    pad = " " * ((LENGTH_RASTER - used_raster) * CHARS_PER_BLOCK)
    st.markdown(f"```\n{bar}{pad}\n```")
    # Zusammenfassung
    t_long  = sum(1 for r in rows if r['type'] == "EURO_3_LONG")
    t_q2    = sum(1 for r in rows if r['type'] == "EURO_2_TRANS")
    t_q1    = sum(1 for r in rows if r['type'] == "EURO_1_TRANS")
    st.caption(
        f"Paletten: {total_pallets(rows)}  |  Genutzte Länge: {used_cm} cm / {TRAILER_LEN_CM} cm  |  "
        f"Reihen: {len(rows)}  –  3×längs: {t_long}, 2×quer: {t_q2}, 1×quer: {t_q1}"
    )

# -----------------------------
# UI – Vier Spalten nebeneinander
# -----------------------------
st.title("🦊 Paletten Fuchs – Vier Varianten nebeneinander")

# Vier feste Varianten vorbereiten
rows_33 = layout_for_preset_euro(33, singles_front=0)  # 33 Euro
rows_32 = layout_for_preset_euro(32, singles_front=2)  # 32 Euro (2x Einzel quer vorne)
rows_31 = layout_for_preset_euro(31, singles_front=1)  # 31 Euro (1x Einzel quer vorne)
# 24 Euro – dein Referenzmuster: 6×2 quer + 5×3 längs
rows_24 = [euro_row_trans2() for _ in range(6)] + [euro_row_long() for _ in range(5)]

# Harter Abschluss, falls eine Variante rechnerisch > 13,60 m (sollte hier nicht passieren)
def cap_to_trailer(rows: List[Dict]) -> List[Dict]:
    out = []
    s = 0
    for r in rows:
        if s + r['len_cm'] > TRAILER_LEN_CM:
            break
        out.append(r)
        s += r['len_cm']
    return out

rows_33 = cap_to_trailer(rows_33)
rows_32 = cap_to_trailer(rows_32)
rows_31 = cap_to_trailer(rows_31)
rows_24 = cap_to_trailer(rows_24)

# Vier Spalten rendern
c1, c2, c3, c4 = st.columns(4, gap="small")
with c1:
    render_variant("33 Euro", rows_33)
with c2:
    render_variant("32 Euro (2× Einzel quer vorne)", rows_32)
with c3:
    render_variant("31 Euro (1× Einzel quer vorne)", rows_31)
with c4:
    render_variant("24 Euro (6× 2 quer + 5× 3 längs)", rows_24)

st.caption(
    "Hinweis: Darstellung ist gerastert (25 Blöcke × 4 Zeichen). Berechnung erfolgt intern in cm. "
    "Für die 24er-Variante ist das gewünschte Muster fest vorgegeben (6×2 quer, 5×3 längs)."
)
