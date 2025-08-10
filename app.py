# app.py
# Paletten Fuchs – Clean + große Grafik + Gewichtsmodus (mit korrekter FRONT/REAR-Platzierung)
# + Inline 2×2 Vergleich (Toggle) + Tabs-Vergleich (Toggle)
# - Große Draufsicht (matplotlib), keine Unicode-Zeilen
# - Gewichtsmodus: kg/Palette, "schwere" markieren, Reihen mit schweren Paletten nach vorne/hinten platzieren

from typing import List, Dict, Optional, Tuple
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

# ----- Euro-Layout mit Gewichts-PLATZIERUNG (front/rear korrekt) -----
def layout_for_preset_euro(
    n: int,
    singles_front: int = 0,
    heavy_count: int = 0,
    heavy_pos: Optional[str] = None  # "front" | "rear" | None
) -> List[Dict]:
    rows: List[Dict] = []
    remaining = n

    # 1) Einzel-quer vorne (0/1/2)
    take = min(max(0, singles_front), 2, remaining)
    for _ in range(take):
        rows.append(euro_row_trans1())
    remaining -= take

    # 2) Eine 2-quer-Reihe, wenn (rest-2)%3==0
    if remaining >= 2 and (remaining - 2) % 3 == 0:
        rows.append(euro_row_trans2())
        remaining -= 2

    # 3) Rest ggf. Singles zurücknehmen, bis durch 3 teilbar
    while remaining % 3 != 0 and any(r["type"] == "EURO_1_TRANS" for r in rows):
        for i, r in enumerate(rows):
            if r["type"] == "EURO_1_TRANS":
                rows.pop(i)
                remaining += 1
                break

    # 4) Mit 3-längs auffüllen
    if remaining > 0:
        rows += [euro_row_long() for _ in range(remaining // 3)]

    # 5) Absicherung
    if sum(r.get("pallets", 0) for r in rows) != n:
        if n >= 2 and (n - 2) % 3 == 0:
            rows = [euro_row_trans2()] + [euro_row_long() for _ in range((n - 2) // 3)]
        else:
            rows = [euro_row_long() for _ in range(n // 3)]
            rest = n % 3
            if rest == 2:
                rows.insert(0, euro_row_trans2())
            elif rest == 1:
                rows.insert(0, euro_row_trans1())

    # 6) Gewichts-Optimierung: ganze Reihen verschieben (korrekt von vorn ODER hinten zählen)
    if heavy_pos in ("front", "rear") and heavy_count > 0:
        if heavy_pos == "front":
            moved, normal, cnt = [], [], 0
            for r in rows:
                if cnt < heavy_count:
                    moved.append(r); cnt += r["pallets"]
                else:
                    normal.append(r)
            rows = moved + normal
        else:  # rear -> von HINTEN zählen
            moved, normal, cnt = [], [], 0
            for r in reversed(rows):
                if cnt < heavy_count:
                    moved.append(r); cnt += r["pallets"]
                else:
                    normal.append(r)
            moved.reverse()
            normal.reverse()
            rows = normal + moved

    return rows

# ----- Industrie-Layout mit Gewichts-PLATZIERUNG (front/rear korrekt) -----
def layout_for_preset_industry(
    n: int,
    heavy_count: int = 0,
    heavy_pos: Optional[str] = None
) -> List[Dict]:
    if n <= 0:
        return []
    rows: List[Dict] = []
    single = n % 2
    full   = n // 2

    if single:
        rows.append(ind_single())  # 1 vorne
    rows += [ind_row2_long() for _ in range(full)]

    if heavy_pos in ("front", "rear") and heavy_count > 0:
        if heavy_pos == "front":
            moved, normal, cnt = [], [], 0
            for r in rows:
                if cnt < heavy_count:
                    moved.append(r); cnt += r["pallets"]
                else:
                    normal.append(r)
            rows = moved + normal
        else:  # rear -> von HINTEN zählen
            moved, normal, cnt = [], [], 0
            for r in reversed(rows):
                if cnt < heavy_count:
                    moved.append(r); cnt += r["pallets"]
                else:
                    normal.append(r)
            moved.reverse()
            normal.reverse()
            rows = normal + moved

    return rows

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
        t = r["type"]
        L = r["len_cm"]
        if t == "EURO_3_LONG":
            w, h = 120, 80
            for lane in range(3):
                rects.append((x, lane*80, w, h, COLOR_EURO_LONG, "EURO", False))
            x += L
        elif t == "EURO_2_TRANS":
            w, h = 80, 120
            for lane in range(2):
                rects.append((x, lane*120, w, h, COLOR_EURO_QUER, "EURO", False))
            x += L
        elif t == "EURO_1_TRANS":
            w, h = 80, 120
            rects.append((x, 60, w, h, COLOR_EURO_QUER, "EURO", False))
            x += L
        elif t == "IND_ROW_2_LONG":
            w, h = 120, 100
            rects.append((x, 20,  w, h, COLOR_IND, "IND", False))
            rects.append((x, 120, w, h, COLOR_IND, "IND", False))
            x += L
        elif t == "IND_SINGLE":
            w, h = 120, 100
            rects.append((x, 70, w, h, COLOR_IND, "IND", False))
            x += L
    return rects

def rows_to_rects_with_weights(
    rows: List[Dict],
    heavy_euro_count: int = 0, heavy_euro_side: str = "front",
    heavy_ind_count: int = 0,  heavy_ind_side: str  = "front",
) -> Tuple[List[Tuple[float,float,float,float,str,str,bool]], int, int, int, int]:
    """
    Markiert 'heavy_*_count' Paletten je Typ von 'front' ODER 'rear'.
    Rückgabe: (rects, euro_cnt, ind_cnt, euro_hvy, ind_hvy)
    """
    rects = []
    x = 0
    euro_rects = []
    ind_rects  = []

    for r in cap_to_trailer(rows):
        t = r["type"]; L = r["len_cm"]
        if t == "EURO_3_LONG":
            w, h = 120, 80
            for lane in range(3):
                rects.append((x, lane*80, w, h, COLOR_EURO_LONG, "EURO", False))
                euro_rects.append(len(rects)-1)
            x += L
        elif t == "EURO_2_TRANS":
            w, h = 80, 120
            for lane in range(2):
                rects.append((x, lane*120, w, h, COLOR_EURO_QUER, "EURO", False))
                euro_rects.append(len(rects)-1)
            x += L
        elif t == "EURO_1_TRANS":
            w, h = 80, 120
            rects.append((x, 60, w, h, COLOR_EURO_QUER, "EURO", False))
            euro_rects.append(len(rects)-1)
            x += L
        elif t == "IND_ROW_2_LONG":
            w, h = 120, 100
            for y0 in (20, 120):
                rects.append((x, y0, w, h, COLOR_IND, "IND", False))
                ind_rects.append(len(rects)-1)
            x += L
        elif t == "IND_SINGLE":
            w, h = 120, 100
            rects.append((x, 70, w, h, COLOR_IND, "IND", False))
            ind_rects.append(len(rects)-1)
            x += L

    # Euro markieren (front oder rear)
    euro_cnt = len(euro_rects)
    if heavy_euro_count > 0 and euro_cnt > 0:
        if heavy_euro_side == "rear":
            indices = list(reversed(euro_rects))[:heavy_euro_count]
        else:
            indices = euro_rects[:heavy_euro_count]
        for idx in indices:
            x0,y0,w0,h0,c0,cat0,_ = rects[idx]
            rects[idx] = (x0,y0,w0,h0,c0,cat0,True)
    euro_hvy = sum(1 for i in euro_rects if rects[i][6] is True)

    # Industrie markieren (front oder rear)
    ind_cnt = len(ind_rects)
    if heavy_ind_count > 0 and ind_cnt > 0:
        if heavy_ind_side == "rear":
            indices = list(reversed(ind_rects))[:heavy_ind_count]
        else:
            indices = ind_rects[:heavy_ind_count]
        for idx in indices:
            x0,y0,w0,h0,c0,cat0,_ = rects[idx]
            rects[idx] = (x0,y0,w0,h0,c0,cat0,True)
    ind_hvy = sum(1 for i in ind_rects if rects[i][6] is True)

    return rects, euro_cnt, ind_cnt, euro_hvy, ind_hvy

def draw_graph(
    title: str,
    rows: List[Dict],
    figsize: Tuple[float,float] = (8, 1.7),
    weight_mode: bool = False,
    kg_euro: int = 0,
    kg_ind: int = 0,
    heavy_euro_count: int = 0,
    heavy_ind_count: int = 0,
    heavy_side: str = "front"   # "front" | "rear"
):
    """Grafische Draufsicht; bei weight_mode=True werden schwere von 'heavy_side' markiert & Summen angezeigt."""
    if weight_mode:
        rects, euro_cnt, ind_cnt, euro_hvy, ind_hvy = rows_to_rects_with_weights(
            rows,
            heavy_euro_count=heavy_euro_count, heavy_euro_side=heavy_side,
            heavy_ind_count=heavy_ind_count,   heavy_ind_side=heavy_side
        )
    else:
        base = rows_to_rects(cap_to_trailer(rows))
        rects = base
        euro_cnt = sum(1 for *_, cat, _ in rects if cat == "EURO")
        ind_cnt  = sum(1 for *_, cat, _ in rects if cat == "IND")
        euro_hvy = ind_hvy = 0

    fig, ax = plt.subplots(figsize=figsize)

    # Trailer-Rahmen
    ax.add_patch(Rectangle((0, 0), TRAILER_LEN_CM, TRAILER_W_CM,
                           fill=False, linewidth=2, edgecolor="#333"))

    # Paletten zeichnen
    for (x, y, w, h, c, cat, hvy) in rects:
        face = c
        edge = EDGE
        lw = 0.8
        if weight_mode and hvy:
            edge = "#222222"; lw = 1.6
            face = {"#d9f2d9":"#bfe6bf", "#cfe8ff":"#a8d7ff", "#ffe2b3":"#ffd089"}.get(c, c)
        ax.add_patch(Rectangle((x, y), w, h, facecolor=face, edgecolor=edge, linewidth=lw))

    ax.set_xlim(0, TRAILER_LEN_CM)
    ax.set_ylim(0, TRAILER_W_CM)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=12, pad=6)
    st.pyplot(fig)
    import matplotlib.pyplot as _plt; _plt.close(fig)

    if weight_mode and (kg_euro or kg_ind):
        total = euro_cnt * kg_euro + ind_cnt * kg_ind
        front = euro_hvy * kg_euro + ind_hvy * kg_ind
        st.caption(
            f"Gewicht: gesamt ≈ **{total:.0f} kg**, {'vorne' if heavy_side=='front' else 'hinten'} (markiert) ≈ **{front:.0f} kg**  "
            f"(Euro: {euro_cnt}×{kg_euro} kg, Ind.: {ind_cnt}×{kg_ind} kg)"
        )

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

# Gewichts-Expander (optional, inkl. Platzierung)
with st.expander("Gewicht & Platzierung (optional)", expanded=False):
    weight_mode = st.checkbox("Gewichtsmodus aktivieren", value=False)
    colw1, colw2, colw3 = st.columns(3)
    with colw1:
        kg_euro = st.number_input("kg/Euro", 0, 2000, 700, step=10)
    with colw2:
        kg_ind  = st.number_input("kg/Industrie", 0, 2500, 900, step=10)
    with colw3:
        pos_choice = st.radio("Schwere markieren/platzieren ab", ["Vorne","Hinten"], index=0, horizontal=True)
    heavy_side = "front" if pos_choice == "Vorne" else "rear"

    colh1, colh2 = st.columns(2)
    with colh1:
        hvy_e = st.number_input("Schwere Euro (Stk.)", 0, 200, 0, step=1)
    with colh2:
        hvy_i = st.number_input("Schwere Industrie (Stk.)", 0, 200, 0, step=1)

# Reihen AUFBAU (mit optionaler PLATZIERUNG der „schweren“ Reihen)
heavy_pos_for_build = heavy_side if (hvy_e or hvy_i) else None  # nur wenn Stückzahl > 0
rows_clean: List[Dict] = []
if euro_n > 0:
    rows_clean += layout_for_preset_euro(
        euro_n,
        singles_front=singles_front,
        heavy_count=hvy_e,
        heavy_pos=heavy_pos_for_build
    )
if ind_n > 0:
    rows_clean += layout_for_preset_industry(
        ind_n,
        heavy_count=hvy_i,
        heavy_pos=heavy_pos_for_build
    )

draw_graph(
    f"Clean: {euro_n} Euro (S{singles_front}) + {ind_n} Industrie",
    rows_clean,
    figsize=(8, 1.7),
    weight_mode=weight_mode,
    kg_euro=kg_euro if weight_mode else 0,
    kg_ind=kg_ind if weight_mode else 0,
    heavy_euro_count=hvy_e if weight_mode else 0,
    heavy_ind_count=hvy_i if weight_mode else 0,
    heavy_side=heavy_side
)

# ------------------ Inline 2×2 Vergleich (per Toggle) ------------------
def inline_four_variants_grid():
    st.markdown("#### Vier Varianten (2×2, kompakt)")

    def controls(idx: int):
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            e = st.number_input(f"Euro V{idx}", 0, 40, 0 if idx>1 else 33, step=1, key=f"iv_e{idx}")
        with cc2:
            s = st.slider(f"Einzel V{idx}", 0, 2, 0, key=f"iv_s{idx}")
        with cc3:
            i = st.number_input(f"Industrie V{idx}", 0, 40, 0, step=1, key=f"iv_i{idx}")

        with st.expander(f"Gewicht & Platzierung V{idx} (optional)", expanded=False):
            wm = st.checkbox(f"Aktiv V{idx}", value=False, key=f"iv_wm{idx}")
            cA, cB, cC, cD, cE = st.columns([1,1,1,1,1.2])
            with cA:
                kge = st.number_input(f"kg Euro V{idx}", 0, 2000, 700, step=10, key=f"iv_kge{idx}")
            with cB:
                kgi = st.number_input(f"kg Ind V{idx}", 0, 2500, 900, step=10, key=f"iv_kgi{idx}")
            with cC:
                he  = st.number_input(f"schwere Euro V{idx}", 0, 200, 0, step=1, key=f"iv_he{idx}")
            with cD:
                hi  = st.number_input(f"schwere Ind V{idx}", 0, 200, 0, step=1, key=f"iv_hi{idx}")
            with cE:
                pos = st.radio(f"Seite V{idx}", ["Vorne","Hinten"], index=0, horizontal=True, key=f"iv_pos{idx}")
        heavy_side_v = "front" if pos == "Vorne" else "rear"

        # Reihen bauen (mit evtl. Platzierung)
        heavy_pos_build_v = heavy_side_v if (he or hi) else None
        r: List[Dict] = []
        if e > 0:
            r += layout_for_preset_euro(e, singles_front=s,
                                        heavy_count=he, heavy_pos=heavy_pos_build_v)
        if i > 0:
            r += layout_for_preset_industry(i,
                                            heavy_count=hi, heavy_pos=heavy_pos_build_v)
        title = f"V{idx}: {e} Euro (S{s}) + {i} Ind."
        return r, title, wm, kge, kgi, he, hi, heavy_side_v

    r1,t1,w1,kge1,kgi1,he1,hi1,side1 = controls(1)
    r2,t2,w2,kge2,kgi2,he2,hi2,side2 = controls(2)
    r3,t3,w3,kge3,kgi3,he3,hi3,side3 = controls(3)
    r4,t4,w4,kge4,kgi4,he4,hi4,side4 = controls(4)

    figsz = (6.6, 1.25)
    row1 = st.columns(2, gap="small")
    with row1[0]:
        draw_graph(t1, r1, figsize=figsz, weight_mode=w1, kg_euro=kge1, kg_ind=kgi1,
                   heavy_euro_count=he1, heavy_ind_count=hi1, heavy_side=side1)
    with row1[1]:
        draw_graph(t2, r2, figsize=figsz, weight_mode=w2, kg_euro=kge2, kg_ind=kgi2,
                   heavy_euro_count=he2, heavy_ind_count=hi2, heavy_side=side2)

    row2 = st.columns(2, gap="small")
    with row2[0]:
        draw_graph(t3, r3, figsize=figsz, weight_mode=w3, kg_euro=kge3, kg_ind=kgi3,
                   heavy_euro_count=he3, heavy_ind_count=hi3, heavy_side=side3)
    with row2[1]:
        draw_graph(t4, r4, figsize=figsz, weight_mode=w4, kg_euro=kge4, kg_ind=kgi4,
                   heavy_euro_count=he4, heavy_ind_count=hi4, heavy_side=side4)

if INLINE_GRID_ON:
    inline_four_variants_grid()

# ------------------ Vergleich (Tabs) – 4 Varianten frei ------------------
def compare_tabs_four_variants():
    st.subheader("Vergleich (Tabs) – 4 Varianten (frei konfigurierbar)")

    tab1, tab2, tab3, tab4 = st.tabs(["Variante 1", "Variante 2", "Variante 3", "Variante 4"])

    def var_ui(tab, idx: int, defaults=(33,0,0)):
        with tab:
            e = st.number_input(f"Euro (V{idx})", 0, 40, defaults[0], step=1, key=f"tv_e{idx}")
            s = st.slider(f"Einzel (V{idx})", 0, 2, defaults[1], key=f"tv_s{idx}")
            i = st.number_input(f"Industrie (V{idx})", 0, 40, defaults[2], step=1, key=f"tv_i{idx}")

            with st.expander(f"Gewicht & Platzierung V{idx} (optional)", expanded=False):
                wm = st.checkbox(f"Aktiv V{idx}", value=False, key=f"tv_wm{idx}")
                cA, cB, cC, cD, cE = st.columns([1,1,1,1,1.2])
                with cA:
                    kge = st.number_input(f"kg Euro V{idx}", 0, 2000, 700, step=10, key=f"tv_kge{idx}")
                with cB:
                    kgi = st.number_input(f"kg Ind V{idx}", 0, 2500, 900, step=10, key=f"tv_kgi{idx}")
                with cC:
                    he  = st.number_input(f"schwere Euro V{idx}", 0, 200, 0, step=1, key=f"tv_he{idx}")
                with cD:
                    hi  = st.number_input(f"schwere Ind V{idx}", 0, 200, 0, step=1, key=f"tv_hi{idx}")
                with cE:
                    pos = st.radio(f"Seite V{idx}", ["Vorne","Hinten"], index=0, horizontal=True, key=f"tv_pos{idx}")
            side = "front" if pos == "Vorne" else "rear"

            heavy_pos_build = side if (he or hi) else None
            r: List[Dict] = []
            if e > 0:
                r += layout_for_preset_euro(e, singles_front=s,
                                            heavy_count=he, heavy_pos=heavy_pos_build)
            if i > 0:
                r += layout_for_preset_industry(i,
                                                heavy_count=hi, heavy_pos=heavy_pos_build)

            draw_graph(f"V{idx}: {e} Euro (S{s}) + {i} Ind.", r,
                       weight_mode=wm, kg_euro=kge, kg_ind=kgi,
                       heavy_euro_count=he, heavy_ind_count=hi, heavy_side=side)

    var_ui(tab1, 1, (33, 0, 0))
    var_ui(tab2, 2, (32, 2, 0))
    var_ui(tab3, 3, (31, 1, 0))
    var_ui(tab4, 4, (24, 0, 0))

if SHOW_TABS:
    compare_tabs_four_variants()

st.caption("Gewichtsmodus: markiert schwere Paletten und ordnet deren REIHEN auf Wunsch vorne/hinten an. "
           "Grafik im Maßstab 1360×240 cm. Farben: Grün=Euro längs, Blau=Euro quer, Orange=Industrie.")
