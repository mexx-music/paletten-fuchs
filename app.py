import streamlit as st

# =========================
# Paletten Fuchs 7 – Update
# Raster: Breite=4, Länge=25 (fix)
# Presets im Pop-up, Blumenwagen verborgen bis Toggle
# Abschluss-Logik: letzte Reihe geschlossen (3 längs bevorzugt, sonst 2 quer)
# =========================

st.set_page_config(page_title="Paletten Fuchs – v7+", layout="centered")

GRID_W = 4   # fix
GRID_L = 25  # fix

# ---------- Hilfsfunktionen ----------

def can_use_popover():
    """Prüft, ob st.popover verfügbar ist (neuere Streamlit-Versionen)."""
    return hasattr(st, "popover")

def layout_euro_auto_close(n_euro: int):
    """
    Verteilt Euro-Paletten in Reihen so, dass der hintere Abschluss geschlossen ist.
    Reihen-Typen:
      - '3L' = 3 Euro längs (bevorzugt), zählt 3 Paletten
      - '2Q' = 2 Euro quer, zählt 2 Paletten
    Strategie:
      - So viele 3L wie möglich.
      - Falls Rest = 1, ersetze ein 3L durch zwei 2Q (… -3 +2 +2), wenn möglich.
      - Reihen werden in dieser Reihenfolge gelegt; die letzte belegte Reihe ist dadurch immer geschlossen (3L oder 2Q).
    Rückgabe:
      - list[str] mit '3L'/'2Q' in Reihenfolge (max GRID_L)
      - verbrauchte Paletten (zur Kontrolle)
    """
    rows = []
    used = 0
    if n_euro <= 0:
        return rows, 0

    # maximale mögliche Reihen begrenzen
    max_rows = GRID_L

    # Zuerst Anzahl 3L-Reihen
    n3 = n_euro // 3
    r = n_euro % 3

    # Restbehandlung
    n2 = 0
    if r == 1:
        # 1 bleibt übrig -> versuche ein 3L in zwei 2Q umzuwandeln
        if n3 >= 1:
            n3 -= 1
            n2 += 2  # ersetzt 3 Paletten durch 4 Paletten-Gruppierung (2+2), ergibt Summe korrekt: -3 + 2*2 = +1 -> deckt r==1
        else:
            # kein 3L zum Tauschen; dann 2Q + (1 übrig) -> geht nicht sauber.
            # Fallback: wenn n_euro >= 2, mache nur 2Q-Reihen
            n2 = n_euro // 2
            n3 = 0
            r = n_euro % 2  # könnte 1 sein -> bleibt unplatziert, wird unten erkannt
    elif r == 2:
        n2 += 1

    # Reihen zusammenbauen: 3L bevorzugt vorne, 2Q danach
    plan = (["3L"] * n3) + (["2Q"] * n2)

    # Begrenzen auf GRID_L
    if len(plan) > max_rows:
        plan = plan[:max_rows]

    # Verbrauch berechnen
    used = plan.count("3L") * 3 + plan.count("2Q") * 2

    return plan, used

def layout_industrie(n_ind: int):
    """
    Industriepaletten (120x100) behandeln wir hier vereinfachend als '2 quer'-Äquivalent,
    d.h. pro Reihe passen 2 Industrie quer (füllen Breite=4).
    """
    rows = []
    used = 0
    if n_ind <= 0:
        return rows, 0

    max_rows = GRID_L
    n_rows = min((n_ind + 1) // 2, max_rows)  # jede Reihe: bis zu 2 Industrie
    rows = ["2Q-I"] * n_rows
    used = min(n_ind, n_rows * 2)
    return rows, used

def compose_rows(rows_euro, rows_ind):
    """
    Reihen zusammenführen:
    - Industrie-Reihen zuerst (sind exakt 2 quer = volle Breite)
    - dann Euro-Reihen nach dem Plan
    """
    rows = []
    # 1) Industrie
    rows.extend(rows_ind)
    # 2) Euro
    for r in rows_euro:
        if len(rows) >= GRID_L:
            break
        rows.append(r)
    return rows[:GRID_L]

def draw_grid(rows, n_euro_used, n_euro_total, n_ind_used, n_ind_total, show_flowers=False, n_flowers=0):
    """
    Zeichnet das 4x25 Raster in Unicode:
    - '3L': ▮ ▮ ▮ (drei schmale Blöcke linksbündig) + Randfüller ▯ (optisch)
    - '2Q': ▬ ▬ (zwei breite Blöcke, decken die volle Breite = 4 Zellen)
    - '2Q-I': ⬜ ⬜ (Industrie quer, volle Breite)
    - Leerreihe: ▁ ▁ ▁ ▁
    Hinweis: rein optisch; maßstabsgerecht im Sinne der vereinbarten Breite=4.
    """
    lines = []
    for i in range(GRID_L):
        if i < len(rows):
            r = rows[i]
            if r == "3L":
                # drei schmale, 1 Zelle frei rechts als Abschlussfüller
                line = "▮▮▮▯"
            elif r == "2Q":
                # zwei breite (= je 2 Zellen)
                line = "▬▬"
            elif r == "2Q-I":
                # Industrie quer
                line = "⬜⬜"
            else:
                line = "▁▁▁▁"
        else:
            line = "▁▁▁▁"
        lines.append(line)

    st.markdown("**Ladeplan (Draufsicht, hinten = unten):**")
    st.code("\n".join(lines), language="text")

    # Info-Balken
    st.info(
        f"Euro verwendet: {n_euro_used}/{n_euro_total} | Industrie verwendet: {n_ind_used}/{n_ind_total}"
        + (f" | Blumenwagen: {n_flowers}" if show_flowers and n_flowers > 0 else "")
    )

def capacity_check(n_euro, n_ind):
    """
    Grobe Kapazitätsprüfung pro Reihe:
      - 3L -> 3 Euro
      - 2Q -> 2 Euro
      - 2Q-I -> 2 Industrie
    Max-Kapazität (nur Euro) wäre 25 * 3 = 75 als Obergrenze.
    Mischen wir Euro + Industrie, reservieren wir zuerst Reihen für Industrie, dann für Euro.
    """
    # Erst Industrie: jede Reihe 2 Industrie
    max_ind_rows = GRID_L
    max_ind_cap = max_ind_rows * 2

    if n_ind > max_ind_cap:
        return False, f"Platz reicht nicht: {n_ind} Industrie > {max_ind_cap} möglich."

    # Reihen übrig für Euro
    euro_rows_possible = GRID_L - ((n_ind + 1) // 2)
    max_euro_cap = euro_rows_possible * 3  # 3L als Obergrenze
    if n_euro > max_euro_cap:
        return False, f"Platz reicht nicht: {n_euro} Euro > {max_euro_cap} möglich (bei {euro_rows_possible} Euro-Reihen)."

    return True, ""

# ---------- UI: Header ----------
st.title("📦 Paletten Fuchs – Sattelzug Ladeplan (Unicode)")

# ---------- UI: Presets im Pop-up ----------
open_fn = st.popover if can_use_popover() else st.expander
with open_fn("🎛️ Presets & Schnellwahl"):
    preset = st.selectbox(
        "Preset wählen:",
        [
            "— kein Preset —",
            "20 Euro (Auto-Abschluss)",
            "24 Euro (Auto-Abschluss)",
            "20 Euro + 8 Industrie",
            "30 Euro (gemischt erlaubt)",
        ],
        index=0,
    )
    apply = st.button("Preset anwenden")

# ---------- Eingaben ----------
col_left, col_right = st.columns(2)

with col_left:
    euro = st.number_input("Euro-Paletten (120×80)", min_value=0, max_value=200, value=20, step=1)
    ind = st.number_input("Industrie-Paletten (120×100)", min_value=0, max_value=200, value=0, step=1)

with col_right:
    # Blumenwagen über kleines Icon/Toggle aus- und einblenden
    show_flowers = st.checkbox("🌼 Blumenwagen anzeigen", value=False)
    flowers = 0
    if show_flowers:
        flowers = st.number_input("Blumenwagen (optional)", min_value=0, max_value=200, value=0, step=1)

# Preset anwenden
if apply and preset != "— kein Preset —":
    if preset == "20 Euro (Auto-Abschluss)":
        euro, ind, flowers = 20, 0, 0
    elif preset == "24 Euro (Auto-Abschluss)":
        euro, ind, flowers = 24, 0, 0
    elif preset == "20 Euro + 8 Industrie":
        euro, ind, flowers = 20, 8, 0
    elif preset == "30 Euro (gemischt erlaubt)":
        euro, ind, flowers = 30, 0, 0
    st.success(f"Preset gesetzt: {preset}")

st.markdown(f"**Raster:** Breite = {GRID_W}, Länge = {GRID_L} (fix)")

# ---------- Kapazität prüfen ----------
ok, msg = capacity_check(euro, ind)
if not ok:
    st.error(msg)
    st.stop()

# ---------- Layout berechnen ----------
rows_ind, used_ind = layout_industrie(ind)
rows_euro, used_euro = layout_euro_auto_close(euro)

# Falls Euro nicht komplett untergebracht -> Hinweis (sollte durch capacity_check selten passieren)
if used_euro < euro:
    st.warning(f"Nicht alle Euro-Paletten konnten platziert werden: {used_euro}/{euro}. "
               f"Erhöhe ggf. die Länge (aktuell {GRID_L}) oder reduziere die Menge.")

# Reihen zusammenführen und zeichnen
rows = compose_rows(rows_euro, rows_ind)
draw_grid(rows, used_euro, euro, used_ind, ind, show_flowers, flowers)

# ---------- Hinweise ----------
with st.expander("ℹ️ Hinweise zur Darstellung"):
    st.markdown("""
- **3 längs (Euro)**: `▮▮▮▯` – drei schmale Blöcke (rechts optischer Abschlussfüller).
- **2 quer (Euro)**: `▬▬` – zwei breite Blöcke (füllen Breite=4).
- **Industrie quer**: `⬜⬜` – zwei breite Kästen (füllen Breite=4).
- Leere Reihe: `▁▁▁▁`.

**Abschluss-Logik:** Der Algorithmus vermeidet einen Rest von 1 Euro-Palette
und erzwingt hinten immer eine geschlossene Reihe (3 längs bevorzugt, sonst 2 quer).
    """)
