import streamlit as st

st.set_page_config(page_title="🦊 Paletten Fuchs – Unicode-Darstellung", layout="centered")
st.title("🦊 Paletten Fuchs – Unicode-Ladeplan")

# 🚛 Trailergröße
trailer_length = 1360
trailer_width = 245
cm_per_cell = 10
cells_x = trailer_length // cm_per_cell
cells_y = trailer_width // cm_per_cell

# Palettentypen fix
paletten_typen = [
    {"name": "Euro", "l": 120, "b": 80, "symbol": "▮"},
    {"name": "Industrie", "l": 120, "b": 100, "symbol": "⬜"},
    {"name": "Blumenwagen", "l": 135, "b": 55, "symbol": "▣"},
    {"name": "Benutzerdefiniert", "l": 120, "b": 80, "symbol": "▪"},
]

st.markdown("### 📥 Eingabe pro Palettentyp")
for typ in paletten_typen:
    cols = st.columns([1.5, 1, 1, 1])
    with cols[0]:
        st.markdown(f"**{typ['name']}**")
    if typ["name"] == "Benutzerdefiniert":
        typ["l"] = st.number_input("Länge", min_value=50, max_value=200, value=typ["l"], key=typ["name"] + "_l")
        typ["b"] = st.number_input("Breite", min_value=50, max_value=150, value=typ["b"], key=typ["name"] + "_b")
    else:
        st.markdown(f"{typ['l']} × {typ['b']} cm")
    with cols[2]:
        typ["anzahl"] = st.number_input("Anzahl", min_value=0, max_value=50, value=0, key=typ["name"] + "_anzahl")
    with cols[3]:
        typ["gewicht"] = st.number_input("kg/Stk", min_value=0, max_value=2000, value=150, key=typ["name"] + "_gewicht")

# Belegung vorbereiten
belegung = [[None for _ in range(cells_x)] for _ in range(cells_y)]

def finde_freien_platz(pal_l, pal_b):
    pal_x = pal_l // cm_per_cell
    pal_y = pal_b // cm_per_cell
    for y in range(cells_y - pal_y + 1):
        for x in range(cells_x - pal_x + 1):
            frei = True
            for dy in range(pal_y):
                for dx in range(pal_x):
                    if belegung[y + dy][x + dx] is not None:
                        frei = False
                        break
                if not frei:
                    break
            if frei:
                return x, y
    return None, None

log = []
gesamtgewicht = 0
for typ in paletten_typen:
    geladen = 0
    for _ in range(int(typ["anzahl"])):
        x0, y0 = finde_freien_platz(typ["l"], typ["b"])
        if x0 is None:
            log.append(f"❌ Kein Platz mehr für {typ['name']}")
            break
        else:
            pal_x = typ["l"] // cm_per_cell
            pal_y = typ["b"] // cm_per_cell
            for dy in range(pal_y):
                for dx in range(pal_x):
                    belegung[y0 + dy][x0 + dx] = typ["symbol"]
            geladen += 1
            gesamtgewicht += typ["gewicht"]
    if geladen > 0:
        log.append(f"✅ {geladen}× {typ['name']} geladen")

# Anzeige als Unicode-Zeichen
st.markdown("### 🗺️ Unicode-Ladeplan (oben = vorn)")
for row in belegung:
    zeile = ""
    for zelle in row:
        zeile += zelle if zelle else "▫"
    st.markdown(f"<pre style='font-size:18px; line-height:100%'>{zeile}</pre>", unsafe_allow_html=True)

# Zusammenfassung
st.markdown("### 📦 Übersicht")
for eintrag in log:
    st.write(eintrag)
st.write(f"📏 Ladefläche: {trailer_length} × {trailer_width} cm")
st.write(f"⚖️ Gesamtgewicht: {gesamtgewicht} kg")
