# src/api/nasa_power.py
# ─────────────────────────────────────────────────────────────
# SolarStore AI — NASA POWER API Wrapper
# ─────────────────────────────────────────────────────────────
#
# WHAT THIS FILE DOES:
#   Fetches solar irradiance and weather data from NASA's POWER
#   API for any Nigerian city in our config, then saves it as
#   a clean CSV file ready for EDA.
#
# HOW NASA POWER API WORKS:
#   It's a free REST API — no API key needed.
#   You send a GET request with:
#     - lat, lon       → the city's coordinates
#     - parameters     → which data columns you want
#     - start/end date → the time range
#     - community      → always "RE" (Renewable Energy)
#     - format         → we use "JSON"
#
#   It returns a JSON blob where the actual data lives at:
#   response["properties"]["parameter"][PARAM_NAME][DATE] = VALUE
#
# EXAMPLE URL (Lagos, solar irradiance, Jan 2024):
#   https://power.larc.nasa.gov/api/temporal/daily/point
#   ?parameters=ALLSKY_SFC_SW_DWN
#   &community=RE
#   &longitude=3.3792
#   &latitude=6.5244
#   &start=20240101
#   &end=20240131
#   &format=JSON
# ─────────────────────────────────────────────────────────────

import requests          # for making HTTP GET requests
import pandas as pd      # for building DataFrames from the JSON
import json              # for saving/loading cached JSON responses
import time              # for adding delays between API calls (rate limiting)
import os                # for file path operations
from pathlib import Path # cleaner path handling than os.path
from datetime import datetime

# Import our city list and parameter definitions from config
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import (
    NIGERIAN_CITIES,
    NASA_PARAMETERS,
    NASA_POWER_BASE_URL,
    DEFAULT_START_DATE,
    DEFAULT_END_DATE,
)

# ─────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────
ROOT_DIR  = Path(__file__).resolve().parents[2]   # solarstore-ai/
RAW_DIR   = ROOT_DIR / "data" / "raw"
CACHE_DIR = ROOT_DIR / "data" / "cache"

# Make sure directories exist (won't fail if they already do)
RAW_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# FUNCTION 1: Build the API request URL
# ─────────────────────────────────────────────────────────────
def build_nasa_url(lat: float, lon: float, start: str, end: str) -> str:
    """
    Constructs the full NASA POWER API URL for a given location
    and date range.

    Parameters
    ----------
    lat   : float  → latitude  (e.g. 6.5244 for Lagos)
    lon   : float  → longitude (e.g. 3.3792 for Lagos)
    start : str    → start date in YYYYMMDD format (e.g. "20200101")
    end   : str    → end date   in YYYYMMDD format (e.g. "20241231")

    Returns
    -------
    str → the complete URL ready to pass to requests.get()
    """

    # Join all parameter codes into a comma-separated string
    # e.g. "ALLSKY_SFC_SW_DWN,T2M,RH2M,CLOUD_AMT,..."
    param_string = ",".join(NASA_PARAMETERS.keys())

    # requests.get() can accept a `params` dict and will
    # automatically encode it into the URL query string for us.
    # But we build the dict here so it's readable.
    query_params = {
        "parameters": param_string,
        "community":  "RE",          # RE = Renewable Energy community
        "longitude":  lon,
        "latitude":   lat,
        "start":      start,
        "end":        end,
        "format":     "JSON",
    }

    # Build a PreparedRequest to get the full URL string
    # (useful for debugging — you can paste it in your browser)
    req = requests.Request("GET", NASA_POWER_BASE_URL, params=query_params)
    prepared = req.prepare()
    return prepared.url


# ─────────────────────────────────────────────────────────────
# FUNCTION 2: Fetch raw JSON from NASA API (with caching)
# ─────────────────────────────────────────────────────────────
def fetch_nasa_raw(
    city_name: str,
    lat: float,
    lon: float,
    start: str = DEFAULT_START_DATE,
    end: str   = DEFAULT_END_DATE,
    use_cache: bool = True,
) -> dict:
    """
    Fetches raw JSON data from NASA POWER API for one city.
    Saves the response to cache so we don't re-call the API
    every time we run the script during development.

    WHY CACHING MATTERS:
    NASA POWER API is free but can be slow (5–15 seconds per call).
    Once you've fetched the data, save it locally as a .json file.
    Next time you run the script, load from cache instead of calling
    the API again. This saves time and is considerate to the API.

    Parameters
    ----------
    city_name : str   → used for naming the cache file
    lat, lon  : float → city coordinates
    start, end: str   → date range in YYYYMMDD
    use_cache : bool  → if True, check cache before calling API

    Returns
    -------
    dict → raw NASA JSON response
    """

    # Cache file name: e.g. "Lagos_20200101_20241231.json"
    cache_file = CACHE_DIR / f"{city_name.replace(' ', '_')}_{start}_{end}.json"

    # ── Check cache first ────────────────────────────────────
    if use_cache and cache_file.exists():
        print(f"  📂 Loading {city_name} from cache...")
        with open(cache_file, "r") as f:
            return json.load(f)

    # ── Not in cache → call the API ─────────────────────────
    url = build_nasa_url(lat, lon, start, end)
    print(f"  🛰️  Calling NASA API for {city_name}...")
    print(f"      URL: {url[:80]}...")   # print first 80 chars of URL

    try:
        # NASA POWER requires a User-Agent header — without it you get a 403 Forbidden.
        # We identify ourselves as SolarStore AI so NASA can track usage.
        headers = {
            "User-Agent": "SolarStoreAI/1.0 (Research Project; contact via GitHub)"
        }

        # timeout=60 means "give up if no response after 60 seconds"
        response = requests.get(url, headers=headers, timeout=60)

        # raise_for_status() throws an error if status code is 4xx or 5xx
        # (e.g. 404 Not Found, 500 Server Error)
        response.raise_for_status()

        data = response.json()

        # ── Save to cache ────────────────────────────────────
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  ✅  {city_name} fetched and cached.")

        return data

    except requests.exceptions.Timeout:
        print(f"  ⏱️  Timeout for {city_name}. Try again later.")
        raise

    except requests.exceptions.HTTPError as e:
        print(f"  ❌  HTTP error for {city_name}: {e}")
        raise

    except requests.exceptions.ConnectionError:
        print(f"  ❌  No internet connection. Check your network.")
        raise


# ─────────────────────────────────────────────────────────────
# FUNCTION 3: Parse raw JSON → clean Pandas DataFrame
# ─────────────────────────────────────────────────────────────
def parse_nasa_response(raw_data: dict, city_name: str, zone: str, state: str) -> pd.DataFrame:
    """
    Converts the messy nested NASA JSON into a clean, flat
    Pandas DataFrame where each row = one day.

    NASA JSON structure (simplified):
    {
      "properties": {
        "parameter": {
          "ALLSKY_SFC_SW_DWN": {
            "20200101": 4.5,
            "20200102": 3.8,
            ...
          },
          "T2M": {
            "20200101": 28.4,
            ...
          },
          ...
        }
      }
    }

    We want to turn this into:
    date        | city  | solar_irradiance | temperature | ...
    2020-01-01  | Lagos | 4.5              | 28.4        | ...
    2020-01-02  | Lagos | 3.8              | 27.9        | ...

    Parameters
    ----------
    raw_data  : dict → the JSON returned by fetch_nasa_raw()
    city_name : str  → city label to add as a column
    zone      : str  → geopolitical zone (for EDA grouping)
    state     : str  → state name

    Returns
    -------
    pd.DataFrame → clean, analysis-ready DataFrame
    """

    # Navigate to the nested parameter data
    # If the key doesn't exist, something went wrong with the API response
    try:
        param_data = raw_data["properties"]["parameter"]
    except KeyError:
        raise ValueError(
            f"Unexpected NASA API response structure for {city_name}. "
            f"Keys found: {list(raw_data.keys())}"
        )

    # Build a DataFrame from the parameter dict
    # Each key in param_data is a NASA code (e.g. "ALLSKY_SFC_SW_DWN")
    # Each value is a dict of {date_string: value}
    df = pd.DataFrame(param_data)

    # The index is date strings like "20200101" — convert to real dates
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "date"
    df = df.reset_index()   # make 'date' a regular column

    # Rename columns from NASA codes to human-readable names
    # NASA_PARAMETERS maps code → readable name
    df = df.rename(columns=NASA_PARAMETERS)

    # Add city metadata columns (very useful during EDA)
    df.insert(1, "city",  city_name)
    df.insert(2, "state", state)
    df.insert(3, "zone",  zone)

    # NASA uses -999 as a fill value for missing data
    # Replace with NaN so Pandas treats them as missing
    df = df.replace(-999.0, float("nan"))
    df = df.replace(-999,   float("nan"))

    # Sort chronologically
    df = df.sort_values("date").reset_index(drop=True)

    return df


# ─────────────────────────────────────────────────────────────
# FUNCTION 4: Fetch + parse for ONE city → save CSV
# ─────────────────────────────────────────────────────────────
def fetch_city_data(
    city_name: str,
    start: str = DEFAULT_START_DATE,
    end: str   = DEFAULT_END_DATE,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Full pipeline for one city:
    1. Look up lat/lon from config
    2. Fetch raw JSON (or load from cache)
    3. Parse into clean DataFrame
    4. Save as CSV

    Parameters
    ----------
    city_name : str  → must match a key in NIGERIAN_CITIES
    start, end: str  → date range YYYYMMDD
    use_cache : bool → whether to use cached JSON

    Returns
    -------
    pd.DataFrame → clean solar/weather data for this city
    """

    if city_name not in NIGERIAN_CITIES:
        raise ValueError(
            f"'{city_name}' not found in config. "
            f"Available cities: {list(NIGERIAN_CITIES.keys())}"
        )

    city_info = NIGERIAN_CITIES[city_name]
    lat   = city_info["lat"]
    lon   = city_info["lon"]
    zone  = city_info["zone"]
    state = city_info["state"]

    # Step 1: Fetch raw JSON
    raw_data = fetch_nasa_raw(city_name, lat, lon, start, end, use_cache)

    # Step 2: Parse to DataFrame
    df = parse_nasa_response(raw_data, city_name, zone, state)

    # Step 3: Save to CSV
    csv_path = RAW_DIR / f"{city_name.replace(' ', '_')}_solar_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"  💾  Saved → {csv_path.name}  ({len(df)} rows)")

    return df


# ─────────────────────────────────────────────────────────────
# FUNCTION 5: Fetch ALL Nigerian cities → one combined CSV
# ─────────────────────────────────────────────────────────────
def fetch_all_cities(
    start: str = DEFAULT_START_DATE,
    end: str   = DEFAULT_END_DATE,
    use_cache: bool = True,
    delay_seconds: float = 1.5,
) -> pd.DataFrame:
    """
    Loops through every city in NIGERIAN_CITIES, fetches data,
    and combines everything into one big DataFrame.

    WHY delay_seconds?
    Being polite to public APIs is good practice. Adding a small
    delay between requests avoids hammering the server and getting
    rate-limited or blocked.

    Parameters
    ----------
    start, end     : str   → date range YYYYMMDD
    use_cache      : bool  → use cached JSON where available
    delay_seconds  : float → pause between API calls

    Returns
    -------
    pd.DataFrame → all cities combined (19 cities × ~1825 days ≈ 34,000 rows)
    """

    all_dfs = []
    cities  = list(NIGERIAN_CITIES.keys())
    total   = len(cities)

    print(f"\n{'='*55}")
    print(f"  SolarStore AI — Fetching {total} Nigerian Cities")
    print(f"  Date range: {start} → {end}")
    print(f"{'='*55}\n")

    for i, city_name in enumerate(cities, 1):
        print(f"[{i}/{total}] {city_name}")
        try:
            df = fetch_city_data(city_name, start, end, use_cache)
            all_dfs.append(df)

            # Polite delay between calls (skip after last city)
            if i < total:
                time.sleep(delay_seconds)

        except Exception as e:
            # Don't crash the whole loop if one city fails
            print(f"  ⚠️  Skipping {city_name} due to error: {e}\n")
            continue

        print()  # blank line between cities for readability

    if not all_dfs:
        raise RuntimeError("No data was fetched. Check your internet connection.")

    # Stack all city DataFrames vertically
    combined = pd.concat(all_dfs, ignore_index=True)

    # Save the master combined CSV
    combined_path = RAW_DIR / "all_cities_solar_data.csv"
    combined.to_csv(combined_path, index=False)

    print(f"\n{'='*55}")
    print(f"  ✅  All done!")
    print(f"  📊  Combined dataset: {combined.shape[0]:,} rows × {combined.shape[1]} columns")
    print(f"  💾  Saved → {combined_path}")
    print(f"{'='*55}\n")

    return combined


# ─────────────────────────────────────────────────────────────
# FUNCTION 6: Quick data quality report
# ─────────────────────────────────────────────────────────────
def data_quality_report(df: pd.DataFrame) -> None:
    """
    Prints a quick summary of the fetched data so you can
    immediately spot any issues (missing values, bad date ranges,
    unexpected NaNs from -999 replacements, etc.)
    """
    print("\n📋  DATA QUALITY REPORT")
    print("─" * 45)
    print(f"  Shape          : {df.shape[0]:,} rows × {df.shape[1]} columns")
    print(f"  Date range     : {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"  Cities covered : {df['city'].nunique()} ({', '.join(df['city'].unique())})")
    print(f"  Zones covered  : {df['zone'].nunique()}")
    print()
    print("  Missing values per column:")
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    for col in missing[missing > 0].index:
        print(f"    {col:<40} {missing[col]:>5} ({missing_pct[col]}%)")
    if missing.sum() == 0:
        print("    None ✅")
    print("─" * 45)


# ─────────────────────────────────────────────────────────────
# Run this file directly to test it
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Quick test — fetch just Lagos first to verify everything works
    print("Testing with Lagos only...\n")
    df_lagos = fetch_city_data("Lagos", use_cache=True)
    data_quality_report(df_lagos)
    print("\nFirst 5 rows:")
    print(df_lagos.head())
