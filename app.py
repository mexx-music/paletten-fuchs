# app.py
# Paletten Fuchs – Clean + große Grafik + Gewichtsmodi:
# - Block vorne (unverändert)
# - Block hinten (unverändert)
# - Verteilen (Hecklast) -> Euro & Industrie gemeinsam zählen, hinten dichter
#   (ohne Reihen-Umordnung; Markierung & Summen, leichtes Einzel/Doppel-Muster)
#
# Zusätzlich: Inline 2×2 (optional) + Tabs (optional) – weiter nutzbar.

from typing import List, Dict, Optional, Tuple, Set
import streamlit as st

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
        out.append(r)
        s += L
    return out

# --- Euro-Layout (ohne Gewichtsumordnung) ---
def layout_for_preset_euro(n: int, singles_front: int = 0) -> List[Dict]:
    rows: List[Dict] = []
    remaining = n

    # 1) Einzel quer vorne (0/1/2)
    take = min(max(0, singles_front), 2, remaining)
    for _ in range(take):
        rows.append(euro_row_trans1())
    remaining -= take

    # 2) 2-quer, wenn (rest-2)%3==0
    if remaining >= 2 and (remaining - 2) % 3 == 0:
        rows.append(euro_row_trans2())
        remaining -= 2

    # 3) ggf. Singles zurücknehmen, bis durch 3 teilbar
    while remaining % 3 != 0 and any(r["type"] == "EURO_1_TRANS" for r in rows):
        for i, r in enumerate(rows):
            if r["type"] == "EURO_1_TRANS":
                rows.pop(i); remaining += 1; break

    # 4) 3-längs auffüllen
    if remaining > 0:
        rows += [euro_row_long() for _ in range(remaining // 3)]

    # 5) Absicherung
    if sum(r.get("pallets", 0) for r in rows) != n:
        if n >= 2 and (n - 2) % 3 == 0:
            rows = [euro_row_trans2()] + [euro_row_long() for _ in range((n - 2) // 3)]
        else:
            rows = [euro_row_long() for _ in range(n // 3)]
            rest = n % 3
            if rest == 2: rows.insert(0, euro_row_trans2())
            elif rest == 1: rows.insert(0, euro_row_trans1())

    return rows

# --- Industrie-Layout (ohne Gewichtsumordnung) ---
def layout_for_preset_industry(n: int) -> List[Dict]:
    if n <= 0: return []
    rows: List[Dict] = []
    single = n % 2
    full   = n // 2
    if single:
        rows.append(ind_single())     # 1 vorne
    rows += [ind_row2_long() for _ in range(full)]
    return rows

# ------------------ GLOBAL: Block (für Block vorne/hinten) ------------------
def _cat_of_row(r: Dict) -> str:
    t = r.get("type","")
    return "EURO" if t.startswith("EURO_") else ("IND" if t.startswith("IND") else "OTHER")

def reorder_rows_heavy(rows: List[Dict],
                       heavy_euro_count: int,
                       heavy_ind_count: int,
                       side: str = "front",              # "front" | "rear"
                       group_by_type: bool = True,
                       type_order: Tuple[str,str] = ("EURO","IND")) -> List[Dict]:
    """Zieht die ersten 'heavy_*_count' Paletten als zusammenhängenden Block an die gewählte Seite."""
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
        if need_e <= 0 and need_i <= 0:
            break

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

# ------------------ VERTEILEN (HECKLAST): Reihen auswählen (nur Markierung) ------------------
def pick_heavy_rows_rear_biased(rows: List[Dict], heavy_total: int) -> Set[int]:
    """
    Wählt Reihen-Indices, deren Paletten-Summe ≈ heavy_total ergibt – ohne Reihen umzubauen.
    Hecklast: Reihen nahe dem Ende haben höhere Priorität; leichtes Einzel/Doppel-Muster.
    """
    if heavy_total <= 0 or not rows:
        return set()

    N = len(rows)
    # Score je Reihe: Position + sanfter Quadratik-Bias + Bonus für 1/2er-Reihen
    scored = []
    for i, r in enumerate(rows):
        pos = (i + 1) / N                 # vorne~0 ... hinten~1
        bias = 0.6*pos + 0.4*(pos**2)     # stärkerer Bias nach hinten
        typ = r.get("type","")
        bonus = 0.08 if ("_1_" in typ or "_2_" in typ or "IND_SINGLE" in typ) else 0.0
        scored.append((i, bias + bonus, r.get("pallets", 0)))

    # Greedy von hinten nach vorne (höchster Score zuerst),
    # vermeide direkte Nachbarn (zur Not zulassen, um Soll zu erreichen).
    scored.sort(key=lambda t: t[1], reverse=True)
    picked: Set[int] = set()
    total = 0

    def neighbors(k: int) -> bool:
        return (k-1 in picked) or (k+1 in picked)

    # 1. Runde: ohne Nachbarschaft
    for idx, _, pal in scored:
        if total >= heavy_total: break
        if neighbors(idx): continue
        picked.add(idx); total += pal

    # 2. Runde: gelegentlich Paare zulassen (Doppel-Muster),
    # aber nie 3 direkt hintereinander
    if total < heavy_total:
        for idx, _, pal in scored:
            if total >= heavy_total: break
            if idx in picked: continue
            if ((idx-1 in picked) and (idx-2 in picked)) or ((idx+1 in picked) and (idx+2 in picked)):
                continue  # würde Kettenbildung 3er verursachen
            picked.add(idx); total += pal

    return picked

# ------------------ Grafik (matplotlib) ------------------
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

COLOR_EURO_LONG = "#d9f2d9"   # hellgrün
COLOR_EURO_QUER = "#cfe8ff"   # hellblau
COLOR_IND      = "#ffe2b3"    # hellorange
EDGE           = "#4a4a4a"

def rows_to_rects(rows: List[Dict]) -> List[Tuple[float,float,float,float,str,str,bool]]:
    """Rechtecke ohne Markierung: (x,y,w,h,color,cat,heavy=False)."""
    rects = []
    x = 0
    for r in rows:
        t = r["type"]; L = r["len_cm"]
        if t == "EURO_3_LONG":
            for lane in range(3):
                rects.append((x, lane*80, 120, 80, COLOR_EURO_LONG, "EURO", False))
            x += L
        elif t == "EURO_2_TRANS":
            for lane in range(2):
                rects.append((x, lane*120, 80, 120, COLOR_EURO_QUER, "EURO", False))
            x += L
        elif t == "EURO_1_TRANS":
            rects.append((x, 60, 80, 120, COLOR_EURO_QUER, "EURO", False))
            x += L
        elif t == "IND_ROW_2_LONG":
            rects.append((x, 20, 120, 100, COLOR_IND, "IND", False))
            rects.append((x,120, 120, 100, COLOR_IND, "IND", False))
            x += L
        elif t == "IND_SINGLE":
            rects.append((x, 70, 120, 100, COLOR_IND, "IND", False))
            x += L
    return rects

def rows_to_rects_with_row_index(rows: List[Dict]):
    """Wie rows_to_rects, liefert zusätzlich row_idx je Rechteck (für Verteil-Modus)."""
    rects = []   # (x,y,w,h,color,cat)
    meta  = []   # {"row_idx": i, "cat": "EURO"/"IND"}
    x = 0
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
    """Block-Modus: markiert die ersten heavy_* ab Front oder Rear (pro Typ)."""
    rects = []
    x = 0
    euro_rects = []
    ind_rects  = []

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

    # Euro
    euro_cnt = len(euro_rects)
    if heavy_euro_count > 0 and euro_cnt > 0:
        indices = (list(reversed(euro_rects)) if heavy_euro_side == "rear" else euro_rects)[:heavy_euro_count]
        for idx in indices:
            x0,y0,w0,h0,c0,cat0,_ = rects[idx]
            rects[idx] = (x0,y0,w0,h0,c0,cat0,True)
    euro_hvy = sum(1 for i in euro_rects if rects[i][6] is True)

    # Industrie
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
               # Block-Parameter:
               heavy_euro_count: int = 0, heavy_ind_count: int = 0, heavy_side: str = "front",
               # Verteilen-Parameter:
               heavy_rows: Optional[Set[int]] = None):
    """
    Grafische Draufsicht. Drei Modi:
      - Kein Gewicht: rows_to_rects
      - Block: rows_to_rects_with_weights (pro Typ, Front/Rear)
      - Verteilen: rows_to_rects_with_row_index + heavy_rows (Euro+Ind gemeinsam, Heck-Bias)
    """
    if not weight_mode:
        rects = rows_to_rects(cap_to_trailer(rows))
        euro_cnt = sum(1 for *_,cat,_ in rects if cat=="EURO")
        ind_cnt  = sum(1 for *_,cat,_ in rects if cat=="IND")
        euro_hvy = ind_hvy = 0
    elif heavy_rows is not None:
        # Verteilen (Hecklast)
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
        # Block
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
    st.pyplot(fig); import matplotlib.pyplot as _plt; _plt.close(fig)

    if weight_mode and (kg_euro or kg_ind):
        total = euro_cnt * kg_euro + ind_cnt * kg_ind
        marked = (euro_hvy * kg_euro + ind_hvy * kg_ind)
        st.caption(f"Gewicht: gesamt ≈ **{total:.0f} kg**, markiert ≈ **{marked:.0f} kg** "
                   f"(Euro: {euro_cnt}×{kg_euro} kg, Ind.: {ind_cnt}×{kg_ind} kg)")

# ------------------ Sidebar-Schalter ------------------
st.title("🦊 Paletten Fuchs – Grafik & Gewicht")

INLINE_GRID_ON = st.sidebar.toggle("Vier Varianten (2×2) direkt oben", value=False)
SHOW_TABS      = st.sidebar.toggle("Vergleich (Tabs) anzeigen", value=True)

# ------------------ Clean-Ansicht (oben) ------------------
st.subheader("Clean-Ansicht (Grafik) – Euro + Industrie")

c1, c2, c3 = st.columns(3)
with c1:
    euro_n = st.number_input("Euro-Paletten", 0, 40, 33, step=1)
with c2:
    singles_front = st.slider("Einzel-quer vorne (0/1/2)", 0, 2, 0)
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

    # Eingaben für Block-Modus (unverändert):
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

    # Eingabe für Verteilen (Euro+Ind gemeinsam):
    heavy_total = 0
    if mode == "Verteilen (Hecklast)":
        heavy_total = st.number_input("Gesamtanzahl schwere Paletten", 0, 200, 20, step=1,
                                      help="Euro + Industrie zusammen; werden hecklastig verteilt.")

# 1) Reihen bauen (ohne Umordnung)
rows_clean: List[Dict] = []
if euro_n > 0:
    rows_clean += layout_for_preset_euro(euro_n, singles_front=singles_front)
if ind_n > 0:
    rows_clean += layout_for_preset_industry(ind_n)

# 2) Gewichtslogik anwenden (Block vs. Verteilen)
heavy_rows: Optional[Set[int]] = None
if weight_mode:
    if mode == "Block vorne":
        rows_clean = reorder_rows_heavy(rows_clean, hvy_e, hvy_i, side="front",
                                        group_by_type=group_block, type_order=type_order)
    elif mode == "Block hinten":
        rows_clean = reorder_rows_heavy(rows_clean, hvy_e, hvy_i, side="rear",
                                        group_by_type=group_block, type_order=type_order)
    elif mode == "Verteilen (Hecklast)":
        # Alle schwer? -> markiere alle Reihen; sonst hecklastig auswählen
        total_pal = sum(r.get("pallets",0) for r in rows_clean)
        qty = min(heavy_total, total_pal)
        if qty >= total_pal:
            heavy_rows = set(range(len(rows_clean)))   # alle Reihen schwer
        else:
            heavy_rows = pick_heavy_rows_rear_biased(rows_clean, qty)

# 3) Zeichnen
title = f"Clean: {euro_n} Euro (S{singles_front}) + {ind_n} Industrie"
draw_graph(
    title,
    rows_clean,
    figsize=(8, 1.7),
    weight_mode=weight_mode,
    kg_euro=kg_euro if weight_mode else 0,
    kg_ind=kg_ind if weight_mode else 0,
    heavy_euro_count=hvy_e if (weight_mode and mode in ("Block vorne","Block hinten")) else 0,
    heavy_ind_count=hvy_i if (weight_mode and mode in ("Block vorne","Block hinten")) else 0,
    heavy_side=("rear" if mode=="Block hinten" else "front"),
    heavy_rows=heavy_rows if (weight_mode and mode=="Verteilen (Hecklast)") else None
)

# ------------------ Inline 2×2 Vergleich (optional) ------------------
def inline_four_variants_grid():
    st.markdown("#### Vier Varianten (2×2, kompakt)")

    def controls(idx: int):
        c = st.columns(3)
        with c[0]:
            e = st.number_input(f"Euro V{idx}", 0, 40, 0 if idx>1 else 33, step=1, key=f"iv_e{idx}")
        with c[1]:
            s = st.slider(f"Einzel V{idx}", 0, 2, 0, key=f"iv_s{idx}")
        with c[2]:
            i = st.number_input(f"Industrie V{idx}", 0, 40, 0, step=1, key=f"iv_i{idx}")

        with st.expander(f"Gewicht (optional) V{idx}", expanded=False):
            m = st.radio(f"Modus V{idx}",
                         ["Aus", "Block vorne", "Block hinten", "Verteilen (Hecklast)"],
                         index=0, horizontal=True, key=f"iv_mode{idx}")
            wm = (m != "Aus")
            kge = kgi = 0
            he = hi = 0
            group_v = True
            order_v = ("EURO","IND")
            heavy_total_v = 0
            if wm:
                kge = st.number_input(f"kg Euro V{idx}", 0, 2000, 700, step=10, key=f"iv_kge{idx}")
                kgi = st.number_input(f"kg Ind V{idx}", 0, 2500, 900, step=10, key=f"iv_kgi{idx}")
                if m in ("Block vorne","Block hinten"):
                    he  = st.number_input(f"schwere Euro V{idx}", 0, 200, 0, step=1, key=f"iv_he{idx}")
                    hi  = st.number_input(f"schwere Ind V{idx}", 0, 200, 0, step=1, key=f"iv_hi{idx}")
                    group_v = st.checkbox("Block nach Typ sortieren", value=True, key=f"iv_group{idx}")
                    ord_lbl = st.radio("Reihenfolge", ["Euro zuerst","Industrie zuerst"],
                                       index=0, horizontal=True, key=f"iv_order{idx}")
                    order_v = ("EURO","IND") if ord_lbl=="Euro zuerst" else ("IND","EURO")
                else:
                    heavy_total_v = st.number_input(f"Gesamt schwer V{idx}", 0, 200, 20, step=1, key=f"iv_ht{idx}")

        # Reihen
        r: List[Dict] = []
        if e > 0: r += layout_for_preset_euro(e, singles_front=s)
        if i > 0: r += layout_for_preset_industry(i)

        # Gewichtslogik
        heavy_rows_v: Optional[Set[int]] = None
        if wm:
            if m == "Block vorne":
                r = reorder_rows_heavy(r, he, hi, side="front", group_by_type=group_v, type_order=order_v)
            elif m == "Block hinten":
                r = reorder_rows_heavy(r, he, hi, side="rear", group_by_type=group_v, type_order=order_v)
            elif m == "Verteilen (Hecklast)":
                total_pal_v = sum(x.get("pallets",0) for x in r)
                qty = min(heavy_total_v, total_pal_v)
                if qty >= total_pal_v:
                    heavy_rows_v = set(range(len(r)))
                else:
                    heavy_rows_v = pick_heavy_rows_rear_biased(r, qty)

        return r, wm, kge, kgi, he, hi, heavy_rows_v, m

    r1,w1,kge1,kgi1,he1,hi1,hr1,m1 = controls(1)
    r2,w2,kge2,kgi2,he2,hi2,hr2,m2 = controls(2)
    r3,w3,kge3,kgi3,he3,hi3,hr3,m3 = controls(3)
    r4,w4,kge4,kgi4,he4,hi4,hr4,m4 = controls(4)

    figsz = (6.6, 1.25)
    row1 = st.columns(2, gap="small")
    with row1[0]:
        draw_graph("V1", r1, figsize=figsz, weight_mode=w1, kg_euro=kge1, kg_ind=kgi1,
                   heavy_euro_count=he1 if m1 in ("Block vorne","Block hinten") else 0,
                   heavy_ind_count=hi1  if m1 in ("Block vorne","Block hinten") else 0,
                   heavy_side=("rear" if m1=="Block hinten" else "front"),
                   heavy_rows=hr1 if m1=="Verteilen (Hecklast)" else None)
    with row1[1]:
        draw_graph("V2", r2, figsize=figsz, weight_mode=w2, kg_euro=kge2, kg_ind=kgi2,
                   heavy_euro_count=he2 if m2 in ("Block vorne","Block hinten") else 0,
                   heavy_ind_count=hi2  if m2 in ("Block vorne","Block hinten") else 0,
                   heavy_side=("rear" if m2=="Block hinten" else "front"),
                   heavy_rows=hr2 if m2=="Verteilen (Hecklast)" else None)

    row2 = st.columns(2, gap="small")
    with row2[0]:
        draw_graph("V3", r3, figsize=figsz, weight_mode=w3, kg_euro=kge3, kg_ind=kgi3,
                   heavy_euro_count=he3 if m3 in ("Block vorne","Block hinten") else 0,
                   heavy_ind_count=hi3  if m3 in ("Block vorne","Block hinten") else 0,
                   heavy_side=("rear" if m3=="Block hinten" else "front"),
                   heavy_rows=hr3 if m3=="Verteilen (Hecklast)" else None)
    with row2[1]:
        draw_graph("V4", r4, figsize=figsz, weight_mode=w4, kg_euro=kge4, kg_ind=kgi4,
                   heavy_euro_count=he4 if m4 in ("Block vorne","Block hinten") else 0,
                   heavy_ind_count=hi4  if m4 in ("Block vorne","Block hinten") else 0,
                   heavy_side=("rear" if m4=="Block hinten" else "front"),
                   heavy_rows=hr4 if m4=="Verteilen (Hecklast)" else None)

if INLINE_GRID_ON:
    inline_four_variants_grid()

# ------------------ Vergleich (Tabs) – 4 Varianten (optional) ------------------
def compare_tabs_four_variants():
    st.subheader("Vergleich (Tabs) – 4 Varianten")

    def tab_ui(label, defaults=(33,0,0)):
        with st.tab(label):
            e = st.number_input(f"Euro ({label})", 0, 40, defaults[0], step=1, key=f"tv_e_{label}")
            s = st.slider(f"Einzel ({label})", 0, 2, defaults[1], key=f"tv_s_{label}")
            i = st.number_input(f"Industrie ({label})", 0, 40, defaults[2], step=1, key=f"tv_i_{label}")

            with st.expander(f"Gewicht ({label})", expanded=False):
                m = st.radio(f"Modus ({label})",
                             ["Aus", "Block vorne", "Block hinten", "Verteilen (Hecklast)"],
                             index=0, horizontal=True, key=f"tv_mode_{label}")
                wm = (m != "Aus")
                kge = kgi = 0
                he = hi = 0
                group_v = True
                order_v = ("EURO","IND")
                heavy_total_v = 0
                if wm:
                    kge = st.number_input(f"kg Euro ({label})", 0, 2000, 700, step=10, key=f"tv_kge_{label}")
                    kgi = st.number_input(f"kg Ind ({label})", 0, 2500, 900, step=10, key=f"tv_kgi_{label}")
                    if m in ("Block vorne","Block hinten"):
                        he  = st.number_input(f"schwere Euro ({label})", 0, 200, 0, step=1, key=f"tv_he_{label}")
                        hi  = st.number_input(f"schwere Ind ({label})", 0, 200, 0, step=1, key=f"tv_hi_{label}")
                        group_v = st.checkbox("Block nach Typ sortieren", value=True, key=f"tv_group_{label}")
                        ord_lbl = st.radio("Reihenfolge", ["Euro zuerst","Industrie zuerst"],
                                           index=0, horizontal=True, key=f"tv_order_{label}")
                        order_v = ("EURO","IND") if ord_lbl=="Euro zuerst" else ("IND","EURO")
                    else:
                        heavy_total_v = st.number_input(f"Gesamt schwer ({label})", 0, 200, 20, step=1, key=f"tv_ht_{label}")

            # Reihen
            r: List[Dict] = []
            if e > 0: r += layout_for_preset_euro(e, singles_front=s)
            if i > 0: r += layout_for_preset_industry(i)

            # Gewichtslogik
            heavy_rows_v: Optional[Set[int]] = None
            if wm:
                if m == "Block vorne":
                    r = reorder_rows_heavy(r, he, hi, side="front", group_by_type=group_v, type_order=order_v)
                elif m == "Block hinten":
                    r = reorder_rows_heavy(r, he, hi, side="rear", group_by_type=group_v, type_order=order_v)
                elif m == "Verteilen (Hecklast)":
                    total_pal_v = sum(x.get("pallets",0) for x in r)
                    qty = min(heavy_total_v, total_pal_v)
                    if qty >= total_pal_v:
                        heavy_rows_v = set(range(len(r)))
                    else:
                        heavy_rows_v = pick_heavy_rows_rear_biased(r, qty)

            draw_graph(f"{label}: {e} Euro (S{s}) + {i} Ind.", r,
                       weight_mode=wm, kg_euro=kge, kg_ind=kgi,
                       heavy_euro_count=he if m in ("Block vorne","Block hinten") else 0,
                       heavy_ind_count=hi if m in ("Block vorne","Block hinten") else 0,
                       heavy_side=("rear" if m=="Block hinten" else "front"),
                       heavy_rows=heavy_rows_v if m=="Verteilen (Hecklast)" else None)

    tab1, tab2, tab3, tab4 = st.tabs(["Var 1", "Var 2", "Var 3", "Var 4"])
    with tab1: tab_ui("Var 1", (33,0,0))
    with tab2: tab_ui("Var 2", (32,2,0))
    with tab3: tab_ui("Var 3", (31,1,0))
    with tab4: tab_ui("Var 4", (24,0,0))

if SHOW_TABS:
    compare_tabs_four_variants()

st.caption("Grafik 1360×240 cm. Grün=Euro längs (120×80), Blau=Euro quer (80×120), Orange=Industrie (120×100). "
           "Modi: Block vorne/hinten (unverändert) oder Verteilen (Hecklast) mit Gesamt‑Schwerzahl (Euro+Industrie).")
