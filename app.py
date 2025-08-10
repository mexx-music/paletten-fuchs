# pal_fuchs_app_clean.py
# 🦊 Pal Fuchs – Varianten & Gewichtsmodus (bereinigt, Keys ergänzt, farbliche Orientierung)
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Tuple, Dict
import streamlit as st

# ---------- Basis ----------
TRAILER_L = 1360  # cm
TRAILER_W = 245   # cm

st.set_page_config(page_title="🦊 Pal Fuchs – Varianten & Achslast", layout="wide")
st.title("🦊 Pal Fuchs – Varianten & Gewichtsmodus")

# ---------- Sidebar: Anzeige & Fahrzeug ----------
with st.sidebar:
    st.markdown("### ⚙️ Anzeige")
    cell_cm = st.slider("Raster (cm/Zelle)", 20, 50, 40, 5, key="cfg_cell_cm")
    auto_zoom = st.checkbox("Auto‑Zoom auf konstante Breite", False, key="cfg_auto_zoom")
    cell_px = st.slider("Zell‑Pixel", 4, 20, 6, 1, disabled=auto_zoom, key="cfg_cell_px")
    st.markdown("---")
    st.markdown("### 🚛 Kühlsattel / Puffer")
    use_buffers = st.checkbox("Puffer aktivieren (dicke Türen / Aggregat)", False, key="cfg_buffers")
    front_buf = st.number_input("Front‑Puffer (cm)", 0, 120, 0, 5, disabled=not use_buffers, key="cfg_front_buf")
    rear_buf = st.number_input("Heck‑Puffer (cm)", 0, 120, 0, 5, disabled=not use_buffers, key="cfg_rear_buf")
    st.caption("Hinweis: Front‑Puffer ist praktisch nur relevant, wenn Paletten hoch genug fürs Aggregat sind.")

# Effektive Länge & Grid
L_EFF = max(0, TRAILER_L - (front_buf if use_buffers else 0) - (rear_buf if use_buffers else 0))
X = max(1, math.floor(TRAILER_L / cell_cm))  # volle Trailerlänge, für optische Puffer
Y = max(1, math.ceil(TRAILER_W / cell_cm))

# Auto‑Zoom (optional)
if auto_zoom:
    cell_px = max(4, min(20, round(820 / X)))

x_offset_cells = math.ceil((front_buf if use_buffers else 0) / cell_cm)  # optischer Offset links

# ---------- Datenmodelle ----------
@dataclass
class PalType:
    name: str
    depth_l: int     # cm, entlang Länge (längs)
    width_l: int     # cm, quer (längs)
    depth_q: int     # cm, entlang Länge (quer)
    width_q: int     # cm, quer (quer)
    default_weight: int  # kg

EURO = PalType("Euro", depth_l=120, width_l=80, depth_q=80, width_q=120, default_weight=250)
IND  = PalType("Industrie/IBC", depth_l=120, width_l=100, depth_q=100, width_q=120, default_weight=1100)

# ---------- Board / Platzierung ----------
def span_to_cells(depth_cm: int, width_cm: int) -> Tuple[int, int]:
    dx = max(1, math.ceil(depth_cm / cell_cm))  # entlang Länge
    dy = max(1, math.ceil(width_cm / cell_cm))  # quer
    return dx, dy

def center_y(dy: int) -> int:
    return max(0, (Y - dy) // 2)

def empty_board():
    occ = [[False] * X for _ in range(Y)]
    # items: (x, y, dx, dy, typ, depth_cm, weight_kg)
    items: List[Tuple[int, int, int, int, str, int, int]] = []
    placed: Dict[str, int] = {"Euro": 0, "Industrie/IBC": 0}
    return occ, items, placed

def free(occ, x: int, y: int, dx: int, dy: int) -> bool:
    if x < 0 or y < 0 or x + dx > X or y + dy > Y:
        return False
    for yy in range(y, y + dy):
        for xx in range(x, x + dx):
            if occ[yy][xx]:
                return False
    return True

def place(occ, items, placed, x: int, y: int, dx: int, dy: int,
          typ_name: str, depth_cm: int, weight_kg: int) -> None:
    for yy in range(y, y + dy):
        for xx in range(x, x + dx):
            occ[yy][xx] = True
    items.append((x, y, dx, dy, typ_name, depth_cm, weight_kg))
    placed[typ_name] = placed.get(typ_name, 0) + 1

def used_length_cm_real(items) -> int:
    if not items:
        return 0
    rightmost = 0
    for (x, _y, _dx, _dy, _typ, depth_cm, _w) in items:
        rightmost = max(rightmost, x * cell_cm + depth_cm)
    return min((front_buf if use_buffers else 0) + rightmost, TRAILER_L)

# ---------- Hilfs‑Platzierer ----------
def place_euro_col_l(occ, items, placed, x: int, want: int, weight: int = EURO.default_weight) -> Tuple[int, int]:
    dx, dy = span_to_cells(EURO.depth_l, EURO.width_l)
    placed_now = 0
    for y in (0, center_y(dy), Y - dy):
        if placed_now >= want:
            break
        if free(occ, x, y, dx, dy):
            place(occ, items, placed, x, y, dx, dy, "Euro", EURO.depth_l, weight)
            placed_now += 1
    return placed_now, x + dx

def place_euro_row_q(occ, items, placed, x: int, want: int, weight: int = EURO.default_weight) -> Tuple[int, int]:
    dx, dy = span_to_cells(EURO.depth_q, EURO.width_q)
    placed_now = 0
    for y in (0, Y - dy):
        if placed_now >= want:
            break
        if free(occ, x, y, dx, dy):
            place(occ, items, placed, x, y, dx, dy, "Euro", EURO.depth_q, weight)
            placed_now += 1
    return placed_now, x + dx

def place_ind_row_q(occ, items, placed, x: int, want: int, heavy: bool) -> Tuple[int, int]:
    dx, dy = span_to_cells(IND.depth_q, IND.width_q)
    w = IND.default_weight if heavy else max(600, IND.default_weight // 2)
    placed_now = 0
    for y in (0, Y - dy):
        if placed_now >= want:
            break
        if free(occ, x, y, dx, dy):
            place(occ, items, placed, x, y, dx, dy, "Industrie/IBC", IND.depth_q, w)
            placed_now += 1
    return placed_now, x + dx

def place_ind_mid_then_edges(occ, items, placed, x: int, count: int, heavy: bool) -> int:
    dx, dy = span_to_cells(IND.depth_q, IND.width_q)
    w = IND.default_weight if heavy else max(600, IND.default_weight // 2)
    x_start = x + (1 if heavy and (x + 1 + dx <= X) else 0)
    # ungerade → 1 mittig
    if count % 2 == 1 and free(occ, x_start, center_y(dy), dx, dy):
        place(occ, items, placed, x_start, center_y(dy), dx, dy, "Industrie/IBC", IND.depth_q, w)
        count -= 1
        x_start += dx
    while count > 0 and x_start + dx <= X:
        for y in (0, Y - dy):
            if count <= 0:
                break
            if free(occ, x_start, y, dx, dy):
                place(occ, items, placed, x_start, y, dx, dy, "Industrie/IBC", IND.depth_q, w)
                count -= 1
        x_start += dx
    return x_start

# ---------- Reale Varianten‑Logik (Euro) ----------
def euro_variant_q_then_l(occ, items, placed, x_start: int, n: int) -> None:
    max_q = L_EFF // EURO.depth_q
    best = None
    for q_rows in range(min(n // 2, max_q), -1, -1):
        used_q = 2 * q_rows
        rem = n - used_q
        len_left = L_EFF - q_rows * EURO.depth_q
        need_l = math.ceil(rem / 3) if rem > 0 else 0
        if need_l * EURO.depth_l <= len_left:
            best = (q_rows, need_l)
            break
    if best is None:
        best = (0, math.ceil(n / 3))
    q_rows, l_cols = best
    x = x_start
    done = 0
    for _ in range(q_rows):
        want = min(2, n - done)
        got, x = place_euro_row_q(occ, items, placed, x, want)
        done += got
    for _ in range(l_cols):
        if done >= n:
            break
        want = min(3, n - done)
        got, nx = place_euro_col_l(occ, items, placed, x, want)
        done += got
        x = nx
    if done < n:
        want = min(2, n - done)
        place_euro_row_q(occ, items, placed, x, want)

def euro_variant_l_then_q(occ, items, placed, x_start: int, n: int) -> None:
    max_l = L_EFF // EURO.depth_l
    best = None
    for l_cols in range(min(math.ceil(n / 3), max_l), -1, -1):
        used_l = 3 * l_cols
        rem = n - used_l
        len_left = L_EFF - l_cols * EURO.depth_l
        need_q = math.ceil(rem / 2) if rem > 0 else 0
        if need_q * EURO.depth_q <= len_left:
            best = (l_cols, need_q)
            break
    if best is None:
        best = (0, math.ceil(n / 2))
    l_cols, q_rows = best
    x = x_start
    done = 0
    for _ in range(l_cols):
        want = min(3, n - done)
        got, nx = place_euro_col_l(occ, items, placed, x, want)
        done += got
        x = nx
        if done >= n:
            break
    for _ in range(q_rows):
        if done >= n:
            break
        want = min(2, n - done)
        got, x = place_euro_row_q(occ, items, placed, x, want)
        done += got

def euro_variant_all_l(occ, items, placed, x_start: int, n: int) -> None:
    x = x_start
    left = n
    while left > 0 and (x - x_start) * cell_cm < L_EFF + 1:
        want = min(3, left)
        got, nx = place_euro_col_l(occ, items, placed, x, want)
        if got == 0:
            break
        left -= got
        x = nx

def euro_variant_all_q_with_tail(occ, items, placed, x_start: int, n: int) -> None:
    x = x_start
    left = n
    full_q = min(L_EFF // EURO.depth_q, math.ceil(n / 2))
    for _ in range(full_q):
        if left <= 0:
            break
        want = min(2, left)
        got, x = place_euro_row_q(occ, items, placed, x, want)
        left -= got
    while left > 0:
        want = min(3, left)
        got, nx = place_euro_col_l(occ, items, placed, x, want)
        if got == 0:
            break
        left -= got
        x = nx

# ---------- Gewichts‑Muster ----------
def weight_pattern_A(occ, items, placed, x_start: int, n_euro: int) -> None:
    done = 0
    x = x_start
    dx, dy = span_to_cells(EURO.depth_q, EURO.width_q)
    if n_euro > 0 and free(occ, x, center_y(dy), dx, dy):
        place(occ, items, placed, x, center_y(dy), dx, dy, "Euro", EURO.depth_q, EURO.default_weight); done += 1
        x += dx
    while done + 2 <= n_euro and (x - x_start) * cell_cm + EURO.depth_q <= L_EFF:
        got, x = place_euro_row_q(occ, items, placed, x, want=2)
        if got == 0:
            break
        done += got
    while done < n_euro and (x - x_start) * cell_cm + EURO.depth_l <= L_EFF:
        want = min(3, n_euro - done)
        got, nx = place_euro_col_l(occ, items, placed, x, want)
        if got == 0:
            break
        done += got
        x = nx
    if done < n_euro:
        want = min(2, n_euro - done)
        place_euro_row_q(occ, items, placed, x, want)

def weight_pattern_B(occ, items, placed, x_start: int, n_euro: int) -> None:
    done = 0
    x = x_start
    dx, dy = span_to_cells(EURO.depth_q, EURO.width_q)
    for _ in range(2):
        if done < n_euro and free(occ, x, center_y(dy), dx, dy):
            place(occ, items, placed, x, center_y(dy), dx, dy, "Euro", EURO.depth_q, EURO.default_weight); done += 1
            x += dx
    while done + 2 <= n_euro and (x - x_start) * cell_cm + EURO.depth_q <= L_EFF:
        got, x = place_euro_row_q(occ, items, placed, x, want=2)
        if got == 0:
            break
        done += got
    while done < n_euro and (x - x_start) * cell_cm + EURO.depth_l <= L_EFF:
        want = min(3, n_euro - done)
        got, nx = place_euro_col_l(occ, items, placed, x, want)
        if got == 0:
            break
        done += got
        x = nx

def weight_pattern_C(occ, items, placed, x_start: int, n_euro: int) -> None:
    done = 0
    x = x_start
    dx, dy = span_to_cells(EURO.depth_q, EURO.width_q)
    if n_euro > 0 and free(occ, x, center_y(dy), dx, dy):
        place(occ, items, placed, x, center_y(dy), dx, dy, "Euro", EURO.depth_q, EURO.default_weight); done += 1
        x += dx
    while done < n_euro and (x - x_start) * cell_cm + EURO.depth_l <= L_EFF:
        want = min(3, n_euro - done)
        got, nx = place_euro_col_l(occ, items, placed, x, want)
        if got == 0:
            break
        done += got
        x = nx
    while done < n_euro and (x - x_start) * cell_cm + EURO.depth_q <= L_EFF:
        want = min(2, n_euro - done)
        got, x = place_euro_row_q(occ, items, placed, x, want)
        if got == 0:
            break
        done += got

def generate_weight_variants(n_euro: int, n_ind_light: int, n_ind_heavy: int):
    variants = []
    for pattern in (weight_pattern_A, weight_pattern_B, weight_pattern_C):
        occ, items, placed = empty_board()
        x = x_offset_cells
        if n_ind_light > 0:
            x = place_ind_mid_then_edges(occ, items, placed, x, n_ind_light, heavy=False)
        pattern(occ, items, placed, x, n_euro)
        if n_ind_heavy > 0:
            x_heavy = max(x, x + 1)
            place_ind_mid_then_edges(occ, items, placed, x_heavy, n_ind_heavy, heavy=True)
        variants.append((items, placed))
    return variants

# ---------- Standard‑Varianten ----------
def generate_standard_variants(n_euro: int, n_ind_light: int, n_ind_heavy: int):
    variants = []
    # 1) Quer‑lastig
    occ, items, placed = empty_board()
    x = x_offset_cells
    if n_ind_light > 0:
        x = place_ind_mid_then_edges(occ, items, placed, x, n_ind_light, heavy=False)
    euro_variant_q_then_l(occ, items, placed, x, n_euro)
    if n_ind_heavy > 0:
        place_ind_mid_then_edges(occ, items, placed, max(x, x + 1), n_ind_heavy, heavy=True)
    variants.append((items, placed))

    # 2) Längs‑lastig
    occ, items, placed = empty_board()
    x = x_offset_cells
    if n_ind_light > 0:
        x = place_ind_mid_then_edges(occ, items, placed, x, n_ind_light, heavy=False)
    euro_variant_l_then_q(occ, items, placed, x, n_euro)
    if n_ind_heavy > 0:
        place_ind_mid_then_edges(occ, items, placed, max(x, x + 1), n_ind_heavy, heavy=True)
    variants.append((items, placed))

    # 3) Nur längs
    occ, items, placed = empty_board()
    x = x_offset_cells
    if n_ind_light > 0:
        x = place_ind_mid_then_edges(occ, items, placed, x, n_ind_light, heavy=False)
    euro_variant_all_l(occ, items, placed, x, n_euro)
    if n_ind_heavy > 0:
        place_ind_mid_then_edges(occ, items, placed, max(x, x + 1), n_ind_heavy, heavy=True)
    variants.append((items, placed))

    # 4) Nur quer (+ Tail)
    occ, items, placed = empty_board()
    x = x_offset_cells
    if n_ind_light > 0:
        x = place_ind_mid_then_edges(occ, items, placed, x, n_ind_light, heavy=False)
    euro_variant_all_q_with_tail(occ, items, placed, x, n_euro)
    if n_ind_heavy > 0:
        place_ind_mid_then_edges(occ, items, placed, max(x, x + 1), n_ind_heavy, heavy=True)
    variants.append((items, placed))

    return variants

# ---------- Achslast‑Schätzung ----------
def axle_balance(items) -> Tuple[int, int]:
    if not items:
        return 0, 0
    front_origin_cm = (front_buf if use_buffers else 0)
    total_w = 0.0
    front_moment = 0.0
    for (x, _y, _dx, _dy, _typ, depth_cm, w) in items:
        x_cm_start = front_origin_cm + x * cell_cm
        x_cm_center = x_cm_start + depth_cm / 2
        total_w += w
        eff = L_EFF if L_EFF > 0 else TRAILER_L
        pos_factor = max(0.0, 1.0 - (x_cm_center - front_origin_cm) / max(1.0, eff))
        front_moment += w * pos_factor
    if total_w <= 0:
        return 0, 0
    front_pct = int(round(100 * front_moment / total_w))
    rear_pct = 100 - front_pct
    return front_pct, rear_pct

# ---------- UI: Tabs ----------
tab1, tab2 = st.tabs(["🔄 Standard‑Varianten", "⚖️ Gewichtsmodus"])

def render_board(items):
    html = f"""
    <div style='display:grid;
      grid-template-columns: repeat({X}, {cell_px}px);
      grid-auto-rows: {cell_px}px;
      gap: 1px;
      background:#ddd; padding:6px; border:2px solid #333; width:fit-content;'>
    """
    if x_offset_cells > 0:
        html += f"<div style='grid-column:1/span {x_offset_cells}; grid-row:1/span {Y}; background:#f3f3f3;'></div>"
    for (x, y, dx, dy, typ, depth, _w) in items:
        # Farbcode: Euro längs (depth=120) hellblau, Euro quer (depth=80) hellgrün,
        # Industrie/IBC (depth=100) hellorange
        if typ == "Euro":
            bg = "#e3f2fd" if depth == 120 else "#e8f5e9"
        else:
            bg = "#ffe0b2"
        html += f"<div style='grid-column:{x+1}/span {dx}; grid-row:{y+1}/span {dy}; background:{bg}; border:1px solid #777;'></div>"
    html += "</div>"
    height_px = min(680, max(240, (cell_px + 1) * Y + 28))
    st.components.v1.html(html, height=height_px, scrolling=False)

with tab1:
    st.markdown("### Eingaben")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        n_euro = st.number_input("Euro (120×80)", 0, 45, 33, key="std_n_euro")
    with c2:
        n_ind_light = st.number_input("Industrie/IBC leicht", 0, 30, 0, key="std_ind_light")
    with c3:
        n_ind_heavy = st.number_input("Industrie/IBC schwer (z. B. IBC)", 0, 30, 0, key="std_ind_heavy")
    with c4:
        _ = st.markdown("&nbsp;")

    variants = generate_standard_variants(int(n_euro), int(n_ind_light), int(n_ind_heavy))

    if "std_idx" not in st.session_state:
        st.session_state.std_idx = 0
    nvar = len(variants)
    ncol1, ncol2, ncol3 = st.columns([1, 1, 3])
    with ncol1:
        if st.button("◀ Variante", key="std_prev"):
            st.session_state.std_idx = (st.session_state.std_idx - 1) % nvar
    with ncol2:
        if st.button("Variante ▶", key="std_next"):
            st.session_state.std_idx = (st.session_state.std_idx + 1) % nvar
    with ncol3:
        st.markdown(f"**Variante:** {st.session_state.std_idx + 1} / {nvar}")

    items, placed = variants[st.session_state.std_idx]
    render_board(items)

    used_cm = used_length_cm_real(items)
    share = used_cm / TRAILER_L if TRAILER_L else 0.0
    st.markdown(f"**Genutzte Länge (realistisch):** {used_cm} cm von {TRAILER_L} cm (≈ {share:.0%})")
    f_pct, r_pct = axle_balance(items)
    st.markdown(f"**Achslast‑Schätzung:** vorne {f_pct}% / hinten {r_pct}%")

with tab2:
    st.markdown("### Eingaben (Gewichtsmodus)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        n_euro_w = st.number_input("Euro (120×80)", 0, 45, 21, key="w_n_euro")
    with c2:
        n_ind_light_w = st.number_input("Industrie/IBC leicht", 0, 30, 0, key="w_ind_light")
    with c3:
        n_ind_heavy_w = st.number_input("Industrie/IBC schwer (z. B. IBC)", 0, 30, 0, key="w_ind_heavy")
    with c4:
        _ = st.markdown("&nbsp;")

    weight_variants = generate_weight_variants(int(n_euro_w), int(n_ind_light_w), int(n_ind_heavy_w))

    if "w_idx" not in st.session_state:
        st.session_state.w_idx = 0
    nvar_w = len(weight_variants)
    ncol1, ncol2, ncol3 = st.columns([1, 1, 3])
    with ncol1:
        if st.button("◀ Variante", key="w_prev"):
            st.session_state.w_idx = (st.session_state.w_idx - 1) % nvar_w
    with ncol2:
        if st.button("Variante ▶", key="w_next"):
            st.session_state.w_idx = (st.session_state.w_idx + 1) % nvar_w
    with ncol3:
        st.markdown(f"**Gewichts‑Variante:** {st.session_state.w_idx + 1} / {nvar_w}")

    items_w, placed_w = weight_variants[st.session_state.w_idx]
    render_board(items_w)

    used_cm_w = used_length_cm_real(items_w)
    share_w = used_cm_w / TRAILER_L if TRAILER_L else 0.0
    st.markdown(f"**Genutzte Länge (realistisch):** {used_cm_w} cm von {TRAILER_L} cm (≈ {share_w:.0%})")
    f_pct_w, r_pct_w = axle_balance(items_w)
    st.markdown(f"**Achslast‑Schätzung:** vorne {f_pct_w}% / hinten {r_pct_w}%")

with st.expander("🔎 Legende / Hinweise"):
    st.markdown(
        "- **Farbcode:** Euro längs = hellblau, Euro quer = hellgrün, Industrie/IBC = orange\n"
        "- Euro quer = 80×120 cm, Euro längs = 120×80 cm\n"
        "- Industrie/IBC quer = 100×120 cm; schwere Güter eher hinten\n"
        "- Puffer (Front/Heck) reduzieren die **effektive Länge**; links wird ein leerer Bereich dargestellt\n"
        "- Achslast‑Schätzung ist **vereinfacht** und dient nur zur Orientierung"
    )
# ==== 4‑Varianten‑Vergleich: Add-on ==========================================
# Fügt ein flexibles Vergleichsfenster mit 4 frei konfigurierbaren Varianten hinzu.
# Nutzt vorhandene Layout-Funktionen aus deiner Clean-Version, falls vorhanden.
# Darstellung: NUR große Rechteckgrafik (matplotlib).

import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from typing import List, Dict

# ---- Farben / Konstanten (übernehmen Trailer-Maße aus deiner Datei) ----
try:
    TRAILER_LEN_CM
    TRAILER_W_CM
except NameError:
    TRAILER_LEN_CM = 1360
    TRAILER_W_CM = 240

# Palettenmaße (Euro / Industrie)
EURO_L_CM, EURO_W_CM = 120, 80
IND_L_CM,  IND_W_CM  = 120, 100

COLOR_EURO_LONG = "#d9f2d9"    # 3× Euro längs (hellgrün)
COLOR_EURO_QUER = "#cfe8ff"    # Euro quer (2er / Einzel) (hellblau)
COLOR_IND      = "#ffe2b3"     # Industrie (hellorange)
EDGE = "#4a4a4a"

# ---- Hooks auf deine vorhandenen Layout-Funktionen -------------------------
# Erwartete Signaturen (wenn vorhanden):
# - layout_for_preset_euro(n: int, singles_front: int) -> List[Dict]
# - layout_for_preset_industry(n: int)                 -> List[Dict] (falls du eine hast)
def _have(name: str) -> bool:
    return name in globals() and callable(globals()[name])

def _layout_euro(n: int, singles_front: int) -> List[Dict]:
    if _have("layout_for_preset_euro"):
        return globals()["layout_for_preset_euro"](n, singles_front=singles_front)
    # Fallback (einfach, falls deine Funktion anders heißt)
    rows = []
    rem = n
    for _ in range(min(singles_front, rem)):
        rows.append({"type":"EURO_1_TRANS","len_cm":EURO_W_CM}); rem -= 1
    if rem >= 2 and (rem - 2) % 3 == 0:
        rows.append({"type":"EURO_2_TRANS","len_cm":EURO_W_CM}); rem -= 2
    if rem > 0:
        rows += [{"type":"EURO_3_LONG","len_cm":EURO_L_CM} for _ in range(rem // 3)]
    return rows

def _layout_ind(n: int) -> List[Dict]:
    # Wenn du eine eigene Industrie-Funktion hast, nutze sie
    if _have("layout_for_preset_industry"):
        return globals()["layout_for_preset_industry"](n)
    # Minimaler Fallback: bildet Reihen à 2 Industrie längs (120 x 100 → 2 nebeneinander = 200 Breite)
    rows = []
    if n <= 0:
        return rows
    # Wir mappen 2 Industrie ≈ eine "Industrie-Reihe" (120 cm Länge)
    full_rows = n // 2
    single = n % 2
    rows += [{"type":"IND_ROW_2_LONG","len_cm":IND_L_CM}] * full_rows
    if single:
        rows.insert(0, {"type":"IND_SINGLE","len_cm":IND_L_CM})  # eine einzelne Industrie vorne
    return rows

def _cap_to_trailer(rows: List[Dict]) -> List[Dict]:
    out, s = [], 0
    for r in rows:
        L = r.get("len_cm", EURO_L_CM)
        if s + L > TRAILER_LEN_CM:
            break
        rr = dict(r); rr["len_cm"] = L
        out.append(rr); s += L
    return out

# ---- Rows → Rechteck-Koordinaten ------------------------------------------
def _rows_to_rects(rows: List[Dict]) -> list:
    """
    Wandelt Reihen in Rechtecke um:
    - EURO_3_LONG: 3× (120×80) über die Breite 240 (y=0,80,160)
    - EURO_2_TRANS: 2× (80×120) (y=0,120)
    - EURO_1_TRANS: 1× (80×120) mittig (y=60)
    - Industrie:
      - IND_ROW_2_LONG: 2× (120×100) über 200 Breite (y=20,120) -> mit 20 cm "Luft" je Seite
      - IND_SINGLE: 1× (120×100) mittig (y=70)
    """
    rects = []
    x = 0
    for r in rows:
        t = r.get("type", "")
        L = r.get("len_cm", EURO_L_CM)

        if t == "EURO_3_LONG":
            w, h = 120, 80
            for lane in range(3):
                rects.append((x, lane*80, w, h, COLOR_EURO_LONG))
            x += L

        elif t == "EURO_2_TRANS":
            w, h = 80, 120
            for lane in range(2):
                rects.append((x, lane*120, w, h, COLOR_EURO_QUER))
            x += L

        elif t == "EURO_1_TRANS":
            w, h = 80, 120
            rects.append((x, 60, w, h, COLOR_EURO_QUER))
            x += L

        elif t == "IND_ROW_2_LONG":
            w, h = 120, 100
            rects.append((x, 20,  w, h, COLOR_IND))   # y=20
            rects.append((x, 120, w, h, COLOR_IND))   # y=120
            x += L

        elif t == "IND_SINGLE":
            w, h = 120, 100
            rects.append((x, 70, w, h, COLOR_IND))    # mittig
            x += L

        else:
            # unbekannt: versuche generisch (als Euro-längs)
            w, h = L, 80
            rects.append((x, 80, w, h, "#dddddd"))
            x += L
    return rects

def _draw_graph(title: str, rows: List[Dict], figsize=(7.5, 1.5)):
    rects = _rows_to_rects(_cap_to_trailer(rows))
    fig, ax = plt.subplots(figsize=figsize)
    ax.add_patch(Rectangle((0, 0), TRAILER_LEN_CM, TRAILER_W_CM,
                           fill=False, linewidth=1.8, edgecolor="#333333"))
    for (x, y, w, h, c) in rects:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=c, edgecolor="#4a4a4a", linewidth=0.8))
    ax.set_xlim(0, TRAILER_LEN_CM); ax.set_ylim(0, TRAILER_W_CM)
    ax.set_aspect('equal'); ax.axis('off')
    ax.set_title(title, fontsize=11, pad=5)
    st.pyplot(fig); plt.close(fig)

# ---- UI: 4 Varianten --------------------------------------------------------
def show_compare_four_variants():
    st.subheader("Vergleich (4 Varianten) – reine Grafik")

    layout_choice = st.radio("Layout", ["4 Spalten", "2×2 Grid"], index=0, horizontal=True)
    size = st.slider("Grafikgröße", 1, 10, 6, help="Kleiner = kompaktere Leisten", key="gfx_size")

    def variant_controls(idx: int):
        with st.container(border=True):
            st.markdown(f"**Variante {idx}**")
            c1, c2, c3 = st.columns(3)
            with c1:
                euro_n = st.number_input(f"Euro (Var {idx})", 0, 40, 33 if idx==1 else 0, step=1)
            with c2:
                singles = st.slider(f"Einzel quer (Var {idx})", 0, 2, 0)
            with c3:
                ind_n = st.number_input(f"Industrie (Var {idx})", 0, 40, 0, step=1)

            # Reihen aus deinen Funktionen (Euro + Industrie) zusammensetzen
            rows = []
            if euro_n > 0:
                rows += _layout_euro(euro_n, singles)
            if ind_n > 0:
                rows += _layout_ind(ind_n)
            return rows, f"Var {idx}: {euro_n} Euro (Singles {singles}) + {ind_n} Industrie"

    # Eingaben für 4 Varianten
    rows1, title1 = variant_controls(1)
    rows2, title2 = variant_controls(2)
    rows3, title3 = variant_controls(3)
    rows4, title4 = variant_controls(4)

    # Render
    figsize = (6 + size*0.3, 1.3)  # kompakt skalieren

    if layout_choice == "4 Spalten":
        c1, c2, c3, c4 = st.columns(4)
        with c1: _draw_graph(title1, rows1, figsize=figsize)
        with c2: _draw_graph(title2, rows2, figsize=figsize)
        with c3: _draw_graph(title3, rows3, figsize=figsize)
        with c4: _draw_graph(title4, rows4, figsize=figsize)
    else:
        r1 = st.columns(2); r2 = st.columns(2)
        with r1[0]: _draw_graph(title1, rows1, figsize=figsize)
        with r1[1]: _draw_graph(title2, rows2, figsize=figsize)
        with r2[0]: _draw_graph(title3, rows3, figsize=figsize)
        with r2[1]: _draw_graph(title4, rows4, figsize=figsize)

# ---- Toggle im Sidebar: Vergleich einschalten -------------------------------
st.sidebar.markdown("---")
if st.sidebar.toggle("Vergleich (4 Varianten)", value=False, help="Vier frei konfigurierbare Varianten parallel anzeigen."):
    show_compare_four_variants()
# ==== /Add-on ================================================================
