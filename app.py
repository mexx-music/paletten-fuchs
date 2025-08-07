
import streamlit as st
import math
import streamlit.components.v1 as components

st.set_page_config(page_title="🟧 Paletten Fuchs – Multi-Paletten-Planung", layout="wide")
st.title("🟧 Paletten Fuchs – Ladeplan mit mehreren Palettentypen")

# Ladeflächengröße
LKW_BREITE_CM = 245

# Definition der Palettentypen
PALETTEN_TYPEN = {
    "Euro-Palette (120×80)": {"maße": (120, 80), "symbol": "▭", "farbe": "#FFA500"},
    "Industriepalette (120×100)": {"maße": (120, 100), "symbol": "▯", "farbe": "#FF5733"},
    "Blumenwagen (135×67)": {"maße": (135, 67), "symbol": "⬜", "farbe": "#8E44AD"},
    "Benutzerdefiniert": {"maße": None, "symbol": "⚙️", "farbe": "#3498DB"}
}

st.sidebar.header("📦 Palettentypen auswählen & Anzahl eingeben")

paletten_eingaben = []

# Gewicht allgemein aktivierbar
show_gewicht = st.sidebar.checkbox("⚖️ Gewichtseingabe aktivieren")

for typ, daten in PALETTEN_TYPEN.items():
    aktiv = st.sidebar.checkbox(f"{daten['symbol']} {typ}", key=typ)
    if aktiv:
        if typ == "Benutzerdefiniert":
            laenge = st.sidebar.number_input(f"↔️ Länge {typ} (cm)", 50, 300, 120, key=f"{typ}_l")
            breite = st.sidebar.number_input(f"↕️ Breite {typ} (cm)", 50, 150, 80, key=f"{typ}_b")
        else:
            laenge, breite = daten["maße"]

        anzahl = st.sidebar.number_input(f"Anzahl – {typ}", 1, 66, 10, key=f"{typ}_anzahl")

        gewicht = None
        if show_gewicht:
            gewicht = st.sidebar.number_input(f"Gewicht pro Palette (kg) – {typ}", 1, 1500, 500, key=f"{typ}_gewicht")

        paletten_eingaben.append({
            "typ": typ,
            "symbol": daten["symbol"],
            "farbe": daten["farbe"],
            "laenge": laenge,
            "breite": breite,
            "anzahl": anzahl,
            "gewicht": gewicht
        })

# Anzeige vorbereiten
st.subheader("📊 Ladeflächenansicht")

html = "<div style='width:100%; max-width:850px; margin:auto; display:flex; flex-wrap:wrap; gap:4px;'>"

for pal in paletten_eingaben:
    pro_reihe = max(1, math.floor(LKW_BREITE_CM / pal["breite"]))
    reihen = math.ceil(pal["anzahl"] / pro_reihe)

    for i in range(pal["anzahl"]):
        html += f"<div title='{pal['typ']} P{i+1}' style='background:{pal['farbe']}; border:1px solid #333; width:80px; height:40px; text-align:center; font-size:11px; line-height:40px;'>{pal['symbol']} {i+1}</div>"

html += "</div><br>"

components.html(html, height=600)

# Gesamtgewicht anzeigen
if show_gewicht:
    gesamt = sum(p["anzahl"] * p["gewicht"] for p in paletten_eingaben if p["gewicht"])
    st.info(f"🔩 Gesamtgewicht aller Paletten: {gesamt:,} kg")

st.markdown("---")
st.markdown("🔧 Darstellung symbolisch – Maßstab folgt in nächster Version.")
