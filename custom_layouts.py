# custom_layouts.py — Presets-Editor (Drag&Drop nur hier), Snap & echt fixierbar
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
_SS_PRESETS        = "pf_presets"
_SS_LAST_META      = "pf_last_meta"
_SS_OBJS           = "pf_canvas_objs"      # Quelle der Wahrheit (persistierte fabric-Objekte)
_SS_NEXT_IDX       = "pf_next_pos_idx"
_SS_LOCKED         = "pf_locked"           # True => wirklich gesperrt
_SS_SNAP_CM        = "pf_snap_cm"          # Raster fürs X/Y-Snap auf „Übernehmen“
_SS_SCOPE_LAST     = "pf_scope_last"       # "zuletzt" | "alle"

def _ensure():
    if _SS_PRESETS not in st.session_state:  st.session_state[_SS_PRESETS] = []
    if _SS_LAST_META not in st.session_state:st.session_state[_SS_LAST_META] = UserMeta()
    if _SS_OBJS not in st.session_state:     st.session_state[_SS_OBJS] = []
    if _SS_NEXT_IDX not in st.session_state: st.session_state[_SS_NEXT_IDX] = 0
    if _SS_LOCKED not in st.session_state:   st.session_state[_SS_LOCKED] = False
    if _SS_SNAP_CM not in st.session_state:  st.session_state[_SS_SNAP_CM] = 10
    if _SS_SCOPE_LAST not in st.session_state: st.session_state[_SS_SCOPE_LAST] = "zuletzt"

def get_active_meta() -> UserMeta:
    _ensure()
    return st.session_state[_SS_LAST_META]

def export_all_presets_json() -> bytes:
    import json
    _ensure()
    try:
        return json.dumps(st.session_state[_SS_PRESETS], ensure_ascii=False, indent=2).encode("utf-8")
    except Exception:
        return b"[]"

# ---------- Utilities ----------
def _snap(v: int, step: int) -> int:
    if step <= 1: return int(v)
    return int(round(v / step) * step)

def _clamp(val: int, low: int, high: int) -> int:
    return max(low, min(high, val))

def _apply_snap_xy(left: int, top: int, w: int, h: int, step: int) -> (int,int):
    x = _clamp(_snap(left, step), 0, max(0, TRAILER_LEN_CM - w))
    y = _clamp(_snap(top,  step), 0, max(0, TRAILER_W_CM  - h))
    return x, y

# ---------- Fabric Helpers ----------
def _fabric_rect(x: int, y: int, w: int, h: int, label: str, selectable: bool) -> Dict[str, Any]:
    """Fabric-Rect mit fixen Größen. Nur bewegen (wenn selectable=True)."""
    return {
        "type": "rect",
        "left": x, "top": y,
        "width": w, "height": h,
        "fill": "rgba(0,0,0,0)",    # Farbe macht deine Clean-Grafik separat
        "stroke": "#222222", "strokeWidth": 2,
        "angle": 0,
        "selectable": bool(selectable),
        "evented": bool(selectable),
        "hasControls": False,
        "lockScalingX": True, "lockScalingY": True, "lockUniScaling": True,
        "lockRotation": True,       # kein Rotieren
        "name": label,              # "Euro" | "Industrie"
        "scaleX": 1, "scaleY": 1,
    }

def _add(kind: str):
    _ensure()
    if st.session_state[_SS_LOCKED]: return

    if kind == "EURO_LONG":  w,h,typ = 120, 80,  "Euro"
    elif kind == "EURO_TRANS": w,h,typ= 80, 120, "Euro"
    elif kind == "IND":      w,h,typ = 120, 100, "Industrie"
    else: return

    idx = st.session_state[_SS_NEXT_IDX]
    gap = 8
    per_row = max(1, TRAILER_LEN_CM // (w + gap))
    row = idx // per_row
    col = idx % per_row
    x = min(TRAILER_LEN_CM - w, 10 + col * (w + gap))
    y = min(TRAILER_W_CM - h, 10 + row * (max(100, h) + gap))

    # X/Y vorab auf Raster snappen, damit niemand „springt“
    step = st.session_state[_SS_SNAP_CM]
    x, y = _apply_snap_xy(x, y, w, h, step)

    st.session_state[_SS_OBJS].append(_fabric_rect(x, y, w, h, typ, selectable=True))
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

def _normalize_rect(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """fabric.js -> cm + Fixgrößen + Snap + Bounds; 3 Y-Positionen per Buttons steuerbar."""
    if not isinstance(obj, dict) or obj.get("type") != "rect":
        return None
    left   = int(round((obj.get("left") or 0)))
    top    = int(round((obj.get("top")  or 0)))
    width  = int(round((obj.get("width")  or 0) * (obj.get("scaleX") or 1)))
    height = int(round((obj.get("height") or 0) * (obj.get("scaleY") or 1)))
    typ = obj.get("name") or "Custom"

    # Fixgrößen erzwingen
    if typ == "Euro":
        if width < height: width, height = 80, 120
        else:              width, height = 120, 80
    elif typ == "Industrie":
        width, height = 120, 100

    step = st.session_state[_SS_SNAP_CM]
    left, top = _apply_snap_xy(left, top, width, height, step)
    return {"x_cm": left, "y_cm": top, "w_cm": width, "h_cm": height, "typ": typ}

def _json_to_items(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not json_data: return []
    objs = json_data.get("objects") or []
    out: List[Dict[str, Any]] = []
    for o in objs:
        r = _normalize_rect(o)
        if r: out.append(r)
    return out

# ---------- Ausrichten (nur Y: links/mitte/rechts) ----------
def _align(scope_last: bool, pos: str):
    _ensure()
    if st.session_state[_SS_LOCKED]: return
    objs = st.session_state[_SS_OBJS]
    if not objs: return
    targets = [len(objs)-1] if scope_last else list(range(len(objs)))

    step = st.session_state[_SS_SNAP_CM]
    for i in targets:
        o = dict(objs[i])
        name = o.get("name")
        w = int(round((o.get("width") or 0)))
        h = int(round((o.get("height") or 0)))
        # Fixgrößen absichern
        if name == "Euro":
            if w < h: w,h = 80,120
            else:     w,h = 120,80
        elif name == "Industrie":
            w,h = 120,100

        if pos == "left":
            y = 0
        elif pos == "right":
            y = TRAILER_W_CM - h
        else:
            y = (TRAILER_W_CM - h) // 2

        # X nicht ändern, nur snappen/bounds prüfen
        x = int(o.get("left") or 0)
        x = _clamp(_snap(x, step), 0, max(0, TRAILER_LEN_CM - w))
        y = _clamp(_snap(y, step), 0, max(0, TRAILER_W_CM  - h))

        o["left"], o["top"] = x, y
        o["width"], o["height"] = w, h
        objs[i] = o

# ---------- Lock/Unlock ----------
def _set_locked(flag: bool):
    _ensure()
    st.session_state[_SS_LOCKED] = bool(flag)
    # alle Objekte entsprechend sperren/freigeben
    new_objs = []
    for o in st.session_state[_SS_OBJS]:
        q = dict(o)
        q["selectable"] = not flag
        q["evented"] = not flag
        new_objs.append(q)
    st.session_state[_SS_OBJS] = new_objs

# ---------- Public UI ----------
def render_manager(title: str = "Eigene Layouts (Presets-Editor)", show_expander: bool = True) -> List[Dict[str, Any]]:
    """Presets-Editor (Drag&Drop): Snap beim Übernehmen, echt fixierbar; beeinflusst NICHT die Clean-Grafik."""
    _ensure()
    items: List[Dict[str, Any]] = []

    ct = st.expander(title, expanded=show_expander) if show_expander else st.container()
    with ct:
        if not _HAS_CANVAS:
            st.info("Canvas nicht verfügbar.")
            return []

        # Kopf: Raster & Lock
        ctop = st.columns([1.1, 1, 1.2])
        with ctop[0]:
            snap_cm = st.number_input("Snap-Raster (cm)", 1, 100, st.session_state[_SS_SNAP_CM], step=1)
            st.session_state[_SS_SNAP_CM] = int(snap_cm)
        with ctop[1]:
            lock_now = st.toggle("Fixiert (gesperrt)", value=st.session_state[_SS_LOCKED])
            if lock_now != st.session_state[_SS_LOCKED]:
                _set_locked(lock_now)
        with ctop[2]:
            st.caption("1 px = 1 cm · Trailer 1360×240 cm")

        st.caption("Hinzufügen → ggf. Y ausrichten (Links/Mitte/Rechts) → „Übernehmen“. "
                   "„Übernehmen & fixieren“ sperrt die Paletten (nicht mehr verschiebbar). "
                   "Diese Presets beeinflussen NICHT die Clean-Grafik.")

        # Hinzufügen/Löschen
        b1, b2, b3, b4, b5 = st.columns(5)
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

        # Ausrichten (nur Y)
        scope = st.radio("Ausrichten für …", ["zuletzt", "alle"], horizontal=True, index=(0 if st.session_state[_SS_SCOPE_LAST]=="zuletzt" else 1),
                         disabled=st.session_state[_SS_LOCKED])
        st.session_state[_SS_SCOPE_LAST] = scope
        s1, s2, s3 = st.columns(3)
        with s1:
            st.button("⟸ Links", on_click=_align, args=(scope=="zuletzt", "left"), disabled=st.session_state[_SS_LOCKED])
        with s2:
            st.button("◎ Mitte", on_click=_align, args=(scope=="zuletzt", "mid"), disabled=st.session_state[_SS_LOCKED])
        with s3:
            st.button("⟹ Rechts", on_click=_align, args=(scope=="zuletzt", "right"), disabled=st.session_state[_SS_LOCKED])

        # Canvas
        initial_json = {"version": "5.2.4", "objects": st.session_state[_SS_OBJS]}
        try:
            canvas_result = st_canvas(
                width=TRAILER_LEN_CM,
                height=TRAILER_W_CM,
                drawing_mode=("transform" if not st.session_state[_SS_LOCKED] else "none"),
                stroke_width=2,
                stroke_color="#222222",
                key="pf_canvas",
                update_streamlit=False,    # kein Blinken
                initial_drawing=initial_json,
            )
        except Exception as e:
            st.error(f"Canvas konnte nicht initialisiert werden: {e!s}")
            return []

        # Speichern
        cs = st.columns([1.4, 1.4, 1])
        with cs[0]:
            if st.button("⏎ Übernehmen (Snap anwenden)", disabled=st.session_state[_SS_LOCKED]):
                if canvas_result and canvas_result.json_data:
                    new = []
                    for o in canvas_result.json_data.get("objects") or []:
                        r = _normalize_rect(o)
                        if r:
                            new.append(_fabric_rect(r["x_cm"], r["y_cm"], r["w_cm"], r["h_cm"], r["typ"], selectable=True))
                    # Wichtig: bestehende bleiben unangetastet, nur ersetzt durch gesnappten Stand
                    st.session_state[_SS_OBJS] = new
                st.success("Übernommen (gesnappt).")
        with cs[1]:
            if st.button("🔒 Übernehmen & fixieren"):
                # immer vom aktuellen Canvas lesen, dann sperren
                if canvas_result and canvas_result.json_data:
                    new = []
                    for o in canvas_result.json_data.get("objects") or []:
                        r = _normalize_rect(o)
                        if r:
                            new.append(_fabric_rect(r["x_cm"], r["y_cm"], r["w_cm"], r["h_cm"], r["typ"], selectable=False))
                    st.session_state[_SS_OBJS] = new
                _set_locked(True)
                st.success("Übernommen & fixiert.")
        with cs[2]:
            if st.button("🔓 Bearbeiten", disabled=not st.session_state[_SS_LOCKED]):
                _set_locked(False)
                st.info("Bearbeitung wieder aktiviert.")

        # Rückgabe als Items (für evtl. Vorschau/Export)
        items = _json_to_items({"objects": st.session_state[_SS_OBJS]})

        # Meta aktualisieren
        total_pal = sum(1 for it in items if it["typ"] in ("Euro", "Industrie"))
        st.session_state[_SS_LAST_META] = UserMeta(name="Canvas", total_pal=total_pal, heavy_count=0)

        # Presets speichern/exportieren
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
