# src/config.py
# ─────────────────────────────────────────────────────────────
# SolarStore AI — Project Configuration
# ─────────────────────────────────────────────────────────────
# Every city we support is defined here as a dict with:
#   lat  → latitude  (positive = North of equator)
#   lon  → longitude (positive = East of Greenwich)
#   zone → geopolitical zone in Nigeria (useful for grouping in EDA)
#
# Why do we need lat/lon?
# NASA POWER API doesn't accept city names — it works purely
# on geographic coordinates. So we map city → coordinates here.
# ─────────────────────────────────────────────────────────────

NIGERIAN_CITIES = {
    # ── South West ──────────────────────────────────────────
    "Lagos": {
        "lat": 6.5244,
        "lon": 3.3792,
        "state": "Lagos",
        "zone": "South West",
    },
    "Ibadan": {
        "lat": 7.3776,
        "lon": 3.9470,
        "state": "Oyo",
        "zone": "South West",
    },
    "Abeokuta": {
        "lat": 7.1475,
        "lon": 3.3619,
        "state": "Ogun",
        "zone": "South West",
    },
    "Akure": {
        "lat": 7.2526,
        "lon": 5.1931,
        "state": "Ondo",
        "zone": "South West",
    },
    # ── South East ──────────────────────────────────────────
    "Awka": {
        "lat": 6.2104,
        "lon": 7.0678,
        "state": "Anambra",
        "zone": "South East",
    },
    "Enugu": {
        "lat": 6.4698,
        "lon": 7.5093,
        "state": "Enugu",
        "zone": "South East",
    },
    "Owerri": {
        "lat": 5.4836,
        "lon": 7.0333,
        "state": "Imo",
        "zone": "South East",
    },
    # ── South South ─────────────────────────────────────────
    "Port Harcourt": {
        "lat": 4.8156,
        "lon": 7.0498,
        "state": "Rivers",
        "zone": "South South",
    },
    "Benin City": {
        "lat": 6.3350,
        "lon": 5.6037,
        "state": "Edo",
        "zone": "South South",
    },
    "Calabar": {
        "lat": 4.9517,
        "lon": 8.3220,
        "state": "Cross River",
        "zone": "South South",
    },
    # ── North Central ───────────────────────────────────────
    "Abuja": {
        "lat": 9.0765,
        "lon": 7.3986,
        "state": "FCT",
        "zone": "North Central",
    },
    "Lokoja": {
        "lat": 7.7961,
        "lon": 6.7370,
        "state": "Kogi",
        "zone": "North Central",
    },
    "Ilorin": {
        "lat": 8.4966,
        "lon": 4.5426,
        "state": "Kwara",
        "zone": "North Central",
    },
    # ── North West ──────────────────────────────────────────
    "Kano": {
        "lat": 12.0022,
        "lon": 8.5920,
        "state": "Kano",
        "zone": "North West",
    },
    "Kaduna": {
        "lat": 10.5222,
        "lon": 7.4383,
        "state": "Kaduna",
        "zone": "North West",
    },
    "Sokoto": {
        "lat": 13.0059,
        "lon": 5.2476,
        "state": "Sokoto",
        "zone": "North West",
    },
    # ── North East ──────────────────────────────────────────
    "Maiduguri": {
        "lat": 11.8333,
        "lon": 13.1500,
        "state": "Borno",
        "zone": "North East",
    },
    "Bauchi": {
        "lat": 10.3158,
        "lon": 9.8442,
        "state": "Bauchi",
        "zone": "North East",
    },
    "Yola": {
        "lat": 9.2035,
        "lon": 12.4954,
        "state": "Adamawa",
        "zone": "North East",
    },
}

# ─────────────────────────────────────────────────────────────
# NASA POWER API — Parameters we want to pull
# ─────────────────────────────────────────────────────────────
# Each key is the NASA parameter code, value is a human label
# we'll use in our DataFrames and charts.
NASA_PARAMETERS = {
    "ALLSKY_SFC_SW_DWN": "solar_irradiance_kwh_m2_day",   # ☀️ Main solar metric
    "CLRSKY_SFC_SW_DWN": "clear_sky_irradiance_kwh_m2_day", # ☀️ Cloud-free baseline
    "T2M":               "temperature_2m_c",               # 🌡️ Temp at 2m height
    "RH2M":              "humidity_pct",                   # 💧 Relative humidity
    "CLOUD_AMT":         "cloud_cover_pct",                # ☁️ Cloud amount
    "WS2M":              "wind_speed_2m_ms",               # 🌬️ Wind speed (bonus)
    "PRECTOTCORR":       "precipitation_mm_day",           # 🌧️ Rainfall
}

# ─────────────────────────────────────────────────────────────
# NASA POWER API — Base URL
# ─────────────────────────────────────────────────────────────
NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# ─────────────────────────────────────────────────────────────
# Default date range for historical pulls
# ─────────────────────────────────────────────────────────────
DEFAULT_START_DATE = "20200101"   # Jan 1 2020
DEFAULT_END_DATE   = "20241231"   # Dec 31 2024  (5 years of data)
