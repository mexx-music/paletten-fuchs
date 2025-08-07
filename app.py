
import streamlit as st
import math

st.set_page_config(page_title="🟧 Paletten Fuchs – Ladeplan", layout="wide")

st.title("🟧 Paletten Fuchs – Ladeflächenplaner für Sattelzug")

# Ladeflächengröße (innen): ca. 13.6m x 2.45m → 1360 x 245 cm
LKW_LAENGE_CM = 1360
LKW_BREITE_CM = 245

PALETTEN_TYPEN = {
    "Euro-Palette (120×80)": (120, 80),
    "Industriepalette (120×100)": (120, 100),
    "Blumenwagen (67×135)": (67, 135),
    "Benutzerdefiniert": None
}

st.sidebar.header("📦 Paletten-Einstellungen")
palettentyp = st.sidebar.selectbox("Palettentyp wählen", list(PALETTEN_TYPEN.keys()))

if palettentyp == "Benutzerdefiniert":
    pal_laenge = st.sidebar.number_input("Länge (cm)", min_value=50, max_value=300, value=120)
    pal_breite = st.sidebar.number_input("Breite (cm)", min_value=50, max_value=150, value=80)
else:
    pal_laenge, pal_breite = PALETTEN_TYPEN[palettentyp]

anzahl = st.sidebar.number_input("Anzahl Paletten", min_value=1, max_value=66, value=33)

# Optional Gewichtseingabe
show_gewicht = st.sidebar.checkbox("Gewicht eingeben")
gewicht = None
if show_gewicht:
    gewicht = st.sidebar.number_input("Gewicht pro Palette (kg)", min_value=1, max_value=1500, value=500)

# Berechnung: Wieviele Paletten passen in eine Reihe (nebeneinander)?
pal_pro_reihe = math.floor(LKW_BREITE_CM / pal_breite)
pal_reihen = math.ceil(anzahl / pal_pro_reihe)

st.subheader(f"🔢 Palettenanzeige ({anzahl} Stück) – {pal_pro_reihe} pro Reihe")

# Zeichnen
import streamlit.components.v1 as components

html = f"""<div style='display: grid; grid-template-columns: repeat({pal_pro_reihe}, 1fr); 
            gap: 2px; width: 100%; max-width: 800px; margin: auto;'>\"""

for i in range(anzahl):
    html += f""<div style='background:#FFA500AA; border:1px solid #333; height:40px; text-align:center; font-size:10px;'>P{i+1}</div>\""

html += "</div><br><br>"
components.html(html, height=pal_reihen * 45 + 50)

# Zusatzanzeige
if show_gewicht:
    gesamt = anzahl * gewicht
    st.info(f"🔩 Gesamtgewicht: {gesamt:,} kg")

st.markdown("---")
st.markdown("📏 Maßstabsgerechte Darstellung folgt in Vollversion.")
