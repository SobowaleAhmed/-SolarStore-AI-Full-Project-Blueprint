# app/utils.py
# ─────────────────────────────────────────────────────────────
# SolarStore AI — Shared App Utilities
# ─────────────────────────────────────────────────────────────

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import joblib
import os
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parents[1]
DATA_DIR  = ROOT / "data" / "raw"
MODEL_DIR = ROOT / "models"

# ── Plot theme — dark, consistent with app CSS ─────────────────
PLOTLY_THEME = dict(
    template   = "plotly_dark",
    paper_bgcolor = "#0D1117",
    plot_bgcolor  = "#161B22",
    font = dict(family="DM Sans", color="#E6EDF3"),
    margin = dict(l=40, r=20, t=50, b=40),
)

ACCENT  = "#F7B731"
ACCENT2 = "#2A9D8F"
DANGER  = "#E63946"

# ── City config ───────────────────────────────────────────────
NIGERIAN_CITIES = {
    "Lagos":         {"lat": 6.5244,  "lon": 3.3792,  "state": "Lagos",       "zone": "South West"},
    "Ibadan":        {"lat": 7.3776,  "lon": 3.9470,  "state": "Oyo",         "zone": "South West"},
    "Abeokuta":      {"lat": 7.1475,  "lon": 3.3619,  "state": "Ogun",        "zone": "South West"},
    "Akure":         {"lat": 7.2526,  "lon": 5.1931,  "state": "Ondo",        "zone": "South West"},
    "Awka":          {"lat": 6.2104,  "lon": 7.0678,  "state": "Anambra",     "zone": "South East"},
    "Enugu":         {"lat": 6.4698,  "lon": 7.5093,  "state": "Enugu",       "zone": "South East"},
    "Owerri":        {"lat": 5.4836,  "lon": 7.0333,  "state": "Imo",         "zone": "South East"},
    "Port Harcourt": {"lat": 4.8156,  "lon": 7.0498,  "state": "Rivers",      "zone": "South South"},
    "Benin City":    {"lat": 6.3350,  "lon": 5.6037,  "state": "Edo",         "zone": "South South"},
    "Calabar":       {"lat": 4.9517,  "lon": 8.3220,  "state": "Cross River", "zone": "South South"},
    "Abuja":         {"lat": 9.0765,  "lon": 7.3986,  "state": "FCT",         "zone": "North Central"},
    "Lokoja":        {"lat": 7.7961,  "lon": 6.7370,  "state": "Kogi",        "zone": "North Central"},
    "Ilorin":        {"lat": 8.4966,  "lon": 4.5426,  "state": "Kwara",       "zone": "North Central"},
    "Kano":          {"lat": 12.0022, "lon": 8.5920,  "state": "Kano",        "zone": "North West"},
    "Kaduna":        {"lat": 10.5222, "lon": 7.4383,  "state": "Kaduna",      "zone": "North West"},
    "Sokoto":        {"lat": 13.0059, "lon": 5.2476,  "state": "Sokoto",      "zone": "North West"},
    "Maiduguri":     {"lat": 11.8333, "lon": 13.1500, "state": "Borno",       "zone": "North East"},
    "Bauchi":        {"lat": 10.3158, "lon": 9.8442,  "state": "Bauchi",      "zone": "North East"},
    "Yola":          {"lat": 9.2035,  "lon": 12.4954, "state": "Adamawa",     "zone": "North East"},
}

# ── Load historical solar data ─────────────────────────────────
@st.cache_data
def load_solar_data():
    path = DATA_DIR / "all_cities_solar_data.csv"
    df = pd.read_csv(path, parse_dates=["date"])
    df["month"]       = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear
    df["month_sin"]   = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"]   = np.cos(2 * np.pi * df["month"] / 12)
    df["doy_sin"]     = np.sin(2 * np.pi * df["day_of_year"] / 365)
    df["doy_cos"]     = np.cos(2 * np.pi * df["day_of_year"] / 365)
    return df

# ── Load battery cycle data ────────────────────────────────────
@st.cache_data
def load_battery_data():
    path = DATA_DIR / "battery" / "all_batteries_cycles.csv"
    return pd.read_csv(path)

# ── Load XGBoost model ─────────────────────────────────────────
@st.cache_resource
def load_xgb_model():
    import xgboost as xgb
    model = xgb.XGBRegressor()
    model.load_model(str(MODEL_DIR / "xgboost_solar.json"))
    feature_cols = joblib.load(MODEL_DIR / "xgb_feature_cols.pkl")
    le_city      = joblib.load(MODEL_DIR / "label_encoder_city.pkl")
    le_zone      = joblib.load(MODEL_DIR / "label_encoder_zone.pkl")
    return model, feature_cols, le_city, le_zone

# ── Load battery scaler & isolation forest ────────────────────
@st.cache_resource
def load_battery_models():
    scaler     = joblib.load(MODEL_DIR / "battery_scaler_X.pkl")
    iso        = joblib.load(MODEL_DIR / "isolation_forest.pkl")
    features   = joblib.load(MODEL_DIR / "battery_dnn_features.pkl")
    anom_feats = joblib.load(MODEL_DIR / "anomaly_features.pkl")
    return scaler, iso, features, anom_feats

# ── Fetch live weather (OpenWeatherMap) ───────────────────────
def fetch_live_weather(city_name: str, api_key: str) -> dict:
    import requests
    city = NIGERIAN_CITIES[city_name]
    url  = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": city["lat"], "lon": city["lon"],
        "appid": api_key, "units": "metric",
    }
    try:
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        raw = r.json()
        return {
            "temperature_c":       raw["main"]["temp"],
            "humidity_pct":        raw["main"]["humidity"],
            "cloud_cover_pct":     raw["clouds"]["all"],
            "wind_speed_ms":       raw["wind"]["speed"],
            "weather_description": raw["weather"][0]["description"].title(),
            "weather_icon":        raw["weather"][0]["icon"],
        }
    except Exception as e:
        return {"error": str(e)}

# ── Estimate solar irradiance from weather ────────────────────
def estimate_irradiance(cloud_pct: float, clear_sky_base: float = 5.5) -> float:
    """Simple heuristic: reduce clear-sky irradiance by cloud factor."""
    cloud_factor = 1 - (cloud_pct / 100) * 0.75
    return round(clear_sky_base * cloud_factor, 2)

# ── Predict SoH from inputs (DNN proxy using historical data) ──
def predict_soh(cycle_number: int, temperature_c: float,
                internal_resistance: float, capacity_loss_pct: float) -> dict:
    """
    Simplified SoH predictor using the exponential degradation model.
    In production this calls the PyTorch DNN.
    SoH = exp(-alpha * n) where alpha depends on temperature.
    """
    import math
    # Temperature-adjusted alpha (Arrhenius: doubles every 10°C above 25°C)
    base_alpha = 0.00085
    temp_factor = 2 ** ((temperature_c - 25) / 10)
    alpha = base_alpha * temp_factor

    soh = math.exp(-alpha * cycle_number)
    soh = max(0.0, min(1.0, soh))

    # RUL: cycles until SoH = 0.70
    if soh > 0.70:
        rul = int((-math.log(0.70) / alpha) - cycle_number)
    else:
        rul = 0

    # Health category
    if soh >= 0.90:
        category, badge = "Excellent", "good"
    elif soh >= 0.80:
        category, badge = "Good", "good"
    elif soh >= 0.70:
        category, badge = "Fair — Monitor Closely", "warning"
    else:
        category, badge = "End of Life Reached", "danger"

    return {
        "soh":      round(soh, 4),
        "soh_pct":  round(soh * 100, 2),
        "rul":      max(0, rul),
        "category": category,
        "badge":    badge,
        "alpha":    round(alpha, 6),
    }

# ── SoH gauge chart ───────────────────────────────────────────
def soh_gauge(soh_pct: float) -> go.Figure:
    color = ACCENT2 if soh_pct >= 80 else (ACCENT if soh_pct >= 70 else DANGER)
    fig = go.Figure(go.Indicator(
        mode  = "gauge+number+delta",
        value = soh_pct,
        delta = {"reference": 100, "suffix": "%"},
        title = {"text": "State of Health", "font": {"size": 14, "color": "#8B949E"}},
        number= {"suffix": "%", "font": {"size": 40, "color": color}},
        gauge = {
            "axis":  {"range": [0, 100], "tickcolor": "#8B949E"},
            "bar":   {"color": color, "thickness": 0.25},
            "bgcolor": "#21262D",
            "bordercolor": "#30363D",
            "steps": [
                {"range": [0, 70],  "color": "rgba(230,57,70,0.15)"},
                {"range": [70, 80], "color": "rgba(247,183,49,0.15)"},
                {"range": [80, 100],"color": "rgba(42,157,143,0.15)"},
            ],
            "threshold": {
                "line": {"color": DANGER, "width": 2},
                "thickness": 0.8,
                "value": 70,
            },
        },
    ))
    fig.update_layout(
        height=280,
        **PLOTLY_THEME,
        margin=dict(l=20, r=20, t=40, b=10),
    )
    return fig

# ── Degradation curve chart ───────────────────────────────────
def degradation_curve(current_cycle: int, alpha: float) -> go.Figure:
    import math
    cycles = np.arange(0, max(200, current_cycle + 50))
    soh_curve = [math.exp(-alpha * n) * 100 for n in cycles]

    eol_cycle = int(-math.log(0.70) / alpha) if alpha > 0 else 999

    fig = go.Figure()

    # Full degradation curve
    fig.add_trace(go.Scatter(
        x=cycles, y=soh_curve,
        mode="lines", name="Projected SoH",
        line=dict(color=ACCENT2, width=2.5),
        fill="tozeroy",
        fillcolor="rgba(42,157,143,0.08)",
    ))

    # Current position
    current_soh = math.exp(-alpha * current_cycle) * 100
    fig.add_trace(go.Scatter(
        x=[current_cycle], y=[current_soh],
        mode="markers", name="Current",
        marker=dict(color=ACCENT, size=12, symbol="circle",
                    line=dict(color="#0D1117", width=2)),
    ))

    # EoL line
    fig.add_hline(y=70, line_dash="dash", line_color=DANGER,
                  line_width=1.5, annotation_text="End of Life (70%)",
                  annotation_font_color=DANGER)

    # EoL vertical
    if eol_cycle < max(cycles):
        fig.add_vline(x=eol_cycle, line_dash="dot", line_color=DANGER,
                      line_width=1, opacity=0.5)

    fig.update_layout(
        title=dict(text="Projected Degradation Curve", font=dict(size=13)),
        xaxis_title="Cycle Number",
        yaxis_title="State of Health (%)",
        yaxis=dict(range=[50, 105]),
        legend=dict(orientation="h", y=1.1),
        height=320,
        **PLOTLY_THEME,
    )
    return fig

# ── Metric card HTML ──────────────────────────────────────────
def metric_card(label: str, value: str, unit: str = "", color: str = "#E6EDF3") -> str:
    return f"""
    <div class="metric-card">
        <div class="label">{label}</div>
        <div class="value" style="color:{color}">{value}</div>
        <div class="unit">{unit}</div>
    </div>
    """

def badge(text: str, kind: str = "good") -> str:
    return f'<span class="badge badge-{kind}">{text}</span>'

def section_header(text: str) -> None:
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)

def rec_card(title: str, body: str, warning: bool = False) -> str:
    cls = "rec-card warning" if warning else "rec-card"
    return f"""
    <div class="{cls}">
        <div class="rec-title">{title}</div>
        <div class="rec-body">{body}</div>
    </div>
    """
