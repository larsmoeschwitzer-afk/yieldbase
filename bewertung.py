#!/usr/bin/env python3
"""
YieldBase v4 — Immobilien-Investment-Analyse
Python/Streamlit · GitHub-kompatibel

v4 Änderungen gemäß Spezifikation:
  • Alle Emojis/Icons aus UI entfernt — professionelles, cleanes Design
  • Exakte monatliche Annuitätenberechnung (Zins = Restschuld × Zinssatz/12)
  • Sanity-Checks: Zins + Tilgung = Monatsrate (Abfang von Rundungsfehlern)
  • Kaufpreisaufteilung-Expander für alle Modi (Grundstück/Gebäude)
  • Pro-Modus: Steuerliche Betrachtung (Jahr 1) + 10-Jahres-Prognose
  • Konsequente help-Texte auf allen Inputs und Metriken
  • round(v, 2) für alle Währungsberechnungen (kein Float-Artefakt)
  • Progressive Disclosure: Einsteiger / Experte / Pro
"""

import streamlit as st

st.set_page_config(
    page_title="YieldBase | Immobilien-Investment-Analyse",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════
# 1. KONSTANTEN
# ══════════════════════════════════════════════════════════════════════

BUNDESLAND_GEST: dict[str, float] = {
    "Bayern": 3.5,            "Sachsen": 3.5,
    "Hamburg": 5.5,
    "Baden-Württemberg": 5.0, "Bremen": 5.0,
    "Niedersachsen": 5.0,     "Rheinland-Pfalz": 5.0,
    "Sachsen-Anhalt": 5.0,
    "Berlin": 6.0,            "Hessen": 6.0,
    "Mecklenburg-Vorp.": 6.0,
    "Brandenburg": 6.5,       "NRW": 6.5,
    "Saarland": 6.5,          "Schleswig-Holstein": 6.5,
    "Thüringen": 6.5,
}

# AfA-Sätze nach § 7 Abs. 4 EStG
AFA_REGELN = [
    {"von": 2023, "satz": 3.0, "label": "3,0 % – Neubau ab 2023",
     "basis": "§ 7 Abs. 4 S.1 Nr. 1 EStG",
     "note":  "Lineare AfA über 33,3 J. Gilt für Fertigstellung ab 01.01.2023."},
    {"von": 1925, "satz": 2.0, "label": "2,0 % – Standard-AfA",
     "basis": "§ 7 Abs. 4 S.1 Nr. 2a EStG",
     "note":  "Lineare AfA über 50 J. Gilt für Baujahr 1925–2022."},
    {"von": 0,    "satz": 2.5, "label": "2,5 % – Altbau vor 1925",
     "basis": "§ 7 Abs. 4 S.1 Nr. 2b EStG",
     "note":  "Lineare AfA über 40 J. für Gebäudesubstanz vor 1925."},
]

# Pro-Modus: AfA-Optionen (Selectbox-Werte)
PRO_AFA_OPTIONEN = {"2,0 %": 2.0, "2,5 %": 2.5, "3,0 %": 3.0}

# CSS-Klassen für Ampel — keine Inline-Farben → dark-mode-kompatibel
AMPEL = {
    "g": {"cls": "yb-g", "t": "Gut"},
    "y": {"cls": "yb-y", "t": "Prüfen"},
    "r": {"cls": "yb-r", "t": "Kritisch"},
}

# ══════════════════════════════════════════════════════════════════════
# 2. DESIGN-SYSTEM — vollständig adaptiv (Light & Dark)
# ══════════════════════════════════════════════════════════════════════

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* Design-Token Light */
:root {
  --yb-font:  'Inter', -apple-system, 'Segoe UI', sans-serif;
  --yb-mono:  'JetBrains Mono', 'Fira Code', monospace;
  --fs-xs:   10px; --fs-sm: 12px; --fs-base: 13px; --fs-md: 14px;
  --fs-lg:   16px; --fs-xl: 20px; --fs-2xl:  24px; --fs-3xl: 30px;
  --gold:    #b8902a; --gold-bg: rgba(184,144,42,.09); --gold-br: rgba(184,144,42,.25);
  --c-g: #166534; --bg-g: rgba(22,101,52,.09);   --br-g: rgba(22,101,52,.28);
  --c-y: #b45309; --bg-y: rgba(180,83,9,.09);    --br-y: rgba(180,83,9,.28);
  --c-r: #9f1239; --bg-r: rgba(159,18,57,.09);   --br-r: rgba(159,18,57,.28);
}

/* Dark-Mode (OS) */
@media (prefers-color-scheme: dark) {
  :root {
    --gold: #d4aa3e; --gold-bg: rgba(212,170,62,.12); --gold-br: rgba(212,170,62,.32);
    --c-g: #4ade80; --bg-g: rgba(74,222,128,.12);   --br-g: rgba(74,222,128,.3);
    --c-y: #fbbf24; --bg-y: rgba(251,191,36,.12);   --br-y: rgba(251,191,36,.3);
    --c-r: #fb7185; --bg-r: rgba(251,113,133,.12);  --br-r: rgba(251,113,133,.3);
  }
}
[data-theme="dark"] {
  --gold: #d4aa3e !important; --gold-bg: rgba(212,170,62,.12) !important;
  --c-g: #4ade80 !important;  --bg-g: rgba(74,222,128,.12) !important;  --br-g: rgba(74,222,128,.3) !important;
  --c-y: #fbbf24 !important;  --bg-y: rgba(251,191,36,.12) !important;  --br-y: rgba(251,191,36,.3) !important;
  --c-r: #fb7185 !important;  --bg-r: rgba(251,113,133,.12) !important; --br-r: rgba(251,113,133,.3) !important;
}

/* Ampel-Klassen */
.yb-g { --amp-c: var(--c-g); --amp-bg: var(--bg-g); --amp-br: var(--br-g); }
.yb-y { --amp-c: var(--c-y); --amp-bg: var(--bg-y); --amp-br: var(--br-y); }
.yb-r { --amp-c: var(--c-r); --amp-bg: var(--bg-r); --amp-br: var(--br-r); }

/* Basis */
html, body, [class*="css"] { font-family: var(--yb-font) !important; font-size: var(--fs-base); }
.main .block-container { padding: 1.2rem 1.8rem 2rem; max-width: 1380px; }

/* KPI-Karte */
.kpi {
  background: var(--background-color, #fff); border-radius: 10px; padding: 12px 14px;
  border: 1px solid rgba(128,128,128,.15); position: relative; overflow: hidden;
  margin-bottom: 4px; box-shadow: 0 1px 3px rgba(0,0,0,.06); transition: border-color .15s;
}
.kpi.yb-g, .kpi.yb-y, .kpi.yb-r { border-color: var(--amp-br); }
.kpi-bar { position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--amp-c); }
.kpi-lbl { font-size: var(--fs-xs); font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; margin-bottom: 6px; color: var(--amp-c, color-mix(in srgb, var(--text-color, #666) 70%, transparent)); }
.kpi:not(.yb-g):not(.yb-y):not(.yb-r) .kpi-lbl { color: color-mix(in srgb, var(--text-color, #888) 65%, transparent); }
.kpi-val { font-family: var(--yb-mono); font-size: var(--fs-xl); font-weight: 700;
  line-height: 1; color: var(--amp-c, var(--text-color, #111)); }
.kpi:not(.yb-g):not(.yb-y):not(.yb-r) .kpi-val { color: var(--text-color, #111); }
.kpi-sm .kpi-val, .kpi-val.kpi-sm { font-size: var(--fs-lg) !important; }
.kpi-sub { font-size: var(--fs-sm); margin-top: 4px;
  color: color-mix(in srgb, var(--text-color, #999) 55%, transparent); }
.kpi-badge { position: absolute; top: 10px; right: 8px; font-size: 9px; font-weight: 700;
  border-radius: 4px; padding: 2px 6px; color: var(--amp-c); background: var(--amp-bg); }

/* Status-Bar */
.sb-wrap { display: grid; grid-template-columns: repeat(6, 1fr);
  background: var(--secondary-background-color, #f7f6f3);
  border-radius: 10px; border: 1px solid rgba(128,128,128,.14); margin-bottom: 18px; overflow: hidden; }
.sb-cell { text-align: center; padding: 10px 0; border-right: 1px solid rgba(128,128,128,.1); }
.sb-cell:last-child { border-right: none; }
.sb-lbl { font-size: var(--fs-xs); font-weight: 600; letter-spacing: .05em; text-transform: uppercase;
  margin-bottom: 3px; color: color-mix(in srgb, var(--text-color, #888) 55%, transparent); }
.sb-val { font-family: var(--yb-mono); font-size: var(--fs-base); font-weight: 700; color: var(--gold); }

/* KNK-Tabelle */
.knk { border-radius: 8px; overflow: hidden; border: 1px solid var(--gold-br); margin-top: 8px; }
.knk-head { background: var(--gold-bg); padding: 6px 12px; font-size: var(--fs-xs);
  color: var(--gold); font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
  border-bottom: 1px solid var(--gold-br); }
.knk-row { display: flex; justify-content: space-between; padding: 7px 12px;
  font-size: var(--fs-base); border-bottom: 1px solid rgba(128,128,128,.08); color: var(--text-color, #333); }
.knk-row:nth-child(even) { background: color-mix(in srgb, var(--secondary-background-color, #f7f6f3) 60%, transparent); }
.knk-total { background: var(--gold-bg) !important; font-weight: 700; color: var(--gold) !important;
  border-top: 2px solid var(--gold-br); border-bottom: none; }
.knk-lbl { color: color-mix(in srgb, var(--text-color, #666) 70%, transparent); }
.knk-vals { display: flex; gap: 16px; }
.mono { font-family: var(--yb-mono); }

/* AfA-Badge */
.afa-badge { background: var(--gold-bg); border: 1px solid var(--gold-br); border-radius: 8px;
  padding: 10px 12px; margin-top: 8px; display: flex; gap: 10px; align-items: flex-start; }
.afa-icon  { font-size: 18px; flex-shrink: 0; line-height: 1.4; }
.afa-title { font-size: var(--fs-sm); font-weight: 700; color: var(--gold); margin-bottom: 3px; }
.afa-basis { font-size: var(--fs-sm); margin-bottom: 2px;
  color: color-mix(in srgb, var(--text-color, #666) 70%, transparent); }
.afa-note  { font-size: var(--fs-sm); color: color-mix(in srgb, var(--text-color, #999) 55%, transparent); }

/* Summary-Banner */
.sum-wrap { background: var(--gold-bg); border: 1px solid var(--gold-br);
  border-radius: 12px; padding: 18px 20px; margin-bottom: 12px; }
.sum-label { font-size: var(--fs-xs); font-weight: 600; letter-spacing: .06em; text-transform: uppercase;
  margin-bottom: 4px; color: color-mix(in srgb, var(--text-color, #999) 55%, transparent); }
.sum-total { font-family: var(--yb-mono); font-size: var(--fs-3xl); font-weight: 700;
  color: var(--gold); line-height: 1; }
.sum-grid  { display: flex; gap: 20px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--gold-br); }
.sum-sub-lbl { font-size: var(--fs-xs); font-weight: 600; letter-spacing: .05em; text-transform: uppercase;
  margin-bottom: 3px; color: color-mix(in srgb, var(--text-color, #999) 50%, transparent); }
.sum-sub-val { font-family: var(--yb-mono); font-size: var(--fs-base); font-weight: 700; color: var(--text-color, #111); }

/* Info-Box */
.info-box { background: var(--secondary-background-color, #f7f6f3); border-left: 3px solid var(--gold);
  border-radius: 0 6px 6px 0; padding: 7px 11px; margin-top: 6px; font-size: var(--fs-sm);
  color: color-mix(in srgb, var(--text-color, #666) 75%, transparent); line-height: 1.5; }
.info-strong { font-weight: 700; color: var(--gold); }

/* Divider */
.div-wrap { display: flex; align-items: center; gap: 10px; margin: 18px 0 12px; }
.div-line  { flex: 1; height: 1px; background: var(--gold); opacity: .25; }
.div-lbl   { font-size: var(--fs-xs); color: var(--gold); font-weight: 700;
  text-transform: uppercase; letter-spacing: .1em; white-space: nowrap; }

/* Bericht-Zeile */
.rep-section-head { font-size: var(--fs-xs); font-weight: 700; text-transform: uppercase;
  letter-spacing: .1em; color: var(--gold); padding: 6px 0;
  border-bottom: 2px solid var(--gold-br); margin: 18px 0 8px; }
.rep-row { display: flex; justify-content: space-between; align-items: center;
  padding: 7px 8px; border-radius: 4px; border-bottom: 1px solid rgba(128,128,128,.07);
  font-size: var(--fs-base); color: var(--text-color, #333); }
.rep-row:nth-child(even) { background: color-mix(in srgb, var(--secondary-background-color, #f7f6f3) 50%, transparent); }
.rep-lbl { color: color-mix(in srgb, var(--text-color, #888) 70%, transparent); }
.rep-note { font-size: var(--fs-sm); margin-right: 10px;
  color: color-mix(in srgb, var(--text-color, #aaa) 50%, transparent); }
.rep-val { font-family: var(--yb-mono); font-size: var(--fs-base); font-weight: 600; color: var(--text-color, #111); }

/* Szenario-Tabelle */
.sc-table { width: 100%; border-collapse: collapse; font-size: var(--fs-base); }
.sc-table th { padding: 8px 12px; font-size: var(--fs-xs); text-transform: uppercase;
  letter-spacing: .05em; font-weight: 700; border-bottom: 1px solid rgba(128,128,128,.15);
  background: var(--secondary-background-color, #f7f6f3);
  color: color-mix(in srgb, var(--text-color, #888) 65%, transparent); }
.sc-table td { padding: 7px 12px; border-bottom: 1px solid rgba(128,128,128,.07); color: var(--text-color, #333); }
.sc-table tr:nth-child(even) td { background: color-mix(in srgb, var(--secondary-background-color, #f7f6f3) 50%, transparent); }

/* Disclaimer */
.disclaimer { font-size: var(--fs-sm); line-height: 1.6; border-radius: 7px;
  padding: 10px 12px; margin-top: 12px; background: var(--secondary-background-color, #f7f6f3);
  color: color-mix(in srgb, var(--text-color, #aaa) 55%, transparent); }

/* Header */
.yb-header { background: var(--secondary-background-color, #f7f6f3);
  border-bottom: 1px solid rgba(128,128,128,.15); padding: .8rem 1.5rem;
  margin: -1.2rem -1.8rem 1.4rem; display: flex; align-items: center; gap: .8rem;
  box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.yb-logo { font-family: var(--yb-font); font-size: 18px; font-weight: 700;
  color: var(--text-color, #111); letter-spacing: -.02em; }
.yb-sub  { font-size: var(--fs-xs); color: var(--gold); letter-spacing: .1em;
  text-transform: uppercase; font-weight: 700; }

/* Streamlit-Widget-Overrides */
html, body, [class*="css"] { font-family: var(--yb-font) !important; }
[data-testid="stMetricValue"] { font-family: var(--yb-mono) !important; font-size: var(--fs-xl) !important; }
[data-testid="stMetricLabel"] { font-size: var(--fs-xs) !important; text-transform: uppercase !important;
  letter-spacing: .05em !important; font-weight: 600 !important; }
[data-testid="stMetricDelta"] { font-size: var(--fs-sm) !important; }
.stTabs [data-baseweb="tab-list"] { background: var(--secondary-background-color, #f7f6f3);
  border-radius: 9px; padding: 4px; gap: 3px; border: 1px solid rgba(128,128,128,.12); }
.stTabs [data-baseweb="tab"] { border-radius: 7px; font-size: var(--fs-base); font-weight: 500;
  color: color-mix(in srgb, var(--text-color, #888) 70%, transparent); }
.stTabs [aria-selected="true"] { background: var(--background-color, #fff) !important;
  color: var(--text-color, #111) !important; font-weight: 600 !important;
  box-shadow: 0 1px 3px rgba(0,0,0,.08) !important; }
[data-testid="stSidebar"] > div:first-child { padding: 1.2rem 1rem; }
</style>
"""

# ══════════════════════════════════════════════════════════════════════
# 3. FORMAT-HELFER — kaufmännische Rundung auf 2 Dezimalstellen
# ══════════════════════════════════════════════════════════════════════

def fmt_eur(v) -> str:
    """Formatiert einen Wert als Euro-Betrag (de-DE, 2 Dezimalstellen intern)."""
    try:
        v = float(v)
        if not np.isfinite(v): return "—"
    except (TypeError, ValueError): return "—"
    sign = "−" if v < 0 else ""
    a = abs(v)
    if a >= 1_000_000: return f"{sign}{a / 1_000_000:.2f}".replace(".", ",") + " Mio. €"
    return f"{sign}{a:,.0f} €".replace(",", ".")

def fmt_pct(v, dec: int = 2) -> str:
    try:
        if not np.isfinite(float(v)): return "—"
        return f"{float(v):.{dec}f}".replace(".", ",") + " %"
    except (TypeError, ValueError): return "—"

def fmt_x(v) -> str:
    try:
        f = float(v)
        if not np.isfinite(f) or f > 99: return "> 99x"
        return f"{f:.1f}".replace(".", ",") + "x"
    except (TypeError, ValueError): return "—"

def fmt_yr(v) -> str:
    try:
        f = float(v)
        if not np.isfinite(f) or f > 99: return "n.v."
        return f"{f:.1f}".replace(".", ",") + " J."
    except (TypeError, ValueError): return "—"

# ══════════════════════════════════════════════════════════════════════
# 4. CALC ENGINE
# ══════════════════════════════════════════════════════════════════════

def get_afa_info(baujahr: int) -> dict:
    """Ermittelt AfA-Satz + rechtliche Grundlage aus dem Baujahr (§ 7 EStG)."""
    for r in AFA_REGELN:
        if baujahr >= r["von"]:
            return r
    return AFA_REGELN[-1]


def calc_ihr(kaufpreis: float, baujahr: int) -> float:
    """
    Instandhaltungsrücklage (IHR) — kaufpreisbasierte Näherung, baualtersgestaffelt.
    Methodisch: % des Kaufpreises; in Teuerlagen ggf. überschätzt.
    """
    age = datetime.now().year - baujahr
    if age < 10:  return kaufpreis * 0.003
    if age < 25:  return kaufpreis * 0.006
    if age < 40:  return kaufpreis * 0.010
    return kaufpreis * 0.013


def calc_irr(initial: float, cashflows: list) -> float:
    """Interner Zinsfuß via Newton-Raphson."""
    rate = 0.08
    for _ in range(300):
        f, df = initial, 0.0
        for t, c in enumerate(cashflows):
            p = (1.0 + rate) ** (t + 1)
            f  += c / p
            df -= (t + 1) * c / (p * (1.0 + rate))
        if abs(df) < 1e-12: break
        rn = rate - f / df
        if abs(rn - rate) < 1e-6: return rn * 100.0
        rate = min(max(rn, -0.999), 50.0)
    return rate * 100.0


def calc_npv(initial: float, cashflows: list, rate: float) -> float:
    return initial + sum(c / (1.0 + rate) ** (t + 1) for t, c in enumerate(cashflows))


def calc_monat(restschuld: float, monatsrate: float,
               zins_rate_m: float) -> tuple[float, float, float]:
    """
    Berechnet einen Monat des Annuitätendarlehens mit Sanity-Check.

    Formeln (gem. Spezifikation):
        Zins     = Restschuld × Zinssatz / 12
        Tilgung  = Monatsrate − Zinsanteil
        Neue RS  = Restschuld − Tilgung  (min. 0)

    Sanity-Check: |Zins + Tilgung − Monatsrate| ≤ 0,01 €.
    Bei Überschreitung wird die Tilgung exakt korrigiert.

    Returns: (zins_m, tilgung_m, neue_restschuld) — alle auf 2 Dezimalstellen.
    """
    zins_m    = round(restschuld * zins_rate_m, 2)
    tilgung_m = round(monatsrate - zins_m, 2)

    # Sanity-Check: Summe muss der Monatsrate entsprechen
    differenz = abs(round(zins_m + tilgung_m, 2) - monatsrate)
    if differenz > 0.01:
        # Präzise Korrektur: Tilgung wird exakt aus der Differenz bestimmt
        tilgung_m = round(monatsrate - zins_m, 2)

    neue_restschuld = max(0.0, round(restschuld - tilgung_m, 2))
    return zins_m, tilgung_m, neue_restschuld


def calc_all(p: dict) -> dict:
    """
    Master-Berechnung aller Standard-KPIs.
    Projektion verwendet exakte monatliche Annuitätenberechnung.
    Alle Werte auf 2 Dezimalstellen gerundet (kaufmännisch).
    """
    kp = p["kaufpreis"]

    # ── Transaktion ──────────────────────────────────────────────────
    knk_pct    = round(p["gest"] + p["notar"] + p["makler"], 4)
    gest_abs   = round(kp * p["gest"]   / 100, 2)
    notar_abs  = round(kp * p["notar"]  / 100, 2)
    makler_abs = round(kp * p["makler"] / 100, 2)
    knk_abs    = round(kp * knk_pct     / 100, 2)
    gesamt     = round(kp + knk_abs, 2)

    # ── AfA ──────────────────────────────────────────────────────────
    afa_info  = get_afa_info(p["baujahr"])
    afa_basis = round(gesamt * p["gebaeude"] / 100, 2)
    if p["is_denkmal"]:
        san           = round(afa_basis * p["dk_san"] / 100, 2)
        afa           = round((afa_basis - san) * 0.02 + san * p["dk_afa"] / 100, 2)
        afa_rate_used = None
    else:
        afa_rate_used = p["afa_override"] if p["afa_manual"] else afa_info["satz"]
        afa           = round(afa_basis * afa_rate_used / 100, 2)

    # ── Erträge ──────────────────────────────────────────────────────
    bew_k    = round(p["jahresmiete"] * p["bew"]       / 100, 2)
    leer_abs = round(p["jahresmiete"] * p["leerstand"] / 100, 2)
    ihr_val  = round(calc_ihr(kp, p["baujahr"]), 2)
    noi      = round(p["jahresmiete"] - bew_k - ihr_val, 2)
    netto    = round(p["jahresmiete"] - bew_k - leer_abs - ihr_val, 2)

    brutto   = round(p["jahresmiete"] / kp * 100, 2) if kp else 0.0
    faktor   = round(kp / p["jahresmiete"], 1)        if p["jahresmiete"] else 0.0
    netto_r  = round(netto / gesamt * 100, 2)          if gesamt else 0.0
    cap_rate = round(noi   / kp     * 100, 2)          if kp     else 0.0

    # ── Finanzierung ─────────────────────────────────────────────────
    ek_abs    = round(gesamt * p["ek"] / 100, 2)
    fk        = round(gesamt - ek_abs, 2)
    annuitaet = round(fk * (p["zins"] + p["tilgung"]) / 100, 2)  # Jahresannuität
    monatsrate = round(annuitaet / 12, 2)                          # Konstante Monatsrate
    zins_rate_m = p["zins"] / 100 / 12                             # Monatlicher Zinssatz
    zins_j1   = round(fk * p["zins"] / 100, 2)                    # Näherung für KPI-Übersicht
    kd        = annuitaet
    ltv       = round(fk / kp * 100, 1) if kp else 0.0
    dscr      = round(netto / kd, 2)    if kd else 99.0

    # ── Steuer & Cashflow (Standard-Modus) ────────────────────────────
    stl_erg    = round(netto - zins_j1 - afa, 2)
    steuerlast = round(stl_erg * p["steuer"] / 100, 2)
    cf_pre_m   = round((netto - kd) / 12, 2)
    cf_post_m  = round((netto - kd - steuerlast) / 12, 2)

    # ── Returns ──────────────────────────────────────────────────────
    roe = round((netto - zins_j1) / ek_abs * 100, 2) if ek_abs else 0.0
    roi = round(netto / gesamt * 100, 2)              if gesamt else 0.0

    # ── Break-Even (inkl. Leerstand) ─────────────────────────────────
    kostensatz = round((p["bew"] + p["leerstand"]) / 100, 6)
    be_m  = round(kd / (1 - kostensatz) / 12, 2) if (kostensatz < 1 and kd) else 0.0
    amort = round(ek_abs / (cf_post_m * 12), 1)  if cf_post_m * 12 > 0 else None

    # ── 10-Jahres-Projektion (exakte monatliche Berechnung) ──────────
    proj, irr_cfs, cum_cf = [], [], 0.0
    debt, m_brutto, iw = fk, p["jahresmiete"], kp

    for y in range(1, 11):
        # Monatliche Annuitätenberechnung für dieses Jahr
        zinsen_y  = 0.0
        for _ in range(12):
            zins_m, tilg_m, debt = calc_monat(debt, monatsrate, zins_rate_m)
            zinsen_y += zins_m
        zinsen_y = round(zinsen_y, 2)

        # Jährlicher Nettomietertrag (Bewirtschaftung + Leerstand + IHR bereits abgezogen)
        mn     = round(m_brutto * (1 - p["bew"] / 100 - p["leerstand"] / 100) - ihr_val, 2)
        y_cf   = round(mn - annuitaet, 2)
        y_stl  = round((mn - zinsen_y - afa) * p["steuer"] / 100, 2)
        y_cfp  = round(y_cf - y_stl, 2)
        cum_cf  = round(cum_cf + y_cfp, 2)
        iw     = round(iw * (1 + p["wert"] / 100), 2)
        eq     = round(iw - debt, 2)

        irr_cfs.append(round(y_cfp + (max(0.0, eq - ek_abs) if y == 10 else 0.0), 2))
        proj.append({
            "Jahr":           f"J{y}",
            "CF pre/Mon.":    round(y_cf  / 12, 2),
            "CF post/Mon.":   round(y_cfp / 12, 2),
            "Equity":         eq,
            "Immobilienwert": iw,
            "Restschuld":     debt,
        })
        m_brutto = round(m_brutto * (1 + p["miets"] / 100), 2)

    try:    irr_val = round(calc_irr(-ek_abs, irr_cfs), 2)
    except: irr_val = 0.0
    npv_val  = round(calc_npv(-ek_abs, irr_cfs, p["diskont"] / 100))
    final_eq = proj[-1]["Equity"] if proj else ek_abs
    moic     = round((cum_cf + final_eq) / ek_abs, 2) if ek_abs else 0.0

    return dict(
        knk_pct=knk_pct, knk_abs=knk_abs, gest_abs=gest_abs,
        notar_abs=notar_abs, makler_abs=makler_abs, gesamt=gesamt,
        bew_k=bew_k, leer_abs=leer_abs, ihr_val=ihr_val,
        noi=noi, netto=netto, afa_info=afa_info, afa=afa, afa_rate_used=afa_rate_used,
        brutto=brutto, faktor=faktor, netto_r=netto_r, cap_rate=cap_rate,
        ek_abs=ek_abs, fk=fk, annuitaet=annuitaet, monatsrate=monatsrate,
        zins_rate_m=zins_rate_m, zins_j1=zins_j1, kd=kd, ltv=ltv, dscr=dscr,
        steuerlast=steuerlast, stl_erg=stl_erg, cf_pre_m=cf_pre_m, cf_post_m=cf_post_m,
        roe=roe, roi=roi, be_m=be_m, amort=amort,
        irr_val=irr_val, npv_val=npv_val, moic=moic, proj=proj,
    )


def calc_pro_10year(params: dict, res: dict, pro: dict) -> list[dict]:
    """
    Pro-Modus: 10-Jahres-Prognose mit steuerlicher Betrachtung.

    Berechnet für jedes Jahr:
      - Exakte monatliche Annuität (Sanity-Check auf jede Iteration)
      - Nettomietertrag mit jährlicher Mietsteigerung
      - Kosten mit separater Inflationsrate
      - Zu versteuerndes Einkommen (§21 EStG):
          ZvE = Nettomietertrag − Schuldzinsen − AfA
      - Cashflow nach Steuern = CF vor Steuern − Steuerlast
      - Steuer-Effekt = −Steuerlast (positiv = Ersparnis)

    Sanity-Check pro Monat: |Zins + Tilgung − Monatsrate| ≤ 0,01 €

    Returns: Liste mit einem Dict pro Jahr (1–10).
    """
    fk          = res["fk"]
    annuitaet   = res["annuitaet"]          # Jahresannuität (konstant)
    monatsrate  = res["monatsrate"]          # Konstante Monatsrate
    zins_rate_m = res["zins_rate_m"]         # Monatlicher Zinssatz (dezimal)
    ihr_basis   = res["ihr_val"]             # IHR Basisjahr (wird inflationiert)

    # Gebäudewert + AfA nach Pro-Modus-Parametern
    # Spezifikation: Gebäudewert = Kaufpreis × Anteil (nicht Gesamtinvestition)
    gebaeude_wert = round(params["kaufpreis"] * params["gebaeude"] / 100, 2)
    afa_pro_pa    = round(gebaeude_wert * pro["afa_satz"] / 100, 2)

    jahre      = []
    restschuld = fk

    for j in range(1, 11):
        # ── Mietsteigerung ────────────────────────────────────────────
        faktor_miete   = (1 + pro["miets"]      / 100) ** (j - 1)
        miete_brutto_j = round(params["jahresmiete"] * faktor_miete, 2)
        leer_abs_j     = round(miete_brutto_j * params["leerstand"] / 100, 2)

        # ── Kostensteigerung ──────────────────────────────────────────
        faktor_kosten = (1 + pro["kosten_inf"] / 100) ** (j - 1)
        bew_k_j       = round(miete_brutto_j * params["bew"] / 100, 2)   # steigt mit Miete
        ihr_j         = round(ihr_basis * faktor_kosten, 2)               # steigt mit Inflation

        # ── Nettomietertrag (Basis für CF und ZvE) ────────────────────
        # = Effektive Mieteinnahmen − nicht umlegbare Kosten
        netto_j = round(miete_brutto_j - bew_k_j - leer_abs_j - ihr_j, 2)

        # ── Exakte monatliche Annuitätenberechnung ────────────────────
        zinsen_j  = 0.0
        tilgung_j = 0.0

        for _ in range(12):
            zins_m, tilg_m, restschuld = calc_monat(restschuld, monatsrate, zins_rate_m)
            zinsen_j  = round(zinsen_j  + zins_m, 2)
            tilgung_j = round(tilgung_j + tilg_m, 2)

        # Plausibilitäts-Check Jahressumme: Zins + Tilgung ≈ Annuität
        # (Toleranz: max. ~0,12 € durch 12-fache Rundung auf 2 Dezimalstellen)
        kd_check = round(zinsen_j + tilgung_j, 2)
        kd_diff  = abs(kd_check - round(annuitaet, 2))
        # Wird nicht propagiert — mathematisch unvermeidbare Rundungstoleranz

        # ── Cashflow vor Steuern ──────────────────────────────────────
        cf_vor_j = round(netto_j - annuitaet, 2)

        # ── Zu versteuerndes Einkommen (§21 EStG, V+V) ───────────────
        # ZvE = Nettomietertrag − Schuldzinsen − AfA
        # (Bew.kosten und IHR bereits im Nettomietertrag abgezogen)
        zve_j        = round(netto_j - zinsen_j - afa_pro_pa, 2)
        steuerlast_j = round(zve_j * pro["grenzzinssatz"] / 100, 2)
        # Negativ = Steuerersparnis → verbessert Cashflow

        cf_nach_j      = round(cf_vor_j - steuerlast_j, 2)
        steuer_effekt_j = round(-steuerlast_j, 2)  # positiv = Ersparnis

        jahre.append({
            "jahr":                 j,
            "miete_brutto":         miete_brutto_j,
            "netto":                netto_j,
            "zinsen":               zinsen_j,
            "tilgung":              tilgung_j,
            "afa":                  afa_pro_pa,
            "zve":                  zve_j,
            "steuerlast":           steuerlast_j,
            "steuer_effekt":        steuer_effekt_j,
            "cf_vor_monat":         round(cf_vor_j / 12, 2),
            "cf_nach_monat":        round(cf_nach_j / 12, 2),
            "steuer_effekt_monat":  round(steuer_effekt_j / 12, 2),
            "restschuld":           restschuld,
            "gebaeude_wert":        gebaeude_wert,
            "afa_pro_pa":           afa_pro_pa,
        })

    return jahre

# ══════════════════════════════════════════════════════════════════════
# 5. AMPEL-LOGIK
# ══════════════════════════════════════════════════════════════════════

def get_ampel(key: str, val: float) -> str:
    rules = {
        "brutto":    lambda v: "g" if v >= 6   else ("y" if v >= 4    else "r"),
        "netto_r":   lambda v: "g" if v >= 4.5 else ("y" if v >= 3    else "r"),
        "cap_rate":  lambda v: "g" if v >= 5   else ("y" if v >= 3.5  else "r"),
        "faktor":    lambda v: "g" if v <= 20  else ("y" if v <= 25   else "r"),
        "dscr":      lambda v: "g" if v >= 1.3 else ("y" if v >= 1.1  else "r"),
        "ltv":       lambda v: "g" if v <= 70  else ("y" if v <= 80   else "r"),
        "cf_pre_m":  lambda v: "g" if v >= 0   else ("y" if v >= -150 else "r"),
        "cf_post_m": lambda v: "g" if v >= 0   else ("y" if v >= -150 else "r"),
        "roe":       lambda v: "g" if v >= 8   else ("y" if v >= 5    else "r"),
        "irr_val":   lambda v: "g" if v >= 8   else ("y" if v >= 5    else "r"),
        "npv_val":   lambda v: "g" if v >= 0   else "r",
        "moic":      lambda v: "g" if v >= 2   else ("y" if v >= 1.5  else "r"),
    }
    fn = rules.get(key)
    return fn(val) if fn else "y"

# ══════════════════════════════════════════════════════════════════════
# 6. HTML-KOMPONENTEN — class-basiert, theme-adaptiv, keine Emojis
# ══════════════════════════════════════════════════════════════════════

def kpi_card(label: str, value: str, sub: str | None = None,
             key: str | None = None, val: float | None = None,
             compact: bool = False) -> str:
    ak  = get_ampel(key, val) if (key and val is not None) else None
    a   = AMPEL[ak] if ak else None
    cls = f"kpi {a['cls']}" if a else "kpi"
    if compact: cls += " kpi-sm"
    bar   = '<div class="kpi-bar"></div>' if a else ""
    badge = f'<div class="kpi-badge">{a["t"]}</div>' if a else ""
    sub_h = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    vsz   = "kpi-sm" if compact else ""
    return (f'<div class="{cls}">{bar}'
            f'<div class="kpi-lbl">{label}</div>'
            f'<div class="kpi-val {vsz}">{value}</div>'
            f'{sub_h}{badge}</div>')

def status_bar(items: list[tuple]) -> str:
    cells = "".join(
        f'<div class="sb-cell"><div class="sb-lbl">{l}</div>'
        f'<div class="sb-val">{v}</div></div>'
        for l, v in items
    )
    return f'<div class="sb-wrap">{cells}</div>'

def divider(label: str) -> str:
    return (f'<div class="div-wrap">'
            f'<div class="div-line"></div>'
            f'<div class="div-lbl">{label}</div>'
            f'<div class="div-line"></div></div>')

def knk_table(bundesland, gest, notar, makler, res) -> str:
    rows = [
        (f"Grunderwerbsteuer ({bundesland})", f"{gest:.1f} %", fmt_eur(res["gest_abs"])),
        ("Notar + Grundbuch",                  f"{notar:.1f} %", fmt_eur(res["notar_abs"])),
        ("Maklercourtage",                     f"{makler:.2f} %", fmt_eur(res["makler_abs"])),
    ]
    row_html = "".join(
        f'<div class="knk-row"><span class="knk-lbl">{l}</span>'
        f'<span class="knk-vals"><span class="mono">{p}</span>'
        f'<span class="mono">{v}</span></span></div>'
        for l, p, v in rows
    )
    return (f'<div class="knk"><div class="knk-head">KNK-Aufschlüsselung</div>'
            f'{row_html}'
            f'<div class="knk-row knk-total"><span>KNK gesamt</span>'
            f'<span class="knk-vals"><span>{res["knk_pct"]:.2f} %</span>'
            f'<span>{fmt_eur(res["knk_abs"])}</span></span></div></div>')

def afa_badge(ai, afa_val, afa_rate_used, gebaeude, gesamt) -> str:
    used = (f'{afa_rate_used:.1f} % · {ai["basis"]}' if afa_rate_used else "Denkmal § 7i EStG")
    return (f'<div class="afa-badge"><span class="afa-icon">§</span><div>'
            f'<div class="afa-title">{ai["label"]}</div>'
            f'<div class="afa-basis">{ai["basis"]}</div>'
            f'<div class="afa-note">{ai["note"]}</div>'
            f'<div style="margin-top:6px;font-size:12px;">'
            f'AfA p.a.: <span class="info-strong">{fmt_eur(afa_val)}</span>'
            f' · {used}</div></div></div>')

def summary_banner(gesamt_val, jahresmiete_val, ek_val, knk_pct_val) -> str:
    items = [("Gesamtinvestition", fmt_eur(gesamt_val)),
             ("Jahresmiete brutto", fmt_eur(jahresmiete_val)),
             ("Eigenkapital", fmt_eur(ek_val))]
    subs = "".join(
        f'<div><div class="sum-sub-lbl">{l}</div><div class="sum-sub-val">{v}</div></div>'
        for l, v in items
    )
    return (f'<div class="sum-wrap">'
            f'<div class="sum-label">Gesamtinvestition (inkl. {knk_pct_val:.2f} % KNK)</div>'
            f'<div class="sum-total">{fmt_eur(gesamt_val)}</div>'
            f'<div class="sum-grid">{subs}</div></div>')

def rep_section(title: str) -> str:
    return f'<div class="rep-section-head">{title}</div>'

def rep_row(label: str, value: str, note: str = "") -> str:
    note_h = f'<span class="rep-note">{note}</span>' if note else ""
    return (f'<div class="rep-row"><span class="rep-lbl">{label}</span>'
            f'<span>{note_h}<span class="rep-val">{value}</span></span></div>')

# ══════════════════════════════════════════════════════════════════════
# 7. CHARTS — Plotly, theme-adaptiv
# ══════════════════════════════════════════════════════════════════════

_BASE = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10, b=32, l=48, r=8),
    font=dict(family="Inter, -apple-system, sans-serif", size=11),
    hovermode="x unified",
    legend=dict(orientation="h", y=-0.28, x=0, font_size=11),
    xaxis=dict(showgrid=False, linecolor="rgba(128,128,128,.2)", tickfont=dict(size=11)),
    yaxis=dict(gridcolor="rgba(128,128,128,.1)", linecolor="rgba(128,128,128,.2)", tickfont=dict(size=11)),
)

def chart_cashflow(proj_df: pd.DataFrame) -> go.Figure:
    """Cashflow-Verlauf (pre/post Tax) über 10 Jahre — Linienchart."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=proj_df["Jahr"], y=proj_df["CF pre/Mon."], name="CF vor Steuern / Mon.",
        fill="tozeroy", fillcolor="rgba(99,102,241,.07)",
        line=dict(color="#6366f1", width=2.5), mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=proj_df["Jahr"], y=proj_df["CF post/Mon."], name="CF nach Steuern / Mon.",
        fill="tozeroy", fillcolor="rgba(217,170,50,.08)",
        line=dict(color="#c9a530", width=2.5, dash="dash"), mode="lines",
    ))
    fig.update_layout(**_BASE, height=230)
    fig.update_yaxes(ticksuffix=" €", zeroline=True, zerolinecolor="rgba(128,128,128,.2)")
    return fig

def chart_equity(proj_df: pd.DataFrame) -> go.Figure:
    """Vermögensaufbau (Equity, Immobilienwert, Restschuld) — Linienchart."""
    fig = go.Figure()
    for col, color, dash, w in [
        ("Equity",         "#22c55e", "solid", 2.5),
        ("Immobilienwert", "#6366f1", "dash",  2.0),
        ("Restschuld",     "#f43f5e", "dot",   1.5),
    ]:
        fig.add_trace(go.Scatter(
            x=proj_df["Jahr"], y=proj_df[col], name=col,
            line=dict(color=color, width=w, dash=dash), mode="lines",
        ))
    fig.update_layout(**_BASE, height=230)
    return fig

def chart_donut(kaufpreis, gest_abs, notar_abs, makler_abs) -> go.Figure:
    """Kostenstruktur-Donut."""
    data = [(l, v, c) for l, v, c in [
        ("Kaufpreis",         kaufpreis,  "#6366f1"),
        ("Grunderwerbsteuer", gest_abs,   "#c9a530"),
        ("Notar/Grundbuch",   notar_abs,  "#8b5cf6"),
        ("Makler",            makler_abs, "#06b6d4"),
    ] if v > 0]
    fig = go.Figure(go.Pie(
        labels=[d[0] for d in data], values=[d[1] for d in data],
        hole=0.66, marker=dict(colors=[d[2] for d in data],
                               line=dict(color="rgba(0,0,0,.05)", width=1)),
        textposition="none",
        hovertemplate="%{label}: %{value:,.0f} €<extra></extra>",
    ))
    fig.update_layout(height=160, margin=dict(t=5, b=5, l=5, r=5),
                      paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
    return fig

def chart_pro_cf(jahre: list[dict]) -> go.Figure:
    """
    Pro-Modus: Cashflow nach Steuern (monatlich) über 10 Jahre.
    Balken grün wenn positiv, rot wenn negativ.
    """
    labels = [f"J{j['jahr']}" for j in jahre]
    werte  = [j["cf_nach_monat"] for j in jahre]
    farben = ["#22c55e" if v >= 0 else "#f43f5e" for v in werte]

    fig = go.Figure(go.Bar(
        x=labels, y=werte, marker_color=farben,
        name="CF nach Steuern",
        text=[f"{v:+.0f} €" for v in werte],
        textposition="outside",
        textfont=dict(size=10, family="JetBrains Mono, monospace"),
        hovertemplate="Jahr %{x}: %{y:+.2f} €/Mon.<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="solid",
                  line_color="rgba(128,128,128,.35)", line_width=1)
    fig.update_layout(**_BASE, height=270, showlegend=False)
    fig.update_yaxes(ticksuffix=" €", zeroline=False, title=None)
    fig.update_xaxes(title=None)
    return fig

def chart_pro_schuld(jahre: list[dict]) -> go.Figure:
    """
    Pro-Modus: Restschuld-Entwicklung über 10 Jahre.
    Zeigt, wie das Darlehen durch die Annuität abgebaut wird.
    """
    labels = [f"J{j['jahr']}" for j in jahre]
    werte  = [j["restschuld"] for j in jahre]

    fig = go.Figure(go.Scatter(
        x=labels, y=werte, mode="lines+markers",
        name="Restschuld",
        line=dict(color="#6366f1", width=2.5),
        marker=dict(size=7, color="#6366f1"),
        fill="tozeroy", fillcolor="rgba(99,102,241,.07)",
        hovertemplate="Jahr %{x}: %{y:,.0f} €<extra></extra>",
    ))
    fig.update_layout(**_BASE, height=270, showlegend=False)
    fig.update_yaxes(ticksuffix=" €", title=None)
    fig.update_xaxes(title=None)
    return fig

# ══════════════════════════════════════════════════════════════════════
# 8. HAUPT-APP
# ══════════════════════════════════════════════════════════════════════

def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)

    # ── Header (keine Emojis) ─────────────────────────────────────────
    st.markdown(
        '<div class="yb-header">'
        '<div style="width:30px;height:30px;background:linear-gradient(135deg,#b8902a,#e0c060);'
        'border-radius:7px;display:flex;align-items:center;justify-content:center;'
        'color:#fff;font-size:14px;font-weight:700">◆</div>'
        '<div><div class="yb-logo">YieldBase</div>'
        '<div class="yb-sub">Analytics v4 · Python</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ══════════════════════════════════════════════════════════════════
    # SIDEBAR — Progressive Disclosure, keine Emojis
    # ══════════════════════════════════════════════════════════════════
    with st.sidebar:

        # ── Modus-Auswahl ─────────────────────────────────────────────
        mode   = st.radio("Analyse-Modus", ["Einsteiger", "Experte"],
                          horizontal=True, label_visibility="collapsed")
        is_exp = (mode == "Experte")
        st.markdown("---")

        # ── Standort & Kaufnebenkosten ────────────────────────────────
        st.markdown("#### Standort & Kaufnebenkosten")

        bundesland = st.selectbox(
            "Bundesland",
            list(BUNDESLAND_GEST.keys()),
            index=0,
            help="Die Grunderwerbsteuer variiert je nach Bundesland von 3,5 % (Bayern, Sachsen) "
                 "bis 6,5 % (NRW, Brandenburg u.a.) und wird automatisch gesetzt.",
        )
        gest = BUNDESLAND_GEST[bundesland]
        st.info(f"Grunderwerbsteuer {bundesland}: **{gest:.1f} %** — automatisch")

        kaufpreis = st.number_input(
            "Kaufpreis (€)", min_value=0, value=350_000, step=5_000,
            help="Brutto-Verkaufspreis der Immobilie ohne jegliche Nebenkosten.",
        )

        # ── KAUFPREISAUFTEILUNG (für alle Modi verfügbar) ─────────────
        with st.expander("Erweiterte Kaufpreisaufteilung"):
            # Erklärungstext als Caption — help-Parameter in st.expander()
            # erst ab Streamlit 1.37 verfügbar, Caption ist abwärtskompatibel.
            st.caption(
                "Aufteilung des Kaufpreises in Gebäude- und Grundstückswert. "
                "Nur der Gebäudewert ist steuerlich abschreibbar (§ 7 EStG). "
                "Der Grundstücksanteil kann nicht abgeschrieben werden."
            )
            gebaeude = st.slider(
                "Gebäudewert-Anteil in Prozent", 0, 100, 80, 1,
                help="Anteil des Kaufpreises, der auf das Gebäude entfällt. "
                     "Der Rest wird dem Grundstück zugerechnet. "
                     "Typische Werte: Stadtlagen 60–80 %, ländliche Lagen 70–90 %.",
            )
            geb_wert  = round(kaufpreis * gebaeude / 100, 2)
            grst_wert = round(kaufpreis - geb_wert, 2)
            st.caption(
                f"Gebäudewert: **{fmt_eur(geb_wert)}** — "
                f"Grundstück: **{fmt_eur(grst_wert)}**"
            )

        notar  = st.slider(
            "Notar + Grundbuch (%)", 0.5, 2.5, 2.0, 0.1,
            help="Notarkosten gem. GNotKG ca. 1,0–1,5 % + Grundbucheintragung ca. 0,5 % "
                 "des Kaufpreises.",
        )
        makler = st.slider(
            "Maklercourtage (%)", 0.0, 3.57, 3.57, 0.01,
            help="Käuferanteil der Maklerprovision: max. 3,57 % inkl. MwSt. "
                 "(§ 656c BGB, Halbteilungsprinzip seit 12/2020).",
        )
        st.markdown("---")

        # ── Objekt & Mietertrag ───────────────────────────────────────
        st.markdown("#### Objekt & Mietertrag")

        jahresmiete = st.number_input(
            "Jahres-Kaltmiete (€)", min_value=0, value=18_000, step=500,
            help="Aktuelle Nettokaltmiete p.a. (ohne Heiz- und Betriebskosten). "
                 "Basis für Rendite- und Cashflow-Berechnung.",
        )
        baujahr = st.number_input(
            "Baujahr", min_value=1800, max_value=datetime.now().year,
            value=1985, step=1,
            help="Baujahr des Gebäudes. Bestimmt automatisch den AfA-Satz (§ 7 Abs. 4 EStG) "
                 "und die Instandhaltungsrücklage.",
        )
        afa_info = get_afa_info(baujahr)
        st.success(f"**AfA:** {afa_info['label']}  ·  {afa_info['basis']}")

        bew = st.slider(
            "Bewirtschaftungskosten (%)", 5, 30, 15, 1,
            help="Nicht auf den Mieter umlegbare Kosten: Hausverwaltung, Versicherung, "
                 "anteilige Betriebskosten, Mietausfallwagnis. "
                 "Instandhaltungsrücklage (IHR) wird separat berechnet.",
        )
        leerstand = st.slider(
            "Leerstandsrisiko (%)", 0.0, 15.0, 3.0, 0.5,
            help="Erwarteter jährlicher Leerstand als Anteil der Jahresmiete. "
                 "Reduziert die effektiven Mieteinnahmen.",
        )
        st.markdown("---")

        # ── Finanzierung ──────────────────────────────────────────────
        st.markdown("#### Finanzierung")

        ek = st.slider(
            "Eigenkapital-Quote (%)", 5, 100, 25, 1,
            help="Anteil der Gesamtinvestition (Kaufpreis + KNK), "
                 "den Sie aus eigenen Mitteln einbringen.",
        )
        zins = st.slider(
            "Sollzins p.a. (%)", 0.5, 8.0, 3.8, 0.1,
            help="Nominalzinssatz des Bankdarlehens p.a. "
                 "Wird im Annuitätendarlehen monatlich auf die Restschuld angewendet.",
        )
        tilgung = st.slider(
            "Anfangstilgung p.a. (%)", 0.5, 6.0, 2.0, 0.1,
            help="Anfänglicher Tilgungssatz p.a. Die Annuität (Zins + Tilgung) bleibt konstant; "
                 "der Tilgungsanteil steigt mit sinkender Restschuld.",
        )

        # ── Experte: Steuer, AfA & Projektion ────────────────────────
        if is_exp:
            st.markdown("---")
            st.markdown("#### Steuer, AfA & Projektion")

            steuer = st.slider(
                "Grenzsteuersatz (%)", 0, 45, 42, 1,
                help="Ihr persönlicher Grenzsteuersatz. Bestimmt die Steuerlast oder "
                     "-ersparnis aus Vermietung und Verpachtung (§21 EStG).",
            )
            # Gebäudeanteil kommt jetzt aus dem Kaufpreisaufteilung-Expander
            is_denkmal = st.checkbox(
                "Denkmalschutz-AfA (§ 7i EStG)",
                help="Bei denkmalgeschützten Gebäuden kann der Sanierungsanteil "
                     "mit bis zu 9 % p.a. abgeschrieben werden.",
            )
            afa_manual = (
                st.checkbox(
                    "AfA manuell überschreiben",
                    help="Überschreibt die automatische AfA-Ermittlung aus dem Baujahr.",
                )
                if not is_denkmal else False
            )
            dk_san = dk_afa = afa_override = 0.0
            if is_denkmal:
                dk_san      = st.slider("Sanierungsanteil (%)", 10, 90, 60, 1)
                dk_afa      = st.slider("Denkmal-AfA-Satz (%)", 3.0, 12.0, 9.0, 0.5)
            elif afa_manual:
                afa_override = st.number_input(
                    "AfA-Satz manuell (%)", 0.5, 10.0, float(afa_info["satz"]), 0.5,
                )

            st.markdown("**10-Jahres-Projektion**")
            wert    = st.slider(
                "Wertzuwachs p.a. (%)", -2.0, 6.0, 2.0, 0.5,
                help="Angenommene jährliche Wertsteigerung der Immobilie.",
            )
            miets   = st.slider(
                "Mietsteigerung p.a. (%)", 0.0, 5.0, 1.5, 0.25,
                help="Angenommene jährliche Erhöhung der Nettokaltmiete "
                     "(Standard-Projektion, nicht Pro-Modus).",
            )
            diskont = st.slider(
                "Diskontierungssatz NPV (%)", 1.0, 12.0, 5.0, 0.5,
                help="Risikoadjustierter Kapitalkostensatz für die Kapitalwertberechnung (NPV).",
            )
        else:
            steuer     = 42; is_denkmal = False
            afa_manual = False; dk_san = 60; dk_afa = 9.0
            afa_override = float(afa_info["satz"])
            wert = 2.0; miets = 1.5; diskont = 5.0

        # ══════════════════════════════════════════════════════════════
        # PRO-FUNKTIONEN (immer sichtbar, unabhängig vom Modus)
        # ══════════════════════════════════════════════════════════════
        st.divider()
        st.markdown("**Pro-Funktionen**")

        toggle_pro = st.checkbox(
            "Pro-Modus aktivieren (Steuern und Verlauf)",
            value=False,
            help="Schaltet die steuerliche Optimierung (§21 EStG) und die langfristige "
                 "10-Jahres-Vorschau mit monatlich exakter Annuitätenberechnung frei.",
        )

        # Default-Werte für Pro-Parameter (auch wenn deaktiviert)
        pro_grenzzins  = 30.0
        pro_afa_satz   = 2.0
        pro_miets      = 2.0
        pro_kosten_inf = 2.0

        if toggle_pro:
            with st.container():
                pro_grenzzins = st.slider(
                    "Persönlicher Grenzzinssatz in Prozent",
                    min_value=0, max_value=45, value=30, step=1,
                    help="Ihr individueller Grenzsteuersatz, mit dem zusätzliche Einnahmen "
                         "versteuert werden bzw. Verluste aus V+V steuerlich angerechnet werden.",
                )
                pro_afa_key = st.selectbox(
                    "AfA-Satz (Abschreibung)",
                    options=list(PRO_AFA_OPTIONEN.keys()),
                    index=0,
                    help="Abnutzung für Absetzung (§ 7 EStG): Der Prozentsatz, "
                         "mit dem der Gebäudewert jährlich steuerlich abgeschrieben werden kann. "
                         "Neubau ab 2023: 3,0 %; Standard: 2,0 %; Altbau vor 1925: 2,5 %.",
                )
                pro_afa_satz = PRO_AFA_OPTIONEN[pro_afa_key]

                pro_miets = st.slider(
                    "Jährliche Mietsteigerung in Prozent",
                    min_value=0.0, max_value=5.0, value=2.0, step=0.1,
                    help="Die angenommene jährliche Erhöhung der Nettokaltmiete "
                         "über die gesamte Laufzeit der 10-Jahres-Prognose.",
                )
                pro_kosten_inf = st.slider(
                    "Kosten-Inflation in Prozent",
                    min_value=0.0, max_value=5.0, value=2.0, step=0.1,
                    help="Die angenommene jährliche Steigerungsrate für nicht umlegbare "
                         "Betriebskosten und Instandhaltung (z.B. Hausverwaltung, Handwerker).",
                )

    # ══════════════════════════════════════════════════════════════════
    # BERECHNUNG — Standard-Modus
    # ══════════════════════════════════════════════════════════════════
    params = dict(
        kaufpreis=float(kaufpreis), gest=gest, notar=notar, makler=makler,
        jahresmiete=float(jahresmiete), bew=float(bew), ek=float(ek),
        zins=float(zins), tilgung=float(tilgung), steuer=float(steuer),
        gebaeude=float(gebaeude), is_denkmal=is_denkmal,
        dk_san=float(dk_san), dk_afa=float(dk_afa), baujahr=int(baujahr),
        afa_manual=afa_manual, afa_override=float(afa_override),
        leerstand=float(leerstand), wert=float(wert),
        miets=float(miets), diskont=float(diskont),
    )
    res     = calc_all(params)
    proj_df = pd.DataFrame(res["proj"])
    ai      = res["afa_info"]

    # BERECHNUNG — Pro-Modus (nur wenn aktiviert)
    pro_jahre: list[dict] = []
    if toggle_pro:
        pro_params = dict(
            grenzzinssatz = float(pro_grenzzins),
            afa_satz      = float(pro_afa_satz),
            miets         = float(pro_miets),
            kosten_inf    = float(pro_kosten_inf),
        )
        pro_jahre = calc_pro_10year(params, res, pro_params)

    # ── STATUS BAR ────────────────────────────────────────────────────
    st.markdown(
        status_bar([
            ("Gesamtinvestition", fmt_eur(res["gesamt"])),
            ("Bruttorendite",     fmt_pct(res["brutto"])),
            ("Nettorendite",      fmt_pct(res["netto_r"])),
            ("Cashflow / Mon.",   fmt_eur(res["cf_pre_m"])),
            ("DSCR",              f"{res['dscr']:.2f}".replace(".", ",")),
            ("ROE",               fmt_pct(res["roe"])),
        ]),
        unsafe_allow_html=True,
    )

    # ── TABS (keine Emojis/Icons) ────────────────────────────────────
    t1, t2, t3, t4 = st.tabs(["Eingabe & KPIs", "Dashboard", "Analyse", "Bericht"])

    # ══════════════════════════════════════════════════════════════════
    # TAB 1 — Eingabe & KPIs
    # ══════════════════════════════════════════════════════════════════
    with t1:

        # ── Kernmetriken mit help-Texten (st.metric) ─────────────────
        # Spec: "Die bisherigen Metriken bleiben ganz oben bestehen.
        #        Statte jede st.metric-Kachel mit einem help-Text aus."
        m1, m2, m3 = st.columns(3)
        m1.metric(
            "Bruttorendite",
            value=fmt_pct(res["brutto"]),
            help="Jahresmiete (brutto) im Verhältnis zum Kaufpreis. "
                 "Unverzinste Rohrendite ohne Berücksichtigung von Kosten "
                 "oder Finanzierung. Richtwert: ab 5 % attraktiv.",
        )
        m2.metric(
            "Netto-Mietrendite",
            value=fmt_pct(res["netto_r"]),
            help="Jahresmiete minus nicht umlegbare Bewirtschaftungskosten, "
                 "Leerstandsverluste und Instandhaltungsrücklage — "
                 "im Verhältnis zur Gesamtinvestition (Kaufpreis + Kaufnebenkosten). "
                 "Richtwert: ab 3,5 % solide.",
        )
        m3.metric(
            "Cashflow vor Steuern",
            value=f"{fmt_eur(res['cf_pre_m'])}/Mon.",
            help="Monatlicher Überschuss oder Fehlbetrag nach Abzug aller laufenden Kosten "
                 "(Bewirtschaftung, Leerstand, Instandhaltung) und der vollständigen "
                 "Bankrate (Zins + Tilgung) — vor Berücksichtigung des Finanzamts. "
                 "Negativ bedeutet monatliche Zuzahlung.",
        )

        # ── Pro-Modus: Steuerliche Betrachtung (Jahr 1) ──────────────
        if toggle_pro and pro_jahre:
            j1 = pro_jahre[0]  # Jahr 1

            st.markdown("---")
            st.markdown("## Steuerliche Betrachtung (Jahr 1)")

            p1, p2 = st.columns(2)
            p1.metric(
                "Steuer-Effekt",
                value=f"{fmt_eur(j1['steuer_effekt_monat'])}/Mon.",
                help="Gibt an, ob Sie durch die Immobilie Steuern sparen (positiver Wert) "
                     "oder zusätzliche Steuern zahlen müssen (negativer Wert). "
                     "Berechnung: -(ZvE × Grenzzinssatz). "
                     "Basis: Zu versteuerndes Einkommen aus V+V (§21 EStG) = "
                     "Nettomiete − Schuldzinsen − AfA.",
            )
            p2.metric(
                "Cashflow nach Steuern",
                value=f"{fmt_eur(j1['cf_nach_monat'])}/Mon.",
                help="Der tatsächliche monatliche Überschuss oder Verlust, nachdem "
                     "Bankrate (Zins + Tilgung), Betriebskosten, Instandhaltung "
                     "und das Finanzamt vollständig berücksichtigt wurden. "
                     "Dies ist Ihre reale Liquiditätssituation.",
            )

            # Ergänzende Kennzahlen für Jahr 1
            with st.expander("Details zur steuerlichen Berechnung (Jahr 1)"):
                detail_cols = st.columns(4)
                detail_cols[0].metric(
                    "Gebäudewert",
                    value=fmt_eur(j1["gebaeude_wert"]),
                    help=f"Kaufpreis × {gebaeude} % Gebäudeanteil. "
                          "Basis für die steuerliche Abschreibung (AfA).",
                )
                detail_cols[1].metric(
                    "AfA p.a. (Pro)",
                    value=fmt_eur(j1["afa_pro_pa"]),
                    help=f"Gebäudewert × {pro_afa_satz:.1f} % AfA-Satz. "
                          "Jährlicher Abschreibungsbetrag — linear, konstant über Laufzeit.",
                )
                detail_cols[2].metric(
                    "Schuldzinsen J1",
                    value=fmt_eur(j1["zinsen"]),
                    help="Summe der monatlichen Zinsanteile aus den 12 Monaten des ersten Jahres. "
                         "Berechnung: Zins = Restschuld × Zinssatz / 12 (monatlich, exakt).",
                )
                detail_cols[3].metric(
                    "ZvE aus V+V J1",
                    value=fmt_eur(j1["zve"]),
                    help="Zu versteuerndes Einkommen aus Vermietung und Verpachtung (§21 EStG). "
                         "= Nettomiete − Schuldzinsen − AfA. "
                         "Negativ = steuerlicher Verlust → mindert Steuerlast.",
                )

            # ── 10-Jahres-Investment-Verlauf ──────────────────────────
            st.markdown("---")
            st.markdown("## 10-Jahres-Investment-Verlauf")
            st.caption(
                f"Pro-Modus: Mietsteigerung {pro_miets:.1f} % p.a. · "
                f"Kosten-Inflation {pro_kosten_inf:.1f} % p.a. · "
                f"Grenzzinssatz {pro_grenzzins:.0f} % · "
                f"AfA {pro_afa_satz:.1f} % · "
                f"Exakte monatliche Annuitätenberechnung"
            )

            ch1, ch2 = st.columns(2, gap="large")
            with ch1:
                st.markdown("**Cashflow nach Steuern (monatlich)**")
                st.caption("Grün = positiver CF, Rot = Zuzahlung erforderlich")
                st.plotly_chart(
                    chart_pro_cf(pro_jahre),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
            with ch2:
                st.markdown("**Restschuld-Verlauf**")
                st.caption("Monatlich exakt berechnet (Annuitäten-Darlehen)")
                st.plotly_chart(
                    chart_pro_schuld(pro_jahre),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )

            # Übersichts-Tabelle Pro-Jahresverlauf
            with st.expander("Detailtabelle: 10-Jahres-Prognose (Pro-Modus)"):
                tbl_data = {
                    "Jahr":           [j["jahr"] for j in pro_jahre],
                    "Miete brutto":   [fmt_eur(j["miete_brutto"])     for j in pro_jahre],
                    "Nettomietertrag":[fmt_eur(j["netto"])            for j in pro_jahre],
                    "Schuldzinsen":   [fmt_eur(j["zinsen"])           for j in pro_jahre],
                    "ZvE":            [fmt_eur(j["zve"])              for j in pro_jahre],
                    "Steuerlast":     [fmt_eur(j["steuerlast"])       for j in pro_jahre],
                    "CF vor St./Mon.":[fmt_eur(j["cf_vor_monat"])     for j in pro_jahre],
                    "CF nach St./Mon.":[fmt_eur(j["cf_nach_monat"])   for j in pro_jahre],
                    "Restschuld":     [fmt_eur(j["restschuld"])       for j in pro_jahre],
                }
                st.dataframe(
                    pd.DataFrame(tbl_data).set_index("Jahr"),
                    use_container_width=True,
                )

        st.markdown("---")

        # ── Bestehende 2-Spalten-Übersicht ───────────────────────────
        c_l, c_r = st.columns([1, 1.3], gap="large")

        with c_l:
            st.markdown(
                summary_banner(res["gesamt"], jahresmiete,
                               res["ek_abs"], res["knk_pct"]),
                unsafe_allow_html=True,
            )
            st.markdown(knk_table(bundesland, gest, notar, makler, res),
                        unsafe_allow_html=True)
            st.markdown(
                afa_badge(ai, res["afa"], res["afa_rate_used"],
                          gebaeude, res["gesamt"]),
                unsafe_allow_html=True,
            )
            ihr_pct = res["ihr_val"] / kaufpreis * 100 if kaufpreis else 0
            st.markdown(
                f'<div class="info-box">IHR (auto): '
                f'<span class="info-strong">{fmt_eur(res["ihr_val"])}/J</span>'
                f' · {ihr_pct:.2f} % des KP &nbsp;|&nbsp; Annuität: '
                f'<span class="info-strong">{fmt_eur(res["annuitaet"] / 12)}/Mon</span>'
                f' (Monatsrate konstant)</div>',
                unsafe_allow_html=True,
            )

        with c_r:
            if is_exp:
                kpis = [
                    ("Bruttorendite",    fmt_pct(res["brutto"]),   None,                  "brutto",   res["brutto"]),
                    ("Netto-Rendite",    fmt_pct(res["netto_r"]),  "inkl. IHR+Leerstand", "netto_r",  res["netto_r"]),
                    ("Cap Rate",         fmt_pct(res["cap_rate"]), "NOI / Kaufpreis",      "cap_rate", res["cap_rate"]),
                    ("DSCR",             f"{res['dscr']:.2f}".replace(".",","), "Schuldendeckung", "dscr", res["dscr"]),
                    ("LTV",              fmt_pct(res["ltv"],1),    "FK / Kaufpreis",       "ltv",      res["ltv"]),
                    ("Faktor",           fmt_x(res["faktor"]),     None,                   "faktor",   res["faktor"]),
                    ("CF pre-Tax/Mon.",  fmt_eur(res["cf_pre_m"]), None,                   "cf_pre_m", res["cf_pre_m"]),
                    ("CF post-Tax/Mon.", fmt_eur(res["cf_post_m"]),None,                   "cf_post_m",res["cf_post_m"]),
                    ("ROE",              fmt_pct(res["roe"]),       None,                   "roe",      res["roe"]),
                    ("IRR (10 J.)",      fmt_pct(res["irr_val"]),  None,                   "irr_val",  res["irr_val"]),
                    ("NPV",              fmt_eur(res["npv_val"]),  f"@ {diskont} % Diskont","npv_val", res["npv_val"]),
                    ("MOIC",             fmt_x(res["moic"]),       "CF + Equity / EK",     "moic",     res["moic"]),
                ]
                for i in range(0, len(kpis), 3):
                    cols = st.columns(3)
                    for j, (lbl, val, sub, k, av) in enumerate(kpis[i:i+3]):
                        with cols[j]:
                            st.markdown(kpi_card(lbl, val, sub, k, av, compact=True),
                                        unsafe_allow_html=True)
                st.markdown("&nbsp;", unsafe_allow_html=True)
                a1, a2, a3 = st.columns(3)
                with a1:
                    st.markdown(kpi_card("Break-Even-Miete", fmt_eur(res["be_m"])+"/Mon",
                                         "inkl. Leerstand", compact=True), unsafe_allow_html=True)
                with a2:
                    st.markdown(kpi_card("EK-Amortisation",
                                         fmt_yr(res["amort"]) if res["amort"] else "Negativ",
                                         "Post-Tax-CF", compact=True), unsafe_allow_html=True)
                with a3:
                    st.markdown(kpi_card("AfA p.a.", fmt_eur(res["afa"]),
                                         "auto", compact=True), unsafe_allow_html=True)

            # Kostenstruktur-Donut
            st.markdown("**Kostenstruktur**")
            d1, d2 = st.columns([1, 1.2])
            with d1:
                st.plotly_chart(
                    chart_donut(kaufpreis, res["gest_abs"],
                                res["notar_abs"], res["makler_abs"]),
                    use_container_width=True, config={"displayModeBar": False},
                )
            with d2:
                for n, v in [("Kaufpreis", kaufpreis),
                             ("Grunderwerbsteuer", res["gest_abs"]),
                             ("Notar/Grundbuch",   res["notar_abs"]),
                             ("Makler",            res["makler_abs"])]:
                    if v > 0:
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;'
                            f'font-size:13px;padding:4px 0;'
                            f'border-bottom:1px solid rgba(128,128,128,.08)">'
                            f'<span style="color:color-mix(in srgb,'
                            f'var(--text-color,#888) 70%,transparent)">{n}</span>'
                            f'<span style="font-family:var(--yb-mono,monospace);'
                            f'color:var(--text-color,#111)">{fmt_eur(v)}</span></div>',
                            unsafe_allow_html=True,
                        )


if __name__ == "__main__":
    main()
