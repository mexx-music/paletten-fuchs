# app.py — Paletten Fuchs 9.5 (bereinigt)
# - Clean-Ansicht (Euro/Industrie + "Exakt bis hinten")
# - Varianten (2×2) IMMER sichtbar, gekoppelt an die Eingaben oben
# - JSON-Konfig: variants.json upload (beliebig viele Muster), Default-Konfig als Fallback
# - Neue Variantentypen: recipe, heavy_auto_rear, light_auto_mix
# - JSON-Filter: n_exact, n_min, n_max, weight_required, weight_forbidden (+ euro_min/max, ind_min/max)
# - Gewicht: Block vorne/hinten, Verteilen (Hecklast), All-Heavy
# - BONUS: Bei aktivem Gewicht zusätzliches 2×2 mit Gewichts-Logik
# - Achslast-Schätzung (grob): Front/Rear basierend auf Hebelmodell (Stützen an den Enden des 1360-cm-Rahmens)

from custom_layouts import render_manager, get_active_meta, export_all_presets_json
from typing import List, Dict, Optional, Tuple, Set
import streamlit as st
import json
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import re
# (oben / im Canvas-Block)
st.download_button(
    "Presets (Canvas) exportieren",
    data=export_all_presets_json(),
    file_name="palettenfuchs_presets.json",
    mime="application/json",
    key="presets_export_btn_top",   # << NEU, eindeutig
)


# ===================== 3) Canvas-Manager (nur Presets) =====================
use_canvas_for_presets = st.toggle("Canvas für Presets nutzen (Drag&Drop – nur zum Speichern/Laden)", value=False)

user_layout_cm = []
user_meta = None
if use_canvas_for_presets:
    from custom_layouts import render_manager, get_active_meta, export_all_presets_json
    user_layout_cm = render_manager(title="Eigene Layouts (Presets-Editor)", show_expander=True)
    user_meta = get_active_meta()
    st.download_button(
        "Presets (Canvas) exportieren",
        data=export_all_presets_json(),
        file_name="palettenfuchs_presets.json",
        mime="application/json"
    )

# GANZ WICHTIG:
# Canvas beeinflusst NICHT die Clean-Grafik unten.
# Die Hauptdarstellung rechnet IMMER aus Euro/Industrie + Optionen!
use_user_layout = False


# ===================== 4) Helper: Canvas-Layout zeichnen =================
TRAILER_LEN_CM = 1360
TRAILER_W_CM   = 240

def _draw_trailer_frame(ax):
    ax.add_patch(Rectangle((0, 0), TRAILER_LEN_CM, TRAILER_W_CM,
                           fill=False, linewidth=2, edgecolor="#333"))
    ax.set_xlim(0, TRAILER_LEN_CM)
    ax.set_ylim(0, TRAILER_W_CM)
    ax.set_aspect('equal')
    ax.axis('off')

def draw_canvas_layout(title: str, items: List[Dict], figsize: Tuple[float,float]=(8,1.7)):
    """Zeichnet frei platzierte Paletten (cm-Koordinaten) aus dem Canvas."""
    fig, ax = plt.subplots(figsize=figsize)
    _draw_trailer_frame(ax)
    for it in items:
        x, y = float(it["x_cm"]), float(it["y_cm"])
        w, h = float(it["w_cm"]), float(it["h_cm"])
        typ = it.get("typ", "")
        # Farben analog Clean-Grafik:
        if typ == "Euro" and {w,h} == {80.0,120.0}:
            face = "#cfe8ff" if w < h else "#d9f2d9"
        elif typ == "Industrie" and {w,h} == {100.0,120.0}:
            face = "#ffe2b3"
        else:
            face = "#bbbbbb"
        ax.add_patch(Rectangle((x, y), w, h, facecolor=face, edgecolor="#4a4a4a", linewidth=0.9))
    ax.set_title(title, fontsize=12, pad=6)
    st.pyplot(fig)
    plt.close(fig)

# ------------------ Geometrie / Konstanten ------------------
EURO_L_CM, EURO_W_CM = 120, 80
IND_L_CM,  IND_W_CM  = 120, 100

# ------------------ Basis-Layoutfunktionen (Euro/Industrie) ------------------
def euro_row_long() -> Dict:   return {"type": "EURO_3_LONG", "len_cm": EURO_L_CM, "pallets": 3}
def euro_row_trans2() -> Dict: return {"type": "EURO_2_TRANS", "len_cm": EURO_W_CM, "pallets": 2}
def euro_row_trans1() -> Dict: return {"type": "EURO_1_TRANS", "len_cm": EURO_W_CM, "pallets": 1}
def ind_row2_long() -> Dict:   return {"type": "IND_ROW_2_LONG", "len_cm": IND_L_CM, "pallets": 2}
def ind_single() -> Dict:      return {"type": "IND_SINGLE", "len_cm": IND_L_CM, "pallets": 1}

def cap_to_trailer(rows: List[Dict]) -> List[Dict]:
    out, s = [], 0
    for r in rows:
        L = r.get("len_cm", EURO_L_CM)
        if s + L > TRAILER_LEN_CM: break
        out.append(r); s += L
    return out

def rows_length_cm(rows: List[Dict]) -> int: return sum(r.get("len_cm", EURO_L_CM) for r in rows)
def rows_pallets(rows: List[Dict]) -> int:   return sum(r.get("pallets", 0) for r in rows)

# ------------------ Tail-Guard: keine Singles in letzten 4 Reihen ------------------
def enforce_tail_no_single(rows: List[Dict], target_pal: int) -> List[Dict]:
    rows = cap_to_trailer(list(rows))
    n = len(rows)
    if n > 0:
        tail_start = max(0, n - 4)
        cleaned = []
        for i, r in enumerate(rows):
            if i >= tail_start and r["type"] == "EURO_1_TRANS":
                continue
            cleaned.append(r)
        rows = cleaned
    if rows and rows[-1]["type"] == "EURO_1_TRANS":
        rows.pop()

    deficit = target_pal - rows_pallets(rows)
    if deficit <= 0:
        if deficit < 0:
            base = layout_for_preset_euro_stable(target_pal, singles_front=0)
            return cap_to_trailer(base)
        return rows

    insert_limit = max(0, len(rows) - 4)

    def try_insert(row_factory, at_idx: int) -> bool:
        new_rows = rows[:at_idx] + [row_factory()] + rows[at_idx:]
        if rows_length_cm(new_rows) <= TRAILER_LEN_CM:
            rows[:] = new_rows
            return True
        return False

    if deficit % 3 == 2:
        placed = False
        for ins in range(0, insert_limit + 1):
            if try_insert(euro_row_trans2, ins):
                deficit -= 2; placed = True; break
        if not placed and rows_length_cm(rows) + EURO_W_CM <= TRAILER_LEN_CM:
            rows.append(euro_row_trans2()); deficit -= 2

    while deficit >= 3 and rows_length_cm(rows) + EURO_L_CM <= TRAILER_LEN_CM:
        rows = rows[:insert_limit] + [euro_row_long()] + rows[insert_limit:]
        deficit -= 3

    if deficit == 2 and rows_length_cm(rows) + EURO_W_CM <= TRAILER_LEN_CM:
        rows = [euro_row_trans2()] + rows; deficit -= 2

    if deficit != 0:
        rows = cap_to_trailer(layout_for_preset_euro_stable(target_pal, singles_front=0))

    n = len(rows); tail_start = max(0, n - 4)
    if any(r["type"] == "EURO_1_TRANS" for r in rows[tail_start:]):
        rows = cap_to_trailer(layout_for_preset_euro_stable(target_pal, singles_front=0))
    return rows

# ------------------ Euro-Layouts (stabil & exakt) ------------------
def layout_for_preset_euro_stable(n: int, singles_front: int = 0) -> List[Dict]:
    rows: List[Dict] = []; remaining = n
    take = min(max(0, singles_front), 2, remaining)
    for _ in range(take): rows.append(euro_row_trans1()); remaining -= 1

    if remaining >= 2 and (remaining - 2) % 3 == 0:
        rows.append(euro_row_trans2()); remaining -= 2

    while remaining % 3 != 0 and any(r["type"] == "EURO_1_TRANS" for r in rows):
        for i, r in enumerate(rows):
            if r["type"] == "EURO_1_TRANS":
                rows.pop(i); remaining += 1; break

    if remaining > 0:
        rows += [euro_row_long() for _ in range(remaining // 3)]

    if rows_pallets(rows) != n:
        if n >= 2 and (n - 2) % 3 == 0:
            rows = [euro_row_trans2()] + [euro_row_long() for _ in range((n - 2) // 3)]
        else:
            rows = [euro_row_long() for _ in range(n // 3)]
            rest = n % 3
            if rest == 2: rows.insert(0, euro_row_trans2())
            elif rest == 1: rows.insert(0, euro_row_trans1())
    return enforce_tail_no_single(rows, n)

def build_euro_exact_tail(n: int) -> List[Dict]:
    if n <= 0: return []
    s = max(0, 34 - n)   # minimale 1-quer
    rem = n - s          # 3a + 2k = rem
    a_max = rem // 3
    if a_max % 2 == 1: a_max -= 1

    a = -1
    for cand in range(a_max, -1, -2):      # nur gerade a
        if (rem - 3*cand) % 2 == 0:
            a = cand; break
    if a < 0:
        return layout_for_preset_euro_stable(n, singles_front=0)

    k = (rem - 3*a) // 2
    rows: List[Dict] = []
    s_front = s // 2; s_tailguard = s - s_front
    for _ in range(s_front): rows.append(euro_row_trans1())
    rows += [euro_row_long() for _ in range(a)]
    rows += [euro_row_trans2() for _ in range(k)]
    if s_tailguard > 0:
        insert_at = max(0, len(rows) - 4)
        rows = rows[:insert_at] + [euro_row_trans1() for _ in range(s_tailguard)] + rows[insert_at:]
    return enforce_tail_no_single(rows, n)

# ------------------ Industrie-Layout ------------------
def layout_for_preset_industry(n: int) -> List[Dict]:
    if n <= 0: return []
    rows: List[Dict] = []
    single = n % 2; full = n // 2
    if single: rows.append(ind_single())
    rows += [ind_row2_long() for _ in range(full)]
    return rows

# ------------------ Gewicht: Block/Verteilen ------------------
def _cat_of_row(r: Dict) -> str:
    t = r.get("type","")
    return "EURO" if t.startswith("EURO_") else ("IND" if t.startswith("IND") else "OTHER")

def reorder_rows_heavy(rows: List[Dict],
                       heavy_euro_count: int,
                       heavy_ind_count: int,
                       side: str = "front",
                       group_by_type: bool = True,
                       type_order: Tuple[str,str] = ("EURO","IND")) -> List[Dict]:
    if heavy_euro_count <= 0 and heavy_ind_count <= 0:
        return rows

    idx_iter = range(len(rows)) if side == "front" else reversed(range(len(rows)))
    taken_idx_e, taken_idx_i = [], []
    need_e, need_i = heavy_euro_count, heavy_ind_count

    for i in idx_iter:
        r = rows[i]; cat = _cat_of_row(r)
        if cat == "EURO" and need_e > 0:
            taken_idx_e.append(i); need_e -= r.get("pallets", 0)
        elif cat == "IND" and need_i > 0:
            taken_idx_i.append(i); need_i -= r.get("pallets", 0)
        if need_e <= 0 and need_i <= 0: break

    taken = set(taken_idx_e + taken_idx_i)
    remaining = [r for j, r in enumerate(rows) if j not in taken]
    block_e = [rows[j] for j in sorted(taken_idx_e)]
    block_i = [rows[j] for j in sorted(taken_idx_i)]

    if group_by_type:
        block = []
        for cat in type_order:
            if cat == "EURO": block += block_e
            elif cat == "IND": block += block_i
    else:
        block = [rows[j] for j in sorted(taken)]

    return (block + remaining) if side == "front" else (remaining + block)

def pick_heavy_rows_rear_biased(rows: List[Dict], heavy_total: int) -> Set[int]:
    if heavy_total <= 0 or not rows: return set()
    N = len(rows); scored = []
    for i, r in enumerate(rows):
        pos = (i + 1) / N
        bias = 0.6*pos + 0.4*(pos**2)
        typ = r.get("type","")
        bonus = 0.08 if ("_1_" in typ or "_2_" in typ or "IND_SINGLE" in typ) else 0.0
        scored.append((i, bias + bonus, r.get("pallets", 0)))
    scored.sort(key=lambda t: t[1], reverse=True)
    picked: Set[int] = set(); total = 0

    def neighbors(k: int) -> bool: return (k-1 in picked) or (k+1 in picked)

    for idx, _, pal in scored:
        if total >= heavy_total: break
        if neighbors(idx): continue
        picked.add(idx); total += pal

    if total < heavy_total:
        for idx, _, pal in scored:
            if total >= heavy_total: break
            if idx in picked: continue
            if ((idx-1 in picked) and (idx-2 in picked)) or ((idx+1 in picked) and (idx+2 in picked)):
                continue
            picked.add(idx); total += pal
    return picked

# ------------------ Grafik ------------------
COLOR_EURO_LONG = "#d9f2d9"
COLOR_EURO_QUER = "#cfe8ff"
COLOR_IND      = "#ffe2b3"
EDGE           = "#4a4a4a"

def rows_to_rects(rows: List[Dict]) -> List[Tuple[float,float,float,float,str,str,bool]]:
    rects = []; x = 0
    for r in rows:
        t = r["type"]; L = r["len_cm"]
        if t == "EURO_3_LONG":
            for lane in range(3): rects.append((x, lane*80, 120, 80, COLOR_EURO_LONG, "EURO", False))
            x += L
        elif t == "EURO_2_TRANS":
            for lane in range(2): rects.append((x, lane*120, 80, 120, COLOR_EURO_QUER, "EURO", False))
            x += L
        elif t == "EURO_1_TRANS":
            rects.append((x, 60, 80, 120, COLOR_EURO_QUER, "EURO", False)); x += L
        elif t == "IND_ROW_2_LONG":
            rects.append((x, 20, 120, 100, COLOR_IND, "IND", False))
            rects.append((x,120, 120, 100, COLOR_IND, "IND", False)); x += L
        elif t == "IND_SINGLE":
            rects.append((x, 70, 120, 100, COLOR_IND, "IND", False)); x += L
    return rects

def rows_to_rects_with_row_index(rows: List[Dict]):
    rects = []; meta  = []; x = 0
    for i, r in enumerate(rows):
        t = r["type"]; L = r["len_cm"]
        if t == "EURO_3_LONG":
            for lane in range(3):
                rects.append((x, lane*80, 120, 80, COLOR_EURO_LONG, "EURO"))
                meta.append({"row_idx": i, "cat": "EURO"})
            x += L
        elif t == "EURO_2_TRANS":
            for lane in range(2):
                rects.append((x, lane*120, 80, 120, COLOR_EURO_QUER, "EURO"))
                meta.append({"row_idx": i, "cat": "EURO"})
            x += L
        elif t == "EURO_1_TRANS":
            rects.append((x, 60, 80, 120, COLOR_EURO_QUER, "EURO"))
            meta.append({"row_idx": i, "cat": "EURO"})
            x += L
        elif t == "IND_ROW_2_LONG":
            for y0 in (20, 120):
                rects.append((x, y0, 120, 100, COLOR_IND, "IND"))
                meta.append({"row_idx": i, "cat": "IND"})
            x += L
        elif t == "IND_SINGLE":
            rects.append((x, 70, 120, 100, COLOR_IND, "IND"))
            meta.append({"row_idx": i, "cat": "IND"})
            x += L
    return rects, meta

def rows_to_rects_with_weights(rows: List[Dict],
                               heavy_euro_count: int = 0, heavy_euro_side: str = "front",
                               heavy_ind_count: int = 0,  heavy_ind_side: str  = "front"):
    rects = []; x = 0; euro_rects = []; ind_rects  = []
    for r in cap_to_trailer(rows):
        t = r["type"]; L = r["len_cm"]
        if t == "EURO_3_LONG":
            for lane in range(3):
                rects.append((x, lane*80, 120, 80, COLOR_EURO_LONG, "EURO", False))
                euro_rects.append(len(rects)-1)
            x += L
        elif t == "EURO_2_TRANS":
            for lane in range(2):
                rects.append((x, lane*120, 80, 120, COLOR_EURO_QUER, "EURO", False))
                euro_rects.append(len(rects)-1)
            x += L
        elif t == "EURO_1_TRANS":
            rects.append((x, 60, 80, 120, COLOR_EURO_QUER, "EURO", False))
            euro_rects.append(len(rects)-1)
            x += L
        elif t == "IND_ROW_2_LONG":
            for y0 in (20, 120):
                rects.append((x, y0, 120, 100, COLOR_IND, "IND", False))
                ind_rects.append(len(rects)-1)
            x += L
        elif t == "IND_SINGLE":
            rects.append((x, 70, 120, 100, COLOR_IND, "IND", False))
            ind_rects.append(len(rects)-1)
            x += L

    euro_cnt = len(euro_rects)
    if heavy_euro_count > 0 and euro_cnt > 0:
        indices = (list(reversed(euro_rects)) if heavy_euro_side == "rear" else euro_rects)[:heavy_euro_count]
        for idx in indices:
            x0,y0,w0,h0,c0,cat0,_ = rects[idx]
            rects[idx] = (x0,y0,w0,h0,c0,cat0,True)
    euro_hvy = sum(1 for i in euro_rects if rects[i][6] is True)

    ind_cnt = len(ind_rects)
    if heavy_ind_count > 0 and ind_cnt > 0:
        indices = (list(reversed(ind_rects)) if heavy_ind_side == "rear" else ind_rects)[:heavy_ind_count]
        for idx in indices:
            x0,y0,w0,h0,c0,cat0,_ = rects[idx]
            rects[idx] = (x0,y0,w0,h0,c0,cat0,True)
    ind_hvy = sum(1 for i in ind_rects if rects[i][6] is True)

    return rects, euro_cnt, ind_cnt, euro_hvy, ind_hvy

def estimate_axle_loads(rows: List[Dict], kg_euro: int, kg_ind: int) -> Tuple[float, float, float]:
    if kg_euro <= 0 and kg_ind <= 0: return (0.0, 0.0, 0.0)
    rects = rows_to_rects(cap_to_trailer(rows))
    L = float(TRAILER_LEN_CM)
    W = 0.0; M_about_front = 0.0
    for (x, y, w, h, color, cat, hv) in rects:
        wkg = kg_euro if cat == "EURO" else kg_ind
        if wkg <= 0: continue
        xc = x + w / 2.0
        W += wkg; M_about_front += wkg * xc
    if W <= 0: return (0.0, 0.0, 0.0)
    R_rear = M_about_front / L
    R_front = W - R_rear
    return (max(0.0, R_front), max(0.0, R_rear), W)

def caption_axle(front: float, rear: float, total: float) -> str:
    if total <= 0: return ""
    pf = 100.0 * front / total
    pr = 100.0 * rear  / total
    return f"Achslast (grob): Front ≈ **{front:.0f} kg** ({pf:.1f}%), Rear ≈ **{rear:.0f} kg** ({pr:.1f}%)."

def draw_graph(title: str,
               rows: List[Dict],
               figsize: Tuple[float,float] = (8, 1.7),
               weight_mode: bool = False,
               kg_euro: int = 0,
               kg_ind: int = 0,
               heavy_euro_count: int = 0, heavy_ind_count: int = 0, heavy_side: str = "front",
               heavy_rows: Optional[Set[int]] = None,
               show_axle_note: bool = False):
    if not weight_mode:
        rects = rows_to_rects(cap_to_trailer(rows))
        euro_cnt = sum(1 for *_,cat,_ in rects if cat=="EURO")
        ind_cnt  = sum(1 for *_,cat,_ in rects if cat=="IND")
        euro_hvy = ind_hvy = 0
    elif heavy_rows is not None:
        base, meta = rows_to_rects_with_row_index(cap_to_trailer(rows))
        rects = []
        euro_cnt = sum(1 for m in meta if m["cat"]=="EURO")
        ind_cnt  = sum(1 for m in meta if m["cat"]=="IND")
        euro_hvy = ind_hvy = 0
        for (x,y,w,h,c,cat), m in zip(base, meta):
            hv = (m["row_idx"] in heavy_rows)
            if hv and cat=="EURO": euro_hvy += 1
            if hv and cat=="IND":  ind_hvy  += 1
            rects.append((x,y,w,h,c,cat,hv))
    else:
        rects, euro_cnt, ind_cnt, euro_hvy, ind_hvy = rows_to_rects_with_weights(
            rows, heavy_euro_count=heavy_euro_count, heavy_euro_side=heavy_side,
            heavy_ind_count=heavy_ind_count, heavy_ind_side=heavy_side
        )

    fig, ax = plt.subplots(figsize=figsize)
    ax.add_patch(Rectangle((0, 0), TRAILER_LEN_CM, TRAILER_W_CM,
                           fill=False, linewidth=2, edgecolor="#333"))

    for (x, y, w, h, c, cat, hvy) in rects:
        face = c; edge = "#4a4a4a"; lw = 0.8
        if weight_mode and hvy:
            edge = "#222222"; lw = 1.6
            face = {"#d9f2d9":"#bfe6bf", "#cfe8ff":"#a8d7ff", "#ffe2b3":"#ffd089"}.get(c, c)
        ax.add_patch(Rectangle((x, y), w, h, facecolor=face, edgecolor=edge, linewidth=lw))

    ax.set_xlim(0, TRAILER_LEN_CM); ax.set_ylim(0, TRAILER_W_CM)
    ax.set_aspect('equal'); ax.axis('off'); ax.set_title(title, fontsize=12, pad=6)
    st.pyplot(fig); plt.close(fig)

    if (weight_mode or show_axle_note) and (kg_euro or kg_ind):
        front, rear, total = estimate_axle_loads(rows, kg_euro, kg_ind)
        axl = caption_axle(front, rear, total)
        if weight_mode:
            total_e = euro_cnt * kg_euro
            total_i = ind_cnt  * kg_ind
            st.caption(
                f"Gewicht: gesamt ≈ **{total_e + total_i:.0f} kg** "
                f"(Euro: {euro_cnt}×{kg_euro}, Ind.: {ind_cnt}×{kg_ind}). {axl}"
            )
        else:
            st.caption(axl)

# ---------- GROG: Auto-Scorer & Auswahl ----------
def _has_tail_single(rows: List[Dict]) -> bool:
    rows = cap_to_trailer(rows)
    n = len(rows); tail_start = max(0, n - 4)
    return any(r["type"] == "EURO_1_TRANS" for r in rows[tail_start:])

def _last_row_full(rows: List[Dict]) -> bool:
    rows = cap_to_trailer(rows)
    if not rows: return True
    t = rows[-1]["type"]
    return t not in ("EURO_1_TRANS", "IND_SINGLE")

def _weight_split_grog(rows: List[Dict], kg_euro: int, kg_ind: int) -> float:
    rects = rows_to_rects(cap_to_trailer(rows))
    if not rects: return 0.5
    L = float(TRAILER_LEN_CM)
    W = 0.0; M_front = 0.0
    for (x, y, w, h, color, cat, hv) in rects:
        wkg = (kg_euro if cat == "EURO" else kg_ind) or 1.0
        xc = x + w/2.0
        W += wkg; M_front += wkg * xc
    if W <= 0: return 0.5
    rear = M_front / L
    rear_share = max(0.0, min(1.0, rear / W))
    return rear_share

def score_layout_grog(rows: List[Dict],
                      kg_euro: int = 0,
                      kg_ind: int = 0,
                      target_rear_share: float = 0.52,
                      w_tail_single: float = 1000.0,
                      w_last_not_full: float = 80.0,
                      w_unused_cm: float = 0.6,
                      w_rear_dev: float = 220.0,
                      w_switch: float = 3.5) -> float:
    rows = cap_to_trailer(rows)
    s = 0.0
    if _has_tail_single(rows): s += w_tail_single
    if not _last_row_full(rows): s += w_last_not_full
    unused = max(0, TRAILER_LEN_CM - rows_length_cm(rows))
    s += w_unused_cm * unused
    rear_share = _weight_split_grog(rows, kg_euro, kg_ind)
    dev = rear_share - target_rear_share
    s += w_rear_dev * (dev * dev)
    def is_qu(tp):  return tp in ("EURO_2_TRANS", "EURO_1_TRANS")
    switches = sum(1 for a, b in zip(rows, rows[1:])
                   if ("Q" if is_qu(a["type"]) else "L") != ("Q" if is_qu(b["type"]) else "L"))
    s += w_switch * switches
    return s

def grog_pick_best(variants: List[Tuple[str, List[Dict]]],
                   kg_euro: int,
                   kg_ind: int,
                   target_rear_share: float,
                   topk: int = 4) -> List[Tuple[str, List[Dict], float, float]]:
    scored = []
    for title, rows in variants:
        sc = score_layout_grog(rows, kg_euro=kg_euro, kg_ind=kg_ind,
                               target_rear_share=target_rear_share)
        rear = _weight_split_grog(rows, kg_euro, kg_ind)
        scored.append((title, rows, sc, rear))
    scored.sort(key=lambda t: t[2])
    return scored[:topk]

# ------------------ Vordefinierte Euro-Typen ------------------
def _choose_k_for_no_single(n: int, k_max: int) -> int:
    k_cap = min(k_max, n // 2)
    want = (3 - (n % 3)) % 3  # k ≡ -n (mod 3)
    for k in range(k_cap, -1, -1):
        if k % 3 == want:
            return k
    return 0

def build_euro_all_long(n: int, exact_tail: bool) -> List[Dict]:
    return build_euro_exact_tail(n) if exact_tail else layout_for_preset_euro_stable(n, singles_front=0)

def build_euro_rear_2trans_block(n: int, approx_block: int, exact_tail: bool) -> List[Dict]:
    if n <= 0: return []
    if exact_tail: return build_euro_exact_tail(n)
    k = _choose_k_for_no_single(n, k_max=max(0, approx_block))
    if k == 0: return build_euro_all_long(n, exact_tail=False)
    long_cnt = (n - 2*k) // 3
    rows = [euro_row_long() for _ in range(long_cnt)] + [euro_row_trans2() for _ in range(k)]
    return enforce_tail_no_single(rows, n)

def build_euro_mixed_periodic(n: int, period: int, exact_tail: bool) -> List[Dict]:
    if n <= 0: return []
    if exact_tail: return build_euro_exact_tail(n)
    approx_k = max(1, n // period)
    k = _choose_k_for_no_single(n, k_max=approx_k)
    if k == 0: return build_euro_all_long(n, exact_tail=False)
    long_cnt = (n - 2*k) // 3
    out: List[Dict] = []
    quota = max(1e-9, long_cnt / (k + 1))
    used_long = 0; used_k = 0
    while used_long + used_k < long_cnt + k:
        if used_k < k and (used_long + used_k) >= (used_k + 1) * quota:
            out.append(euro_row_trans2()); used_k += 1
        else:
            out.append(euro_row_long()); used_long += 1
    return enforce_tail_no_single(out, n)

def build_euro_alt_pattern(n: int, exact_tail: bool) -> List[Dict]:
    if n <= 0: return []
    if exact_tail: return build_euro_exact_tail(n)
    approx_block = max(1, n // 6)
    return build_euro_rear_2trans_block(n, approx_block=approx_block, exact_tail=False)

def build_euro_recipe(rowspec: list) -> List[Dict]:
    rows: List[Dict] = []
    for r in rowspec:
        if r == 3: rows.append(euro_row_long())
        elif r == 2: rows.append(euro_row_trans2())
        elif r == 1: rows.append(euro_row_trans1())
    return enforce_tail_no_single(rows, sum(rowspec))

def build_euro_heavy_auto_rear(n: int, exact_tail: bool, params: dict) -> List[Dict]:
    if n <= 0: return []
    if exact_tail: return build_euro_exact_tail(n)
    target_share = float(params.get("target_rear_share", 0.42))
    min_k = int(params.get("min_k", 3))
    max_k = n // 2
    k_guess = max(min_k, min(max_k, int(round(target_share * n / 2.0))))
    k = _choose_k_for_no_single(n, k_max=k_guess)
    if k == 0: return build_euro_all_long(n, exact_tail=False)
    long_cnt = (n - 2*k) // 3
    rows = [euro_row_long() for _ in range(long_cnt)] + [euro_row_trans2() for _ in range(k)]
    return enforce_tail_no_single(rows, n)

def build_euro_light_auto_mix(n: int, exact_tail: bool, params: dict) -> List[Dict]:
    if n <= 0: return []
    period = int(params.get("period", 4))
    return build_euro_mixed_periodic(n, period=period, exact_tail=exact_tail)

def combine_with_industry_pos(euro_rows: List[Dict], ind_n: int, pos: str) -> List[Dict]:
    if ind_n <= 0:
        return euro_rows
    ind_rows = layout_for_preset_industry(ind_n)
    return cap_to_trailer(ind_rows + euro_rows) if pos == "front" else cap_to_trailer(euro_rows + ind_rows)

def build_euro_by_type(t: str, n: int, exact_tail: bool, params: dict) -> List[Dict]:
    if t == "recipe":          return build_euro_recipe(params.get("rows", []))
    if t == "heavy_auto_rear": return build_euro_heavy_auto_rear(n, exact_tail, params)
    if t == "light_auto_mix":  return build_euro_light_auto_mix(n, exact_tail, params)
    if t == "all_long":        return build_euro_all_long(n, exact_tail=exact_tail)
    if t == "rear_block":      return build_euro_rear_2trans_block(n, approx_block=int(params.get("approx_block", 15)), exact_tail=exact_tail)
    if t == "mixed_periodic":  return build_euro_mixed_periodic(n, period=int(params.get("period", 4)), exact_tail=exact_tail)
    if t == "alt_block":       return build_euro_alt_pattern(n, exact_tail=exact_tail)
    return build_euro_all_long(n, exact_tail=exact_tail)

# ===================== Varianten-Generator aus JSON =====================
def _variant_letter(title: str, fallback_letter: str) -> str:
    m = re.search(r"\bVar\s+([A-Z])\b", title, re.IGNORECASE)
    if m: 
        return m.group(1).upper()
    m = re.search(r"\b([A-Z])\b", title)
    if m:
        return m.group(1).upper()
    return fallback_letter  # z. B. A, B, C, D nach Reihenfolge

def _passes_filters(v: dict, euro_n: int, ind_n: int, weight_mode: bool) -> (bool, str):
    total = euro_n + ind_n
    if v.get("weight_required") and not weight_mode:
        return False, "weight_required"
    if v.get("weight_forbidden") and weight_mode:
        return False, "weight_forbidden"

    n_exact = v.get("n_exact")
    if n_exact is not None and total != int(n_exact):
        return False, f"n_exact={n_exact}"
    n_min = v.get("n_min")
    if n_min is not None and total < int(n_min):
        return False, f"n_min={n_min}"
    n_max = v.get("n_max")
    if n_max is not None and total > int(n_max):
        return False, f"n_max={n_max}"

    e_min = v.get("euro_min"); e_max = v.get("euro_max")
    i_min = v.get("ind_min");  i_max = v.get("ind_max")
    if e_min is not None and euro_n < int(e_min): return False, f"euro_min={e_min}"
    if e_max is not None and euro_n > int(e_max): return False, f"euro_max={e_max}"
    if i_min is not None and ind_n  < int(i_min): return False, f"ind_min={i_min}"
    if i_max is not None and ind_n  > int(i_max): return False, f"ind_max={i_max}"

    return True, ""

def _variant_params(v: dict) -> dict:
    return {k: v[k] for k in v.keys() if k not in ("title", "type")}

def generate_variants_from_config(cfg: dict,
                                  euro_n: int,
                                  ind_n: int,
                                  exact_tail: bool = False,
                                  weight_mode: bool = False):
    variants_cfg = cfg.get("variants", [])
    ind_pos_map  = cfg.get("industry_position", {})

    results = []
    skipped = []
    total_cfg = len(variants_cfg)
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for idx, v in enumerate(variants_cfg):
        title = str(v.get("title", f"Var {letters[idx%26]}"))
        vtype = str(v.get("type", "all_long")).strip()

        ok, reason = _passes_filters(v, euro_n, ind_n, weight_mode)
        if not ok:
            skipped.append((title, reason))
            continue

        params = _variant_params(v)
        euro_rows = build_euro_by_type(vtype, euro_n, exact_tail, params)

        var_letter = _variant_letter(title, letters[idx % 26])
        ind_pos = v.get("industry_position", ind_pos_map.get(var_letter, "front"))
        ind_pos = "rear" if str(ind_pos).lower().startswith("r") else "front"

        rows_v = combine_with_industry_pos(euro_rows, ind_n, pos=ind_pos)
        results.append((title, rows_v))

    return results, skipped, total_cfg

# ------------------ UI ------------------
st.title("🦊 Paletten Fuchs – Grafik & Gewicht")
st.subheader("Clean-Ansicht (Grafik) – Euro + Industrie")

c1, c3 = st.columns([1,1])
with c1:
    euro_n = st.number_input("Euro-Paletten", 0, 40, 33, step=1)
with c3:
    ind_n = st.number_input("Industrie-Paletten", 0, 40, 0, step=1)

exact_tail = st.toggle("Exakt bis hinten (Euro)", value=False,
                       help="Euro füllt exakt 1360 cm (Heck 0 cm), keine 1-quer im Heck (letzte 4 Reihen), letzte Reihe voll.")

with st.expander("Gewicht & Modus (optional)", expanded=False):
    colw = st.columns([1.2,1.2,1.6])
    with colw[0]:
        kg_euro = st.number_input("kg/Euro", 0, 2000, 700, step=10)
    with colw[1]:
        kg_ind  = st.number_input("kg/Industrie", 0, 2500, 900, step=10)
    with colw[2]:
        mode = st.radio("Modus", ["Aus", "Block vorne", "Block hinten", "Verteilen (Hecklast)"],
                        index=0, horizontal=True)
    weight_mode = (mode != "Aus")

    all_heavy = st.toggle("Schwer: alle Paletten sind schwer", value=False,
                          help="Markiert alle Paletten als schwer (unabhängig vom Modus).")

    hvy_e = hvy_i = 0
    group_block = True
    type_order = ("EURO","IND")
    if mode in ("Block vorne", "Block hinten"):
        cB = st.columns([1,1,1.4])
        with cB[0]:
            hvy_e = st.number_input("Schwere Euro (Stk.)", 0, 200, 0, step=1)
        with cB[1]:
            hvy_i = st.number_input("Schwere Industrie (Stk.)", 0, 200, 0, step=1)
        with cB[2]:
            group_block = st.checkbox("Block nach Typ sortieren", value=True)
        cBo = st.columns([1,1])
        with cBo[0]:
            first = st.radio("Reihenfolge im Block", ["Euro zuerst","Industrie zuerst"], index=0, horizontal=True)
        type_order = ("EURO","IND") if first=="Euro zuerst" else ("IND","EURO")

    heavy_total = 0
    if mode == "Verteilen (Hecklast)":
        heavy_total = st.number_input("Gesamtanzahl schwere Paletten", 0, 200, 20, step=1,
                                      help="Euro + Industrie zusammen; werden hecklastig verteilt.")

# ===================== 5) Clean-Aufbau mit Canvas-Weiche =====================
if use_user_layout:
    rows_clean: List[Dict] = []
else:
    rows_clean: List[Dict] = []
    if euro_n > 0:
        rows_clean += (build_euro_exact_tail(euro_n) if exact_tail else layout_for_preset_euro_stable(euro_n, singles_front=0))
    if ind_n > 0:
        rows_clean += layout_for_preset_industry(ind_n)

# 2) Gewichtslogik anwenden (nur wenn NICHT Canvas aktiv ist)
heavy_rows: Optional[Set[int]] = None
rows_clean_weighted = list(rows_clean)
if (not use_user_layout) and weight_mode:
    if mode == "Block vorne":
        rows_clean_weighted = reorder_rows_heavy(
            rows_clean_weighted, hvy_e, hvy_i, side="front",
            group_by_type=group_block, type_order=type_order
        )
    elif mode == "Block hinten":
        rows_clean_weighted = reorder_rows_heavy(
            rows_clean_weighted, hvy_e, hvy_i, side="rear",
            group_by_type=group_block, type_order=type_order
        )
    elif mode == "Verteilen (Hecklast)":
        total_pal = rows_pallets(rows_clean_weighted)
        qty = min(heavy_total, total_pal)
        if all_heavy:
            heavy_rows = set(range(len(rows_clean_weighted)))
        else:
            heavy_rows = set(range(len(rows_clean_weighted))) if qty >= total_pal else pick_heavy_rows_rear_biased(rows_clean_weighted, qty)

    if all_heavy and mode in ("Block vorne", "Block hinten"):
        heavy_rows = set(range(len(rows_clean_weighted)))

# ===================== 6) Zeichnen (Canvas oder Clean) =====================
if use_user_layout:
    total_from_canvas = sum(1 for it in user_layout_cm if it.get("typ") in ("Euro","Industrie"))
    st.info(f"Canvas aktiv: {total_from_canvas} Paletten erkannt – Meta: {user_meta.name} · total={user_meta.total_pal}, heavy={user_meta.heavy_count}")

    with st.expander("Unicode-Plan (Canvas)", expanded=False):
        import math
        TRAILER_W_CM_UNI = 246
        CELL_CM = 20
        cols = math.ceil(TRAILER_LEN_CM / CELL_CM)
        rows = math.ceil(TRAILER_W_CM_UNI / CELL_CM)
        grid = [["·" for _ in range(cols)] for __ in range(rows)]
        def cm_to_cells(v): return max(1, round(v / CELL_CM))
        for it in user_layout_cm:
            x = cm_to_cells(it["x_cm"])
            y = cm_to_cells(it["y_cm"])
            w = cm_to_cells(it["w_cm"])
            h = cm_to_cells(it["h_cm"])
            ch = "▭" if it["typ"] == "Euro" else ("▮" if it["typ"] == "Industrie" else "■")
            x = min(max(1, x), cols); y = min(max(1, y), rows)
            w = max(1, min(w, cols - x + 1)); h = max(1, min(h, rows - y + 1))
            for r in range(y-1, y-1+h):
                for c in range(x-1, x-1+w):
                    grid[r][c] = ch
        st.text("\n".join("".join(row) for row in grid))

    draw_canvas_layout("Canvas: Benutzerdefiniertes Layout", user_layout_cm, figsize=(8, 1.7))
else:
    title_clean = f"Clean: {euro_n} Euro ({'exakt bis hinten' if exact_tail else 'stabil'}) + {ind_n} Industrie"
    draw_graph(
        title_clean + (" – (Gewichtsansicht)" if weight_mode else ""),
        rows_clean_weighted if weight_mode else rows_clean,
        figsize=(8, 1.7),
        weight_mode=weight_mode,
        kg_euro=kg_euro if weight_mode else 0,
        kg_ind=kg_ind if weight_mode else 0,
        heavy_euro_count=hvy_e if (weight_mode and mode in ('Block vorne','Block hinten')) else 0,
        heavy_ind_count=hvy_i if (weight_mode and mode in ('Block vorne','Block hinten')) else 0,
        heavy_side=('rear' if mode=='Block hinten' else 'front'),
        heavy_rows=heavy_rows if weight_mode else None,
        show_axle_note=True
    )

# ------------------ Varianten-Konfiguration (JSON) ------------------
st.markdown("##### Varianten-Konfiguration")
conf_col1, conf_col2 = st.columns([1,1])
with conf_col1:
    cfg_file = st.file_uploader("variants.json laden", type=["json"], accept_multiple_files=False)
with conf_col2:
    use_default_cfg = st.toggle(
        "Default-Varianten verwenden",
        value=(False if cfg_file else True),
        help="Wenn aktiviert, werden die eingebauten Standard-Varianten verwendet und die hochgeladene JSON ignoriert."
    )

DEFAULT_CFG = {
    "variants": [
        { "title": "Var A – alles längs",         "type": "all_long" },
        { "title": "Var B – 2×quer Heckblock",    "type": "rear_block",     "approx_block": 15 },
        { "title": "Var C – gemischt (Periodik)", "type": "mixed_periodic", "period": 4 },
        { "title": "Var D – alternative Blockung","type": "alt_block" }
    ],
    "industry_position": { "A":"front","B":"front","C":"front","D":"rear" }
}

cfg_source = "Default"
if cfg_file and not use_default_cfg:
    try:
        cfg = json.load(cfg_file)
        cfg_source = f"Upload: {getattr(cfg_file, 'name', 'variants.json')}"
        st.success(f"Varianten-Konfiguration geladen ({cfg_source}).")
    except Exception as e:
        st.error(f"Konfig konnte nicht gelesen werden: {e} – verwende Default.")
        cfg = DEFAULT_CFG
        cfg_source = "Default (Fallback)"
else:
    cfg = DEFAULT_CFG

show_cfg_debug = st.checkbox("Konfig-Debug anzeigen", value=False,
                             help="Zeigt geladene Varianten und Gründe, warum Varianten ggf. gefiltert wurden.")

show_variants = st.toggle("Vordefinierte Varianten (2×2) anzeigen", value=False,
                          help="Zeigt Varianten aus der JSON-Konfig basierend auf den obigen Eingaben.")
if show_variants:
    variants_dbg, skipped, total_cfg = generate_variants_from_config(
        cfg, euro_n, ind_n, exact_tail=exact_tail, weight_mode=weight_mode
    )
    st.caption(f"Quelle: **{cfg_source}** – Varianten geladen: {len(variants_dbg)}/{total_cfg}")

    figsz = (6.6, 1.25)
    cols_top = st.columns(2, gap="small")
    cols_bot = st.columns(2, gap="small")
    slots = [cols_top[0], cols_top[1], cols_bot[0], cols_bot[1]]
    for i, (title_v, rows_v) in enumerate(variants_dbg[:4]):
        with slots[i]:
            draw_graph(title_v, rows_v, figsize=figsz, weight_mode=False)
    if len(variants_dbg) == 0:
        st.info("Keine Varianten nach Filterung übrig. Prüfe n_exact / Min/Max / weight_required.")
    elif len(variants_dbg) > 4:
        st.info(f"In der Konfig sind {len(variants_dbg)} Varianten. Es werden die ersten 4 gezeigt.")
    if show_cfg_debug:
        with st.expander("Debug: Geladene Konfig & verworfene Varianten", expanded=False):
            st.write("Verworfene Varianten (Grund):")
            for t, why in skipped: st.write(f"- {t}: {why}")
            st.write("Roh-Konfig:"); st.json(cfg, expanded=False)

# ---- Auto-Bestenliste (GROG) ----
st.markdown("#### Auto-Bestenliste (Grog)")
auto_on = st.toggle("Grog aktivieren", value=True,
                    help="Bewertet alle Varianten automatisch und zeigt die besten an.")
target_rear = st.slider("Ziel-Heckanteil (%)", 40, 65, 52, step=1) / 100.0

all_variants, _sk, _tot = generate_variants_from_config(cfg, euro_n, ind_n, exact_tail=exact_tail, weight_mode=False)
if auto_on and all_variants:
    picked = grog_pick_best(all_variants, kg_euro=kg_euro, kg_ind=kg_ind,
                            target_rear_share=target_rear, topk=4)
    figsz = (6.6, 1.25)
    cols_top = st.columns(2, gap="small")
    cols_bot = st.columns(2, gap="small")
    slots = [cols_top[0], cols_top[1], cols_bot[0], cols_bot[1]]
    for i, (title_v, rows_v, sc, rear) in enumerate(picked):
        with slots[i]:
            draw_graph(f"{title_v} – Score {sc:.1f} – Heck {rear*100:.0f}%", rows_v,
                       figsize=figsz, weight_mode=False)
elif auto_on and not all_variants:
    st.info("Keine Varianten vorhanden.")

# ------------------ Varianten (2×2): IMMER anzeigen ------------------
st.markdown("#### Vordefinierte Varianten (2×2)")
variants_plain, _sk2, _tot2 = generate_variants_from_config(
    cfg, euro_n, ind_n, exact_tail=exact_tail, weight_mode=False
)
figsz = (6.6, 1.25)
cols_top = st.columns(2, gap="small")
cols_bot = st.columns(2, gap="small")
slots = [cols_top[0], cols_top[1], cols_bot[0], cols_bot[1]]
for i, (title_v, rows_v) in enumerate(variants_plain[:4]):
    with slots[i]:
        draw_graph(title_v, rows_v, figsize=figsz, weight_mode=False, show_axle_note=False)

if len(variants_plain) == 0:
    st.info("Keine Varianten in der Konfig gefunden.")
elif len(variants_plain) > 4:
    st.caption(f"Es sind {len(variants_plain)} Varianten in der JSON. Momentan werden die ersten 4 gezeigt.")

# ===== Zusatz-Grid: Nur wenn Gewicht aktiv ist -> bevorzugt Heavy-Varianten aus JSON =====
if weight_mode:
    variants_heavy, _sk3, _tot3 = generate_variants_from_config(
        cfg, euro_n, ind_n, exact_tail=exact_tail, weight_mode=True
    )
    if len(variants_heavy) == 0:
        variants_heavy = variants_plain  # Fallback
    st.markdown("#### Varianten mit Gewichts-Logik (2×2)")
    cols_top_w = st.columns(2, gap="small")
    cols_bot_w = st.columns(2, gap="small")
    slots_w = [cols_top_w[0], cols_top_w[1], cols_bot_w[0], cols_bot_w[1]]

    for i, (title_v, rows_v) in enumerate(variants_heavy[:4]):
        with slots_w[i]:
            if mode in ("Block vorne", "Block hinten"):
                heavy_rows_v = set(range(len(rows_v))) if all_heavy else None
                draw_graph(
                    f"{title_v} – {'Block hinten' if mode=='Block hinten' else 'Block vorne'}",
                    rows_v,
                    figsize=figsz,
                    weight_mode=True,
                    kg_euro=kg_euro,
                    kg_ind=kg_ind,
                    heavy_euro_count=hvy_e,
                    heavy_ind_count=hvy_i,
                    heavy_side=("rear" if mode=="Block hinten" else "front"),
                    heavy_rows=heavy_rows_v,
                    show_axle_note=True
                )
            elif mode == "Verteilen (Hecklast)":
                total_pal_v = rows_pallets(rows_v)
                qty = min(heavy_total, total_pal_v)
                if all_heavy:
                    heavy_rows_v = set(range(len(rows_v)))
                else:
                    heavy_rows_v = set(range(len(rows_v))) if qty >= total_pal_v else pick_heavy_rows_rear_biased(rows_v, qty)
                draw_graph(
                    f"{title_v} – Verteilen (hecklastig)",
                    rows_v,
                    figsize=figsz,
                    weight_mode=True,
                    kg_euro=kg_euro,
                    kg_ind=kg_ind,
                    heavy_rows=heavy_rows_v,
                    show_axle_note=True
                )

# ===================== 7) Presets-Export (außerhalb des Expanders) =====================
st.download_button(
    "Presets (Canvas) exportieren",
    data=export_all_presets_json(),
    file_name="palettenfuchs_presets.json",
    mime="application/json"
)

st.caption(
    "Grafik 1360×240 cm. Grün=Euro längs (120×80), Blau=Euro quer (80×120), Orange=Industrie (120×100). "
    "Tail-Regel: In den letzten 4 Reihen keine Einzel-quer; letzte Reihe immer voll. "
    "„Exakt bis hinten (Euro)“ füllt 1360 cm ohne Heck-Luft. "
    "Varianten erweiterbar per JSON; Typen: all_long, rear_block, mixed_periodic, alt_block, "
    "recipe (rows: 1/2/3), heavy_auto_rear, light_auto_mix. "
    "Filter: n_exact / n_min / n_max / weight_required / weight_forbidden (+ euro_min/max, ind_min/max). "
    "Achslast-Schätzung ist grob (Hebelmodell)."
)
