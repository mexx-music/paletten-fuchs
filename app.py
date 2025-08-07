import streamlit as st

st.set_page_config(page_title="🦊 Paletten Fuchs – Unicode-Version", layout="centered")
st.title("🦊 Paletten Fuchs – Ladeplan (Unicode Darstellung)")

st.markdown("### 📥 Beispielladung: 30 Euro-Paletten")

# Fest definierte Unicode-Ladeplan-Zeilen
ladeplan = [
    "     ▭     ",         # 1 quer mittig
    "   ▭    ▭   ",         # 2 quer nebeneinander mit Abstand, nicht über Industriebreite hinaus
    "▮ ▮ ▮",                 # Reihe 1 Euro längs
    "▮ ▮ ▮",                 # Reihe 2 Euro längs
    "▮ ▮ ▮",                 # Reihe 3 Euro längs
    "▮ ▮ ▮",                 # Reihe 4 Euro längs
    "▮ ▮ ▮",                 # Reihe 5 Euro längs
    "▮ ▮ ▮",                 # Reihe 6 Euro längs
    "▮ ▮ ▮",                 # Reihe 7 Euro längs
    "▮ ▮ ▮",                 # Reihe 8 Euro längs
    "▮ ▮ ▮",                 # Reihe 9 Euro längs
]

# Optional: Gewichtseingabe
with st.expander("⚖️ Gewichtsdaten anzeigen"):
    gesamtgewicht = st.number_input("Gesamtgewicht (kg)", min_value=0, value=7500)
    st.write(f"📦 Durchschnitt pro Palette: {gesamtgewicht // 30} kg")

# Ladeplan anzeigen
st.markdown("### 🗺️ Ladeplan (Draufsicht – vorne → hinten)")
for zeile in ladeplan:
    st.markdown(f"<pre style='font-size:24px'>{zeile}</pre>", unsafe_allow_html=True)

# Legende
st.markdown("### 🔎 Legende:")
st.markdown("- ▭ = Euro quer")
st.markdown("- ▮ = Euro längs")
st.markdown("- ⬜ = Industrie quer (nicht im Beispiel)")
