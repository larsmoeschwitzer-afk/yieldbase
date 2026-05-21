import streamlit as st
import pandas as pd
import altair as alt
import math

st.set_page_config(page_title="YieldBase v2 | Analytics", layout="wide", initial_sidebar_state="collapsed")

# ─────────────────────────────────────────────────────────────────────────────
# 1. DESIGN TOKENS & CSS (React SaaS Dark Mode Portierung)
# ─────────────────────────────────────────────────────────────────────────────
T = {
    "bg": "#080d1a", "surface": "#0d1526", "surface2": "#111f35", "surface3": "#162440",
    "border": "#1e3054", "gold": "#c9a84c", "goldFaint": "rgba(201,168,76,0.12)",
    "green": "#10b981", "yellow": "#f59e0b", "red": "#ef4444", "blue": "#3b82f6", "cyan": "#06b6d4",
    "text": "#e8eef7", "textMuted": "#8ba3c7", "textDim": "#3d5a87"
}

st.markdown(f"""
    <style>
    /* Dark Theme Base */
    .stApp {{ background-color: {T["bg"]}; color: {T["text"]}; font-family: 'Inter', sans-serif; }}
    
    /* Layout & Cards */
    .saas-card {{ background-color: {T["surface"]}; border: 1px solid {T["border"]}; border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
    .saas-card-header {{ font-family: 'Georgia', serif; font-size: 1.1rem; color: {T["text"]}; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }}
    .saas-card-header span {{ color: {T["gold"]}; }}
    
    /* KPI Metric Cards (Custom) */
    .kpi-box {{ background: {T["surface2"]}; border: 1px solid {T["border"]}; border-radius: 10px; padding: 14px 16px; position: relative; overflow: hidden; }}
    .kpi-title {{ font-size: 0.7rem; color: {T["textMuted"]}; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }}
    .kpi-value {{ font-family: 'Courier New', monospace; font-size: 1.25rem; font-weight: 700; color: {T["text"]}; }}
    .kpi-sub {{ font-size: 0.7rem; color: {T["textDim"]}; margin-top: 4px; }}
    .ampel-badge {{ position: absolute; top: 10px; right: 10px; font-size: 0.6rem; font-weight: 600; padding: 2px 6px; border-radius: 4px; }}
    
    /* Streamlit Native Overrides */
    div[data-testid="stTabs"] button {{ color: {T["textMuted"]}; font-size: 0.9rem; padding-top: 1rem; padding-bottom: 1rem; }}
    div[data-testid="stTabs"] button[aria-selected="true"] {{ color: {T["text"]}; border-bottom-color: {T["gold"]}; }}
    .stSlider > div > div > div > div {{ background-color: {T["gold"]} !important; }}
    
    /* Benchmarks & Helpers */
    .benchmark-box {{ background: {T["goldFaint"]}; border: 1px solid rgba(201,168,76,0.25); border-radius: 8px; padding: 10px 14px; margin-top: 10px; font-size: 0.8rem; color: {T["textMuted"]}; }}
    hr {{ border-color: {T["border"]}; }}
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 2. CALC ENGINE (exakter Port der JS Pure Functions)
# ─────────────────────────────────────────────────────────────────────────────
def fmt_eur(v):
    if not isinstance(v, (int, float)) or math.isnan(v): return "—"
    if abs(v) >= 1_000_000: return f"{(v / 1_000_000):.2f} Mio. €".replace(".", ",")
    return f"{v:,.0f} €".replace(",", ".")

def fmt_pct(v):
    if not isinstance(v, (int, float)) or math.isnan(v): return "—"
    return f"{v:.2f} %".replace(".", ",")

def fmt_x(v):
    if not isinstance(v, (int, float)) or math.isnan(v) or v > 99: return "> 99x"
    return f"{v:.1f}x".replace(".", ",")

def calc_ihr(kaufpreis, baujahr):
    age = 2025 - baujahr
    if age < 10: return kaufpreis * 0.003
    if age < 25: return kaufpreis * 0.006
    if age < 40: return kaufpreis * 0.010
    return kaufpreis * 0.013

def calc_irr(initial_investment, cashflows):
    rate = 0.08
    for _ in range(300):
        f = initial_investment
        df = 0
        for t, c in enumerate(cashflows):
            p = (1 + rate) ** (t + 1)
            f += c / p
            df -= (t + 1) * c / (p * (1 + rate))
        if abs(df) < 1e-12: break
        rn = rate - (f / df) if df != 0 else rate
        if abs(rn - rate) < 1e-6: return rn * 100
        rate = max(min(rn, 50.0), -0.999)
    return rate * 100

def calc_npv(initial_investment, cashflows, rate):
    npv = initial_investment
    for t, c in enumerate(cashflows):
        npv += c / ((1 + rate) ** (t + 1))
    return npv

def calc_all(inp):
    # Transaktion
    grunderwerbsteuer = inp['kaufpreis'] * 0.035
    notar = inp['kaufpreis'] * 0.020
    makler = max(0, inp['kaufpreis'] * ((inp['knk'] - 5.5) / 100))
    knk_abs = inp['kaufpreis'] * (inp['knk'] / 100)
    gesamt = inp['kaufpreis'] + knk_abs

    # Erträge
    bew_kosten = inp['jahresmiete'] * (inp['bew'] / 100)
    leerstand_abs = inp['jahresmiete'] * (inp['leerstand'] / 100)
    ihr = calc_ihr(inp['kaufpreis'], inp['baujahr'])
    noi = inp['jahresmiete'] - bew_kosten - ihr
    netto_miete = inp['jahresmiete'] - bew_kosten - leerstand_abs - ihr

    # Renditen
    brutto = (inp['jahresmiete'] / inp['kaufpreis'] * 100) if inp['kaufpreis'] > 0 else 0
    faktor = (inp['kaufpreis'] / inp['jahresmiete']) if inp['jahresmiete'] > 0 else 0
    netto_rend = (netto_miete / gesamt * 100) if gesamt > 0 else 0
    cap_rate = (noi / inp['kaufpreis'] * 100) if inp['kaufpreis'] > 0 else 0

    # Finanzierung
    ek_abs = gesamt * (inp['ek'] / 100)
    fk = gesamt - ek_abs
    zinslast = fk * (inp['zins'] / 100)
    tilg_abs = fk * (inp['tilgung'] / 100)
    kd = zinslast + tilg_abs
    ltv = (fk / inp['kaufpreis'] * 100) if inp['kaufpreis'] > 0 else 0
    dscr = (netto_miete / kd) if kd > 0 else 99

    # Steuer & AfA
    afa_basis = gesamt * (inp['gebaeude'] / 100)
    if inp['isDenkmal']:
        san = afa_basis * (inp['dkSan'] / 100)
        afa = (afa_basis - san) * 0.02 + san * (inp['dkAfa'] / 100)
    else:
        afa = afa_basis * (inp['regAfa'] / 100)

    stl_ergebnis = netto_miete - zinslast - afa
    steuerlast = stl_ergebnis * (inp['steuer'] / 100)
    cf_pre_m = (netto_miete - kd) / 12
    cf_post_m = (netto_miete - kd - steuerlast) / 12

    # Returns
    gewinn_nach_zinsen = netto_miete - zinslast
    roe = (gewinn_nach_zinsen / ek_abs * 100) if ek_abs > 0 else 0
    roi = (netto_miete / gesamt * 100) if gesamt > 0 else 0

    # Operativ
    kostensatz = (inp['bew'] + inp['leerstand']) / 100
    be_monat = ((kd / (1 - kostensatz)) / 12) if (kostensatz < 1 and kd > 0) else 0
    amort = (ek_abs / (cf_post_m * 12)) if (cf_post_m * 12 > 0) else None

    # 10-Jahres-Projektion
    annuitaet = fk * (inp['zins'] + inp['tilgung']) / 100
    proj = []
    debt = fk
    m_brutto = inp['jahresmiete']
    iwert = inp['kaufpreis']
    irr_cfs = []
    cum_cf_post = 0

    for y in range(1, 11):
        m_bew = m_brutto * (inp['bew'] / 100)
        m_leer = m_brutto * (inp['leerstand'] / 100)
        m_netto = m_brutto - m_bew - m_leer - ihr
        
        y_zins = debt * (inp['zins'] / 100)
        y_tilg = min(debt, max(0, annuitaet - y_zins))
        y_kd = y_zins + y_tilg
        
        y_stl = (m_netto - y_zins - afa) * (inp['steuer'] / 100)
        y_cf_pre = m_netto - y_kd
        y_cf_post = y_cf_pre - y_stl
        
        cum_cf_post += y_cf_post
        debt = max(0, debt - y_tilg)
        iwert *= (1 + inp['wertZuwachs'] / 100)
        eq = iwert - debt
        
        irr_cfs.append(y_cf_post + (max(0, eq - ek_abs) if y == 10 else 0))
        proj.append({
            "Jahr": f"J{y}", "CF pre-Tax": y_cf_pre / 12, "CF post-Tax": y_cf_post / 12,
            "Eigenkapital": eq, "Immobilienwert": iwert, "Restschuld": debt
        })
        m_brutto *= (1 + inp['mietSteigerung'] / 100)

    try: irr_val = calc_irr(-ek_abs, irr_cfs)
    except: irr_val = 0
    npv_val = calc_npv(-ek_abs, irr_cfs, inp['diskont'] / 100)
    
    final_eq = proj[-1]['Eigenkapital'] if proj else ek_abs
    moic = (cum_cf_post + final_eq) / ek_abs if ek_abs > 0 else 0

    pie = [
        {"name": "Kaufpreis", "value": inp['kaufpreis'], "color": T["blue"]},
        {"name": "Grunderwerbsteuer", "value": grunderwerbsteuer, "color": T["gold"]},
        {"name": "Notar/Grundbuch", "value": notar, "color": "#8b5cf6"},
        {"name": "Makler", "value": makler, "color": T["cyan"]}
    ]

    return {
        "knkAbs": knk_abs, "grunderwerbsteuer": grunderwerbsteuer, "notarGrundbuch": notar, "makler": makler, "gesamt": gesamt,
        "bewKosten": bew_kosten, "leerstandAbs": leerstand_abs, "ihr": ihr, "noi": noi, "nettoMiete": netto_miete,
        "brutto": brutto, "faktor": faktor, "nettoRend": netto_rend, "capRate": cap_rate,
        "ekAbs": ek_abs, "fk": fk, "zinslast": zinslast, "tilgAbs": tilg_abs, "kd": kd, "annuitaet": annuitaet, "ltv": ltv, "dscr": dscr,
        "afa": afa, "steuerlast": steuerlast, "stlErgebnis": stl_ergebnis,
        "cfPreM": cf_pre_m, "cfPostM": cf_post_m,
        "roe": roe, "roi": roi, "beMonat": be_monat, "amort": amort,
        "irrVal": irr_val, "npvVal": npv_val, "moic": moic,
        "proj": proj, "pie": [d for d in pie if d["value"] > 0]
    }

def calc_scenario(base_inp, mode):
    sc_inp = base_inp.copy()
    if mode == "optimistic":
        sc_inp['jahresmiete'] *= 1.10
        sc_inp['zins'] = max(0.5, sc_inp['zins'] - 0.5)
        sc_inp['leerstand'] = max(0, sc_inp['leerstand'] - 1)
        sc_inp['wertZuwachs'] += 1.5
    elif mode == "pessimistic":
        sc_inp['jahresmiete'] *= 0.90
        sc_inp['zins'] += 0.8
        sc_inp['leerstand'] += 3
        sc_inp['wertZuwachs'] = max(0, sc_inp['wertZuwachs'] - 1.5)
        sc_inp['bew'] = min(35, sc_inp['bew'] + 3)
    return calc_all(sc_inp)

# ─────────────────────────────────────────────────────────────────────────────
# 3. AMPEL-LOGIK & KARTEN-RENDERER
# ─────────────────────────────────────────────────────────────────────────────
def get_ampel(key, val):
    if key == "brutto": return "green" if val >= 6 else "yellow" if val >= 4 else "red"
    if key == "nettoRend": return "green" if val >= 4.5 else "yellow" if val >= 3 else "red"
    if key == "capRate": return "green" if val >= 5 else "yellow" if val >= 3.5 else "red"
    if key == "faktor": return "green" if val <= 20 else "yellow" if val <= 25 else "red"
    if key == "dscr": return "green" if val >= 1.3 else "yellow" if val >= 1.1 else "red"
    if key == "ltv": return "green" if val <= 70 else "yellow" if val <= 80 else "red"
    if key == "cfPreM": return "green" if val >= 0 else "yellow" if val >= -150 else "red"
    if key == "cfPostM": return "green" if val >= 0 else "yellow" if val >= -150 else "red"
    if key == "roe": return "green" if val >= 8 else "yellow" if val >= 5 else "red"
    if key == "irrVal": return "green" if val >= 8 else "yellow" if val >= 5 else "red"
    if key == "npvVal": return "green" if val >= 0 else "red"
    if key == "moic": return "green" if val >= 2 else "yellow" if val >= 1.5 else "red"
    return "yellow"

AMP = {
    "green": {"color": T["green"], "bg": "rgba(16,185,129,0.12)", "label": "Gut", "border": "rgba(16,185,129,0.25)"},
    "yellow": {"color": T["yellow"], "bg": "rgba(245,158,11,0.12)", "label": "Akzeptabel", "border": "rgba(245,158,11,0.25)"},
    "red": {"color": T["red"], "bg": "rgba(239,68,68,0.12)", "label": "Kritisch", "border": "rgba(239,68,68,0.25)"}
}

def render_kpi(label, value, sub_label="", ampel_key=None, ampel_val=None):
    ampel_html = ""
    border_top = ""
    val_color = T["text"]
    if ampel_key:
        a = AMP[get_ampel(ampel_key, ampel_val if ampel_val is not None else value)]
        val_color = a["color"]
        border_top = f"border-top: 2px solid {a['color']};"
        ampel_html = f"<div class='ampel-badge' style='color:{a['color']}; background:{a['bg']};'>{a['label']}</div>"
    
    st.markdown(f"""
        <div class='kpi-box' style='{border_top}'>
            <div class='kpi-title'>{label}</div>
            <div class='kpi-value' style='color: {val_color};'>{value}</div>
            <div class='kpi-sub'>{sub_label}</div>
            {ampel_html}
        </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 4. APP LAYOUT & HEADER
# ─────────────────────────────────────────────────────────────────────────────
col_logo, col_mode = st.columns([3, 1])
with col_logo:
    st.markdown(f"### <span style='color:{T['gold']}'>YieldBase v2</span> | Investment Analytics", unsafe_allow_html=True)
with col_mode:
    mode = st.radio("Modus", ["Einsteiger", "Experte"], horizontal=True, label_visibility="collapsed")
is_expert = mode == "Experte"

# Globale Inputs sammeln
if 'inp' not in st.session_state:
    st.session_state.inp = {
        "kaufpreis": 450000.0, "knk": 8.5, "jahresmiete": 16800.0, "bew": 18.0,
        "ek": 25.0, "zins": 3.8, "tilgung": 2.0, "steuer": 42.0, "gebaeude": 80.0,
        "isDenkmal": False, "dkSan": 60.0, "dkAfa": 9.0, "regAfa": 2.0,
        "baujahr": 1975, "wertZuwachs": 2.0, "mietSteigerung": 1.5, "leerstand": 3.0, "diskont": 5.0
    }

inp = st.session_state.inp.copy()

# ─────────────────────────────────────────────────────────────────────────────
# 5. TABS & CONTENT
# ─────────────────────────────────────────────────────────────────────────────
t1, t2, t3, t4 = st.tabs(["⌨ Eingabe", "▦ KPI Dashboard", "⛶ Analyse", "▤ Bericht"])

with t1:
    col_l, col_r = st.columns([1, 1.2], gap="large")
    
    with col_l:
        st.markdown(f"<div class='saas-card'><div class='saas-card-header'><span>01</span> Objekt & Transaktion</div>", unsafe_allow_html=True)
        inp['kaufpreis'] = st.number_input("Kaufpreis (€)", value=inp['kaufpreis'], step=5000.0)
        inp['knk'] = st.slider("Kaufnebenkosten (KNK %)", 5.0, 15.0, value=inp['knk'], step=0.5)
        inp['jahresmiete'] = st.number_input("Jahres-Kaltmiete (€)", value=inp['jahresmiete'], step=500.0)
        inp['bew'] = st.slider("Bewirtschaftungskosten (%)", 5.0, 35.0, value=inp['bew'], step=1.0)
        inp['leerstand'] = st.slider("Leerstandsrisiko (%)", 0.0, 15.0, value=inp['leerstand'], step=0.5)
        inp['baujahr'] = st.number_input("Baujahr", value=inp['baujahr'], step=1)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(f"<div class='saas-card'><div class='saas-card-header'><span>02</span> Finanzierung</div>", unsafe_allow_html=True)
        inp['ek'] = st.slider("Eigenkapital-Quote (%)", 5.0, 100.0, value=inp['ek'], step=1.0)
        inp['zins'] = st.slider("Sollzins p.a. (%)", 0.5, 8.0, value=inp['zins'], step=0.1)
        inp['tilgung'] = st.slider("Anfangstilgung p.a. (%)", 0.5, 6.0, value=inp['tilgung'], step=0.1)
        st.markdown("</div>", unsafe_allow_html=True)

        if is_expert:
            st.markdown(f"<div class='saas-card'><div class='saas-card-header'><span>03</span> Steuer & AfA</div>", unsafe_allow_html=True)
            inp['steuer'] = st.slider("Persönlicher Steuersatz (%)", 0.0, 45.0, value=inp['steuer'], step=1.0)
            inp['gebaeude'] = st.slider("Gebäudeanteil (%)", 40.0, 100.0, value=inp['gebaeude'], step=1.0)
            inp['isDenkmal'] = st.toggle("Denkmalschutz-AfA aktiv (§ 7i EStG)", value=inp['isDenkmal'])
            if inp['isDenkmal']:
                inp['dkSan'] = st.slider("Sanierungsanteil (%)", 10.0, 90.0, value=inp['dkSan'], step=1.0)
                inp['dkAfa'] = st.slider("Denkmal-AfA-Satz (%)", 3.0, 12.0, value=inp['dkAfa'], step=0.5)
            else:
                inp['regAfa'] = st.slider("Reguläre Gebäude-AfA (%)", 1.0, 4.0, value=inp['regAfa'], step=0.5)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(f"<div class='saas-card'><div class='saas-card-header'><span>04</span> Projekt-Prämissen (10 J.)</div>", unsafe_allow_html=True)
            inp['wertZuwachs'] = st.slider("Wertzuwachs p.a. (%)", -2.0, 6.0, value=inp['wertZuwachs'], step=0.5)
            inp['mietSteigerung'] = st.slider("Mietsteigerung p.a. (%)", 0.0, 5.0, value=inp['mietSteigerung'], step=0.25)
            inp['diskont'] = st.slider("Diskontierungssatz (%)", 1.0, 12.0, value=inp['diskont'], step=0.5)
            st.markdown("</div>", unsafe_allow_html=True)

    # Master Calculation
    st.session_state.inp = inp
    res = calc_all(inp)

    with col_r:
        # Kernergebnis-Banner
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {T['surface2']} 0%, {T['surface3']} 100%); border: 1px solid {T['border']}; border-radius: 12px; padding: 22px 24px; margin-bottom: 20px;">
            <div style="font-family: Georgia, serif; font-size: 0.9rem; color: {T['textMuted']}; margin-bottom: 6px;">Gesamtinvestition (inkl. {fmt_pct(inp['knk'])} KNK)</div>
            <div style="font-family: 'Courier New', monospace; font-size: 2.2rem; font-weight: 700; color: {T['gold']};">{fmt_eur(res['gesamt'])}</div>
            <div style="display: flex; gap: 20px; margin-top: 14px;">
                <div><div style="font-size: 0.7rem; color: {T['textDim']}; text-transform: uppercase;">Eigenkapital</div><div style="font-family: monospace; color: {T['text']};">{fmt_eur(res['ekAbs'])}</div></div>
                <div><div style="font-size: 0.7rem; color: {T['textDim']}; text-transform: uppercase;">Fremdkapital</div><div style="font-family: monospace; color: {T['text']};">{fmt_eur(res['fk'])}</div></div>
                <div><div style="font-size: 0.7rem; color: {T['textDim']}; text-transform: uppercase;">Kaufnebenkosten</div><div style="font-family: monospace; color: {T['text']};">{fmt_eur(res['knkAbs'])}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not is_expert:
            c1, c2 = st.columns(2)
            with c1:
                render_kpi("Bruttorendite", fmt_pct(res['brutto']), "Kaufpreis-Basis", "brutto", res['brutto'])
                render_kpi("Kaufpreisfaktor", fmt_x(res['faktor']), "Jahre bis Amortisation", "faktor", res['faktor'])
                render_kpi("Cashflow/Monat", fmt_eur(res['cfPreM']), "Vor Steuer", "cfPreM", res['cfPreM'])
            with c2:
                render_kpi("Netto-Rendite", fmt_pct(res['nettoRend']), "Gesamtinvestition", "nettoRend", res['nettoRend'])
                render_kpi("DSCR", f"{res['dscr']:.2f}".replace(".", ","), "Schuldendeckungsgrad", "dscr", res['dscr'])
                render_kpi("Break-Even-Miete", fmt_eur(res['beMonat']), "Mindestmiete/Monat")
            
            msg = "Günstiger Einstieg (< 22x)." if res['faktor'] <= 22 else "Marktüblich (22–27x)." if res['faktor'] <= 27 else "Teuer (> 27x)."
            st.markdown(f"<div class='benchmark-box'>💡 Kaufpreisfaktor: {fmt_x(res['faktor'])} — {msg}</div>", unsafe_allow_html=True)

        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                render_kpi("Bruttorendite", fmt_pct(res['brutto']), ampel_key="brutto", ampel_val=res['brutto'])
                render_kpi("Kaufpreisfaktor", fmt_x(res['faktor']), ampel_key="faktor", ampel_val=res['faktor'])
                render_kpi("CF pre-Tax/Mon.", fmt_eur(res['cfPreM']), ampel_key="cfPreM", ampel_val=res['cfPreM'])
                render_kpi("IRR (10 J.)", fmt_pct(res['irrVal']), ampel_key="irrVal", ampel_val=res['irrVal'])
                render_kpi("AfA p.a.", fmt_eur(res['afa']), "Denkmal § 7i" if inp['isDenkmal'] else "Regulär")
            with c2:
                render_kpi("Netto-Rendite", fmt_pct(res['nettoRend']), ampel_key="nettoRend", ampel_val=res['nettoRend'])
                render_kpi("DSCR", f"{res['dscr']:.2f}".replace(".",","), ampel_key="dscr", ampel_val=res['dscr'])
                render_kpi("CF post-Tax/Mon.", fmt_eur(res['cfPostM']), ampel_key="cfPostM", ampel_val=res['cfPostM'])
                render_kpi("NPV", fmt_eur(res['npvVal']), ampel_key="npvVal", ampel_val=res['npvVal'])
                render_kpi("Break-Even-Miete", fmt_eur(res['beMonat']), "Mindestmiete/Mon.")
            with c3:
                render_kpi("Cap Rate (NOI)", fmt_pct(res['capRate']), ampel_key="capRate", ampel_val=res['capRate'])
                render_kpi("LTV", fmt_pct(res['ltv']), ampel_key="ltv", ampel_val=res['ltv'])
                render_kpi("ROE", fmt_pct(res['roe']), ampel_key="roe", ampel_val=res['roe'])
                render_kpi("MOIC", fmt_x(res['moic']), ampel_key="moic", ampel_val=res['moic'])
                render_kpi("Amortisation EK", fmt_yr(res['amort']) if res['amort'] else "Negativ", "aus Post-Tax-CF")

        # Kostenstruktur Donut Chart
        st.markdown(f"<div class='saas-card' style='margin-top:20px;'><div class='saas-card-header'>Kostenstruktur</div>", unsafe_allow_html=True)
        df_pie = pd.DataFrame(res['pie'])
        base = alt.Chart(df_pie).encode(
            theta=alt.Theta("value:Q", stack=True),
            color=alt.Color("name:N", scale=alt.Scale(domain=df_pie['name'].tolist(), range=df_pie['color'].tolist()), legend=None),
            tooltip=["name", "value"]
        )
        pie = base.mark_arc(innerRadius=50, outerRadius=90)
        
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1: st.altair_chart(pie, use_container_width=True)
        with col_p2:
            for item in res['pie']:
                st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:8px;'><span style='color:{T['textMuted']}; font-size:0.9rem;'><span style='display:inline-block; width:10px; height:10px; background:{item['color']}; border-radius:2px; margin-right:8px;'></span>{item['name']}</span><span style='font-family:monospace;'>{fmt_eur(item['value'])}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

with t2:
    st.markdown("### Rendite & Ertrag")
    c1, c2, c3, c4 = st.columns(4)
    with c1: render_kpi("Bruttorendite", fmt_pct(res['brutto']), "Jahresmiete / Kaufpreis", "brutto", res['brutto'])
    with c2: render_kpi("Netto-Mietrendite", fmt_pct(res['nettoRend']), "Nach Bewirtschaftung", "nettoRend", res['nettoRend'])
    with c3: render_kpi("Cap Rate (NOI)", fmt_pct(res['capRate']), "Vor Finanzierung", "capRate", res['capRate'])
    with c4: render_kpi("Kaufpreisfaktor", fmt_x(res['faktor']), "Brutto-Rückzahldauer", "faktor", res['faktor'])

    st.markdown("### Cashflow & Liquidität")
    c1, c2, c3, c4 = st.columns(4)
    with c1: render_kpi("CF / Monat (pre)", fmt_eur(res['cfPreM']), "Vor Steuer", "cfPreM", res['cfPreM'])
    with c2: render_kpi("CF / Monat (post)", fmt_eur(res['cfPostM']), "Nach Steuerschild", "cfPostM", res['cfPostM'])
    with c3: render_kpi("AfA Steuerschild", fmt_eur(res['afa']), "p.a.")
    with c4: render_kpi("Steuerlast p.a.", fmt_eur(res['steuerlast']), f"{inp['steuer']} % Steuersatz")

    if is_expert:
        st.markdown("### Finanzierung & Verschuldung")
        c1, c2, c3, c4 = st.columns(4)
        with c1: render_kpi("DSCR", f"{res['dscr']:.2f}".replace(".",","), "Schuldendeckungsgrad", "dscr", res['dscr'])
        with c2: render_kpi("LTV", fmt_pct(res['ltv']), "Loan-to-Value", "ltv", res['ltv'])
        with c3: render_kpi("Kapitaldienst p.a.", fmt_eur(res['kd']), "Zins + Tilgung")
        with c4: render_kpi("Zinslast p.a.", fmt_eur(res['zinslast']), f"{inp['zins']}% p.a.")

with t3:
    st.markdown("### Cashflow-Projektion (10 Jahre)")
    df_proj = pd.DataFrame(res['proj']).set_index('Jahr')
    st.area_chart(df_proj[['CF pre-Tax', 'CF post-Tax']], color=[T["cyan"], T["gold"]], height=300)

    st.markdown("### Vermögensaufbau (Equity Buildup)")
    st.line_chart(df_proj[['Eigenkapital', 'Immobilienwert', 'Restschuld']], color=[T["green"], T["blue"], T["red"]], height=300)

    st.markdown("### Szenario-Vergleich")
    sc_opt = calc_scenario(inp, "optimistic")
    sc_real = res
    sc_pess = calc_scenario(inp, "pessimistic")
    
    sc_data = {
        "KPI": ["Bruttorendite", "Netto-Rendite", "DSCR", "Cashflow / Monat", "ROE", "IRR (10 J.)", "NPV", "MOIC"],
        "Optimistisch": [fmt_pct(sc_opt['brutto']), fmt_pct(sc_opt['nettoRend']), f"{sc_opt['dscr']:.2f}", fmt_eur(sc_opt['cfPreM']), fmt_pct(sc_opt['roe']), fmt_pct(sc_opt['irrVal']), fmt_eur(sc_opt['npvVal']), fmt_x(sc_opt['moic'])],
        "Realistisch": [fmt_pct(sc_real['brutto']), fmt_pct(sc_real['nettoRend']), f"{sc_real['dscr']:.2f}", fmt_eur(sc_real['cfPreM']), fmt_pct(sc_real['roe']), fmt_pct(sc_real['irrVal']), fmt_eur(sc_real['npvVal']), fmt_x(sc_real['moic'])],
        "Pessimistisch": [fmt_pct(sc_pess['brutto']), fmt_pct(sc_pess['nettoRend']), f"{sc_pess['dscr']:.2f}", fmt_eur(sc_pess['cfPreM']), fmt_pct(sc_pess['roe']), fmt_pct(sc_pess['irrVal']), fmt_eur(sc_pess['npvVal']), fmt_x(sc_pess['moic'])]
    }
    st.dataframe(pd.DataFrame(sc_data), use_container_width=True, hide_index=True)

with t4:
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {T['surface2']} 0%, {T['surface3']} 100%); border: 1px solid {T['border']}; border-radius: 14px; padding: 30px 36px; margin-bottom: 20px;">
        <div style="font-family: Georgia, serif; font-size: 2rem; color: {T['text']}; margin-bottom: 6px;">Investment Summary</div>
        <div style="font-size: 0.9rem; color: {T['textDim']}; margin-bottom: 24px;">YieldBase Analytics v2</div>
        <div style="display: flex; gap: 20px; margin-bottom: 24px;">
            <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 14px 16px; flex: 1;">
                <div style="font-size: 0.7rem; color: {T['textDim']}; text-transform: uppercase;">Gesamtinvestition</div>
                <div style="font-family: monospace; font-size: 1.5rem; color: {T['gold']};">{fmt_eur(res['gesamt'])}</div>
            </div>
            <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 14px 16px; flex: 1;">
                <div style="font-size: 0.7rem; color: {T['textDim']}; text-transform: uppercase;">Jahresmiete (Brutto)</div>
                <div style="font-family: monospace; font-size: 1.5rem; color: {T['gold']};">{fmt_eur(inp['jahresmiete'])}</div>
            </div>
        </div>
        <hr/>
        <div style="background: rgba(0,0,0,0.15); border-radius: 8px; padding: 14px 16px; font-size: 0.95rem; line-height: 1.6; color: {T['textMuted']};">
            <strong style="color: {T['text']}">Analyse:</strong> Bei einem Kaufpreis von <strong style="color: {T['gold']}">{fmt_eur(inp['kaufpreis'])}</strong> und einer 
            Jahresnettomiete von <strong style="color: {T['gold']}">{fmt_eur(inp['jahresmiete'])}</strong> ergibt sich ein 
            Kaufpreisfaktor von <strong style="color: {T['text']}">{fmt_x(res['faktor'])}</strong>. Der monatliche Cashflow vor Steuer 
            liegt bei <strong>{fmt_eur(res['cfPreM'])}</strong>. Der DSCR von <strong>{res['dscr']:.2f}</strong> {'signalisiert solide Bankfähigkeit.' if res['dscr'] >= 1.2 else 'ist kritisch.'}
        </div>
    </div>
    """, unsafe_allow_html=True)
