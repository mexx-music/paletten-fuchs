# pal_fuchs_9_side_by_side_html.py
# Vier Varianten garantiert nebeneinander (HTML-Flex) mit vereinbarten Unicode-Symbolen:
# Euro längs = ▮, Euro quer (2) = ▬, Euro quer (1) = ▭, Industrie = ⬜
# Blockbreite = 1 (kein "4er-Pack" mehr pro Rasterblock)

import streamlit as st
import html
from typing import List, Dict, Tuple

st.set_page_config(page_title="Paletten Fuchs – Side-by-Side (Unicode clean)", layout="wide")

# Optional kompaktere Schrift für bessere Übersicht
st.markdown("""
<style>
.block-container {max-width: 1600px; padding-top: 0.4rem;}
pre, code {font-size: 10px; line-height: 1.05;}
</style>
""", unsafe_allow_html=True)

# --- Geometrie / Raster ---
TRAILER_LEN_CM = 1360
EURO_L_CM, EURO_W_CM = 120, 80
LENGTH_RASTER = 25          # 25 Längs-Raster über 13,60 m
CHARS_PER_BLOCK = 1         # <-- WICHTIG: nur 1 Zeichen pro Rasterblock (kein 4er-Pack!)
CM_PER_RASTER = TRAILER_LEN_CM / LENGTH_RASTER  # ≈ 54.4 cm pro Raster

# --- Unicode-Symbole (vereinbart) ---
SYM_EURO_LONG   = "▮"   # 3 Euro längs (120 cm)
SYM_EURO_TRANS2 = "▬"   # 2 Euro quer  (80 cm)
SYM_EURO_TRANS1 = "▭"   # 1 Euro quer  (80 cm, Einzel)
SYM_INDUSTRY    = "⬜"   # Industrie (nur Platzhalter hier)

# --- Hilfsfunktionen ---
def blocks(n: int, symbol: str) -> str:
    # genau n Zeichen, jedes ein Symbol
    return symbol * (n * CHARS_PER_BLOCK)

def cm_to_raster(cm: int) -> int:
    # Stabil: 80 cm -> 1 Block, 120 cm -> 2 Blöcke
    if abs(cm - 80)  < 1e-6: return 1
    if abs(cm - 120) < 1e-6: return 2
    return max(1, round(cm / CM_PER_RASTER))

def euro_row_long() -> Dict:
    return {"type": "EURO_3_LONG", "len_cm": EURO_L_CM, "pallets": 3, "sym": SYM_EURO_LONG}

def euro_row_trans2() -> Dict:
    return {"type": "EURO_2_TRANS", "len_cm": EURO_W_CM, "pallets": 2, "sym": SYM_EURO_TRANS2}

def euro_row_trans1() -> Dict:
    return {"type": "EURO_1_TRANS", "len_cm": EURO_W_CM, "pallets": 1, "sym": SYM_EURO_TRANS1}

def render_rows(rows: List[Dict], length_limit_cm: int = TRAILER_LEN_CM) -> Tuple[str, int]:
    out, used_cm = [], 0
    line_width_blocks = LENGTH_RASTER
    for r in rows:
        if used_cm + r['len_cm'] > length_limit_cm:
            break
        fill_blocks = cm_to_raster(r['len_cm'])
        line = blocks(fill_blocks, r['sym'])
        pad_blocks = line_width_blocks - fill_blocks
        if pad_blocks > 0:
            line += " " * (pad_blocks * CHARS_PER_BLOCK)
        out.append(line)
        used_cm += r['len_cm']
    return "\n".join(out), used_cm

def layout_for_preset_euro(n: int, singles_front: int = 0) -> List[Dict]:
    rows: List[Dict] = []
    remaining = n

    # 1) 1/2 Einzel-quer vorne
    for _ in range(min(singles_front, remaining)):
        rows.append(euro_row_trans1()); remaining -= 1

    # 2) 2-quer, wenn Rest dadurch durch 3 teilbar wird
    if remaining >= 2 and (remaining - 2) % 3 == 0:
        rows.append(euro_row_trans2()); remaining -= 2

    # 3) falls Rest nicht durch 3 teilbar, Singles entfernen bis teilbar
    while remaining % 3 != 0 and any(r['type']=="EURO_1_TRANS" for r in rows):
        for i, r in enumerate(rows):
            if r['type']=="EURO_1_TRANS":
                rows.pop(i); remaining += 1; break

    # 4) mit 3-längs auffüllen
    if remaining < 0: remaining = 0
    rows += [euro_row_long() for _ in range(remaining // 3)]

    # 5) Fallback, falls Anzahl nicht exakt passt
    if sum(r['pallets'] for r in rows) != n:
        if n >= 2 and (n - 2) % 3 == 0:
            rows = [euro_row_trans2()] + [euro_row_long() for _ in range((n-2)//3)]
        else:
            rows = [euro_row_long() for _ in range(n // 3)]
            rest = n % 3
            if rest == 2: rows.insert(0, euro_row_trans2())
            elif rest == 1: rows.insert(0, euro_row_trans1())
    return rows

def cap_to_trailer(rows: List[Dict]) -> List[Dict]:
    out, s = [], 0
    for r in rows:
        if s + r['len_cm'] > TRAILER_LEN_CM: break
        out.append(r); s += r['len_cm']
    return out

# --- Varianten berechnen ---
rows_33 = cap_to_trailer(layout_for_preset_euro(33, singles_front=0))
rows_32 = cap_to_trailer(layout_for_preset_euro(32, singles_front=2))
rows_31 = cap_to_trailer(layout_for_preset_euro(31, singles_front=1))
rows_24 = cap_to_trailer([euro_row_trans2() for _ in range(6)] + [euro_row_long() for _ in range(5)])

txt_33, used_33 = render_rows(rows_33)
txt_32, used_32 = render_rows(rows_32)
txt_31, used_31 = render_rows(rows_31)
txt_24, used_24 = render_rows(rows_24)

# --- Garantiert nebeneinander via HTML Flexbox ---
st.title("🦊 Paletten Fuchs – Vier Varianten (Unicode clean)")

def card(title: str, body: str, used: int) -> str:
    body = html.escape(body)
    return f"""
    <div style="flex:0 0 auto; border:1px solid #ddd; padding:8px; border-radius:6px; background:#fff;">
      <div style="font: 600 12px system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin-bottom:6px;">
        {html.escape(title)} &nbsp;•&nbsp; {used} cm / {TRAILER_LEN_CM} cm
      </div>
      <pre style="margin:0; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:10px; line-height:1.05; white-space:pre;">
{body}
      </pre>
    </div>
    """

html_block = f"""
<div style="display:flex; gap:12px; overflow-x:auto; padding:4px; white-space:nowrap;">
  {card("33 Euro", txt_33, used_33)}
  {card("32 Euro (2× Einzel quer vorne)", txt_32, used_32)}
  {card("31 Euro (1× Einzel quer vorne)", txt_31, used_31)}
  {card("24 Euro (6×2 quer + 5×3 längs)", txt_24, used_24)}
</div>
"""

st.markdown(html_block, unsafe_allow_html=True)
st.caption("Zeichensatz: ▮ (längs), ▬ (quer, 2er-Reihe), ▭ (Einzel quer), ⬜ (Industrie, später). Blockbreite = 1, Raster = 25.")
