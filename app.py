import streamlit as st

st.set_page_config(page_title="🦊 Paletten Fuchs – Unicode Clean", layout="centered")
st.title("🦊 Paletten Fuchs – Unicode Ladeplan")

st.markdown("### 📦 Optimale Belegung für 30 Euro-Paletten (Unicode-Anzeige)")

# ⬛ Euro längs, ▭ Euro quer, ⬜ Industrie quer
# Em-spaces for Abstand:   = " "

ladeplan = [
    "    ▭    ",                     # 1 quer mittig
    "  ▭      ▭",                    # 2 quer nebeneinander mit Abstand
    "▮ ▮ ▮",                          # Reihe 1
    "▮ ▮ ▮",                          # Reihe 2
    "▮ ▮ ▮",                          # Reihe 3
    "▮ ▮ ▮",                          # Reihe 4
    "▮ ▮ ▮",                          # Reihe 5
    "▮ ▮ ▮",                          # Reihe 6
    "▮ ▮ ▮",                          # Reihe 7
    "▮ ▮ ▮",                          # Reihe 8
    "▮ ▮ ▮"                           # Reihe 9
]

# Gewicht optional
with st.expander("⚖️ Gewichtsdaten anzeigen"):
    gesamtgewicht = st.number_input("Gesamtgewicht (kg)", min_value=0, value=7500)
    st.write(f"📦 Durchschnitt pro Palette: {gesamtgewicht // 30} kg")

# Ladeplan anzeigen
st.markdown("### 🗺️ Unicode-Ladeplan (von oben – vorne → hinten)")
for zeile in ladeplan:
    st.markdown(f"<pre style='font-size:26px'>{zeile}</pre>", unsafe_allow_html=True)

# Legende
st.markdown("### 🔎 Legende:")
st.markdown("- ▭ = Euro quer")
st.markdown("- ▮ = Euro längs")
st.markdown("- ⬜ = Industrie quer (nicht im Beispiel)")
