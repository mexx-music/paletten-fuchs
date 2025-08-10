# paletten_fuchs_app.py
# 🦊 Paletten Fuchs – Finale, fusionierte Version (Unicode | Abbildung 1)
# - Eine Datei
# - Unicode-Darstellung (keine Icons)
# - Kühlsattel-Puffer, L_eff
# - Varianten V1–V4 (Euro), Industrie/IBC-Mix, Gewichtsmodus
# - Ceil-Rasterung, saubere Heckabschlüsse
# - Achslast-Schätzung, Varianten-Karussell, Testfälle

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import streamlit as st


# ----------------------------- Grunddaten -----------------------------
TRAILER_W_CM = 245         # Innenbreite (cm)
TRAILER_L_CM = 1360        # Nominal-Länge (cm) – Basis Kühlsattel
EURO_L, EURO_W = 120, 80   # Euro 120x80
IND_L, IND_W = 120, 100    # Industrie 120x100 (quer bevorzugt / fest)
# Unicode "Look" wie Abbildung 1:
CHAR_EURO_LONG = "▮"       # längs (schmal)
CHAR_EURO_CROSS = "▬"      # quer (flach)
CHAR_IND = "⬜"             # Industrie/IBC


@dataclass
class PalSpec:
    name: str
    depth_cm: int     # entlang Laderaumlänge
    width_cm: int     # quer
    char: str
    heavy: bool       # für Gewichtsmodus / Achslast
    force_cross: bool # z. B. Industrie/IBC überwiegend quer


# Palettentypen (Industrie/IBC immer "schwer")
PALETTEN: Dict[str, PalSpec] = {
    "EURO_L": PalSpec("Euro längs", EURO_L, EURO_W, CHAR_EURO_LONG, False, False),
    "EURO_Q": PalSpec("Euro quer", EURO_W, EURO_L, CHAR_EURO_CROSS, False, False),
    "IND_Q": PalSpec("Industrie/IBC quer", IND_W, IND_L, CHAR_IND, True, True),
}


# ----------------------------- Helfer -----------------------------
def ceil_cells(cm: int, cell_cm: int) -> int:
    """Auf Rasterzellen nach oben runden (maßhaltig)."""
    return max(1, math.ceil(cm / cell_cm))


def center_row(total_rows: int, h: int) -> int:
    return max(0, (total_rows - h) // 2)


def used_length_cm(items: List[Tuple[int, int, int, int, str]], cell_cm: int) -> int:
    if not items:
        return 0
    x_end = max(x + dx for (x, y, dx, dy, ch) in items)
    return x_end * cell_cm


def estimate_axle_balance(
    items: List[Tuple[int, int, int, int, str]],
    cell_cm: int,
    l_eff_cm: int,
) -> Tuple[int, int]:
    """
    Sehr grobe Achslast-Schätzung (% vorn, % hinten):
    - projiziert Blöcke entlang der Länge
    - Schwer=Gewichtsfaktor 2, sonst 1
    - Splittet Anteil relativ zur Position (vorne/hinten)
    """
    if not items:
        return 50, 50

    total = 0.0
    front_score = 0.0
    half = l_eff_cm / 2

    for (x, _y, dx, dy, ch) in items:
        block_l = dx * cell_cm
        x_cm = x * cell_cm
        block_center = x_cm + block_l / 2
        # Gewichtsfaktor: Industrie/IBC (⬜) schwerer
        g = 2.0 if ch == CHAR_IND else 1.0
        total += g

        # Anteil: je näher an Front (<half), desto mehr vorn
        # Linearer Split:
        if block_center <= half:
            # ganz vorn -> 100% vorn
            # Mitte -> ~50/50
            front_share = 0.5 + (half - block_center) / (2 * half)
        else:
            front_share = 0.5 - (block_center - half) / (2 * half)
        front_share = max(0.0, min(1.0, front_share))
        front_score += g * front_share

    front_pct = int(round(100 * front_score / total))
    back_pct = 100 - front_pct
    return front_pct, back_pct


# ----------------------------- Belegung / Board -----------------------------
class Board:
    def __init__(self, l_eff_cm: int, w_cm: int, cell_cm: int):
        self.cell_cm = cell_cm
        self.X = ceil_cells(l_eff_cm, cell_cm)
        self.Y = ceil_cells(w_cm, cell_cm)
        self.occ = [[False] * self.X for _ in range(self.Y)]
        self.items: List[Tuple[int, int, int, int, str]] = []  # (x,y,dx,dy,char)

    def free(self, x: int, y: int, dx: int, dy: int) -> bool:
        if x < 0 or y < 0 or x + dx > self.X or y + dy > self.Y:
            return False
        for yy in range(y, y + dy):
            for xx in range(x, x + dx):
                if self.occ[yy][xx]:
                    return False
        return True

    def place(self, x: int, y: int, dx: int, dy: int, ch: str) -> None:
        for yy in range(y, y + dy):
            for xx in range(x, x + dx):
                self.occ[yy][xx] = True
        self.items.append((x, y, dx, dy, ch))

    def first_free_x(self) -> int:
        for xx in range(self.X):
            if any(not self.occ[yy][xx] for yy in range(self.Y)):
                return xx
        return self.X


# ----------------------------- Platzierungs-Bausteine -----------------------------
def place_euro_3lane_long(board: Board, n: int) -> int:
    """3-Spur längs (Euro 120x80). Gibt belegte Spalten (x-Ende) zurück."""
    dl = ceil_cells(EURO_L, board.cell_cm)
    wl = ceil_cells(EURO_W, board.cell_cm)
    x = board.first_free_x()
    lanes = [0, center_row(board.Y, wl), board.Y - wl]
    while n > 0 and x + dl <= board.X:
        for y in lanes:
            if n <= 0:
                break
            if board.free(x, y, dl, wl):
                board.place(x, y, dl, wl, CHAR_EURO_LONG)
                n -= 1
        x += dl
    return n


def tail_close_clean(board: Board, n_left: int) -> int:
    """
    Sauberer Heckabschluss:
    - bevorzugt: 3 längs, ansonsten 2 quer, wenn sinnvoll
    """
    if n_left <= 0:
        return 0

    dl = ceil_cells(EURO_L, board.cell_cm)
    wl = ceil_cells(EURO_W, board.cell_cm)
    dq = ceil_cells(EURO_W, board.cell_cm)
    wq = ceil_cells(EURO_L, board.cell_cm)
    x = board.first_free_x()
    lanes_long = [0, center_row(board.Y, wl), board.Y - wl]

    # Falls n durch 3 teilbar – versuche 3 längs-Spuren:
    if n_left >= 3 and x + dl <= board.X:
        ok = True
        for y in lanes_long:
            if not board.free(x, y, dl, wl):
                ok = False
                break
        if ok:
            for y in lanes_long:
                board.place(x, y, dl, wl, CHAR_EURO_LONG)
            return n_left - 3

    # Sonst 2 quer außen:
    if n_left >= 2 and x + dq <= board.X:
        left_ok = board.free(x, 0, dq, wq)
        right_ok = board.free(x, board.Y - wq, dq, wq)
        if left_ok:
            board.place(x, 0, dq, wq, CHAR_EURO_CROSS)
            n_left -= 1
        if n_left > 0 and right_ok:
            board.place(x, board.Y - wq, dq, wq, CHAR_EURO_CROSS)
            n_left -= 1
        return n_left

    # Notlösung: ein längs, falls Platz:
    if n_left >= 1 and x + dl <= board.X:
        # mittlere Spur bevorzugen
        y = center_row(board.Y, wl)
        if board.free(x, y, dl, wl):
            board.place(x, y, dl, wl, CHAR_EURO_LONG)
            n_left -= 1

    return n_left


def place_euro_max_cross_then_tail(board: Board, n: int, offset_cross: int = 0) -> int:
    """Quer-lastig: so viele Querreihen wie möglich, Rest mit sauberem Tail."""
    dq = ceil_cells(EURO_W, board.cell_cm)
    wq = ceil_cells(EURO_L, board.cell_cm)
    x = board.first_free_x()

    while n >= 3 and x + dq <= board.X:
        # Drei Quer nebeneinander (oben/mittig/unten) – optisch wie Abbildung 1
        y_mid = center_row(board.Y, wq) + offset_cross
        y_mid = max(0, min(board.Y - wq, y_mid))
        spots = [0, y_mid, board.Y - wq]
        placed_any = False
        for y in spots:
            if n <= 0:
                break
            if board.free(x, y, dq, wq):
                board.place(x, y, dq, wq, CHAR_EURO_CROSS)
                n -= 1
                placed_any = True
        if placed_any:
            x += dq
        else:
            # wenn blockiert, 1 Zelle weiter
            x += 1

    # Rest sauber schließen
    return tail_close_clean(board, n)


def place_euro_max_long_then_tail(board: Board, n: int) -> int:
    """Längs-lastig: so viele 3-Spur-Längsblöcke wie möglich, Rest sauber schließen."""
    while True:
        before = n
        n = place_euro_3lane_long(board, n)
        if n == before:
            break
    return tail_close_clean(board, n)


def place_euro_all_long(board: Board, n: int) -> int:
    """Nur längs (3-Spur); Rest wird ggf. Tail geschlossen."""
    n = place_euro_3lane_long(board, n)
    return tail_close_clean(board, n)


def place_euro_all_cross_with_smart_tail(board: Board, n: int, offset_cross: int = 0) -> int:
    """Nur quer, dann sinnvoller Längs-Tail – kein unrealistisches Voll-Quer bei 33."""
    dq = ceil_cells(EURO_W, board.cell_cm)
    wq = ceil_cells(EURO_L, board.cell_cm)
    x = board.first_free_x()

    while n > 0 and x + dq <= board.X:
        y_mid = center_row(board.Y, wq) + offset_cross
        y_mid = max(0, min(board.Y - wq, y_mid))
        spots = [0, y_mid, board.Y - wq]
        filled = 0
        for y in spots:
            if n <= 0:
                break
            if board.free(x, y, dq, wq):
                board.place(x, y, dq, wq, CHAR_EURO_CROSS)
                n -= 1
                filled += 1
        if filled == 0:
            x += 1
        else:
            x += dq

        # Sicherheitsbremse gegen "33 alles quer"
        # Wenn wenig Länge übrig bleibt, brich ab und Tail schliessen
        if n > 0 and (board.X - x) < ceil_cells(EURO_L, board.cell_cm):
            break

    return tail_close_clean(board, n)


def place_industry_mix(board: Board, n_ind: int, mode_heavy_back: bool = True, offset_cross: int = 0) -> None:
    """Industrie/IBC (quer). Bei 'schwer': eher hinten, sonst vorn/mittig."""
    if n_ind <= 0:
        return
    dq = ceil_cells(IND_W, board.cell_cm)
    wq = ceil_cells(IND_L, board.cell_cm)
    x = board.first_free_x()

    # Reihen von quer-Blöcken paarweise außen, ungerade zuerst mittig
    if n_ind % 2 == 1:
        y_mid = center_row(board.Y, wq) + offset_cross
        y_mid = max(0, min(board.Y - wq, y_mid))
        if board.free(x, y_mid, dq, wq):
            board.place(x, y_mid, dq, wq, CHAR_IND)
            n_ind -= 1
            x += dq

    while n_ind > 0 and x + dq <= board.X:
        spots = [0, board.Y - wq]
        # Gewichtsmodus: bei "schwer hinten" zuerst unten (angenommen "hinten" = unten),
        # ansonsten oben beginnen – rein optische Heuristik
        if mode_heavy_back:
            spots = [board.Y - wq, 0]
        for y in spots:
            if n_ind > 0 and board.free(x, y, dq, wq):
                board.place(x, y, dq, wq, CHAR_IND)
                n_ind -= 1
        x += dq


# ----------------------------- Varianten (Euro) -----------------------------
def build_variant(
    l_eff_cm: int,
    cell_cm: int,
    n_euro: int,
    n_ind: int,
    variant: str,
    cross_offset: int,
    heavy_back: bool,
) -> Tuple[Board, int]:
    board = Board(l_eff_cm, TRAILER_W_CM, cell_cm)

    # Industrie/IBC zuerst
    place_industry_mix(board, n_ind, mode_heavy_back=heavy_back, offset_cross=cross_offset)

    # Dann Euro gemäß Variante
    if variant == "V1 Quer-lastig":
        n_rem = place_euro_max_cross_then_tail(board, n_euro, offset_cross=cross_offset)
    elif variant == "V2 Längs-lastig":
        n_rem = place_euro_max_long_then_tail(board, n_euro)
    elif variant == "V3 Nur längs (3-Spur)":
        n_rem = place_euro_all_long(board, n_euro)
    elif variant == "V4 Nur quer (+ Tail)":
        n_rem = place_euro_all_cross_with_smart_tail(board, n_euro, offset_cross=cross_offset)
    else:
        n_rem = n_euro

    return board, n_rem


# ----------------------------- Rendering -----------------------------
def render_board(board: Board, cell_px: int) -> None:
    # Unicode-Blocks als absolut positionierte "Zellen"
    html = [
        f"""
        <div style="
            position:relative;
            width:{board.X*(cell_px+1)+6}px;
            padding:4px;
            border:2px solid #333;
            background:#e9ecef;">
        """
    ]
    # Paletten zeichnen
    for (x, y, dx, dy, ch) in board.items:
        left = x * (cell_px + 1)
        top = y * (cell_px + 1)
        w = dx * (cell_px + 1) - 1
        h = dy * (cell_px + 1) - 1
        html.append(
            f"""
            <div style="
                position:absolute; left:{left}px; top:{top}px;
                width:{w}px; height:{h}px;
                border:1px solid #666; background:#fff;
                display:flex; align-items:center; justify-content:center;
                font-size:{max(10, cell_px)}px; line-height:1;">
                {ch}
            </div>
            """
        )
    html.append("</div>")
    st.components.v1.html("".join(html), height=min(700, board.Y * (cell_px + 1) + 20))


# ----------------------------- App -----------------------------
def main() -> None:
    st.set_page_config(page_title="🦊 Paletten Fuchs – Finale Unicode", layout="centered")
    st.title("🦊 Paletten Fuchs – Finale Unicode-Version (Abbildung 1)")

    # --- Presets / Popup ---
    col_preset, col_info = st.columns([1, 2])
    with col_preset:
        with st.expander("⚙️ Presets & Setup", expanded=False):
            preset = st.selectbox(
                "Preset wählen",
                [
                    "Standard 40cm / 6px",
                    "Kompatibel 25cm / 4px",
                    "Kühlsattel ohne Puffer",
                    "Kühlsattel mit Puffer 10/10",
                ],
                index=0,
            )
    with col_info:
        st.caption("Unicode-Darstellung wie *Abbildung 1*. Ceil-Rasterung aktiv. Sauberer Heckabschluss.")

    # --- Basis-Parameter ---
    # Standardanzeige: Raster 40, Zell-Pixel 6
    cell_cm_default, cell_px_default = (40, 6)
    if preset == "Kompatibel 25cm / 4px":
        cell_cm_default, cell_px_default = (25, 4)
    cell_cm = st.number_input("Raster (cm/Zelle)", 10, 50, cell_cm_default, 5)
    cell_px = st.slider("Zell-Pixel (Zoom)", 4, 12, cell_px_default, 1)

    # Kühlsattel-Puffer
    st.subheader("🚛 Laderaum & Puffer")
    c1, c2, c3 = st.columns(3)
    with c1:
        front_buf = st.number_input("Front-Puffer (cm)", 0, 60, 0, 1)
    with c2:
        back_buf = st.number_input("Heck-Puffer (cm)", 0, 60, 0, 1)
    with c3:
        l_nominal = st.number_input("Nominal-Länge (cm)", 1000, 1500, TRAILER_L_CM, 10)

    l_eff = max(0, l_nominal - front_buf - back_buf)
    st.caption(f"Effektive Laderaumlänge **L_eff = {l_eff} cm** (von {l_nominal} cm)")

    # --- Mengen / Gewichte ---
    st.subheader("📦 Paletten & Gewichte")
    c4, c5, c6, c7 = st.columns(4)
    with c4:
        n_euro = st.number_input("Euro (120×80)", 0, 45, 30, 1)
    with c5:
        n_ind = st.number_input("Industrie/IBC (100×120 quer)", 0, 30, 0, 1)
    with c6:
        cross_offset = st.slider("Feinjustierung Quer (Zeilen-Offset)", -3, 3, 0, 1)
    with c7:
        weight_mode = st.toggle("Gewichtsmodus (Achslast optimieren)", value=False, help="Zeigt gewichtsoptimierte Varianten.")

    # Gewichtsmodus-Optionen
    heavy_back = True
    if weight_mode:
        heavy_back = st.radio("Schwer eher hinten?", ["Ja (empfohlen)", "Nein (vorne)"], index=0) == "Ja (empfohlen)"

    # --- Variantenliste (inkl. Gewicht) ---
    base_variants = ["V1 Quer-lastig", "V2 Längs-lastig", "V3 Nur längs (3-Spur)", "V4 Nur quer (+ Tail)"]
    variants: List[str] = base_variants.copy()

    if weight_mode:
        # Dupliziere Basismuster als „Gewicht-Optimiert“
        variants.extend([v + " – Gewichtsvariante" for v in base_variants])

    # Testfälle
    with st.expander("🧪 Schnelltests (füllt Eingaben)", expanded=False):
        t = st.selectbox(
            "Szenario wählen",
            ["–", "Euro 20", "Euro 21", "Euro 23", "Euro 24", "Euro 29", "Euro 30", "Euro 31", "Euro 32", "Euro 33", "Mix: 24 Euro + 4 Industrie"],
            index=0,
        )
        if t != "–":
            if "Euro" in t and "Mix" not in t:
                n_euro = int(t.split()[1])
                n_ind = 0
            elif t.startswith("Mix"):
                n_euro, n_ind = 24, 4
            st.info(f"Testfall gesetzt: Euro={n_euro}, Industrie/IBC={n_ind}")

    # Varianten-Karussell
    if "var_idx" not in st.session_state:
        st.session_state.var_idx = 0

    nav1, nav2, nav3 = st.columns([1, 1, 3])
    with nav1:
        if st.button("◀ Variante"):
            st.session_state.var_idx = (st.session_state.var_idx - 1) % len(variants)
    with nav2:
        if st.button("Variante ▶"):
            st.session_state.var_idx = (st.session_state.var_idx + 1) % len(variants)
    with nav3:
        st.markdown(f"**Variante:** {st.session_state.var_idx + 1} / {len(variants)} – {variants[st.session_state.var_idx]}")

    # Baue aktuelle Variante
    variant_name = variants[st.session_state.var_idx]
    is_weighted = "Gewichtsvariante" in variant_name
    active_variant = variant_name.replace(" – Gewichtsvariante", "")

    board, n_euro_rest = build_variant(
        l_eff_cm=l_eff,
        cell_cm=cell_cm,
        n_euro=n_euro,
        n_ind=n_ind,
        variant=active_variant,
        cross_offset=cross_offset,
        heavy_back=(heavy_back if (weight_mode or is_weighted) else True),
    )

    # Darstellung (Expander auf/zu)
    with st.expander("📋 Ladeplan anzeigen", expanded=True):
        render_board(board, cell_px=cell_px)

    # Status / Kennzahlen
    used_cm = used_length_cm(board.items, cell_cm)
    pct = (used_cm / l_eff) if l_eff else 0.0
    front_pct, back_pct = estimate_axle_balance(board.items, cell_cm, l_eff)

    cols = st.columns(3)
    with cols[0]:
        st.markdown(f"**Genutzte Länge:** {used_cm} cm von {l_eff} cm (≈ {pct:.0%})")
    with cols[1]:
        st.markdown(f"**Achslast-Schätzung:** vorn {front_pct}% / hinten {back_pct}%")
    with cols[2]:
        if n_euro > 0 and n_euro_rest > 0:
            st.error(f"🚫 **{n_euro_rest}× Euro** passen nicht mehr.")
        else:
            st.success("✅ **Alle Euro-Paletten platziert.**")
        if n_ind > 0:
            # grobe Prüfung: gezählte Blöcke ⬜
            placed_ind = sum(1 for *_, ch in board.items if ch == CHAR_IND)
            missing_ind = max(0, n_ind - placed_ind)
            if missing_ind > 0:
                st.error(f"🚫 **{missing_ind}× Industrie/IBC** passen nicht mehr.")
            else:
                st.success("✅ **Alle Industrie/IBC platziert.**")

    # Hinweise
    st.info(
        "Hinweis: Ceil‑Rasterung aktiv. Quer‑Offset bewirkt rein optische Feinkorrektur. "
        "Bei 33 Euro im Kühlsattel wird **kein** unrealistisches Voll‑Quer erzeugt – "
        "stattdessen sinnvoller Tail‑Abschluss."
    )


if __name__ == "__main__":
    main()
