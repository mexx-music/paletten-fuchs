import streamlit as st

st.set_page_config(page_title="🦊 Paletten Fuchs – Fusion Unicode", layout="centered")
st.title("🦊 Paletten Fuchs – Ladeplan (Unicode statt HTML)")

# 🚛 Trailergröße in cm
trailer_length = 1360
trailer_width = 245
cm_per_cell = 20  # gröberes Raster für klare Unicode-Ansicht
cells_x = trailer_length // cm_per_cell
cells_y = trailer_width // cm_per_cell

# 📦 Palettentypen fix (mit Unicode-Symbolen)
paletten_typen = [
    {"name": "Euro", "l": 120, "b": 80, "symbol_l": "▮", "symbol_q": "▭"},
    {"name": "Industrie", "l": 120, "b": 100, "symbol_l": "⬜", "symbol_q": "⬜"},
    {"name": "Blumenwagen", "l": 135, "b": 55, "symbol_l": "▣", "symbol_q": "▣"},
    {"name": "Benutzerdefiniert", "l": 120, "b": 80, "symbol_l": "▪", "symbol_q": "▪"},
]

st.markdown("### 📥 Eingabe pro Palettentyp")

# Eingaben sammeln
eingaben = []
for typ in paletten_typen:
    cols = st.columns([1.5, 1, 1, 1, 1])
    with cols[0]:
        st.markdown(f"**{typ['name']}**")
        if typ["name"] == "Benutzerdefiniert":
            typ_l = st.number_input("Länge", min_value=50, max_value=200, value=typ["l"], key=typ["name"] + "_l")
            typ_b = st.number_input("Breite", min_value=40, max_value=150, value=typ["b"], key=typ["name"] + "_b")
        else:
            typ_l, typ_b = typ["l"], typ["b"]
            st.markdown(f"{typ_l} × {typ_b} cm")
    with cols[1]:
        anzahl = st.number_input("Anzahl", min_value=0, max_value=60, value=0, key=typ["name"] + "_anzahl")
    with cols[2]:
        ausrichtung = st.selectbox("Ausrichtung", ["Längs", "Quer"], key=typ["name"] + "_ori")
    with cols[3]:
        gewicht = st.number_input("kg/Stk", min_value=0, max_value=2000, value=150, key=typ["name"] + "_gewicht")
    with cols[4]:
        symbol = typ["symbol_l"] if ausrichtung == "Längs" else typ["symbol_q"]
        st.markdown(f"**Symbol:** `{symbol}`")
    # Drehung anwenden
    if ausrichtung == "Quer":
        typ_l, typ_b = typ_b, typ_l
    if anzahl > 0:
        eingaben.append({"name": typ["name"], "l": typ_l, "b": typ_b, "anzahl": int(anzahl), "symbol": symbol, "gewicht": gewicht})

# 🧮 Raster initialisieren
belegung = [[None for _ in range(cells_x)] for _ in range(cells_y)]

def finde_freien_platz(pal_l, pal_b):
    pal_x = max(1, pal_l // cm_per_cell)
    pal_y = max(1, pal_b // cm_per_cell)
    for y in range(cells_y - pal_y + 1):
        for x in range(cells_x - pal_x + 1):
            frei = True
            for dy in range(pal_y):
                for dx in range(pal_x):
                    if belegung[y+dy][x+dx] is not None:
                        frei = False; break
                if not frei: break
            if frei:
                return x, y, pal_x, pal_y
    return None, None, None, None

# 📦 Platzieren (First-Fit). Unicode: Nur EIN Symbol am Anker (oben/links), Rest bleibt leer für klare Optik
log = []
gesamtgewicht = 0
for typ in eingaben:
    geladen = 0
    for i in range(typ["anzahl"]):
        x0, y0, pal_x, pal_y = finde_freien_platz(typ["l"], typ["b"])
        if x0 is None:
            log.append(f"❌ Kein Platz mehr für {typ['name']} Nr. {i+1}")
            break
        # Block markieren (ohne Symbol flood)
        for dy in range(pal_y):
            for dx in range(pal_x):
                belegung[y0+dy][x0+dx] = ""  # block belegt
        # Symbol nur im Anker
        belegung[y0][x0] = typ["symbol"]
        geladen += 1
        gesamtgewicht += typ["gewicht"]
    if geladen:
        log.append(f"✅ {geladen}× {typ['name']} geladen")

# 🗺️ Anzeige als Unicode / Text
st.markdown("### 🗺️ Unicode-Ladeplan (oben = vorn)")
EM = " "  #   em-space
for row in belegung:
    line = "".join((cell if cell else EM) for cell in row)
    st.markdown(f"<pre style='font-size:22px; line-height:100%; margin:0'>{line}</pre>", unsafe_allow_html=True)

with st.expander("⚖️ Gewichtsdaten anzeigen"):
    st.write(f"Gesamtgewicht: {gesamtgewicht} kg")

st.markdown("### 📦 Übersicht")
for e in log:
    st.write(e)

st.caption("Unicode-Ansicht: ▭ Euro quer, ▮ Euro längs, ⬜ Industrie. Symbol erscheint nur am linken oberen Eck jeder Palette für ruhige Darstellung. Rastergröße oben einstellbar.")
