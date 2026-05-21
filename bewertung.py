import streamlit as st
import pandas as pd
import altair as alt
import math

st.set_page_config(page_title="YieldBase v2 | Analytics", layout="wide", initial_sidebar_state="collapsed")

# ─────────────────────────────────────────────────────────────────────────────
# 1. DESIGN TOKENS & CSS (Modern Light SaaS Theme)
# ─────────────────────────────────────────────────────────────────────────────
T = {
    "bg": "#f8fafc", "surface": "#ffffff", "surface2": "#f1f5f9", "surface3": "#e2e8f0",
    "border": "#e2e8f0", "borderHi": "#cbd5e1", "primary": "#2563eb", "primaryFaint": "rgba(37,99,235,0.08)",
    "green": "#059669", "yellow": "#d97706", "red": "#dc2626", "blue": "#2563eb", "cyan": "#0891b2",
    "text": "#0f172a", "textMuted": "#475569", "textDim": "#64748b"
}

st.markdown(f"""
    <style>
    /* Moderne Google Fonts importieren */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');

    /* Light Theme Base */
    .stApp {{ background-color: {T["bg"]}; color: {T["text"]}; font-family: 'Outfit', sans-serif; }}
    
    /* Typografie Overrides für Streamlit Natives */
    h1, h2, h3, h4, h5, h6, p, span, div, label {{ font-family: 'Outfit', sans-serif; }}
    
    /* Layout & Cards mit weichen Schatten */
    .saas-card {{ background-color: {T["surface"]}; border: 1px solid {T["border"]}; border-radius: 16px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); }}
    .saas-card-header {{ font-weight: 600; font-size: 1.15rem; color: {T["text"]}; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; letter-spacing: -0.01em; }}
    .saas-card-header span {{ color: {T["primary"]}; background: {T["primaryFaint"]}; padding: 4px 10px; border-radius: 8px; font-size: 0.95rem; font-weight: 700; }}
    
    /* KPI Metric Cards (Custom) */
    .kpi-box {{ background: {T["surface"]}; border: 1px solid {T["border"]}; border-radius: 12px; padding: 18px; position: relative; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); transition: transform 0.2s, box-shadow 0.2s; }}
    .kpi-box:hover {{ transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.08); }}
    .kpi-title {{ font-size: 0.75rem; color: {T["textDim"]}; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; margin-bottom: 6px; }}
    .kpi-value {{ font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: {T["text"]}; letter-spacing: -0.02em; }}
    .kpi-sub {{ font-size: 0.75rem; color: {T["textMuted"]}; margin-top: 6px; font-weight: 400; }}
    .ampel-badge {{ position: absolute; top: 12px; right: 12px; font-size: 0.65rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; text-transform: uppercase; letter-spacing: 0.05em; }}
    
    /* Streamlit Native Overrides für Light Mode */
    div[data-testid="stTabs"] button {{ color: {T["textDim"]}; font-size: 0.95rem; font-weight: 500; padding-top: 1rem; padding-bottom: 1rem; }}
    div[data-testid="stTabs"] button[aria-selected="true"] {{ color: {T["primary"]}; border-bottom-color: {T["primary"]}; font-weight: 600; }}
    .stSlider > div > div > div > div {{ background-color: {T["primary"]} !important; }}
    .stNumberInput input {{ background-color: {T["bg"]} !important; border: 1px solid {T["borderHi"]} !important; border-radius: 8px !important; color: {T["text"]} !important; font-family: 'JetBrains Mono', monospace !important; font-weight: 600; }}
    .stNumberInput input:focus {{ border-color: {T["primary"]} !important; box-shadow: 0 0 0 1px {T["primary"]} !important; }}
    
    /* Benchmarks & Helpers */
    .benchmark-box {{ background: {T["primaryFaint"]}; border: 1px solid rgba(37,99,235,0.2); border-left: 4px solid {T["primary"]}; border-radius: 8px; padding: 12px 16px; margin-top: 14px; font-size: 0.85rem; color: {T["textMuted"]}; line-height: 1.5; }}
    hr {{ border-color: {T["border"]}; margin: 2rem 0; }}
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 2. CALC ENGINE
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
    if age
