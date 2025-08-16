# custom_layouts.py — Presets-Editor (stabil, Snap, pfid, default gesperrt)
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import streamlit as st

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

# Session keys
_SS_PRESETS  = "pf_presets"
_SS_META     = "pf_last_meta"
_SS_OBJS     = "pf_canvas_objs"   # fabric-Objekte mit pfid
_SS_NEXTIDX  = "pf_next_pos_idx"
_SS_NEXTPID  = "pf_next_pid"      # fortlaufende, persistente ID
_SS_LOCKED   = "pf_locked"        # True => gesperrt (kein Drag)
_SS_EDIT     = "pf_edit_drag"     # True => Edit/Drag-Modus aktiv
_SS_SNAP_X   = "pf_snap_x"        # X-Raster (cm)

def _ensure():
    if _SS_PRESETS not in st.session_state: st.session_state[_SS_PRESETS] = []
    if _SS_META not in st.session_state:    st.session_state[_SS_META]    = UserMeta()
    if _SS_OBJS not in st.session_state:    st.session_state[_SS_OBJS]    = []
    if _SS_NEXTIDX not in st.session_state: st.session_state[_SS_NEXTIDX] = 0
    if _SS_NEXTPID not in st.session_state: st.session_state[_SS_NEXTPID] = 1
    if _SS_LOCKED not in st.session_state:  st.session_state[_SS_LOCKED]  = True   # <<< standard: gesperrt
    if _SS_EDIT not in st.session_state:    st.session_state[_SS_EDIT]    = False  # <<< Drag aus
    if _SS_SNAP_X not in st.session_state:  st.session_state[_SS_SNAP_X]  = 10

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
def _snap_grid(v: int, step: int) -> int:
    if step <= 1: return int(v)
    return int(round(v / step) * step)

def _fix_size(name: str, w: int, h: int) -> (int,int):
    if name == "Euro":
        return (80,120) if w < h else (120,80)
    if name == "Industrie":
        return (120,100)
    return (w,h)

def _snap_xy(name: str, x: int, y: int, w: int, h: int, step_x: int) -> (int,int):
    # X: Raster
    x = max(0, min(TRAILER_LEN_CM - w, _snap_grid(x, step_x)))
    # Y: auf nächstgelegene L/M/R
    y_left  = 0
    y_mid   = (TRAILER_W_CM - h) // 2
    y_right = TRAILER_W_CM - h
    y = min(((abs(y - y_left), y_left),
             (abs(y - y_mid),  y_mid),
             (abs(y - y_right),y_right)), key=lambda t: t[0])[1]
    return x, y

# ---------- Fabric Helpers ----------
def _fabric_rect(pfid: int, x: int, y: int, w: int, h: int, label: str, selectable: bool) -> Dict[str, Any]:
    return {
        "type": "rect",
        "pfid": pfid,
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
        "name": label,
        "scaleX": 1, "scaleY": 1,
    }

# ---------- Stable commit (kein Springen) ----------
def _commit_from_canvas(json_data: Optional[Dict[str, Any]]):
    """Übernimmt aktuellen Canvas-Stand stabil: match per pfid, snap X + Y(L/M/R), Reihenfolge bleibt."""
    _ensure()
    if st.session_state[_SS_LOCKED] or not json_data:
        return
    by_id = {o.get("pfid"): o for o in (json_data.get("objects") or []) if isinstance(o, dict) and o.get("type") == "rect"}
    step_x = st.session_state[_SS_SNAP_X]
    new_list: List[Dict[str, Any]] = []

    for o in st.session_state[_SS_OBJS]:
        pfid = o.get("pfid")
        base = dict(o)
        if pfid in by_id:
            src  = by_id[pfid]
            name = src.get("name") or base.get("name") or "Custom"
            w = int(round((src.get("width")  or base.get("width")  or 0) * (src.get("scaleX") or 1)))
            h = int(round((src.get("height") or base.get("height") or 0) * (src.get("scaleY") or 1)))
            w,h = _fix_size(name, w, h)
            x = int(round(src.get("left") or base.get("left") or 0))
            y = int(round(src.get("top")  or base.get("top")  or 0))
            x,y = _snap_xy(name, x, y, w, h, step_x)  # <<< auto-snap beim Commit
            base.update({"left": x, "top": y, "width": w, "height": h, "name": name})
        new_list.append(base)

    st.session_state[_SS_OBJS] = new_list

# ---------- Commands ----------
def _add(kind: str):
    _ensure()
    # immer zuerst committen, damit Alt-Objekte nicht springen:
    # (wir lesen den letzten Stand ein, snappen ihn und schreiben in-place zurück)
    # => Buttons wirken auf stabile Basis.
    # Edit muss NICHT aktiv sein; commit übernimmt nur, wenn unlocked.
    # (Bei Lock passiert nichts.)
    # Hinweis: canvas_result.json_data wird in render_manager vorher übergeben.
    # Hier kein Zugriff – daher kein weiterer Commit hier.

    if st.session_state[_SS_LOCKED]: return
    if kind == "EURO_LONG": w,h,name = 120,80,"Euro"
    elif kind == "EURO_TRANS": w,h,name = 80,120,"Euro"
    elif kind == "IND": w,h,name = 120,100,"Industrie"
    else: return

    idx = st.session_state[_SS_NEXTIDX]
    gap = 8
    per = max(1, TRAILER_LEN_CM // (w + gap))
    row, col = idx // per, idx % per
    x0 = min(TRAILER_LEN_CM - w, 10 + col * (w + gap))
    y0 = min(TRAILER_W_CM  - h, 10 + row * (max(100, h) + gap))
    x,y = _snap_xy(name, x0, y0, w, h, st.session_state[_SS_SNAP_X])

    pfid = st.session_state[_SS_NEXTPID]; st.session_state[_SS_NEXTPID] += 1
    st.session_state[_SS_OBJS].append(_fabric_rect(pfid, x, y, w, h, name, selectable=st.session_state[_SS_EDIT]))
    st.session_state[_SS_NEXTIDX] += 1

def _delete_last():
    _ensure()
    if st.session_state[_SS_LOCKED]: return
    if st.session_state[_SS_OBJS]:
        st.session_state[_SS_OBJS].pop()
        st.session_state[_SS_NEXTIDX] = max(0, st.session_state[_SS_NEXTIDX]-1)

def _delete_all():
    _ensure()
    if st.session_state[_SS_LOCKED]: return
    st.session_state[_SS_OBJS] = []
    st.session_state[_SS_NEXTIDX] = 0

def _align(scope_last: bool, pos: str):
    _ensure()
    if st.session_state[_SS_LOCKED]: return
    objs = st.session_state[_SS_OBJS]
    if not objs: return
    targets = [len(objs)-1] if scope_last else list(range(len(objs)))
    step_x = st.session_state[_SS_SNAP_X]
    for i in targets:
        o = dict(objs[i])
        name = o.get("name") or "Custom"
        w,h = _fix_size(name, int(o.get("width") or 0), int(o.get("height") or 0))
        if pos == "left":   y = 0
        elif pos == "right":y = TRAILER_W_CM - h
        else:               y = (TRAILER_W_CM - h)//2
        x = int(o.get("left") or 0)
        x,y = _snap_xy(name, x, y, w, h, step_x)
        o.update({"left": x, "top": y, "width": w, "height": h})
        objs[i] = o

def _set_locked(flag: bool):
    _ensure()
    st.session_state[_SS_LOCKED] = bool(flag)
    # Drag-Modus automatisch aus, wenn gesperrt
    if flag:
        st.session_state[_SS_EDIT] = False
    # selectable/evented nachziehen
    new = []
    for o in st.session_state[_SS_OBJS]:
        q = dict(o)
        q["selectable"] = bool(st.session_state[_SS_EDIT]) and (not flag)
        q["evented"]    = q["selectable"]
        new.append(q)
    st.session_state[_SS_OBJS] = new

def _set_edit(flag: bool):
    _ensure()
    st.session_state[_SS_EDIT] = bool(flag) and (not st.session_state[_SS_LOCKED])
    # Objekte togglen
    new = []
    for o in st.session_state[_SS_OBJS]:
        q = dict(o)
        q["selectable"] = st.session_state[_SS_EDIT]
        q["evented"]    = st.session_state[_SS_EDIT]
        new.append(q)
    st.session_state[_SS_OBJS] = new

# ---------- Public UI ----------
def render_manager(title: str = "Eigene Layouts (Presets-Editor)", show_expander: bool = True) -> List[Dict[str, Any]]:
    _ensure()
    items: List[Dict[str, Any]] = []

    ct = st.expander(title, expanded=show_expander) if show_expander else st.container()
    with ct:
        if not _HAS_CANVAS:
            st.info("Canvas nicht verfügbar.")
            return []

        # Kopf
        ctop = st.columns([1.1, 1, 1, 1.4])
        with ctop[0]:
            step_x = st.number_input("X-Raster (cm)", 1, 100, st.session_state[_SS_SNAP_X], step=1)
            st.session_state[_SS_SNAP_X] = int(step_x)
        with ctop[1]:
            locked_now = st.toggle("Fixiert", value=st.session_state[_SS_LOCKED], help="Wenn aktiv: kein Drag.")
            if locked_now != st.session_state[_SS_LOCKED]:
                _set_locked(locked_now)
        with ctop[2]:
            edit_now = st.toggle("Bearbeiten (Drag)", value=st.session_state[_SS_EDIT],
                                 help="Nur aktivieren, wenn du ziehen willst. Snap greift automatisch beim Commit.")
            if edit_now != st.session_state[_SS_EDIT]:
                _set_edit(edit_now)
        with ctop[3]:
            st.caption("Y rastet automatisch auf Links/Mitte/Rechts · 1 px = 1 cm")

        # Canvas zuerst rendern
        initial_json = {"version": "5.2.4", "objects": st.session_state[_SS_OBJS]}
        try:
            canvas_result = st_canvas(
                width=TRAILER_LEN_CM,
                height=TRAILER_W_CM,
                drawing_mode=("transform" if (st.session_state[_SS_EDIT] and not st.session_state[_SS_LOCKED]) else "none"),
                stroke_width=2,
                stroke_color="#222222",
                key="pf_canvas",
                update_streamlit=True,  # Drag-Stand kommt rein; wir committen stabil
                initial_drawing=initial_json,
            )
        except Exception as e:
            st.error(f"Canvas konnte nicht initialisiert werden: {e!s}")
            return []

        # WICHTIG: vor Buttons aktuellen Stand stabil übernehmen (match pfid + snap)
        if canvas_result and canvas_result.json_data:
            _commit_from_canvas(canvas_result.json_data)

        # Buttons – wirken jetzt auf stabilen, gesnappten Stand
        b1,b2,b3,b4,b5 = st.columns(5)
        with b1: st.button("➕ Euro längs 120×80", on_click=_add, args=("EURO_LONG",), disabled=st.session_state[_SS_LOCKED])
        with b2: st.button("➕ Euro quer 80×120",  on_click=_add, args=("EURO_TRANS",), disabled=st.session_state[_SS_LOCKED])
        with b3: st.button("➕ Industrie 120×100", on_click=_add, args=("IND",),      disabled=st.session_state[_SS_LOCKED])
        with b4: st.button("⟲ Letzte löschen",    on_click=_delete_last,              disabled=st.session_state[_SS_LOCKED])
        with b5: st.button("✖ Alles löschen",     on_click=_delete_all,               disabled=st.session_state[_SS_LOCKED])

        scope = st.radio("Ausrichten für …", ["zuletzt", "alle"], horizontal=True, index=0,
                         disabled=st.session_state[_SS_LOCKED])
        s1,s2,s3 = st.columns(3)
        with s1: st.button("⟸ Links",  on_click=_align, args=(scope=="zuletzt","left"),  disabled=st.session_state[_SS_LOCKED])
        with s2: st.button("◎ Mitte",  on_click=_align, args=(scope=="zuletzt","mid"),   disabled=st.session_state[_SS_LOCKED])
        with s3: st.button("⟹ Rechts", on_click=_align, args=(scope=="zuletzt","right"), disabled=st.session_state[_SS_LOCKED])

        # Rückgabe (Export)
        items = []
        for o in st.session_state[_SS_OBJS]:
            name = o.get("name") or "Custom"
            w,h = _fix_size(name, int(o.get("width") or 0), int(o.get("height") or 0))
            x   = int(o.get("left") or 0)
            y   = int(o.get("top")  or 0)
            items.append({"x_cm": x, "y_cm": y, "w_cm": w, "h_cm": h, "typ": name})

        # Meta
        total_pal = sum(1 for it in items if it["typ"] in ("Euro","Industrie"))
        st.session_state[_SS_META] = UserMeta(name="Canvas", total_pal=total_pal, heavy_count=0)

        # Presets speichern
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

        # Optional Diagnose
        if st.checkbox("Canvas-JSON anzeigen", value=False):
            st.json({"objects": st.session_state[_SS_OBJS]})

    return items
