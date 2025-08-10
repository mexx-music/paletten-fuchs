import streamlit as st

class PalFuchsApp:
    # ---------- Constants ----------
    TRAILER_L, TRAILER_W = 1360, 245  # cm

    ICON = {
        ("Euro","l"): "icons/euro_l.png",
        ("Euro","q"): "icons/euro_q.png",
        ("Industrie","q"): "icons/ind_q.png",
        ("Blume","l"): "icons/flower_l.png",
        ("Blume","q"): "icons/flower_q.png",
    }

    def __init__(self):
        # runtime state (filled in by layout_sidebar)
        self.cell_cm = 25
        self.cell_px = 4
        self.allow_euro_cross_in_lanes = False
        self.n_euro = 30
        self.n_ind = 0

        # grid dependent (computed)
        self.X = None  # columns (entlang Länge)
        self.Y = None  # rows (quer)

        # current variant data (computed)
        self.items = []     # (x,y,dx,dy,icon,typ)
        self.placed = {}    # counts per type

    # ---------- Top-level run ----------
    def run(self):
        self.setup_page()
        self.layout_sidebar()
        self.compute_grid()
        var_idx, variants = self.layout_controls_and_build_variants()
        self.items, self.placed = variants[var_idx]
        self.render_board()
        self.render_status()

    # ---------- Page/Layout ----------
    def setup_page(self):
        st.set_page_config(page_title="🦊 PAL Fuchs 8 – Klassen-App", layout="wide")
        st.title("🦊 PAL Fuchs 8 – Draufsicht mit Icons & Varianten (Klassenbasiert)")

    def layout_sidebar(self):
        st.sidebar.markdown("### ⚙️ Einstellungen")
        self.cell_cm = st.sidebar.slider("Raster (cm/Zelle)", 5, 40, 25, 5)
        self.cell_px = st.sidebar.slider("Zellpixel (Zoom)", 4, 14, 4, 1)
        self.allow_euro_cross_in_lanes = st.sidebar.checkbox(
            "Euro auch **quer in Spuren** zulassen", value=False,
            help="Erlaubt, Euro-Paletten innerhalb der drei Längsspuren quer zu setzen – "
                 "nicht nur am Heckabschluss."
        )

    def compute_grid(self):
        self.X = self.TRAILER_L // self.cell_cm
        self.Y = self.TRAILER_W // self.cell_cm

    def layout_controls_and_build_variants(self):
        st.markdown("### 📥 Manuelle Menge")
        c1,c2,c3,c4 = st.columns([1.2,1.2,1.6,1])
        with c1:
            self.n_euro = int(st.number_input("Euro (120×80)", 0, 45, 30))
        with c2:
            self.n_ind  = int(st.number_input("Industrie (120×100)", 0, 45, 0))
        with c3:
            st.caption("Variante wählen (Navigation unten)")

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

        return st.session_state.var_idx, variants

    # ---------- Geometry helpers ----------
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

    # ---------- Euro tail-closure (unchanged logic) ----------
    def fill_tail_closed_euro(self, occ, items, placed, x_start, euro_left):
        if euro_left <= 0: return
        dq,wq = self.span("Euro","q")
        dl,wl = self.span("Euro","l")

        if euro_left % 3 == 0 or euro_left < 2:
            cols_long = euro_left // 3
            need_tail_q = False
        else:
            cols_long = max(0, (euro_left - 2)//3)
            need_tail_q = True

        lanes = [0, self.center_y(wl), self.Y-wl]
        x = x_start

        # 3er Längsreihen
        for _ in range(cols_long):
            if x + dl > self.X: break
            for y in lanes:
                if self.free(occ, x,y,dl,wl):
                    self.place(occ, items, placed, x,y,dl,wl, self.ICON[("Euro","l")], "Euro")
            x += dl

        # 2× Querabschluss
        if need_tail_q and x + dq <= self.X:
            if self.free(occ, x,0,dq,wq):
                self.place(occ, items, placed, x,0,dq,wq, self.ICON[("Euro","q")], "Euro")
            if self.free(occ, x,self.Y-wq,dq,wq):
                self.place(occ, items, placed, x,self.Y-wq,dq,wq, self.ICON[("Euro","q")], "Euro")

    # ---------- Blocks / strategies ----------
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
        return x  # nächste freie Spalte (ungefähr)

    def block_euro_only_long(self, occ, items, placed, x_start, n):
        dl,wl = self.span("Euro","l")
        lanes = [0, self.center_y(wl), self.Y-wl]
        x = x_start
        while n>0 and x+dl<=self.X:
            for y in lanes:
                if n>0 and self.free(occ, x,y,dl,wl):
                    self.place(occ, items, placed, x,y,dl,wl, self.ICON[("Euro","l")], "Euro")
                    n -= 1
            x += dl

    def block_euro_cross_then_long(self, occ, items, placed, x_start, n):
        dq,wq = self.span("Euro","q");  dl,wl = self.span("Euro","l")
        x = x_start
        # 1 quer mittig
        if n>0 and x+dq<=self.X and self.free(occ, x,self.center_y(wq),dq,wq):
            self.place(occ, items, placed, x,self.center_y(wq),dq,wq, self.ICON[("Euro","q")], "Euro")
            n -= 1; x += dq
        # 2 quer außen
        if n>=2 and x+dq<=self.X:
            for y in [0, self.Y-wq]:
                if n>0 and self.free(occ, x,y,dq,wq):
                    self.place(occ, items, placed, x,y,dq,wq, self.ICON[("Euro","q")], "Euro")
                    n -= 1
            x += dq
        # Rest: geschlossen
        self.fill_tail_closed_euro(occ, items, placed, x, n)

    def block_euro_long_then_cross_tail(self, occ, items, placed, x_start, n):
        dl,wl = self.span("Euro","l")
        lanes = [0, self.center_y(wl), self.Y-wl]
        x = x_start
        col_cap = 3
        while n >= col_cap and x+self.span("Euro","l")[0] <= self.X:
            for y in lanes:
                if self.free(occ, x,y,dl,wl):
                    self.place(occ, items, placed, x,y,dl,wl, self.ICON[("Euro","l")], "Euro")
            n -= col_cap
            x += dl
        self.fill_tail_closed_euro(occ, items, placed, x, n)

    # NEW: Euro in lanes may be crosswise too (if toggle is on)
    def block_euro_fill_lanes_mixed(self, occ, items, placed, x_start, n, allow_cross):
        """
        Füllt Spalte für Spalte über die drei Längsspuren.
        Pro Spur: bevorzugt längs; wenn belegt und erlaubtes Quer möglich, dann quer.
        """
        if n <= 0: return
        dl,wl = self.span("Euro","l")
        dq,wq = self.span("Euro","q")
        lanes_long = [ (0, wl), (self.center_y(wl), wl), (self.Y-wl, wl) ]
        lanes_cross = [ (0, wq), (self.center_y(wq), wq), (self.Y-wq, wq) ]

        x = x_start
        while n>0 and x < self.X:
            # wir nehmen die längs-Spaltenbreite als Grundschritt; falls quer genutzt wird,
            # rücken wir mit dq weiter.
            progressed = False

            # Versuche, alle drei Spuren an dieser X-Position zu füllen
            filled_this_col = 0

            # 1) Versuch längs in allen drei Spuren
            if x + dl <= self.X:
                for (y, h) in lanes_long:
                    if n>0 and self.free(occ, x,y,dl,wl):
                        self.place(occ, items, placed, x,y,dl,wl, self.ICON[("Euro","l")], "Euro")
                        n -= 1
                        filled_this_col += 1
                if filled_this_col > 0:
                    x += dl
                    progressed = True

            # 2) Falls nichts längs ging und Quer erlaubt, versuche quer-Spalte an gleicher Stelle
            if not progressed and allow_cross and x + dq <= self.X:
                for (y, h) in lanes_cross:
                    if n>0 and self.free(occ, x,y,dq,wq):
                        self.place(occ, items, placed, x,y,dq,wq, self.ICON[("Euro","q")], "Euro")
                        n -= 1
                        filled_this_col += 1
                if filled_this_col > 0:
                    x += dq
                    progressed = True

            # 3) Wenn weder längs noch quer ging, rücke um 1 Zelle nach rechts und versuche erneut
            if not progressed:
                x += 1

    # ---------- Varianten ----------
    def generate_variants(self, n_euro, n_ind, allow_euro_cross_in_lanes=False):
        variants = []

        # Variante 1: Industrie → Euro (quer+quer+geschlossen)
        occ, items, placed = self.empty_board()
        if n_ind>0:
            self.block_industrie_all(occ, items, placed, n_ind)
        start = self.first_free_x(occ)
        self.block_euro_cross_then_long(occ, items, placed, start, n_euro)
        variants.append((items, placed))

        # Variante 2: Industrie → Euro (längs zuerst, dann geschlossener Abschluss)
        occ, items, placed = self.empty_board()
        if n_ind>0:
            self.block_industrie_all(occ, items, placed, n_ind)
        start = self.first_free_x(occ)
        self.block_euro_long_then_cross_tail(occ, items, placed, start, n_euro)
        variants.append((items, placed))

        # Variante 3: Euro only längs (über alles)
        occ, items, placed = self.empty_board()
        if n_ind>0:
            self.block_industrie_all(occ, items, placed, n_ind)
            start = self.first_free_x(occ)
        else:
            start = 0
        self.block_euro_only_long(occ, items, placed, start, n_euro)
        variants.append((items, placed))

        # Variante 4 (NEU): Gemischte Spuren – längs bevorzugt, ggf. quer in Spuren
        occ, items, placed = self.empty_board()
        if n_ind>0:
            self.block_industrie_all(occ, items, placed, n_ind)
        start = self.first_free_x(occ)
        self.block_euro_fill_lanes_mixed(
            occ, items, placed, start, n_euro,
            allow_cross=allow_euro_cross_in_lanes
        )
        variants.append((items, placed))

        return variants

    # ---------- Render ----------
    def render_board(self):
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
        st.markdown(f"**Genutzte Länge:** {used_cm} cm von {self.TRAILER_L} cm  (≈ {used_cm/self.TRAILER_L:.0%})")

        if missing_msgs:
            st.error("🚫 **Platz reicht nicht:**\n" + "\n".join(missing_msgs))
        else:
            st.success("✅ **Alle angeforderten Paletten passen in den Laderaum.**")

        st.info("Tipp: Raster 25 cm & Zoom 4 px sind die empfohlenen Grundwerte.")

# ---------- Entrypoint ----------
if __name__ == "__main__":
    PalFuchsApp().run()
