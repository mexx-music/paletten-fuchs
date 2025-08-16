# custom_layouts.py
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
import json
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import numpy as np  # <--- NEU: NumPy importiert

# --- Trailer & Raster (cm / px Skalierung) ---
TRAILER_INNER_LEN_CM = 1360
TRAILER_INNER_W_CM   = 246
GRID_CM = 20
SCALE   = 3
CANVAS_W = int(TRAILER_INNER_LEN_CM / GRID_CM * SCALE)
CANVAS_H = int(TRAILER_INNER_W_CM   / GRID_CM * SCALE)

# --- Palettenmaße ---
PAL_EURO_L = 120
PAL_EURO_W =  80
PAL_IND_L  = 120
PAL_IND_W  = 100
PAL_TYPEN = {
    "Euro 120×80": (PAL_EURO_L, PAL_EURO_W),
    "Industrie 120×100": (PAL_IND_L, PAL_IND_W),
}

# --- Datenstrukturen ---
@dataclass
class LayoutItem:
    x_cm: int
    y_cm: int
    w_cm: int
    h_cm: int
    typ: str

@dataclass
class Meta:
    name: str = ""
    total_pal: int = 0
    heavy_mode: bool = False
    heavy_count: int = 0
    notes: str = ""

@dataclass
class Preset:
    meta: Meta
    layout: List[LayoutItem]

# --- Keys im Session State ---
SS = "pf_custom"

def _ensure_state():
    if SS not in st.session_state:
        st.session_state[SS] = {}
    s = st.session_state[SS]
    s.setdefault("canvas_data", {"objects": []})
    s.setdefault("meta", Meta(name="23 Pal schwer – Vers X", total_pal=23, heavy_mode=True, heavy_count=23, notes=""))
    s.setdefault("presets", {"Vers 1": None, "Vers 2": None, "Vers 3": None, "Vers 4": None})
    return s

# --- Helpers ---
def _grid_background(w, h, step_px):
    img = Image.new("RGB", (w, h), (255,255,255))
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,w-1,h-1], outline=(150,150,150), width=2)
    if step_px > 0:
        for x in range(0, w, step_px):
            d.line([(x,0),(x,h)], fill=(230,230,230))
        for y in range(0, h, step_px):
            d.line([(0,y),(w,y)], fill=(230,230,230))
    return img

def _snap_to_grid(px):
    grid_px = GRID_CM * SCALE / GRID_CM
    return int(round(px / grid_px) * grid_px)

def _make_rect_obj(x_px, y_px, w_cm, h_cm, color="#4a90e2"):
    return {
        "type": "rect",
        "left": x_px, "top": y_px,
        "width": w_cm * SCALE / GRID_CM,
        "height": h_cm * SCALE / GRID_CM,
        "fill": color, "stroke": "#1a1a1a", "strokeWidth": 1,
        "opacity": 0.9, "selectable": True, "hasControls": False,
        "hasBorders": True, "rx": 2, "ry": 2,
    }

def _placed_from_canvas_json(fabric_json, snap=True) -> List[LayoutItem]:
    if not fabric_json or "objects" not in fabric_json:
        return []
    cm_per_px = GRID_CM / SCALE
    out: List[LayoutItem] = []
    for obj in fabric_json["objects"]:
        if obj.get("type") != "rect":
            continue
        x_px = obj.get("left", 0)
        y_px = obj.get("top", 0)
        w_px = obj.get("width", 0) * obj.get("scaleX", 1)
        h_px = obj.get("height", 0) * obj.get("scaleY", 1)
        if snap:
            x_px = _snap_to_grid(x_px); y_px = _snap_to_grid(y_px)
        x_cm = round(x_px * (GRID_CM / SCALE))
        y_cm = round(y_px * (GRID_CM / SCALE))
        w_cm = round(w_px * (GRID_CM / SCALE))
        h_cm = round(h_px * (GRID_CM / SCALE))

        dims = sorted([w_cm, h_cm])
        if dims == sorted([PAL_EURO_W, PAL_EURO_L]):
            typ = "Euro 120×80"
        elif dims == sorted([PAL_IND_W, PAL_IND_L]):
            typ = "Industrie 120×100"
        else:
            typ = f"Custom {dims[0]}×{dims[1]}"
        out.append(LayoutItem(x_cm, y_cm, w_cm, h_cm, typ))
    return out

def _canvas_from_layout(layout: List[LayoutItem]) -> Dict[str, Any]:
    objs = []
    for it in layout:
        x_px = it.x_cm / (GRID_CM / SCALE)
        y_px = it.y_cm / (GRID_CM / SCALE)
        color = "#4a90e2" if "Euro" in it.typ else ("#7ec050" if "Industrie" in it.typ else "#999999")
        objs.append(_make_rect_obj(x_px, y_px, it.w_cm, it.h_cm, color=color))
    return {"objects": objs}

def _preset_to_dict(p: Preset) -> Dict[str, Any]:
    return {"meta": asdict(p.meta), "layout": [asdict(x) for x in p.layout]}

def _preset_from_dict(d: Dict[str, Any]) -> Preset:
    meta = Meta(**d["meta"])
    layout = [LayoutItem(**x) for x in d["layout"]]
    return Preset(meta=meta, layout=layout)

# --- Öffentliche API ---
def render_manager(title: str = "Eigene Layouts (Vers 1–4)", show_expander: bool = True) -> List[LayoutItem]:
    s = _ensure_state()
    container = st.expander(title, expanded=False) if show_expander else st.container()
    with container:
        top_l, top_m, top_r = st.columns([3,2,2])

        with top_m:
            st.subheader("Meta / Schnell-Setzer")
            with st.form("pf_meta_form", clear_on_submit=False):
                meta = s["meta"]
                meta.name = st.text_input("Name", meta.name)
                meta.total_pal = st.number_input("Gesamt-Paletten", 0, 40, meta.total_pal)
                meta.heavy_mode = st.checkbox("Schwer-Modus aktiv", value=meta.heavy_mode)
                meta.heavy_count = st.number_input("Davon schwer (Anzahl)", 0, 40, meta.heavy_count)
                meta.notes = st.text_area("Notizen", value=meta.notes)
                set_23 = st.form_submit_button("Schnell setzen: 23 Pal schwer")
                if set_23:
                    s["meta"] = Meta(name="23 Pal schwer – Vers X", total_pal=23, heavy_mode=True, heavy_count=23, notes="Schnell-Setzer")
                    st.success("Meta auf ‚23 Pal schwer‘ gesetzt.")

        with top_r:
            st.subheader("Presets Export/Import")
            export_dict = {k: (None if v is None else _preset_to_dict(v)) for k, v in s["presets"].items()}
            st.download_button("Alle Presets als JSON", data=json.dumps(export_dict, ensure_ascii=False, indent=2),
                               file_name="palettenfuchs_presets.json", mime="application/json")
            up = st.file_uploader("Presets JSON laden", type=["json"], key="pf_upload")
            if up:
                try:
                    data = json.load(up)
                    for key, val in data.items():
                        if key in s["presets"]:
                            s["presets"][key] = None if val is None else _preset_from_dict(val)
                    st.success("Presets importiert.")
                except Exception as e:
                    st.error(f"Import fehlgeschlagen: {e}")

        # Canvas
        with top_l:
            st.subheader("Canvas (Drag/Move/Löschen)")
            pal_typ = st.selectbox("Paletten-Typ hinzufügen", list(PAL_TYPEN.keys()), key="pf_pal_typ")
            add_here = st.button("Palette mittig hinzufügen", key="pf_add_here")
            show_grid = st.toggle("Raster anzeigen", value=True, key="pf_show_grid")
            snap = st.toggle("Snapping", value=True, key="pf_snap")
            clear_canvas = st.button("Canvas leeren", key="pf_clear")

            # FIX: PIL → NumPy konvertieren
            bg = _grid_background(CANVAS_W, CANVAS_H, int(GRID_CM * SCALE / GRID_CM)) if show_grid else None
            bg_np = np.array(bg) if bg is not None else None

            canvas_result = st_canvas(
                fill_color="rgba(0, 0, 0, 0)",
                stroke_width=2, stroke_color="#333333",
                background_color="#FFFFFF" if bg_np is None else None,
                background_image=bg_np,
                update_streamlit=True,
                height=CANVAS_H, width=CANVAS_W,
                drawing_mode="transform",
                key="pf_canvas",
            )
            if canvas_result.json_data is not None:
                s["canvas_data"] = canvas_result.json_data

            if clear_canvas:
                s["canvas_data"] = {"objects": []}
                st.rerun()

            if add_here:
                w_cm, h_cm = PAL_TYPEN[pal_typ]
                rect_w_px = w_cm * SCALE / GRID_CM
                rect_h_px = h_cm * SCALE / GRID_CM
                x = CANVAS_W//2 - rect_w_px//2
                y = CANVAS_H//2 - rect_h_px//2
                if snap:
                    x = _snap_to_grid(x); y = _snap_to_grid(y)
                color = "#4a90e2" if "Euro" in pal_typ else "#7ec050"
                data = s["canvas_data"] or {"objects": []}
                objs = data.get("objects", [])
                objs.append(_make_rect_obj(x, y, w_cm, h_cm, color=color))
                data["objects"] = objs
                s["canvas_data"] = data
                st.rerun()

        # Preset-Slots
        st.subheader("Versionen: Speichern & Laden")
        cols = st.columns(4)
        slot_names = ["Vers 1","Vers 2","Vers 3","Vers 4"]

        def ui_slot(col, slot_name):
            with col:
                st.markdown(f"**{slot_name}**")
                p: Optional[Preset] = s["presets"][slot_name]
                if p:
                    st.caption(f"{p.meta.name} | {len(p.layout)} Objekte | Notiz: {p.meta.notes[:32]}{'...' if len(p.meta.notes)>32 else ''}")
                else:
                    st.caption("— leer —")

                save = st.button(f"Save → {slot_name}", key=f"pf_save_{slot_name}")
                load = st.button(f"Load ← {slot_name}", key=f"pf_load_{slot_name}")
                clr  = st.button(f"Clear {slot_name}", key=f"pf_clr_{slot_name}")

                if save:
                    layout = _placed_from_canvas_json(s["canvas_data"], snap=True)
                    s["presets"][slot_name] = Preset(meta=s["meta"], layout=layout)
                    st.success(f"{slot_name} gespeichert ({len(layout)} Objekte).")

                if load:
                    preset = s["presets"].get(slot_name)
                    if preset:
                        s["meta"] = preset.meta
                        s["canvas_data"] = _canvas_from_layout(preset.layout)
                        st.success(f"{slot_name} geladen: {preset.meta.name}")
                        st.rerun()
                    else:
                        st.warning(f"{slot_name} ist leer.")

                if clr:
                    s["presets"][slot_name] = None
                    st.info(f"{slot_name} geleert.")

        for c, n in zip(cols, slot_names):
            ui_slot(c, n)

        layout_cm = _placed_from_canvas_json(s["canvas_data"], snap=True)
        st.caption("Aktuelles Layout (cm, für App-Logik):")
        st.write([asdict(x) for x in layout_cm])

    return layout_cm

def get_active_meta() -> Meta:
    s = _ensure_state()
    return s["meta"]

def export_all_presets_json() -> str:
    s = _ensure_state()
    data = {k: (None if v is None else _preset_to_dict(v)) for k, v in s["presets"].items()}
    return json.dumps(data, ensure_ascii=False, indent=2)
