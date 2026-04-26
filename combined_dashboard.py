# app/tabs/combined_dashboard.py
# ─────────────────────────────────────────────────────────────
# SolarStore AI — Tab 3: Combined Dashboard
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
    load_solar_data, load_battery_data,
    predict_soh, section_header, metric_card, badge,
)


def render():

    section_header("Solar Generation vs Battery Storage — Nigeria Overview")

    # ── Load data ─────────────────────────────────────────────
    df_solar  = load_solar_data()
    df_batt   = load_battery_data()

    # ── National solar summary ────────────────────────────────
    city_avgs = (
        df_solar.groupby(["city", "zone"])["solar_irradiance_kwh_m2_day"]
        .mean().reset_index()
        .sort_values("solar_irradiance_kwh_m2_day", ascending=False)
    )
    city_avgs["lat"] = city_avgs["city"].map(lambda c: NIGERIAN_CITIES[c]["lat"])
    city_avgs["lon"] = city_avgs["city"].map(lambda c: NIGERIAN_CITIES[c]["lon"])

    national_avg  = city_avgs["solar_irradiance_kwh_m2_day"].mean()
    best_city     = city_avgs.iloc[0]
    worst_city    = city_avgs.iloc[-1]
    north_avg     = city_avgs[city_avgs["zone"].str.contains("North")]["solar_irradiance_kwh_m2_day"].mean()
    south_avg     = city_avgs[city_avgs["zone"].str.contains("South")]["solar_irradiance_kwh_m2_day"].mean()

    # ── Top metrics row ───────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(metric_card("National Avg", f"{national_avg:.2f}", "kWh/m²/day", ACCENT2), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("Best City", best_city["city"], f"{best_city['solar_irradiance_kwh_m2_day']:.2f} kWh/m²/day", ACCENT), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("North Avg", f"{north_avg:.2f}", "kWh/m²/day", ACCENT2), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card("South Avg", f"{south_avg:.2f}", "kWh/m²/day", DANGER), unsafe_allow_html=True)
    with c5:
        gap = ((north_avg / south_avg) - 1) * 100
        st.markdown(metric_card("N/S Gap", f"+{gap:.0f}%", "more sun in North", ACCENT), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1: Irradiance heatmap + Battery health overview ───
    col_left, col_right = st.columns([3, 2])

    with col_left:
        section_header("City × Month Irradiance Heatmap")

        month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"]
        pivot = (
            df_solar.groupby(["city", "month"])["solar_irradiance_kwh_m2_day"]
            .mean().unstack(level="month").round(2)
        )
        pivot.columns = month_names
        city_order = city_avgs["city"].tolist()
        pivot = pivot.loc[[c for c in city_order if c in pivot.index]]

        fig_heat = go.Figure(go.Heatmap(
            z=pivot.values,
            x=month_names,
            y=pivot.index.tolist(),
            colorscale="YlOrRd",
            text=pivot.values.round(2),
            texttemplate="%{text}",
            textfont=dict(size=9),
            colorbar=dict(title="kWh/m²/day", tickfont=dict(color="#E6EDF3")),
            zmin=1.0, zmax=7.0,
        ))
        fig_heat.update_layout(
            title="Average Solar Irradiance (kWh/m²/day) — All Cities",
            height=480,
            xaxis=dict(side="top"),
            **PLOTLY_THEME,
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    with col_right:
        section_header("Battery Fleet Health Overview")

        # Summary per battery
        batt_summary = df_batt.groupby("battery_id").agg(
            total_cycles = ("cycle_number",             "max"),
            final_soh    = ("state_of_health",          "last"),
            avg_temp     = ("temperature_c",            "mean"),
            final_resist = ("internal_resistance_mohm", "last"),
        ).reset_index().round(3)

        for _, row in batt_summary.iterrows():
            soh_pct  = row["final_soh"] * 100
            color    = ACCENT2 if soh_pct >= 80 else (ACCENT if soh_pct >= 70 else DANGER)
            bdg_kind = "good" if soh_pct >= 80 else ("warning" if soh_pct >= 70 else "danger")

            st.markdown(f"""
            <div class="metric-card" style="margin-bottom:10px">
                <div style="display:flex; justify-content:space-between; align-items:center">
                    <span style="font-family:var(--font-mono); font-weight:700;
                                 color:var(--text)">{row['battery_id']}</span>
                    <span class="badge badge-{bdg_kind}">{soh_pct:.1f}% SoH</span>
                </div>
                <div style="margin-top:10px; display:grid; grid-template-columns:1fr 1fr; gap:8px">
                    <div style="font-size:0.78rem; color:var(--muted)">
                        Cycles: <span style="color:var(--text)">{int(row['total_cycles'])}</span>
                    </div>
                    <div style="font-size:0.78rem; color:var(--muted)">
                        Avg Temp: <span style="color:var(--text)">{row['avg_temp']:.1f}°C</span>
                    </div>
                    <div style="font-size:0.78rem; color:var(--muted)">
                        Resistance: <span style="color:var(--text)">{row['final_resist']:.0f} mΩ</span>
                    </div>
                    <div style="font-size:0.78rem; color:var(--muted)">
                        Profile: <span style="color:var(--text)">{'🔥 High Temp' if row['avg_temp'] > 35 else '❄️ Room Temp'}</span>
                    </div>
                </div>
                <!-- SoH progress bar -->
                <div style="margin-top:10px; background:#21262D; border-radius:4px; height:6px; overflow:hidden">
                    <div style="width:{soh_pct}%; height:100%; background:{color}; border-radius:4px;
                                transition:width 0.5s ease;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Row 2: Side-by-side time series ───────────────────────
    section_header("Solar Generation vs Battery Degradation — Parallel View")

    city_sel = st.selectbox(
        "Select city for solar time series",
        options=list(NIGERIAN_CITIES.keys()),
        index=0,
        key="combined_city",
    )
    batt_sel = st.selectbox(
        "Select battery for SoH overlay",
        options=["B0005", "B0006", "B0007", "B0018"],
        index=0,
        key="combined_batt",
    )

    BATT_COLORS = {"B0005": DANGER, "B0006": ACCENT2, "B0007": "#457B9D", "B0018": ACCENT}

    city_solar = df_solar[df_solar["city"] == city_sel].sort_values("date")
    batt_data  = df_batt[df_batt["battery_id"] == batt_sel].sort_values("cycle_number")

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=False,
        subplot_titles=[
            f"☀️ {city_sel} — Daily Solar Irradiance",
            f"🔋 {batt_sel} — State of Health over Cycles",
        ],
        vertical_spacing=0.15,
    )

    # Solar trace
    rolling = city_solar["solar_irradiance_kwh_m2_day"].rolling(30, center=True).mean()
    fig.add_trace(go.Scatter(
        x=city_solar["date"], y=city_solar["solar_irradiance_kwh_m2_day"],
        mode="lines", name="Daily Irradiance",
        line=dict(color=ACCENT2, width=0.8), opacity=0.3,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=city_solar["date"], y=rolling,
        mode="lines", name="30-day avg",
        line=dict(color=ACCENT, width=2.5),
    ), row=1, col=1)

    # Battery SoH trace
    fig.add_trace(go.Scatter(
        x=batt_data["cycle_number"], y=batt_data["state_of_health"],
        mode="lines", name=f"{batt_sel} SoH",
        line=dict(color=BATT_COLORS[batt_sel], width=2.5),
        fill="tozeroy",
        fillcolor=f"rgba{tuple(int(BATT_COLORS[batt_sel].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.08,)}",
    ), row=2, col=1)
    fig.add_hline(
        y=0.70, line_dash="dash", line_color=DANGER,
        line_width=1.5, row=2, col=1,
        annotation_text="EoL threshold",
        annotation_font_color=DANGER,
    )

    fig.update_layout(
        height=580,
        showlegend=True,
        legend=dict(orientation="h", y=1.05),
        **PLOTLY_THEME,
    )
    fig.update_yaxes(title_text="kWh/m²/day", row=1, col=1)
    fig.update_yaxes(title_text="State of Health", row=2, col=1, range=[0.6, 1.05])
    fig.update_xaxes(title_text="Date", row=1, col=1)
    fig.update_xaxes(title_text="Cycle Number", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: Zone comparison bar ────────────────────────────
    section_header("Solar Potential by Geopolitical Zone")

    zone_avgs = (
        df_solar.groupby("zone")["solar_irradiance_kwh_m2_day"]
        .agg(["mean","std"]).reset_index().round(3)
        .sort_values("mean", ascending=False)
    )

    fig_zone = go.Figure()
    zone_colors = {
        "North West":    DANGER,
        "North East":    "#F4A261",
        "North Central": ACCENT2,
        "South West":    "#457B9D",
        "South East":    "#6A4C93",
        "South South":   "#2D6A4F",
    }
    for _, row in zone_avgs.iterrows():
        col = zone_colors.get(row["zone"], ACCENT2)
        fig_zone.add_trace(go.Bar(
            name=row["zone"],
            x=[row["zone"]],
            y=[row["mean"]],
            error_y=dict(type="data", array=[row["std"]], color="#30363D"),
            marker_color=col,
            text=[f"{row['mean']:.2f}"],
            textposition="auto",
        ))

    fig_zone.add_hline(
        y=zone_avgs["mean"].mean(),
        line_dash="dash", line_color="#8B949E", line_width=1.2,
        annotation_text=f"National avg: {zone_avgs['mean'].mean():.2f}",
        annotation_font_color="#8B949E",
    )
    fig_zone.update_layout(
        title="Mean Solar Irradiance by Zone (error bars = std dev)",
        xaxis_title="Zone",
        yaxis_title="kWh/m²/day",
        showlegend=False,
        height=340,
        **PLOTLY_THEME,
    )
    st.plotly_chart(fig_zone, use_container_width=True)
