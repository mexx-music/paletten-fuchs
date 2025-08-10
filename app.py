# pal_fuchs9_icon_final.py
# 🦊 Pal Fuchs 9 – Icon-Version (Kühler fix, 3-Quer-Reihen fix, Tail-Fix, Raster 25cm)
import streamlit as st

class PalFuchsApp:
    # ---------- Feste Kühler-Geometrie ----------
    TRAILER_L_NOM, TRAILER_W = 1360, 245    # cm, Kühlsattel fix
    FRONT_BUF_CM, BACK_BUF_CM = 0, 0        # aktuell fix; bei Bedarf später UI

    # ---------- Icons ----------
    ICON = {
        ("Euro","l"): "icons/euro_l.png",
        ("Euro","q"): "icons/euro_q.png",
        ("Industrie","q"): "icons/ind_q.png",
        ("Blume","l"): "icons/flower_l.png",
        ("Blume","q"): "icons/flower_q.png",
    }

    def __init__(self):
        # UI/State
        self.cell_cm = 25          # Raster fix
        self.cell_px = 4           # Zoom einstellbar
        self.allow_euro_cross_in_lanes = False
        self.n_euro = 30
        self.n_ind  = 0

        # Grid
        self.X = None  # columns (entlang Länge)
        self.Y = None  # rows (quer)
        self.L_EFF = None

        # Variant result
        self.items = []     # (x,y,dx,dy,icon,typ)
        self.placed = {}    # counts per type

    # ---------- Run ----------
    def run(self):
        self.setup_page()
        self.layout_sidebar()
        self.compute_grid()
        var_idx, variants = self.layout_controls_and_build_variants()
        self.items, self.placed = variants[var_idx]
        self.render_board()
        self.render_status()

    # ---------- Page ----------
    def setup_page(self):
        st.set_page_config(page_title="🦊 PAL Fuchs 9 – Icon-Version (fix Kühler)", layout="wide")
        st.title("🦊 PAL Fuchs 9 – Icon-Version (fix Kühler)")

    def layout_sidebar(self):
        st.sidebar.markdown("### ⚙️ Einstellungen")
        # Raster ist fix 25 cm (wie gewünscht)
        st.sidebar.markdown("**Raster:** 25 cm/Zelle (fix)")
        self.cell_px = st.sidebar.slider("Zell‑Pixel (Zoom)", 4, 14, self.cell_px, 1)
        self.allow_euro_cross_in_lanes = st.sidebar.checkbox(
            "Euro auch **quer in Spuren** zulassen", value=False,
            help="Erlaubt Quer in den drei Längsspuren – nur falls gewünscht."
        )

    def compute_grid(self):
        # Effektive Länge (aktuell ohne einstellbare Puffer – fix Kühler)
        self.L_EFF = max(0, self.TRAILER_L_NOM - self.FRONT_BUF_CM - self.BACK_BUF_CM)
        self.X = max(1, self.L_EFF // self.cell_cm)
        self.Y = max(1, self.TRAILER_W // self.cell_cm)

    def layout_controls_and_build_variants(self):
        st.subheader("📦 Paletten & Gewichte")
        c1,c2,c3 = st.columns([1.2,1.2,1.6])
        with c1:
            self.n_euro = int(st.number_input("Euro (120×80)", 0, 45, self.n_euro))
        with c2:
            self.n_ind  = int(st.number_input("Industrie (120×100)", 0, 30, self.n_ind))
        with c3:
            st.caption("Varianten unten durchblättern")

        variants = self.generate_variants(
            n_euro=self.n_euro,
            n_ind=self.n_ind,
            allow_euro_cross_in_lanes=self.allow_euro_cross_in_lanes
        )

        # Navigation
        if "var_idx" not in st.session_state: st.session_state.var_idx = 0
        nav1,nav2,nav3 = st.columns([1,1,3])
        with nav1:
            if st.button("◀ Variante"):
                st.session_state.var_idx = (st.session_state.var_idx - 1) % len(variants)
        with nav2:
            if st.button("Variante ▶"):
                st.session_state.var_idx = (st.session_state.var_idx + 1) % len(variants)
        with nav3:
            st.markdown(f"**Variante:** {st.session_state.var_idx+1} / {len(variants)}")

        # Anzeige einklappbar
        st.markdown("—")
        return st.session_state.var_idx, variants

    # ---------- Geometry ----------
    def span(self, name, ori):
        if name == "Euro":        L,B = 120, 80
        elif name == "Industrie": L,B = 120,100
        else:                     L,B = 135, 55  # Demo
        if name == "Industrie":
            ori = "q"  # Industrie immer quer
        if ori == "q":
            depth_cm, width_cm = B, L
        else:
            depth_cm, width_cm = L, B
        dx = max(1, depth_cm // self.cell_cm)   # entlang Trailer-Länge (x)
        dy = max(1, width_cm // self.cell_cm)   # quer im Trailer (y)
        return dx, dy

    def three_rows_fixed(self, h):
        """Stabile 3-Quer-Reihen (oben / exakt Mitte / unten), ohne Rundungsdrift."""
        top = 0
        mid = max(0, (self.Y - h) // 2)
        bot = self.Y - h
        # Duplikate vermeiden (kleine Höhen)
        rows = []
        for y in (top, mid, bot):
            if y not in rows:
                rows.append(y)
        return rows

    def center_y(self, dy):
        return max(0, (self.Y - dy) // 2)

    def empty_board(self):
        occupied = [[False]*self.X for _ in range(self.Y)]
        items = []
        placed = {"Euro":0, "Industrie":0, "Blume":0}
        return occupied, items, placed

    # ---------- Occupancy ----------
    def free(self, occ, x,y,dx,dy):
        if x<0 or y<0 or x+dx>self.X or y+dy>self.Y: return False
        for yy in range(y,y+dy):
            for xx in range(x,x+dx):
                if occ[yy][xx]: return False
        return True

    def place(self, occ, items, placed, x,y,dx,dy,icon,typ):
        for yy in range(y,y+dy):
            for xx in range(x,x+dx):
                occ[yy][xx] = True
        items.append((x,y,dx,dy,icon,typ))
        placed[typ] += 1

    def first_free_x(self, occ):
        for xx in range(self.X):
            if any(not occ[yy][xx] for yy in range(self.Y)): return xx
        return self.X

    def used_length_cm(self, items):
        if not items: return 0
        x_end = max(x+dx for (x,y,dx,dy,icon,typ) in items)
        return x_end * self.cell_cm

    # ---------- Heckabschluss (sauber) ----------
    def tail_close_clean_euro(self, occ, items, placed, x_start, euro_left):
        if euro_left <= 0: return 0
        dq,wq = self.span("Euro","q")
        dl,wl = self.span("Euro","l")

        x = x_start

        # 1) Bevorzugt 3x längs (wenn exakt Platz vorhanden)
        if euro_left >= 3 and x + dl <= self.X:
            ok = True
            for y in self.three_rows_fixed(wl):
                if not self.free(occ, x,y,dl,wl):
                    ok = False; break
            if ok:
                for y in self.three_rows_fixed(wl):
                    self.place(occ, items, placed, x,y,dl,wl, self.ICON[("Euro","l")], "Euro")
                return euro_left - 3

        # 2) Sonst 2x quer außen
        placed_here = 0
        if euro_left >= 1 and x + dq <= self.X and self.free(occ, x,0,dq,wq):
            self.place(occ, items, placed, x,0,dq,wq, self.ICON[("Euro","q")], "Euro")
            euro_left -= 1; placed_here += 1
        if euro_left >= 1 and x + dq <= self.X and self.free(occ, x,self.Y-wq,dq,wq):
            self.place(occ, items, placed, x,self.Y-wq,dq,wq, self.ICON[("Euro","q")], "Euro")
            euro_left -= 1; placed_here += 1
        if placed_here:
            return euro_left

        # 3) Notfall: 1x längs mittig
        if euro_left >= 1 and x + dl <= self.X and self.free(occ, x,self.center_y(wl),dl,wl):
            self.place(occ, items, placed, x,self.center_y(wl),dl,wl, self.ICON[("Euro","l")], "Euro")
            euro_left -= 1
        return euro_left

    # ---------- Blocks / Strategien ----------
    def block_industrie_all(self, occ, items, placed, n):
        dq,wq = self.span("Industrie","q")
        x=0
        # ungerade → 1 mittig zuerst
        if n%2==1:
            y=self.center_y(wq)
            if self.free(occ, x,y,dq,wq):
                self.place(occ, items, placed, x,y,dq,wq, self.ICON[("Industrie","q")], "Industrie")
                n -= 1; x += dq
        # Paare links+rechts
        while n>0 and x+dq<=self.X:
            for y in [0, self.Y-wq]:
                if n>0 and self.free(occ, x,y,dq,wq):
                    self.place(occ, items, placed, x,y,dq,wq, self.ICON[("Industrie","q")], "Industrie")
                    n -= 1
            x += dq
        return x

    def block_euro_only_long(self, occ, items, placed, x_start, n):
        dl,wl = self.span("Euro","l")
        lanes = self.three_rows_fixed(wl)
        x = x_start
        while n>0 and x+dl<=self.X:
            for y in lanes:
                if n>0 and self.free(occ, x,y,dl,wl):
                    self.place(occ, items, placed, x,y,dl,wl, self.ICON[("Euro","l")], "Euro")
                    n -= 1
            x += dl
        return n

    def block_euro_cross_then_long(self, occ, items, placed, x_start, n):
        dq,wq = self.span("Euro","q")
        dl,wl = self.span("Euro","l")
        x = x_start
        # Querblöcke spaltenweise mit 3 stabilen Reihen
        while n>=3 and x+dq<=self.X:
            filled = 0
            for y in self.three_rows_fixed(wq):
                if n>0 and self.free(occ, x,y,dq,wq):
                    self.place(occ, items, placed, x,y,dq,wq, self.ICON[("Euro","q")], "Euro")
                    n -= 1; filled += 1
            x += dq if filled>0 else 1
        # Rest sauber schließen
        return self.tail_close_clean_euro(occ, items, placed, x, n)

    def block_euro_long_then_cross_tail(self, occ, items, placed, x_start, n):
        dl,wl = self.span("Euro","l")
        lanes = self.three_rows_fixed(wl)
        x = x_start
        col_cap = 3
        while n >= col_cap and x+dl <= self.X:
            ok = True
            for y in lanes:
                if not self.free(occ, x,y,dl,wl): ok=False; break
            if ok:
                for y in lanes:
                    self.place(occ, items, placed, x,y,dl,wl, self.ICON[("Euro","l")], "Euro")
                n -= col_cap
                x += dl
            else:
                break
        return self.tail_close_clean_euro(occ, items, placed, x, n)

    # NEW: Fülle Längsspuren mit optional quer (wenn erlaubt)
    def block_euro_fill_lanes_mixed(self, occ, items, placed, x_start, n, allow_cross):
        if n <= 0: return
        dl,wl = self.span("Euro","l")
        dq,wq = self.span("Euro","q")
        lanes_long = self.three_rows_fixed(wl)
        lanes_cross = self.three_rows_fixed(wq)
        x = x_start
        while n>0 and x < self.X:
            progressed = False
            filled_this_col = 0
            # längs bevorzugt
            if x + dl <= self.X:
                for y in lanes_long:
                    if n>0 and self.free(occ, x,y,dl,wl):
                        self.place(occ, items, placed, x,y,dl,wl, self.ICON[("Euro","l")], "Euro")
                        n -= 1; filled_this_col += 1
                if filled_this_col>0:
                    x += dl; progressed = True
            # quer-Notlösung in Spuren
            if not progressed and allow_cross and x + dq <= self.X:
                for y in lanes_cross:
                    if n>0 and self.free(occ, x,y,dq,wq):
                        self.place(occ, items, placed, x,y,dq,wq, self.ICON[("Euro","q")], "Euro")
                        n -= 1; filled_this_col += 1
                if filled_this_col>0:
                    x += dq; progressed = True
            if not progressed:
                x += 1

    # ---------- Varianten ----------
    def generate_variants(self, n_euro, n_ind, allow_euro_cross_in_lanes=False):
        variants = []

        # V1: Industrie → Euro (quer-lastig, dann Tail)
        occ, items, placed = self.empty_board()
        if n_ind>0: self.block_industrie_all(occ, items, placed, n_ind)
        start = self.first_free_x(occ)
        n_rest = self.block_euro_cross_then_long(occ, items, placed, start, n_euro)
        variants.append((items, placed))

        # V2: Industrie → Euro (längs-lastig, dann Tail)
        occ, items, placed = self.empty_board()
        if n_ind>0: self.block_industrie_all(occ, items, placed, n_ind)
        start = self.first_free_x(occ)
        n_rest = self.block_euro_long_then_cross_tail(occ, items, placed, start, n_euro)
        variants.append((items, placed))

        # V3: Euro only längs (3-Spur + Tail)
        occ, items, placed = self.empty_board()
        if n_ind>0: self.block_industrie_all(occ, items, placed, n_ind)
        start = self.first_free_x(occ)
        self.block_euro_only_long(occ, items, placed, start, n_euro)
        variants.append((items, placed))

        # V4: Gemischte Spuren – längs bevorzugt, ggf. quer in Spuren
        occ, items, placed = self.empty_board()
        if n_ind>0: self.block_industrie_all(occ, items, placed, n_ind)
        start = self.first_free_x(occ)
        self.block_euro_fill_lanes_mixed(occ, items, placed, start, n_euro, allow_cross=allow_euro_cross_in_lanes)
        variants.append((items, placed))

        return variants

    # ---------- Render ----------
    def render_board(self):
        with st.expander("📋 Ladeplan anzeigen", expanded=True):
            html = f"""
            <div style="
              display:grid;
              grid-template-columns: repeat({self.X}, {self.cell_px}px);
              grid-auto-rows: {self.cell_px}px;
              gap: 1px;
              background:#ddd; padding:4px; border:2px solid #333; width:fit-content;">
            """
            for (x,y,dx,dy,icon,typ) in self.items:
                html += f"""
                <div style="
                  grid-column:{x+1}/span {dx};
                  grid-row:{y+1}/span {dy};
                  background: url('{icon}') center/contain no-repeat, #fafafa;
                  border:1px solid #777;"></div>
                """
            html += "</div>"
            height = min(560, (self.cell_px+1)*self.Y + 40)
            st.components.v1.html(html, height=height, scrolling=False)

    def render_status(self):
        wanted = {"Euro": int(self.n_euro), "Industrie": int(self.n_ind)}
        missing_msgs = []
        for typ in ["Euro","Industrie"]:
            if wanted[typ] > 0 and self.placed.get(typ,0) < wanted[typ]:
                missing = wanted[typ] - self.placed.get(typ,0)
                missing_msgs.append(f"– {missing}× {typ} passt/passen nicht mehr")

        used_cm = self.used_length_cm(self.items)
        st.markdown(f"**Genutzte Länge:** {used_cm} cm von {self.L_EFF} cm  (≈ {used_cm/max(1,self.L_EFF):.0%})")

        if missing_msgs:
            st.error("🚫 **Platz reicht nicht:**\n" + "\n".join(missing_msgs))
        else:
            st.success("✅ **Alle angeforderten Paletten passen in den Laderaum.**")

        st.info("Fixe Kühler‑Geometrie aktiv • Raster 25 cm • Zoom verstellbar.")

# ---------- Entrypoint ----------
if __name__ == "__main__":
    PalFuchsApp().run()
