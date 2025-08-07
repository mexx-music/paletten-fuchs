
import streamlit as st

st.set_page_config(page_title="🟧 Paletten Fuchs – Einzel-Symbol ▭ + Slider", layout="centered")
st.title("🟧 Paletten Fuchs – Einzelsymbol ▭ mit Schieberegler")

st.markdown("### 🎛️ Feinjustierung: Einzelnes Rechteck-Symbol (▭)")

# Slider für Einrückung
offset = st.slider("Leerzeichen vor ▭ (Querpalette)", 0, 10, 2)

# Ein einzelnes Symbol ▭, eingerückt
euro_quer_oben = " " * offset + "▭"
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
st.markdown("✅ Test mit nur einem Rechteck ▭ oben – exakt positionierbar.")
