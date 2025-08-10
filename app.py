# -*- coding: utf-8 -*-
# app.py
# Paletten Fuchs – Drag & Drop (Trailer 1360x245 cm, Grid 25 cm)
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple

import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------
TRAILER_L_CM = 1360
TRAILER_W_CM = 245
CELL_CM = 25
SCALE = 1.0  # px per cm (1.0 => 1360x245 px)

CANVAS_W = int(TRAILER_L_CM * SCALE)
CANVAS_H = int(TRAILER_W_CM * SCALE)
CELL_PX = CELL_CM * SCALE

EURO = {"L_cm": 120, "W_cm": 80}
IND = {"L_cm": 120, "W_cm": 100}  # IBC same size, heavier

COLOR_EURO = "#cfe8ff"
COLOR_IND = "#ffe7b3"
COLOR_IBC = "#ffb3b3"
STROKE = "#444"

SAVE_DIR = Path("layouts")
SAVE_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def cm_to_px(cm: float) -> float:
    return cm * SCALE

def px_to_cm(px: float) -> float:
    return px / SCALE

def snap(v: float, grid: float) -> float:
    return round(v / grid) * grid if grid > 0 else v

def rect_obj(x_px: float, y_px: float, w_px: float, h_px: float, fill: str, label: str) -> Dict[str, Any]:
    return {
        "type": "rect",
        "left": float(x_px),
        "top": float(y_px),
        "width": float(w_px),
        "height": float(h_px),
        "fill": fill,
        "stroke": STROKE,
        "strokeWidth": 1,
        "angle": 0,
        "opacity": 1,
        "selectable": True,
        "hasControls": True,
        "hasBorders": True,
        "name": label,
        "rx": 2,
        "ry": 2,
    }

def spawn_initial_objects(n_euro: int, n_ind: int, n_ibc: int) -> Dict[str, Any]:
    objs: List[Dict[str, Any]] = []

    def stack(items: List[Tuple[float, float, str, str]], start_x: float) -> None:
        gap = 6.0
        x = float(start_x)
        y = 6.0
        for w, h, color, label in items:
            if y + h + 6.0 > CANVAS_H:
                x += max(w + gap, 80.0)
                y = 6.0
            objs.append(rect_obj(x, y, w, h, color, label))
            y += h + gap

    euro_rects = [(cm_to_px(EURO["L_cm"]), cm_to_px(EURO["W_cm"]), COLOR_EURO, "EURO")] * int(n_euro)
    ind_rects  = [(cm_to_px(IND["L_cm"]),  cm_to_px(IND["W_cm"]),  COLOR_IND,  "IND")]  * int(n_ind)
    ibc_rects  = [(cm_to_px(IND["L_cm"]),  cm_to_px(IND["W_cm"]),  COLOR_IBC,  "IBC")]  * int(n_ibc)

    stack(euro_rects, 6.0)
    stack(ind_rects,  200.0)
    stack(ibc_rects,  400.0)

    return {"version": "5.2.4", "objects": objs}

def snap_current_objects(json_data: Dict[str, Any]) -> Dict[str, Any]:
    objs_out: List[Dict[str, Any]] = []
    for o in json_data.get("objects", []):
        if o.get("type") != "rect":
            continue
        left  = snap(float(o.get("left", 0)), CELL_PX)
        top   = snap(float(o.get("top", 0)),  CELL_PX)
        width = float(o.get("width", 0))
        height= float(o.get("height", 0))
        ang   = (round(float(o.get("angle", 0)) / 90) * 90) % 360
        if ang in (90, 270):
            width, height = height, width
        width = snap(width, CELL_PX)
        height = snap(height, CELL_PX)
        left  = max(0.0, min(left, CANVAS_W - width))
        top   = max(0.0, min(top,  CANVAS_H - height))
        out = rect_obj(left, top, width, height, o.get("fill", COLOR_EURO), o.get("name", "EURO"))
        objs_out.append(out)
    return {"version": "5.2.4", "objects": objs_out}

def compute_used_length_cm(fabric_json: Dict[str, Any]) -> int:
    max_right = 0.0
    for o in fabric_json.get("objects", []):
        if o.get("type") != "rect":
            continue
        left = float(o.get("left", 0))
        width = float(o.get("width", 0))
        angle = float(o.get("angle", 0))
        height = float(o.get("height", 0))
        rad = math.radians(angle)
        w_rot = abs(width * math.cos(rad)) + abs(height * math.sin(rad))
        right = left + w_rot
        if right > max_right:
            max_right = right
    return int(px_to_cm(max_right))

def estimate_axle_split(fabric_json: Dict[str, Any]) -> Tuple[int, int]:
    total = 0.0
    front_score = 0.0
    half_cm = float(TRAILER_L_CM) / 2.0
    for o in fabric_json.get("objects", []):
        if o.get("type") != "rect":
            continue
        name = o.get("name", "EURO")
        left = float(o.get("left", 0))
        width = float(o.get("width", 0))
        angle = float(o.get("angle", 0))
        height = float(o.get("height", 0))
        rad = math.radians(angle)
        w_rot = abs(width * math.cos(rad)) + abs(height * math.sin(rad))
        center_x_cm = px_to_cm(left + w_rot / 2.0)
        g = 2.0 if name in ("IBC", "IND") else 1.0
        total += g
        if center_x_cm <= half_cm:
            share = 0.5 + (half_cm - center_x_cm) / (2.0 * half_cm)
        else:
            share = 0.5 - (center_x_cm - half_cm) / (2.0 * half_cm)
        share = max(0.0, min(1.0, share))
        front_score += g * share
    if total <= 0.0:
        return 50, 50
    f = int(round(100.0 * front_score / total))
    return f, 100 - f

# ------------------------------------------------------------
# App
# ------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Paletten Fuchs – Drag & Drop", layout="wide")
    st.title("Paletten Fuchs – Drag & Drop (Trailer 1360 x 245 cm)")

    with st.sidebar:
        st.header("Create pallets")

        n_euro = st.number_input(
            "Euro (120x80)",
            min_value=0, max_value=45, value=12, step=1, format="%d",
            key="n_euro",
        )
        n_ind = st.number_input(
            "Industry (100x120 cross)",
            min_value=0, max_value=30, value=4, step=1, format="%d",
            key="n_ind",
        )
        n_ibc = st.number_input(
            "IBC (heavy)",
            min_value=0, max_value=30, value=0, step=1, format="%d",
            key="n_ibc",
        )

        if "init_json" not in st.session_state:
            st.session_state.init_json = spawn_initial_objects(int(n_euro), int(n_ind), int(n_ibc))

        if st.button("Refill", key="refill_btn"):
            st.session_state.init_json = spawn_initial_objects(int(n_euro), int(n_ind), int(n_ibc))

    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.subheader("Canvas (drag, rotate, then snap to grid)")

        bg_style = (
            f"background: repeating-linear-gradient(90deg, #fafafa, #fafafa {CELL_PX-1}px, #eaeaea {CELL_PX}px), "
            f"repeating-linear-gradient(180deg, #fafafa, #fafafa {CELL_PX-1}px, #eaeaea {CELL_PX}px); "
            f"border:1px solid #999;"
        )

        canvas = st_canvas(
            fill_color="rgba(0, 0, 0, 0)",   # required by component
            stroke_width=1,                  # required by component
            stroke_color="#666666",          # required by component
            background_color=None,
            width=CANVAS_W,
            height=CANVAS_H,
            drawing_mode="transform",
            initial_drawing=st.session_state.init_json,
            key="canvas",
            css_background=bg_style,
            update_streamlit=True,
            display_toolbar=False,
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Snap to grid (25 cm)"):
                if canvas.json_data:
                    st.session_state.init_json = snap_current_objects(canvas.json_data)
                    st.experimental_rerun()
        with c2:
            if st.button("Reset all"):
                st.session_state.init_json = spawn_initial_objects(
                    int(st.session_state.get("n_euro", 12)),
                    int(st.session_state.get("n_ind", 4)),
                    int(st.session_state.get("n_ibc", 0)),
                )
                st.experimental_rerun()

        layout_name = st.text_input("Scenario name", value="my_layout")

    with col_right:
        st.subheader("Metrics")
        if canvas.json_data:
            used_len = compute_used_length_cm(canvas.json_data)
            f_pct, b_pct = estimate_axle_split(canvas.json_data)
            st.markdown(f"**Used length:** {used_len} cm of {TRAILER_L_CM} cm (≈ {used_len/TRAILER_L_CM:.0%})")
            st.markdown(f"**Axle load (rough):** front {f_pct}% / rear {b_pct}%")

            if st.button("Save (JSON + PNG)"):
                data = {
                    "meta": {
                        "trailer": {"L_cm": TRAILER_L_CM, "W_cm": TRAILER_W_CM},
                        "cell_cm": CELL_CM,
                        "scale_px_per_cm": SCALE,
                        "verified": True,
                    },
                    "objects": canvas.json_data.get("objects", []),
                    "metrics": {
                        "used_length_cm": used_len,
                        "axle_front_pct": f_pct,
                        "axle_back_pct": b_pct,
                    },
                }
                json_path = SAVE_DIR / f"{layout_name}.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                if canvas.image_data is not None:
                    try:
                        img = Image.fromarray(canvas.image_data)
                        img.save(SAVE_DIR / f"{layout_name}.png")
                    except Exception:
                        pass

                st.success(f"Saved: {json_path}")
        else:
            st.info("Drag/rotate pallets on the canvas, then snap to grid and save.")

# ------------------------------------------------------------
if __name__ == "__main__":
    main()
