# app/tabs/battery_health.py
# ─────────────────────────────────────────────────────────────
# SolarStore AI — Tab 2: Battery Health
# ─────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.utils import (
    PLOTLY_THEME, ACCENT, ACCENT2, DANGER,
    load_battery_data, load_battery_models,
    predict_soh, soh_gauge, degradation_curve,
    section_header, metric_card, badge, rec_card,
)


def render():

    # ── Sidebar controls ──────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🔋 Battery Settings")

        cycle_number = st.number_input(
            "Cycle Number",
            min_value=1, max_value=2000, value=80, step=1,
            help="How many full charge/discharge cycles has the battery completed?",
        )
        temperature_c = st.slider(
            "Operating Temperature (°C)",
            min_value=10.0, max_value=55.0, value=25.0, step=0.5,
            help="Average temperature during operation. Higher = faster degradation.",
        )
        internal_resistance = st.slider(
            "Internal Resistance (mΩ)",
            min_value=100.0, max_value=400.0, value=175.0, step=5.0,
            help="Measured internal resistance. Rises with aging.",
        )
        capacity_loss = st.slider(
            "Measured Capacity Loss (%)",
            min_value=0.0, max_value=40.0, value=8.0, step=0.5,
            help="How much capacity has the battery lost since new?",
        )
        rated_capacity = st.selectbox(
            "Rated Capacity",
            ["2.0 Ah (Standard)", "3.0 Ah", "4.0 Ah", "100 Ah (EV pack)"],
            index=0,
        )

    # ── Compute prediction ────────────────────────────────────
    result = predict_soh(
        cycle_number     = cycle_number,
        temperature_c    = temperature_c,
        internal_resistance = internal_resistance,
        capacity_loss_pct   = capacity_loss,
    )

    soh     = result["soh"]
    soh_pct = result["soh_pct"]
    rul     = result["rul"]
    cat     = result["category"]
    bdg     = result["badge"]
    alpha   = result["alpha"]

    # ── Header metrics ────────────────────────────────────────
    section_header("Battery State of Health")

    col_gauge, col_metrics = st.columns([1, 2])

    with col_gauge:
        st.plotly_chart(soh_gauge(soh_pct), use_container_width=True)
        st.markdown(
            f"<div style='text-align:center'>{badge(cat, bdg)}</div>",
            unsafe_allow_html=True,
        )

    with col_metrics:
        r1c1, r1c2 = st.columns(2)
        r2c1, r2c2 = st.columns(2)

        with r1c1:
            rul_color = ACCENT2 if rul > 50 else (ACCENT if rul > 20 else DANGER)
            st.markdown(
                metric_card("Remaining Useful Life", str(rul), "cycles", rul_color),
                unsafe_allow_html=True,
            )
        with r1c2:
            st.markdown(
                metric_card("Current Cycle", str(cycle_number), "completed"),
                unsafe_allow_html=True,
            )
        with r2c1:
            temp_color = DANGER if temperature_c > 40 else (ACCENT if temperature_c > 30 else ACCENT2)
            st.markdown(
                metric_card("Temperature", f"{temperature_c:.1f}", "°C", temp_color),
                unsafe_allow_html=True,
            )
        with r2c2:
            res_color = DANGER if internal_resistance > 250 else (ACCENT if internal_resistance > 200 else ACCENT2)
            st.markdown(
                metric_card("Internal Resistance", f"{internal_resistance:.0f}", "mΩ", res_color),
                unsafe_allow_html=True,
            )

        # Chemistry note
        st.markdown(f"""
        <div style='background:#161B22; border:1px solid #30363D; border-radius:8px;
                    padding:12px 16px; margin-top:8px; font-size:0.82rem; color:#8B949E;'>
            <b style='color:#E6EDF3'>Degradation rate (α):</b> {alpha:.6f} per cycle<br>
            Higher temperature increases α via Arrhenius kinetics —
            every 10°C rise roughly doubles SEI growth rate.
        </div>
        """, unsafe_allow_html=True)

    # ── Degradation curve ─────────────────────────────────────
    section_header("Projected Degradation Curve")
    st.plotly_chart(
        degradation_curve(cycle_number, alpha),
        use_container_width=True,
    )

    # ── Voltage profile evolution ─────────────────────────────
    section_header("Discharge Profile Simulation")

    try:
        df_volt = pd.read_csv("data/raw/battery/all_batteries_voltage.csv")

        # Pick closest matching battery profile
        selected_batt = "B0018" if temperature_c > 35 else "B0005"
        bvolt  = df_volt[df_volt["battery_id"] == selected_batt]
        cycles = sorted(bvolt["cycle_number"].unique())

        fig = go.Figure()
        cycle_colors = [
            f"rgba(42,157,143,{0.3 + 0.7*(i/(len(cycles)-1))})"
            for i in range(len(cycles))
        ]

        for cyc, col in zip(cycles, cycle_colors):
            cdata = bvolt[bvolt["cycle_number"] == cyc]
            soh_c = cdata["state_of_health"].iloc[0]
            fig.add_trace(go.Scatter(
                x=cdata["time_min"],
                y=cdata["voltage_v"],
                mode="lines",
                name=f"Cycle {cyc} (SoH={soh_c:.3f})",
                line=dict(color=col, width=2),
            ))

        fig.add_hline(
            y=2.5, line_dash="dot",
            line_color="#30363D", line_width=1,
            annotation_text="Discharge cutoff (2.5V)",
            annotation_font_color="#8B949E",
        )
        fig.update_layout(
            title=f"Voltage Discharge Profiles — {selected_batt} "
                  f"({'High Temp ~40°C' if selected_batt == 'B0018' else 'Room Temp ~24°C'})"
                  f"<br><sup>Green = fresh battery · Teal = aged battery</sup>",
            xaxis_title="Time (min)",
            yaxis_title="Voltage (V)",
            yaxis=dict(range=[2.3, 4.35]),
            legend=dict(orientation="h", y=1.15, font_size=10),
            height=340,
            **PLOTLY_THEME,
        )
        st.plotly_chart(fig, use_container_width=True)

    except FileNotFoundError:
        st.info("Run `python src/api/battery_mock_data.py` to generate voltage profile data.")

    # ── Anomaly check ─────────────────────────────────────────
    section_header("Cycle Anomaly Check")

    try:
        _, iso_forest, dnn_features, anomaly_features = load_battery_models()
        import joblib
        from pathlib import Path
        scaler = joblib.load(Path("models/battery_scaler_X.pkl"))

        # Build a single-row feature vector from user inputs
        # We use median values from the dataset for features not in the UI
        df_batt = load_battery_data()
        medians = df_batt[anomaly_features].median()

        anomaly_input = medians.copy()
        anomaly_input["internal_resistance_mohm"] = internal_resistance
        anomaly_input["temperature_c"]            = temperature_c
        anomaly_input["soh_delta"]                = -(soh_pct * 0.0001)
        anomaly_input["resistance_delta"]         = internal_resistance - 150

        X_input = anomaly_input.values.reshape(1, -1)
        anomaly_pred  = iso_forest.predict(X_input)[0]
        anomaly_score = iso_forest.score_samples(X_input)[0]

        is_anomaly = anomaly_pred == -1

        a1, a2 = st.columns(2)
        with a1:
            if is_anomaly:
                st.markdown(
                    metric_card("Cycle Status", "⚠️  ANOMALOUS", "Unusual behaviour detected", DANGER),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    metric_card("Cycle Status", "✅  NORMAL", "Cycle within expected range", ACCENT2),
                    unsafe_allow_html=True,
                )
        with a2:
            st.markdown(
                metric_card(
                    "Anomaly Score",
                    f"{anomaly_score:.4f}",
                    "Lower = more anomalous",
                    DANGER if is_anomaly else ACCENT2,
                ),
                unsafe_allow_html=True,
            )

        if is_anomaly:
            st.markdown(
                rec_card(
                    "⚠️ Anomalous Cycle Detected",
                    "This cycle's electrical signature deviates from normal patterns. "
                    "Check for: cell imbalance, temperature spikes, unexpected voltage drops, "
                    "or charger malfunction. Consider running a full diagnostic.",
                    warning=True,
                ),
                unsafe_allow_html=True,
            )

    except Exception as e:
        st.info(f"Anomaly model not loaded — run Phase 5 notebook first. ({e})")
