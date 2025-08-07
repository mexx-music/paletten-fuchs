
import streamlit as st

st.set_page_config(page_title="🟧 Paletten Fuchs – Alle Symbole verschiebbar", layout="centered")
st.title("🟧 Paletten Fuchs – Feinjustierung aller Palettentypen")

st.markdown("### 🎛️ Alle Palettenpositionen individuell verschiebbar")

# Slider für alle Symbole
offset_q1 = st.slider("Leerzeichen vor Querpalette 1 (▭)", 0, 20, 2)
offset_q2 = st.slider("Leerzeichen vor Querpalette 2 (▭)", 0, 20, 6)
offset_i1 = st.slider("Leerzeichen vor Industriepalette 1 (⬜)", 0, 20, 0)
offset_i2 = st.slider("Leerzeichen vor Industriepalette 2 (⬜)", 0, 20, 4)

# Zeilenaufbau
euro_quer_1 = " " * offset_q1 + "▭"
euro_quer_2 = " " * offset_q2 + "▭"
euro_l1 = "▮ ▮ ▮"
euro_l2 = "▮ ▮ ▮"
industrie_1 = " " * offset_i1 + "⬜"
industrie_2 = " " * offset_i2 + "⬜"

st.subheader("🔲 Ladeflächenansicht:")
st.markdown(f"""
```
{euro_quer_1}
{euro_quer_2}
{euro_l1}
{euro_l2}
{industrie_1}
{industrie_2}
```
""")

if st.checkbox("⚖️ Gewicht anzeigen"):
    gewicht_euro = st.number_input("Gewicht pro Euro (kg)", 1, 1500, 500)
    gewicht_ind = st.number_input("Gewicht pro Industrie (kg)", 1, 1500, 600)
    euro_gesamt = 6 * gewicht_euro
    ind_gesamt = 2 * gewicht_ind
    gesamt = euro_gesamt + ind_gesamt
    st.success(f"🔩 Gesamtgewicht: {gesamt:,} kg")

st.markdown("---")
st.markdown("✅ Jede Palette ist einzeln verschiebbar – feines Layout möglich.")
