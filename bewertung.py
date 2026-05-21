import streamlit as st
import pandas as pd
import altair as alt
import math

st.set_page_config(page_title="YieldBase v2 | Gold Analytics", layout="wide", initial_sidebar_state="collapsed")

# ─────────────────────────────────────────────────────────────────────────────
# 1. DESIGN TOKENS (Modern Luxury / Gold Theme)
# ─────────────────────────────────────────────────────────────────────────────
T = {
    "bg": "#fcfcfc", "surface": "#ffffff", "surface2": "#f8f9fa", "surface3": "#f1f5f9",
    "border": "#e2e8f0", "borderHi": "#cbd5e1", "gold": "#c9a84c", "goldFaint": "rgba(201,168,76,0.08)",
    "green": "#059669", "yellow": "#d97706", "red": "#dc2626", "primary": "#1e293b",
    "text": "#1e293b", "textMuted": "#64748b", "textDim": "#94a3b8"
}

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');

    .stApp {{ background-color: {T["bg"]}; color: {T["text"]}; font-family: 'Outfit', sans-serif; }}
    
    /* Layout & Cards */
    .saas-card {{ background-color: {T["surface"]}; border: 1px solid {T["border"]}; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03); }}
    .saas-card-header {{ font-weight: 600; font-size: 1.1rem; color: {T["text"]}; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }}
    .saas-card-header span {{ color: {T["gold"]}; }}
    
    /* KPI Metric Cards */
    .kpi-box {{ background: {T["surface"]}; border: 1px solid {T["border"]}; border-radius: 10px; padding: 18px; position: relative; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,0.03); }}
    .kpi-title {{ font-size: 0.7rem; color: {T["textDim"]}; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; margin-bottom: 4px; }}
    .kpi-value {{ font-family: 'JetBrains Mono', monospace; font-size: 1.35rem; font-weight: 700; color: {T["text"]}; }}
    .kpi-sub {{ font-size: 0.7rem; color: {T["textMuted"]}; margin-top: 4px; }}
    .ampel-badge {{ position: absolute; top: 10px; right: 10px; font-size: 0.6rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; }}
    
    /* Native Overrides */
    div[data-testid="stTabs"] button {{ color: {T["textMuted"]}; font-size: 0.9rem; font-weight: 500; }}
    div[data-testid="stTabs"] button[aria-selected="true"] {{ color: {T["gold"]}; border-bottom-color: {T["gold"]}; font-weight: 600; }}
    .stSlider > div > div > div > div {{ background-color: {T["gold"]} !important; }}
    
    .benchmark-box {{ background: {T["goldFaint"]}; border: 1px solid {T["gold"]}30; border-left: 4px solid {T["gold"]}; border-radius: 6px; padding: 12px; margin-top: 10px; font-size: 0.85rem; color: {T["textMuted"]}; }}
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 2. CALC ENGINE (Logik bleibt identisch)
# ─────────────────────────────────────────────────────────────────────────────
# [Hinweis: Hier bleibt deine bisherige Logik exakt gleich, ich habe sie der Übersicht halber hier verkürzt eingefügt]
def fmt_eur(v): return f"{v:,.0f} €".replace(",", ".") if isinstance(v, (int, float)) else "—"
def fmt_pct(v): return f"{v:.2f} %".replace(".", ",") if isinstance(v, (int, float)) else "—"
def fmt_x(v): return f"{v:.1f}x".replace(".", ",") if isinstance(v, (int, float)) else "> 99x"
def fmt_yr(v): return f"{v:.1f} J." if v else "n.v."

def calc_all(inp):
    # (Deine Logik aus dem vorherigen Code bleibt hier 1:1 bestehen)
    # Ich habe die Funktion hier implizit als gegeben vorausgesetzt
    pass

# Da ich den Code hier aus Platzgründen nicht 600 Zeilen wiederhole, 
# setze bitte hier einfach deine bestehende `calc_all`, `calc_scenario` und `calc_ihr` Funktionen ein!
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 3. LAYOUT & UI
# ─────────────────────────────────────────────────────────────────────────────
# Stelle sicher, dass `res` und `inp` hier definiert sind wie vorher.

# Beispiel für die Anzeige der Investment Summary im "Gold"-Design:
def render_gold_summary(res, inp):
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {T['surface']} 0%, #ffffff 100%); border: 1px solid {T['border']}; border-radius: 16px; padding: 36px; margin-bottom: 20px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05);">
        <div style="font-weight: 700; font-size: 2.2rem; color: {T['text']}; margin-bottom: 4px; letter-spacing: -0.02em;">Investment Summary</div>
        <div style="font-size: 0.95rem; color: {T['textDim']}; margin-bottom: 30px;">YieldBase Analytics v2</div>
        
        <div style="display: flex; gap: 24px; margin-bottom: 30px;">
            <div style="background: {T['surface2']}; border-radius: 12px; padding: 20px; flex: 1; border: 1px solid {T['border']};">
                <div style="font-size: 0.75rem; color: {T['textDim']}; text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Gesamtinvestition</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 1.8rem; font-weight: 700; color: {T['gold']};">{fmt_eur(res['gesamt'])}</div>
            </div>
            <div style="background: {T['surface2']}; border-radius: 12px; padding: 20px; flex: 1; border: 1px solid {T['border']};">
                <div style="font-size: 0.75rem; color: {T['textDim']}; text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Jahresmiete (Brutto)</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 1.8rem; font-weight: 700; color: {T['gold']};">{fmt_eur(inp['jahresmiete'])}</div>
            </div>
        </div>
        
        <div style="background: {T['goldFaint']}; border-radius: 12px; padding: 20px; font-size: 1.05rem; line-height: 1.6; color: {T['textMuted']}; border-left: 4px solid {T['gold']};">
            <strong style="color: {T['text']}; font-weight: 600;">Analyse:</strong> Bei einem Kaufpreis von <strong style="color: {T['gold']}">{fmt_eur(inp['kaufpreis'])}</strong> und einer 
            Jahresnettomiete von <strong style="color: {T['gold']}">{fmt_eur(inp['jahresmiete'])}</strong> ergibt sich ein 
            Kaufpreisfaktor von <strong style="color: {T['text']}">{fmt_x(res['faktor'])}</strong>.
        </div>
    </div>
    """, unsafe_allow_html=True)
