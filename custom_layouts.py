# custom_layouts.py — Paletten Fuchs 9.5 (robust, minimaler Canvas-Call)
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import streamlit as st

# Drawable-Canvas laden (und sauber degradieren, falls das Paket fehlt)
try:
    from streamlit_drawable_canvas import st_canvas  # >=0.9.3 empfohlen
    _HAS_CANVAS = True
except Exception as _e:
    st.warning(f"Drawable-Canvas nicht verfügbar: {_e!s}")
    _HAS_CANVAS = False

TRAILER_LEN_CM = 1360
TRAILER_W_CM   = 240

# ---------- Meta für Presets ----------
@dataclass
class UserMeta:
    name: str = "Preset 1"
    total_pal: int = 0
    heavy_count: int = 0

# Session Keys
_SS_PRESETS   = "pf_presets"
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
        return json.dumps(st.session_state[_SS_PRESETS], ensure_ascii=False, indent=2).encode("utf-8")
    except Exception:
        return b"[]"

# ---------- fabric.js JSON -> Items ----------
def _cm_int(x: float) -> int:
    try:
        return int(round(float(x)))
    except Exception:
        return 0

def _normalize_rect(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Mappt fabric.js-Objekt -> cm-Koordinaten (1 px = 1 cm, da Canvas 1360x240)."""
    if not isinstance(obj, dict) or obj.get("type") != "rect":
        return None
    left   = obj.get("left", 0)
    top    = obj.get("top", 0)
    width  = obj.get("width", 0)
    height = obj.get("height", 0)
    sx = obj.get("scaleX", 1) or 1
    sy = obj.get("scaleY", 1) or 1

    w = (width  or 0) * sx
    h = (height or 0) * sy

    x_cm = max(0, min(TRAILER_LEN_CM, _cm_int(left)))
    y_cm = max(0, min(TRAILER_W_CM,   _cm_int(top)))
    w_cm = max(1, min(TRAILER_LEN_CM - x_cm, _cm_int(w)))
    h_cm = max(1, min(TRAILER_W_CM   - y_cm, _cm_int(h)))

    # Typ nur zur Anzeige/Färbung schätzen (Euro 120×80/80×120, Industrie 120×100)
    typ = "Custom"
    pair = (min(w_cm, h_cm), max(w_cm, h_cm))
    if pair == (80, 120):
        typ = "Euro"
    elif pair == (100, 120):
        typ = "Industrie"

    return {"x_cm": x_cm, "y_cm": y_cm, "w_cm": w_cm, "h_cm": h_cm, "typ": typ}

def _json_to_items(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not json_data:
        return []
    objs = json_data.get("objects") or []
    out: List[Dict[str, Any]] = []
    for o in objs:
        r = _normalize_rect(o)
        if r:
            out.append(r)
    return out

# ---------- Canvas-Manager ----------
def render_manager(title: str = "Eigene Layouts (Vers 1–4)", show_expander: bool = True) -> List[Dict[str, Any]]:
    """Zeigt einen 1360×240 Canvas. Robust: minimaler st_canvas-Aufruf ohne background_* & fill_color."""
    _ensure_session()
    items: List[Dict[str, Any]] = []

    container = st.expander(title, expanded=show_expander) if show_expander else st.container()
    with container:
        if not _HAS_CANVAS:
            st.info("Canvas ist deaktiviert (Paket fehlt oder Fehler beim Import).")
            return []

        st.caption("Rechtecke (Paletten) auf Trailer (1 px = 1 cm) zeichnen. Größen nachträglich anpassen.")

        # --- Minimal & stabil: nur essenzielle Parameter ---
        try:
            canvas_result = st_canvas(
                width=TRAILER_LEN_CM,           # 1360
                height=TRAILER_W_CM,            # 240
                drawing_mode="rect",
                stroke_width=2,
                stroke_color="#222222",
                key="pf_canvas",                 # fester Key (ein Canvas)
                update_streamlit=True,
            )
        except Exception as e:
            st.error(f"Canvas konnte nicht initialisiert werden: {e!s}")
            return []

        items = _json_to_items(canvas_result.json_data if canvas_result else None)

        # Meta aktualisieren
        total_pal = sum(1 for it in items if it["typ"] in ("Euro", "Industrie"))
        st.session_state[_SS_LAST_META] = UserMeta(name="Canvas", total_pal=total_pal, heavy_count=0)

        # Preset-Steuerung
        col = st.columns([1, 1, 1])
        with col[0]:
            preset_name = st.text_input("Preset-Name", value=f"Layout {len(st.session_state[_SS_PRESETS]) + 1}")
        with col[1]:
            if st.button("Preset speichern", use_container_width=True):
                st.session_state[_SS_PRESETS].append({"name": preset_name, "items": items})
                st.success(f"Preset „{preset_name}“ gespeichert ({len(items)} Objekte).")
        with col[2]:
            if st.button("Alle Presets löschen", use_container_width=True):
                st.session_state[_SS_PRESETS] = []
                st.warning("Alle Presets gelöscht.")

        # Optional: Roh-JSON zur Diagnose
        if st.checkbox("Canvas-JSON anzeigen", value=False):
            st.json(canvas_result.json_data or {})

    return items
