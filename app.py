import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="🦊 Paletten Fuchs – Version 3", layout="centered")
st.title("🦊 Paletten Fuchs – Ladeplan für Sattelzug")

# 🚛 Trailergröße in cm
trailer_length = 1360
trailer_width = 245
cm_per_cell = 10
cells_x = trailer_length // cm_per_cell
cells_y = trailer_width // cm_per_cell

# 📦 Palettentypen fix
paletten_typen = [
    {"name": "Euro", "l": 120, "b": 80, "farbe": "#8ecae6"},
    {"name": "Industrie", "l": 120, "b": 100, "farbe": "#90be6d"},
    {"name": "Blumenwagen", "l": 135, "b": 55, "farbe": "#f4a261"},
    {"name": "Benutzerdefiniert", "l": 120, "b": 80, "farbe": "#e76f51"},
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

# 🧮 Raster initialisieren
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

# 📦 Platzieren
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
                    belegung[y0 + dy][x0 + dx] = typ["farbe"]
            geladen += 1
            gesamtgewicht += typ["gewicht"]
    if geladen > 0:
        log.append(f"✅ {geladen}× {typ['name']} geladen")

# 🗺️ Anzeige
st.markdown("### 🗺️ Ladeplan (Draufsicht – vorne → hinten)")

html = "<div style='display: grid; grid-template-columns: " + " ".join(["10px"] * cells_x) + "; gap:1px; border: 2px solid #444;'>"
for row in belegung:
    for zelle in row:
        farbe = zelle if zelle else "#eee"
        html += f"<div style='background-color:{farbe}; width:10px; height:10px; border:1px solid #aaa;'></div>"
html += "</div>"

components.html(html, height=500, scrolling=True)

# 📦 Zusammenfassung
st.markdown("### 📦 Übersicht")
for eintrag in log:
    st.write(eintrag)
st.write(f"📏 Ladefläche: {trailer_length} × {trailer_width} cm")
st.write(f"⚖️ Gesamtgewicht: {gesamtgewicht:.1f} kg")
