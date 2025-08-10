# app.py
# Paletten Fuchs – Drag & Drop (Kühler 1360×245 cm, Raster 25 cm)
# - Euro / Industrie / IBC als Blöcke
# - Drag & Drop + Rotieren
# - Raster-Snapping (25 cm)
# - Speichern: JSON + PNG in ./layouts
# - Laden: gespeicherte Layouts aus ./layouts

from __future__ import annotations
import json, math, os
from pathlib import Path
from typing import Dict, Any, List, Tuple

import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image

# ---------- feste Geometrie (Kühler) ----------
TRAILER_L_CM = 1360
TRAILER_W_CM = 245
CELL_CM = 25
SCALE = 1.0  # px pro cm (1.0 = 1360x245 px)

CANVAS_W = int(TRAILER_L_CM * SCALE)
CANVAS_H = int(TRAILER_W_CM * SCALE)
CELL_PX = CELL_CM * SCALE

EURO = {"L_cm": 120, "W_cm": 80}
IND  = {"L_cm": 120, "W_cm": 100}  # IBC identisch, aber "schwer"

COLOR_EURO = "#cfe8ff"
COLOR_IND  = "#ffe7b3"
COLOR_IBC  = "#ffb3b3"
STROKE     = "#444"

SAVE_DIR = Path("layouts")
SAVE_DIR.mkdir(exist_ok=True)

# ---------- Helpers ----------
def cm_to_px(cm: float) -> float: return cm * SCALE
def px_to_cm(px: float) -> float: return px / SCALE
def snap(v: float, grid: float) -> float: return round(v / grid) * grid if grid > 0 else v

def rect_obj(x_px: float, y_px: float, w_px: float, h_px: float, fill: str, label: str) -> Dict[str, Any]:
    return {
        "type": "rect", "left": x_px, "top": y_px, "width": w_px, "height": h_px,
        "fill": fill, "stroke": STROKE, "strokeWidth": 1, "angle": 0,
        "opacity": 1, "selectable": True, "hasControls": True, "hasBorders": True,
        "name": label, "rx": 2, "ry": 2,
    }

def spawn_initial_objects(n_euro: int, n_ind: int, n_ibc: int) -> Dict[str, Any]:
    objs: List[Dict[str, Any]] = []
    def stack(items: List[Tuple[float,float,str,str]], start_x: float):
        gap = 6; x = start_x; y = 6
        for w,h,color,label in items:
            if y + h + 6 > CANVAS_H:
                x += max(w + gap, 80); y = 6
            objs.append(rect_obj(x, y, w, h, color, label))
            y += h + gap
    euro_rects = [(cm_to_px(EURO["L_cm"]), cm_to_px(EURO["W_cm"]), COLOR_EURO, "EURO")] * n_euro
    ind_rects  = [(cm_to_px(IND["L_cm"]),  cm_to_px(IND["W_cm"]),  COLOR_IND,  "IND")]  * n_ind
    ibc_rects  = [(cm_to_px(IND["L_cm"]),  cm_to_px(IND["W_cm"]),  COLOR_IBC,  "IBC")]  * n_ibc
    stack(euro_rects, 6); stack(ind_rects, 200); stack(ibc_rects, 400)
    return {"version": "5.2.4", "objects": objs}

def snap_current_objects(json_data: Dict[str, Any]) -> Dict[str, Any]:
    objs_out = []
    for o in json_data.get("objects", []):
        if o.get("type") != "rect": continue
        left  = snap(float(o.get("left", 0)), CELL_PX)
        top   = snap(float(o.get("top", 0)),  CELL_PX)
        width = float(o.get("width", 0))
        height= float(o.get("height", 0))
        ang   = (round(float(o.get("angle", 0)) / 90) * 90) % 360
        if ang in (90, 270): width, height = height, width
        width = snap(width, CELL_PX); height = snap(height, CELL_PX)
        left  = max(0, min(left, CANVAS_W - width))
        top   = max(0, min(top,  CANVAS_H - height))
        out = rect_obj(left, top, width, height, o.get("fill", COLOR_EURO), o.get("name", "EURO"))
        objs_out.append(out)
    return {"version": "5.2.4", "objects": objs_out}

def compute_used_length_cm(fabric_json: Dict[str, Any]) -> int:
    max_right = 0.0
    for o in fabric_json.get("objects", []):
        if o.get("type") != "rect": continue
        left = float(o.get("left", 0)); width = float(o.get("width", 0))
        angle= float(o.get("angle", 0)); height= float(o.get("height", 0))
        rad = math.radians(angle)
        w_rot = abs(width * math.cos(rad)) + abs(height * math.sin(rad))
        right = left + w_rot
        if right > max_right: max_right = right
    return int(px_to_cm(max_right))

def estimate_axle_split(fabric_json: Dict[str, Any]) -> Tuple[int,int]:
    total = 0.0; front_score = 0.0; half_cm = TRAILER_L_CM / 2
    for o in fabric_json.get("objects", []):
        if o.get("type") != "rect": continue
        name = o.get("name", "EURO")
        left = float(o.get("left", 0)); width = float(o.get("width", 0))
        angle= float(o.get("angle", 0)); height= float(o.get("height", 0))
        rad = math.radians(angle)
        w_rot = abs(width * math.cos(rad)) + abs(height * math.sin(rad))
        center_x_cm = px_to_cm(left + w_rot / 2)
        g = 2.0 if name in ("IBC","IND") else 1.0
        total += g
        share = 0.5 + (half_cm - center_x_cm) / (2*half_cm) if center_x_cm <= half_cm \
                else 0.5 - (center_x_cm - half_cm) / (2*half_cm)
        share = max(0.0, min(1.0, share))
        front_score += g * share
    if total == 0: return 50, 50
    f = int(round(100 * front_score / total)); return f, 100 - f

def list_layout_files() -> List[Path]:
    return sorted(SAVE_DIR.glob("*.json"))

def save_layout(name: str, json_data: Dict[str, Any], image) -> Path:
    data = {
        "meta": {
            "trailer": {"L_cm": TRAILER_L_CM, "W_cm": TRAILER_W_CM},
            "cell_cm": CELL_CM, "scale_px_per_cm": SCALE, "verified": True
        },
        "objects": json_data.get("objects", []),
        "metrics": {
            "used_length_cm": compute_used_length_cm(json_data),
            "axle_front_pct": estimate_axle_split(json_data)[0],
            "axle_back_pct":  estimate_axle_split(json_data)[1],
        },
    }
    json_path = SAVE_DIR / f"{name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # PNG (falls Bild verfügbar)
    if image is not None:
        try:
            image.save(SAVE_DIR / f"{name}.png")
        except Exception:
            pass
    return json_path

def load_layout(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Fabric-kompatibles JSON aus gespeicherten Objekten aufbauen
    return {"version": "5.2.4", "objects": data.get("objects", [])}

# ---------- UI ----------
st.set_page_config(page_title="Paletten Fuchs – Drag & Drop", layout="wide")
st.title("🦊 Paletten Fuchs – Drag & Drop (Kühler 1360×245 cm)")

with st.sidebar:
    st.subheader("📦 Paletten anlegen")

    # --> WICHTIG: alle Parameter benannt + format und eindeutige keys
    n_euro = st.number_input(
        label="Euro (120×80)",
        min_value=0,
        max_value=45,
        value=12,
        step=1,
        format="%d",
        key="n_euro_input",
    )
    n_ind = st.number_input(
        label="Industrie (100×120 quer)",
        min_value=0,
        max_value=30,
        value=4,
        step=1,
        format="%d",
        key="n_ind_input",
    )
    n_ibc = st.number_input(
        label="IBC (schwer)",
        min_value=0,
        max_value=30,
        value=0,
        step=1,
        format="%d",
        key="n_ibc_input",
    )

    # Erst NACH den Inputs initialisieren – und mit einem eigenen Key
    if "init_json" not in st.session_state:
        st.session_state.init_json = spawn_initial_objects(int(n_euro), int(n_ind), int(n_ibc))

    if st.button("Neu befüllen", key="refill_btn"):
        st.session_state.init_json = spawn_initial_objects(int(n_euro), int(n_ind), int(n_ibc))

    if load_choice != "– nichts –":
        path = SAVE_DIR / load_choice
        try:
            st.session_state.init_json = load_layout(path)
            st.success(f"Layout geladen: {path.name}")
        except Exception as e:
            st.error(f"Konnte Layout nicht laden: {e}")

col_left, col_right = st.columns([3, 2], gap="large")

with col_left:
    st.write("### 🧱 Canvas – ziehen/rotieren, danach auf Raster einrasten")
    bg_style = (
        f"background: repeating-linear-gradient(90deg, #fafafa, #fafafa {CELL_PX-1}px, #eaeaea {CELL_PX}px), "
        f"repeating-linear-gradient(180deg, #fafafa, #fafafa {CELL_PX-1}px, #eaeaea {CELL_PX}px); "
        f"border:1px solid #999;"
    )
    canvas = st_canvas(
        background_color=None,
        width=CANVAS_W, height=CANVAS_H,
        drawing_mode="transform",
        initial_drawing=st.session_state.init_json,
        key="canvas",
        css_background=bg_style,
        update_streamlit=True,
        display_toolbar=False,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔲 Raster einrasten (25 cm)"):
            if canvas.json_data:
                st.session_state.init_json = snap_current_objects(canvas.json_data)
                st.experimental_rerun()
    with c2:
        if st.button("♻️ Alles zurücksetzen"):
            st.session_state.init_json = spawn_initial_objects(n_euro, n_ind, n_ibc)
            st.experimental_rerun()

    layout_name = st.text_input("Szenario-Name zum Speichern", value="mein_layout")

with col_right:
    st.write("### 📏 Maße & Achslast")
    if canvas.json_data:
        used_len = compute_used_length_cm(canvas.json_data)
        f_pct, b_pct = estimate_axle_split(canvas.json_data)
        st.markdown(f"**Genutzte Länge:** {used_len} cm von {TRAILER_L_CM} cm (≈ {used_len/TRAILER_L_CM:.0%})")
        st.markdown(f"**Achslast (grobe Schätzung):** vorn **{f_pct}%** / hinten **{b_pct}%**")

        if st.button("💾 Layout speichern (JSON + PNG)"):
            path = save_layout(layout_name, canvas.json_data, canvas.image_data)
            st.success(f"Gespeichert: {path}")
            st.caption("JSON liegt im Ordner ./layouts – PNG wird mit gespeichert, falls möglich.")
    else:
        st.info("Zieh/rotiere die Paletten im Canvas – dann erscheinen hier die Werte.")
