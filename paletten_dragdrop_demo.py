# paletten_dragdrop_demo.py
# 🦊 Paletten Fuchs – Drag&Drop Demo (Kühler 1360×245 cm, Raster 25 cm)
# - Drag & Drop / Rotieren via Canvas (Fabric.js)
# - Euro / Industrie / IBC als Rechtecke
# - Raster-Snapping (25 cm)
# - Speichern als JSON + PNG (layouts/)

import json
import math
import os
from pathlib import Path
from typing import List, Dict, Any

import streamlit as st
from streamlit_drawable_canvas import st_canvas

# ----------------------- feste Geometrie & Raster -----------------------
TRAILER_L_CM = 1360   # Länge (cm)
TRAILER_W_CM = 245    # Breite (cm)
CELL_CM = 25          # Rasterweite (cm/Zelle)
SCALE = 1.0           # px pro cm (1.0 => Canvas 1360×245 px; auf iPad gut bedienbar)

CANVAS_W = int(TRAILER_L_CM * SCALE)
CANVAS_H = int(TRAILER_W_CM * SCALE)
CELL_PX = CELL_CM * SCALE

EURO = {"L_cm": 120, "W_cm": 80}
IND  = {"L_cm": 120, "W_cm": 100}  # IBC identisch, aber "schwer"

# Farben (hell, mit Rand)
COLOR_EURO = "#cfe8ff"
COLOR_IND  = "#ffe7b3"
COLOR_IBC  = "#ffb3b3"
STROKE     = "#444"

SAVE_DIR = Path("layouts")
SAVE_DIR.mkdir(exist_ok=True)

# ----------------------- Hilfsfunktionen -----------------------
def rect_obj(x_px: float, y_px: float, w_px: float, h_px: float, fill: str, label: str) -> Dict[str, Any]:
    """Fabric.js Rect-Objekt."""
    return {
        "type": "rect",
        "left": x_px,
        "top": y_px,
        "width": w_px,
        "height": h_px,
        "fill": fill,
        "stroke": STROKE,
        "strokeWidth": 1,
        "angle": 0,
        "opacity": 1,
        "selectable": True,
        "hasControls": True,
        "hasBorders": True,
        "name": label,      # wir nutzen 'name' als Typ/ID
        "rx": 2, "ry": 2,   # leicht abgerundet
    }

def cm_to_px(cm: float) -> float:
    return cm * SCALE

def px_to_cm(px: float) -> float:
    return px / SCALE

def snap(v: float, grid: float) -> float:
    if grid <= 0: return v
    return round(v / grid) * grid

def spawn_initial_objects(n_euro: int, n_ind: int, n_ibc: int) -> Dict[str, Any]:
    """Erzeuge Start-Objekte links vorne, in Spalten gestapelt."""
    objs: List[Dict[str, Any]] = []

    # Helper, stapelt eine Liste von (w,h,farbe,label)
    def stack(items: List[tuple], start_x: float):
        gap = 6
        x = start_x
        y = 6
        for (w, h, color, label) in items:
            if y + h + 6 > CANVAS_H:  # neue Spalte
                x += max(w + gap, 80)
                y = 6
            objs.append(rect_obj(x, y, w, h, color, label))
            y += h + gap

    euro_rects = [(cm_to_px(EURO["L_cm"]), cm_to_px(EURO["W_cm"]), COLOR_EURO, "EURO")] * n_euro
    ind_rects  = [(cm_to_px(IND["L_cm"]),  cm_to_px(IND["W_cm"]),  COLOR_IND,  "IND")]  * n_ind
    ibc_rects  = [(cm_to_px(IND["L_cm"]),  cm_to_px(IND["W_cm"]),  COLOR_IBC,  "IBC")]  * n_ibc

    stack(euro_rects, 6)
    stack(ind_rects,  200)   # nächste Spalte
    stack(ibc_rects,  400)   # nächste Spalte

    return {"version": "5.2.4", "objects": objs}  # Fabric JSON minimal

def compute_used_length_cm(fabric_json: Dict[str, Any]) -> int:
    """Maximale x-Ausdehnung (rechts) in cm."""
    max_right = 0.0
    for o in fabric_json.get("objects", []):
        if o.get("type") != "rect": continue
        left = float(o.get("left", 0))
        top = float(o.get("top", 0))
        width = float(o.get("width", 0))
        height = float(o.get("height", 0))
        angle = float(o.get("angle", 0))
        # Rotation berücksichtigen: bounding box
        rad = math.radians(angle)
        w_rot = abs(width * math.cos(rad)) + abs(height * math.sin(rad))
        # Canvas hat keinen Offset: 0..CANVAS_W
        right = left + w_rot
        if right > max_right:
            max_right = right
    return int(px_to_cm(max_right))

def estimate_axle_split(fabric_json: Dict[str, Any]) -> (int, int):
    """Grobe Achslast-Schätzung: positionelle Verteilung (IBC/IND doppelt gewichtet)."""
    total = 0.0
    front_score = 0.0
    half_cm = TRAILER_L_CM / 2
    for o in fabric_json.get("objects", []):
        if o.get("type") != "rect": continue
        name = o.get("name", "EURO")
        left = float(o.get("left", 0))
        width = float(o.get("width", 0))
        angle = float(o.get("angle", 0))
        height = float(o.get("height", 0))
        rad = math.radians(angle)
        w_rot = abs(width * math.cos(rad)) + abs(height * math.sin(rad))
        center_x_px = left + w_rot / 2
        center_x_cm = px_to_cm(center_x_px)
        # Gewichtsfaktor
        g = 2.0 if name in ("IBC", "IND") else 1.0
        total += g
        if center_x_cm <= half_cm:
            share = 0.5 + (half_cm - center_x_cm) / (2 * half_cm)
        else:
            share = 0.5 - (center_x_cm - half_cm) / (2 * half_cm)
        share = max(0.0, min(1.0, share))
        front_score += g * share
    if total == 0:
        return 50, 50
    front = int(round(100 * front_score / total))
    return front, 100 - front

def snap_current_objects(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """Alle Objekte auf Raster (CELL_PX) einrasten und Winkel auf 0/90/180/270 runden."""
    objs_out = []
    for o in json_data.get("objects", []):
        if o.get("type") != "rect":
            continue
        left = snap(float(o.get("left", 0)), CELL_PX)
        top = snap(float(o.get("top", 0)),  CELL_PX)
        width = float(o.get("width", 0))
        height = float(o.get("height", 0))
        angle = float(o.get("angle", 0))
        # Winkel auf 90er Schritte runden
        ang = (round(angle / 90) * 90) % 360
        # Bei 90/270: width/height tauschen
        if ang in (90, 270):
            width, height = height, width
        width = snap(width, CELL_PX)
        height = snap(height, CELL_PX)
        # Grenzen einhalten
        left = max(0, min(left, CANVAS_W - width))
        top  = max(0, min(top,  CANVAS_H - height))
        out = rect_obj(left, top, width, height, o.get("fill", COLOR_EURO), o.get("name", "EURO"))
        out["angle"] = 0  # nach Snapping ausgerichtet
        objs_out.append(out)
    return {"version": "5.2.4", "objects": objs_out}

# ----------------------- UI -----------------------
st.set_page_config(page_title="🦊 Paletten Drag&Drop Demo", layout="wide")
st.title("🦊 Paletten Fuchs – Drag & Drop (Kühler 1360×245 cm)")

with st.sidebar:
    st.subheader("📦 Paletten anlegen")
    n_euro = st.number_input("Euro (120×80)", 0, 45, 12, 1)
    n_ind  = st.number_input("Industrie (100×120 quer)", 0, 30, 4, 1)
    n_ibc  = st.number_input("IBC (schwer, 100×120 quer)", 0, 30, 0, 1)
    st.caption("Rotation: Ecke greifen und drehen • Verschieben per Drag • Raster: 25 cm")
    if "init_json" not in st.session_state or st.button("Neu befüllen"):
        st.session_state.init_json = spawn_initial_objects(n_euro, n_ind, n_ibc)

col_left, col_right = st.columns([3, 2], gap="large")

with col_left:
    st.write("### 🧱 Canvas (Drag & Drop / Rotieren)")
    # leichte Rahmen / Hintergrund
    bg_style = f"background: repeating-linear-gradient(90deg, #fafafa, #fafafa {CELL_PX-1}px, #eaeaea {CELL_PX}px), repeating-linear-gradient(180deg, #fafafa, #fafafa {CELL_PX-1}px, #eaeaea {CELL_PX}px); border:1px solid #999;"

    canvas_res = st_canvas(
        fill_color="rgba(255, 165, 0, 0.2)",  # ungenutzt (wir malen Rects aus initial_drawing)
        stroke_width=1,
        stroke_color="#666666",
        background_color=None,
        width=CANVAS_W,
        height=CANVAS_H,
        drawing_mode="transform",  # Objekte anfassen/verschieben/rotieren
        initial_drawing=st.session_state.init_json,
        key="canvas",
        css_background=bg_style,
        update_streamlit=True,
        display_toolbar=False,
    )

    col_a, col_b, col_c = st.columns([1,1,2])
    with col_a:
        if st.button("🔲 Raster einrasten (25 cm)"):
            if canvas_res.json_data:
                snapped = snap_current_objects(canvas_res.json_data)
                st.session_state.init_json = snapped
                st.experimental_rerun()
    with col_b:
        if st.button("♻️ Alles zurücksetzen"):
            st.session_state.init_json = spawn_initial_objects(n_euro, n_ind, n_ibc)
            st.experimental_rerun()
    with col_c:
        layout_name = st.text_input("Szenario‑Name zum Speichern (z. B. 24E_4IND)", value="mein_layout")

with col_right:
    st.write("### 📏 Maße & Achslast")
    if canvas_res.json_data:
        used_len = compute_used_length_cm(canvas_res.json_data)
        front_pct, back_pct = estimate_axle_split(canvas_res.json_data)
        st.markdown(f"**Genutzte Länge:** {used_len} cm von {TRAILER_L_CM} cm (≈ {used_len/TRAILER_L_CM:.0%})")
        st.markdown(f"**Achslast (grobe Schätzung):** vorn **{front_pct}%** / hinten **{back_pct}%**")
        st.caption("Hinweis: Rotationswinkel werden für die Achslast über Bounding Box angenähert.")

        # Speichern
        if st.button("💾 Layout speichern (JSON + PNG)"):
            data = {
                "meta": {
                    "trailer": {"L_cm": TRAILER_L_CM, "W_cm": TRAILER_W_CM},
                    "cell_cm": CELL_CM,
                    "scale_px_per_cm": SCALE,
                    "verified": True
                },
                "objects": canvas_res.json_data["objects"],
                "metrics": {
                    "used_length_cm": used_len,
                    "axle_front_pct": front_pct,
                    "axle_back_pct": back_pct
                }
            }
            json_path = SAVE_DIR / f"{layout_name}.json"
            png_path  = SAVE_DIR / f"{layout_name}.png"

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # canvas_res.image_data ist ein PIL‑Image (oder None, je nach Version)
            img = canvas_res.image_data
            if img is not None:
                img.save(png_path)

            st.success(f"Gespeichert: {json_path} & {png_path}")
            st.write(f"JSON: `{json_path}`")
            st.write(f"PNG:  `{png_path}`")
    else:
        st.info("Zieh/rotiere die Paletten im Canvas – Daten erscheinen hier.")
