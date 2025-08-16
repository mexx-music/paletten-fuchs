# custom_layouts.py — Paletten Fuchs 9.5
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image

TRAILER_LEN_CM = 1360
TRAILER_W_CM   = 240

# ---------- kleine Meta-Struktur für Canvas-Presets ----------
@dataclass
class UserMeta:
    name: str = "Preset 1"
    total_pal: int = 0
    heavy_count: int = 0

# Session Keys
_SS_PRESETS = "pf_presets"
_SS_LAST_META = "pf_last_meta"

def _ensure_session():
    if _SS_PRESETS not in st.session_state:
        st.session_state[_SS_PRESETS] = []
    if _SS_LAST_META not in st.session_state:
        st.session_state[_SS_LAST_META] = UserMeta()

def get_active_meta() -> UserMeta:
    _ensure_session()
    return st.session_state[_SS_LAST_META]

def export_all_presets_json() -> bytes:
    """Alle gespeicherten Canvas-Presets als JSON-Bytes exportieren."""
    import json
    _ensure_session()
    try:
        data = st.session_state[_SS_PRESETS]
        return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    except Exception as e:
        return b"[]"

def _cm_int(x: float) -> int:
    try:
        return int(round(float(x)))
    except Exception:
        return 0

def _normalize_rect(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Mappt fabric.js-Objekt -> cm-Koordinaten (hier 1 px = 1 cm, da Canvas 1360x240)."""
    t = obj.get("type")
    if t != "rect":
        return None
    left   = obj.get("left", 0)
    top    = obj.get("top", 0)
    width  = obj.get("width", 0)
    height = obj.get("height", 0)
    # fabric skaliert manchmal; 'scaleX/scaleY' berücksichtigen:
    sx = obj.get("scaleX", 1) or 1
    sy = obj.get("scaleY", 1) or 1
    w = width * sx
    h = height * sy
    # Bounds in Trailer halten
    x_cm = max(0, min(TRAILER_LEN_CM, _cm_int(left)))
    y_cm = max(0, min(TRAILER_W_CM,   _cm_int(top)))
    w_cm = max(1, min(TRAILER_LEN_CM - x_cm, _cm_int(w)))
    h_cm = max(1, min(TRAILER_W_CM   - y_cm, _cm_int(h)))

    # Typ grob raten anhand Verhältnis (Euro 120x80 / 80x120; Industrie 120x100)
    typ = "Custom"
    pair = (min(w_cm, h_cm), max(w_cm, h_cm))
    if pair in ((80,120),):
        typ = "Euro"
    elif pair == (100,120):
        typ = "Industrie"
    return {"x_cm": x_cm, "y_cm": y_cm, "w_cm": w_cm, "h_cm": h_cm, "typ": typ}

def _json_to_items(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not json_data:
        return []
    objs = json_data.get("objects") or []
    out: List[Dict[str, Any]] = []
    for o in objs:
        r = _normalize_rect(o)
        if r: out.append(r)
    return out

def render_manager(title: str = "Eigene Layouts (Vers 1–4)", show_expander: bool = True) -> List[Dict[str, Any]]:
    """Zeigt einen Canvas (1360x240) zum Platzieren von Rechtecken als Paletten.
       ACHTUNG: Wir übergeben KEIN NumPy an background_image, um den drawable-canvas Bug zu vermeiden.
    """
    _ensure_session()
    container = st.expander(title, expanded=show_expander) if show_expander else st.container()
    items: List[Dict[str, Any]] = []
    with container:
        st.caption("Ziehe Rechtecke (Paletten) auf den Trailer (1 Pixel = 1 cm). "
                   "Euro ≈ 120×80, Industrie ≈ 120×100. Du kannst Größe nachträglich anpassen.")

        # IMPORTANT: Kein NumPy-Array an background_image! Entweder PIL.Image ODER URL, oder None.
        bg_pil = None           # type: Optional[Image.Image]
        bg_url = None           # type: Optional[str]

        canvas_result = st_canvas(
            fill_color="rgba(0, 0, 0, 0)",     # transparente Füllung
            stroke_width=2,
            stroke_color="#222",
            background_color="rgba(0,0,0,0)",
            background_image=bg_pil,           # KEIN NumPy hier!
            background_image_url=bg_url,       # und nur setzen, wenn kein PIL
            width=TRAILER_LEN_CM,
            height=TRAILER_W_CM,
            drawing_mode="rect",
            update_streamlit=True,
            key="pf_canvas",
        )

        items = _json_to_items(canvas_result.json_data if canvas_result else None)

        # Meta: Zählen & Speichern
        total_pal = sum(1 for it in items if it["typ"] in ("Euro","Industrie"))
        st.session_state[_SS_LAST_META] = UserMeta(name="Canvas", total_pal=total_pal, heavy_count=0)

        col = st.columns([1,1,1])
        with col[0]:
            preset_name = st.text_input("Preset-Name", value=f"Layout {len(st.session_state[_SS_PRESETS])+1}")
        with col[1]:
            if st.button("Preset speichern", use_container_width=True):
                st.session_state[_SS_PRESETS].append({"name": preset_name, "items": items})
                st.success(f"Preset „{preset_name}“ gespeichert ({len(items)} Objekte).")
        with col[2]:
            if st.button("Alle Presets löschen", use_container_width=True):
                st.session_state[_SS_PRESETS] = []
                st.warning("Alle Presets gelöscht.")

        if st.checkbox("Letztes Canvas-JSON anzeigen", value=False):
            st.json(canvas_result.json_data or {})
    return items
