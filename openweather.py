# src/api/openweather.py
# ─────────────────────────────────────────────────────────────
# SolarStore AI — OpenWeatherMap API Wrapper
# ─────────────────────────────────────────────────────────────
#
# WHAT THIS FILE DOES:
#   Fetches REAL-TIME weather data for Nigerian cities.
#   This is what powers the live tab in the Streamlit app.
#
# WHY TWO APIs (NASA + OpenWeather)?
#   NASA POWER  → historical data (2020–2024). Great for training
#                 ML models. Updated daily but not "live".
#   OpenWeather → real-time current conditions + 5-day forecast.
#                 Free tier allows 1,000 calls/day. Perfect for
#                 powering the live dashboard.
#
# HOW TO GET A FREE API KEY:
#   1. Go to https://openweathermap.org/api
#   2. Sign up for a free account
#   3. Go to API Keys section → copy your key
#   4. Create a .env file in solarstore-ai/ and add:
#      OPENWEATHER_API_KEY=your_key_here
#   5. This script reads it with python-dotenv
#
# FREE TIER LIMITS:
#   - 1,000 API calls/day
#   - Current weather + 5-day/3-hour forecast
#   - No historical data on free tier
# ─────────────────────────────────────────────────────────────

import requests
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv   # reads .env file into environment variables
import sys

# Explicitly point to .env in the project root
# Search multiple locations for .env
for _p in [
    Path(__file__).resolve().parent / ".env",
    Path(__file__).resolve().parents[1] / ".env",
    Path(__file__).resolve().parents[2] / ".env",
    Path.cwd() / ".env",
]:
    if _p.exists():
        load_dotenv(dotenv_path=_p, override=True)
        break
from config import NIGERIAN_CITIES

OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
API_KEY = os.getenv("OPENWEATHER_API_KEY") or "a628fbc0d73799bc0de630cd778c6633"

# ── API Configuration ─────────────────────────────────────────
def _check_api_key():
    """Helper to raise a clear error if API key is missing."""
    if not API_KEY:
        raise EnvironmentError(
            "OpenWeatherMap API key not found.\n"
            "Steps to fix:\n"
            "  1. Get a free key at https://openweathermap.org/api\n"
            "  2. Create a file called .env in solarstore-ai/\n"
            "  3. Add this line: OPENWEATHER_API_KEY=your_key_here\n"
            "  4. Re-run this script."
        )


# ─────────────────────────────────────────────────────────────
# FUNCTION 1: Current weather for a city
# ─────────────────────────────────────────────────────────────
def get_current_weather(city_name: str) -> dict:
    """
    Fetches current real-time weather conditions for a city.

    Returns a clean dict with the fields we care about for
    solar forecasting (temperature, humidity, cloud cover,
    weather description).

    Parameters
    ----------
    city_name : str → must match a key in NIGERIAN_CITIES

    Returns
    -------
    dict → {
        city, timestamp, temperature_c, feels_like_c,
        humidity_pct, cloud_cover_pct, wind_speed_ms,
        weather_description, visibility_m, is_daytime
    }
    """
    _check_api_key()

    if city_name not in NIGERIAN_CITIES:
        raise ValueError(f"'{city_name}' not in config.")

    city = NIGERIAN_CITIES[city_name]

    # OpenWeatherMap accepts lat/lon directly — more reliable than city name
    params = {
        "lat":   city["lat"],
        "lon":   city["lon"],
        "appid": API_KEY,
        "units": "metric",   # Celsius, m/s — not imperial
    }

    url = f"{OPENWEATHER_BASE_URL}/weather"
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    raw = response.json()

    # Parse the relevant fields from the nested JSON
    # OpenWeather's response structure:
    # { "main": {temp, humidity, ...},
    #   "clouds": {all: cloud_pct},
    #   "wind": {speed: m/s},
    #   "weather": [{description: "..."}],
    #   "sys": {sunrise, sunset},
    #   "dt": unix_timestamp }

    now_unix   = raw["dt"]
    sunrise    = raw["sys"]["sunrise"]
    sunset     = raw["sys"]["sunset"]
    is_daytime = sunrise <= now_unix <= sunset

    return {
        "city":                city_name,
        "state":               city["state"],
        "zone":                city["zone"],
        "timestamp":           datetime.utcfromtimestamp(now_unix).strftime("%Y-%m-%d %H:%M UTC"),
        "temperature_c":       raw["main"]["temp"],
        "feels_like_c":        raw["main"]["feels_like"],
        "humidity_pct":        raw["main"]["humidity"],
        "cloud_cover_pct":     raw["clouds"]["all"],
        "wind_speed_ms":       raw["wind"]["speed"],
        "weather_description": raw["weather"][0]["description"].title(),
        "weather_icon":        raw["weather"][0]["icon"],
        "visibility_m":        raw.get("visibility", None),
        "is_daytime":          is_daytime,
        "sunrise_utc":         datetime.utcfromtimestamp(sunrise).strftime("%H:%M"),
        "sunset_utc":          datetime.utcfromtimestamp(sunset).strftime("%H:%M"),
    }


# ─────────────────────────────────────────────────────────────
# FUNCTION 2: 5-day / 3-hour forecast for a city
# ─────────────────────────────────────────────────────────────
def get_forecast(city_name: str) -> pd.DataFrame:
    """
    Fetches a 5-day weather forecast in 3-hour intervals.
    OpenWeatherMap free tier returns 40 data points (5d × 8 per day).

    We aggregate these into daily summaries (mean temp,
    mean cloud cover, total rain) to make them useful for
    predicting daily solar generation.

    Parameters
    ----------
    city_name : str → city from NIGERIAN_CITIES

    Returns
    -------
    pd.DataFrame → one row per day, columns:
        date, city, avg_temp_c, avg_humidity_pct,
        avg_cloud_cover_pct, total_rain_mm,
        weather_description, solar_factor
    """
    _check_api_key()

    if city_name not in NIGERIAN_CITIES:
        raise ValueError(f"'{city_name}' not in config.")

    city = NIGERIAN_CITIES[city_name]

    params = {
        "lat":   city["lat"],
        "lon":   city["lon"],
        "appid": API_KEY,
        "units": "metric",
    }

    url = f"{OPENWEATHER_BASE_URL}/forecast"
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    raw = response.json()

    # raw["list"] is a list of 40 forecast entries (3-hour intervals)
    records = []
    for entry in raw["list"]:
        records.append({
            "datetime":        pd.to_datetime(entry["dt_txt"]),
            "temperature_c":   entry["main"]["temp"],
            "humidity_pct":    entry["main"]["humidity"],
            "cloud_cover_pct": entry["clouds"]["all"],
            "rain_3h_mm":      entry.get("rain", {}).get("3h", 0),
            "description":     entry["weather"][0]["description"],
        })

    df_3h = pd.DataFrame(records)

    # Aggregate 3-hour intervals → daily summaries
    df_3h["date"] = df_3h["datetime"].dt.date

    daily = df_3h.groupby("date").agg(
        avg_temp_c        = ("temperature_c",   "mean"),
        avg_humidity_pct  = ("humidity_pct",    "mean"),
        avg_cloud_pct     = ("cloud_cover_pct", "mean"),
        total_rain_mm     = ("rain_3h_mm",      "sum"),
        weather_desc      = ("description",     lambda x: x.mode()[0]),  # most common
    ).reset_index()

    # ── Solar Factor ──────────────────────────────────────────
    # A simple 0–1 multiplier estimating how much cloud cover
    # will reduce solar irradiance relative to a clear-sky day.
    # Formula: solar_factor = 1 - (cloud_cover% / 100) * 0.75
    # (clouds don't block 100% of irradiance — diffuse light still passes)
    daily["solar_factor"] = (1 - (daily["avg_cloud_pct"] / 100) * 0.75).round(3)

    daily.insert(0, "city",  city_name)
    daily.insert(1, "state", city["state"])

    return daily


# ─────────────────────────────────────────────────────────────
# FUNCTION 3: Current weather for ALL Nigerian cities
# ─────────────────────────────────────────────────────────────
def get_all_cities_current_weather() -> pd.DataFrame:
    """
    Calls get_current_weather() for every city in NIGERIAN_CITIES
    and returns a combined DataFrame.

    Useful for:
    - The "Combined Dashboard" tab in Streamlit
    - Creating a national solar potential heatmap
    - Comparing current conditions across Nigeria

    Returns
    -------
    pd.DataFrame → one row per city, all current weather fields
    """
    results = []
    for city_name in NIGERIAN_CITIES:
        try:
            weather = get_current_weather(city_name)
            results.append(weather)
            print(f"  ✅  {city_name}: {weather['temperature_c']}°C, "
                  f"{weather['cloud_cover_pct']}% cloud, "
                  f"{weather['weather_description']}")
        except Exception as e:
            print(f"  ⚠️  {city_name}: {e}")

    return pd.DataFrame(results)


# ─────────────────────────────────────────────────────────────
# FUNCTION 4: Estimate solar irradiance from current weather
# ─────────────────────────────────────────────────────────────
def estimate_current_irradiance(city_name: str) -> dict:
    """
    Uses current weather data to estimate *right now* solar
    irradiance using a simplified physical model.

    WHY THIS EXISTS:
    NASA POWER gives daily averages, not real-time readings.
    For the live Streamlit dashboard, we want to show the user
    an estimated current solar irradiance based on:
      - Time of day (is it daytime?)
      - Cloud cover (how much is blocked?)
      - Latitude (affects solar angle)

    This is NOT a substitute for the LSTM model — it's a fast
    heuristic for the live dashboard while the model does the
    heavy forecasting work.

    Formula (simplified):
      base_irradiance   = clear_sky_max × sin(solar_elevation)
      cloud_reduction   = 1 - (cloud_pct/100) × 0.75
      current_estimate  = base_irradiance × cloud_reduction

    Returns
    -------
    dict → { city, estimated_irradiance_w_m2, solar_factor,
             cloud_cover_pct, is_daytime, notes }
    """
    import math

    weather = get_current_weather(city_name)
    city    = NIGERIAN_CITIES[city_name]

    if not weather["is_daytime"]:
        return {
            "city":                        city_name,
            "estimated_irradiance_w_m2":   0,
            "solar_factor":                0,
            "cloud_cover_pct":             weather["cloud_cover_pct"],
            "is_daytime":                  False,
            "notes":                       "Nighttime — no solar generation.",
        }

    # Very rough solar elevation estimate using latitude
    # (a full model would use hour angle + declination angle)
    lat_rad      = math.radians(abs(city["lat"]))
    solar_elev   = math.cos(lat_rad)                  # simplified proxy
    clear_sky_max = 1000                               # W/m² at sea level peak

    base = clear_sky_max * solar_elev
    cloud_factor = 1 - (weather["cloud_cover_pct"] / 100) * 0.75
    estimated    = round(base * cloud_factor, 1)

    return {
        "city":                        city_name,
        "estimated_irradiance_w_m2":   estimated,
        "solar_factor":                round(cloud_factor, 3),
        "cloud_cover_pct":             weather["cloud_cover_pct"],
        "temperature_c":               weather["temperature_c"],
        "is_daytime":                  True,
        "weather_description":         weather["weather_description"],
        "notes":                       "Simplified heuristic estimate (not LSTM model output).",
    }


# ─────────────────────────────────────────────────────────────
# Run directly to test
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Testing OpenWeatherMap API...")
    print(f"Key in use: {API_KEY[:8]}...{API_KEY[-4:]}\n")

    try:
        weather = get_current_weather("Lagos")
        print("Current weather in Lagos:")
        for k, v in weather.items():
            print(f"  {k:<25} {v}")

        print("\n5-day forecast for Abuja:")
        forecast = get_forecast("Abuja")
        print(forecast.to_string(index=False))

    except Exception as e:
        print(f"Error: {e}")