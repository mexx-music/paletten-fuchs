# custom_layouts.py — Paletten Fuchs 9.5 (Fixgrößen + L/M/R-Ausrichten, ohne Blinken)
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
_SS_PRESETS        = "pf_presets"
_SS_LAST_META      = "pf_last_meta"
_SS_CANVAS_OBJS    = "pf_canvas_objs"       # persistierte fabric-Objekte (Quelle der Wahrheit)
_SS_NEXT_POS_IDX   = "pf_next_pos_idx"      # einfache Auto-Positionierung
_SS_PENDING_JSON   = "pf_canvas_pending"    # zuletzt vom Canvas gelesener Stand (nur Vorschau, nicht committet)

def _ensure_session():
    if _SS_PRESETS not in st.session_state:
        st.session_state[_SS_PRESETS] = []
    if _SS_LAST_META not in st.session_state:
        st.session_state[_SS_LAST_META] = UserMeta()
    if _SS_CANVAS_OBJS not in st.session_state:
        st.session_state[_SS_CANVAS_OBJS] = []
    if _SS_NEXT_POS_IDX not in st.session_state:
        st.session_state[_SS_NEXT_POS_IDX] = 0
    if _SS_PENDING_JSON not in st.session_state:
        st.session_state[_SS_PENDING_JSON] = None

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

# ---------- Fabric Helpers ----------
def _fabric_rect(x: int, y: int, w: int, h: int, label: str) -> Dict[str, Any]:
    """Fabric-Rect mit fixen Größen (nur bewegen/rotieren erlaubt). 1 px = 1 cm."""
    return {
        "type": "rect",
        "left": x, "top": y,
        "width": w, "height": h,
        "fill": "rgba(0,0,0,0)",    # transparent; Farbe macht app.py
        "stroke": "#222222", "strokeWidth": 2,
        "angle": 0,
        "selectable": True, "evented": True,
        "hasControls": False,       # keine Größenhandles
        "lockScalingX": True, "lockScalingY": True, "lockUniScaling": True,
        "lockRotation": False,
        "name": label,              # "Euro" | "Industrie"
        "scaleX": 1, "scaleY": 1,
    }

def _add_fixed_rect(kind: str):
    """Fügt ein fixgroßes Objekt an 'nächster' Position hinzu."""
    _ensure_session()
    if kind == "EURO_LONG":
        w, h, typ = 120, 80, "Euro"
    elif kind == "EURO_TRANS":
        w, h, typ = 80, 120, "Euro"
    elif kind == "IND":
        w, h, typ = 120, 100, "Industrie"
    else:
        return
    idx = st.session_state[_SS_NEXT_POS_IDX]
    gap = 8
    per_row = max(1, TRAILER_LEN_CM // (w + gap))
    row = idx // per_row
    col = idx % per_row
    x = min(TRAILER_LEN_CM - w, 10 + col * (w + gap))
    y = min(TRAILER_W_CM - h, 10 + row * (max(100, h) + gap))
    st.session_state[_SS_CANVAS_OBJS].append(_fabric_rect(x, y, w, h, typ))
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
    """fabric.js -> cm-Koordinaten + Typ (aus 'name'); Fixgrößen erzwungen."""
    if not isinstance(obj, dict) or obj.get("type") != "rect":
        return None
    left   = int(round((obj.get("left") or 0)))
    top    = int(round((obj.get("top")  or 0)))
    width  = int(round((obj.get("width")  or 0) * (obj.get("scaleX") or 1)))
    height = int(round((obj.get("height") or 0) * (obj.get("scaleY") or 1)))
    typ = obj.get("name") or "Custom"

    # Bounds
    left = max(0, min(TRAILER_LEN_CM - 1, left))
    top  = max(0, min(TRAILER_W_CM  - 1, top))
    width  = max(1, min(TRAILER_LEN_CM - left, width))
    height = max(1, min(TRAILER_W_CM   - top,  height))

    # Fixgrößen
    if typ == "Euro":
        if width < height: width, height = 80, 120
        else:              width, height = 120, 80
    elif typ == "Industrie":
        width, height = 120, 100

    return {"x_cm": left, "y_cm": top, "w_cm": width, "h_cm": height, "typ": typ}

def _json_to_items(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not json_data: return []
    objs = json_data.get("objects") or []
    out: List[Dict[str, Any]] = []
    for o in objs:
        r = _normalize_rect(o)
        if r: out.append(r)
    return out

# ---------- L/M/R Ausrichten ----------
def _align(scope: str, pos: str):
    """Y-Ausrichtung: left=0, center=(240-h)/2, right=240-h."""
    _ensure_session()
    objs = st.session_state[_SS_CANVAS_OBJS]
    if not objs: return
    targets = [len(objs)-1] if scope == "last" else list(range(len(objs)))
    for i in targets:
        o = dict(objs[i])
        h = int(round((o.get("height") or 0) * (o.get("scaleY") or 1)))
        if pos == "left":   top = 0
        elif pos == "right": top = max(0, TRAILER_W_CM - h)
        else:               top = max(0, (TRAILER_W_CM - h) // 2)
        o["top"] = top
        objs[i] = o

# ---------- Canvas-Manager ----------
def render_manager(title: str = "Eigene Layouts (Vers 1–4)", show_expander: bool = True) -> List[Dict[str, Any]]:
    """Canvas ohne Blinken: update_streamlit=False. Fixgrößen + L/M/R-Ausrichten + '⏎ Übernehmen'."""
    _ensure_session()
    items: List[Dict[str, Any]] = []

    container = st.expander(title, expanded=show_expander) if show_expander else st.container()
    with container:
        if not _HAS_CANVAS:
            st.info("Canvas ist deaktiviert (Paket fehlt oder Fehler beim Import).")
            return []

        st.caption("Füge Paletten hinzu (fixe Größe). Verschiebe per Drag in X. Y-Ausrichten mit Buttons (Links/Mitte/Rechts). '⏎ Übernehmen' speichert.")

        # Hinzufügen/Löschen
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

        # Ausrichten
        scope = st.radio("Ausrichten für …", ["zuletzt", "alle"], horizontal=True, index=0)
        s_left, s_center, s_right = st.columns(3)
        with s_left:
            if st.button("⟸ Links", use_container_width=True):
                _align("last" if scope=="zuletzt" else "all", "left")
        with s_center:
            if st.button("◎ Mitte", use_container_width=True):
                _align("last" if scope=="zuletzt" else "all", "center")
        with s_right:
            if st.button("⟹ Rechts", use_container_width=True):
                _align("last" if scope=="zuletzt" else "all", "right")

        # Canvas-Initialisierung aus persistierten Objekten
        initial_json = {"version": "5.2.4", "objects": st.session_state[_SS_CANVAS_OBJS]}

        # WICHTIG: Kein Blinken -> update_streamlit=False (keine Live-Reruns bei Drag)
        try:
            canvas_result = st_canvas(
                width=TRAILER_LEN_CM,
                height=TRAILER_W_CM,
                drawing_mode="transform",   # nur bewegen/selektieren
                stroke_width=2,
                stroke_color="#222222",
                key="pf_canvas",
                update_streamlit=False,     # <<< verhindert Blinken
                initial_drawing=initial_json,
            )
        except Exception as e:
            st.error(f"Canvas konnte nicht initialisiert werden: {e!s}")
            return []

        # „⏎ Übernehmen“: Pending JSON -> persistieren
        if st.button("⏎ Übernehmen (Positionen speichern)", use_container_width=True):
            if canvas_result and canvas_result.json_data:
                new_objs = canvas_result.json_data.get("objects") or []
                fixed_objs: List[Dict[str, Any]] = []
                for o in new_objs:
                    r = _normalize_rect(o)
                    if not r: 
                        continue
                    fixed_objs.append(_fabric_rect(r["x_cm"], r["y_cm"], r["w_cm"], r["h_cm"], r["typ"]))
                st.session_state[_SS_CANVAS_OBJS] = fixed_objs
                st.success("Positionen gespeichert.")

        # Items an App zurückgeben (IMMER aus persistierter Quelle)
        items = _json_to_items({"objects": st.session_state[_SS_CANVAS_OBJS]})

        # Meta
        total_pal = sum(1 for it in items if it["typ"] in ("Euro", "Industrie"))
        st.session_state[_SS_LAST_META] = UserMeta(name="Canvas", total_pal=total_pal, heavy_count=0)

        # Presets
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
