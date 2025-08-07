
import streamlit as st
import math
import streamlit.components.v1 as components

st.set_page_config(page_title="🟧 Paletten Fuchs – Kompaktansicht", layout="wide")
st.title("🟧 Paletten Fuchs – Kompakter Ladeplan")

LKW_BREITE_CM = 245
MAßSTAB = 2  # 1cm = 2px
MAX_CONTAINER_PX = int(LKW_BREITE_CM * MAßSTAB)

PALETTEN_TYPEN = {
    "Euro-Palette (120×80)": {"maße": (120, 80), "symbol": "▭", "farbe": "#FFA500"},
    "Industriepalette (120×100)": {"maße": (120, 100), "symbol": "▯", "farbe": "#FF5733"},
    "Blumenwagen (135×67)": {"maße": (135, 67), "symbol": "⬜", "farbe": "#8E44AD"},
    "Benutzerdefiniert": {"maße": None, "symbol": "⚙️", "farbe": "#3498DB"}
}

st.sidebar.header("📦 Palettentypen aktivieren")

paletten_eingaben = []
show_gewicht = st.sidebar.checkbox("⚖️ Gewicht anzeigen")

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
            gewicht = st.sidebar.number_input(f"Gewicht (kg) – {typ}", 1, 1500, 500, key=f"{typ}_gewicht")

        paletten_eingaben.append({
            "typ": typ,
            "symbol": daten["symbol"],
            "farbe": daten["farbe"],
            "laenge": laenge,
            "breite": breite,
            "anzahl": anzahl,
            "gewicht": gewicht
        })

st.subheader("📊 Ladefläche (maßstabsgetreu)")

html = f"<div style='width:{MAX_CONTAINER_PX}px; margin:auto; display:flex; flex-wrap:wrap; gap:2px; border:1px solid #ccc; padding:4px;'>"

reihe_offset = 0

for pal in paletten_eingaben:
    pro_reihe = max(1, math.floor(LKW_BREITE_CM / pal["breite"]))
    for i in range(pal["anzahl"]):
        breite_px = int(pal["breite"] * MAßSTAB)
        laenge_px = int(pal["laenge"] * MAßSTAB)
        html += f"<div title='{pal['typ']} {i+1}' style='background:{pal['farbe']}; border:1px solid #333; width:{breite_px}px; height:{laenge_px}px; font-size:10px; text-align:center; line-height:{laenge_px}px;'>{pal['symbol']} {i+1}</div>"

html += "</div><br>"
components.html(html, height=700)

if show_gewicht:
    gesamt = sum(p["anzahl"] * p["gewicht"] for p in paletten_eingaben if p["gewicht"])
    st.info(f"🔩 Gesamtgewicht aller Paletten: {gesamt:,} kg")

st.markdown("---")
st.markdown("🧩 Optimierte Darstellung für Mobilgeräte – Maßstab: 1 cm = 2 px")
