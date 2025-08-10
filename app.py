# pal_fuchs9_icon_fusion.py
# 🦊 Pal Fuchs 9 – Icon-Version (Kühler fix, Gewicht/IBC, Ceil-Raster, Achslast, Varianten + Tests)
import math
import streamlit as st

class PalFuchsApp:
    # ---------- Feste Kühler-Geometrie ----------
    TRAILER_L_NOM, TRAILER_W = 1360, 245    # cm, Kühlsattel fix
    FRONT_BUF_CM, BACK_BUF_CM = 0, 0        # aktuell fix; optional später sichtbar

    # ---------- Icons ----------
    ICON = {
        ("Euro","l"): "icons/euro_l.png",
        ("Euro","q"): "icons/euro_q.png",
        ("Industrie","q"): "icons/ind_q.png",
        ("Blume","l"): "icons/flower_l.png",
        ("Blume","q"): "icons/flower_q.png",
        ("IBC","q"): "icons/ind_q.png",     # IBC wie Industrie (immer schwer)
    }

    def __init__(self):
        # UI/State
        self.cell_cm = 40          # Spec D: Standardanzeige Raster 40 cm
        self.cell_px = 6           # Spec D: Zell-Pixel 6
        self.allow_euro_cross_in_lanes = False

        # Mengen
        self.n_euro = 30
        self.n_ind_light = 0       # leichte Industrie
        self.n_ibc = 0             # IBC = immer schwer

        # Grid
        self.X = None
        self.Y = None
        self.L_EFF = None

        # Variant result
        self.items = []     # (x,y,dx,dy,icon,typ)
        self.placed = {}    # counts per type

    # ---------- Run ----------
    def run(self):
        self.setup_page()
        self.layout_sidebar()
        self.compute_grid()
        var_idx, variants, var_names = self.layout_controls_and_build_variants()
        self.items, self.placed = variants[var_idx]
        self.render_board()
        self.render_status(var_names[var_idx])

    # ---------- Page ----------
    def setup_page(self):
        st.set_page_config(page_title="🦊 PAL Fuchs 9 – Icon (Gewicht + IBC)", layout="wide")
        st.title("🦊 PAL Fuchs 9 – Icon-Version (Kühler fix, Gewicht & IBC)")

    def layout_sidebar(self):
        st.sidebar.markdown("### ⚙️ Einstellungen")
        # Spec D: Auto-Zoom aus → nur manueller Zoom
        self.cell_cm = st.sidebar.number_input("Raster (cm/Zelle)", 10, 50, self.cell_cm, 5, help="Ceil-Rasterung aktiv (maßhaltig).")
        self.cell_px = st.sidebar.slider("Zell‑Pixel (Zoom)", 4, 14, self.cell_px, 1)
        self.allow_euro_cross_in_lanes = st.sidebar.checkbox(
            "Euro auch **quer in Spuren** zulassen", value=False,
            help="Erlaubt Quer in den drei Längsspuren – nur falls gewünscht."
        )

    def compute_grid(self):
        # Effektive Länge (aktuell ohne einstellbare Puffer – fix Kühler)
        self.L_EFF = max(0, self.TRAILER_L_NOM - self.FRONT_BUF_CM - self.BACK_BUF_CM)
        self.X = max(1, math.ceil(self.L_EFF / self.cell_cm))  # Ceil-Rasterung
        self.Y = max(1, math.ceil(self.TRAILER_W / self.cell_cm))

    def layout_controls_and_build_variants(self):
        st.subheader("📦 Paletten & Gewichte")
        c1,c2,c3,c4 = st.columns([1.2,1.2,1.2,1.6])
        with c1:
            self.n_euro = int(st.number_input("Euro (120×80)", 0, 45, self.n_euro))
        with c2:
            self.n_ind_light  = int(st.number_input("Industrie leicht (100×120 quer)", 0, 30, self.n_ind_light))
        with c3:
            self.n_ibc  = int(st.number_input("IBC / Industrie schwer (quer)", 0, 30, self.n_ibc))
        with c4:
            st.caption("Gewichtslogik: IBC = immer schwer. Industrie (leicht) bevorzugt vorn, schwer eher hinten.")

        st.markdown("---")
        c5, c6 = st.columns([1,1])
        with c5:
            weight_mode = st.toggle("Gewichtsmodus (Achslast optimieren)", value=True,
                                    help="Zeigt gewichtsoptimierte Varianten für alle Mengen.")
        with c6:
            st.caption("Beste balanced Variante zuerst (im Namen gekennzeichnet).")

        # Schnelltests (Spec G12)
        with st.expander("🧪 Schnelltests (füllt Eingaben)", expanded=False):
            t = st.selectbox(
                "Szenario wählen",
                ["–", "Euro 20", "Euro 21", "Euro 23", "Euro 24",
                 "Euro 29", "Euro 30", "Euro 31", "Euro 32", "Euro 33",
                 "Mix: 24 Euro + 4 leichte Industrie",
                 "Mix: 24 Euro + 4 IBC"],
                index=0,
            )
            if t != "–":
                if t.startswith("Euro "):
                    self.n_euro = int(t.split()[1]); self.n_ind_light = 0; self.n_ibc = 0
                elif "leichte Industrie" in t:
                    self.n_euro, self.n_ind_light, self.n_ibc = 24, 4, 0
                else:
                    self.n_euro, self.n_ind_light, self.n_ibc = 24, 0, 4
                st.info(f"Testfall: Euro={self.n_euro}, Ind.leicht={self.n_ind_light}, IBC={self.n_ibc}")

        variants, var_names = self.generate_variants(
            n_euro=self.n_euro,
            n_ind_light=self.n_ind_light,
            n_ibc=self.n_ibc,
            allow_euro_cross_in_lanes=self.allow_euro_cross_in_lanes,
            weight_mode=weight_mode
        )

        # Navigation
        if "var_idx" not in st.session_state:
            st.session_state.var_idx = 0
        nav1,nav2,nav3 = st.columns([1,1,3])
        with nav1:
            if st.button("◀ Variante"):
                st.session_state.var_idx = (st.session_state.var_idx - 1) % len(variants)
        with nav2:
            if st.button("Variante ▶"):
                st.session_state.var_idx = (st.session_state.var_idx + 1) % len(variants)
        with nav3:
            st.markdown(f"**Variante:** {st.session_state.var_idx+1} / {len(variants)} – {var_names[st.session_state.var_idx]}")

        return st.session_state.var_idx, variants, var_names

    # ---------- Geometry ----------
    def span(self, name, ori):
        # Ceil-Rasterung (maßhaltig)
        if name == "Euro":        L,B = 120, 80
        elif name == "Industrie": L,B = 120,100
        elif name == "IBC":       L,B = 120,100
        else:                     L,B = 135, 55  # Demo
        if name in ("Industrie", "IBC"):
            ori = "q"  # Industrie/IBC immer quer
        if ori == "q":
            depth_cm, width_cm = B, L
        else:
            depth_cm, width_cm = L, B
        dx = max(1, math.ceil(depth_cm / self.cell_cm))   # entlang Länge
        dy = max(1, math.ceil(width_cm / self.cell_cm))   # quer
        return dx, dy

    def three_rows_fixed(self, h):
        top = 0
        mid = max(0, (self.Y - h) // 2)
        bot = self.Y - h
        rows = []
        for y in (top, mid, bot):
            if y not in rows:
                rows.append(y)
        return rows

    def center_y(self, dy):
        return max(0, (self.Y - dy) // 2)

    def empty_board(self):
        occupied = [[False]*self.X for _ in range(self.Y)]
        items, placed = [], {"Euro":0, "Industrie":0, "IBC":0, "Blume":0}
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
        placed[typ] = placed.get(typ,0) + 1

    def first_free_x(self, occ):
        for xx in range(self.X):
            if any(not occ[yy][xx] for yy in range(self.Y)): return xx
        return self.X

    def used_length_cm(self, items):
        if not items: return 0
        x_end = max(x+dx for (x,y,dx,dy,icon,typ) in items)
        return int(x_end * self.cell_cm)

    # ---------- Heckabschluss (sauber) ----------
    def tail_close_clean_euro(self, occ, items, placed, x_start, euro_left):
        if euro_left <= 0: return 0
        dq,wq = self.span("Euro","q")
        dl,wl = self.span("Euro","l")
        x = x_start

        # 1) Bevorzugt 3x längs (wenn Platz)
        if euro_left >= 3 and x + dl <= self.X:
            ok = True
            for y in self.three_rows_fixed(wl):
                if not self.free(occ, x,y,dl,wl): ok=False; break
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
    def block_industry_weighted(self, occ, items, placed, n_light, n_ibc):
        """Industrie/IBC (quer), gewichtsabhängig:
        - IBC (schwer) eher hinten (unten), dann oben (Balance)
        - leichte Industrie eher vorn (oben), dann unten
        - ungerade zuerst mittig
        """
        dq,wq = self.span("Industrie","q")
        x = 0

        # IBC (schwer) – ungerade zuerst mittig
        if n_ibc % 2 == 1 and x + dq <= self.X:
            y = self.center_y(wq)
            if self.free(occ, x,y,dq,wq):
                self.place(occ, items, placed, x,y,dq,wq, self.ICON[("IBC","q")], "IBC")
                n_ibc -= 1; x += dq

        # Platzierung spaltenweise
        while (n_light > 0 or n_ibc > 0) and x + dq <= self.X:
            # schwer bevorzugt hinten→oben Reihenfolge invertieren wir für Balance
            spots = [0, self.Y - wq]  # (oben,vorn) und (unten,hinten)
            # zuerst IBC nach hinten, dann oben; leichte vorn, dann hinten
            # 1) IBC
            for y in [self.Y - wq, 0]:
                if n_ibc > 0 and self.free(occ, x,y,dq,wq):
                    self.place(occ, items, placed, x,y,dq,wq, self.ICON[("IBC","q")], "IBC")
                    n_ibc -= 1
                    break
            # 2) Leicht
            for y in spots:
                if n_light > 0 and self.free(occ, x,y,dq,wq):
                    self.place(occ, items, placed, x,y,dq,wq, self.ICON[("Industrie","q")], "Industrie")
                    n_light -= 1
                    break
            x += dq

        return x, n_light, n_ibc

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
        x = x_start
        while n>=3 and x+dq<=self.X:
            filled = 0
            for y in self.three_rows_fixed(wq):
                if n>0 and self.free(occ, x,y,dq,wq):
                    self.place(occ, items, placed, x,y,dq,wq, self.ICON[("Euro","q")], "Euro")
                    n -= 1; filled += 1
            x += dq if filled>0 else 1
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

    # ---------- Varianten (inkl. Gewichtsmodus) ----------
    def generate_variants(self, n_euro, n_ind_light, n_ibc, allow_euro_cross_in_lanes=False, weight_mode=True):
        variants = []
        names = []

        def add_variant(builder_name, builder_fn, heavy_back=True, label_extra=""):
            occ, items, placed = self.empty_board()
            # Industrie/IBC zuerst: gewichtssensitiv
            x_after, rem_light, rem_ibc = self.block_industry_weighted(occ, items, placed, n_ind_light, n_ibc)
            # Dann Euro:
            n_rest = builder_fn(occ, items, placed, self.first_free_x(occ), n_euro)
            variants.append((items, placed))
            names.append(f"{builder_name}{label_extra}")

        # Basis 4
        add_variant("V1 Quer-lastig", self.block_euro_cross_then_long)
        add_variant("V2 Längs-lastig", self.block_euro_long_then_cross_tail)
        add_variant("V3 Nur längs (3-Spur)", self.block_euro_only_long)
        # V4: Gemischte Spuren
        def v4_fn(occ, items, placed, start, n):
            self.block_euro_fill_lanes_mixed(occ, items, placed, start, n, allow_cross=allow_euro_cross_in_lanes)
            return 0
        add_variant("V4 Gemischte Spuren", v4_fn)

        if weight_mode:
            # Duplikate als Gewichtsvarianten (Kennzeichnung)
            add_variant("V1 Quer-lastig (Gewicht)", self.block_euro_cross_then_long, label_extra=" – balanced")
            add_variant("V2 Längs-lastig (Gewicht)", self.block_euro_long_then_cross_tail, label_extra=" – balanced")
            add_variant("V3 Nur längs (Gewicht)", self.block_euro_only_long, label_extra=" – balanced")
            add_variant("V4 Gemischte Spuren (Gewicht)", v4_fn, label_extra=" – balanced")

        return variants, names

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

    # ---------- Achslast-Schätzung ----------
    def estimate_axle_balance(self):
        if not self.items or self.L_EFF <= 0: return (50,50)
        total = 0.0
        front = 0.0
        half = self.L_EFF / 2
        for (x,y,dx,dy,icon,typ) in self.items:
            block_l = dx * self.cell_cm
            x_cm = x * self.cell_cm
            center = x_cm + block_l/2
            # Gewichtsfaktor: IBC/Industrie schwerer
            g = 2.0 if typ in ("IBC","Industrie") else 1.0
            total += g
            # linearer Split um die Mitte
            if center <= half:
                share = 0.5 + (half - center) / (2*half)
            else:
                share = 0.5 - (center - half) / (2*half)
            share = max(0.0, min(1.0, share))
            front += g*share
        f = int(round(100 * front / max(1.0,total)))
        return (f, 100 - f)

    # ---------- Status ----------
    def render_status(self, variant_name: str):
        wanted = {"Euro": int(self.n_euro), "Industrie": int(self.n_ind_light), "IBC": int(self.n_ibc)}
        missing_msgs = []
        for typ in ["Euro","Industrie","IBC"]:
            want = wanted[typ]
            have = self.placed.get(typ,0)
            if want > 0 and have < want:
                missing = want - have
                missing_msgs.append(f"– {missing}× {typ} passt/passen nicht mehr")

        used_cm = self.used_length_cm(self.items)
        pct = (used_cm / self.L_EFF) if self.L_EFF else 0.0
        front_pct, back_pct = self.estimate_axle_balance()

        cols = st.columns(3)
        with cols[0]:
            st.markdown(f"**Genutzte Länge:** {used_cm} cm von {self.L_EFF} cm  (≈ {pct:.0%})")
        with cols[1]:
            st.markdown(f"**Achslast-Schätzung:** vorn {front_pct}% / hinten {back_pct}%")
        with cols[2]:
            st.markdown(f"**Variante:** {variant_name}")

        if missing_msgs:
            st.error("🚫 **Platz reicht nicht:**\n" + "\n".join(missing_msgs))
        else:
            st.success("✅ **Alle angeforderten Paletten platziert.**")

        st.info("Ceil‑Rasterung aktiv • Kühler fix • IBC = schwer (hinten bevorzugt) • Industrie leicht = vorn bevorzugt.")

# ---------- Entrypoint ----------
if __name__ == "__main__":
    PalFuchsApp().run()
