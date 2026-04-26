# app/main.py
import streamlit as st
import sys, os

st.set_page_config(
    page_title="SolarStore AI", page_icon="⚡",
    layout="wide", initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
:root {
    --bg:#0D1117;--surface:#161B22;--border:#30363D;
    --accent:#F7B731;--accent2:#2A9D8F;--danger:#E63946;
    --text:#E6EDF3;--muted:#8B949E;
    --font-mono:'Space Mono',monospace;--font-body:'DM Sans',sans-serif;
}
html,body,[data-testid="stAppViewContainer"]{background-color:var(--bg)!important;color:var(--text)!important;font-family:var(--font-body)!important;}
[data-testid="stSidebar"]{background-color:var(--surface)!important;border-right:1px solid var(--border)!important;}
.metric-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px 22px;margin-bottom:8px;}
.metric-card .label{font-size:0.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:1px;font-family:var(--font-mono);margin-bottom:6px;}
.metric-card .value{font-size:1.8rem;font-weight:600;color:var(--text);}
.metric-card .unit{font-size:0.8rem;color:var(--muted);margin-top:4px;}
.section-header{font-family:var(--font-mono);font-size:0.75rem;color:var(--accent);text-transform:uppercase;letter-spacing:2px;margin:28px 0 14px 0;padding-bottom:8px;border-bottom:1px solid var(--border);}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.72rem;font-family:var(--font-mono);font-weight:700;}
.badge-good{background:rgba(42,157,143,0.15);color:#2A9D8F;border:1px solid #2A9D8F;}
.badge-warning{background:rgba(247,183,49,0.15);color:#F7B731;border:1px solid #F7B731;}
.badge-danger{background:rgba(230,57,70,0.15);color:#E63946;border:1px solid #E63946;}
.rec-card{background:var(--surface);border-left:3px solid var(--accent);border-radius:0 8px 8px 0;padding:14px 18px;margin-bottom:12px;}
.rec-card.warning{border-left-color:var(--danger);}
.rec-card .rec-title{font-weight:600;font-size:0.9rem;margin-bottom:4px;}
.rec-card .rec-body{font-size:0.82rem;color:var(--muted);line-height:1.5;}
#MainMenu,footer,[data-testid="stToolbar"]{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style='display:flex;align-items:center;gap:14px;padding:18px 0 24px 0;border-bottom:1px solid #30363D;margin-bottom:28px;'>
    <div>
        <div style='font-family:Space Mono,monospace;font-size:1.6rem;font-weight:700;color:#F7B731;letter-spacing:-1px;'>⚡ SOLARSTORE AI</div>
        <div style='font-size:0.85rem;color:#8B949E;font-weight:300;'>Solar Generation Forecasting · Battery Health Intelligence · Nigeria</div>
    </div>
</div>
""", unsafe_allow_html=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from app.startup import ensure_data_and_models
    ensure_data_and_models()
except Exception as e:
    st.warning(f"Startup: {e}")

tab1, tab2, tab3, tab4 = st.tabs([
    "☀️  SOLAR FORECAST",
    "🔋  BATTERY HEALTH",
    "📊  COMBINED DASHBOARD",
    "💡  RECOMMENDATIONS",
])

with tab1:
    try:
        from app.tabs.solar_forecast import render
        render()
    except Exception as e:
        st.error(f"Solar tab error: {e}")
        st.exception(e)

with tab2:
    try:
        from app.tabs.battery_health import render
        render()
    except Exception as e:
        st.error(f"Battery tab error: {e}")
        st.exception(e)

with tab3:
    try:
        from app.tabs.combined_dashboard import render
        render()
    except Exception as e:
        st.error(f"Dashboard tab error: {e}")
        st.exception(e)

with tab4:
    try:
        from app.tabs.recommendations import render
        render()
    except Exception as e:
        st.error(f"Recommendations tab error: {e}")
        st.exception(e)
