# app/tabs/recommendations.py
# ─────────────────────────────────────────────────────────────
# SolarStore AI — Tab 4: Recommendations
# ─────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.utils import (
    NIGERIAN_CITIES, PLOTLY_THEME, ACCENT, ACCENT2, DANGER,
    load_solar_data, load_battery_data,
    predict_soh, section_header, metric_card, rec_card, badge,
)


def _charging_window_chart(city_df: pd.DataFrame, city: str) -> go.Figure:
    """Bar chart showing best months to charge (highest irradiance)."""
    month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]
    monthly = (
        city_df.groupby("month")["solar_irradiance_kwh_m2_day"]
        .mean().reset_index()
    )
    monthly["month_name"] = monthly["month"].apply(lambda x: month_names[x-1])
    threshold = monthly["solar_irradiance_kwh_m2_day"].quantile(0.60)

    fig = go.Figure(go.Bar(
        x=monthly["month_name"],
        y=monthly["solar_irradiance_kwh_m2_day"].round(2),
        marker_color=[
            ACCENT2 if v >= threshold else DANGER
            for v in monthly["solar_irradiance_kwh_m2_day"]
        ],
        text=monthly["solar_irradiance_kwh_m2_day"].round(2),
        textposition="auto",
    ))
    fig.add_hline(
        y=threshold, line_dash="dash", line_color=ACCENT,
        line_width=1.5, annotation_text="Optimal charging threshold",
        annotation_font_color=ACCENT,
    )
    fig.update_layout(
        title=f"Best Charging Months — {city}<br>"
              f"<sup>Teal = optimal solar charging window · Red = avoid heavy use</sup>",
        xaxis_title="Month",
        yaxis_title="Avg Irradiance (kWh/m²/day)",
        height=320,
        **PLOTLY_THEME,
    )
    return fig


def _roi_table(city_avgs: pd.DataFrame, panel_kw: float,
               efficiency: float, tariff: float) -> pd.DataFrame:
    """Estimate annual energy output and revenue per city."""
    city_avgs = city_avgs.copy()
    city_avgs["annual_kwh"]  = (
        city_avgs["solar_irradiance_kwh_m2_day"]
        * panel_kw * (efficiency / 100) * 365
    ).round(1)
    city_avgs["annual_revenue_ngn"] = (
        city_avgs["annual_kwh"] * tariff
    ).round(0)
    city_avgs["annual_revenue_usd"] = (
        city_avgs["annual_revenue_ngn"] / 1550
    ).round(1)
    return city_avgs.sort_values("annual_kwh", ascending=False).reset_index(drop=True)


def render():

    # ── Sidebar controls ──────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 💡 Recommendation Settings")
        city = st.selectbox(
            "City",
            options=list(NIGERIAN_CITIES.keys()),
            index=0,
            key="rec_city",
        )
        panel_kw   = st.slider("System Size (kWp)", 1.0, 50.0, 5.0, 0.5, key="rec_panel")
        efficiency = st.slider("Panel Efficiency (%)", 15, 22, 18, key="rec_eff")
        tariff_ngn = st.number_input(
            "Electricity Tariff (₦/kWh)",
            min_value=10.0, max_value=200.0, value=68.0, step=1.0,
            help="Current NERC Band A tariff is ~₦68/kWh",
        )
        cycle_number  = st.number_input("Battery Cycle Count", 1, 2000, 80, key="rec_cycle")
        temperature_c = st.slider("Battery Temp (°C)", 10.0, 55.0, 25.0, 0.5, key="rec_temp")

    # ── Load data ─────────────────────────────────────────────
    df_solar = load_solar_data()
    city_df  = df_solar[df_solar["city"] == city].sort_values("date")

    result = predict_soh(
        cycle_number=cycle_number,
        temperature_c=temperature_c,
        internal_resistance=175.0,
        capacity_loss_pct=0.0,
    )
    soh_pct = result["soh_pct"]
    rul     = result["rul"]
    bdg     = result["badge"]

    city_avgs = (
        df_solar.groupby(["city", "zone"])["solar_irradiance_kwh_m2_day"]
        .mean().reset_index()
    )
    roi_df = _roi_table(city_avgs, panel_kw, efficiency, tariff_ngn)

    # ── Summary bar ───────────────────────────────────────────
    section_header("Your System at a Glance")

    avg_irr    = city_df["solar_irradiance_kwh_m2_day"].mean()
    annual_kwh = round(avg_irr * panel_kw * (efficiency / 100) * 365, 1)
    annual_rev = round(annual_kwh * tariff_ngn, 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(metric_card("City", city, NIGERIAN_CITIES[city]["zone"]), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("Avg Irradiance", f"{avg_irr:.2f}", "kWh/m²/day", ACCENT2), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("Annual Generation", f"{annual_kwh:,.0f}", "kWh/year", ACCENT), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card("Annual Revenue", f"₦{annual_rev:,.0f}", f"(~${annual_rev/1550:,.0f} USD)"), unsafe_allow_html=True)
    with c5:
        st.markdown(metric_card("Battery SoH", f"{soh_pct:.1f}%", f"RUL: {rul} cycles", ACCENT2 if soh_pct >= 80 else DANGER), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Solar recommendations ─────────────────────────────────
    col_l, col_r = st.columns([3, 2])

    with col_l:
        section_header("Solar Charging Recommendations")
        st.plotly_chart(
            _charging_window_chart(city_df, city),
            use_container_width=True,
        )

        # Dynamic text recommendations
        monthly = city_df.groupby("month")["solar_irradiance_kwh_m2_day"].mean()
        best_months  = monthly.nlargest(3).index.tolist()
        worst_months = monthly.nsmallest(3).index.tolist()
        month_names  = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                        7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
        best_str  = ", ".join([month_names[m] for m in best_months])
        worst_str = ", ".join([month_names[m] for m in worst_months])
        zone       = NIGERIAN_CITIES[city]["zone"]
        is_north   = "North" in zone

        st.markdown(
            rec_card(
                f"☀️ Peak Solar Windows — {city}",
                f"Best months to maximise solar charging: <b>{best_str}</b>. "
                f"Schedule heavy loads (water pumps, AC, EV charging) between 10am–3pm during these months "
                f"when irradiance peaks. You can expect up to "
                f"<b>{round(monthly.max() * panel_kw * efficiency/100, 1)} kWh/day</b> from your {panel_kw} kWp system.",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            rec_card(
                f"⛅ Low Irradiance Months — Plan Ahead",
                f"Irradiance dips in <b>{worst_str}</b>"
                f"{' (rainy season)' if not is_north else ' (Harmattan dust haze)'}. "
                f"Reduce discretionary loads, top up battery from grid at off-peak hours (11pm–5am), "
                f"and avoid deep discharges below 20% SoC to protect battery longevity.",
                warning=True,
            ),
            unsafe_allow_html=True,
        )

        if is_north:
            st.markdown(
                rec_card(
                    "🌞 Northern Nigeria Advantage",
                    f"{city} in the {zone} receives significantly more solar irradiance than southern cities "
                    f"(avg {avg_irr:.2f} vs ~2.1 kWh/m²/day in the South). "
                    f"A {panel_kw} kWp system here generates ~{int((avg_irr/2.1-1)*100)}% more energy annually "
                    f"than an equivalent system in Port Harcourt or Calabar. "
                    "Ideal for commercial solar installations.",
                ),
                unsafe_allow_html=True,
            )

    with col_r:
        section_header("Battery Recommendations")

        # Dynamic battery advice
        if soh_pct >= 90:
            st.markdown(
                rec_card(
                    "✅ Battery in Excellent Health",
                    f"SoH of {soh_pct:.1f}% — your battery is performing well. "
                    f"Estimated <b>{rul} cycles remaining</b> before End of Life. "
                    "Maintain current operating temperature and avoid charging above 4.1V "
                    "to further extend lifespan.",
                ),
                unsafe_allow_html=True,
            )
        elif soh_pct >= 80:
            st.markdown(
                rec_card(
                    "🟡 Battery in Good Health — Monitor",
                    f"SoH of {soh_pct:.1f}% — approaching the mid-life phase. "
                    f"<b>{rul} cycles remaining</b>. "
                    "Begin monitoring internal resistance monthly. "
                    "Avoid operating above 35°C to slow SEI layer growth.",
                ),
                unsafe_allow_html=True,
            )
        elif soh_pct >= 70:
            st.markdown(
                rec_card(
                    "⚠️ Battery Approaching End of Life",
                    f"SoH of {soh_pct:.1f}% — only <b>{rul} cycles remaining</b> before EoL threshold. "
                    "Start planning battery replacement. Reduce charge rate to 0.5C. "
                    "Avoid full charges (charge to 80% max). "
                    "Do not discharge below 20% SoC.",
                    warning=True,
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                rec_card(
                    "🔴 Battery End of Life — Replace Now",
                    f"SoH of {soh_pct:.1f}% — below the 70% End of Life threshold. "
                    "Battery should be replaced immediately. "
                    "Continuing to use a degraded battery risks: reduced solar storage capacity, "
                    "increased heat generation, and potential safety hazards.",
                    warning=True,
                ),
                unsafe_allow_html=True,
            )

        if temperature_c > 35:
            st.markdown(
                rec_card(
                    "🌡️ High Operating Temperature Detected",
                    f"Operating at {temperature_c:.1f}°C accelerates degradation significantly. "
                    "Every 10°C above 25°C doubles SEI growth rate (Arrhenius kinetics). "
                    "Install active cooling, ensure adequate ventilation, "
                    "or relocate battery to a shaded enclosure.",
                    warning=True,
                ),
                unsafe_allow_html=True,
            )

        st.markdown(
            rec_card(
                "🔌 Optimal Charging Strategy",
                "• Charge during peak solar hours (10am–3pm) using solar power directly.<br>"
                "• Use CC-CV (Constant Current – Constant Voltage) protocol.<br>"
                "• Set charge cutoff at 4.1V (not 4.2V) to reduce stress.<br>"
                "• Avoid overnight fast-charging from grid — use trickle charge.<br>"
                "• Partial state-of-charge (20–80%) cycling extends battery life.",
            ),
            unsafe_allow_html=True,
        )

    # ── ROI table ─────────────────────────────────────────────
    section_header("City-by-City Solar ROI Comparison")

    st.markdown(f"Based on **{panel_kw} kWp** system | **{efficiency}% efficiency** | **₦{tariff_ngn}/kWh** tariff")

    display_df = roi_df[[
        "city", "zone", "solar_irradiance_kwh_m2_day",
        "annual_kwh", "annual_revenue_ngn", "annual_revenue_usd",
    ]].copy()
    display_df.columns = [
        "City", "Zone", "Avg Irradiance (kWh/m²/day)",
        "Annual Output (kWh)", "Annual Revenue (₦)", "Annual Revenue ($)"
    ]
    display_df["Annual Revenue (₦)"] = display_df["Annual Revenue (₦)"].apply(lambda x: f"₦{x:,.0f}")
    display_df["Annual Revenue ($)"] = display_df["Annual Revenue ($)"].apply(lambda x: f"${x:,.1f}")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=500,
    )

    # ── ROI bar chart ─────────────────────────────────────────
    fig_roi = go.Figure(go.Bar(
        x=roi_df["city"],
        y=roi_df["annual_kwh"],
        marker_color=roi_df["annual_kwh"],
        marker_colorscale="YlOrRd",
        text=roi_df["annual_kwh"].apply(lambda x: f"{x:,.0f} kWh"),
        textposition="auto",
    ))
    fig_roi.update_layout(
        title=f"Annual Solar Generation by City — {panel_kw} kWp System",
        xaxis_title="City",
        yaxis_title="Annual Output (kWh)",
        xaxis_tickangle=-35,
        height=360,
        **PLOTLY_THEME,
    )
    st.plotly_chart(fig_roi, use_container_width=True)
