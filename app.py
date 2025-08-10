# app.py
# Paletten Fuchs – Clean + große Grafik + Gewicht
# Modi: Block vorne | Block hinten | Verteilen (Hecklast)
# - "Verteilen (Hecklast)" markiert schwere Paletten ohne Reihen umzubauen:
#   * Nicht alle schwer: hecklastige, gleichmäßige Streuung mit leichtem Muster
#   * Alle schwer: alles markiert (Umordnung optionaler nächster Schritt)

from typing import List, Dict, Optional, Tuple, Set
import streamlit as st

st.set_page_config(page_title="Paletten Fuchs – Grafik & Gewicht", layout="centered")

# ------------------ Geometrie / Konstanten ------------------
TRAILER_LEN_CM = 1360
TRAILER_W_CM   = 240
EURO_L_CM, EURO_W_CM = 120, 80
IND_L_CM,  IND_W_CM  = 120, 100

# ------------------ Basis-Layoutfunktionen ------------------
def euro_row_long() -> Dict:   return {"type":"EURO_3_LONG","len_cm":EURO_L_CM,"pallets":3}
def euro_row_trans2() -> Dict: return {"type":"EURO_2_TRANS","len_cm":EURO_W_CM,"pallets":2}
def euro_row_trans1() -> Dict: return {"type":"EURO_1_TRANS","len_cm":EURO_W_CM,"pallets":1}
def ind_row2_long()  -> Dict:  return {"type":"IND_ROW_2_LONG","len_cm":IND_L_CM,"pallets":2}
def ind_single()     -> Dict:  return {"type":"IND_SINGLE","len_cm":IND_L_CM,"pallets":1}

def cap_to_trailer(rows: List[Dict]) -> List[Dict]:
    out, s = [], 0
    for r in rows:
        L = r.get("len_cm", EURO_L_CM)
        if s + L > TRAILER_LEN_CM: break
        out.append(r); s += L
    return out

def layout_for_preset_euro(n: int, singles_front: int = 0) -> List[Dict]:
    rows: List[Dict] = []; remaining = n
    take = min(max(0, singles_front), 2, remaining)
    for _ in range(take): rows.append(euro_row_trans1())
    remaining -= take
    if remaining >= 2 and (remaining - 2) % 3 == 0:
        rows.append(euro_row_trans2()); remaining -= 2
    while remaining % 3 != 0 and any(r["type"]=="EURO_1_TRANS" for r in rows):
        for i, r in enumerate(rows):
            if r["type"]=="EURO_1_TRANS": rows.pop(i); remaining += 1; break
    if remaining > 0: rows += [euro_row_long() for _ in range(remaining//3)]
    if sum(r.get("pallets",0) for r in rows) != n:
        if n>=2 and (n-2)%3==0:
            rows = [euro_row_trans2()] + [euro_row_long() for _ in range((n-2)//3)]
        else:
            rows = [euro_row_long() for _ in range(n//3)]
            rest = n%3
            if rest==2: rows.insert(0, euro_row_trans2())
            elif rest==1: rows.insert(0, euro_row_trans1())
    return rows

def layout_for_preset_industry(n: int) -> List[Dict]:
    if n <= 0: return []
    rows: List[Dict] = []
    if n % 2 == 1: rows.append(ind_single())
    rows += [ind_row2_long() for _ in range(n//2)]
    return rows

# ------------------ Schwer-Block (für Block vorne/hinten) ------------------
def _cat_of_row(r: Dict) -> str:
    t = r.get("type","")
    return "EURO" if t.startswith("EURO_") else ("IND" if t.startswith("IND") else "OTHER")

def reorder_rows_heavy(rows: List[Dict],
                       heavy_euro_count: int,
                       heavy_ind_count: int,
                       side: str = "front",
                       group_by_type: bool = True,
                       type_order: Tuple[str,str] = ("EURO","IND")) -> List[Dict]:
    if heavy_euro_count<=0 and heavy_ind_count<=0: return rows
    idx_iter = range(len(rows)) if side=="front" else reversed(range(len(rows)))
    taken_idx_e, taken_idx_i = [], []; need_e, need_i = heavy_euro_count, heavy_ind_count
    for i in idx_iter:
        if need_e<=0 and need_i<=0: break
        r = rows[i]; cat = _cat_of_row(r)
        if cat=="EURO" and need_e>0: taken_idx_e.append(i); need_e -= r.get("pallets",0)
        elif cat=="IND" and need_i>0: taken_idx_i.append(i); need_i -= r.get("pallets",0)
    taken = set(taken_idx_e + taken_idx_i)
    remaining = [r for j, r in enumerate(rows) if j not in taken]
    block_e = [rows[j] for j in sorted(taken_idx_e)]
    block_i = [rows[j] for j in sorted(taken_idx_i)]
    if group_by_type:
        block = []
        for cat in type_order:
            if cat=="EURO": block += block_e
            elif cat=="IND": block += block_i
    else:
        block = [rows[j] for j in sorted(taken)]
    return (block + remaining) if side=="front" else (remaining + block)

# ------------------ Verteilen (Hecklast) – Markerwahl ohne Umordnung ------------------
def pick_heavy_rows_rear_biased(rows: List[Dict], heavy_total: int) -> Set[int]:
    """
    Wählt Reihen (Indices), deren Paletten summiert ≈ heavy_total ergeben.
    Hecklast (hinten dichter), vermeidet nach Möglichkeit direkte Nachbarn.
    """
    if heavy_total <= 0 or not rows: return set()
    N = len(rows)
    scores = []
    for i, r in enumerate(rows):
        pos = (i+1)/N
        typ = r.get("type","")
        bonus = 0.10 if ("_2_" in typ or "_1_" in typ) else 0.0  # leichte Präferenz für schmalere Reihen
        scores.append((i, pos + bonus, r.get("pallets",0)))
    scores.sort(key=lambda t: t[1], reverse=True)

    picked: Set[int] = set(); total = 0
    def neighbors_bad(k: int) -> bool: return (k-1 in picked) or (k+1 in picked)

    # Runde 1: ohne Nachbarschaft
    for idx, _, pal in scores:
        if total >= heavy_total: break
        if neighbors_bad(idx): continue
        picked.add(idx); total += pal
    # Runde 2: falls noch Bedarf, erlaube Nachbarschaft
    if total < heavy_total:
        for idx, _, pal in scores:
            if total >= heavy_total: break
            if idx in picked: continue
            picked.add(idx); total += pal
    return picked

def count_total_pallets(rows: List[Dict]) -> int:
    return sum(r.get("pallets",0) for r in rows)

# ------------------ Grafik (matplotlib) ------------------
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

COLOR_EURO_LONG = "#d9f2d9"   # hellgrün
COLOR_EURO_QUER = "#cfe8ff"   # hellblau
COLOR_IND      = "#ffe2b3"    # hellorange
EDGE           = "#4a4a4a"

def rows_to_rects_with_row_index(rows: List[Dict]):
    rects = []   # (x,y,w,h,color,cat)
    meta  = []   # {"row_idx": i, "cat": "..."}
    x = 0
    for i, r in enumerate(rows):
        t = r["type"]; L = r["len_cm"]
        if t == "EURO_3_LONG":
            for lane in range(3):
                rects.append((x, lane*80, 120, 80, COLOR_EURO_LONG, "EURO")); meta.append({"row_idx": i, "cat":"EURO"})
            x += L
        elif t == "EURO_2_TRANS":
            for lane in range(2):
                rects.append((x, lane*120, 80, 120, COLOR_EURO_QUER, "EURO")); meta.append({"row_idx": i, "cat":"EURO"})
            x += L
        elif t == "EURO_1_TRANS":
            rects.append((x, 60, 80, 120, COLOR_EURO_QUER, "EURO")); meta.append({"row_idx": i, "cat":"EURO"})
            x += L
        elif t == "IND_ROW_2_LONG":
            for y0 in (20,120):
                rects.append((x, y0, 120, 100, COLOR_IND, "IND")); meta.append({"row_idx": i, "cat":"IND"})
            x += L
        elif t == "IND_SINGLE":
            rects.append((x, 70, 120, 100, COLOR_IND, "IND")); meta.append({"row_idx": i, "cat":"IND"})
            x += L
    return rects, meta

def draw_graph(title: str,
               rows: List[Dict],
               figsize: Tuple[float,float]=(8,1.7),
               weight_mode: bool=False,
               kg_euro: int=0, kg_ind: int=0,
               block_params: Optional[Dict]=None,
               spread_rows: Optional[Set[int]]=None):
    """
    - block_params={"euro":int,"ind":int,"side":"front"/"rear"}  -> Block-Modus markiert von Seite
    - spread_rows=set(idx) -> Verteilmodus markiert diese Reihen
    """
    rows = cap_to_trailer(rows)
    rects, meta = rows_to_rects_with_row_index(rows)

    # Markierung vorbereiten
    heavy_row_set = set()
    euro_cnt = sum(1 for m in meta if m["cat"]=="EURO")
    ind_cnt  = sum(1 for m in meta if m["cat"]=="IND")
    euro_hvy = ind_hvy = 0

    if weight_mode:
        if spread_rows is not None:
            heavy_row_set = spread_rows
        elif block_params is not None:
            # markiere von Seite aus die ersten counts je Typ
            side = block_params.get("side","front")
            need_e = block_params.get("euro",0)
            need_i = block_params.get("ind",0)
            # Reihenindices je Typ
            euro_rows = [i for i,r in enumerate(rows) if _cat_of_row(r)=="EURO"]
            ind_rows  = [i for i,r in enumerate(rows) if _cat_of_row(r)=="IND"]
            src_e = euro_rows if side=="front" else list(reversed(euro_rows))
            src_i = ind_rows  if side=="front" else list(reversed(ind_rows))
            take_e, s= [], 0
            for idx in src_e:
                if s>=need_e: break
                take_e.append(idx); s += rows[idx].get("pallets",0)
            take_i, s= [], 0
            for idx in src_i:
                if s>=need_i: break
                take_i.append(idx); s += rows[idx].get("pallets",0)
            heavy_row_set = set(take_e+take_i)

    # Rechtecke final zusammensetzen
    final_rects = []
    for (x,y,w,h,c,cat), m in zip(rects, meta):
        hv = m["row_idx"] in heavy_row_set
        if hv and cat=="EURO": euro_hvy += 1
        if hv and cat=="IND":  ind_hvy  += 1
        final_rects.append((x,y,w,h,c,cat,hv))

    fig, ax = plt.subplots(figsize=figsize)
    ax.add_patch(Rectangle((0,0), TRAILER_LEN_CM, TRAILER_W_CM, fill=False, linewidth=2, edgecolor="#333"))
    for (x,y,w,h,c,cat,hv) in final_rects:
        edge = "#4a4a4a"; lw = 0.8; face = c
        if weight_mode and hv:
            edge = "#222222"; lw = 1.6
            face = {"#d9f2d9":"#bfe6bf", "#cfe8ff":"#a8d7ff", "#ffe2b3":"#ffd089"}.get(c, c)
        ax.add_patch(Rectangle((x,y), w,h, facecolor=face, edgecolor=edge, linewidth=lw))
    ax.set_xlim(0,TRAILER_LEN_CM); ax.set_ylim(0,TRAILER_W_CM)
    ax.set_aspect('equal'); ax.axis('off'); ax.set_title(title, fontsize=12, pad=6)
    st.pyplot(fig); import matplotlib.pyplot as _plt; _plt.close(fig)

    if weight_mode and (kg_euro or kg_ind):
        total_rect = euro_cnt*kg_euro + ind_cnt*kg_ind
        heavy_rect = euro_hvy*kg_euro + ind_hvy*kg_ind
        st.caption(f"Gewicht: gesamt ≈ **{total_rect:.0f} kg**, markiert ≈ **{heavy_rect:.0f} kg** "
                   f"(Euro: {euro_cnt}×{kg_euro}, Ind.: {ind_cnt}×{kg_ind})")

# ------------------ Sidebar ------------------
st.title("🦊 Paletten Fuchs – Grafik & Gewicht")
INLINE_GRID_ON = st.sidebar.toggle("Vier Varianten (2×2) direkt oben", value=False)
SHOW_TABS      = st.sidebar.toggle("Vergleich (Tabs) anzeigen", value=True)

# ------------------ Clean ------------------
st.subheader("Clean-Ansicht (Grafik) – Euro + Industrie")
c1, c2, c3 = st.columns(3)
with c1: euro_n = st.number_input("Euro-Paletten", 0, 40, 33, step=1)
with c2: singles_front = st.slider("Einzel-quer vorne (0/1/2)", 0, 2, 0)
with c3: ind_n = st.number_input("Industrie-Paletten", 0, 40, 0, step=1)

with st.expander("Gewicht & Modus (optional)", expanded=False):
    kg_col1, kg_col2 = st.columns(2)
    with kg_col1: kg_euro = st.number_input("kg/Euro", 0, 2000, 700, step=10)
    with kg_col2: kg_ind  = st.number_input("kg/Industrie", 0, 2500, 900, step=10)
    mode = st.radio("Gewichtsmodus", ["Aus", "Block vorne", "Block hinten", "Verteilen (Hecklast)"],
                    index=0, horizontal=True)
    weight_mode = (mode != "Aus")
    heavy_total = st.number_input("Gesamtanzahl schwere Paletten", 0, 100, 20, step=1,
                                  help="Gilt für Euro + Industrie zusammen (frei wählbar).")
    # Für Block-Modus brauchen wir grob eine Splittung nach Typ (abschätzen proportional)
    split_info = st.checkbox("Block-Modus: Typverhältnis aus aktueller Ladung übernehmen", value=True,
                             help="Schätzt im Block-Modus die schweren Euro/Industrie anteilig der aktuellen Ladung.")

# Reihen bauen (ohne Umordnung)
rows_clean: List[Dict] = []
if euro_n > 0: rows_clean += layout_for_preset_euro(euro_n, singles_front=singles_front)
if ind_n  > 0: rows_clean += layout_for_preset_industry(ind_n)

# Heavy-Markierung/Block bestimmen
block_params = None
spread_rows: Optional[Set[int]] = None
if weight_mode and heavy_total>0:
    total_pal = count_total_pallets(rows_clean)
    if mode == "Verteilen (Hecklast)":
        # ALLE schwer? -> alles markieren (ohne Umordnung). Für echte Umverteilung könnten wir später Reihenumsortierung ergänzen.
        if heavy_total >= total_pal:
            spread_rows = set(range(len(rows_clean)))
        else:
            spread_rows = pick_heavy_rows_rear_biased(rows_clean, heavy_total)
    else:
        # Block vorne/hinten: schweren Block bilden – je Typ anteilig der Ladung
        euro_total = sum(r.get("pallets",0) for r in rows_clean if _cat_of_row(r)=="EURO")
        ind_total  = sum(r.get("pallets",0) for r in rows_clean if _cat_of_row(r)=="IND")
        if split_info and (euro_total+ind_total)>0:
            heavy_e = round(heavy_total * (euro_total/(euro_total+ind_total)))
            heavy_i = max(0, heavy_total - heavy_e)
        else:
            # fallback: alles als Euro rechnen
            heavy_e, heavy_i = heavy_total, 0
        side = "front" if mode=="Block vorne" else "rear"
        rows_clean = reorder_rows_heavy(rows_clean, heavy_e, heavy_i, side=side, group_by_type=True, type_order=("EURO","IND"))
        block_params = {"euro":heavy_e, "ind":heavy_i, "side":side}

draw_graph(
    f"Clean: {euro_n} Euro (S{singles_front}) + {ind_n} Industrie",
    rows_clean,
    figsize=(8,1.7),
    weight_mode=weight_mode,
    kg_euro=kg_euro if weight_mode else 0,
    kg_ind=kg_ind if weight_mode else 0,
    block_params=block_params,
    spread_rows=spread_rows
)

# ------------------ Inline 2×2 ------------------
def inline_four_variants_grid():
    st.markdown("#### Vier Varianten (2×2, kompakt)")

    def controls(idx: int):
        cc1, cc2, cc3 = st.columns(3)
        with cc1: e = st.number_input(f"Euro V{idx}", 0, 40, 33 if idx==1 else 0, step=1, key=f"iv_e{idx}")
        with cc2: s = st.slider(f"Einzel V{idx}", 0, 2, 0, key=f"iv_s{idx}")
        with cc3: i = st.number_input(f"Industrie V{idx}", 0, 40, 0, step=1, key=f"iv_i{idx}")

        with st.expander(f"Gewicht & Modus V{idx} (optional)", expanded=False):
            wm = st.checkbox(f"Aktiv V{idx}", value=False, key=f"iv_wm{idx}")
            kge = st.number_input(f"kg Euro V{idx}", 0, 2000, 700, step=10, key=f"iv_kge{idx}")
            kgi = st.number_input(f"kg Ind V{idx}", 0, 2500, 900, step=10, key=f"iv_kgi{idx}")
            mode_v = st.radio(f"Modus V{idx}", ["Block vorne","Block hinten","Verteilen (Hecklast)"],
                              index=2, horizontal=True, key=f"iv_mode{idx}")
            ht = st.number_input(f"Gesamt schwer V{idx}", 0, 100, 20, step=1, key=f"iv_ht{idx}")
            spl = st.checkbox("Block: Typverhältnis übernehmen", value=True, key=f"iv_spl{idx}")
        return e, s, i, wm, kge, kgi, mode_v, ht, spl

    def build_and_draw(idx: int, params):
        e, s, i, wm, kge, kgi, mode_v, ht, spl = params
        r: List[Dict] = []
        if e>0: r += layout_for_preset_euro(e, singles_front=s)
        if i>0: r += layout_for_preset_industry(i)
        bp=None; sp=None
        if wm and ht>0:
            if mode_v=="Verteilen (Hecklast)":
                tot = count_total_pallets(r)
                if ht >= tot: sp = set(range(len(r)))
                else:         sp = pick_heavy_rows_rear_biased(r, ht)
            else:
                euro_tot = sum(x.get("pallets",0) for x in r if _cat_of_row(x)=="EURO")
                ind_tot  = sum(x.get("pallets",0) for x in r if _cat_of_row(x)=="IND")
                if spl and (euro_tot+ind_tot)>0:
                    he = round(ht * (euro_tot/(euro_tot+ind_tot))); hi = max(0, ht-he)
                else:
                    he, hi = ht, 0
                side = "front" if mode_v=="Block vorne" else "rear"
                r = reorder_rows_heavy(r, he, hi, side=side, group_by_type=True, type_order=("EURO","IND"))
                bp = {"euro":he,"ind":hi,"side":side}
        draw_graph(f"V{idx}", r, figsize=(6.6,1.25), weight_mode=wm, kg_euro=kge, kg_ind=kgi,
                   block_params=bp, spread_rows=sp)

    p1 = controls(1); p2 = controls(2); p3 = controls(3); p4 = controls(4)
    row1 = st.columns(2, gap="small"); row2 = st.columns(2, gap="small")
    with row1[0]: build_and_draw(1, p1)
    with row1[1]: build_and_draw(2, p2)
    with row2[0]: build_and_draw(3, p3)
    with row2[1]: build_and_draw(4, p4)

if INLINE_GRID_ON:
    inline_four_variants_grid()

# ------------------ Tabs ------------------
def compare_tabs_four_variants():
    st.subheader("Vergleich (Tabs) – 4 Varianten")
    tab1, tab2, tab3, tab4 = st.tabs(["Variante 1","Variante 2","Variante 3","Variante 4"])

    def tab_ui(tab, idx: int, defaults=(33,0,0)):
        with tab:
            e = st.number_input(f"Euro (V{idx})", 0, 40, defaults[0], step=1, key=f"tv_e{idx}")
            s = st.slider(f"Einzel (V{idx})", 0, 2, defaults[1], key=f"tv_s{idx}")
            i = st.number_input(f"Industrie (V{idx})", 0, 40, defaults[2], step=1, key=f"tv_i{idx}")
            with st.expander(f"Gewicht & Modus V{idx} (optional)", expanded=False):
                wm  = st.checkbox(f"Aktiv V{
