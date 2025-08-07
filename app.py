
import streamlit as st
import math

st.set_page_config(page_title="🟧 Paletten Fuchs – Fixgrafik + Berechnung", layout="centered")
st.title("🟧 Paletten Fuchs – Grafik + Palettenberechnung")

st.markdown("### 📦 Fixe Palettengrafik (optisch)")

# Fixes Layout
euro_quer_left = "▭"
euro_quer_mid = "  ▭"
euro_quer_right = "    ▭"
euro_l1 = "▮ ▮ ▮"
euro_l2 = "▮ ▮ ▮"
industrie_left = "⬜"
industrie_right = "   ⬜"

st.markdown(f"""
```
{euro_quer_left}
{euro_quer_mid}
{euro_quer_right}
{euro_l1}
{euro_l2}
{industrie_left}
{industrie_right}
```
""")

st.markdown("### 📏 Palettenberechnung")

ladeflaeche_m = st.number_input("Ladeflächenlänge (in Metern)", 1.0, 20.0, 13.6, step=0.1)
palettenlaenge_m = 1.2  # Euro-Palettenlänge
anzahl_euro = int(ladeflaeche_m // palettenlaenge_m)

st.success(f"🧮 Es passen ca. **{anzahl_euro} Euro-Paletten** längs nebeneinander.")

if st.checkbox("⚖️ Gewicht anzeigen"):
    gewicht_pro = st.number_input("Gewicht pro Palette (kg)", 1, 1500, 500)
    gesamt = anzahl_euro * gewicht_pro
    st.success(f"🔩 Gesamtgewicht: {gesamt:,} kg")

st.markdown("---")
st.markdown("✅ Optische Vorschau + Längsberechnung für Euro-Paletten (1,20 m)")
