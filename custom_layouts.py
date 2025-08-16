# custom_layouts.py — Paletten Fuchs 9.5 (Fixgrößen + Buttons)
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import streamlit as st

# Drawable-Canvas
try:
    from streamlit_drawable_canvas import st_canvas
    _HAS_CANVAS = True
except Exception as _e:
    st.warning(f"Drawable-Canvas nicht verfügbar: {_e!s}")
    _HAS_CANVAS = False

TRAILER_LEN_CM = 1360
TRAILER_W_CM   = 240

# ---------- Meta ----------
@dataclass
class UserMeta:
    name: str = "Preset 1"
    total_pal: int = 0
    heavy_count: int = 0

# Session Keys
_SS_PRESETS       = "pf_presets"
_SS_LAST_META     = "pf_last_meta"
_SS_CANVAS_OBJS   = "pf_canvas_objs"      # fabric.js objects (persistiert)
_SS_NEXT_POS_IDX  = "pf_next_pos_idx"     # einfache Auto-Positionierung

def _ensure_session():
    if _SS_PRESETS not in st.session_state:
        st.session_state[_SS_PRESETS] = []
    if _SS_LAST_META not in st.session_state:
        st.session_state[_SS_LAST_META] = UserMeta()
    if _SS_CANVAS_OBJS not in st.session_state:
        st.session_state[_SS_CANVAS_OBJS] = []
    if _SS_NEXT_POS_IDX not in st.session_state:
        st.session_state[_SS_NEXT_POS_IDX] = 0

def get_active_meta() -> UserMeta:
    _ensure_session()
    return st.session_state[_SS_LAST_META]

def export_all_presets_json() -> bytes:
    import json
    _ensure_session()
    try:
        return json.dumps(st.session_state[_SS_PRESETS], ensure_ascii=False, indent=2).encode("utf-8")
    except Exception:
        return b"[]"

# ---------- fabric.js Helper ----------
def _fabric_rect(x: int, y: int, w: int, h: int, label: str) -> Dict[str, Any]:
    """Erzeuge ein Fabric-Rect mit LOCKED scaling (nur bewegen/rotieren). 1 px = 1 cm."""
    return {
        "type": "rect",
        "left": x, "top": y,
        "width": w, "height": h,
        "fill": "rgba(0,0,0,0)",   # transparent; Farbe machen wir in app.py-Grafik
        "stroke": "#222222", "strokeWidth": 2,
        "angle": 0,
        "selectable": True,
        "evented": True,
        "hasControls": False,      # keine Größenhandles
        "lockScalingX": True,
        "lockScalingY": True,
        "lockUniScaling": True,
        "lockRotation": False,
        "name": label,             # eigene Kennung
        # fabric erwartet evtl. scaleX/scaleY; auf 1 setzen
        "scaleX": 1, "scaleY": 1,
    }

def _add_fixed_rect(kind: str):
    """Fügt ein fixgroßes Objekt an 'nächster' Position hinzu."""
    _ensure_session()
    # Fixgrößen in CM
    if kind == "EURO_LONG":
        w, h, typ = 120, 80, "Euro"
    elif kind == "EURO_TRANS":
        w, h, typ = 80, 120, "Euro"
    elif kind == "IND":
        w, h, typ = 120, 100, "Industrie"
    else:
        return

    # Simple Auto-Positionierung in Zeilen (ohne Überlappung – grob)
    idx = st.session_state[_SS_NEXT_POS_IDX]
    gap = 8
    per_row = max(1, TRAILER_LEN_CM // (w + gap))
    row = idx // per_row
    col = idx % per_row
    x = min(TRAILER_LEN_CM - w, 10 + col * (w + gap))
    y = min(TRAILER_W_CM - h, 10 + row * (max(100, h) + gap))

    obj = _fabric_rect(x, y, w, h, typ)
    st.session_state[_SS_CANVAS_OBJS].append(obj)
    st.session_state[_SS_NEXT_POS_IDX] += 1

def _delete_last():
    _ensure_session()
    if st.session_state[_SS_CANVAS_OBJS]:
        st.session_state[_SS_CANVAS_OBJS].pop()
        st.session_state[_SS_NEXT_POS_IDX] = max(0, st.session_state[_SS_NEXT_POS_IDX]-1)

def _delete_all():
    _ensure_session()
    st.session_state[_SS_CANVAS_OBJS] = []
    st.session_state[_SS_NEXT_POS_IDX] = 0

def _normalize_rect(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """fabric.js -> cm-Koordinaten + Typ (aus 'name'). Größen sind fix hinterlegt."""
    if not isinstance(obj, dict) or obj.get("type") != "rect":
        return None
    left   = int(round((obj.get("left") or 0)))
    top    = int(round((obj.get("top")  or 0)))
    width  = int(round((obj.get("width")  or 0) * (obj.get("scaleX") or 1)))
    height = int(round((obj.get("height") or 0) * (obj.get("scaleY") or 1)))
    typ = obj.get("name") or "Custom"

    # Auf Trailer begrenzen
    left = max(0, min(TRAILER_LEN_CM - 1, left))
    top  = max(0, min(TRAILER_W_CM  - 1, top))
    width  = max(1, min(TRAILER_LEN_CM - left, width))
    height = max(1, min(TRAILER_W_CM   - top,  height))

    # Typ -> exakte Fixgröße (sichert gegen manuelles Resizing; ist eh gelockt)
    if typ == "Euro":
        # entscheiden anhand Orientierung
        if width < height:
            width, height = 80, 120
        else:
            width, height = 120, 80
    elif typ == "Industrie":
        width, height = 120, 100

    return {"x_cm": left, "y_cm": top, "w_cm": width, "h_cm": height, "typ": typ}

def _json_to_items(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not json_data:
        return []
    objs = json_data.get("objects") or []
    out: List[Dict[str, Any]] = []
    for o in objs:
        r = _normalize_rect(o)
        if r: out.append(r)
    return out

# ---------- Canvas-Manager ----------
def render_manager(title: str = "Eigene Layouts (Vers 1–4)", show_expander: bool = True) -> List[Dict[str, Any]]:
    """Canvas mit Fixgrößen-Buttons. Bewegen erlaubt, Skalieren gesperrt. 1 px = 1 cm."""
    _ensure_session()
    items: List[Dict[str, Any]] = []

    container = st.expander(title, expanded=show_expander) if show_expander else st.container()
    with container:
        if not _HAS_CANVAS:
            st.info("Canvas ist deaktiviert (Paket fehlt oder Fehler beim Import).")
            return []

        st.caption("Füge Paletten mit den Buttons hinzu (fixe Größe). Bewegen erlaubt, Skalieren gesperrt.")

        # Button-Leiste
        b1, b2, b3, b4, b5 = st.columns([1,1,1,1,1])
        with b1:
            if st.button("➕ Euro längs (120×80)", use_container_width=True):
                _add_fixed_rect("EURO_LONG")
        with b2:
            if st.button("➕ Euro quer (80×120)", use_container_width=True):
                _add_fixed_rect("EURO_TRANS")
        with b3:
            if st.button("➕ Industrie (120×100)", use_container_width=True):
                _add_fixed_rect("IND")
        with b4:
            if st.button("⟲ Letzte löschen", use_container_width=True):
                _delete_last()
        with b5:
            if st.button("✖ Alles löschen", use_container_width=True):
                _delete_all()

        # Initial-Drawing aus Session-Objekten
        initial_json = {
            "version": "5.2.4",
            "objects": st.session_state[_SS_CANVAS_OBJS]
        }

        # Minimal & stabiler Canvas-Call (nur nötige Parameter + initial_drawing)
        try:
            canvas_result = st_canvas(
                width=TRAILER_LEN_CM,
                height=TRAILER_W_CM,
                drawing_mode="transform",   # nur bewegen/selektieren
                stroke_width=2,
                stroke_color="#222222",
                key="pf_canvas",
                update_streamlit=True,
                initial_drawing=initial_json,
            )
        except Exception as e:
            st.error(f"Canvas konnte nicht initialisiert werden: {e!s}")
            return []

        # Rückdaten übernehmen (Positionen), Größen wieder auf Fixwerte clampen
        if canvas_result and canvas_result.json_data:
            new_objs = canvas_result.json_data.get("objects") or []
            # wir übernehmen neue left/top, erzwingen aber wieder Fixgrößen & Locks
            fixed_objs: List[Dict[str, Any]] = []
            for o in new_objs:
                r = _normalize_rect(o)
                if not r: 
                    continue
                # zurück in fabric-Objekt (Fixgröße + Locks)
                fab = _fabric_rect(r["x_cm"], r["y_cm"], r["w_cm"], r["h_cm"], r["typ"])
                fixed_objs.append(fab)
            st.session_state[_SS_CANVAS_OBJS] = fixed_objs

        # Items an App zurückgeben
        items = _json_to_items({"objects": st.session_state[_SS_CANVAS_OBJS]})

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
            if st.button("Alle Presets löschen (Presets)", use_container_width=True):
                st.session_state[_SS_PRESETS] = []
                st.warning("Alle Presets gelöscht.")

        # Diagnose optional
        if st.checkbox("Canvas-JSON anzeigen", value=False):
            st.json({"objects": st.session_state[_SS_CANVAS_OBJS]})

    return items
