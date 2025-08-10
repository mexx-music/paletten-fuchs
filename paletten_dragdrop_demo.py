# app.py — Pal Fuchs: Varianten, Gewichtsmodus & Heavy-Presets 21/22/23/24
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict
import streamlit as st

# ---------- TRAILER & PAL CONSTANTS ----------
TRAILER_L = 1360  # cm (innen)
TRAILER_W = 245   # cm

EURO_DEPTH_LONG = 120  # cm
EURO_WIDTH_LONG = 80   # cm
EURO_DEPTH_CROSS = 80  # cm
EURO_WIDTH_CROSS = 120 # cm

INDUSTRIE_DEPTH = 100  # cm
INDUSTRIE_WIDTH = 120  # cm

EURO_NORMAL_KG = 250
EURO_HEAVY_KG  = 400
INDUSTRIE_LIGHT_WEIGHT = 600
INDUSTRIE_HEAVY_WEIGHT = 1100  # IBC

# UI Defaults
DEFAULT_CELL_CM  = 40
DEFAULT_CELL_PX  = 6
DEFAULT_AUTO_ZOOM = False
DEFAULT_FRONT_BUFFER = 20
DEFAULT_REAR_BUFFER  = 0

@dataclass
class PalletType:
    name: str
    depth_long: int
    width_long: int
    depth_cross: int
    width_cross: int
    default_weight: int

EURO = PalletType("Euro",
                  EURO_DEPTH_LONG, EURO_WIDTH_LONG,
                  EURO_DEPTH_CROSS, EURO_WIDTH_CROSS,
                  EURO_NORMAL_KG)
IND  = PalletType("Industrie",
                  INDUSTRIE_DEPTH, INDUSTRIE_WIDTH,
                  INDUSTRIE_DEPTH,  INDUSTRIE_WIDTH,
                  INDUSTRIE_LIGHT_WEIGHT)

class PalFuchs:
    def __init__(self, cell_cm: int, cell_px: int, auto_zoom: bool,
                 front_buffer: int, rear_buffer: int):
        self.cell_cm = cell_cm
        self.cell_px = cell_px
        self.auto_zoom = auto_zoom
        self.front_buffer = front_buffer
        self.rear_buffer  = rear_buffer
        self._compute_grid()

    # ---- Grid helpers ----
    def _ceil_div(self, a, b): return -(-a // b)

    def _compute_grid(self):
        self.X = self._ceil_div(TRAILER_L, self.cell_cm)
        self.Y = self._ceil_div(TRAILER_W, self.cell_cm)
        if self.auto_zoom:
            self.cell_px = max(4, min(20, round(820 / self.X)))
        self.x_off = self._ceil_div(self.front_buffer, self.cell_cm) if self.front_buffer > 0 else 0
        self.effective_length = max(0, TRAILER_L - self.front_buffer - self.rear_buffer)

    def span_cells(self, depth_cm: int, width_cm: int) -> Tuple[int,int]:
        return self._ceil_div(depth_cm, self.cell_cm), self._ceil_div(width_cm, self.cell_cm)

    def long_lanes(self) -> List[int]:
        _, dy = self.span_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        total_gap = max(0, self.Y - 3*dy)
        g = total_gap // 4
        r = total_gap % 4
        gaps = [g,g,g,g]
        for i in range(r): gaps[i]+=1
        y1 = gaps[0]
        y2 = y1 + dy + gaps[1]
        y3 = y2 + dy + gaps[2]
        return [y1, y2, min(y3, max(0, self.Y - dy))]

    def center_in_band(self, band_y: int, band_h: int, h: int) -> int:
        return max(0, min(band_y + max(0, (band_h - h)//2), max(0, self.Y - h)))

    # ---- Board state ----
    def empty(self):
        occ = [[False]*self.X for _ in range(self.Y)]
        return occ, [], {"Euro":0,"Industrie":0,"IBC":0}  # items: (x,y,dx,dy,typ,ori,kg)

    def is_free(self, occ, x,y,dx,dy) -> bool:
        if x<0 or y<0 or x+dx>self.X or y+dy>self.Y: return False
        for yy in range(y,y+dy):
            for xx in range(x,x+dx):
                if occ[yy][xx]: return False
        return True

    def place(self, occ, items, placed, x,y,dx,dy,typ,ori,kg):
        for yy in range(y,y+dy):
            for xx in range(x,x+dx):
                occ[yy][xx] = True
        items.append((x,y,dx,dy,typ,ori,kg))
        placed[typ] = placed.get(typ,0)+1

    # ---- Column placers ----
    def place_euro_column(self, occ, items, placed, x, count, orient, euro_kg) -> int:
        if orient=="long":
            dx,dy = self.span_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
            lanes = self.long_lanes()
        else:
            dx,dy = self.span_cells(EURO_DEPTH_CROSS, EURO_WIDTH_CROSS)
            lanes_long = self.long_lanes()
            _, dy_l = self.span_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
            lanes = [ self.center_in_band(lanes_long[i], dy_l, dy) for i in (0,1,2) ]
        if x+dx>self.X: return 0
        placed_in_col = 0
        if count==1 and len(lanes)>=2:
            y=lanes[1]
            if self.is_free(occ,x,y,dx,dy):
                self.place(occ,items,placed,x,y,dx,dy,"Euro",orient,euro_kg); return 1
        if count>=2 and len(lanes)>=3:
            for y in [lanes[0], lanes[2]]:
                if placed_in_col<2 and self.is_free(occ,x,y,dx,dy):
                    self.place(occ,items,placed,x,y,dx,dy,"Euro",orient,euro_kg)
                    placed_in_col+=1
            if placed_in_col: return placed_in_col
        if count>=3:
            for y in lanes:
                if placed_in_col<3 and self.is_free(occ,x,y,dx,dy):
                    self.place(occ,items,placed,x,y,dx,dy,"Euro",orient,euro_kg)
                    placed_in_col+=1
        return placed_in_col

    def fill_euro_full(self, occ, items, placed, x, euro_left, orient, euro_kg):
        dx,_ = self.span_cells(*( (EURO_DEPTH_LONG, EURO_WIDTH_LONG) if orient=="long"
                                  else (EURO_DEPTH_CROSS,EURO_WIDTH_CROSS)))
        while euro_left>=3 and x+dx<=self.X:
            c = self.place_euro_column(occ,items,placed,x,3,orient,euro_kg)
            if c==3: euro_left-=3; x+=dx
            else: break
        return x, euro_left

    def tail_close_euro(self, occ, items, placed, x, euro_left, euro_kg) -> int:
        if euro_left<=0: return 0
        # 1) try 3 long, else 3 cross
        for orient in ("long","cross"):
            if euro_left>=3:
                c = self.place_euro_column(occ,items,placed,x,3,orient,euro_kg)
                if c==3: return 3
        # 2) try 2 long, else 2 cross
        for orient in ("long","cross"):
            if euro_left>=2:
                c = self.place_euro_column(occ,items,placed,x,2,orient,euro_kg)
                if c>0: return c
        # 3) single: **always cross center**, last resort long
        c = self.place_euro_column(occ,items,placed,x,1,"cross",euro_kg)
        if c==1: return 1
        return self.place_euro_column(occ,items,placed,x,1,"long",euro_kg)

    def block_industry_pairs(self, occ, items, placed, n_light, n_ibc) -> int:
        """Fill columns left→right; each column: TOP+BOTTOM.
           Light first, then IBC. Singles werden hinten (BOTTOM) gesetzt."""
        dx_i, dy_i = self.span_cells(INDUSTRIE_DEPTH, INDUSTRIE_WIDTH)
        lanes_long = self.long_lanes()
        _, dy_l = self.span_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        top_y = self.center_in_band(lanes_long[0], dy_l, dy_i)
        bot_y = self.center_in_band(lanes_long[2], dy_l, dy_i)

        x = self.x_off
        def try_put(y, typ, kg):
            if self.is_free(occ,x,y,dx_i,dy_i):
                self.place(occ,items,placed,x,y,dx_i,dy_i,typ,"cross",kg); return True
            return False

        # Light first
        while n_light>0 and x+dx_i<=self.X:
            filled=0
            for y in [top_y, bot_y]:
                if n_light>0 and try_put(y,"Industrie",INDUSTRIE_LIGHT_WEIGHT):
                    n_light-=1; filled+=1
            if filled: x+=dx_i
            else: x+=1

        # Then IBC heavy (prefer BOTTOM → then TOP). Singles gehen auf BOTTOM.
        while n_ibc>0 and x+dx_i<=self.X:
            filled=0
            for y in [bot_y, top_y]:
                if n_ibc>0 and try_put(y,"IBC",INDUSTRIE_HEAVY_WEIGHT):
                    n_ibc-=1; filled+=1
            if filled: x+=dx_i
            else: x+=1

        return x

    # ---- Variants ----
    def generate_variants(self, n_euro:int, n_light:int, n_ibc:int, euro_kg:int):
        variants=[]
        gens=[self._v_cross_heavy, self._v_long_heavy, self._v_only_long, self._v_mixed, self._v_balanced]
        names=["Cross-heavy","Long-heavy","Only long","Mixed lanes","Balanced"]
        for name,gen in zip(names,gens):
            occ,items,placed = self.empty()
            x = self.block_industry_pairs(occ,items,placed,n_light,n_ibc) if (n_light or n_ibc) else self.x_off
            gen(occ,items,placed,x,n_euro,euro_kg)
            variants.append((items,placed,name))
        return variants

    def _v_cross_heavy(self, occ,items,placed,x,n,euro_kg):
        dx,_ = self.span_cells(EURO_DEPTH_CROSS, EURO_WIDTH_CROSS)
        while n>=2 and x+dx<=self.X:
            c = self.place_euro_column(occ,items,placed,x,2,"cross",euro_kg)
            if c>0: n-=c; x+=dx
            else: break
        while n>0 and x<self.X:
            c = self.tail_close_euro(occ,items,placed,x,n,euro_kg)
            if c<=0: break
            n-=c; x+=dx

    def _v_long_heavy(self, occ,items,placed,x,n,euro_kg):
        x,n = self.fill_euro_full(occ,items,placed,x,n,"long",euro_kg)
        dx,_ = self.span_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        while n>0 and x<self.X:
            c=self.tail_close_euro(occ,items,placed,x,n,euro_kg)
            if c<=0: break
            n-=c; x+=dx

    def _v_only_long(self, occ,items,placed,x,n,euro_kg):
        dx,_ = self.span_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        while n>0 and x+dx<=self.X:
            c=self.place_euro_column(occ,items,placed,x,min(3,n),"long",euro_kg)
            if c>0: n-=c; x+=dx
            else: break

    def _v_mixed(self, occ,items,placed,x,n,euro_kg):
        dxL,_ = self.span_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        dxQ,_ = self.span_cells(EURO_DEPTH_CROSS, EURO_WIDTH_CROSS)
        while n>0 and x<self.X:
            c=self.place_euro_column(occ,items,placed,x,min(3,n),"long",euro_kg)
            if c>0: n-=c; x+=dxL; continue
            c=self.place_euro_column(occ,items,placed,x,min(2,n),"cross",euro_kg)
            if c>0: n-=c; x+=dxQ; continue
            x+=1

    def _v_balanced(self, occ,items,placed,x,n,euro_kg):
        dxL,_ = self.span_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        dxQ,_ = self.span_cells(EURO_DEPTH_CROSS, EURO_WIDTH_CROSS)
        use_long=True
        while n>0 and x<self.X:
            if use_long and x+dxL<=self.X:
                c=self.place_euro_column(occ,items,placed,x,min(3,n),"long",euro_kg)
                if c>0: n-=c; x+=dxL; use_long=False; continue
            if (not use_long) and x+dxQ<=self.X:
                c=self.place_euro_column(occ,items,placed,x,min(2,n),"cross",euro_kg)
                if c>0: n-=c; x+=dxQ; use_long=True; continue
            # fallback
            c=self.place_euro_column(occ,items,placed,x,min(3,n),"long",euro_kg)
            if c>0: n-=c; x+=dxL; continue
            x+=1

    # ---- Deterministische Front-Rezepte 24/23/22/21 (schwer optimiert) ----
    def recipe_front(self, n_euro:int, n_light:int, n_ibc:int, euro_kg:int):
        """Explizite Muster:
           24: 8× (3 long)
           23: 1× (2 cross außen) + 7× (3 long)
           22: 1× (1 cross mittig) + 7× (3 long)
           21: 7× (3 long)
           Sonst: generische n%3‑Variante (quer seed → long → tail)"""
        occ,items,placed = self.empty()
        x = self.block_industry_pairs(occ,items,placed,n_light,n_ibc) if (n_light or n_ibc) else self.x_off
        dxL,_ = self.span_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        dxQ,_ = self.span_cells(EURO_DEPTH_CROSS, EURO_WIDTH_CROSS)

        def seed_cross(count):
            nonlocal x, n_euro
            if count<=0: return
            c = self.place_euro_column(occ,items,placed,x,count,"cross",euro_kg)
            if c>0:
                n_euro -= c
                x += dxQ

        if n_euro==24:
            # 8 volle Längs-Spalten
            x, n_euro = self.fill_euro_full(occ,items,placed,x,n_euro,"long",euro_kg)
            name="Recipe 24 = 8×(3 long)"
        elif n_euro==23:
            seed_cross(2)                       # 2 quer außen
            x, n_euro = self.fill_euro_full(occ,items,placed,x,n_euro,"long",euro_kg)
            name="Recipe 23 = 2 cross + 7×(3 long)"
        elif n_euro==22:
            seed_cross(1)                       # 1 quer mittig
            x, n_euro = self.fill_euro_full(occ,items,placed,x,n_euro,"long",euro_kg)
            name="Recipe 22 = 1 cross + 7×(3 long)"
        elif n_euro==21:
            x, n_euro = self.fill_euro_full(occ,items,placed,x,n_euro,"long",euro_kg)
            name="Recipe 21 = 7×(3 long)"
        else:
            # generisches Rezept nach Restklasse
            rem = n_euro % 3
            if rem==2: seed_cross(2)
            elif rem==1: seed_cross(1)
            x, n_euro = self.fill_euro_full(occ,items,placed,x,n_euro,"long",euro_kg)
            while n_euro>0 and x<self.X:
                c=self.tail_close_euro(occ,items,placed,x,n_euro,euro_kg)
                if c<=0: break
                n_euro-=c; x+=dxL
            name=f"Recipe n%3={rem}"

        return (items, placed, name)

    # ---- Metrics / Render ----
    def used_len_cm(self, items) -> int:
        if not items: return 0
        x_end = max(x+dx for (x,y,dx,dy,typ,ori,kg) in items)
        return int(x_end * self.cell_cm)

    def estimate_balance(self, items):
        if not items: return 50,50
        total=0.0; front_moment=0.0
        for (x,y,dx,dy,typ,ori,kg) in items:
            x_cm = self.front_buffer + x*self.cell_cm + (dx*self.cell_cm)/2
            eff = self.effective_length if self.effective_length>0 else TRAILER_L
            pos = max(0.0, 1.0 - (x_cm - self.front_buffer)/max(1.0, eff))
            total += kg
            front_moment += kg*pos
        if total<=0: return 50,50
        f = int(round(100*front_moment/total))
        return f, 100-f

    def render_html(self, items, flip=False):
        html = f"""
        <div style='display:grid;
          grid-template-columns: repeat({self.X}, {self.cell_px}px);
          grid-auto-rows: {self.cell_px}px;
          gap:1px; background:#ddd; padding:6px; border:2px solid #333; width:fit-content;'>
        """
        # Buffers
        rear_cells = self._ceil_div(DEFAULT_REAR_BUFFER, self.cell_cm) if DEFAULT_REAR_BUFFER>0 else 0
        if not flip:
            if self.x_off>0:
                html += f"<div style='grid-column:1/span {self.x_off}; grid-row:1/span {self.Y}; background:#f3f3f3; border:1px dashed #999;'></div>"
            if rear_cells>0:
                start = self.X - rear_cells + 1
                html += f"<div style='grid-column:{start}/span {rear_cells}; grid-row:1/span {self.Y}; background:#f3f3f3; border:1px dashed #999;'></div>"
        else:
            if self.x_off>0:
                start = self.X - self.x_off + 1
                html += f"<div style='grid-column:{start}/span {self.x_off}; grid-row:1/span {self.Y}; background:#f3f3f3; border:1px dashed #999;'></div>"
            if rear_cells>0:
                html += f"<div style='grid-column:1/span {rear_cells}; grid-row:1/span {self.Y}; background:#f3f3f3; border:1px dashed #999;'></div>"

        # items
        for (x,y,dx,dy,typ,ori,kg) in items:
            bg = "#e3f2fd" if (typ=="Euro" and ori=="long") else ("#e8f5e9" if typ=="Euro" else "#ffe0b2")
            col = (self.X-(x+dx)+1) if flip else (x+1)
            html += f"<div style='grid-column:{col}/span {dx}; grid-row:{y+1}/span {dy}; background:{bg}; border:1px solid #777;'></div>"
        html += "</div>"
        return html

# ---------- STREAMLIT UI ----------
st.set_page_config(page_title="🦊 Pal Fuchs – Varianten & Achslast", layout="wide")
st.title("🦊 Pal Fuchs – Varianten & Gewichtsmodus")

with st.sidebar:
    st.markdown("### ⚙️ Anzeige")
    cell_cm  = st.slider("Raster (cm/Zelle)", 20, 50, DEFAULT_CELL_CM, 5, key="cfg_cell_cm")
    autozoom = st.checkbox("Auto‑Zoom auf konstante Breite", DEFAULT_AUTO_ZOOM, key="cfg_auto_zoom")
    cell_px  = st.slider("Zell‑Pixel", 4, 20, DEFAULT_CELL_PX, 1, disabled=autozoom, key="cfg_cell_px")

    st.markdown("---")
    st.markdown("### 🚛 Kühlsattel (Standard)")
    st.info(f"Front-Puffer: {DEFAULT_FRONT_BUFFER} cm\nHeck-Puffer: {DEFAULT_REAR_BUFFER} cm")

    st.markdown("---")
    st.markdown("### 📦 Euro Gewicht")
    st.radio("Euro weight", ["normal","heavy"], index=1, key="cfg_euro_w")  # default heavy

    st.markdown("---")
    weight_mode = st.checkbox("⚖️ Gewichtsmodus aktivieren (sort by axle balance)", False, key="cfg_weight")
    flip_view   = st.checkbox("Ansicht spiegeln (Front rechts)", False, key="cfg_flip")

# init core
fuchs = PalFuchs(cell_cm=cell_cm, cell_px=cell_px, auto_zoom=autozoom,
                 front_buffer=DEFAULT_FRONT_BUFFER, rear_buffer=DEFAULT_REAR_BUFFER)

euro_kg = EURO_HEAVY_KG if st.session_state.get("cfg_euro_w","heavy")=="heavy" else EURO_NORMAL_KG

# Eingaben
st.markdown("### Eingaben")
c1,c2,c3,c4 = st.columns([1.1,1.1,1.1,1.4])
with c1: n_euro = st.number_input("Euro (120×80)", 0, 45, 24, key="n_euro")
with c2: n_indL = st.number_input("Industrie leicht", 0, 30, 0, key="n_industrie_light")
with c3: n_ibc  = st.number_input("IBC schwer", 0, 30, 0, key="n_industrie_heavy")

with c4:
    st.caption("Heavy‑Presets")
    b21,b22,b23,b24 = st.columns(4)
    with b21:
        if st.button("21H"): st.session_state.n_euro=21; st.session_state.cfg_euro_w="heavy"
    with b22:
        if st.button("22H"): st.session_state.n_euro=22; st.session_state.cfg_euro_w="heavy"
    with b23:
        if st.button("23H"): st.session_state.n_euro=23; st.session_state.cfg_euro_w="heavy"
    with b24:
        if st.button("24H"): st.session_state.n_euro=24; st.session_state.cfg_euro_w="heavy"

# Varianten + Rezepte
variants = fuchs.generate_variants(int(st.session_state.n_euro),
                                   int(st.session_state.n_industrie_light),
                                   int(st.session_state.n_industrie_heavy),
                                   euro_kg)

# deterministisches Front‑Rezept zusätzlich (immer heavy‑kompatibel)
recipe = fuchs.recipe_front(int(st.session_state.n_euro),
                            int(st.session_state.n_industrie_light),
                            int(st.session_state.n_industrie_heavy),
                            euro_kg)
variants.append(recipe)  # (items, placed, name)

# Sortierung nach Achslast wenn gewünscht
if weight_mode:
    def score(v):
        items,_,_ = v
        f,r = fuchs.estimate_balance(items)
        return abs(f-50)
    variants.sort(key=score)

# Navigation
if "v_idx" not in st.session_state: st.session_state.v_idx=0
nav1,nav2 = st.columns(2)
with nav1:
    if st.button("◀ Vorherige Variante", use_container_width=True):
        st.session_state.v_idx = (st.session_state.v_idx-1) % len(variants)
with nav2:
    if st.button("Nächste Variante ▶", use_container_width=True):
        st.session_state.v_idx = (st.session_state.v_idx+1) % len(variants)

items, placed, name = variants[st.session_state.v_idx]
st.markdown(f"**Variante:** {st.session_state.v_idx+1} / {len(variants)} – {name} "
            f"[{st.session_state.get('cfg_euro_w','heavy')} Euro: {euro_kg} kg]")

# Render
board_html = fuchs.render_html(items, flip_view)
height_px  = min(680, max(240, (fuchs.cell_px+1)*fuchs.Y + 28))
st.components.v1.html(board_html, height=height_px, scrolling=False)

# Status
used_cm = fuchs.used_len_cm(items)
st.markdown(f"**Genutzte Länge:** {used_cm} cm von {TRAILER_L} cm (≈ {used_cm/TRAILER_L:.0%})")
f_pct, r_pct = fuchs.estimate_balance(items)
st.markdown(f"**Achslast‑Schätzung:** vorne {f_pct}% / hinten {r_pct}%")
st.markdown(f"**Effektive Länge:** {fuchs.effective_length} cm (mit Kühlsattel‑Puffern)")

with st.expander("🔎 Legende / Hinweise"):
    st.markdown(
        "- **Farben:** Euro längs = hellblau, Euro quer = hellgrün, Industrie/IBC = orange\n"
        "- **Presets:** Buttons 21H/22H/23H/24H setzen schwere Euro & passendes Rezept.\n"
        "- **Remainder‑Logik:** Quer zuerst (Mitte bzw. außen), dann 3er‑Längsspalten, kein einzelner Längs‑Euro am Start.\n"
        "- **Industrie/IBC:** Immer paarweise pro Spalte (oben+unten). Einzelne schwere Paletten landen hinten (BOTTOM).\n"
        "- Achslast ist eine vereinfachte Schätzung – zur Orientierung."
    )
