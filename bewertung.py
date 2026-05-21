#!/usr/bin/env python3
"""
YieldBase v3.1 — Immobilien-Investment-Analyse
Python/Streamlit · GitHub-kompatibel

Fixes v3.1:
  • Vollständige Dark-Mode-Unterstützung via CSS-Variablen
  • Einheitliche Schrift: Inter (400/500/600/700)
  • Konsistente Schriftgrößen (10 / 12 / 13 / 14 / 16 / 20 / 24 px)
  • Alle Farben adaptiv — kein hartkodiertes Weiß/Dunkel mehr
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

AFA_REGELN = [
    {"von": 2023, "satz": 3.0, "label": "3,0 % – Neubau ab 2023",
     "basis": "§ 7 Abs. 4 S.1 Nr. 1 EStG",
     "note": "Lineare AfA über 33,3 J. Gilt für Fertigstellung ab 01.01.2023."},
    {"von": 1925, "satz": 2.0, "label": "2,0 % – Standard-AfA",
     "basis": "§ 7 Abs. 4 S.1 Nr. 2a EStG",
     "note": "Lineare AfA über 50 J. Gilt für Baujahr 1925–2022."},
    {"von": 0,    "satz": 2.5, "label": "2,5 % – Altbau vor 1925",
     "basis": "§ 7 Abs. 4 S.1 Nr. 2b EStG",
     "note": "Lineare AfA über 40 J. für Gebäudesubstanz vor 1925."},
]

# CSS-Klassen statt Inline-Farben → dark-mode-kompatibel
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
/* ── Schrift laden ──────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Design-Token (Light-Standard) ──────────────────────────────── */
:root {
  --yb-font:  'Inter', -apple-system, 'Segoe UI', sans-serif;
  --yb-mono:  'JetBrains Mono', 'Fira Code', monospace;

  /* Schriftgrößen — strikt einheitlich */
  --fs-xs:   10px;   /* Kategorie-Labels (UPPERCASE) */
  --fs-sm:   12px;   /* Notizen, Fußzeilen            */
  --fs-base: 13px;   /* Fließtext, Tabellen           */
  --fs-md:   14px;   /* Abschnitts-Titel              */
  --fs-lg:   16px;   /* KPI-Werte (kompakt)           */
  --fs-xl:   20px;   /* KPI-Werte (normal)            */
  --fs-2xl:  24px;   /* Zusammenfassungs-Werte        */
  --fs-3xl:  30px;   /* Hero-Zahl                     */

  /* Gold-Akzent */
  --gold:     #b8902a;
  --gold-bg:  rgba(184,144,42,.09);
  --gold-br:  rgba(184,144,42,.25);

  /* Ampel-Farben — lichtmodus */
  --c-g: #166534;  --bg-g: rgba(22,101,52,.09);   --br-g: rgba(22,101,52,.28);
  --c-y: #b45309;  --bg-y: rgba(180,83,9,.09);    --br-y: rgba(180,83,9,.28);
  --c-r: #9f1239;  --bg-r: rgba(159,18,57,.09);   --br-r: rgba(159,18,57,.28);
}

/* ── Dark-Mode (OS-Systemeinstellung + Streamlit) ─────────────── */
@media (prefers-color-scheme: dark) {
  :root {
    --gold:    #d4aa3e;
    --gold-bg: rgba(212,170,62,.12);
    --gold-br: rgba(212,170,62,.32);
    --c-g: #4ade80;  --bg-g: rgba(74,222,128,.12);   --br-g: rgba(74,222,128,.3);
    --c-y: #fbbf24;  --bg-y: rgba(251,191,36,.12);   --br-y: rgba(251,191,36,.3);
    --c-r: #fb7185;  --bg-r: rgba(251,113,133,.12);  --br-r: rgba(251,113,133,.3);
  }
}

/* Streamlit Dark-Theme (data-Attribut falls gesetzt) */
[data-theme="dark"] {
  --gold:    #d4aa3e !important;
  --gold-bg: rgba(212,170,62,.12) !important;
  --c-g: #4ade80 !important;
  --c-y: #fbbf24 !important;
  --c-r: #fb7185 !important;
  --bg-g: rgba(74,222,128,.12) !important;
  --bg-y: rgba(251,191,36,.12) !important;
  --bg-r: rgba(251,113,133,.12) !important;
  --br-g: rgba(74,222,128,.3) !important;
  --br-y: rgba(251,191,36,.3) !important;
  --br-r: rgba(251,113,133,.3) !important;
}

/* ── Ampel-Klassen ──────────────────────────────────────────────── */
.yb-g { --amp-c: var(--c-g); --amp-bg: var(--bg-g); --amp-br: var(--br-g); }
.yb-y { --amp-c: var(--c-y); --amp-bg: var(--bg-y); --amp-br: var(--br-y); }
.yb-r { --amp-c: var(--c-r); --amp-bg: var(--bg-r); --amp-br: var(--br-r); }

/* ── Basis-Reset ────────────────────────────────────────────────── */
html, body, [class*="css"] {
  font-family: var(--yb-font) !important;
  font-size: var(--fs-base);
}
.main .block-container { padding: 1.2rem 1.8rem 2rem; max-width: 1380px; }

/* ── KPI-Karte ──────────────────────────────────────────────────── */
.kpi {
  background: var(--background-color, #fff);
  border-radius: 10px;
  padding: 12px 14px;
  border: 1px solid rgba(128,128,128,.15);
  position: relative;
  overflow: hidden;
  margin-bottom: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
  transition: border-color .15s;
}
.kpi.yb-g, .kpi.yb-y, .kpi.yb-r { border-color: var(--amp-br); }
.kpi-bar {
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--amp-c);
}
.kpi-lbl {
  font-size: var(--fs-xs); font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; margin-bottom: 6px;
  color: var(--amp-c, color-mix(in srgb, var(--text-color, #666) 70%, transparent));
}
/* Wenn keine Ampel-Farbe → Standard Textfarbe */
.kpi:not(.yb-g):not(.yb-y):not(.yb-r) .kpi-lbl {
  color: color-mix(in srgb, var(--text-color, #888) 65%, transparent);
}
.kpi-val {
  font-family: var(--yb-mono);
  font-size: var(--fs-xl);
  font-weight: 700;
  line-height: 1;
  color: var(--amp-c, var(--text-color, #111));
}
.kpi:not(.yb-g):not(.yb-y):not(.yb-r) .kpi-val { color: var(--text-color, #111); }
.kpi-sm .kpi-val, .kpi-val.kpi-sm { font-size: var(--fs-lg) !important; }
.kpi-sub {
  font-size: var(--fs-sm); margin-top: 4px;
  color: color-mix(in srgb, var(--text-color, #999) 55%, transparent);
}
.kpi-badge {
  position: absolute; top: 10px; right: 8px;
  font-size: 9px; font-weight: 700; border-radius: 4px; padding: 2px 6px;
  color: var(--amp-c); background: var(--amp-bg);
}

/* ── Status-Bar ─────────────────────────────────────────────────── */
.sb-wrap {
  display: grid; grid-template-columns: repeat(6, 1fr);
  background: var(--secondary-background-color, #f7f6f3);
  border-radius: 10px; border: 1px solid rgba(128,128,128,.14);
  margin-bottom: 18px; overflow: hidden;
}
.sb-cell {
  text-align: center; padding: 10px 0;
  border-right: 1px solid rgba(128,128,128,.1);
}
.sb-cell:last-child { border-right: none; }
.sb-lbl {
  font-size: var(--fs-xs); font-weight: 600; letter-spacing: .05em;
  text-transform: uppercase; margin-bottom: 3px;
  color: color-mix(in srgb, var(--text-color, #888) 55%, transparent);
}
.sb-val {
  font-family: var(--yb-mono); font-size: var(--fs-base); font-weight: 700;
  color: var(--gold);
}

/* ── KNK-Tabelle ────────────────────────────────────────────────── */
.knk {
  border-radius: 8px; overflow: hidden;
  border: 1px solid var(--gold-br); margin-top: 8px;
}
.knk-head {
  background: var(--gold-bg); padding: 6px 12px;
  font-size: var(--fs-xs); color: var(--gold); font-weight: 700;
  letter-spacing: .08em; text-transform: uppercase;
  border-bottom: 1px solid var(--gold-br);
}
.knk-row {
  display: flex; justify-content: space-between; padding: 7px 12px;
  font-size: var(--fs-base);
  border-bottom: 1px solid rgba(128,128,128,.08);
  color: var(--text-color, #333);
}
.knk-row:nth-child(even) {
  background: color-mix(in srgb, var(--secondary-background-color, #f7f6f3) 60%, transparent);
}
.knk-total {
  background: var(--gold-bg) !important; font-weight: 700; color: var(--gold) !important;
  border-top: 2px solid var(--gold-br); border-bottom: none;
}
.knk-lbl { color: color-mix(in srgb, var(--text-color, #666) 70%, transparent); }
.knk-vals { display: flex; gap: 16px; }
.mono { font-family: var(--yb-mono); }

/* ── AfA-Badge ──────────────────────────────────────────────────── */
.afa-badge {
  background: var(--gold-bg); border: 1px solid var(--gold-br);
  border-radius: 8px; padding: 10px 12px; margin-top: 8px;
  display: flex; gap: 10px; align-items: flex-start;
}
.afa-icon  { font-size: 18px; flex-shrink: 0; line-height: 1.4; }
.afa-title { font-size: var(--fs-sm); font-weight: 700; color: var(--gold); margin-bottom: 3px; }
.afa-basis { font-size: var(--fs-sm); margin-bottom: 2px;
  color: color-mix(in srgb, var(--text-color, #666) 70%, transparent); }
.afa-note  { font-size: var(--fs-sm);
  color: color-mix(in srgb, var(--text-color, #999) 55%, transparent); }

/* ── Summary-Banner ─────────────────────────────────────────────── */
.sum-wrap {
  background: var(--gold-bg);
  border: 1px solid var(--gold-br); border-radius: 12px;
  padding: 18px 20px; margin-bottom: 12px;
}
.sum-label {
  font-size: var(--fs-xs); font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; margin-bottom: 4px;
  color: color-mix(in srgb, var(--text-color, #999) 55%, transparent);
}
.sum-total {
  font-family: var(--yb-mono); font-size: var(--fs-3xl);
  font-weight: 700; color: var(--gold); line-height: 1;
}
.sum-grid  {
  display: flex; gap: 20px; margin-top: 12px; padding-top: 12px;
  border-top: 1px solid var(--gold-br);
}
.sum-sub-lbl {
  font-size: var(--fs-xs); font-weight: 600; letter-spacing: .05em;
  text-transform: uppercase; margin-bottom: 3px;
  color: color-mix(in srgb, var(--text-color, #999) 50%, transparent);
}
.sum-sub-val {
  font-family: var(--yb-mono); font-size: var(--fs-base); font-weight: 700;
  color: var(--text-color, #111);
}

/* ── Info-Box ────────────────────────────────────────────────────── */
.info-box {
  background: var(--secondary-background-color, #f7f6f3);
  border-left: 3px solid var(--gold); border-radius: 0 6px 6px 0;
  padding: 7px 11px; margin-top: 6px; font-size: var(--fs-sm);
  color: color-mix(in srgb, var(--text-color, #666) 75%, transparent);
  line-height: 1.5;
}
.info-strong { font-weight: 700; color: var(--gold); }

/* ── Szenario-Tabelle ────────────────────────────────────────────── */
.sc-table { width: 100%; border-collapse: collapse; font-size: var(--fs-base); }
.sc-table th {
  padding: 8px 12px; font-size: var(--fs-xs); text-transform: uppercase;
  letter-spacing: .05em; font-weight: 700;
  border-bottom: 1px solid rgba(128,128,128,.15);
  background: var(--secondary-background-color, #f7f6f3);
  color: color-mix(in srgb, var(--text-color, #888) 65%, transparent);
}
.sc-table td {
  padding: 7px 12px; border-bottom: 1px solid rgba(128,128,128,.07);
  color: var(--text-color, #333);
}
.sc-table tr:nth-child(even) td {
  background: color-mix(in srgb, var(--secondary-background-color, #f7f6f3) 50%, transparent);
}

/* ── Divider ─────────────────────────────────────────────────────── */
.div-wrap { display: flex; align-items: center; gap: 10px; margin: 18px 0 12px; }
.div-line  { flex: 1; height: 1px; background: var(--gold); opacity: .25; }
.div-lbl   {
  font-size: var(--fs-xs); color: var(--gold); font-weight: 700;
  text-transform: uppercase; letter-spacing: .1em; white-space: nowrap;
}

/* ── Bericht-Zeile ───────────────────────────────────────────────── */
.rep-section-head {
  font-size: var(--fs-xs); font-weight: 700; text-transform: uppercase;
  letter-spacing: .1em; color: var(--gold); padding: 6px 0;
  border-bottom: 2px solid var(--gold-br); margin: 18px 0 8px;
}
.rep-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 7px 8px; border-radius: 4px;
  border-bottom: 1px solid rgba(128,128,128,.07);
  font-size: var(--fs-base); color: var(--text-color, #333);
}
.rep-row:nth-child(even) {
  background: color-mix(in srgb, var(--secondary-background-color, #f7f6f3) 50%, transparent);
}
.rep-lbl { color: color-mix(in srgb, var(--text-color, #888) 70%, transparent); }
.rep-note { font-size: var(--fs-sm); margin-right: 10px;
  color: color-mix(in srgb, var(--text-color, #aaa) 50%, transparent); }
.rep-val { font-family: var(--yb-mono); font-size: var(--fs-base); font-weight: 600;
  color: var(--text-color, #111); }

/* ── Disclaimer ─────────────────────────────────────────────────── */
.disclaimer {
  font-size: var(--fs-sm); line-height: 1.6; border-radius: 7px;
  padding: 10px 12px; margin-top: 12px;
  background: var(--secondary-background-color, #f7f6f3);
  color: color-mix(in srgb, var(--text-color, #aaa) 55%, transparent);
}

/* ── Header ─────────────────────────────────────────────────────── */
.yb-header {
  background: var(--secondary-background-color, #f7f6f3);
  border-bottom: 1px solid rgba(128,128,128,.15);
  padding: .8rem 1.5rem; margin: -1.2rem -1.8rem 1.4rem;
  display: flex; align-items: center; gap: .8rem;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.yb-logo { font-family: var(--yb-font); font-size: 18px; font-weight: 700;
  color: var(--text-color, #111); letter-spacing: -.02em; }
.yb-sub  { font-size: var(--fs-xs); color: var(--gold); letter-spacing: .1em;
  text-transform: uppercase; font-weight: 700; }

/* ── Streamlit-Widget-Overrides ─────────────────────────────────── */
html, body, [class*="css"] { font-family: var(--yb-font) !important; }
[data-testid="stMetricValue"]  { font-family: var(--yb-mono) !important; font-size: var(--fs-xl) !important; }
[data-testid="stMetricLabel"]  { font-size: var(--fs-xs) !important; text-transform: uppercase !important;
  letter-spacing: .05em !important; font-weight: 600 !important; }
[data-testid="stMetricDelta"]  { font-size: var(--fs-sm) !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  background: var(--secondary-background-color, #f7f6f3);
  border-radius: 9px; padding: 4px; gap: 3px;
  border: 1px solid rgba(128,128,128,.12);
}
.stTabs [data-baseweb="tab"] {
  border-radius: 7px; font-size: var(--fs-base); font-weight: 500;
  color: color-mix(in srgb, var(--text-color, #888) 70%, transparent);
}
.stTabs [aria-selected="true"] {
  background: var(--background-color, #fff) !important;
  color: var(--text-color, #111) !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 3px rgba(0,0,0,.08) !important;
}

/* Sidebar */
[data-testid="stSidebar"] > div:first-child { padding: 1.2rem 1rem; }
</style>
"""

# ══════════════════════════════════════════════════════════════════════
# 3. FORMAT-HELFER
# ══════════════════════════════════════════════════════════════════════

def fmt_eur(v) -> str:
    try:
        v = float(v)
        if not np.isfinite(v): return "—"
    except (TypeError, ValueError): return "—"
    sign = "−" if v < 0 else ""
    a = abs(v)
    if a >= 1_000_000: return f"{sign}{a/1_000_000:.2f}".replace(".", ",") + " Mio. €"
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
# 4. CALC ENGINE — Formeln geprüft (Audit v2.1)
# ══════════════════════════════════════════════════════════════════════

def get_afa_info(baujahr: int) -> dict:
    for r in AFA_REGELN:
        if baujahr >= r["von"]: return r
    return AFA_REGELN[-1]

def calc_ihr(kaufpreis: float, baujahr: int) -> float:
    age = datetime.now().year - baujahr
    if age < 10:  return kaufpreis * 0.003
    if age < 25:  return kaufpreis * 0.006
    if age < 40:  return kaufpreis * 0.010
    return kaufpreis * 0.013

def calc_irr(initial: float, cashflows: list) -> float:
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
    return initial + sum(c / (1.0 + rate)**(t+1) for t, c in enumerate(cashflows))

def calc_all(p: dict) -> dict:
    kp = p["kaufpreis"]
    knk_pct  = p["gest"] + p["notar"] + p["makler"]
    gest_abs  = kp * p["gest"]  / 100
    notar_abs = kp * p["notar"] / 100
    makler_abs= kp * p["makler"]/ 100
    knk_abs   = kp * knk_pct    / 100
    gesamt    = kp + knk_abs

    afa_info  = get_afa_info(p["baujahr"])
    afa_basis = gesamt * p["gebaeude"] / 100
    if p["is_denkmal"]:
        san = afa_basis * p["dk_san"] / 100
        afa = (afa_basis - san) * 0.02 + san * p["dk_afa"] / 100
        afa_rate_used = None
    else:
        afa_rate_used = p["afa_override"] if p["afa_manual"] else afa_info["satz"]
        afa = afa_basis * afa_rate_used / 100

    bew_k    = p["jahresmiete"] * p["bew"]       / 100
    leer_abs = p["jahresmiete"] * p["leerstand"] / 100
    ihr_val  = calc_ihr(kp, p["baujahr"])
    noi      = p["jahresmiete"] - bew_k - ihr_val
    netto    = p["jahresmiete"] - bew_k - leer_abs - ihr_val

    brutto   = round(p["jahresmiete"] / kp * 100, 2) if kp else 0.0
    faktor   = round(kp / p["jahresmiete"], 1) if p["jahresmiete"] else 0.0
    netto_r  = round(netto / gesamt * 100, 2) if gesamt else 0.0
    cap_rate = round(noi / kp * 100, 2) if kp else 0.0

    ek_abs    = gesamt * p["ek"] / 100
    fk        = gesamt - ek_abs
    annuitaet = fk * (p["zins"] + p["tilgung"]) / 100
    zins_j1   = fk * p["zins"] / 100
    kd        = annuitaet
    ltv       = round(fk / kp * 100, 1) if kp else 0.0
    dscr      = round(netto / kd, 2) if kd else 99.0

    stl_erg    = netto - zins_j1 - afa
    steuerlast = stl_erg * p["steuer"] / 100
    cf_pre_m   = round((netto - kd) / 12, 2)
    cf_post_m  = round((netto - kd - steuerlast) / 12, 2)

    roe = round((netto - zins_j1) / ek_abs * 100, 2) if ek_abs else 0.0
    roi = round(netto / gesamt * 100, 2) if gesamt else 0.0

    kostensatz = (p["bew"] + p["leerstand"]) / 100
    be_m = round(kd / (1 - kostensatz) / 12, 2) if (kostensatz < 1 and kd) else 0.0
    amort = round(ek_abs / (cf_post_m * 12), 1) if cf_post_m * 12 > 0 else None

    proj, irr_cfs, cum_cf = [], [], 0.0
    debt, m_brutto, iw = fk, p["jahresmiete"], kp
    for y in range(1, 11):
        mn     = m_brutto * (1 - p["bew"]/100 - p["leerstand"]/100) - ihr_val
        y_zins = debt * p["zins"] / 100
        y_tilg = min(debt, max(0.0, annuitaet - y_zins))
        y_cf   = mn - (y_zins + y_tilg)
        y_stl  = (mn - y_zins - afa) * p["steuer"] / 100
        y_cfp  = y_cf - y_stl
        cum_cf += y_cfp
        debt    = max(0.0, debt - y_tilg)
        iw     *= (1 + p["wert"] / 100)
        eq      = iw - debt
        irr_cfs.append(y_cfp + (max(0.0, eq - ek_abs) if y == 10 else 0.0))
        proj.append({"Jahr": f"J{y}", "CF pre/Mon.": round(y_cf/12),
                     "CF post/Mon.": round(y_cfp/12), "Equity": round(eq),
                     "Immobilienwert": round(iw), "Restschuld": round(debt)})
        m_brutto *= (1 + p["miets"] / 100)

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
        ek_abs=ek_abs, fk=fk, annuitaet=annuitaet, zins_j1=zins_j1,
        kd=kd, ltv=ltv, dscr=dscr,
        steuerlast=steuerlast, stl_erg=stl_erg, cf_pre_m=cf_pre_m, cf_post_m=cf_post_m,
        roe=roe, roi=roi, be_m=be_m, amort=amort,
        irr_val=irr_val, npv_val=npv_val, moic=moic, proj=proj,
    )

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
# 6. HTML-KOMPONENTEN — class-basiert, theme-adaptiv
# ══════════════════════════════════════════════════════════════════════

def kpi_card(label: str, value: str, sub: str | None = None,
             key: str | None = None, val: float | None = None,
             compact: bool = False) -> str:
    """KPI-Karte — adaptiert sich automatisch an Light/Dark-Mode."""
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
            f'<div class="div-line"></div>'
            f'</div>')


def knk_table(bundesland, gest, notar, makler, res) -> str:
    knk_pct = res["knk_pct"]
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
    return (f'<div class="knk">'
            f'<div class="knk-head">KNK-Aufschlüsselung</div>'
            f'{row_html}'
            f'<div class="knk-row knk-total"><span>KNK gesamt</span>'
            f'<span class="knk-vals"><span>{knk_pct:.2f} %</span>'
            f'<span>{fmt_eur(res["knk_abs"])}</span></span></div></div>')


def afa_badge(ai, afa_val, afa_rate_used, gebaeude, gesamt) -> str:
    used = (f'{afa_rate_used:.1f}% · {ai["basis"]}' if afa_rate_used else "Denkmal § 7i EStG")
    return (f'<div class="afa-badge"><span class="afa-icon">§</span><div>'
            f'<div class="afa-title">{ai["label"]}</div>'
            f'<div class="afa-basis">{ai["basis"]}</div>'
            f'<div class="afa-note">{ai["note"]}</div>'
            f'<div style="margin-top:6px;font-size:12px;">'
            f'AfA p.a.: <span class="info-strong">{fmt_eur(afa_val)}</span>'
            f' · {used}</div></div></div>')


def summary_banner(gesamt_val, jahresmiete_val, ek_val, bundesland_val, knk_pct_val) -> str:
    items = [("Gesamtinvestition", fmt_eur(gesamt_val)),
             ("Jahresmiete brutto", fmt_eur(jahresmiete_val)),
             ("Eigenkapital", fmt_eur(ek_val))]
    subs = "".join(
        f'<div><div class="sum-sub-lbl">{l}</div><div class="sum-sub-val">{v}</div></div>'
        for l, v in items
    )
    return (f'<div class="sum-wrap">'
            f'<div class="sum-label">Gesamtinvestition (inkl. {knk_pct_val:.2f}% KNK)</div>'
            f'<div class="sum-total">{fmt_eur(gesamt_val)}</div>'
            f'<div class="sum-grid">{subs}</div></div>')


def rep_section(title: str) -> str:
    return f'<div class="rep-section-head">{title}</div>'


def rep_row(label: str, value: str, note: str = "") -> str:
    note_h = f'<span class="rep-note">{note}</span>' if note else ""
    return (f'<div class="rep-row"><span class="rep-lbl">{label}</span>'
            f'<span>{note_h}<span class="rep-val">{value}</span></span></div>')

# ══════════════════════════════════════════════════════════════════════
# 7. CHARTS — Plotly mit theme-adaptierten Farben
# ══════════════════════════════════════════════════════════════════════

_BASE = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10, b=32, l=48, r=8),
    font=dict(family="Inter, -apple-system, sans-serif", size=11),
    hovermode="x unified",
    legend=dict(orientation="h", y=-0.28, x=0, font_size=11),
    xaxis=dict(showgrid=False, linecolor="rgba(128,128,128,.2)",
               tickfont=dict(size=11)),
    yaxis=dict(gridcolor="rgba(128,128,128,.1)", linecolor="rgba(128,128,128,.2)",
               tickfont=dict(size=11)),
)


def chart_cashflow(proj_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    # Navy-Linie für pre-tax (neutral, works in both modes)
    fig.add_trace(go.Scatter(
        x=proj_df["Jahr"], y=proj_df["CF pre/Mon."], name="CF pre-Tax / Mon.",
        fill="tozeroy", fillcolor="rgba(99,102,241,.07)",
        line=dict(color="#6366f1", width=2.5), mode="lines",
    ))
    # Gold-Linie für post-tax (CSS var kann in Plotly nicht verwendet werden)
    fig.add_trace(go.Scatter(
        x=proj_df["Jahr"], y=proj_df["CF post/Mon."], name="CF post-Tax / Mon.",
        fill="tozeroy", fillcolor="rgba(217,170,50,.08)",
        line=dict(color="#c9a530", width=2.5, dash="dash"), mode="lines",
    ))
    fig.update_layout(**_BASE, height=230)
    fig.update_yaxes(ticksuffix=" €", zeroline=True, zerolinecolor="rgba(128,128,128,.2)")
    return fig


def chart_equity(proj_df: pd.DataFrame) -> go.Figure:
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
    data = [(l, v, c) for l, v, c in [
        ("Kaufpreis",        kaufpreis,   "#6366f1"),
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
    fig.update_layout(
        height=160, margin=dict(t=5, b=5, l=5, r=5),
        paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
    )
    return fig

# ══════════════════════════════════════════════════════════════════════
# 8. HAUPT-APP
# ══════════════════════════════════════════════════════════════════════

def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)

    # Header
    st.markdown(
        '<div class="yb-header">'
        '<div style="width:30px;height:30px;background:linear-gradient(135deg,#b8902a,#e0c060);'
        'border-radius:7px;display:flex;align-items:center;justify-content:center;'
        'color:#fff;font-size:14px;font-weight:700">◆</div>'
        '<div><div class="yb-logo">YieldBase</div>'
        '<div class="yb-sub">Analytics v3 · Python</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── SIDEBAR ───────────────────────────────────────────────────────
    with st.sidebar:
        mode   = st.radio("Modus", ["Einsteiger", "Experte"],
                          horizontal=True, label_visibility="collapsed")
        is_exp = (mode == "Experte")
        st.markdown("---")

        st.markdown("#### 🏠 Standort & Kaufnebenkosten")
        bundesland = st.selectbox(
            "Bundesland", list(BUNDESLAND_GEST.keys()), index=0,
            help=" | ".join(f"{n}: {r:.1f}%" for n, r in BUNDESLAND_GEST.items()),
        )
        gest = BUNDESLAND_GEST[bundesland]
        st.info(f"Grunderwerbsteuer **{bundesland}**: **{gest:.1f} %** — automatisch")
        kaufpreis   = st.number_input("Kaufpreis (€)", 0, value=350_000, step=5_000)
        notar       = st.slider("Notar + Grundbuch (%)", 0.5, 2.5, 2.0, 0.1,
                                help="Notar ca. 1–1,5 % + Grundbuch ca. 0,5 %")
        makler      = st.slider("Maklercourtage (%)", 0.0, 3.57, 3.57, 0.01,
                                help="Käuferanteil max. 3,57 % inkl. MwSt. (§ 656c BGB)")
        st.markdown("---")

        st.markdown("#### 📋 Objekt & Mietertrag")
        jahresmiete = st.number_input("Jahres-Kaltmiete (€)", 0, value=18_000, step=500)
        baujahr     = st.number_input("Baujahr", 1800,
                                      datetime.now().year, value=1985, step=1,
                                      help="Bestimmt AfA-Satz und IHR automatisch.")
        afa_info    = get_afa_info(baujahr)
        st.success(f"**AfA:** {afa_info['label']}  ·  {afa_info['basis']}")
        bew         = st.slider("Bewirtschaftungskosten (%)", 5, 30, 15, 1,
                                help="Verwaltung + nicht-umlegbare BK + Ausfallwagnis. Ohne IHR!")
        leerstand   = st.slider("Leerstandsrisiko (%)", 0.0, 15.0, 3.0, 0.5)
        st.markdown("---")

        st.markdown("#### 🏦 Finanzierung")
        ek      = st.slider("Eigenkapital-Quote (%)", 5, 100, 25, 1)
        zins    = st.slider("Sollzins p.a. (%)", 0.5, 8.0, 3.8, 0.1)
        tilgung = st.slider("Anfangstilgung p.a. (%)", 0.5, 6.0, 2.0, 0.1,
                            help="Annuität = FK × (Zins + Tilgung) / 100 = konstant")

        if is_exp:
            st.markdown("---")
            st.markdown("#### ⚙️ Steuer, AfA & Projektion")
            steuer     = st.slider("Grenzsteuersatz (%)", 0, 45, 42, 1)
            gebaeude   = st.slider("Gebäudeanteil (%)", 40, 100, 80, 1,
                                   help="Boden ist nicht abschreibbar")
            is_denkmal = st.checkbox("Denkmalschutz-AfA (§ 7i EStG)")
            afa_manual = st.checkbox("AfA manuell überschreiben") if not is_denkmal else False
            dk_san = dk_afa = afa_override = 0.0
            if is_denkmal:
                dk_san  = st.slider("Sanierungsanteil (%)", 10, 90, 60, 1)
                dk_afa  = st.slider("Denkmal-AfA-Satz (%)", 3.0, 12.0, 9.0, 0.5)
            elif afa_manual:
                afa_override = st.number_input(
                    "AfA-Satz manuell (%)", 0.5, 10.0, float(afa_info["satz"]), 0.5)
            st.markdown("**10-Jahres-Projektion**")
            wert    = st.slider("Wertzuwachs p.a. (%)", -2.0, 6.0, 2.0, 0.5)
            miets   = st.slider("Mietsteigerung p.a. (%)", 0.0, 5.0, 1.5, 0.25)
            diskont = st.slider("Diskontierungssatz NPV (%)", 1.0, 12.0, 5.0, 0.5)
        else:
            steuer = 42; gebaeude = 80; is_denkmal = False
            afa_manual = False; dk_san = 60; dk_afa = 9.0
            afa_override = float(afa_info["satz"])
            wert = 2.0; miets = 1.5; diskont = 5.0

    # ── BERECHNUNG ────────────────────────────────────────────────────
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

    # ── STATUS BAR ────────────────────────────────────────────────────
    st.markdown(
        status_bar([
            ("Gesamtinvestition",  fmt_eur(res["gesamt"])),
            ("Brutto-Rendite",     fmt_pct(res["brutto"])),
            ("Netto-Rendite",      fmt_pct(res["netto_r"])),
            ("Cashflow / Mon.",    fmt_eur(res["cf_pre_m"])),
            ("DSCR",               f"{res['dscr']:.2f}".replace(".", ",")),
            ("ROE",                fmt_pct(res["roe"])),
        ]),
        unsafe_allow_html=True,
    )

    # ── TABS ──────────────────────────────────────────────────────────
    t1, t2, t3, t4 = st.tabs(
        ["📊 Eingabe & KPIs", "▦ Dashboard", "⛶ Analyse", "▤ Bericht"]
    )

    # ══════════════════════════════════════════════════════════════════
    # TAB 1
    # ══════════════════════════════════════════════════════════════════
    with t1:
        c_l, c_r = st.columns([1, 1.3], gap="large")

        with c_l:
            st.markdown(
                summary_banner(res["gesamt"], jahresmiete, res["ek_abs"],
                               bundesland, res["knk_pct"]),
                unsafe_allow_html=True,
            )
            st.markdown(knk_table(bundesland, gest, notar, makler, res),
                        unsafe_allow_html=True)
            st.markdown(
                afa_badge(ai, res["afa"], res["afa_rate_used"], gebaeude, res["gesamt"]),
                unsafe_allow_html=True,
            )
            ihr_pct = res["ihr_val"] / kaufpreis * 100 if kaufpreis else 0
            st.markdown(
                f'<div class="info-box">IHR (auto): '
                f'<span class="info-strong">{fmt_eur(res["ihr_val"])}/J</span>'
                f' · {ihr_pct:.2f} % des KP &nbsp;|&nbsp; Annuität: '
                f'<span class="info-strong">{fmt_eur(res["annuitaet"]/12)}/Mon</span></div>',
                unsafe_allow_html=True,
            )

        with c_r:
            if is_exp:
                kpis = [
                    ("Bruttorendite",    fmt_pct(res["brutto"]),   None,                   "brutto",   res["brutto"]),
                    ("Netto-Rendite",    fmt_pct(res["netto_r"]),  "inkl. IHR+Leerstand",  "netto_r",  res["netto_r"]),
                    ("Cap Rate",         fmt_pct(res["cap_rate"]), "NOI / Kaufpreis",       "cap_rate", res["cap_rate"]),
                    ("DSCR",             f"{res['dscr']:.2f}".replace(".",","), "Schuldendeckung", "dscr", res["dscr"]),
                    ("LTV",              fmt_pct(res["ltv"],1),    "FK / Kaufpreis ✓",      "ltv",      res["ltv"]),
                    ("Faktor",           fmt_x(res["faktor"]),     None,                    "faktor",   res["faktor"]),
                    ("CF pre-Tax/Mon.",  fmt_eur(res["cf_pre_m"]), None,                    "cf_pre_m", res["cf_pre_m"]),
                    ("CF post-Tax/Mon.", fmt_eur(res["cf_post_m"]),None,                    "cf_post_m",res["cf_post_m"]),
                    ("ROE",              fmt_pct(res["roe"]),       None,                    "roe",      res["roe"]),
                    ("IRR (10 J.)",      fmt_pct(res["irr_val"]),  None,                    "irr_val",  res["irr_val"]),
                    ("NPV",              fmt_eur(res["npv_val"]),  f"@ {diskont} % Diskont","npv_val",  res["npv_val"]),
                    ("MOIC",             fmt_x(res["moic"]),       "CF + Equity / EK ✓",    "moic",     res["moic"]),
                ]
                for i in range(0, len(kpis), 3):
                    cols = st.columns(3)
                    for j, (lbl, val, sub, k, av) in enumerate(kpis[i:i+3]):
                        with cols[j]:
                            st.markdown(kpi_card(lbl, val, sub, k, av, compact=True),
                                        unsafe_allow_html=True)
                st.markdown("&nbsp;", unsafe_allow_html=True)
                a1, a2, a3 = st.columns(3)
                with a1: st.markdown(kpi_card("Break-Even-Miete", fmt_eur(res["be_m"])+"/Mon",
                                              "inkl. Leerstand ✓", compact=True), unsafe_allow_html=True)
                with a2: st.markdown(kpi_card("EK-Amortisation",
                                              fmt_yr(res["amort"]) if res["amort"] else "Negativ",
                                              "Post-Tax-CF", compact=True), unsafe_allow_html=True)
                with a3: st.markdown(kpi_card("AfA p.a.", fmt_eur(res["afa"]),
                                              "auto ✓", compact=True), unsafe_allow_html=True)
            else:
                b = [
                    ("Bruttorendite",   fmt_pct(res["brutto"]),   "Kaufpreis-Basis",           "brutto",   res["brutto"]),
                    ("Netto-Rendite",   fmt_pct(res["netto_r"]),  "nach Bew. + Leerstand + IHR","netto_r",  res["netto_r"]),
                    ("DSCR",           f"{res['dscr']:.2f}".replace(".",","), "Schuldendeckung","dscr",     res["dscr"]),
                    ("Cashflow / Mon.", fmt_eur(res["cf_pre_m"]), "Vor Steuer",                 "cf_pre_m", res["cf_pre_m"]),
                ]
                c1, c2 = st.columns(2)
                for i, (lbl, val, sub, k, av) in enumerate(b):
                    with (c1 if i % 2 == 0 else c2):
                        st.markdown(kpi_card(lbl, val, sub, k, av), unsafe_allow_html=True)

            st.markdown("**Kostenstruktur**")
            d1, d2 = st.columns([1, 1.2])
            with d1:
                st.plotly_chart(
                    chart_donut(kaufpreis, res["gest_abs"], res["notar_abs"], res["makler_abs"]),
                    use_container_width=True, config={"displayModeBar": False},
                )
            with d2:
                for n, v in [("Kaufpreis", kaufpreis), ("Grunderwerbsteuer", res["gest_abs"]),
                             ("Notar/Grundbuch", res["notar_abs"]), ("Makler", res["makler_abs"])]:
                    if v > 0:
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;'
                            f'font-size:13px;padding:4px 0;border-bottom:1px solid rgba(128,128,128,.08)">'
                            f'<span style="color:color-mix(in srgb,var(--text-color,#888) 70%,transparent)">{n}</span>'
                            f'<span style="font-family:var(--yb-mono,monospace);color:var(--text-color,#111)">{fmt_eur(v)}</span></div>',
                            unsafe_allow_html=True,
                        )

    # ══════════════════════════════════════════════════════════════════
    # TAB 2 — Dashboard
    # ══════════════════════════════════════════════════════════════════
    with t2:
        sects = [
            ("Rendite & Ertrag", [
                ("Bruttorendite",    fmt_pct(res["brutto"]),    "Jahresmiete / KP",           "brutto",   res["brutto"]),
                ("Netto-Rendite",    fmt_pct(res["netto_r"]),   "nach Bew. + Leerstand + IHR","netto_r",  res["netto_r"]),
                ("Cap Rate",         fmt_pct(res["cap_rate"]),  "NOI / Kaufpreis",             "cap_rate", res["cap_rate"]),
                ("Kaufpreisfaktor",  fmt_x(res["faktor"]),      None,                          "faktor",   res["faktor"]),
                ("Jahresmiete",      fmt_eur(jahresmiete),       "Brutto",                      None,       None),
                ("Nettomietertrag",  fmt_eur(res["netto"]),      "Miete − Bew. − Leerst. − IHR",None,      None),
            ]),
            ("Cashflow & Liquidität", [
                ("CF / Mon. (pre)",  fmt_eur(res["cf_pre_m"]),  "Vor Steuer",                  "cf_pre_m", res["cf_pre_m"]),
                ("CF / Mon. (post)", fmt_eur(res["cf_post_m"]), "Nach Steuer",                 "cf_post_m",res["cf_post_m"]),
                ("CF / Jahr",        fmt_eur(res["cf_pre_m"]*12),"Annualisiert (pre)",          None,       None),
                ("Break-Even-Miete", fmt_eur(res["be_m"])+"/Mon","inkl. Leerstand ✓",           None,       None),
                ("AfA p.a.",         fmt_eur(res["afa"]),        ai["basis"],                    None,       None),
                ("Steuerlast p.a.",  fmt_eur(res["steuerlast"]),  f"{steuer} % Steuersatz",      None,       None),
            ]),
            ("Finanzierung & Verschuldung", [
                ("DSCR",             f"{res['dscr']:.2f}".replace(".",","), "Schuldendeckung", "dscr",     res["dscr"]),
                ("LTV (FK / KP)",    fmt_pct(res["ltv"],1),      "Banküblich ✓",                "ltv",      res["ltv"]),
                ("Eigenkapital",     fmt_eur(res["ek_abs"]),     f"{ek} %",                     None,       None),
                ("Fremdkapital",     fmt_eur(res["fk"]),         None,                          None,       None),
                ("Zinslast J1",      fmt_eur(res["zins_j1"]),    f"{zins} %",                   None,       None),
                ("Annuität p.a.",    fmt_eur(res["annuitaet"]),  "konstant ✓",                  None,       None),
            ]),
            ("Investment-Returns (10 Jahre)", [
                ("ROE",              fmt_pct(res["roe"]),        "Leveraged Return",             "roe",      res["roe"]),
                ("ROI",              fmt_pct(res["roi"]),        "Gesamtkapital",                None,       None),
                ("IRR (10 J.)",      fmt_pct(res["irr_val"]),    "inkl. Wertzuwachs",           "irr_val",  res["irr_val"]),
                ("NPV",              fmt_eur(res["npv_val"]),     f"@ {diskont} % Diskont",      "npv_val",  res["npv_val"]),
                ("MOIC",             fmt_x(res["moic"]),         "CF + Equity / EK ✓",          "moic",     res["moic"]),
                ("EK-Amortisation",  fmt_yr(res["amort"]) if res["amort"] else "Negativ", "Post-Tax-CF", None, None),
            ]),
        ]
        for sec_title, cards in sects:
            st.markdown(divider(sec_title), unsafe_allow_html=True)
            cols = st.columns(6)
            for i, (lbl, val, sub, k, av) in enumerate(cards):
                with cols[i % 6]:
                    st.markdown(kpi_card(lbl, val, sub, k, av, compact=True),
                                unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════
    # TAB 3 — Analyse
    # ══════════════════════════════════════════════════════════════════
    with t3:
        ca, cb = st.columns(2, gap="large")
        with ca:
            st.markdown(f"**Cashflow-Projektion (10 Jahre)**")
            st.caption(f"Annuität {fmt_eur(res['annuitaet']/12)}/Mon konstant — Annuitätendarlehen")
            st.plotly_chart(chart_cashflow(proj_df), use_container_width=True,
                            config={"displayModeBar": False})
        with cb:
            st.markdown("**Vermögensaufbau — Equity Buildup**")
            st.caption("Eigenkapital = Immobilienwert − Restschuld")
            st.plotly_chart(chart_equity(proj_df), use_container_width=True,
                            config={"displayModeBar": False})

        st.markdown("---")
        st.markdown("**Szenario-Vergleich**")
        st.caption("Opt.: +10 % Miete, −0,5 % Zins, +1,5 % Wert · Pess.: −10 % Miete, +0,8 % Zins, +3 % Leerstand")

        p_opt  = {**params, "jahresmiete": jahresmiete*1.1,
                  "zins": max(0.5, zins-0.5), "leerstand": max(0.0, leerstand-1.0),
                  "wert": wert+1.5}
        p_pess = {**params, "jahresmiete": jahresmiete*0.9,
                  "zins": zins+0.8, "leerstand": leerstand+3.0,
                  "wert": max(0.0, wert-1.5)}
        r_opt, r_pess = calc_all(p_opt), calc_all(p_pess)

        sc_kpis = [
            ("Brutto-Rendite", "brutto",   fmt_pct),
            ("Netto-Rendite",  "netto_r",  fmt_pct),
            ("DSCR",           "dscr",     lambda v: f"{v:.2f}".replace(".", ",")),
            ("CF / Mon. (pre)","cf_pre_m", fmt_eur),
            ("LTV",            "ltv",      lambda v: fmt_pct(v, 1)),
            ("ROE",            "roe",      fmt_pct),
            ("IRR (10 J.)",    "irr_val",  fmt_pct),
            ("NPV",            "npv_val",  fmt_eur),
            ("MOIC",           "moic",     fmt_x),
        ]

        # Ampel-Farben als CSS-Variablen für Szenario-Zellen
        AMP_CSS = {"g": "var(--c-g)", "y": "var(--c-y)", "r": "var(--c-r)"}

        def sc_td(key, v, fmt_fn):
            c = AMP_CSS[get_ampel(key, v)]
            return f'<td style="text-align:right;font-family:var(--yb-mono,monospace);color:{c}">{fmt_fn(v)}</td>'

        rows_h = "".join(
            f'<tr><td style="font-size:13px;padding:7px 12px">{lbl}</td>'
            f'{sc_td(k, r_opt[k], fn)}'
            f'{sc_td(k, res[k],   fn)}'
            f'{sc_td(k, r_pess[k],fn)}</tr>'
            for lbl, k, fn in sc_kpis
        )
        heads = [("KPI","left","color:var(--text-color,#888)"),
                 ("Optimistisch","right","color:var(--c-g)"),
                 ("Realistisch","right","color:var(--gold)"),
                 ("Pessimistisch","right","color:var(--c-r)")]
        head_h = "".join(
            f'<th style="text-align:{a};font-size:10px;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:.05em;padding:8px 12px;'
            f'border-bottom:1px solid rgba(128,128,128,.15);{c}">{h}</th>'
            for h, a, c in heads
        )
        st.markdown(
            f'<table class="sc-table"><thead><tr>{head_h}</tr></thead>'
            f'<tbody>{rows_h}</tbody></table>',
            unsafe_allow_html=True,
        )

    # ══════════════════════════════════════════════════════════════════
    # TAB 4 — Bericht
    # ══════════════════════════════════════════════════════════════════
    with t4:
        col_rep, _ = st.columns([2.2, 1])
        with col_rep:

            # Ampel-Tags
            tags_h = " ".join(
                f'<span style="font-size:11px;font-weight:700;padding:3px 10px;'
                f'border-radius:20px;background:var(--bg-{get_ampel(k,v)});'
                f'color:var(--c-{get_ampel(k,v)});'
                f'border:1px solid var(--br-{get_ampel(k,v)})">{l}</span>'
                for l, k, v in [
                    ("Rendite","netto_r",res["netto_r"]),
                    ("CF","cf_pre_m",res["cf_pre_m"]),
                    ("DSCR","dscr",res["dscr"]),
                    ("LTV","ltv",res["ltv"]),
                    ("ROE","roe",res["roe"]),
                    ("IRR","irr_val",res["irr_val"]),
                    ("NPV","npv_val",res["npv_val"]),
                    ("MOIC","moic",res["moic"]),
                ]
            )
            sum_cards = "".join(
                f'<div style="flex:1;background:var(--background-color,#fff);'
                f'border-radius:8px;padding:12px 14px;border:1px solid var(--gold-br)">'
                f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:.06em;color:color-mix(in srgb,var(--text-color,#999) 55%,transparent);'
                f'margin-bottom:4px">{l}</div>'
                f'<div style="font-family:var(--yb-mono,monospace);font-size:20px;'
                f'font-weight:700;color:var(--gold)">{v}</div></div>'
                for l, v in [("Gesamtinvestition",fmt_eur(res["gesamt"])),
                              ("Jahresmiete brutto",fmt_eur(jahresmiete)),
                              ("Eigenkapital",fmt_eur(res["ek_abs"]))]
            )
            st.markdown(
                f'<div class="sum-wrap" style="border-radius:14px;padding:22px 26px">'
                f'<div style="font-family:var(--yb-font);font-size:22px;font-weight:700;'
                f'color:var(--text-color,#111);margin-bottom:4px;letter-spacing:-.02em">'
                f'Investment Summary</div>'
                f'<div style="font-size:12px;margin-bottom:16px;'
                f'color:color-mix(in srgb,var(--text-color,#aaa) 55%,transparent)">'
                f'YieldBase v3 · {datetime.now().strftime("%d.%m.%Y")} · {bundesland}</div>'
                f'<div style="display:flex;gap:10px;margin-bottom:14px">{sum_cards}</div>'
                f'<div style="display:flex;flex-wrap:wrap;gap:5px">{tags_h}</div></div>',
                unsafe_allow_html=True,
            )

            st.markdown("**Vollständige KPI-Tabelle**")

            kpi_sects = [
                ("Transaktion", [
                    ("Kaufpreis",                      fmt_eur(kaufpreis),         ""),
                    (f"Grunderwerbsteuer ({bundesland})", fmt_eur(res["gest_abs"]),  f"{gest:.1f} %"),
                    ("Notar + Grundbuch",               fmt_eur(res["notar_abs"]),  f"{notar:.1f} %"),
                    ("Maklercourtage",                  fmt_eur(res["makler_abs"]),  f"{makler:.2f} %"),
                    (f"KNK gesamt ({res['knk_pct']:.2f} %)", fmt_eur(res["knk_abs"]), "Summe"),
                    ("Gesamtinvestition",               fmt_eur(res["gesamt"]),      ""),
                ]),
                ("Ertrag & Rendite", [
                    ("Jahresmiete (Brutto)",            fmt_eur(jahresmiete),        ""),
                    (f"Bewirtschaftungskosten ({bew} %)",fmt_eur(res["bew_k"]),     ""),
                    (f"Leerstandsverlust ({leerstand} %)",fmt_eur(res["leer_abs"]), ""),
                    ("Instandhaltungsrücklage (auto)",  fmt_eur(res["ihr_val"]),     ""),
                    ("Nettomietertrag",                 fmt_eur(res["netto"]),       ""),
                    ("NOI (Cap-Rate-Basis)",            fmt_eur(res["noi"]),         "ohne Leerstand"),
                    ("Bruttorendite",                   fmt_pct(res["brutto"]),      ""),
                    ("Netto-Rendite",                   fmt_pct(res["netto_r"]),     ""),
                    ("Cap Rate",                       fmt_pct(res["cap_rate"]),    ""),
                    ("Kaufpreisfaktor",                 fmt_x(res["faktor"]),        ""),
                ]),
                ("Finanzierung & AfA", [
                    ("Eigenkapital",                    fmt_eur(res["ek_abs"]),      f"{ek} %"),
                    ("Fremdkapital",                    fmt_eur(res["fk"]),          ""),
                    ("LTV (FK / Kaufpreis) ✓",          fmt_pct(res["ltv"],1),       ""),
                    ("Annuität p.a. ✓",                 fmt_eur(res["annuitaet"]),   "konstant"),
                    ("Zinslast J1",                     fmt_eur(res["zins_j1"]),     ""),
                    ("DSCR",                           f"{res['dscr']:.2f}".replace(".",","), ""),
                    (f"AfA ({ai['label']})",            fmt_eur(res["afa"]),         ai["basis"]),
                    ("Steuerlast p.a.",                 fmt_eur(res["steuerlast"]),  f"{steuer} %"),
                    ("CF / Monat pre-Tax",              fmt_eur(res["cf_pre_m"]),    ""),
                    ("CF / Monat post-Tax",             fmt_eur(res["cf_post_m"]),   ""),
                    ("Break-Even-Miete ✓",              fmt_eur(res["be_m"])+"/Mon.","inkl. Leerstand"),
                ]),
                ("Investment-Returns", [
                    ("ROE (Eigenkapitalrendite)",       fmt_pct(res["roe"]),         ""),
                    ("ROI (Gesamtkapital)",             fmt_pct(res["roi"]),         ""),
                    ("IRR (10 Jahre)",                  fmt_pct(res["irr_val"]),     "inkl. Wertzuwachs"),
                    (f"NPV ({diskont} % Diskont)",       fmt_eur(res["npv_val"]),    ""),
                    ("MOIC ✓",                         fmt_x(res["moic"]),           "CF + Equity / EK"),
                    ("EK-Amortisation",                fmt_yr(res["amort"]) if res["amort"] else "Negativ", ""),
                ]),
            ]
            for sec_title, rows in kpi_sects:
                st.markdown(rep_section(sec_title), unsafe_allow_html=True)
                for lbl, val, note in rows:
                    st.markdown(rep_row(lbl, val, note), unsafe_allow_html=True)

            st.markdown(
                f'<div class="disclaimer">Rechtlicher Hinweis: Modellsimulation ohne Gewähr. '
                f'Keine Anlageberatung. AfA: {ai["label"]} — {ai["basis"]}. '
                f'GrESt {bundesland}: {gest:.1f} %. '
                f'Formeln geprüft (Audit v2.1). © 2025 YieldBase Analytics.</div>',
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
