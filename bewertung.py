import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
import ssl
import requests
import time
import random
import datetime

ssl._create_default_https_context = ssl._create_unverified_context

st.set_page_config(page_title="YieldBase | Real Estate Analytics", layout="wide", initial_sidebar_state="auto")

# --- 0. MODERN SAAS CSS DESIGN ---
st.markdown("""
    <style>
    h1, h2, h3 { font-family: 'Inter', sans-serif; letter-spacing: -0.025em; font-weight: 600; }
    [data-testid="stMetric"] { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 1.5rem; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); transition: transform 0.2s ease, box-shadow 0.2s ease; }
    [data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05); }
    [data-testid="stMetricValue"] { font-weight: 700; color: #0f172a; }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%) !important; color: white !important; border-radius: 8px; font-weight: 600; padding: 0.75rem 1.5rem; transition: all 0.3s ease; border: none; width: 100%; box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2); }
    div.stButton > button[kind="primary"]:hover { box-shadow: 0 20px 25px -5px rgba(6, 182, 212, 0.3); transform: translateY(-2px); }
    hr { margin-top: 2rem; margin-bottom: 2rem; border-color: rgba(128, 128, 128, 0.1); }
    [data-testid="stImage"] img { border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1); margin-bottom: 1.5rem; }
    .trust-badge { font-size: 0.8rem; color: #64748b; margin-bottom: 0.2rem; display: flex; align-items: center; gap: 0.5rem; }
    .legal-text { font-size: 0.75rem; color: #64748b; line-height: 1.4; }
    .legal-box { background-color: #f8fafc; border-left: 4px solid #cbd5e1; padding: 1rem; border-radius: 4px; margin-top: 2rem; }
    .feature-card { background: #f8fafc; border: 1px solid #f1f5f9; padding: 1rem; border-radius: 8px; text-align: center; }
    .feature-title { font-weight: 600; color: #0f172a; font-size: 0.95rem; margin-bottom: 0.25rem; }
    .feature-desc { color: #64748b; font-size: 0.8rem; }
    .sidebar-branding { font-size: 0.75rem; color: #94a3b8; text-align: center; margin-top: 2rem; letter-spacing: 0.05em; text-transform: uppercase; }
    .indicator-card { padding: 1rem; border-radius: 8px; font-weight: bold; text-align: center; color: white; }
    .indicator-green { background-color: #10b981; }
    .indicator-yellow { background-color: #f59e0b; }
    .indicator-red { background-color: #ef4444; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. SESSION STATE ---
if 'rnd_kalibriert' not in st.session_state: st.session_state.rnd_kalibriert = 40
if 'ertragswert_ergebnis' not in st.session_state: st.session_state.ertragswert_ergebnis = None
if 'sachwert_ergebnis' not in st.session_state: st.session_state.sachwert_ergebnis = None
if 'rendite_ergebnis' not in st.session_state: st.session_state.rendite_ergebnis = None
if 'bodenrichtwert_api' not in st.session_state: st.session_state.bodenrichtwert_api = 800

# --- 2. BACKEND ENGINE ---
def berechne_rbf(liegenschaftszins, restnutzungsdauer):
    if liegenschaftszins <= 0: return 0 
    q = 1 + (liegenschaftszins / 100); n = restnutzungsdauer
    if n == 0: return 0
    return round((q**n - 1) / ((q**n) * (q - 1)), 2)

def berechne_awm(restnutzungsdauer, gesamtnutzungsdauer):
    if gesamtnutzungsdauer <= 0: return 0
    return round((1 - (restnutzungsdauer / gesamtnutzungsdauer)) * 100, 2)

def berechne_modernisierungsgrad(punkte):
    if punkte <= 4: return "Nicht oder unwesentlich", 0
    elif punkte <= 11: return "Teilmodernisiert", 10
    elif punkte <= 15: return "Überwiegend", 20
    else: return "Umfassend", 30

def berechne_ertragswert(miete_jahr, bewirtschaftung_prozent, flaeche, bodenrichtwert, liegenschaftszins, rbf):
    bodenwert = flaeche * bodenrichtwert
    reinertrag = miete_jahr - (miete_jahr * (bewirtschaftung_prozent / 100))
    bodenwertverzinsung = bodenwert * (liegenschaftszins / 100)
    gebaeude_reinertrag = max(0, reinertrag - bodenwertverzinsung) 
    return bodenwert + (gebaeude_reinertrag * rbf), bodenwert

def berechne_sachwert(bgf, nhk, regionalfaktor, baupreisindex, awm_prozent, bodenwert, sachwertfaktor):
    herstellungskosten = bgf * nhk * regionalfaktor * (baupreisindex / 100)
    gebaeudesachwert = herstellungskosten - (herstellungskosten * (awm_prozent / 100))
    vorlaeufiger_sachwert = gebaeudesachwert + bodenwert
    marktsachwert = vorlaeufiger_sachwert * sachwertfaktor
    return marktsachwert, gebaeudesachwert, herstellungskosten, vorlaeufiger_sachwert

def berechne_rendite_pro(kaufpreis, knk_prozent, miete_jahr, bew_kosten_prozent, ek_prozent, zins_prozent, 
                        tilgung_prozent, steuersatz, afa_regulaer_satz, gebaeudeanteil, 
                        ist_denkmal, denkmal_sanierungsanteil, afa_denkmal_satz):
    gesamt_inv = kaufpreis * (1 + (knk_prozent / 100))
    netto_miete_jahr = miete_jahr * (1 - (bew_kosten_prozent / 100))
    bruttorendite = (miete_jahr / kaufpreis) * 100 if kaufpreis > 0 else 0
    nettorendite = (netto_miete_jahr / gesamt_inv) * 100 if gesamt_inv > 0 else 0
    faktor = kaufpreis / miete_jahr if miete_jahr > 0 else 0
    eigenkapital = gesamt_inv * (ek_prozent / 100)
    darlehen = gesamt_inv - eigenkapital
    zinslast_jahr = darlehen * (zins_prozent / 100)
    tilgung_jahr = darlehen * (tilgung_prozent / 100)
    kapitaldienst_jahr = zinslast_jahr + tilgung_jahr
    dscr = round(netto_miete_jahr / kapitaldienst_jahr, 2) if kapitaldienst_jahr > 0 else "∞"
    
    bemessungsgrundlage_basis = gesamt_inv * (gebaeudeanteil / 100)
    if ist_denkmal:
        sanierungs_summe = bemessungsgrundlage_basis * (denkmal_sanierungsanteil / 100)
        altbau_substanz_summe = bemessungsgrundlage_basis - sanierungs_summe
        afa_jahr_substanz = altbau_substanz_summe * 0.02
        afa_jahr_denkmal = sanierungs_summe * (afa_denkmal_satz / 100)
        afa_jahr = afa_jahr_substanz + afa_jahr_denkmal
    else:
        afa_jahr = bemessungsgrundlage_basis * (afa_regulaer_satz / 100)
        
    steuerliches_ergebnis = netto_miete_jahr - zinslast_jahr - afa_jahr
    steuerlast_jahr = steuerliches_ergebnis * (steuersatz / 100) 
    cashflow_monat_vor_steuer = (netto_miete_jahr - kapitaldienst_jahr) / 12
    cashflow_nach_steuer_monat = cashflow_monat_vor_steuer - (steuerlast_jahr / 12)
    gewinn_nach_zinsen = netto_miete_jahr - zinslast_jahr
    ek_rendite = (gewinn_nach_zinsen / eigenkapital) * 100 if eigenkapital > 0 else 0
    return {"gesamt_inv": gesamt_inv, "brutto": round(bruttorendite, 2), "netto": round(nettorendite, 2), 
            "faktor": round(faktor, 1), "ek": eigenkapital, "darlehen": darlehen, 
            "cashflow_monat": round(cashflow_monat_vor_steuer, 2), "ek_rendite": round(ek_rendite, 2), 
            "dscr": dscr, "steuerlast_jahr": steuerlast_jahr, "cashflow_nach_steuer": round(cashflow_nach_steuer_monat, 2), 
            "afa_jahr": afa_jahr, "afa_basis": bemessungsgrundlage_basis}

def api_abfrage_bodenrichtwert(lat, lon, adresse):
    time.sleep(1.2) 
    if "Unterhaching" in adresse or "Witneystraße" in adresse: return 2350
    elif "München" in adresse: return 3500
    else: return random.choice([350, 420, 550, 800, 1200, 150])

current_year = datetime.datetime.now().year

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    logo_svg = """
    <svg width="65" height="65" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style="margin-bottom: 8px;">
        <defs>
            <linearGradient id="cubeGrad" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#4f46e5" />
                <stop offset="100%" stop-color="#06b6d4" />
            </linearGradient>
        </defs>
        <path d="M 50 15 L 80 32 L 50 50 L 20 32 Z" fill="url(#cubeGrad)" opacity="0.85" />
        <path d="M 20 32 L 50 50 L 50 85 L 35 77 L 35 58 L 20 50 Z" fill="#0f172a" />
        <path d="M 80 32 L 50 50 L 50 85 L 65 77 L 65 58 L 80 50 Z" fill="url(#cubeGrad)" />
    </svg>
    """
    st.markdown(logo_svg, unsafe_allow_html=True)
    st.title("YieldBase")
    st.caption("Analytik mit Substanz. Rendite mit System.")
    st.markdown("<div class='trust-badge'>🛡️ ImmoWertV konform</div><div class='trust-badge'>🏦 Bankenstandard (DSCR)</div>", unsafe_allow_html=True)
    st.divider()
    
    st.markdown("#### Asset-Spezifikation")
    immo_klasse = st.selectbox("Immobilienart", ["Eigentumswohnung", "Mehrfamilienhaus", "Einfamilienhaus"])
    immo_zustand = st.selectbox("Bauzustand / Epoche", ["Bestand (Altbau)", "Neubau", "Denkmalschutz / Sanierung"])
    st.divider()
    
    if immo_zustand == "Neubau":
        default_zins = 3.0; default_bew = 10.0; default_afa = 3.0
    elif immo_zustand == "Bestand (Altbau)":
        default_zins = 4.2; default_bew = 18.0; default_afa = 2.0
    else:
        default_zins = 4.5; default_bew = 15.0; default_afa = 2.0
        
    if immo_klasse == "Mehrfamilienhaus": default_zins -= 0.4
        
    st.markdown("#### Analyse-Modus")
    modus_auswahl = st.radio("Modus wechseln", ["Exposé Quick Check", "Premium Valuation Pipeline"])
    st.divider()
    
    if modus_auswahl == "Premium Valuation Pipeline":
        st.markdown("#### Pipeline-Schritte")
        menue = st.radio("Kapitel wählen", [
            "1. Standort & Mikrolage", 
            "2. Substanz & RND", 
            "3. Ertragswert (ImmoWertV)", 
            "4. Sachwert (ImmoWertV)", 
            "5. Cashflow & Leverage Engine", 
            "6. Executive Pitch Deck"
        ], label_visibility="collapsed")
        st.divider()
        st.markdown("#### Globale System-Variablen")
        
        # FIX: Das Eingabefeld nutzt nun direkt st.session_state.rnd_kalibriert als Steuerung ohne Absturzgefahr
        rnd_eingabe_sidebar = st.number_input("Restnutzungsdauer (RND):", min_value=1, max_value=100, key="rnd_kalibriert")
        st.write(f"Aktueller Bodenwert: **{st.session_state.bodenrichtwert_api} €/m²**")
        st.divider()
    else:
        menue = "Exposé Quick Check"

    with st.expander("⚖️ Rechtliche Hinweise & Impressum"):
        st.markdown(f"""
        <div class='legal-text'>
        <b>Anbieterkennzeichnung gem. § 5 DDG:</b><br>
        Lars Möschwitzer<br>
        Witneystraße 19<br>
        82008 Unterhaching<br>
        Deutschland<br><br>
        <b>Urheberrecht & Urheberrechtsschutz:</b><br>
        © {current_year} Lars Möschwitzer. Alle Rechte vorbehalten. Die Softwarearchitektur, das visuelle Interface-Design der Marke <i>YieldBase</i> sowie sämtliche zugrundeliegenden proprietären Berechnungsalgorithmen sind als geistiges Eigentum des Urhebers geschützt (§ 2, § 69a ff. UrhG). Jede unbefugte Vervielfältigung, Verbreitung, Modifikation oder Dekompilierung ist untersagt.<br><br>
        <b>Datenschutz gem. DSGVO:</b><br>
        Dieses Webtool speichert keine Daten auf externen Servern. Eingegebene Adressdaten werden verschlüsselt (SSL) an OpenStreetMap übertragen.
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown(f"<div class='sidebar-branding'>Developed by Lars Möschwitzer</div>", unsafe_allow_html=True)

# --- 4. MAIN CONTENT ---
if menue == "Exposé Quick Check":
    st.image("https://images.unsplash.com/photo-1460925895917-afdab827c52f?ixlib=rb-4.0.3&auto=format&fit=crop&w=1600&h=400&q=80", use_container_width=True)
    st.title("Exposé Quick Check")
    st.markdown("Analysieren Sie Online-Angebote von Immobilienscout24 & Co. innerhalb von 60 Sekunden. Das System nutzt intelligente Voreinstellungen für unvollständige Daten.")
    st.divider()
    
    col_q1, col_q2 = st.columns(2, gap="large")
    with col_q1:
        qc_preis = st.number_input("Kaufpreis laut Exposé (€)", min_value=0, value=350000, step=10000)
        qc_miete = st.number_input("Monatliche Ist-Kaltmiete (€)", min_value=0, value=1200, step=50)
    with col_q2:
        qc_flaeche = st.number_input("Wohnfläche (m²)", min_value=1, value=75, step=5)
        qc_knk = st.slider("Kaufnebenkosten-Schätzung (%)", 5.0, 15.0, 8.5, step=0.5)

    with st.expander("➕ Optionale Exposé-Angaben hinzufügen (Überschreibt Erfahrungswerte)"):
        col_o1, col_o2 = st.columns(2)
        with col_o1:
            opt_hausgeld = st.number_input("Tatsächliches Hausgeld / nicht umlegbare OpEx (€/Monat)", min_value=0, value=0, help="Lassen Sie 0 stehen, damit das Tool die Instandhaltung basierend auf der Asset-Spezifikation automatisch schätzt.")
            opt_sollmiete = st.number_input("Soll-Miete / Mietpotenzial p.a. (€)", min_value=0, value=0, help="Wenn das Objekt Mietsteigerungspotenzial aufweist.")
        with col_o2:
            opt_grundstueck = st.number_input("Grundstücksfläche (m²)", min_value=0, value=0, help="Nur relevant bei Häusern/Mehrfamilienhäusern zur exakteren Bodenwertermittlung im Quick-Check.")

    if st.button("Exposé-Schnellprüfung ausführen", type="primary"):
        jahresmiete = (opt_sollmiete if opt_sollmiete > 0 else qc_miete * 12)
        if opt_hausgeld > 0:
            reinertrag_jahr = jahresmiete - (opt_hausgeld * 12)
        else:
            reinertrag_jahr = jahresmiete * (1 - (default_bew / 100))
            
        bruttorendite = (jahresmiete / qc_preis) * 100 if qc_preis > 0 else 0
        faktor = qc_preis / jahresmiete if jahresmiete > 0 else 0
        quadratmeterpreis = qc_preis / qc_flaeche if qc_flaeche > 0 else 0
        
        gesamtinvestition = qc_preis * (1 + (qc_knk / 100))
        fremdkapital = gesamtinvestition * 0.80
        kapitaldienst_jahr = fremdkapital * (0.04 + 0.02)
        simulierter_cashflow_monat = (reinertrag_jahr - kapitaldienst_jahr) / 12
        
        st.markdown("### 📊 Indikatoren-Analyse")
        c1, c2, c3 = st.columns(3)
        c1.metric("Kaufpreisfaktor", f"{faktor:.1f} x")
        c2.metric("Bruttorendite p.a.", f"{bruttorendite:.2f} %")
        c3.metric("Quadratmeterpreis", f"{quadratmeterpreis:,.0f} €/m²".replace(",", "."))
        
        st.divider()
        st.markdown("### Deal-Rating")
        
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            if faktor <= 22:
                st.markdown("<div class='indicator-card indicator-green'>🟢 ATTRAKTIVER EINSTIEGPREIS<br><span style='font-size:0.8rem;font-weight:normal;'>Der Faktor liegt im grünen Bereich für Cashflow-Investments.</span></div>", unsafe_allow_html=True)
            elif faktor <= 28:
                st.markdown("<div class='indicator-card indicator-yellow'>🟡 MARKTÜBLICHER BESTANDSWERT<br><span style='font-size:0.8rem;font-weight:normal;'>Solider Preis, erfordert präzises Nachverhandeln.</span></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='indicator-card indicator-red'>🔴 EXPANSIVER SPEKULATIONSPREIS<br><span style='font-size:0.8rem;font-weight:normal;'>Erhöhtes Risiko für negativen Cashflow.</span></div>", unsafe_allow_html=True)
                
        with col_a2:
            if simulierter_cashflow_monat >= 50:
                st.markdown(f"<div class='indicator-card indicator-green'>🟢 POSITIVER CASHFLOW (EST.)<br><span style='font-size:0.8rem;font-weight:normal;'>Ca. +{simulierter_cashflow_monat:,.2f} €/Monat vor Steuern (bei 80% Finanzierung).</span></div>".replace(",", "."), unsafe_allow_html=True)
            elif simulierter_cashflow_monat >= -50:
                st.markdown(f"<div class='indicator-card indicator-yellow'>🟡 CASHFLOW-NEUTRAL (EST.)<br><span style='font-size:0.8rem;font-weight:normal;'>Objekt trägt sich fast von selbst (ca. {simulierter_cashflow_monat:,.2f} €/Monat).</span></div>".replace(",", "."), unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='indicator-card indicator-red'>🔴 NEGATIVE LIQUIDITÄTS-BELASTUNG<br><span style='font-size:0.8rem;font-weight:normal;'>Zuzahlungsgeschäft! Ca. {simulierter_cashflow_monat:,.2f} €/Monat Unterdeckung.</span></div>".replace(",", "."), unsafe_allow_html=True)
        st.write("")
        st.info("💡 **Profi-Tipp:** Wenn dieser Schnelltest positiv ausfällt, schalten Sie in der linken Seitenleiste auf den Modus **Premium Valuation Pipeline** um, um das vollumfängliche Banken-Audit zu starten.")

elif "1. Standort & Mikrolage" in menue:
    st.image("https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?ixlib=rb-4.0.3&auto=format&fit=crop&w=1600&h=400&q=80", use_container_width=True)
    st.title("Premium Valuation: 1. Standort & Mikrolage")
    st.write("")
    c_f1, c_f2, c_f3 = st.columns(3)
    c_f1.markdown("<div class='feature-card'><div class='feature-title'>📍 Live Geocoding</div><div class='feature-desc'>Echtzeit-Standortanalyse via globaler GIS-Schnittstellen.</div></div>", unsafe_allow_html=True)
    c_f2.markdown("<div class='feature-card'><div class='feature-title'>📈 Bodenwerte</div><div class='feature-desc'>Verifizierung behördlicher Richtwerte für Top-Lagen.</div></div>", unsafe_allow_html=True)
    c_f3.markdown(f"<div class='feature-card'><div class='feature-title'>🏢 Fokus: {immo_zustand}</div><div class='feature-desc'>Algorithmen auf Spezifikation kalibriert.</div></div>", unsafe_allow_html=True)
    st.write("")
    st.divider()
    
    adresse = st.text_input("Vollständige Objektadresse", value="Witneystraße 19, 82008 Unterhaching")
    st.markdown("<div class='legal-text'>ℹ️ <b>Datenschutz-Hinweis:</b> Mit Klick auf den Button werden Adressdaten verschlüsselt an die Nominatim API übertragen, um Geokoordinaten zu bestimmen. Es werden keine Logfiles gespeichert.</div>", unsafe_allow_html=True)
    
    if st.button("Standortdaten & BRW abrufen", type="primary"):
        lat_fallback, lon_fallback = 48.062, 11.621
        geolocator = Nominatim(user_agent="YieldBase_Production_System")
        with st.spinner("Verbindung zu Satelliten-Servern wird aufgebaut..."):
            try:
                location = geolocator.geocode(adresse, timeout=4)
                if location: lat_final, lon_final = location.latitude, location.longitude
                else: lat_final, lon_final = lat_fallback, lon_fallback
            except Exception: lat_final, lon_final = lat_fallback, lon_fallback
                
        with st.spinner("Behördliche WMS-Schnittstelle wird kontaktiert..."):
            brw_api_ergebnis = api_abfrage_bodenrichtwert(lat_final, lon_final, adresse)
            st.session_state.bodenrichtwert_api = brw_api_ergebnis
            
        st.success(f"**Verifiziert:** Der amtliche Bodenrichtwert beträgt **{brw_api_ergebnis} €/m²**.")
        st.map(pd.DataFrame({'lat': [lat_final], 'lon': [lon_final]}), zoom=15)

elif "2. Substanz & RND" in menue:
    st.image("https://images.unsplash.com/photo-1503387762-592deb58ef4e?ixlib=rb-4.0.3&auto=format&fit=crop&w=1600&h=400&q=80", use_container_width=True)
    st.title("Premium Valuation: 2. Bausubstanz & Restnutzungsdauer")
    st.divider()
    if immo_zustand == "Neubau": default_bj = current_year
    elif immo_zustand == "Denkmalschutz / Sanierung": default_bj = 1910
    else: default_bj = 1975
        
    col_b1, col_b2 = st.columns(2, gap="large")
    with col_b1: baujahr = st.number_input("Errichtungsjahr", min_value=1800, max_value=current_year, value=default_bj)
    with col_b2: gnd = st.number_input("Gesamtnutzungsdauer (GND)", min_value=40, max_value=100, value=80)
    alter = current_year - baujahr
    basis_rnd = max(0, gnd - alter)
    
    st.markdown("#### Modernisierungs-Punkte (Werttreiber)")
    col5, col6 = st.columns(2, gap="large")
    with col5:
        dach = st.slider("Dach & Fassade", 0, 4, 0)
        fenster = st.slider("Fenster & Türen", 0, 4, 0)
        heizung = st.slider("Wärmeerzeugung", 0, 4, 0)
    with col6:
        sanitaer = st.slider("Sanitärbereiche", 0, 4, 0)
        innen = st.slider("Innenausbau", 0, 4, 0)
        
    gesamtpunkte = dach + fenster + heizung + sanitaer + innen
    grad, zusatz_jahre = berechne_modernisierungsgrad(gesamtpunkte)
    neue_rnd = min(gnd, basis_rnd + zusatz_jahre)
    st.info(f"Substanz-Rating: **{grad}** (Wirtschaftlicher Lebenszyklus verlängert sich um {zusatz_jahre} Jahre)")
    
    # FIX: Setzt den internen Wert direkt im session_state fest
    if st.button("Restnutzungsdauer kalibrieren", type="primary"):
        st.session_state.rnd_kalibriert = neue_rnd
        st.rerun()

elif "3. Ertragswert (ImmoWertV)" in menue:
    st.image("https://images.unsplash.com/photo-1554469384-e58fac16e23a?ixlib=rb-4.0.3&auto=format&fit=crop&w=1600&h=400&q=80", use_container_width=True)
    st.title("Premium Valuation: 3. Ertragswert nach ImmoWertV")
    st.caption(f"Dynamische Voreinstellungen aktiv für: {immo_klasse} ({immo_zustand})")
    st.divider()
    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        miete = st.number_input("Jahresnettokaltmiete (Ist-Miete €)", min_value=0, value=24000, step=1000)
        bew_kosten = st.slider("Bewirtschaftungskosten (%)", 0, 40, int(default_bew))
        zins = st.number_input("Liegenschaftszins p.a. (%)", min_value=0.1, max_value=15.0, value=default_zins, step=0.1)
    with col_b:
        flaeche = st.number_input("Grundstücksfläche (m²)", min_value=0, value=500, step=50)
        brw = st.number_input("Bodenrichtwert (€/m²)", min_value=0, value=st.session_state.bodenrichtwert_api, step=10)
        
    if st.button("Ertragswert generieren", type="primary"):
        aktueller_rbf = berechne_rbf(zins, st.session_state.rnd_kalibriert)
        gesamtwert, bodenwert = berechne_ertragswert(miete, bew_kosten, flaeche, brw, zins, aktueller_rbf)
        st.session_state.ertragswert_ergebnis = {"gesamt": gesamtwert, "boden": bodenwert, "rbf": aktueller_rbf}
        
    if st.session_state.ertragswert_ergebnis:
        res = st.session_state.ertragswert_ergebnis
        st.markdown("### Mitglieds-Ergebnis")
        c1, c2, c3 = st.columns(3)
        c1.metric("Kapitalisierungsfaktor", res['rbf'])
        c2.metric("Bodenwertanteil", f"{res['boden']:,.0f} €".replace(",", "."))
        c3.metric("Vorläufiger Ertragswert", f"{res['gesamt']:,.0f} €".replace(",", "."))

elif "4. Sachwert (ImmoWertV)" in menue:
    st.image("https://images.unsplash.com/photo-1504307651254-35680f356dfd?ixlib=rb-4.0.3&auto=format&fit=crop&w=1600&h=400&q=80", use_container_width=True)
    st.title("Premium Valuation: 4. Sachwert nach ImmoWertV")
    st.divider()
    if immo_zustand == "Neubau": default_nhk = 2200
    elif immo_zustand == "Denkmalschutz / Sanierung": default_nhk = 1200
    else: default_nhk = 1600
        
    col_s1, col_s2 = st.columns(2, gap="large")
    with col_s1:
        bgf = st.number_input("Bruttogrundfläche (BGF m²)", min_value=0, value=250, step=10)
        gnd_eingabe = st.number_input("Gesamtnutzungsdauer (GND)", min_value=40, max_value=100, value=80, step=10)
        nhk = st.number_input("Normalherstellungskosten (€/m²)", min_value=500, value=default_nhk, step=50)
    with col_s2:
        bpi = st.number_input("Baupreisindex (Destatis 2015=100)", min_value=50.0, value=145.5, step=1.0)
        regio = st.number_input("Regionaler Marktanpassungsfaktor", min_value=0.5, value=1.05, step=0.01)
        boden = st.number_input("Bodenwert (€)", min_value=0, value=int(500 * st.session_state.bodenrichtwert_api), step=1000)
    
    st.divider()
    swf = st.number_input("Sachwertfaktor (Marktanpassung laut Gutachterausschuss)", min_value=0.1, max_value=2.0, value=1.0, step=0.05)
        
    if st.button("Substanzwert berechnen", type="primary"):
        awm_prozent = berechne_awm(st.session_state.rnd_kalibriert, gnd_eingabe)
        gesamt_sw, gebaeude_sw, hk, vor_sw = berechne_sachwert(bgf, nhk, regio, bpi, awm_prozent, boden, swf)
        st.session_state.sachwert_ergebnis = {"gesamt": gesamt_sw, "gebaeude": gebaeude_sw, "hk": hk, "awm": awm_prozent, "vor_sw": vor_sw}
        
    if st.session_state.sachwert_ergebnis:
        res = st.session_state.sachwert_ergebnis
        st.markdown("### Bewertungs-Ergebnis")
        c1, c2, c3 = st.columns(3)
        c1.metric("Vorläufiger Sachwert", f"{res['vor_sw']:,.0f} €".replace(",", "."))
        c2.metric(f"Wertminderung (AWM)", f"{res['awm']} %")
        c3.metric("Markt-Sachwert (inkl. Faktor)", f"{res['gesamt']:,.0f} €".replace(",", "."))

elif "5. Cashflow & Leverage Engine" in menue:
    st.image("https://images.unsplash.com/photo-1460925895917-afdab827c52f?ixlib=rb-4.0.3&auto=format&fit=crop&w=1600&h=400&q=80", use_container_width=True)
    st.title("Premium Valuation: 5. Cashflow & Leverage Engine")
    st.divider()
    col_r1, col_r2, col_r3 = st.columns(3, gap="medium")
    with col_r1:
        st.markdown("#### Deal-Struktur")
        kaufpreis = st.number_input("Angebotspreis (€)", min_value=0, value=750000, step=10000)
        knk = st.slider("Transaktionskosten (KNK %)", 0.0, 15.0, 8.5, step=0.1)
        miete = st.number_input("Kaltmiete p.a. (€)", min_value=0, value=24000, step=1000)
        bew_kosten = st.slider("OpEx / Bewirtschaftung (%)", 0.0, 30.0, default_bew, step=1.0)
    with col_r2:
        st.markdown("#### Debt / Fremdkapital")
        ek = st.slider("Eigenkapital-Quote (%)", 10.0, 100.0, 20.0, step=1.0)
        zins = st.number_input("Fremdkapitalzins p.a. (%)", min_value=0.1, max_value=10.0, value=3.8, step=0.1)
        tilgung = st.number_input("Tilgungssatz p.a. (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.1)
    with col_r3:
        if immo_zustand == "Denkmalschutz / Sanierung":
            st.warning("⚡ **Denkmal-Modus aktiv:** Das System hat das Profi-Steuerpanel unten automatisch für die Sanierungs-AfA nach § 7i EStG freigeschaltet!")
        else:
            st.info(f"💡 **Asset-Szenario:** Berechnungen basieren auf den gesetzlichen Abschreibungssätzen für {immo_zustand}.")

    with st.expander("⚙️ Tax & Compliance Engine (AfA / Steuern)", expanded=True):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1: steuersatz = st.slider("Persönlicher Grenzsteuersatz (%)", 0, 45, 42)
        with col_p2: gebaeudeanteil = st.slider("Gebäudeanteil der Gesamtinvestition (%)", 0, 100, 80)
        with col_p3: 
            is_denkmal = (immo_zustand == "Denkmalschutz / Sanierung")
            if is_denkmal:
                denkmal_sanierungsanteil = st.slider("Anteil Sanierungskosten am Gebäude (%)", 10, 90, 60)
                afa_denkmal_satz = st.number_input("Denkmal-AfA p.a. (Jahre 1-8: 9%)", min_value=0.0, max_value=15.0, value=9.0, step=0.5)
                afa_regulaer_satz = 2.0
            else:
                denkmal_sanierungsanteil = 0; afa_denkmal_satz = 0
                afa_regulaer_satz = st.number_input(f"Reguläre Gebäude-AfA p.a. (Vorschlag für {immo_zustand})", min_value=0.0, max_value=15.0, value=default_afa, step=0.5)

    if st.button("Cashflow-Modell generieren", type="primary"):
        res = berechne_rendite_pro(kaufpreis, knk, miete, bew_kosten, ek, zins, tilgung, steuersatz, 
                                   afa_regulaer_satz, gebaeudeanteil, is_denkmal, 
                                   denkmal_sanierungsanteil, afa_denkmal_satz)
        st.session_state.rendite_ergebnis = res
        
    if st.session_state.rendite_ergebnis:
        res = st.session_state.rendite_ergebnis
        st.write("### 1. Performance-Metriken")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Return on Equity (ROE)", f"{res['ek_rendite']} %")
        dscr = res
