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
    if is_denkmal:
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
