#!/usr/bin/env python3
"""
YieldBase v3 — Immobilien-Investment-Analyse
Python/Streamlit-Port · GitHub-kompatibel

Neue Features:
  • Bundesland-Selektor mit automatischer Grunderwerbsteuer
  • AfA-Automatik aus Baujahr (§ 7 Abs. 4 EStG)
  • KNK-Aufschlüsselung (GrESt + Notar + Makler)
  • Alle geprüften KPIs: IRR, NPV, MOIC, DSCR, LTV etc.
  • Ampel-System (Gut / Prüfen / Kritisch)
  • Szenario-Vergleich
  • Interaktive Plotly-Charts
  • Premium Light-Design

Installation:  pip install -r requirements.txt
Starten:       streamlit run app.py
"""

# ── Seitenconfig muss als ERSTER Streamlit-Aufruf stehen ──────────────
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

# AfA-Sätze nach § 7 Abs. 4 EStG — sortiert absteigend nach Baujahr
AFA_REGELN = [
    {
        "von": 2023, "satz": 3.0,
        "label": "3,0 % – Neubau ab 2023",
        "basis": "§ 7 Abs. 4 S.1 Nr. 1 EStG",
        "note":  "Lineare AfA über 33,3 J. Gilt für Fertigstellung ab 01.01.2023.",
    },
    {
        "von": 1925, "satz": 2.0,
        "label": "2,0 % – Standard-AfA",
        "basis": "§ 7 Abs. 4 S.1 Nr. 2a EStG",
        "note":  "Lineare AfA über 50 J. Gilt für Baujahr 1925 bis 31.12.2022.",
    },
    {
        "von": 0, "satz": 2.5,
        "label": "2,5 % – Altbau vor 1925",
        "basis": "§ 7 Abs. 4 S.1 Nr. 2b EStG",
        "note":  "Lineare AfA über 40 J. für Altbausubstanz vor 01.01.1925.",
    },
]

AMPEL: dict[str, dict] = {
    "g": {"c": "#065f46", "bg": "rgba(6,95,70,.08)",   "br": "rgba(6,95,70,.25)",   "t": "Gut"},
    "y": {"c": "#92400e", "bg": "rgba(146,64,14,.08)", "br": "rgba(146,64,14,.25)", "t": "Prüfen"},
    "r": {"c": "#991b1b", "bg": "rgba(153,27,27,.08)", "br": "rgba(153,27,27,.25)", "t": "Kritisch"},
}

GOLD = "#8b6914"
NAVY = "#1a2332"

# ══════════════════════════════════════════════════════════════════════
# 2. PREMIUM LIGHT-DESIGN — Custom CSS
# ══════════════════════════════════════════════════════════════════════

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono&family=Cormorant+Garamond:ital,wght@1,700&display=swap');

/* Basis */
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', -apple-system, sans-serif; }
.main .block-container { padding: 1.2rem 1.8rem 2rem; max-width: 1380px; }

/* Sidebar */
[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #e8e4dc; }
[data-testid="stSidebar"] > div:first-child { padding: 1.2rem 1rem; }

/* Header-Banner */
.yb-header { background:#fff; border-bottom:1px solid #e8e4dc; padding:.8rem 1.5rem;
  margin:-1.2rem -1.8rem 1.4rem; display:flex; align-items:center; gap:.8rem;
  box-shadow:0 1px 4px rgba(0,0,0,.05); }
.yb-logo { font-family:'Cormorant Garamond',Georgia,serif; font-size:22px;
  font-style:italic; font-weight:700; color:#1a2332; line-height:1; }
.yb-sub  { font-size:9px; color:#8b6914; letter-spacing:.1em;
  text-transform:uppercase; font-weight:700; }

/* Status-Bar */
.sb-wrap { display:grid; grid-template-columns:repeat(6,1fr); background:#f8f6f2;
  border-radius:10px; border:1px solid #e8e4dc; margin-bottom:18px; overflow:hidden; }
.sb-cell { text-align:center; padding:9px 0; border-right:1px solid #e8e4dc; }
.sb-cell:last-child { border-right:none; }
.sb-lbl  { font-size:9px; color:#9ca3af; text-transform:uppercase;
  letter-spacing:.05em; margin-bottom:2px; }
.sb-val  { font-family:'JetBrains Mono',monospace; font-size:13px;
  font-weight:700; color:#8b6914; }

/* KPI-Karten */
.kpi { background:#fff; border-radius:10px; padding:12px 14px; border:1px solid #e8e4dc;
  position:relative; overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,.04);
  margin-bottom:4px; }
.kpi-g { border-color:rgba(6,95,70,.25) !important; }
.kpi-y { border-color:rgba(146,64,14,.25) !important; }
.kpi-r { border-color:rgba(153,27,27,.25) !important; }
.kpi-bar { position:absolute; top:0; left:0; right:0; height:3px; }
.kpi-lbl { font-size:10px; text-transform:uppercase; letter-spacing:.06em;
  font-weight:600; margin-bottom:5px; }
.kpi-val { font-family:'JetBrains Mono',monospace; font-size:17px;
  font-weight:700; line-height:1; }
.kpi-sm  { font-size:13px !important; }
.kpi-sub { font-size:10px; color:#9ca3af; margin-top:3px; }
.kpi-badge { position:absolute; top:9px; right:7px; font-size:9px;
  font-weight:700; border-radius:4px; padding:2px 6px; }

/* KNK-Tabelle */
.knk { border-radius:8px; overflow:hidden; border:1px solid rgba(139,105,20,.2);
  margin-top:8px; font-size:11px; }
.knk-head { background:rgba(139,105,20,.07); padding:6px 10px; font-size:10px;
  color:#8b6914; font-weight:700; text-transform:uppercase; letter-spacing:.08em;
  border-bottom:1px solid rgba(139,105,20,.2); }
.knk-row { display:flex; justify-content:space-between; padding:6px 10px;
  border-bottom:1px solid #f0ece6; }
.knk-row:nth-child(even) { background:#faf8f5; }
.knk-total { background:rgba(139,105,20,.07); font-weight:700; color:#8b6914;
  border-top:2px solid rgba(139,105,20,.2); border-bottom:none; }
.knk-lbl { color:#6b7280; }
.knk-vals { display:flex; gap:14px; }
.mono { font-family:'JetBrains Mono',monospace; color:#1a2332; }

/* AfA-Badge */
.afa-badge { background:rgba(139,105,20,.07); border:1px solid rgba(139,105,20,.2);
  border-radius:8px; padding:10px 12px; margin-top:6px;
  display:flex; gap:10px; align-items:flex-start; }
.afa-icon  { font-size:18px; flex-shrink:0; }
.afa-title { font-size:11px; font-weight:700; color:#8b6914; margin-bottom:2px; }
.afa-basis { font-size:10px; color:#6b7280; margin-bottom:2px; }
.afa-note  { font-size:10px; color:#9ca3af; }

/* Summary-Banner */
.sum-wrap { background:linear-gradient(135deg,rgba(139,105,20,.07),#fff);
  border:1px solid rgba(139,105,20,.2); border-radius:12px;
  padding:18px 20px; margin-bottom:12px; box-shadow:0 1px 6px rgba(139,105,20,.06); }
.sum-total { font-family:'Cormorant Garamond',Georgia,serif; font-size:28px;
  font-style:italic; font-weight:700; color:#8b6914; line-height:1; }
.sum-grid  { display:flex; gap:18px; margin-top:10px; padding-top:10px;
  border-top:1px solid rgba(139,105,20,.18); }
.sum-lbl   { font-size:9px; color:#9ca3af; text-transform:uppercase;
  letter-spacing:.05em; margin-bottom:2px; }
.sum-val   { font-family:'JetBrains Mono',monospace; font-size:13px;
  color:#1a2332; font-weight:700; }

/* Szenario-Tabelle */
.sc-table { width:100%; border-collapse:collapse; font-size:11px; }
.sc-table th { padding:8px 12px; font-size:10px; text-transform:uppercase;
  letter-spacing:.05em; font-weight:700; border-bottom:1px solid #e8e4dc;
  background:#f8f6f2; }
.sc-table td { padding:7px 12px; border-bottom:1px solid #f0ece6; }
.sc-table tr:nth-child(even) td { background:#faf8f5; }

/* Divider */
.div-wrap { display:flex; align-items:center; gap:10px; margin:16px 0 12px; }
.div-line  { flex:1; height:1px; background:linear-gradient(to right,#8b6914,transparent); opacity:.3; }
.div-lbl   { font-size:10px; color:#8b6914; font-weight:700;
  text-transform:uppercase; letter-spacing:.1em; white-space:nowrap; }

/* Info-Box */
.info-box { background:#f8f6f2; border-left:3px solid #8b6914; border-radius:0 6px 6px 0;
  padding:7px 11px; margin-top:6px; font-size:11px; color:#6b7280; line-height:1.5; }
.disclaimer { font-size:10px; color:#9ca3af; line-height:1.6; background:#f8f6f2;
  border-radius:7px; padding:10px 12px; margin-top:12px; }

/* Streamlit overrides */
[data-testid="stMetricValue"] { font-family:'JetBrains Mono',monospace !important; }
.stTabs [data-baseweb="tab-list"] { background:#f8f6f2; border-radius:9px;
  padding:4px; gap:3px; border:1px solid #e8e4dc; }
.stTabs [data-baseweb="tab"] { border-radius:7px; font-size:12px; font-weight:500; }
.stTabs [aria-selected="true"] { background:#fff !important; color:#1a2332 !important;
  font-weight:600 !important; box-shadow:0 1px 3px rgba(0,0,0,.06); }
</style>
"""

# ══════════════════════════════════════════════════════════════════════
# 3. FORMAT-HELFER
# ══════════════════════════════════════════════════════════════════════

def fmt_eur(v) -> str:
    try:
        v = float(v)
        if not np.isfinite(v):
            return "—"
    except (TypeError, ValueError):
        return "—"
    sign = "−" if v < 0 else ""
    a = abs(v)
    if a >= 1_000_000:
        return f"{sign}{a / 1_000_000:.2f}".replace(".", ",") + " Mio. €"
    return f"{sign}{a:,.0f} €".replace(",", ".")


def fmt_pct(v, dec: int = 2) -> str:
    try:
        if not np.isfinite(float(v)):
            return "—"
        return f"{float(v):.{dec}f}".replace(".", ",") + " %"
    except (TypeError, ValueError):
        return "—"


def fmt_x(v) -> str:
    try:
        f = float(v)
        if not np.isfinite(f) or f > 99:
            return "> 99x"
        return f"{f:.1f}".replace(".", ",") + "x"
    except (TypeError, ValueError):
        return "—"


def fmt_yr(v) -> str:
    try:
        f = float(v)
        if not np.isfinite(f) or f > 99:
            return "n.v."
        return f"{f:.1f}".replace(".", ",") + " J."
    except (TypeError, ValueError):
        return "—"

# ══════════════════════════════════════════════════════════════════════
# 4. CALC ENGINE — alle Formeln geprüft (Audit v2.1)
# ══════════════════════════════════════════════════════════════════════

def get_afa_info(baujahr: int) -> dict:
    """§ 7 Abs. 4 EStG: AfA-Satz automatisch aus Baujahr ermitteln."""
    for r in AFA_REGELN:
        if baujahr >= r["von"]:
            return r
    return AFA_REGELN[-1]


def calc_ihr(kaufpreis: float, baujahr: int) -> float:
    """
    Instandhaltungsrücklage — kaufpreisbasierte Näherung, baualtersgestaffelt.
    Methodisch korrekt wäre €/m² × Wohnfläche (Peters-Formel).
    In Teuerlagen überschätzt diese Methode die IHR.
    """
    age = datetime.now().year - baujahr
    if age < 10:  return kaufpreis * 0.003
    if age < 25:  return kaufpreis * 0.006
    if age < 40:  return kaufpreis * 0.010
    return kaufpreis * 0.013


def calc_irr(initial: float, cashflows: list[float]) -> float:
    """Interner Zinsfuß via Newton-Raphson."""
    rate = 0.08
    for _ in range(300):
        f, df = initial, 0.0
        for t, c in enumerate(cashflows):
            p = (1.0 + rate) ** (t + 1)
            f  += c / p
            df -= (t + 1) * c / (p * (1.0 + rate))
        if abs(df) < 1e-12:
            break
        rn = rate - f / df
        if abs(rn - rate) < 1e-6:
            return rn * 100.0
        rate = min(max(rn, -0.999), 50.0)
    return rate * 100.0


def calc_npv(initial: float, cashflows: list[float], rate: float) -> float:
    """Kapitalwert (Net Present Value)."""
    return initial + sum(c / (1.0 + rate) ** (t + 1) for t, c in enumerate(cashflows))


def calc_all(p: dict) -> dict:
    """
    Master-Berechnung: alle KPIs aus einem Parameter-Dict.

    Korrekturen v2.1:
      • LTV = FK / Kaufpreis  (nicht / Gesamtinvestition)
      • MOIC inkl. kumulierter Cashflows
      • Break-Even inkl. Leerstand
      • Annuitätendarlehen-Modell (konstante Jahresrate)
      • Konsistente IHR-Basis: nettoMiete inkl. IHR

    NEU v3:
      • KNK aus Einzelkomponenten (GrESt + Notar + Makler)
      • AfA automatisch aus Baujahr (§ 7 EStG), mit manuellem Override
    """
    kp = p["kaufpreis"]

    # ── Transaktion ──────────────────────────────────────────────────
    knk_pct    = p["gest"] + p["notar"] + p["makler"]
    gest_abs   = kp * p["gest"]   / 100.0
    notar_abs  = kp * p["notar"]  / 100.0
    makler_abs = kp * p["makler"] / 100.0
    knk_abs    = kp * knk_pct     / 100.0
    gesamt     = kp + knk_abs

    # ── AfA automatisch aus Baujahr (NEU) ───────────────────────────
    afa_info  = get_afa_info(p["baujahr"])
    afa_basis = gesamt * p["gebaeude"] / 100.0
    if p["is_denkmal"]:
        san  = afa_basis * p["dk_san"] / 100.0
        afa  = (afa_basis - san) * 0.02 + san * p["dk_afa"] / 100.0
        afa_rate_used = None
    else:
        afa_rate_used = p["afa_override"] if p["afa_manual"] else afa_info["satz"]
        afa = afa_basis * afa_rate_used / 100.0

    # ── Erträge (FIX: nettoMiete inkl. IHR — konsistente Basis) ────
    bew_k    = p["jahresmiete"] * p["bew"]      / 100.0
    leer_abs = p["jahresmiete"] * p["leerstand"] / 100.0
    ihr_val  = calc_ihr(kp, p["baujahr"])
    noi      = p["jahresmiete"] - bew_k - ihr_val          # Cap-Rate-Basis
    netto    = p["jahresmiete"] - bew_k - leer_abs - ihr_val  # DSCR/CF-Basis

    # ── Renditen ─────────────────────────────────────────────────────
    brutto   = round(p["jahresmiete"] / kp * 100, 2) if kp else 0.0
    faktor   = round(kp / p["jahresmiete"], 1) if p["jahresmiete"] else 0.0
    netto_r  = round(netto / gesamt * 100, 2) if gesamt else 0.0
    cap_rate = round(noi / kp * 100, 2) if kp else 0.0

    # ── Finanzierung (FIX: LTV = FK/Kaufpreis, Annuitätendarlehen) ──
    ek_abs    = gesamt * p["ek"] / 100.0
    fk        = gesamt - ek_abs
    annuitaet = fk * (p["zins"] + p["tilgung"]) / 100.0   # konstante Jahresrate
    zins_j1   = fk * p["zins"] / 100.0                     # Zinslast Jahr 1
    kd        = annuitaet
    ltv       = round(fk / kp * 100, 1) if kp else 0.0    # FIX: FK/Kaufpreis
    dscr      = round(netto / kd, 2) if kd else 99.0

    # ── Steuer & Cashflow ────────────────────────────────────────────
    stl_erg    = netto - zins_j1 - afa
    steuerlast = stl_erg * p["steuer"] / 100.0
    cf_pre_m   = round((netto - kd) / 12.0, 2)
    cf_post_m  = round((netto - kd - steuerlast) / 12.0, 2)

    # ── Returns ──────────────────────────────────────────────────────
    roe = round((netto - zins_j1) / ek_abs * 100, 2) if ek_abs else 0.0
    roi = round(netto / gesamt * 100, 2) if gesamt else 0.0

    # ── Break-Even (FIX: inkl. Leerstand) ───────────────────────────
    kostensatz = (p["bew"] + p["leerstand"]) / 100.0
    be_m = round(kd / (1.0 - kostensatz) / 12.0, 2) if (kostensatz < 1.0 and kd) else 0.0
    amort = round(ek_abs / (cf_post_m * 12.0), 1) if cf_post_m * 12.0 > 0 else None

    # ── 10-Jahres-Projektion (FIX: Annuitätendarlehen-Modell) ────────
    proj: list[dict] = []
    debt, m_brutto, iw = fk, p["jahresmiete"], kp
    irr_cfs: list[float] = []
    cum_cf = 0.0

    for y in range(1, 11):
        mn     = m_brutto * (1.0 - p["bew"] / 100.0 - p["leerstand"] / 100.0) - ihr_val
        y_zins = debt * p["zins"] / 100.0
        y_tilg = min(debt, max(0.0, annuitaet - y_zins))
        y_cf   = mn - (y_zins + y_tilg)
        y_stl  = (mn - y_zins - afa) * p["steuer"] / 100.0
        y_cfp  = y_cf - y_stl
        cum_cf += y_cfp
        debt    = max(0.0, debt - y_tilg)
        iw     *= (1.0 + p["wert"] / 100.0)
        eq      = iw - debt
        irr_cfs.append(y_cfp + (max(0.0, eq - ek_abs) if y == 10 else 0.0))
        proj.append({
            "Jahr": f"J{y}",
            "CF pre/Mon.":  round(y_cf / 12.0),
            "CF post/Mon.": round(y_cfp / 12.0),
            "Equity":       round(eq),
            "Immobilienwert": round(iw),
            "Restschuld":   round(debt),
        })
        m_brutto *= (1.0 + p["miets"] / 100.0)

    try:
        irr_val = round(calc_irr(-ek_abs, irr_cfs), 2)
    except Exception:
        irr_val = 0.0

    npv_val  = round(calc_npv(-ek_abs, irr_cfs, p["diskont"] / 100.0))
    final_eq = proj[-1]["Equity"] if proj else ek_abs
    # FIX: MOIC = (kumulierte Post-Tax-CFs + Terminal Equity) / initiales EK
    moic = round((cum_cf + final_eq) / ek_abs, 2) if ek_abs else 0.0

    return {
        "knk_pct": knk_pct, "knk_abs": knk_abs,
        "gest_abs": gest_abs, "notar_abs": notar_abs, "makler_abs": makler_abs,
        "gesamt": gesamt,
        "bew_k": bew_k, "leer_abs": leer_abs, "ihr_val": ihr_val,
        "noi": noi, "netto": netto,
        "afa_info": afa_info, "afa": afa, "afa_rate_used": afa_rate_used,
        "brutto": brutto, "faktor": faktor, "netto_r": netto_r, "cap_rate": cap_rate,
        "ek_abs": ek_abs, "fk": fk, "annuitaet": annuitaet,
        "zins_j1": zins_j1, "kd": kd, "ltv": ltv, "dscr": dscr,
        "afa": afa, "steuerlast": steuerlast, "stl_erg": stl_erg,
        "cf_pre_m": cf_pre_m, "cf_post_m": cf_post_m,
        "roe": roe, "roi": roi, "be_m": be_m, "amort": amort,
        "irr_val": irr_val, "npv_val": npv_val, "moic": moic,
        "proj": proj,
    }

# ══════════════════════════════════════════════════════════════════════
# 5. AMPEL-LOGIK
# ══════════════════════════════════════════════════════════════════════

def get_ampel(key: str, val: float) -> str:
    rules = {
        "brutto":   lambda v: "g" if v >= 6   else ("y" if v >= 4   else "r"),
        "netto_r":  lambda v: "g" if v >= 4.5 else ("y" if v >= 3   else "r"),
        "cap_rate": lambda v: "g" if v >= 5   else ("y" if v >= 3.5 else "r"),
        "faktor":   lambda v: "g" if v <= 20  else ("y" if v <= 25  else "r"),
        "dscr":     lambda v: "g" if v >= 1.3 else ("y" if v >= 1.1 else "r"),
        "ltv":      lambda v: "g" if v <= 70  else ("y" if v <= 80  else "r"),
        "cf_pre_m": lambda v: "g" if v >= 0   else ("y" if v >= -150 else "r"),
        "cf_post_m":lambda v: "g" if v >= 0   else ("y" if v >= -150 else "r"),
        "roe":      lambda v: "g" if v >= 8   else ("y" if v >= 5   else "r"),
        "irr_val":  lambda v: "g" if v >= 8   else ("y" if v >= 5   else "r"),
        "npv_val":  lambda v: "g" if v >= 0   else "r",
        "moic":     lambda v: "g" if v >= 2   else ("y" if v >= 1.5 else "r"),
    }
    fn = rules.get(key)
    return fn(val) if fn else "y"

# ══════════════════════════════════════════════════════════════════════
# 6. HTML-KOMPONENTEN
# ══════════════════════════════════════════════════════════════════════

def kpi_card(label: str, value: str, sub: str | None = None,
             key: str | None = None, val: float | None = None,
             compact: bool = False) -> str:
    """Rendert eine KPI-Karte mit optionalem Ampel-System als HTML-String."""
    a_key = get_ampel(key, val) if (key and val is not None) else None
    a = AMPEL[a_key] if a_key else None
    sz = "kpi-sm" if compact else ""
    cls_card  = f"kpi kpi-{a_key}" if a_key else "kpi"
    bar       = f'<div class="kpi-bar" style="background:{a["c"]}"></div>' if a else ""
    badge     = (f'<div class="kpi-badge" style="color:{a["c"]};background:{a["bg"]}">'
                 f'{a["t"]}</div>') if a else ""
    lbl_col   = a["c"] if a else "#9ca3af"
    val_col   = a["c"] if a else NAVY
    sub_html  = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="{cls_card}">{bar}'
        f'<div class="kpi-lbl" style="color:{lbl_col}">{label}</div>'
        f'<div class="kpi-val {sz}" style="color:{val_col}">{value}</div>'
        f'{sub_html}{badge}</div>'
    )


def status_bar(items: list[tuple]) -> str:
    cells = "".join(
        f'<div class="sb-cell"><div class="sb-lbl">{l}</div>'
        f'<div class="sb-val">{v}</div></div>'
        for l, v in items
    )
    return f'<div class="sb-wrap">{cells}</div>'


def divider(label: str) -> str:
    return (
        f'<div class="div-wrap">'
        f'<div class="div-line"></div>'
        f'<div class="div-lbl">{label}</div>'
        f'<div class="div-line" style="background:linear-gradient(to left,#8b6914,transparent)"></div>'
        f'</div>'
    )

# ══════════════════════════════════════════════════════════════════════
# 7. CHARTS (Plotly)
# ══════════════════════════════════════════════════════════════════════

_LAYOUT = dict(
    plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
    margin=dict(t=10, b=30, l=45, r=8),
    font=dict(family="Plus Jakarta Sans, system-ui", size=11, color="#9ca3af"),
    hovermode="x unified",
    legend=dict(orientation="h", y=-0.28, x=0, font_size=10),
    xaxis=dict(showgrid=False, linecolor="#e8e4dc"),
    yaxis=dict(gridcolor="rgba(0,0,0,.04)", linecolor="#e8e4dc"),
)


def chart_cashflow(proj_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=proj_df["Jahr"], y=proj_df["CF pre/Mon."], name="CF pre-Tax/Mon.",
        fill="tozeroy", fillcolor="rgba(30,58,95,.06)",
        line=dict(color="#1e3a5f", width=2), mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=proj_df["Jahr"], y=proj_df["CF post/Mon."], name="CF post-Tax/Mon.",
        fill="tozeroy", fillcolor="rgba(139,105,20,.06)",
        line=dict(color=GOLD, width=2, dash="dash"), mode="lines",
    ))
    fig.update_layout(**_LAYOUT, height=230)
    fig.update_yaxes(ticksuffix="€", zeroline=True, zerolinecolor="rgba(0,0,0,.1)")
    return fig


def chart_equity(proj_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for col, color, dash, width in [
        ("Equity",          "#065f46", "solid", 2.5),
        ("Immobilienwert",  "#1e3a5f", "dash",  2.0),
        ("Restschuld",      "#991b1b", "dot",   1.5),
    ]:
        fig.add_trace(go.Scatter(
            x=proj_df["Jahr"], y=proj_df[col], name=col,
            line=dict(color=color, width=width, dash=dash), mode="lines",
        ))
    fig.update_layout(**_LAYOUT, height=230)
    return fig


def chart_donut(kaufpreis, gest_abs, notar_abs, makler_abs) -> go.Figure:
    data = [
        ("Kaufpreis",        kaufpreis,  "#1e3a5f"),
        ("Grunderwerbsteuer", gest_abs,   GOLD),
        ("Notar/Grundbuch",   notar_abs,  "#6366f1"),
        ("Makler",            makler_abs, "#0f766e"),
    ]
    data = [(l, v, c) for l, v, c in data if v > 0]
    fig = go.Figure(go.Pie(
        labels=[d[0] for d in data], values=[d[1] for d in data],
        hole=0.65, marker=dict(colors=[d[2] for d in data],
                               line=dict(color="#fff", width=2)),
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

    # CSS + Header
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="yb-header">'
        '<div style="width:30px;height:30px;background:linear-gradient(135deg,#8b6914,#c9a53c);'
        'border-radius:7px;display:flex;align-items:center;justify-content:center;'
        'color:#fff;font-size:14px">◆</div>'
        '<div><div class="yb-logo">YieldBase</div>'
        '<div class="yb-sub">Analytics v3 · Python</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── SIDEBAR ───────────────────────────────────────────────────────
    with st.sidebar:
        mode = st.radio("Modus", ["Einsteiger", "Experte"],
                        horizontal=True, label_visibility="collapsed")
        is_exp = (mode == "Experte")
        st.markdown("---")

        # ── Standort & KNK ────────────────────────────────────────────
        st.markdown("#### 🏠 Standort & Kaufnebenkosten")
        bundesland = st.selectbox(
            "Bundesland",
            list(BUNDESLAND_GEST.keys()),
            index=0,
            help="Setzt die Grunderwerbsteuer automatisch. " +
                 " | ".join(f"{n}: {r:.1f}%" for n, r in BUNDESLAND_GEST.items()),
        )
        gest = BUNDESLAND_GEST[bundesland]
        st.markdown(
            f'<div class="info-box">Grunderwerbsteuer <strong>{bundesland}</strong>: '
            f'<strong style="color:#8b6914">{gest:.1f}%</strong> — automatisch gesetzt</div>',
            unsafe_allow_html=True,
        )
        kaufpreis = st.number_input(
            "Kaufpreis (€)", min_value=0, value=350_000, step=5_000,
            help="Brutto-Verkaufspreis ohne Nebenkosten.",
        )
        notar = st.slider(
            "Notar + Grundbuch (%)", 0.5, 2.5, 2.0, 0.1,
            help="Notargebühren ca. 1–1,5% + Grundbucheintragung ca. 0,5%",
        )
        makler = st.slider(
            "Maklercourtage (%)", 0.0, 3.57, 3.57, 0.01,
            help="Käuferanteil max. 3,57% inkl. MwSt. (§ 656c BGB)",
        )
        st.markdown("---")

        # ── Objekt & Ertrag ───────────────────────────────────────────
        st.markdown("#### 📋 Objekt & Mietertrag")
        jahresmiete = st.number_input(
            "Jahres-Kaltmiete (€)", min_value=0, value=18_000, step=500,
            help="Aktuelle Nettokaltmiete p.a.",
        )
        baujahr = st.number_input(
            "Baujahr", min_value=1800, max_value=datetime.now().year,
            value=1985, step=1,
            help="Bestimmt den AfA-Satz (§ 7 EStG) und die IHR automatisch.",
        )
        afa_info = get_afa_info(baujahr)
        st.success(f"**AfA:** {afa_info['label']} · {afa_info['basis']}")

        bew = st.slider(
            "Bewirtschaftungskosten (%)", 5, 30, 15, 1,
            help="Verwaltung + nicht-umlegbare BK + Mietausfallwagnis. Ohne IHR!",
        )
        leerstand = st.slider("Leerstandsrisiko (%)", 0.0, 15.0, 3.0, 0.5)
        st.markdown("---")

        # ── Finanzierung ──────────────────────────────────────────────
        st.markdown("#### 🏦 Finanzierung")
        ek      = st.slider("Eigenkapital-Quote (%)", 5, 100, 25, 1)
        zins    = st.slider("Sollzins p.a. (%)", 0.5, 8.0, 3.8, 0.1)
        tilgung = st.slider(
            "Anfangstilgung p.a. (%)", 0.5, 6.0, 2.0, 0.1,
            help="Annuität = FK × (Zins + Tilgung) / 100 = konstant (Annuitätendarlehen)",
        )

        # ── Experte: Steuer & Projektion ──────────────────────────────
        if is_exp:
            st.markdown("---")
            st.markdown("#### ⚙️ Steuer, AfA & Projektion")
            steuer    = st.slider("Grenzsteuersatz (%)", 0, 45, 42, 1)
            gebaeude  = st.slider(
                "Gebäudeanteil (%)", 40, 100, 80, 1,
                help="Anteil am Kaufpreis auf das Gebäude (Boden nicht abschreibbar)",
            )
            is_denkmal  = st.checkbox("Denkmalschutz-AfA aktiv (§ 7i EStG)")
            afa_manual  = st.checkbox("AfA manuell überschreiben") if not is_denkmal else False
            dk_san = dk_afa = afa_override = 0.0
            if is_denkmal:
                dk_san  = st.slider("Sanierungsanteil (%)", 10, 90, 60, 1)
                dk_afa  = st.slider("Denkmal-AfA-Satz (%)", 3.0, 12.0, 9.0, 0.5)
            elif afa_manual:
                afa_override = st.number_input(
                    "AfA-Satz manuell (%)", 0.5, 10.0,
                    float(afa_info["satz"]), 0.5,
                )

            st.markdown("**10-J.-Projektion**")
            wert    = st.slider("Wertzuwachs p.a. (%)", -2.0, 6.0, 2.0, 0.5)
            miets   = st.slider("Mietsteigerung p.a. (%)", 0.0, 5.0, 1.5, 0.25)
            diskont = st.slider(
                "Diskontierungssatz NPV (%)", 1.0, 12.0, 5.0, 0.5,
                help="Risikoadjustierter Kapitalkostensatz für NPV-Berechnung",
            )
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
        dk_san=float(dk_san), dk_afa=float(dk_afa),
        baujahr=int(baujahr), afa_manual=afa_manual,
        afa_override=float(afa_override),
        leerstand=float(leerstand), wert=float(wert),
        miets=float(miets), diskont=float(diskont),
    )
    res     = calc_all(params)
    proj_df = pd.DataFrame(res["proj"])
    ai      = res["afa_info"]
    knk_pct = res["knk_pct"]

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
    # TAB 1 — Eingabe & KPIs
    # ══════════════════════════════════════════════════════════════════
    with t1:
        col_l, col_r = st.columns([1, 1.3], gap="large")

        with col_l:
            # Summary Banner
            st.markdown(
                f'<div class="sum-wrap">'
                f'<div style="font-size:11px;color:#9ca3af;text-transform:uppercase;'
                f'letter-spacing:.06em;margin-bottom:3px">Gesamtinvestition '
                f'(inkl. {knk_pct:.2f}% KNK)</div>'
                f'<div class="sum-total">{fmt_eur(res["gesamt"])}</div>'
                f'<div class="sum-grid">'
                f'<div><div class="sum-lbl">Eigenkapital</div>'
                f'<div class="sum-val">{fmt_eur(res["ek_abs"])}</div></div>'
                f'<div><div class="sum-lbl">Fremdkapital</div>'
                f'<div class="sum-val">{fmt_eur(res["fk"])}</div></div>'
                f'<div><div class="sum-lbl">KNK gesamt</div>'
                f'<div class="sum-val">{fmt_eur(res["knk_abs"])}</div></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            # KNK-Tabelle
            rows = [
                (f"Grunderwerbsteuer ({bundesland})", f"{gest:.1f}%", fmt_eur(res["gest_abs"])),
                ("Notar + Grundbuch",                  f"{notar:.1f}%", fmt_eur(res["notar_abs"])),
                ("Maklercourtage",                     f"{makler:.2f}%", fmt_eur(res["makler_abs"])),
            ]
            row_html = "".join(
                f'<div class="knk-row">'
                f'<span class="knk-lbl">{l}</span>'
                f'<span class="knk-vals"><span class="mono">{p}</span>'
                f'<span class="mono">{v}</span></span></div>'
                for l, p, v in rows
            )
            st.markdown(
                f'<div class="knk"><div class="knk-head">KNK-Aufschlüsselung</div>'
                f'{row_html}'
                f'<div class="knk-row knk-total"><span>KNK gesamt</span>'
                f'<span class="knk-vals"><span>{knk_pct:.2f}%</span>'
                f'<span>{fmt_eur(res["knk_abs"])}</span></span></div></div>',
                unsafe_allow_html=True,
            )

            # AfA-Badge
            afa_used = (f'{res["afa_rate_used"]}% · {ai["basis"]}'
                        if res.get("afa_rate_used") is not None
                        else "Denkmal § 7i EStG")
            st.markdown(
                f'<div class="afa-badge"><span class="afa-icon">§</span><div>'
                f'<div class="afa-title">{ai["label"]}</div>'
                f'<div class="afa-basis">{ai["basis"]}</div>'
                f'<div class="afa-note">{ai["note"]}</div>'
                f'<div style="margin-top:6px;font-size:10px;color:#8b6914">'
                f'AfA p.a.: <strong>{fmt_eur(res["afa"])}</strong> · '
                f'{afa_used}</div></div></div>',
                unsafe_allow_html=True,
            )

            # IHR + Annuität Info
            st.markdown(
                f'<div class="info-box" style="margin-top:8px">'
                f'IHR (auto): <strong style="color:#8b6914">{fmt_eur(res["ihr_val"])}/J</strong> · '
                f'{res["ihr_val"] / kaufpreis * 100:.2f}% des KP &nbsp;|&nbsp; '
                f'Annuität: <strong style="color:#8b6914">'
                f'{fmt_eur(res["annuitaet"] / 12)}/Mon</strong></div>',
                unsafe_allow_html=True,
            )

        with col_r:
            if is_exp:
                kpi_data = [
                    ("Bruttorendite",    fmt_pct(res["brutto"]),  None,                   "brutto",    res["brutto"]),
                    ("Netto-Rendite",    fmt_pct(res["netto_r"]), "inkl. IHR+Leerstand",  "netto_r",   res["netto_r"]),
                    ("Cap Rate",         fmt_pct(res["cap_rate"]),"NOI/Kaufpreis",         "cap_rate",  res["cap_rate"]),
                    ("DSCR",             f"{res['dscr']:.2f}".replace(".",","), "Schuldendeckung", "dscr", res["dscr"]),
                    ("LTV",              fmt_pct(res["ltv"], 1),  "FK/Kaufpreis ✓",        "ltv",       res["ltv"]),
                    ("Faktor",           fmt_x(res["faktor"]),    None,                   "faktor",    res["faktor"]),
                    ("CF pre-Tax/Mon.",  fmt_eur(res["cf_pre_m"]),None,                   "cf_pre_m",  res["cf_pre_m"]),
                    ("CF post-Tax/Mon.", fmt_eur(res["cf_post_m"]),None,                  "cf_post_m", res["cf_post_m"]),
                    ("ROE",              fmt_pct(res["roe"]),     None,                   "roe",       res["roe"]),
                    ("IRR (10J.)",       fmt_pct(res["irr_val"]), None,                   "irr_val",   res["irr_val"]),
                    ("NPV",              fmt_eur(res["npv_val"]),  f"@ {diskont}% Diskont","npv_val",  res["npv_val"]),
                    ("MOIC",             fmt_x(res["moic"]),      "CF+Equity/EK ✓",       "moic",      res["moic"]),
                ]
                for row_start in range(0, len(kpi_data), 3):
                    cols = st.columns(3)
                    for i, (lbl, val, sub, k, av) in enumerate(kpi_data[row_start:row_start + 3]):
                        with cols[i]:
                            st.markdown(kpi_card(lbl, val, sub, k, av, compact=True),
                                        unsafe_allow_html=True)

                st.markdown("&nbsp;", unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                with c1: st.markdown(kpi_card("Break-Even-Miete", fmt_eur(res["be_m"]) + "/Mon", "inkl. Leerstand ✓", compact=True), unsafe_allow_html=True)
                with c2: st.markdown(kpi_card("EK-Amortisation", fmt_yr(res["amort"]) if res["amort"] else "Negativ", "Post-Tax-CF", compact=True), unsafe_allow_html=True)
                with c3: st.markdown(kpi_card("AfA p.a.", fmt_eur(res["afa"]), "auto ✓", compact=True), unsafe_allow_html=True)
            else:
                c1, c2 = st.columns(2)
                basic = [
                    ("Bruttorendite",   fmt_pct(res["brutto"]),   "Kaufpreis-Basis",            "brutto",  res["brutto"]),
                    ("Netto-Rendite",   fmt_pct(res["netto_r"]),  "nach Bew.+Leerstand+IHR",   "netto_r", res["netto_r"]),
                    ("DSCR",            f"{res['dscr']:.2f}".replace(".",","), "Schuldendeckung","dscr",   res["dscr"]),
                    ("Cashflow / Mon.", fmt_eur(res["cf_pre_m"]),  "Vor Steuer",                 "cf_pre_m",res["cf_pre_m"]),
                ]
                for i, (lbl, val, sub, k, av) in enumerate(basic):
                    with (c1 if i % 2 == 0 else c2):
                        st.markdown(kpi_card(lbl, val, sub, k, av), unsafe_allow_html=True)

            # Kostenstruktur Donut
            st.markdown("**Kostenstruktur**")
            dc1, dc2 = st.columns([1, 1.2])
            with dc1:
                st.plotly_chart(
                    chart_donut(kaufpreis, res["gest_abs"], res["notar_abs"], res["makler_abs"]),
                    use_container_width=True, config={"displayModeBar": False},
                )
            with dc2:
                for name, val in [
                    ("Kaufpreis",        kaufpreis),
                    ("Grunderwerbsteuer", res["gest_abs"]),
                    ("Notar/Grundbuch",   res["notar_abs"]),
                    ("Makler",            res["makler_abs"]),
                ]:
                    if val > 0:
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;'
                            f'font-size:11px;padding:3px 0;border-bottom:1px solid #f0ece6">'
                            f'<span style="color:#6b7280">{name}</span>'
                            f'<span style="font-family:monospace;color:#1a2332">{fmt_eur(val)}</span></div>',
                            unsafe_allow_html=True,
                        )

    # ══════════════════════════════════════════════════════════════════
    # TAB 2 — Dashboard
    # ══════════════════════════════════════════════════════════════════
    with t2:
        sections = [
            ("Rendite & Ertrag", [
                ("Bruttorendite",    fmt_pct(res["brutto"]),    "Jahresmiete/KP",             "brutto",   res["brutto"]),
                ("Netto-Rendite",    fmt_pct(res["netto_r"]),   "nach Bew.+Leerstand+IHR",    "netto_r",  res["netto_r"]),
                ("Cap Rate",         fmt_pct(res["cap_rate"]),  "NOI/Kaufpreis",               "cap_rate", res["cap_rate"]),
                ("Kaufpreisfaktor",  fmt_x(res["faktor"]),      None,                          "faktor",   res["faktor"]),
                ("Jahresmiete",      fmt_eur(jahresmiete),       "Brutto",                      None,       None),
                ("Nettomietertrag",  fmt_eur(res["netto"]),      "=Miete−Bew.−Leerstand−IHR",  None,       None),
            ]),
            ("Cashflow & Liquidität", [
                ("CF/Mon. (pre)",    fmt_eur(res["cf_pre_m"]),  "Vor Steuer",                  "cf_pre_m", res["cf_pre_m"]),
                ("CF/Mon. (post)",   fmt_eur(res["cf_post_m"]), "Nach Steuern",                "cf_post_m",res["cf_post_m"]),
                ("CF/Jahr",          fmt_eur(res["cf_pre_m"]*12),"Annualisiert",               None,       None),
                ("Break-Even-Miete", fmt_eur(res["be_m"])+"/Mon","inkl. Leerstand ✓",          None,       None),
                ("AfA p.a.",         fmt_eur(res["afa"]),        ai["basis"],                   None,       None),
                ("Steuerlast p.a.",  fmt_eur(res["steuerlast"]),  f"{steuer}% Steuersatz",       None,       None),
            ]),
            ("Finanzierung & Verschuldung", [
                ("DSCR",             f"{res['dscr']:.2f}".replace(".",","), "Schuldendeckung", "dscr",     res["dscr"]),
                ("LTV (FK/KP)",      fmt_pct(res["ltv"], 1),    "Banküblich ✓",                "ltv",      res["ltv"]),
                ("Eigenkapital",     fmt_eur(res["ek_abs"]),     f"{ek}%",                      None,       None),
                ("Fremdkapital",     fmt_eur(res["fk"]),         None,                          None,       None),
                ("Zinslast J1",      fmt_eur(res["zins_j1"]),    f"{zins}%",                    None,       None),
                ("Annuität p.a.",    fmt_eur(res["annuitaet"]),  "konstant ✓",                  None,       None),
            ]),
            ("Investment-Returns (10 Jahre)", [
                ("ROE",              fmt_pct(res["roe"]),        "Leveraged Return",             "roe",      res["roe"]),
                ("ROI",              fmt_pct(res["roi"]),        "Gesamtkapital",                None,       None),
                ("IRR (10J.)",       fmt_pct(res["irr_val"]),    "inkl. Wertzuwachs",           "irr_val",  res["irr_val"]),
                ("NPV",              fmt_eur(res["npv_val"]),     f"@ {diskont}% Diskont",       "npv_val",  res["npv_val"]),
                ("MOIC",             fmt_x(res["moic"]),         "CF+Equity/EK ✓",              "moic",     res["moic"]),
                ("EK-Amortisation",  fmt_yr(res["amort"]) if res["amort"] else "Negativ", "Post-Tax-CF", None, None),
            ]),
        ]
        for sec_title, cards in sections:
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
            st.markdown(f"**📈 Cashflow-Projektion (10 Jahre)**")
            st.caption(f"Annuität {fmt_eur(res['annuitaet']/12)}/Mon konstant")
            st.plotly_chart(chart_cashflow(proj_df), use_container_width=True,
                            config={"displayModeBar": False})
        with cb:
            st.markdown("**📊 Vermögensaufbau — Equity Buildup**")
            st.caption("Eigenkapital = Immobilienwert − Restschuld")
            st.plotly_chart(chart_equity(proj_df), use_container_width=True,
                            config={"displayModeBar": False})

        st.markdown("---")
        st.markdown("**⚖️ Szenario-Vergleich**")
        st.caption("Opt.: +10% Miete, −0,5% Zins, +1,5% Wert · Pess.: −10% Miete, +0,8% Zins, +3% Leerstand")

        p_opt  = {**params, "jahresmiete": jahresmiete*1.1, "zins": max(0.5, zins-0.5),
                  "leerstand": max(0.0, leerstand-1.0), "wert": wert+1.5}
        p_pess = {**params, "jahresmiete": jahresmiete*0.9, "zins": zins+0.8,
                  "leerstand": leerstand+3.0, "wert": max(0.0, wert-1.5)}
        r_opt, r_pess = calc_all(p_opt), calc_all(p_pess)

        sc_rows = [
            ("Brutto-Rendite",   "brutto",   fmt_pct),
            ("Netto-Rendite",    "netto_r",  fmt_pct),
            ("DSCR",             "dscr",     lambda v: f"{v:.2f}".replace(".", ",")),
            ("CF/Monat (pre)",   "cf_pre_m", fmt_eur),
            ("LTV",              "ltv",      lambda v: fmt_pct(v, 1)),
            ("ROE",              "roe",      fmt_pct),
            ("IRR (10J.)",       "irr_val",  fmt_pct),
            ("NPV",              "npv_val",  fmt_eur),
            ("MOIC",             "moic",     fmt_x),
        ]

        def sc_td(key, v, fmt_fn):
            a = AMPEL[get_ampel(key, v)]
            return (f'<td style="text-align:right;font-family:monospace;'
                    f'color:{a["c"]}">{fmt_fn(v)}</td>')

        rows_html = "".join(
            f'<tr style="background:{"#faf8f5" if i%2 else "#fff"}">'
            f'<td style="color:#6b7280">{lbl}</td>'
            f'{sc_td(k, r_opt[k], fn)}'
            f'{sc_td(k, res[k],   fn)}'
            f'{sc_td(k, r_pess[k],fn)}</tr>'
            for i, (lbl, k, fn) in enumerate(sc_rows)
        )
        st.markdown(
            f'<table class="sc-table"><thead><tr>'
            f'<th style="text-align:left;color:#9ca3af">KPI</th>'
            f'<th style="text-align:right;color:#065f46">Optimistisch</th>'
            f'<th style="text-align:right;color:#8b6914">Realistisch</th>'
            f'<th style="text-align:right;color:#991b1b">Pessimistisch</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table>',
            unsafe_allow_html=True,
        )

    # ══════════════════════════════════════════════════════════════════
    # TAB 4 — Bericht
    # ══════════════════════════════════════════════════════════════════
    with t4:
        col_rep, _ = st.columns([2.2, 1])
        with col_rep:

            # Ampel-Tags
            tags = [
                ("Rendite", "netto_r",  res["netto_r"]),
                ("CF",      "cf_pre_m", res["cf_pre_m"]),
                ("DSCR",    "dscr",     res["dscr"]),
                ("LTV",     "ltv",      res["ltv"]),
                ("ROE",     "roe",      res["roe"]),
                ("IRR",     "irr_val",  res["irr_val"]),
                ("NPV",     "npv_val",  res["npv_val"]),
                ("MOIC",    "moic",     res["moic"]),
            ]
            tags_html = " ".join(
                f'<span style="font-size:10px;font-weight:700;padding:3px 10px;'
                f'border-radius:20px;background:{AMPEL[get_ampel(k,v)]["bg"]};'
                f'color:{AMPEL[get_ampel(k,v)]["c"]};'
                f'border:1px solid {AMPEL[get_ampel(k,v)]["br"]}">{l}</span>'
                for l, k, v in tags
            )
            sum_items = "".join(
                f'<div style="background:#fff;border-radius:8px;padding:12px 14px;'
                f'border:1px solid rgba(139,105,20,.2);flex:1">'
                f'<div style="font-size:9px;color:#9ca3af;text-transform:uppercase;'
                f'letter-spacing:.06em;margin-bottom:3px">{l}</div>'
                f'<div style="font-family:\'Cormorant Garamond\',Georgia,serif;font-size:20px;'
                f'font-style:italic;font-weight:700;color:#8b6914">{v}</div></div>'
                for l, v in [
                    ("Gesamtinvestition", fmt_eur(res["gesamt"])),
                    ("Jahresmiete brutto", fmt_eur(jahresmiete)),
                    ("Eigenkapital",       fmt_eur(res["ek_abs"])),
                ]
            )
            st.markdown(
                f'<div class="sum-wrap" style="border-radius:14px;padding:22px 26px">'
                f'<div style="font-family:\'Cormorant Garamond\',Georgia,serif;font-size:24px;'
                f'font-style:italic;font-weight:700;color:#1a2332;margin-bottom:3px">'
                f'Investment Summary</div>'
                f'<div style="font-size:10px;color:#9ca3af;margin-bottom:16px">'
                f'YieldBase v3 · {datetime.now().strftime("%d.%m.%Y")} · {bundesland}</div>'
                f'<div style="display:flex;gap:10px;margin-bottom:14px">{sum_items}</div>'
                f'<div style="display:flex;flex-wrap:wrap;gap:5px">{tags_html}</div></div>',
                unsafe_allow_html=True,
            )

            # Vollständige KPI-Tabelle
            st.markdown("**Vollständige KPI-Tabelle**")
            kpi_sections = [
                ("Transaktion", [
                    ("Kaufpreis",                     fmt_eur(kaufpreis),        ""),
                    (f"Grunderwerbsteuer ({bundesland})", fmt_eur(res["gest_abs"]),  f"{gest:.1f}%"),
                    ("Notar + Grundbuch",              fmt_eur(res["notar_abs"]), f"{notar:.1f}%"),
                    ("Maklercourtage",                 fmt_eur(res["makler_abs"]),f"{makler:.2f}%"),
                    (f"KNK gesamt ({knk_pct:.2f}%)",   fmt_eur(res["knk_abs"]),   "Summe"),
                    ("Gesamtinvestition",              fmt_eur(res["gesamt"]),    ""),
                ]),
                ("Ertrag & Rendite", [
                    ("Jahresmiete (Brutto)",           fmt_eur(jahresmiete),       ""),
                    (f"Bewirtschaftungskosten ({bew}%)", fmt_eur(res["bew_k"]),   ""),
                    (f"Leerstandsverlust ({leerstand}%)", fmt_eur(res["leer_abs"]),""),
                    ("IHR (auto, baualtersgestaffelt)", fmt_eur(res["ihr_val"]),   ""),
                    ("Nettomietertrag",                fmt_eur(res["netto"]),      ""),
                    ("NOI (Cap-Rate-Basis)",           fmt_eur(res["noi"]),        "ohne Leerstand"),
                    ("Bruttorendite",                  fmt_pct(res["brutto"]),     ""),
                    ("Netto-Rendite (adj.)",           fmt_pct(res["netto_r"]),    ""),
                    ("Cap Rate",                      fmt_pct(res["cap_rate"]),    ""),
                    ("Kaufpreisfaktor",               fmt_x(res["faktor"]),        ""),
                ]),
                ("Finanzierung & AfA", [
                    ("Eigenkapital",                   fmt_eur(res["ek_abs"]),     f"{ek}%"),
                    ("Fremdkapital",                   fmt_eur(res["fk"]),         ""),
                    ("LTV (FK/Kaufpreis) ✓",           fmt_pct(res["ltv"], 1),     ""),
                    ("Annuität p.a. ✓",                fmt_eur(res["annuitaet"]),  "konstant"),
                    ("Zinslast J1",                    fmt_eur(res["zins_j1"]),    ""),
                    ("DSCR",                           f"{res['dscr']:.2f}".replace(".",","), ""),
                    (f"AfA ({ai['label']})",           fmt_eur(res["afa"]),        ai["basis"]),
                    ("Steuerlast p.a.",                fmt_eur(res["steuerlast"]), f"{steuer}%"),
                    ("CF/Monat pre-Tax",               fmt_eur(res["cf_pre_m"]),   ""),
                    ("CF/Monat post-Tax",              fmt_eur(res["cf_post_m"]),  ""),
                    ("Break-Even-Miete ✓",             fmt_eur(res["be_m"])+"/Mon","inkl. Leerstand"),
                ]),
                ("Investment-Returns", [
                    ("ROE (Eigenkapitalrendite)",      fmt_pct(res["roe"]),        ""),
                    ("ROI (Gesamtkapital)",            fmt_pct(res["roi"]),        ""),
                    ("IRR (10 Jahre)",                 fmt_pct(res["irr_val"]),    "inkl. Wertzuwachs"),
                    (f"NPV ({diskont}% Diskont)",       fmt_eur(res["npv_val"]),   ""),
                    ("MOIC (CFs+Equity/EK) ✓",        fmt_x(res["moic"]),         ""),
                    ("EK-Amortisation",                fmt_yr(res["amort"]) if res["amort"] else "Negativ", ""),
                ]),
            ]
            for sec_title, rows in kpi_sections:
                st.markdown(
                    f'<div style="font-size:9px;text-transform:uppercase;letter-spacing:.1em;'
                    f'color:#8b6914;font-weight:700;padding:6px 0;'
                    f'border-bottom:2px solid rgba(139,105,20,.2);margin:16px 0 8px">'
                    f'{sec_title}</div>',
                    unsafe_allow_html=True,
                )
                for i, (lbl, val, note) in enumerate(rows):
                    bg = "#faf8f5" if i % 2 else "#ffffff"
                    note_html = (f'<span style="font-size:10px;color:#9ca3af;margin-right:10px">'
                                 f'{note}</span>') if note else ""
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;align-items:center;'
                        f'padding:7px 8px;background:{bg};border-radius:4px;'
                        f'border-bottom:1px solid #f0ece6">'
                        f'<span style="font-size:11px;color:#6b7280">{lbl}</span>'
                        f'<span>{note_html}'
                        f'<span style="font-family:monospace;font-size:12px;color:#1a2332;'
                        f'font-weight:600">{val}</span></span></div>',
                        unsafe_allow_html=True,
                    )

            st.markdown(
                f'<div class="disclaimer">Rechtlicher Hinweis: Modellsimulation ohne Gewähr. '
                f'Keine Anlageberatung. AfA: {ai["label"]} — {ai["basis"]}. '
                f'GrESt {bundesland}: {gest:.1f}%. '
                f'Alle Formeln geprüft (Audit v2.1). © 2025 YieldBase Analytics.</div>',
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
