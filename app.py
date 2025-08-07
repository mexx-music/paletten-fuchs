
import streamlit as st

st.set_page_config(page_title="🟧 Paletten Fuchs – Alternative Symbole", layout="centered")
st.title("🟧 Paletten Fuchs – Gleicher Aufbau mit Symbol „–“")

st.markdown("### 📦 Darstellung wie zuvor – mit anderem Symbol für quer")

# Verwendung des Bindestrichs – für flachere Quer-Palette
euro_quer_oben = "  –"
euro_l1 = "▮ ▮ ▮"
euro_l2 = "▮ ▮ ▮"
industrie = "⬜ ⬜"

st.subheader("🔲 Ladeflächenansicht:")
st.markdown(f"""
```
{euro_quer_oben}
{euro_l1}
{euro_l2}
{industrie}
```
""")

if st.checkbox("⚖️ Gewicht anzeigen"):
    gewicht_euro = st.number_input("Gewicht pro Euro (kg)", 1, 1500, 500)
    gewicht_ind = st.number_input("Gewicht pro Industrie (kg)", 1, 1500, 600)
    gesamt = 7 * gewicht_euro + 2 * gewicht_ind
    st.success(f"🔩 Gesamtgewicht: {gesamt:,} kg")

st.markdown("---")
st.markdown("🛠️ Querpalette oben jetzt mit Symbol: „–“ statt „▬“")
