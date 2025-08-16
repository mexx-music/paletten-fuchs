# custom_layouts.py — Presets-Editor (Auto-Snap, stabil, echt fixierbar)
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

@dataclass
class UserMeta:
    name: str = "Preset"
    total_pal: int = 0
    heavy_count: int = 0

# Session Keys
_SS_PRESETS   = "pf_presets"
_SS_META      = "pf_last_meta"
_SS_OBJS      = "pf_canvas_objs"     # Quelle der Wahrheit (persistiert)
_SS_NEXT_IDX  = "pf_next_pos_idx"
_SS_LOCKED    = "pf_locked"          # True => gesperrt
_SS_SNAP_CM   = "pf_snap_cm"         # Raster (cm)

def _ensure():
    if _SS_PRESETS not in st.session_state: st.session_state[_SS_PRESETS] = []
    if _SS_META not in st.session_state:    st.session_state[_SS_META]    = UserMeta()
    if _SS_OBJS not in st.session_state:    st.session_state[_SS_OBJS]    = []
    if _SS_NEXT_IDX not in st.session_state:st.session_state[_SS_NEXT_IDX]= 0
    if _SS_LOCKED not in st.session_state:  st.session_state[_SS_LOCKED]  = False
    if _SS_SNAP_CM not in st.session_state: st.session_state[_SS_SNAP_CM] = 10

def get_active_meta() -> UserMeta:
    _ensure()
    return st.session_state[_SS_META]

def export_all_presets_json() -> bytes:
    import json
    _ensure()
    try:
        return json.dumps(st.session_state[_SS_PRESETS], ensure_ascii=False, indent=2).encode("utf-8")
    except Exception:
        return b"[]"

# ---------- Utils ----------
def _snap(v: int, step: int) -> int:
    if step <= 1: return int(v)
    return int(round(v / step) * step)

def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))

def _apply_snap_xy(x: int, y: int, w: int, h: int, step: int) -> (int,int):
    x = _clamp(_snap(x, step), 0, max(0, TRAILER_LEN_CM - w))
    y = _clamp(_snap(y, step), 0, max(0, TRAILER_W_CM  - h))
    return x, y

# ---------- Fabric Helpers ----------
def _fabric_rect(x: int, y: int, w: int, h: int, label: str, selectable: bool) -> Dict[str, Any]:
    return {
        "type": "rect",
        "left": x, "top": y,
        "width": w, "height": h,
        "fill": "rgba(0,0,0,0)",
        "stroke": "#222222", "strokeWidth": 2,
        "angle": 0,
        "selectable": bool(selectable),
        "evented": bool(selectable),
        "hasControls": False,
        "lockScalingX": True, "lockScalingY": True, "lockUniScaling": True,
        "lockRotation": True,
        "name": label,          # "Euro" | "Industrie"
        "scaleX": 1, "scaleY": 1,
    }

def _fix_size(name: str, w: int, h: int) -> (int,int):
    if name == "Euro":
        return (80,120) if w < h else (120,80)
    if name == "Industrie":
        return (120,100)
    return (w,h)

# ---------- State Mutators ----------
def _commit_from_canvas(json_data: Optional[Dict[str, Any]]):
    """Auto-Übernahme + Snap des *aktuellen* Canvas-Stands bei jedem Rerun."""
    _ensure()
    if st.session_state[_SS_LOCKED]:   # gesperrt => nicht übernehmen
        return
    if not json_data:
        return
    step = st.session_state[_SS_SNAP_CM]
    new_objs: List[Dict[str, Any]] = []
    for o in (json_data.get("objects") or []):
        if not isinstance(o, dict) or o.get("type") != "rect":
            continue
        name = o.get("name") or "Custom"
        w = int(round((o.get("width") or 0)  * (o.get("scaleX") or 1)))
        h = int(round((o.get("height") or 0) * (o.get("scaleY") or 1)))
        w,h = _fix_size(name, w, h)
        x = int(round(o.get("left") or 0))
        y = int(round(o.get("top")  or 0))
        x,y = _apply_snap_xy(x, y, w, h, step)   # <<< Auto-Snap IMMER
        new_objs.append(_fabric_rect(x, y, w, h, name, selectable=True))
    # Nur ersetzen, wenn wir wirklich Daten bekommen haben
    if new_objs:
        st.session_state[_SS_OBJS] = new_objs

def _add(kind: str):
    _ensure()
    if st.session_state[_SS_LOCKED]: return
    if kind == "EURO_LONG": w,h,name = 120,80,"Euro"
    elif kind == "EURO_TRANS": w,h,name = 80,120,"Euro"
    elif kind == "IND": w,h,name = 120,100,"Industrie"
    else: return
    idx  = st.session_state[_SS_NEXT_IDX]
    gap  = 8
    per  = max(1, TRAILER_LEN_CM // (w + gap))
    row, col = idx // per, idx % per
    x = min(TRAILER_LEN_CM - w, 10 + col*(w+gap))
    y = min(TRAILER_W_CM  - h, 10 + row*(max(100,h)+gap))
    x,y = _apply_snap_xy(x, y, w, h, st.session_state[_SS_SNAP_CM])
    st.session_state[_SS_OBJS].append(_fabric_rect(x,y,w,h,name, selectable=True))
    st.session_state[_SS_NEXT_IDX] += 1

def _delete_last():
    _ensure()
    if st.session_state[_SS_LOCKED]: return
    if st.session_state[_SS_OBJS]:
        st.session_state[_SS_OBJS].pop()
        st.session_state[_SS_NEXT_IDX] = max(0, st.session_state[_SS_NEXT_IDX]-1)

def _delete_all():
    _ensure()
    if st.session_state[_SS_LOCKED]: return
    st.session_state[_SS_OBJS] = []
    st.session_state[_SS_NEXT_IDX] = 0

def _align(scope_last: bool, pos: str):
    _ensure()
    if st.session_state[_SS_LOCKED]: return
    objs = st.session_state[_SS_OBJS]
    if not objs: return
    step = st.session_state[_SS_SNAP_CM]
    targets = [len(objs)-1] if scope_last else list(range(len(objs)))
    for i in targets:
        o = dict(objs[i])
        name = o.get("name") or "Custom"
        w,h = _fix_size(name, int(o.get("width") or 0), int(o.get("height") or 0))
        if pos == "left":   y = 0
        elif pos == "right":y = TRAILER_W_CM - h
        else:               y = (TRAILER_W_CM - h)//2
        x = int(o.get("left") or 0)
        x,y = _apply_snap_xy(x, y, w, h, step)
        o["left"], o["top"], o["width"], o["height"] = x,y,w,h
        objs[i] = o

def _set_locked(flag: bool):
    _ensure()
    st.session_state[_SS_LOCKED] = bool(flag)
    new = []
    for o in st.session_state[_SS_OBJS]:
        q = dict(o)
        q["selectable"] = not flag
        q["evented"]    = not flag
        new.append(q)
    st.session_state[_SS_OBJS] = new

# ---------- Public UI ----------
def render_manager(title: str = "Eigene Layouts (Presets-Editor)", show_expander: bool = True) -> List[Dict[str, Any]]:
    """Canvas NUR für Presets. Auto-Snap & stabile Positionen. Fixierbar."""
    _ensure()
    items: List[Dict[str, Any]] = []

    ct = st.expander(title, expanded=show_expander) if show_expander else st.container()
    with ct:
        if not _HAS_CANVAS:
            st.info("Canvas nicht verfügbar.")
            return []

        # Kopf: Raster & Lock
        ctop = st.columns([1.1, 1, 1.4])
        with ctop[0]:
            snap_cm = st.number_input("Snap-Raster (cm)", 1, 100, st.session_state[_SS_SNAP_CM], step=1)
            st.session_state[_SS_SNAP_CM] = int(snap_cm)
        with ctop[1]:
            locked = st.toggle("Fixiert (gesperrt)", value=st.session_state[_SS_LOCKED])
            if locked != st.session_state[_SS_LOCKED]:
                _set_locked(locked)
        with ctop[2]:
            st.caption("1 px = 1 cm · Trailer 1360×240 cm (Canvas nur für Presets)")

        # --- WICHTIG: Canvas zuerst rendern & AKTUELLEN Stand einlesen ---
        initial_json = {"version": "5.2.4", "objects": st.session_state[_SS_OBJS]}
        try:
            canvas_result = st_canvas(
                width=TRAILER_LEN_CM,
                height=TRAILER_W_CM,
                drawing_mode=("transform" if not st.session_state[_SS_LOCKED] else "none"),
                stroke_width=2,
                stroke_color="#222222",
                key="pf_canvas",
                update_streamlit=True,      # <<< sorgt dafür, dass Drag-Positionen ankommen
                initial_drawing=initial_json,
            )
        except Exception as e:
            st.error(f"Canvas konnte nicht initialisiert werden: {e!s}")
            return []

        # Auto-Commit (inkl. Snap) des letzten Stands
        if canvas_result and canvas_result.json_data:
            _commit_from_canvas(canvas_result.json_data)

        # Buttons (wirken auf den frisch übernommenen Stand, daher kein „Springen“)
        b1,b2,b3,b4,b5 = st.columns(5)
        with b1:
            st.button("➕ Euro längs 120×80", on_click=_add, args=("EURO_LONG",), disabled=st.session_state[_SS_LOCKED])
        with b2:
            st.button("➕ Euro quer 80×120",  on_click=_add, args=("EURO_TRANS",), disabled=st.session_state[_SS_LOCKED])
        with b3:
            st.button("➕ Industrie 120×100", on_click=_add, args=("IND",), disabled=st.session_state[_SS_LOCKED])
        with b4:
            st.button("⟲ Letzte löschen", on_click=_delete_last, disabled=st.session_state[_SS_LOCKED])
        with b5:
            st.button("✖ Alles löschen", on_click=_delete_all, disabled=st.session_state[_SS_LOCKED])

        scope = st.radio("Ausrichten für …", ["zuletzt", "alle"], horizontal=True, index=0, disabled=st.session_state[_SS_LOCKED])
        s1,s2,s3 = st.columns(3)
        with s1:
            st.button("⟸ Links", on_click=_align, args=(scope=="zuletzt","left"), disabled=st.session_state[_SS_LOCKED])
        with s2:
            st.button("◎ Mitte", on_click=_align, args=(scope=="zuletzt","mid"),  disabled=st.session_state[_SS_LOCKED])
        with s3:
            st.button("⟹ Rechts",on_click=_align, args=(scope=="zuletzt","right"),disabled=st.session_state[_SS_LOCKED])

        # Items zurückgeben (aus persistiertem Stand)
        objs = st.session_state[_SS_OBJS]
        items = []
        for o in objs:
            name = o.get("name") or "Custom"
            w,h = _fix_size(name, int(o.get("width") or 0), int(o.get("height") or 0))
            x   = int(o.get("left") or 0)
            y   = int(o.get("top")  or 0)
            items.append({"x_cm": x, "y_cm": y, "w_cm": w, "h_cm": h, "typ": name})

        # Meta
        total_pal = sum(1 for it in items if it["typ"] in ("Euro","Industrie"))
        st.session_state[_SS_META] = UserMeta(name="Canvas", total_pal=total_pal, heavy_count=0)

        # Presets
        col = st.columns([1,1,1])
        with col[0]:
            preset_name = st.text_input("Preset-Name", value=f"Layout {len(st.session_state[_SS_PRESETS])+1}")
        with col[1]:
            if st.button("Preset speichern"):
                st.session_state[_SS_PRESETS].append({"name": preset_name, "items": items})
                st.success(f"Preset „{preset_name}“ gespeichert ({len(items)} Objekte).")
        with col[2]:
            if st.button("Alle Presets löschen"):
                st.session_state[_SS_PRESETS] = []
                st.warning("Alle Presets gelöscht.")

        # Diagnose optional
        if st.checkbox("Canvas-JSON anzeigen", value=False):
            st.json({"objects": st.session_state[_SS_OBJS]})

    return items
