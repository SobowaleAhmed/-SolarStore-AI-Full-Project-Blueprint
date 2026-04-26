# app/tabs/solar_forecast.py
# ─────────────────────────────────────────────────────────────
# SolarStore AI — Tab 1: Solar Forecast
# ─────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.utils import (
    NIGERIAN_CITIES, PLOTLY_THEME, ACCENT, ACCENT2, DANGER,
    load_solar_data, load_xgb_model,
    fetch_live_weather, estimate_irradiance,
    section_header, metric_card, badge,
)


def render():
    # ── Sidebar controls ──────────────────────────────────────
    with st.sidebar:
        st.markdown("### ☀️ Solar Settings")
        city = st.selectbox(
            "Select City",
            options=list(NIGERIAN_CITIES.keys()),
            index=0,
        )
        panel_kw = st.slider(
            "Solar Panel Size (kWp)", 1.0, 20.0, 5.0, 0.5,
            help="Kilowatt-peak rating of your solar installation",
        )
        efficiency = st.slider(
            "Panel Efficiency (%)", 15, 22, 18,
            help="Modern panels: 18-22%. Standard: 15-17%.",
        )
        api_key = st.text_input(
            "OpenWeatherMap API Key",
            type="password",
            value="",
            placeholder="Paste your API key here",
        )
        fetch_live = st.button("🔄 Fetch Live Weather", use_container_width=True)

    # ── Load data & models ────────────────────────────────────
    df = load_solar_data()
    city_info = NIGERIAN_CITIES[city]

    # ── Live weather section ──────────────────────────────────
    section_header("Live Weather Conditions")

    live_weather = None
    if fetch_live and api_key:
        with st.spinner(f"Fetching live weather for {city}..."):
            live_weather = fetch_live_weather(city, api_key)

    if live_weather and "error" not in live_weather:
        c1, c2, c3, c4, c5 = st.columns(5)
        est_irr = estimate_irradiance(live_weather["cloud_cover_pct"])
        with c1:
            st.markdown(metric_card("Temperature", f"{live_weather['temperature_c']:.1f}", "°C"), unsafe_allow_html=True)
        with c2:
            st.markdown(metric_card("Cloud Cover", f"{live_weather['cloud_cover_pct']}", "%"), unsafe_allow_html=True)
        with c3:
            st.markdown(metric_card("Humidity", f"{live_weather['humidity_pct']}", "%"), unsafe_allow_html=True)
        with c4:
            st.markdown(metric_card("Wind Speed", f"{live_weather['wind_speed_ms']:.1f}", "m/s"), unsafe_allow_html=True)
        with c5:
            irr_color = ACCENT2 if est_irr > 3.5 else (ACCENT if est_irr > 2.0 else DANGER)
            st.markdown(metric_card("Est. Irradiance", f"{est_irr}", "kWh/m²/day", irr_color), unsafe_allow_html=True)

        st.markdown(
            f"**Conditions:** {live_weather['weather_description']} &nbsp;|&nbsp; "
            f"Est. daily output: **{round(est_irr * panel_kw * efficiency/100, 2)} kWh** "
            f"for a {panel_kw} kWp system",
            unsafe_allow_html=True,
        )
    elif fetch_live and not api_key:
        st.warning("Please enter your OpenWeatherMap API key in the sidebar.")
    else:
        # Show placeholder from historical average
        city_avg = df[df["city"] == city]["solar_irradiance_kwh_m2_day"].mean()
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(metric_card("5-Year Avg Irradiance", f"{city_avg:.2f}", "kWh/m²/day", ACCENT2), unsafe_allow_html=True)
        with c2:
            zone_label = city_info["zone"]
            st.markdown(metric_card("Zone", zone_label, ""), unsafe_allow_html=True)
        with c3:
            avg_daily_kwh = round(city_avg * panel_kw * efficiency / 100, 2)
            st.markdown(metric_card("Est. Daily Output", f"{avg_daily_kwh}", f"kWh (for {panel_kw} kWp)", ACCENT), unsafe_allow_html=True)
        st.info("Enter your OpenWeatherMap API key and click 'Fetch Live Weather' for real-time data.")

    # ── Historical irradiance patterns ────────────────────────
    section_header("Historical Solar Irradiance")

    city_df = df[df["city"] == city].copy().sort_values("date")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        # Time series with rolling mean
        rolling = city_df["solar_irradiance_kwh_m2_day"].rolling(30, center=True).mean()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=city_df["date"], y=city_df["solar_irradiance_kwh_m2_day"],
            mode="lines", name="Daily",
            line=dict(color=ACCENT2, width=0.7), opacity=0.35,
        ))
        fig.add_trace(go.Scatter(
            x=city_df["date"], y=rolling,
            mode="lines", name="30-day avg",
            line=dict(color=ACCENT, width=2.5),
        ))
        fig.update_layout(
            title=f"{city} — Daily Solar Irradiance (2020–2024)",
            xaxis_title="Date",
            yaxis_title="kWh/m²/day",
            legend=dict(orientation="h", y=1.1),
            height=320,
            **PLOTLY_THEME,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # Monthly average bar chart
        monthly = (
            city_df.groupby("month")["solar_irradiance_kwh_m2_day"]
            .mean().reset_index()
        )
        month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"]
        monthly["month_name"] = monthly["month"].apply(lambda x: month_names[x-1])

        fig2 = go.Figure(go.Bar(
            x=monthly["month_name"],
            y=monthly["solar_irradiance_kwh_m2_day"].round(2),
            marker_color=[
                DANGER if v < monthly["solar_irradiance_kwh_m2_day"].quantile(0.33)
                else (ACCENT if v < monthly["solar_irradiance_kwh_m2_day"].quantile(0.66)
                else ACCENT2)
                for v in monthly["solar_irradiance_kwh_m2_day"]
            ],
            text=monthly["solar_irradiance_kwh_m2_day"].round(2),
            textposition="auto",
        ))
        fig2.update_layout(
            title="Monthly Average",
            xaxis_title="Month",
            yaxis_title="kWh/m²/day",
            height=320,
            **PLOTLY_THEME,
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── XGBoost 30-day forecast ───────────────────────────────
    section_header("30-Day Forecast (XGBoost Model)")

    try:
        xgb_model, feature_cols, le_city, le_zone = load_xgb_model()

        # Build forecast features for next 30 days
        last_date  = city_df["date"].max()
        last_row   = city_df.iloc[-1]
        recent_irr = city_df["solar_irradiance_kwh_m2_day"].values

        forecast_rows = []
        for i in range(1, 31):
            future_date = last_date + pd.Timedelta(days=i)
            month       = future_date.month
            doy         = future_date.dayofyear
            row = {
                "clear_sky_irradiance_kwh_m2_day": last_row["clear_sky_irradiance_kwh_m2_day"],
                "temperature_2m_c":  last_row["temperature_2m_c"],
                "humidity_pct":      last_row["humidity_pct"],
                "cloud_cover_pct":   last_row["cloud_cover_pct"],
                "wind_speed_2m_ms":  last_row["wind_speed_2m_ms"],
                "precipitation_mm_day": 0,
                "month":       month,
                "day_of_year": doy,
                "quarter":     (month - 1) // 3 + 1,
                "year":        future_date.year,
                "month_sin":   np.sin(2 * np.pi * month / 12),
                "month_cos":   np.cos(2 * np.pi * month / 12),
                "doy_sin":     np.sin(2 * np.pi * doy / 365),
                "doy_cos":     np.cos(2 * np.pi * doy / 365),
                "irr_lag_1":   recent_irr[-1]  if len(recent_irr) >= 1 else 4.0,
                "irr_lag_2":   recent_irr[-2]  if len(recent_irr) >= 2 else 4.0,
                "irr_lag_3":   recent_irr[-3]  if len(recent_irr) >= 3 else 4.0,
                "irr_lag_7":   recent_irr[-7]  if len(recent_irr) >= 7 else 4.0,
                "irr_lag_14":  recent_irr[-14] if len(recent_irr) >= 14 else 4.0,
                "irr_lag_30":  recent_irr[-30] if len(recent_irr) >= 30 else 4.0,
                "irr_roll_7d":  np.mean(recent_irr[-7:]),
                "irr_roll_14d": np.mean(recent_irr[-14:]),
                "irr_roll_30d": np.mean(recent_irr[-30:]),
                "cloud_roll_7d":  last_row["cloud_cover_pct"],
                "cloud_roll_14d": last_row["cloud_cover_pct"],
                "cloud_roll_30d": last_row["cloud_cover_pct"],
                "city_enc": int(le_city.transform([city])[0]),
                "zone_enc": int(le_zone.transform([city_info["zone"]])[0]),
            }
            forecast_rows.append(row)

        forecast_df      = pd.DataFrame(forecast_rows)[feature_cols]
        forecast_irr     = xgb_model.predict(forecast_df)
        forecast_dates   = [last_date + pd.Timedelta(days=i) for i in range(1, 31)]
        forecast_kwh     = [round(v * panel_kw * efficiency / 100, 2) for v in forecast_irr]

        # Plot forecast
        fig3 = go.Figure()
        # Historical (last 60 days)
        hist_60 = city_df.tail(60)
        fig3.add_trace(go.Scatter(
            x=hist_60["date"],
            y=hist_60["solar_irradiance_kwh_m2_day"],
            mode="lines", name="Historical",
            line=dict(color=ACCENT2, width=1.5),
        ))
        # Forecast
        fig3.add_trace(go.Scatter(
            x=forecast_dates, y=list(forecast_irr),
            mode="lines+markers", name="30-Day Forecast",
            line=dict(color=ACCENT, width=2, dash="dot"),
            marker=dict(size=5),
        ))
        # Confidence band (±15%)
        upper = [v * 1.15 for v in forecast_irr]
        lower = [v * 0.85 for v in forecast_irr]
        fig3.add_trace(go.Scatter(
            x=forecast_dates + forecast_dates[::-1],
            y=upper + lower[::-1],
            fill="toself", fillcolor="rgba(247,183,49,0.08)",
            line=dict(color="rgba(0,0,0,0)"),
            name="±15% confidence",
        ))
        fig3.add_vline(
            x=str(last_date), line_dash="dash",
            line_color="#30363D", line_width=1,
            annotation_text="Forecast start",
            annotation_font_color="#8B949E",
        )
        fig3.update_layout(
            title=f"{city} — 30-Day Solar Irradiance Forecast (XGBoost)",
            xaxis_title="Date",
            yaxis_title="kWh/m²/day",
            legend=dict(orientation="h", y=1.1),
            height=340,
            **PLOTLY_THEME,
        )
        st.plotly_chart(fig3, use_container_width=True)

        # Summary metrics
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(metric_card("Avg Forecast Irradiance", f"{np.mean(forecast_irr):.2f}", "kWh/m²/day", ACCENT2), unsafe_allow_html=True)
        with c2:
            st.markdown(metric_card("Total Est. Generation", f"{sum(forecast_kwh):.1f}", f"kWh over 30 days", ACCENT), unsafe_allow_html=True)
        with c3:
            best_day = forecast_dates[int(np.argmax(forecast_irr))]
            st.markdown(metric_card("Best Day", str(best_day.date()), f"{max(forecast_irr):.2f} kWh/m²/day"), unsafe_allow_html=True)
        with c4:
            worst_day = forecast_dates[int(np.argmin(forecast_irr))]
            st.markdown(metric_card("Lowest Day", str(worst_day.date()), f"{min(forecast_irr):.2f} kWh/m²/day", DANGER), unsafe_allow_html=True)

    except Exception as e:
        st.warning(f"Model not loaded yet. Run Phase 4 notebook first. ({e})")

    # ── Nigeria solar map ─────────────────────────────────────
    section_header("Nigeria Solar Potential Map")

    city_avgs = (
        df.groupby(["city", "zone"])["solar_irradiance_kwh_m2_day"]
        .mean().reset_index()
    )
    city_avgs["lat"] = city_avgs["city"].map(lambda c: NIGERIAN_CITIES[c]["lat"])
    city_avgs["lon"] = city_avgs["city"].map(lambda c: NIGERIAN_CITIES[c]["lon"])

    fig_map = go.Figure(go.Scattergeo(
        lat=city_avgs["lat"],
        lon=city_avgs["lon"],
        text=city_avgs.apply(
            lambda r: f"{r['city']}<br>{r['solar_irradiance_kwh_m2_day']:.2f} kWh/m²/day", axis=1
        ),
        mode="markers+text",
        textposition="top center",
        marker=dict(
            size=city_avgs["solar_irradiance_kwh_m2_day"] * 4,
            color=city_avgs["solar_irradiance_kwh_m2_day"],
            colorscale="YlOrRd",
            showscale=True,
            colorbar=dict(title="kWh/m²/day", tickfont=dict(color="#E6EDF3")),
            line=dict(color="#0D1117", width=1),
        ),
        textfont=dict(size=9, color="#E6EDF3"),
    ))
    fig_map.update_layout(
        geo=dict(
            scope="africa",
            center=dict(lat=9.0, lon=8.0),
            projection_scale=6,
            showland=True, landcolor="#21262D",
            showocean=True, oceancolor="#161B22",
            showlakes=False,
            showcountries=True, countrycolor="#30363D",
            bgcolor="#0D1117",
        ),
        height=420,
        **PLOTLY_THEME,
        title="Average Solar Irradiance — Nigerian Cities (2020–2024)",
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_map, use_container_width=True)
