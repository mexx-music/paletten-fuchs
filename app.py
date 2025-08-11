# app.py
# Paletten Fuchs – Clean + Grafik + Gewichtsmodi
# – Buttons für Einzel-quer (1/2 vorne, mittig, 1/2 hinten + "Alle aktivieren")
# – Tail-Regel: Letzte 4 Reihen niemals Einzel-quer; letzte Reihe immer voll
# – "Exakt bis hinten (Euro)" – füllt exakt 1360 cm (Heck 0 cm), keine Singles im Tail
# – Eine 2×2-Ansicht mit vordefinierten Varianten (gekoppelt an die oberen Eingaben)
# – JSON-Konfig (variants.json) zum Erweitern der Varianten ohne Code-Upload

from typing import List, Dict, Optional, Tuple, Set
import streamlit as st
import json

st.set_page_config(page_title="Paletten Fuchs – Grafik & Gewicht", layout="centered")

# ------------------ Geometrie / Konstanten ------------------
TRAILER_LEN_CM = 1360
TRAILER_W_CM   = 240

EURO_L_CM, EURO_W_CM = 120, 80
IND_L_CM,  IND_W_CM  = 120, 100

# ------------------ Basis-Layoutfunktionen (Euro/Industrie) ------------------
def euro_row_long() -> Dict:
    return {"type": "EURO_3_LONG", "len_cm": EURO_L_CM, "pallets": 3}

def euro_row_trans2() -> Dict:
    return {"type": "EURO_2_TRANS", "len_cm": EURO_W_CM, "pallets": 2}

def euro_row_trans1() -> Dict:
    return {"type": "EURO_1_TRANS", "len_cm": EURO_W_CM, "pallets": 1}

def ind_row2_long() -> Dict:
    return {"type": "IND_ROW_2_LONG", "len_cm": IND_L_CM, "pallets": 2}

def ind_single() -> Dict:
    return {"type": "IND_SINGLE", "len_cm": IND_L_CM, "pallets": 1}

def cap_to_trailer(rows: List[Dict]) -> List[Dict]:
    out, s = [], 0
    for r in rows:
        L = r.get("len_cm", EURO_L_CM)
        if s + L > TRAILER_LEN_CM:
            break
        out.append(r); s += L
    return out

def rows_length_cm(rows: List[Dict]) -> int:
    return sum(r.get("len_cm", EURO_L_CM) for r in rows)

def rows_pallets(rows: List[Dict]) -> int:
    return sum(r.get("pallets", 0) for r in rows)

# ------------------ Tail-Guard: keine Singles in letzten 4 Reihen ------------------
def enforce_tail_no_single(rows: List[Dict], target_pal: int) -> List[Dict]:
    rows = cap_to_trailer(list(rows))

    # 1) Singles in den letzten 4 Reihen entfernen
    n = len(rows)
    if n > 0:
        tail_start = max(0, n - 4)
        cleaned = []
        for i, r in enumerate(rows):
            if i >= tail_start and r["type"] == "EURO_1_TRANS":
                continue
            cleaned.append(r)
        rows = cleaned

    # 2) Falls letzte Reihe Single -> weg
    if rows and rows[-1]["type"] == "EURO_1_TRANS":
        rows.pop()

    # 3) Fehlende Paletten auffüllen (ohne Trailer zu sprengen)
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

    # Erst 2-quer wenn passend
    if deficit % 3 == 2:
        placed = False
        for ins in range(0, insert_limit + 1):
            if try_insert(euro_row_trans2, ins):
                deficit -= 2; placed = True; break
        if not placed and rows_length_cm(rows) + EURO_W_CM <= TRAILER_LEN_CM:
            rows.append(euro_row_trans2()); deficit -= 2

    # Dann 3-längs vor dem Tail
    while deficit >= 3 and rows_length_cm(rows) + EURO_L_CM <= TRAILER_LEN_CM:
        rows = rows[:insert_limit] + [euro_row_long()] + rows[insert_limit:]
        deficit -= 3

    # Letzter Versuch: 2-quer am Anfang
    if deficit == 2 and rows_length_cm(rows) + EURO_W_CM <= TRAILER_LEN_CM:
        rows = [euro_row_trans2()] + rows; deficit -= 2

    if deficit != 0:
        base = layout_for_preset_euro_stable(target_pal, singles_front=0)
        rows = cap_to_trailer(base)

    # 4) Finale Sicherung
    n = len(rows); tail_start = max(0, n - 4)
    if any(r["type"] == "EURO_1_TRANS" for r in rows[tail_start:]):
        rows = cap_to_trailer(layout_for_preset_euro_stable(target_pal, singles_front=0))
    return rows

# ------------------ Euro-Layouts ------------------
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

def layout_for_preset_euro_buttons(
    n: int,
    front1: bool = False,
    front2: bool = False,
    mid1: bool = False,
    rear1: bool = False,
    rear2: bool = False
) -> List[Dict]:
    rows: List[Dict] = []; remaining = n
    singles_front = 2 if front2 else (1 if front1 else 0)
    singles_mid   = 1 if mid1 else 0
    singles_rear  = 2 if rear2 else (1 if rear1 else 0)
    singles_total = singles_front + singles_mid + singles_rear
    if singles_total > remaining:
        cut = singles_total - remaining
        singles_rear = max(0, singles_rear - cut)

    take = min(singles_front, remaining)
    for _ in range(take): rows.append(euro_row_trans1()); remaining -= 1

    reserve_after = singles_mid + singles_rear
    usable = max(0, remaining - reserve_after)

    if usable >= 2 and (usable - 2) % 3 == 0:
        rows.append(euro_row_trans2()); remaining -= 2; usable -= 2

    take3 = usable // 3
    rows += [euro_row_long() for _ in range(take3)]; remaining -= take3 * 3

    if singles_mid and remaining > 0:
        mid_idx = max(0, min(len(rows), len(rows)//2))
        rows.insert(mid_idx, euro_row_trans1()); remaining -= 1

    take_rear = min(singles_rear, remaining)
    for _ in range(take_rear):
        rows.append(euro_row_trans1()); remaining -= 1

    if remaining == 2 and rows_length_cm(rows) + EURO_W_CM <= TRAILER_LEN_CM:
        rows = [euro_row_trans2()] + rows
    elif remaining > 0:
        return layout_for_preset_euro_stable(n, singles_front=0)

    return enforce_tail_no_single(rows, n)

# --- Euro exakt bis hinten ---
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

# ------------------ Grafik (matplotlib) ------------------
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

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

def draw_graph(title: str,
               rows: List[Dict],
               figsize: Tuple[float,float] = (8, 1.7),
               weight_mode: bool = False,
               kg_euro: int = 0,
               kg_ind: int = 0,
               heavy_euro_count: int = 0, heavy_ind_count: int = 0, heavy_side: str = "front",
               heavy_rows: Optional[Set[int]] = None):
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

    if weight_mode and (kg_euro or kg_ind):
        total = euro_cnt * kg_euro + ind_cnt * kg_ind
        marked = (euro_hvy * kg_euro + ind_hvy * kg_ind)
        st.caption(f"Gewicht: gesamt ≈ **{total:.0f} kg**, markiert ≈ **{marked:.0f} kg** "
                   f"(Euro: {euro_cnt}×{kg_euro} kg, Ind.: {ind_cnt}×{kg_ind} kg)")

# ------------------ Vordefinierte Varianten (Euro) ------------------
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
    if k == 0:
        return build_euro_all_long(n, exact_tail=False)
    long_cnt = (n - 2*k) // 3
    rows = [euro_row_long() for _ in range(long_cnt)] + [euro_row_trans2() for _ in range(k)]
    return enforce_tail_no_single(rows, n)

def build_euro_mixed_periodic(n: int, period: int, exact_tail: bool) -> List[Dict]:
    if n <= 0: return []
    if exact_tail: return build_euro_exact_tail(n)
    approx_k = max(1, n // period)
    k = _choose_k_for_no_single(n, k_max=approx_k)
    if k == 0:
        return build_euro_all_long(n, exact_tail=False)
    long_cnt = (n - 2*k) // 3
    out: List[Dict] = []
    quota = max(1e-9, long_cnt / (k + 1))
    used_long = 0; used_k = 0
    cursor = 0.0
    while used_long + used_k < long_cnt + k:
        # einfache Streuung der 2-quer-Reihen
        if used_k < k and (used_long + used_k) >= cursor + quota * (used_k + 1):
            out.append(euro_row_trans2()); used_k += 1
        else:
            out.append(euro_row_long()); used_long += 1
    return enforce_tail_no_single(out, n)

def build_euro_alt_pattern(n: int, exact_tail: bool) -> List[Dict]:
    if n <= 0: return []
    if exact_tail: return build_euro_exact_tail(n)
    approx_block = max(1, n // 6)
    return build_euro_rear_2trans_block(n, approx_block=approx_block, exact_tail=False)

def combine_with_industry_pos(euro_rows: List[Dict], ind_n: int, pos: str) -> List[Dict]:
    if ind_n <= 0:
        return euro_rows
    ind_rows = layout_for_preset_industry(ind_n)
    return cap_to_trailer(ind_rows + euro_rows) if pos == "front" else cap_to_trailer(euro_rows + ind_rows)

def build_euro_by_type(t: str, n: int, exact_tail: bool, params: dict) -> List[Dict]:
    if t == "all_long":
        return build_euro_all_long(n, exact_tail=exact_tail)
    if t == "rear_block":
        approx = int(params.get("approx_block", 15))
        return build_euro_rear_2trans_block(n, approx_block=approx, exact_tail=exact_tail)
    if t == "mixed_periodic":
        per = int(params.get("period", 4))
        return build_euro_mixed_periodic(n, period=per, exact_tail=exact_tail)
    if t == "alt_block":
        return build_euro_alt_pattern(n, exact_tail=exact_tail)
    # Fallback
    return build_euro_all_long(n, exact_tail=exact_tail)

def generate_variants_from_config(cfg: dict, euro_n: int, ind_n: int, exact_tail: bool):
    """Erzeugt beliebig viele Varianten gemäß JSON-Config."""
    variants = cfg.get("variants", [])
    ind_pos_map = cfg.get("industry_position", {})
    out = []
    for idx, v in enumerate(variants):
        title = v.get("title", f"Var {idx+1}")
        vtype = v.get("type", "all_long")
        euro_rows = build_euro_by_type(vtype, euro_n, exact_tail, v)
        letter = chr(ord('A') + idx)  # A,B,C,...
        pos = v.get("industry_position", ind_pos_map.get(letter, "front"))
        rows = combine_with_industry_pos(euro_rows, ind_n, pos)
        out.append((title, rows))
    return out

# ------------------ UI ------------------
st.title("🦊 Paletten Fuchs – Grafik & Gewicht")
st.subheader("Clean-Ansicht (Grafik) – Euro + Industrie")

c1, c2, c3 = st.columns(3)
with c1:
    euro_n = st.number_input("Euro-Paletten", 0, 40, 33, step=1)
with c2:
    st.markdown("**Einzel-quer platzieren**")
    colbA, colbB = st.columns(2)
    with colbA:
        btn_front1 = st.toggle("1 vorne", value=False)
        btn_mid1   = st.toggle("mittig quer", value=False)
        btn_rear1  = st.toggle("1 hinten", value=False)
    with colbB:
        btn_front2 = st.toggle("2 vorne", value=False)
        btn_all    = st.toggle("Alle aktivieren", value=False,
                               help="Aktiviert 2 vorne, mittig und 2 hinten. Heck bleibt immer voll.")
        btn_rear2  = st.toggle("2 hinten", value=False)
    if btn_all:
        btn_front1 = False; btn_front2 = True
        btn_mid1   = True
        btn_rear1  = False; btn_rear2  = True

    exact_tail = st.toggle("Exakt bis hinten (Euro)", value=False,
                           help="Euro füllt exakt 1360 cm (Heck 0 cm), keine 1‑quer im Heck (letzte 4 Reihen), letzte Reihe voll.")
with c3:
    ind_n = st.number_input("Industrie-Paletten", 0, 40, 0, step=1)

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

# 1) Clean-Reihen aufbauen
rows_clean: List[Dict] = []
if euro_n > 0:
    if exact_tail:
        rows_clean += build_euro_exact_tail(euro_n)
    else:
        rows_clean += layout_for_preset_euro_buttons(
            euro_n,
            front1=btn_front1, front2=btn_front2,
            mid1=btn_mid1,
            rear1=btn_rear1, rear2=btn_rear2
        )
if ind_n > 0:
    rows_clean += layout_for_preset_industry(ind_n)

# 2) Gewichtslogik anwenden
heavy_rows: Optional[Set[int]] = None
if weight_mode:
    if mode == "Block vorne":
        rows_clean = reorder_rows_heavy(rows_clean, hvy_e, hvy_i, side="front",
                                        group_by_type=group_block, type_order=type_order)
    elif mode == "Block hinten":
        rows_clean = reorder_rows_heavy(rows_clean, hvy_e, hvy_i, side="rear",
                                        group_by_type=group_block, type_order=type_order)
    elif mode == "Verteilen (Hecklast)":
        total_pal = rows_pallets(rows_clean)
        qty = min(heavy_total, total_pal)
        heavy_rows = set(range(len(rows_clean))) if qty >= total_pal else pick_heavy_rows_rear_biased(rows_clean, qty)

# 3) Zeichnen Clean
title = f"Clean: {euro_n} Euro ({'exakt bis hinten' if exact_tail else 'Buttons'}) + {ind_n} Industrie"
draw_graph(
    title,
    rows_clean,
    figsize=(8, 1.7),
    weight_mode=weight_mode,
    kg_euro=kg_euro if weight_mode else 0,
    kg_ind=kg_ind if weight_mode else 0,
    heavy_euro_count=hvy_e if (weight_mode and mode in ('Block vorne','Block hinten')) else 0,
    heavy_ind_count=hvy_i if (weight_mode and mode in ('Block vorne','Block hinten')) else 0,
    heavy_side=('rear' if mode=='Block hinten' else 'front'),
    heavy_rows=heavy_rows if (weight_mode and mode=='Verteilen (Hecklast)') else None
)

# ------------------ Varianten-Konfiguration (JSON) ------------------
st.markdown("##### Varianten-Konfiguration")
conf_col1, conf_col2 = st.columns([1,1])
with conf_col1:
    cfg_file = st.file_uploader("variants.json laden", type=["json"], accept_multiple_files=False)
with conf_col2:
    use_default_cfg = st.toggle("Default-Varianten verwenden", value=True if not cfg_file else False)

# Default-Konfig (falls keine Datei geladen)
DEFAULT_CFG = {
    "variants": [
        { "title": "Var A – alles längs",         "type": "all_long" },
        { "title": "Var B – 2×quer Heckblock",    "type": "rear_block",     "approx_block": 15 },
        { "title": "Var C – gemischt (Periodik)", "type": "mixed_periodic", "period": 4 },
        { "title": "Var D – alternative Blockung","type": "alt_block" }
    ],
    "industry_position": { "A":"front","B":"front","C":"front","D":"rear" }
}

if cfg_file and not use_default_cfg:
    try:
        cfg = json.load(cfg_file)
        st.success("Varianten-Konfiguration geladen.")
    except Exception as e:
        st.error(f"Konfig konnte nicht gelesen werden: {e}")
        cfg = DEFAULT_CFG
else:
    cfg = DEFAULT_CFG

# 4) Eine 2×2-Ansicht: vordefinierte Varianten aus JSON (gekoppelt an Eingaben)
show_variants = st.toggle("Vordefinierte Varianten (2×2) anzeigen", value=False,
                          help="Zeigt Varianten aus der JSON-Konfig basierend auf den obigen Eingaben.")
if show_variants:
    variants = generate_variants_from_config(cfg, euro_n, ind_n, exact_tail=exact_tail)

    # bis zu 4 Varianten rendern
    figsz = (6.6, 1.25)
    cols_top = st.columns(2, gap="small")
    cols_bot = st.columns(2, gap="small")
    slots = [cols_top[0], cols_top[1], cols_bot[0], cols_bot[1]]

    for i, (title_v, rows_v) in enumerate(variants[:4]):
        with slots[i]:
            draw_graph(title_v, rows_v, figsize=figsz, weight_mode=False)

    if len(variants) == 0:
        st.info("Keine Varianten in der Konfig gefunden.")
    elif len(variants) > 4:
        st.info(f"In der Konfig sind {len(variants)} Varianten. Es werden die ersten 4 gezeigt.")

st.caption("Grafik 1360×240 cm. Grün=Euro längs (120×80), Blau=Euro quer (80×120), Orange=Industrie (120×100). "
           "Tail-Regel: In den letzten 4 Reihen keine Einzel-quer; letzte Reihe immer voll. "
           "„Exakt bis hinten (Euro)“ füllt 1360 cm ohne Heck-Luft. "
           "Die 2×2-Varianten können per JSON erweitert werden (Uploader).")
