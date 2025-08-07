
import streamlit as st

st.set_page_config(page_title="🟧 Paletten Fuchs – Symbolbreite Test", layout="centered")
st.title("🟧 Paletten Fuchs – Breites Symbol für Querpalette")

st.markdown("### 📦 Darstellung mit ▭▭ oben")

# Neue Darstellung mit breiterem Symbol
euro_quer_oben = "  ▭▭"  # 2 Leerzeichen + breites Symbol
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
st.markdown("🧪 Test: Obere Palette mit Symbol ▭▭ für breitere Darstellung")
