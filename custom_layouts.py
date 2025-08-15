# --- NEU: Eigene Layouts (Option der Haupt-App) ---
import streamlit as st
from custom_layouts import render_manager, get_active_meta

# Schalter im Haupt-UI (standardmäßig AUS, damit UI clean bleibt)
enable_custom = st.toggle("Eigene Layouts (Vers 1–4) nutzen", value=False, help="Manuell zusammenstellen & speichern.")

custom_layout_cm = []
if enable_custom:
    # Rendert Manager im Expander und gibt aktuelle Liste (cm) zurück
    custom_layout_cm = render_manager(title="Eigene Layouts (Vers 1–4)", show_expander=True)

# ... später in deiner Berechnungs-/Darstellungslogik:
# Wenn enable_custom aktiv ist und es ein Layout gibt, nutze es bevorzugt:
if enable_custom and custom_layout_cm:
    # Beispiel: an deinen Unicode-Renderer übergeben
    # unicode_render(custom_layout_cm)
    # Beispiel: Achslast grob berechnen (Hebelarme aus x_cm)
    # axle_result = axle_estimate(custom_layout_cm)
    st.success(f"Custom-Layout aktiv: {len(custom_layout_cm)} Objekte werden verwendet.")
else:
    # Fallback: deine bisherige Auto-/Variant-Logik
    st.info("Custom-Layout aus – benutze Standard-Varianten/Auto-Platzierung.")
