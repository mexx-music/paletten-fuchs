# pal_fuchs_9_clean.py
# Paletten Fuchs – Clean Basis (P0+P1)
# - Unicode/Monospace-Rendering (nur Text, kein HTML)
# - Feste Rasterung: 25 Längsblöcke, 4 Zeichen je Block
# - Presets: 24–33 Euro inkl. 31/32 (Einzel-quer vorne)
# - Sauberer Abschluss: letzte Reihe ist immer eine volle Reihe (3 längs oder 2 quer oder 1 quer-Einzel)
# - Clean-UI: Zusatzoptionen standardmäßig ausgeblendet (Blumenwagen, Feinjustage)
# - Preset-"Popup": via st.popover() (fallback auf st.expander)

import streamlit as st
import math
from typing import List, Tuple, Dict

# -----------------------------
# Konstanten & Grundeinstellungen
# -----------------------------

st.set_page_config(page_title="Paletten Fuchs – Clean Basis", layout="wide")

TRAILER_LEN_CM = 1360         # Kühlsattel Standard
TRAILER_WIDTH_CM = 240
EURO_L_CM, EURO_W_CM = 120, 80
IND_L_CM,  IND_W_CM  = 120, 100

LENGTH_RASTER = 25            # 25 Rasterspalten über 13,60 m
CHARS_PER_BLOCK = 4           # 4 Zeichen je Rasterblock
CM_PER_RASTER = TRAILER_LEN_CM / LENGTH_RASTER  # ≈54.4 cm

# Unicode-Symbole (monospace-tauglich)
SYM_EURO_LONG   = "▮"  # 3 längs in der Breite (Reihenlänge 120 cm)
SYM_EURO_TRANS2 = "▬"  # 2 quer in der Breite (Reihenlänge 80 cm)
SYM_EURO_TRANS1 = "▭"  # 1 quer (Einzel mittig/verschiebbar) (Reihenlänge 80 cm)
SYM_INDUSTRY    = "■"  # Industrie-Reihe (optional, später)

# -----------------------------
# Hilfsfunktionen
# -----------------------------

def blocks(n: int, symbol: str) -> str:
    """Erzeuge n Rasterblöcke mit je CHARS_PER_BLOCK Symbolen."""
    return (symbol * CHARS_PER_BLOCK) * n

def cm_to_raster(cm: int) -> int:
    """Konvertiert cm (Reihenlänge) in Rasterspalten (visuelle Darstellung)."""
    # Stabil: 80 cm -> 1 Raster, 120 cm -> 2 Raster
    # Allgemein über rundung:
    return max(1, round(cm / CM_PER_RASTER))

def render_rows(rows: List[Dict], length_limit_cm: int = TRAILER_LEN_CM) -> Tuple[str, int]:
    """
    Rendert Zeile-für-Zeile als Textblock. Jede Zeile repräsentiert eine Reihenlänge entlang des Trailers.
    rows: Liste von Dikten mit Keys: 'type', 'len_cm', 'pallets', 'sym', optional 'label'
    Return: (text_render, used_len_cm)
    """
    output_lines = []
    used_cm = 0
    for i, r in enumerate(rows, start=1):
        if used_cm + r['len_cm'] > length_limit_cm:
            break
        fill_raster = cm_to_raster(r['len_cm'])
        line = blocks(fill_raster, r['sym'])
        # Rest bis volle Trailerlänge (optisch, optional)
        pad_raster = LENGTH_RASTER - fill_raster
        if pad_raster > 0:
            line += " " * (pad_raster * CHARS_PER_BLOCK)

        label = r.get('label', "")
        if label:
            # Rechts einen knappen Label-Anhang (nicht monospaced-kritisch)
            line += f"   | {label}"

        output_lines.append(line)
        used_cm += r['len_cm']

    return "\n".join(output_lines), used_cm

def euro_row_long() -> Dict:
    return {"type": "EURO_3_LONG", "len_cm": EURO_L_CM, "pallets": 3, "sym": SYM_EURO_LONG}

def euro_row_trans2() -> Dict:
    return {"type": "EURO_2_TRANS", "len_cm": EURO_W_CM, "pallets": 2, "sym": SYM_EURO_TRANS2}

def euro_row_trans1(pos_label: str = "Mitte") -> Dict:
    # Einzel-quer vorne: 1 Palette, 80 cm Reihenlänge, verschiebbar (Label L/M/R)
    return {"type": "EURO_1_TRANS", "len_cm": EURO_W_CM, "pallets": 1, "sym": SYM_EURO_TRANS1, "label": f"Einzel quer: {pos_label}"}

# -----------------------------
# Layout-Generatoren (Euro)
# -----------------------------

def layout_for_preset_euro(n: int, singles_front: int = 0) -> List[Dict]:
    """
    Erzeuge ein Euro-Layout für N Paletten.
    - singles_front: Anzahl Einzel-quer vorne (0/1/2), jeweils 1 Palette und 80 cm Länge pro Reihe.
    - Rest wird mit 3-längs-Reihen (120 cm, 3 Paletten) aufgefüllt.
    - Falls Rest modulo 3 nicht 0 und singles_front < 2, wird versucht, mit einer 2-quer-Reihe (2 Paletten) zu ergänzen.
    Ziel: exakte Stückzahl, Reihenfolge: erst (optional) 1/2 Einzel-quer vorne, dann ggf. 2-quer, danach 3-längs.
    """
    rows: List[Dict] = []
    remaining = n

    # 1) Einzel-quer vorne (0/1/2) – je 1 Palette
    if singles_front > 0:
        take = min(singles_front, remaining)
        for _ in range(take):
            rows.append(euro_row_trans1())  # Label-Update via UI
        remaining -= take

    # 2) Falls mit 2-quer eine schöne Teilbarkeit entsteht
    #    Prüfe, ob wir mit genau EINE 2-quer-Reihe (2 Paletten) die restlichen Paletten auf ein Vielfaches von 3 bringen
    used_two_trans = False
    if remaining >= 2 and (remaining - 2) % 3 == 0:
        rows.append(euro_row_trans2())
        remaining -= 2
        used_two_trans = True

    # 3) Fülle den Rest mit 3-längs-Reihen
    if remaining % 3 != 0:
        # Wenn die Zahl nicht aufgeht, fallback: entferne ggf. die 2-quer wieder und setze alles auf 3-längs
        if used_two_trans:
            # roll back
            rows.pop()
            remaining += 2
        # Wenn Singles gesetzt sind, aber es nicht aufgeht, reduzieren wir Singles vorzugweise
        while remaining % 3 != 0 and any(r['type'] == "EURO_1_TRANS" for r in rows):
            # entferne ein Single (von vorne)
            # (In der Praxis: für 31 -> 1 Einzel + 10*3 passt, für 32 -> 2 Einzel + 10*3 passt)
            # Wenn wir hier landen, dann war die Eingangskombi unvorteilhaft
            for idx, r in enumerate(rows):
                if r['type'] == "EURO_1_TRANS":
                    rows.pop(idx)
                    remaining += 1
                    break

    # Jetzt sollte remaining % 3 == 0 (ansonsten füllen wir ausschließlich mit 3-längs und überschreiten ggf. Ziel nicht exakt)
    if remaining < 0:
        remaining = 0
    count_long_rows = remaining // 3
    rows.extend(euro_row_long() for _ in range(count_long_rows))

    # Falls wir NICHT exakt die gewünschte Anzahl erreicht haben (z. B. 24, 30, 33 gehen exakt; 31/32 durch Singles),
    # prüfen wir Ergebnis und korrigieren konservativ:
    if sum(r['pallets'] for r in rows) != n:
        # Versuche zweite Variante: erst 2-quer, dann long (ohne Singles)
        test_rows = []
        if n >= 2 and (n - 2) % 3 == 0:
            test_rows.append(euro_row_trans2())
            rest = n - 2
            test_rows.extend(euro_row_long() for _ in range(rest // 3))
            rows = test_rows

    return rows

def apply_single_positions(rows: List[Dict], single_pos: int) -> None:
    """
    Aktualisiert die Label der Einzel-quer-Reihen (EURO_1_TRANS) nach Slider (0..4..8).
    0/1 = links, 2 = mitte, 3/4 = rechts. (Wir zeigen nur Label an.)
    """
    label = "Mitte"
    if single_pos <= 1:
        label = "Links"
    elif single_pos >= 3:
        label = "Rechts"
    # Setze Label für alle Singles
    for r in rows:
        if r['type'] == "EURO_1_TRANS":
            r['label'] = f"Einzel quer: {label}"

def total_used_length_cm(rows: List[Dict]) -> int:
    return sum(r['len_cm'] for r in rows)

def total_pallets(rows: List[Dict]) -> int:
    return sum(r['pallets'] for r in rows)

# -----------------------------
# UI
# -----------------------------

st.title("🦊 Paletten Fuchs – Clean Basis")

# Clean-UI / Erweiterte Optionen
col_top1, col_top2, col_top3 = st.columns([1,1,2])
with col_top1:
    clean_mode = st.toggle("🧹 Clean-UI", value=True, help="Zusatzfunktionen ausblenden. Minimal starten.")

with col_top2:
    blumen_on = st.toggle("🌼 Blumenwagen anzeigen", value=False, help="Komplett verborgen, bis aktiv.")

# Preset-"Popup" (Popover, fallback Expander)
chosen_preset = None
singles_front_default = 0
with col_top3:
    try:
        with st.popover("📦 Preset wählen"):
            st.write("Schnellauswahl – Euro-Paletten:")
            preset = st.radio(
                "Vorgaben",
                options=["33 Euro", "32 Euro (2×Einzel quer vorne)", "31 Euro (1×Einzel quer vorne)",
                         "30 Euro", "29 Euro", "28 Euro", "27 Euro", "26 Euro", "25 Euro", "24 Euro",
                         "Benutzerdefiniert"],
                index=0
            )
            chosen_preset = preset
    except Exception:
        with st.expander("📦 Preset wählen", expanded=True):
            st.write("Schnellauswahl – Euro-Paletten:")
            preset = st.radio(
                "Vorgaben",
                options=["33 Euro", "32 Euro (2×Einzel quer vorne)", "31 Euro (1×Einzel quer vorne)",
                         "30 Euro", "29 Euro", "28 Euro", "27 Euro", "26 Euro", "25 Euro", "24 Euro",
                         "Benutzerdefiniert"],
                index=0
            )
            chosen_preset = preset

# Benutzerdefiniertes Ziel / Feineinstellungen
if chosen_preset == "Benutzerdefiniert":
    target_n = st.number_input("Ziel: Anzahl Euro-Paletten", min_value=1, max_value=40, value=33, step=1)
    singles_front = st.slider("Einzel-quer vorne (0/1/2)", 0, 2, 0)
else:
    mapping = {
        "33 Euro": (33, 0),
        "32 Euro (2×Einzel quer vorne)": (32, 2),
        "31 Euro (1×Einzel quer vorne)": (31, 1),
        "30 Euro": (30, 0),
        "29 Euro": (29, 0),
        "28 Euro": (28, 0),
        "27 Euro": (27, 0),
        "26 Euro": (26, 0),
        "25 Euro": (25, 0),
        "24 Euro": (24, 0),
    }
    target_n, singles_front = mapping.get(chosen_preset, (33, 0))

# Erweiterte Optionen (ausgeblendet in Clean)
if not clean_mode:
    st.subheader("Erweiterte Optionen")
    c1, c2, c3 = st.columns(3)
    with c1:
        single_pos = st.slider("Einzel-quer Position", 0, 4, 2, help="0/1=links, 2=mitte, 3/4=rechts")
    with c2:
        fix_back_finish = st.checkbox("Abschluss hinten hart prüfen", value=True,
                                      help="Falls über 13,60 m, letzte Reihen abschneiden.")
    with c3:
        show_length_bar = st.checkbox("Längenbalken anzeigen", value=True)
else:
    single_pos = 2
    fix_back_finish = True
    show_length_bar = True

# Blumenwagen (nur UI-Placeholder, komplett aus, bis aktiv)
if blumen_on and not clean_mode:
    st.info("🌼 Blumenwagen-Logik ist (bewusst) abgeschaltet in dieser Clean-Basis. Nur Anzeige-Toggle implementiert.")

# -----------------------------
# Layout erzeugen (Euro)
# -----------------------------

rows = layout_for_preset_euro(target_n, singles_front=singles_front)
apply_single_positions(rows, single_pos=single_pos)

# Harter Abschluss: Wenn Summenlänge > Trailer, schneide Überschuss (praktisch selten mit den vorgefertigten Presets)
used_cm = total_used_length_cm(rows)
if fix_back_finish and used_cm > TRAILER_LEN_CM:
    # Schneide letzte(n) Reihen ab, bis es passt (Vorrang: Abschluss darf Trailer nicht überragen)
    while rows and total_used_length_cm(rows) > TRAILER_LEN_CM:
        rows.pop()
    used_cm = total_used_length_cm(rows)

# -----------------------------
# Ausgabe
# -----------------------------

left, right = st.columns([2, 1])

with left:
    st.subheader("Ladeplan – Draufsicht (Text/Unicode, Monospace)")
    render_text, used_cm = render_rows(rows, length_limit_cm=TRAILER_LEN_CM)
    # Monospace-Codeblock für saubere Ausrichtung
    st.markdown(f"```\n{render_text}\n```")

    # Optionaler Längenbalken (vereinfacht)
    if show_length_bar:
        used_raster = cm_to_raster(used_cm)
        bar = blocks(used_raster, "▆")
        pad = " " * ((LENGTH_RASTER - used_raster) * CHARS_PER_BLOCK)
        st.markdown(f"```\n{bar}{pad}\n```")

with right:
    st.subheader("Zusammenfassung")
    st.write(f"**Preset:** {chosen_preset}")
    st.write(f"**Euro-Paletten gesamt:** {total_pallets(rows)} (Ziel: {target_n})")
    st.write(f"**Genutzte Länge:** {used_cm} cm von {TRAILER_LEN_CM} cm")
    st.write(f"**Reihen:** {len(rows)}")
    # Aufschlüsselung
    t_long  = sum(1 for r in rows if r['type'] == "EURO_3_LONG")
    t_q2    = sum(1 for r in rows if r['type'] == "EURO_2_TRANS")
    t_q1    = sum(1 for r in rows if r['type'] == "EURO_1_TRANS")
    st.write(f"- 3×Euro längs (120 cm): **{t_long} Reihen**  → {t_long*3} Paletten")
    st.write(f"- 2×Euro quer (80 cm): **{t_q2} Reihen**  → {t_q2*2} Paletten")
    st.write(f"- 1×Euro quer (80 cm): **{t_q1} Reihen**  → {t_q1} Palette")

    if t_q1 > 0:
        pos_txt = "Mitte" if single_pos == 2 else ("Links" if single_pos <= 1 else "Rechts")
        st.caption(f"Einzel-quer Position: **{pos_txt}**")

st.caption("Hinweis: Darstellung ist gerastert (25 Blöcke × 4 Zeichen). Berechnung erfolgt intern exakt in cm; "
           "Unicode-Render bleibt stabil monospaced. Diese Clean-Basis enthält bewusst nur Euro-Logik (Industrie/Blumen ausblendbar).")
