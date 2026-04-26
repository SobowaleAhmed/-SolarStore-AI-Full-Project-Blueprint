# src/api/mock_data.py
# ─────────────────────────────────────────────────────────────
# SolarStore AI — Mock Data Generator
# ─────────────────────────────────────────────────────────────
#
# WHY THIS FILE EXISTS:
#   When building a project that depends on external APIs, you
#   don't want to make real API calls every time you run code
#   during development. Reasons:
#     1. APIs can be slow (5–15 seconds per call)
#     2. Free tiers have rate limits
#     3. You might be offline
#     4. Testing is faster with controlled data
#
#   This file generates REALISTIC synthetic data that follows
#   the same statistical patterns as real NASA POWER data for
#   Nigerian cities. The patterns are based on:
#     - Nigeria's tropical climate (high irradiance year-round)
#     - Harmattan season (Nov–Feb: dusty, slightly less irradiance)
#     - Rainy season (Apr–Oct: more cloud cover in South)
#     - North/South differences (North is sunnier and drier)
#
#   This is NOT fake data for the final app — it's scaffolding
#   so you can build and test EDA + models before the real API
#   data is collected. You'll replace it with real data later.
# ─────────────────────────────────────────────────────────────

import numpy as np
import pandas as pd
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import NIGERIAN_CITIES, NASA_PARAMETERS

# Set random seed for reproducibility
# (same seed = same "random" data every time you run)
np.random.seed(42)


# ─────────────────────────────────────────────────────────────
# Climate profiles for Nigeria's geopolitical zones
# ─────────────────────────────────────────────────────────────
# These values are rough approximations based on:
# - Nigeria Meteorological Agency (NiMet) data
# - Published solar energy research on West Africa
# - NASA POWER data patterns for the region

ZONE_CLIMATE_PROFILES = {
    "North West": {
        "base_irradiance":  5.8,   # kWh/m²/day annual average (high — Sahel region)
        "irradiance_std":   0.8,
        "base_temp":        33.0,  # °C
        "base_cloud":       25.0,  # % cloud cover (low — desert-adjacent)
        "rainy_season_months": [6, 7, 8, 9],   # shorter rainy season
        "harmattan_months":    [11, 12, 1, 2],
    },
    "North East": {
        "base_irradiance":  5.6,
        "irradiance_std":   0.9,
        "base_temp":        34.0,
        "base_cloud":       22.0,
        "rainy_season_months": [6, 7, 8, 9],
        "harmattan_months":    [11, 12, 1, 2],
    },
    "North Central": {
        "base_irradiance":  5.2,
        "irradiance_std":   0.9,
        "base_temp":        30.0,
        "base_cloud":       35.0,
        "rainy_season_months": [4, 5, 6, 7, 8, 9, 10],
        "harmattan_months":    [12, 1, 2],
    },
    "South West": {
        "base_irradiance":  4.5,   # kWh/m²/day (lower — more cloud/rain)
        "irradiance_std":   1.1,
        "base_temp":        28.0,
        "base_cloud":       55.0,  # higher cloud cover
        "rainy_season_months": [3, 4, 5, 6, 7, 8, 9, 10, 11],
        "harmattan_months":    [12, 1],
    },
    "South East": {
        "base_irradiance":  4.3,
        "irradiance_std":   1.2,
        "base_temp":        27.5,
        "base_cloud":       60.0,
        "rainy_season_months": [3, 4, 5, 6, 7, 8, 9, 10, 11],
        "harmattan_months":    [12, 1],
    },
    "South South": {
        "base_irradiance":  4.0,   # lowest — Niger Delta, very rainy
        "irradiance_std":   1.3,
        "base_temp":        27.0,
        "base_cloud":       65.0,
        "rainy_season_months": [3, 4, 5, 6, 7, 8, 9, 10, 11],
        "harmattan_months":    [1],
    },
}


def _seasonal_modifier(month: int, profile: dict) -> dict:
    """
    Returns adjustment multipliers for irradiance, cloud cover,
    and temperature based on the month and climate zone profile.

    Captures Nigeria's two distinct seasons:
    - Harmattan (dry, dusty, Nov–Feb in North): slightly lower irradiance
      due to dust/haze, lower humidity, cooler nights
    - Rainy season (high cloud cover, lower irradiance)
    - Dry season peak (highest irradiance, lowest cloud cover)
    """
    mods = {"irr": 1.0, "cloud": 1.0, "temp": 0.0, "humid": 1.0, "rain": 0.0}

    if month in profile["rainy_season_months"]:
        # Rainy season: more clouds → less irradiance, more rain
        mods["irr"]   = 0.78
        mods["cloud"] = 1.6
        mods["temp"]  = -2.0
        mods["humid"] = 1.4
        mods["rain"]  = 8.0   # mm/day average rainfall

    elif month in profile["harmattan_months"]:
        # Harmattan: dry but dusty → slightly reduced irradiance
        mods["irr"]   = 0.92
        mods["cloud"] = 0.6
        mods["temp"]  = 2.0
        mods["humid"] = 0.5
        mods["rain"]  = 0.1

    else:
        # Shoulder/transition months
        mods["irr"]   = 0.95
        mods["cloud"] = 1.1
        mods["rain"]  = 2.0

    return mods


def generate_city_data(
    city_name: str,
    start: str = "20200101",
    end:   str = "20241231",
) -> pd.DataFrame:
    """
    Generates realistic synthetic solar + weather data for one city.

    The data follows:
    - Seasonal patterns (rainy/dry/harmattan)
    - Zone-appropriate irradiance levels
    - Day-to-day variability (weather isn't perfectly smooth)
    - Physical correlations (more cloud → less irradiance)

    Parameters
    ----------
    city_name : str → must be in NIGERIAN_CITIES
    start, end: str → YYYYMMDD date range

    Returns
    -------
    pd.DataFrame → same schema as real NASA POWER data
    """
    from config import NIGERIAN_CITIES

    if city_name not in NIGERIAN_CITIES:
        raise ValueError(f"'{city_name}' not in NIGERIAN_CITIES config.")

    city    = NIGERIAN_CITIES[city_name]
    zone    = city["zone"]
    profile = ZONE_CLIMATE_PROFILES[zone]

    # Generate daily date range
    dates = pd.date_range(start=start, end=end, freq="D")
    n     = len(dates)

    records = []
    for date in dates:
        m    = date.month
        mods = _seasonal_modifier(m, profile)

        # ── Solar irradiance ──────────────────────────────────
        irr_mean = profile["base_irradiance"] * mods["irr"]
        irr      = np.random.normal(irr_mean, profile["irradiance_std"] * 0.6)
        irr      = max(1.5, min(8.0, irr))   # physically plausible range

        # ── Cloud cover ───────────────────────────────────────
        cloud_mean = profile["base_cloud"] * mods["cloud"]
        cloud      = np.random.normal(cloud_mean, 12)
        cloud      = max(0, min(100, cloud))

        # Cloud and irradiance are anti-correlated
        # More cloud → push irradiance down
        irr = irr * (1 - (cloud / 100) * 0.5)
        irr = max(0.5, irr)

        # Clear-sky irradiance (what it would be with no clouds)
        clear_sky = np.random.normal(profile["base_irradiance"] * 0.98, 0.3)
        clear_sky = max(irr, min(8.5, clear_sky))

        # ── Temperature ───────────────────────────────────────
        temp = np.random.normal(profile["base_temp"] + mods["temp"], 2.0)
        temp = max(18.0, min(45.0, temp))

        # ── Humidity ──────────────────────────────────────────
        humid = np.random.normal(profile["base_cloud"] * mods["humid"] * 0.9, 10)
        humid = max(20, min(98, humid))

        # ── Wind speed ────────────────────────────────────────
        wind = abs(np.random.normal(3.5, 1.5))
        wind = min(15.0, wind)

        # ── Precipitation ─────────────────────────────────────
        rain_mean = mods["rain"]
        # Rain is zero most days, then heavy on rainy days
        rain = np.random.exponential(rain_mean) if rain_mean > 0 else 0
        rain = min(80, rain)   # cap at 80mm/day

        records.append({
            "date":                          date,
            "city":                          city_name,
            "state":                         city["state"],
            "zone":                          zone,
            "solar_irradiance_kwh_m2_day":   round(irr, 3),
            "clear_sky_irradiance_kwh_m2_day": round(clear_sky, 3),
            "temperature_2m_c":              round(temp, 2),
            "humidity_pct":                  round(humid, 1),
            "cloud_cover_pct":               round(cloud, 1),
            "wind_speed_2m_ms":              round(wind, 2),
            "precipitation_mm_day":          round(rain, 2),
        })

    df = pd.DataFrame(records)
    return df


def generate_all_cities(
    start: str = "20200101",
    end:   str = "20241231",
    save:  bool = True,
) -> pd.DataFrame:
    # Find project root by searching upward for requirements.txt
    # Works no matter where you run the script from
    _here = Path(__file__).resolve()
    ROOT_DIR = _here.parent
    for _ in range(4):
        if (ROOT_DIR / "requirements.txt").exists():
            break
        ROOT_DIR = ROOT_DIR.parent
    
    RAW_DIR = ROOT_DIR / "data" / "raw"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  📁  Saving to: {RAW_DIR}")

    all_dfs = []
    cities  = list(NIGERIAN_CITIES.keys())

    print(f"\n{'='*55}")
    print(f"  Generating mock data for {len(cities)} Nigerian cities")
    print(f"  Date range: {start} → {end}")
    print(f"{'='*55}\n")

    for city_name in cities:
        df = generate_city_data(city_name, start, end)
        all_dfs.append(df)

        # Save individual city file
        if save:
            path = RAW_DIR / f"{city_name.replace(' ', '_')}_solar_data.csv"
            df.to_csv(path, index=False)

        print(f"  ✅  {city_name:<20} {len(df):>5} rows | "
              f"avg irradiance: {df['solar_irradiance_kwh_m2_day'].mean():.2f} kWh/m²/day")

    combined = pd.concat(all_dfs, ignore_index=True)

    if save:
        path = RAW_DIR / "all_cities_solar_data.csv"
        combined.to_csv(path, index=False)
        print(f"\n  💾  Saved combined: {path}")

    print(f"\n  📊  Total: {combined.shape[0]:,} rows × {combined.shape[1]} columns")
    print(f"{'='*55}\n")
    return combined


# ─────────────────────────────────────────────────────────────
# Run directly to generate mock dataset
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = generate_all_cities(save=True)
    print("\nSample rows:")
    print(df.sample(5).to_string(index=False))
    print("\nIrradiance by zone:")
    print(
        df.groupby("zone")["solar_irradiance_kwh_m2_day"]
        .agg(["mean", "min", "max"])
        .round(3)
    )
