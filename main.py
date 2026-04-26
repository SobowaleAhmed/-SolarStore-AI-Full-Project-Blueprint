# app/main.py
# ─────────────────────────────────────────────────────────────
# SolarStore AI — Streamlit Dashboard Entry Point
# ─────────────────────────────────────────────────────────────
# Run with: streamlit run app/main.py
# ─────────────────────────────────────────────────────────────

import streamlit as st

# ── Page config — must be first Streamlit call ────────────────
st.set_page_config(
    page_title   = "SolarStore AI",
    page_icon    = "⚡",
    layout       = "wide",
    initial_sidebar_state = "expanded",
)

# ── Inject custom CSS ─────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── CSS Variables ── */
:root {
    --bg:         #0D1117;
    --surface:    #161B22;
    --surface2:   #21262D;
    --border:     #30363D;
    --accent:     #F7B731;
    --accent2:    #2A9D8F;
    --danger:     #E63946;
    --text:       #E6EDF3;
    --muted:      #8B949E;
    --font-mono:  'Space Mono', monospace;
    --font-body:  'DM Sans', sans-serif;
}

/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--font-body) !important;
}

[data-testid="stSidebar"] {
    background-color: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

/* ── Header bar ── */
.top-bar {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px 0 24px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 28px;
}
.top-bar .logo {
    font-family: var(--font-mono);
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: -1px;
}
.top-bar .tagline {
    font-size: 0.85rem;
    color: var(--muted);
    font-weight: 300;
}

/* ── Metric cards ── */
.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 18px 22px;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: var(--accent); }
.metric-card .label {
    font-size: 0.72rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    font-family: var(--font-mono);
    margin-bottom: 6px;
}
.metric-card .value {
    font-size: 1.8rem;
    font-weight: 600;
    color: var(--text);
    line-height: 1;
}
.metric-card .unit {
    font-size: 0.8rem;
    color: var(--muted);
    margin-top: 4px;
}

/* ── Section headers ── */
.section-header {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin: 28px 0 14px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

/* ── Status badges ── */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-family: var(--font-mono);
    font-weight: 700;
    letter-spacing: 0.5px;
}
.badge-good    { background: rgba(42,157,143,0.15); color: #2A9D8F; border: 1px solid #2A9D8F; }
.badge-warning { background: rgba(247,183,49,0.15); color: #F7B731; border: 1px solid #F7B731; }
.badge-danger  { background: rgba(230,57,70,0.15);  color: #E63946; border: 1px solid #E63946; }

/* ── SoH gauge label ── */
.soh-label {
    font-family: var(--font-mono);
    font-size: 2.8rem;
    font-weight: 700;
    text-align: center;
    padding: 20px;
}

/* ── Recommendation cards ── */
.rec-card {
    background: var(--surface);
    border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0;
    padding: 14px 18px;
    margin-bottom: 12px;
}
.rec-card.warning { border-left-color: var(--danger); }
.rec-card .rec-title {
    font-weight: 600;
    font-size: 0.9rem;
    margin-bottom: 4px;
}
.rec-card .rec-body {
    font-size: 0.82rem;
    color: var(--muted);
    line-height: 1.5;
}

/* ── Tab styling ── */
[data-testid="stTabs"] button {
    font-family: var(--font-mono) !important;
    font-size: 0.75rem !important;
    letter-spacing: 1px !important;
}

/* ── Selectbox & sliders ── */
[data-testid="stSelectbox"] label,
[data-testid="stSlider"] label {
    font-family: var(--font-mono) !important;
    font-size: 0.72rem !important;
    color: var(--muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}

/* ── Plotly charts dark bg ── */
.js-plotly-plot { border-radius: 10px; }

/* ── Hide Streamlit default elements ── */
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
st.markdown("""
<div class="top-bar">
    <div>
        <div class="logo">⚡ SOLARSTORE AI</div>
        <div class="tagline">Solar Generation Forecasting · Battery Health Intelligence · Nigeria</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "☀️  SOLAR FORECAST",
    "🔋  BATTERY HEALTH",
    "📊  COMBINED DASHBOARD",
    "💡  RECOMMENDATIONS",
])

# Import tab modules
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tabs.solar_forecast    import render as render_solar
from app.tabs.battery_health    import render as render_battery
from app.tabs.combined_dashboard import render as render_combined
from app.tabs.recommendations   import render as render_recs

with tab1: render_solar()
with tab2: render_battery()
with tab3: render_combined()
with tab4: render_recs()
