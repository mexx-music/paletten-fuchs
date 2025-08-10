# pal_fuchs_app.py
# 🦊 Pal Fuchs – Varianten & Gewichtsmodus (Finale Spezifikation)
# – Kühlsattel-Puffer (Front/Heck) mit effektiver Länge
# – Reale Kombi-Logik (quer-lastig / längs-lastig / nur längs / nur quer+Tail)
# – Industrie/IBC mit gewichtsabhängiger Platzierung (schwer eher hinten)
# – Gewichtsmodus: mehrere gewichtsausbalancierte Muster + Achslast-Schätzung
# – Maßhaltige Darstellung (ceil), Standard: cell_cm=40, cell_px=6, Auto-Zoom aus
# – Ruff/PEP8 freundlich

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
    cell_cm = st.slider("Raster (cm/Zelle)", 20, 50, 40, 5)
    auto_zoom = st.checkbox("Auto‑Zoom auf konstante Breite", False)
    cell_px = st.slider("Zell‑Pixel", 4, 20, 6, 1, disabled=auto_zoom)
    st.markdown("---")
    st.markdown("### 🚛 Kühlsattel / Puffer")
    use_buffers = st.checkbox("Puffer aktivieren (dicke Türen / Aggregat)", False)
    front_buf = st.number_input("Front‑Puffer (cm)", 0, 120, 0, 5, disabled=not use_buffers)
    rear_buf = st.number_input("Heck‑Puffer (cm)", 0, 120, 0, 5, disabled=not use_buffers)
    st.caption("Hinweis: Front‑Puffer ist in der Praxis nur relevant, wenn Paletten hoch genug sind, um ins Aggregat zu ragen.")

# Effektive Länge & Grid
L_EFF = max(0, TRAILER_L - (front_buf if use_buffers else 0) - (rear_buf if use_buffers else 0))
X = max(1, math.floor(TRAILER_L / cell_cm))  # Gesamt-Raster über volle Trailerlänge (für optische Puffer)
Y = max(1, math.ceil(TRAILER_W / cell_cm))

# Auto-Zoom (optional)
if auto_zoom:
    cell_px = max(4, min(20, round(820 / X)))

x_offset_cells = math.ceil((front_buf if use_buffers else 0) / cell_cm)  # optischer Offset

# ---------- Datenmodelle ----------
@dataclass
class PalType:
    name: str
    depth_l: int     # entlang Länge bei "längs" (cm)
    width_l: int     # quer bei "längs" (cm)
    depth_q: int     # entlang Länge bei "quer" (cm)
    width_q: int     # quer bei "quer" (cm)
    default_weight: int  # kg (für Achslast-Schätzung)

EURO = PalType("Euro", depth_l=120, width_l=80, depth_q=80, width_q=120, default_weight=250)
IND  = PalType("Industrie/IBC", depth_l=120, width_l=100, depth_q=100, width_q=120, default_weight=1100)  # IBC schwer

# ---------- Board / Platzierung ----------
def span_to_cells(depth_cm: int, width_cm: int) -> Tuple[int, int]:
    dx = max(1, math.ceil(depth_cm / cell_cm))  # entlang Trailer-Länge
    dy = max(1, math.ceil(width_cm / cell_cm))  # quer
    return dx, dy

def center_y(dy: int) -> int:
    return max(0, (Y - dy) // 2)

def empty_board():
    occ = [[False] * X for _ in range(Y)]
    # items: (x, y, dx, dy, icon_key, typ, depth_cm, weight_kg)
    items: List[Tuple[int, int, int, int, str, str, int, int]] = []
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
    icon_key = ("Euro", "l") if (typ_name == "Euro" and depth_cm == 120) else \
               ("Euro", "q") if (typ_name == "Euro" and depth_cm == 80) else \
               ("Industrie", "q")
    # store
    items.append((x, y, dx, dy, str(icon_key), typ_name, depth_cm, weight_kg))
    placed[typ_name] = placed.get(typ_name, 0) + 1

def used_length_cm_real(items) -> int:
    if not items:
        return 0
    rightmost = 0
    for (x, _y, _dx, _dy, _icon, _typ, depth_cm, _w) in items:
        rightmost = max(rightmost, x * cell_cm + depth_cm)
    # Inkl. Front-Puffer fürs Reporting
    return min((front_buf if use_buffers else 0) + rightmost, TRAILER_L)

# ---------- Hilfs-Platzierer ----------
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

def place_ind_row_q(occ, items, placed, x: int, want: int, weight: int = IND.default_weight) -> Tuple[int, int]:
    # Industrie/IBC quer (immer)
    dx, dy = span_to_cells(IND.depth_q, IND.width_q)
    placed_now = 0
    for y in (0, Y - dy):
        if placed_now >= want:
            break
        if free(occ, x, y, dx, dy):
            place(occ, items, placed, x, y, dx, dy, "Industrie/IBC", IND.depth_q, weight)
            placed_now += 1
    return placed_now, x + dx

def place_ind_mid_then_edges(occ, items, placed, x: int, count: int, heavy: bool) -> int:
    # Erst optional mittig (1), dann Paare außen – heavy kann weiter hinten (x verschieben) gesetzt werden
    dx, dy = span_to_cells(IND.depth_q, IND.width_q)
    w = IND.default_weight if heavy else max(600, IND.default_weight // 2)
    # falls heavy → leicht nach hinten schieben (eine Zelle Puffer vorn), wenn Platz
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

# ---------- Reale Varianten-Logik (Euro) ----------
def euro_variant_q_then_l(occ, items, placed, x_start: int, n: int) -> None:
    """Quer-lastig: maximal Querreihen in L_EFF, Rest längs. Exakt n."""
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
        got, _ = place_euro_row_q(occ, items, placed, x, want)
        done += got

def euro_variant_l_then_q(occ, items, placed, x_start: int, n: int) -> None:
    """Längs-lastig: maximal Längsspalten in L_EFF, Rest quer. Exakt n."""
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

# ---------- Weight-Patterns (für beliebige N, bevorzugt 20/21/23/24) ----------
def weight_pattern_A(occ, items, placed, x_start: int, n_euro: int) -> None:
    """Muster A: 1× mittig quer → Doppel-Querreihen → Längsblock → ggf. Querabschluss."""
    done = 0
    x = x_start
    # 1 mittig quer
    dx, dy = span_to_cells(EURO.depth_q, EURO.width_q)
    if n_euro > 0 and free(occ, x, center_y(dy), dx, dy):
        place(occ, items, placed, x, center_y(dy), dx, dy, "Euro", EURO.depth_q, EURO.default_weight); done += 1
        x += dx
    # Doppel-Querreihen
    while done + 2 <= n_euro and (x - x_start) * cell_cm + EURO.depth_q <= L_EFF:
        got, x = place_euro_row_q(occ, items, placed, x, want=2)
        if got == 0:
            break
        done += got
    # Längsblock
    while done < n_euro and (x - x_start) * cell_cm + EURO.depth_l <= L_EFF:
        want = min(3, n_euro - done)
        got, nx = place_euro_col_l(occ, items, placed, x, want)
        if got == 0:
            break
        done += got
        x = nx
    # Querabschluss (Rest)
    if done < n_euro:
        want = min(2, n_euro - done)
        got, _ = place_euro_row_q(occ, items, placed, x, want)
        done += got

def weight_pattern_B(occ, items, placed, x_start: int, n_euro: int) -> None:
    """Muster B: 2× mittig quer → Doppel-Querreihen → Längsblock."""
    done = 0
    x = x_start
    dx, dy = span_to_cells(EURO.depth_q, EURO.width_q)
    # 2 mittig quer (hintereinander)
    for _ in range(2):
        if done < n_euro and free(occ, x, center_y(dy), dx, dy):
            place(occ, items, placed, x, center_y(dy), dx, dy, "Euro", EURO.depth_q, EURO.default_weight); done += 1
            x += dx
    # Doppel quer
    while done + 2 <= n_euro and (x - x_start) * cell_cm + EURO.depth_q <= L_EFF:
        got, x = place_euro_row_q(occ, items, placed, x, want=2)
        if got == 0:
            break
        done += got
    # Längs
    while done < n_euro and (x - x_start) * cell_cm + EURO.depth_l <= L_EFF:
        want = min(3, n_euro - done)
        got, nx = place_euro_col_l(occ, items, placed, x, want)
        if got == 0:
            break
        done += got
        x = nx

def weight_pattern_C(occ, items, placed, x_start: int, n_euro: int) -> None:
    """Muster C: 1 mittig quer → Längsblock → hinten Doppel-Querreihen."""
    done = 0
    x = x_start
    dx, dy = span_to_cells(EURO.depth_q, EURO.width_q)
    if n_euro > 0 and free(occ, x, center_y(dy), dx, dy):
        place(occ, items, placed, x, center_y(dy), dx, dy, "Euro", EURO.depth_q, EURO.default_weight); done += 1
        x += dx
    # Längs zuerst
    while done < n_euro and (x - x_start) * cell_cm + EURO.depth_l <= L_EFF:
        want = min(3, n_euro - done)
        got, nx = place_euro_col_l(occ, items, placed, x, want)
        if got == 0:
            break
        done += got
        x = nx
    # Hinten quer (so weit möglich)
    while done < n_euro and (x - x_start) * cell_cm + EURO.depth_q <= L_EFF:
        want = min(2, n_euro - done)
        got, x = place_euro_row_q(occ, items, placed, x, want)
        if got == 0:
            break
        done += got

def generate_weight_variants(n_euro: int, n_ind_light: int, n_ind_heavy: int):
    variants = []
    # V0: Industrie/IBC abhängig vom Gewicht verteilen (leicht eher vorn, schwer eher hinten)
    for pattern in (weight_pattern_A, weight_pattern_B, weight_pattern_C):
        occ, items, placed = empty_board()
        x = x_offset_cells  # optischer Start nach Front-Puffer

        # Leichte Industrie vorn:
        if n_ind_light > 0:
            x = place_ind_mid_then_edges(occ, items, placed, x, n_ind_light, heavy=False)

        # Euro nach Muster
        pattern(occ, items, placed, x, n_euro)

        # Schwere Industrie/IBC hinten:
        if n_ind_heavy > 0:
            # schiebe falls möglich einen "Slot" nach rechts, damit sie weiter hinten landen
            x_heavy = max(x, x + 1)
            place_ind_mid_then_edges(occ, items, placed, x_heavy, n_ind_heavy, heavy=True)

        variants.append((items, placed))
    return variants

# ---------- Standard-Varianten-Generator ----------
def generate_standard_variants(n_euro: int, n_ind_light: int, n_ind_heavy: int):
    variants = []
    # 1) Quer-lastig
    occ, items, placed = empty_board()
    x = x_offset_cells
    if n_ind_light > 0:
        x = place_ind_mid_then_edges(occ, items, placed, x, n_ind_light, heavy=False)
    euro_variant_q_then_l(occ, items, placed, x, n_euro)
    if n_ind_heavy > 0:
        place_ind_mid_then_edges(occ, items, placed, max(x, x + 1), n_ind_heavy, heavy=True)
    variants.append((items, placed))

    # 2) Längs-lastig
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

# ---------- Achslast-Schätzung (grobe, relative %) ----------
def axle_balance(items) -> Tuple[int, int]:
    """Schätze Verteilung vorne/hinten: Summe (Gewicht * Distanz) entlang Länge.
    Einfaches Modell: Anteil vorne = mittlere Normierung von Paletten-Schwerpunkt.
    """
    if not items:
        return 0, 0
    front_origin_cm = (front_buf if use_buffers else 0)
    total_w = 0.0
    front_moment = 0.0  # alles links vom Trailer-Mittelpunkt = 'vorne'
    for (x, _y, dx, _dy, _icon, _typ, depth_cm, w) in items:
        # Schwerpunkt der Palette (in cm ab Trailer-Anfang)
        x_cm_start = front_origin_cm + x * cell_cm
        x_cm_center = x_cm_start + depth_cm / 2
        total_w += w
        # Anteil "vorne" als linearer Faktor (je näher an vorne, desto höher)
        # Normiere über L_EFF (falls 0 → TRAILER_L)
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

with tab1:
    st.markdown("### Eingaben")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        n_euro = st.number_input("Euro (120×80)", 0, 45, 33)
    with c2:
        n_ind_light = st.number_input("Industrie/IBC leicht", 0, 30, 0)
    with c3:
        n_ind_heavy = st.number_input("Industrie/IBC schwer (z. B. IBC)", 0, 30, 0)
    with c4:
        _ = st.markdown("&nbsp;")

    variants = generate_standard_variants(int(n_euro), int(n_ind_light), int(n_ind_heavy))

    # Navigation
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

    # Render (optischer linker Puffer)
    html = f"""
    <div style="
      display:grid;
      grid-template-columns: repeat({X}, {cell_px}px);
      grid-auto-rows: {cell_px}px;
      gap: 1px;
      background:#ddd; padding:6px; border:2px solid #333; width:fit-content;">
    """
    # Linker Pufferbereich
    if x_offset_cells > 0:
        html += f'<div style="grid-column:1/span {x_offset_cells}; grid-row:1/span {Y}; background:#f3f3f3;"></div>'
    # Items
    for (x, y, dx, dy, icon_key, typ, _depth, _w) in items:
        html += f"""
        <div style="
          grid-column:{x+1}/span {dx};
          grid-row:{y+1}/span {dy};
          background: #fafafa;
          border:1px solid #777;"></div>
        """
    html += "</div>"
    height_px = min(680, max(240, (cell_px + 1) * Y + 28))
    st.components.v1.html(html, height=height_px, scrolling=False)

    # Auswertung
    used_cm = used_length_cm_real(items)
    share = used_cm / TRAILER_L if TRAILER_L else 0.0
    st.markdown(f"**Genutzte Länge (realistisch):** {used_cm} cm von {TRAILER_L} cm (≈ {share:.0%})")
    front_pct, rear_pct = axle_balance(items)
    st.markdown(f"**Achslast‑Schätzung:** vorne {front_pct}% / hinten {rear_pct}%")

with tab2:
    st.markdown("### Eingaben (Gewichtsmodus)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        n_euro_w = st.number_input("Euro (120×80)", 0, 45, 21)
    with c2:
        n_ind_light_w = st.number_input("Industrie/IBC leicht", 0, 30, 0)
    with c3:
        n_ind_heavy_w = st.number_input("Industrie/IBC schwer (z. B. IBC)", 0, 30, 0)
    with c4:
        _ = st.markdown("&nbsp;")

    # Universell: bei jeder Menge – besonders hilfreich bei 20/21/23/24
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

    # Render
    html = f"""
    <div style="
      display:grid;
      grid-template-columns: repeat({X}, {cell_px}px);
      grid-auto-rows: {cell_px}px;
      gap: 1px;
      background:#ddd; padding:6px; border:2px solid #333; width:fit-content;">
    """
    if x_offset_cells > 0:
        html += f'<div style="grid-column:1/span {x_offset_cells}; grid-row:1/span {Y}; background:#f3f3f3;"></div>'
    for (x, y, dx, dy, icon_key, typ, _depth, _w) in items_w:
        html += f"""
        <div style="
          grid-column:{x+1}/span {dx};
          grid-row:{y+1}/span {dy};
          background:#fafafa; border:1px solid #777;"></div>
        """
    html += "</div>"
    height_px = min(680, max(240, (cell_px + 1) * Y + 28))
    st.components.v1.html(html, height=height_px, scrolling=False)

    used_cm_w = used_length_cm_real(items_w)
    share_w = used_cm_w / TRAILER_L if TRAILER_L else 0.0
    st.markdown(f"**Genutzte Länge (realistisch):** {used_cm_w} cm von {TRAILER_L} cm (≈ {share_w:.0%})")
    front_pct_w, rear_pct_w = axle_balance(items_w)
    st.markdown(f"**Achslast‑Schätzung:** vorne {front_pct_w}% / hinten {rear_pct_w}%")

# ---------- Legende ----------
with st.expander("🔎 Legende / Hinweise"):
    st.markdown(
        "- Euro quer = 80 cm Tiefe × 120 cm Breite, Euro längs = 120×80\n"
        "- Industrie/IBC wird quer 100×120 dargestellt, im Gewichtsmodus als **schwer** behandelt (hinten bevorzugt)\n"
        "- Puffer (Front/Heck) reduzieren die **effektive Länge**; optisch wird links ein leerer Bereich gezeigt\n"
        "- Achslast‑Schätzung ist **vereinfacht** (relativ, nicht rechtlich verbindlich)"
    )
