# src/api/battery_mock_data.py
# ─────────────────────────────────────────────────────────────
# SolarStore AI — NASA Battery Dataset Mock Generator
# ─────────────────────────────────────────────────────────────
#
# ABOUT THE REAL NASA BATTERY DATASET:
#   NASA's Prognostics Center ran lithium-ion batteries through
#   repeated charge/discharge/impedance cycles until End of Life (EoL).
#   EoL is defined as when capacity drops to 70% of rated capacity.
#
#   Real dataset URL:
#   https://www.nasa.gov/content/prognostics-center-of-excellence-data-set-repository
#   (download B0005.mat, B0006.mat, B0007.mat, B0018.mat)
#
# WHAT THIS MOCK GENERATES:
#   Synthetic battery data that follows the same degradation physics:
#
#   1. CAPACITY FADE
#      Lithium-ion batteries lose capacity every cycle due to:
#      - SEI (Solid Electrolyte Interphase) layer growth
#      - Lithium plating
#      - Active material loss
#      Modeled as: capacity(n) = C0 * exp(-alpha * n) + noise
#
#   2. TEMPERATURE EFFECTS
#      High temps accelerate degradation (Arrhenius relationship).
#      Low temps reduce capacity temporarily (reversible).
#
#   3. VOLTAGE PROFILES
#      Charge: voltage rises from ~3.0V to 4.2V (cutoff)
#      Discharge: voltage drops from 4.2V to 2.5V (cutoff)
#      As battery ages, discharge curve flattens and falls faster.
#
#   4. INTERNAL RESISTANCE
#      Increases with cycle number — a key health indicator.
#      High resistance = more heat, less usable energy.
#
# CHEMISTRY NOTE (for your interviews):
#   The dominant degradation mechanism in Li-ion cells at room temp
#   is SEI layer growth on the anode (usually graphite). The SEI
#   consumes cyclable lithium irreversibly, shrinking capacity.
#   This follows a square-root-of-time (sqrt(n)) kinetics at low
#   temps and Arrhenius kinetics at high temps.
# ─────────────────────────────────────────────────────────────

import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)

# ─────────────────────────────────────────────────────────────
# Battery profiles — mimics NASA's B0005, B0006, B0007, B0018
# ─────────────────────────────────────────────────────────────
BATTERY_PROFILES = {
    "B0005": {
        "rated_capacity_ah": 2.0,       # Ah at beginning of life
        "nominal_voltage":   3.7,       # V
        "charge_cutoff_v":   4.2,       # V (stop charging above this)
        "discharge_cutoff_v":2.5,       # V (stop discharging below this)
        "alpha":             0.00085,   # degradation rate constant
        "temp_mean_c":       24.0,      # average operating temperature
        "temp_std_c":        2.5,
        "max_cycles":        168,       # real B0005 ran for 168 cycles
    },
    "B0006": {
        "rated_capacity_ah": 2.0,
        "nominal_voltage":   3.7,
        "charge_cutoff_v":   4.2,
        "discharge_cutoff_v":2.5,
        "alpha":             0.00090,   # slightly faster degradation
        "temp_mean_c":       24.0,
        "temp_std_c":        2.5,
        "max_cycles":        168,
    },
    "B0007": {
        "rated_capacity_ah": 2.0,
        "nominal_voltage":   3.7,
        "charge_cutoff_v":   4.2,
        "discharge_cutoff_v":2.5,
        "alpha":             0.00080,   # slowest degradation
        "temp_mean_c":       24.0,
        "temp_std_c":        2.0,
        "max_cycles":        168,
    },
    "B0018": {
        "rated_capacity_ah": 2.0,
        "nominal_voltage":   3.7,
        "charge_cutoff_v":   4.2,
        "discharge_cutoff_v":2.5,
        "alpha":             0.00110,   # fastest degradation (higher temp)
        "temp_mean_c":       40.0,      # ran at higher temperature
        "temp_std_c":        3.0,
        "max_cycles":        132,       # reached EoL sooner
    },
}

# End of Life threshold — industry standard
EOL_THRESHOLD = 0.70   # 70% of rated capacity


# ─────────────────────────────────────────────────────────────
# FUNCTION 1: Generate cycle-level summary data
# ─────────────────────────────────────────────────────────────
def generate_cycle_data(battery_id: str) -> pd.DataFrame:
    """
    Generates one row per charge/discharge cycle for a battery.

    Each row represents one complete cycle and contains:
    - cycle_number         → how many cycles completed
    - capacity_ah          → measured discharge capacity (Ah)
    - state_of_health      → capacity / rated_capacity (0–1)
    - temperature_c        → avg temperature during cycle
    - internal_resistance  → ohms (increases with aging)
    - charge_time_min      → minutes to fully charge
    - discharge_time_min   → minutes to fully discharge
    - voltage_drop         → voltage sag under load
    - is_end_of_life       → True when SoH < 0.70

    Parameters
    ----------
    battery_id : str → must match key in BATTERY_PROFILES

    Returns
    -------
    pd.DataFrame → one row per cycle
    """
    if battery_id not in BATTERY_PROFILES:
        raise ValueError(f"Unknown battery: {battery_id}. Choose from {list(BATTERY_PROFILES.keys())}")

    p      = BATTERY_PROFILES[battery_id]
    cycles = p["max_cycles"]
    C0     = p["rated_capacity_ah"]

    records = []
    for n in range(1, cycles + 1):

        # ── Capacity fade model ───────────────────────────────
        # Exponential decay is a good approximation for Li-ion fade.
        # More precise models use sqrt(n) for SEI-dominated fade,
        # but exponential is standard in ML battery papers.
        #
        # capacity(n) = C0 * exp(-alpha * n) + gaussian_noise
        capacity = C0 * np.exp(-p["alpha"] * n)
        capacity += np.random.normal(0, 0.008)   # measurement noise
        capacity  = max(0.1, capacity)            # can't go below 0

        # ── State of Health (SoH) ─────────────────────────────
        # SoH = current capacity / initial rated capacity
        # 1.0 = brand new, 0.70 = End of Life
        soh = capacity / C0

        # ── Temperature ───────────────────────────────────────
        # Temperature varies cycle to cycle (lab conditions aren't perfect)
        # Higher temp → slightly faster degradation (captured in alpha)
        temp = np.random.normal(p["temp_mean_c"], p["temp_std_c"])
        temp = max(15.0, min(55.0, temp))

        # ── Internal Resistance ───────────────────────────────
        # Resistance grows approximately linearly with cycle number
        # and increases faster at high temperatures.
        # Units: milliohms (mΩ)
        base_resistance = 150 + (n * 0.6) + ((temp - 24) * 1.2)
        resistance = base_resistance + np.random.normal(0, 5)
        resistance = max(100, resistance)

        # ── Charge time ───────────────────────────────────────
        # As capacity fades, charge time decreases slightly
        # (less lithium to intercalate). CC-CV charging protocol.
        charge_time = 90 + (soh * 30) + np.random.normal(0, 3)
        charge_time = max(60, min(140, charge_time))

        # ── Discharge time ────────────────────────────────────
        # Directly proportional to remaining capacity
        discharge_time = (capacity / C0) * 90 + np.random.normal(0, 2)
        discharge_time = max(20, discharge_time)

        # ── Voltage drop under load ────────────────────────────
        # V_drop = I × R (Ohm's law)
        # As resistance increases, more voltage is lost to heat
        current       = 2.0   # A (1C discharge rate)
        voltage_drop  = (resistance / 1000) * current   # convert mΩ → Ω
        voltage_drop += np.random.normal(0, 0.01)
        voltage_drop  = max(0, voltage_drop)

        # ── Energy throughput ─────────────────────────────────
        # Total energy delivered this cycle (Wh)
        energy_wh = capacity * p["nominal_voltage"]

        # ── End of Life flag ──────────────────────────────────
        is_eol = soh < EOL_THRESHOLD

        # ── Remaining Useful Life ─────────────────────────────
        # How many cycles until EoL?
        # Solve: C0 * exp(-alpha * n_eol) = 0.70 * C0
        # → n_eol = -ln(0.70) / alpha
        import math
        n_eol = -math.log(EOL_THRESHOLD) / p["alpha"]
        rul   = max(0, int(n_eol - n))

        records.append({
            "battery_id":         battery_id,
            "cycle_number":       n,
            "capacity_ah":        round(capacity, 5),
            "rated_capacity_ah":  C0,
            "state_of_health":    round(soh, 5),
            "temperature_c":      round(temp, 2),
            "internal_resistance_mohm": round(resistance, 2),
            "charge_time_min":    round(charge_time, 2),
            "discharge_time_min": round(discharge_time, 2),
            "voltage_drop_v":     round(voltage_drop, 4),
            "energy_wh":          round(energy_wh, 4),
            "remaining_useful_life": rul,
            "is_end_of_life":     is_eol,
            "alpha":              p["alpha"],
            "temp_profile":       "High Temp" if p["temp_mean_c"] > 30 else "Room Temp",
        })

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────
# FUNCTION 2: Generate voltage-time profiles for one cycle
# ─────────────────────────────────────────────────────────────
def generate_voltage_profile(
    battery_id: str,
    cycle_numbers: list,
    points_per_cycle: int = 100,
) -> pd.DataFrame:
    """
    Generates detailed voltage vs. time profiles for specific cycles.
    Shows how the discharge curve changes as the battery ages.

    This is what NASA's raw data looks like — time-series voltage
    readings during a discharge cycle.

    Parameters
    ----------
    battery_id      : str  → battery to simulate
    cycle_numbers   : list → which cycles to generate (e.g. [1, 50, 100, 150])
    points_per_cycle: int  → how many time steps per cycle

    Returns
    -------
    pd.DataFrame → time, voltage, current, capacity_ah, cycle_number
    """
    p  = BATTERY_PROFILES[battery_id]
    C0 = p["rated_capacity_ah"]

    all_records = []

    for cycle_n in cycle_numbers:
        # Remaining capacity at this cycle
        remaining_cap = C0 * np.exp(-p["alpha"] * cycle_n)
        soh           = remaining_cap / C0

        # Time axis (normalized 0→1, then scaled to discharge time)
        discharge_time_min = soh * 90
        times = np.linspace(0, discharge_time_min, points_per_cycle)

        for t in times:
            # Normalized time (0 = start, 1 = end of discharge)
            t_norm = t / discharge_time_min if discharge_time_min > 0 else 0

            # Discharge voltage curve
            # New battery: flat plateau around 3.7V then sharp drop
            # Old battery: shorter plateau, drops sooner
            #
            # Modeled as a sigmoid-like curve:
            # V(t) = V_max - (V_max - V_min) * sigmoid(k*(t-t0))
            V_max    = p["charge_cutoff_v"] - 0.05
            V_min    = p["discharge_cutoff_v"] + 0.05
            plateau  = 0.75 * soh       # plateau region shrinks with age
            k        = 8 / (1 - plateau + 0.01)
            t0       = plateau
            sigmoid  = 1 / (1 + np.exp(-k * (t_norm - t0)))
            voltage  = V_max - (V_max - V_min) * sigmoid
            voltage += np.random.normal(0, 0.005)
            voltage  = max(V_min - 0.05, min(V_max + 0.05, voltage))

            # Capacity delivered so far (Ah)
            cap_delivered = remaining_cap * t_norm

            all_records.append({
                "battery_id":    battery_id,
                "cycle_number":  cycle_n,
                "time_min":      round(t, 3),
                "voltage_v":     round(voltage, 4),
                "current_a":     -2.0,              # constant 1C discharge
                "capacity_ah":   round(cap_delivered, 5),
                "state_of_health": round(soh, 4),
                "temp_c":        round(np.random.normal(p["temp_mean_c"], 1), 2),
            })

    return pd.DataFrame(all_records)


# ─────────────────────────────────────────────────────────────
# FUNCTION 3: Generate all batteries → save CSVs
# ─────────────────────────────────────────────────────────────
def generate_all_batteries(save: bool = True) -> tuple:
    """
    Generates cycle data and voltage profiles for all 4 batteries.

    Returns
    -------
    tuple → (df_cycles, df_voltage)
        df_cycles  : cycle-level summary (one row per cycle per battery)
        df_voltage : voltage-time profiles for early/mid/late cycles
    """
    ROOT_DIR   = Path(__file__).resolve().parent
    BATT_DIR   = ROOT_DIR / "data" / "raw" / "battery"
    BATT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*55}")
    print(f"  SolarStore AI — Battery Data Generator")
    print(f"{'='*55}\n")

    all_cycles   = []
    all_voltages = []

    for battery_id in BATTERY_PROFILES:
        p = BATTERY_PROFILES[battery_id]
        print(f"  🔋  {battery_id}  |  {p['max_cycles']} cycles  |  "
              f"temp: {p['temp_mean_c']}°C  |  alpha: {p['alpha']}")

        # Cycle-level data
        df_cyc = generate_cycle_data(battery_id)
        all_cycles.append(df_cyc)

        eol_cycle = df_cyc[df_cyc['is_end_of_life']]['cycle_number'].min()
        final_soh = df_cyc['state_of_health'].iloc[-1]
        print(f"          Final SoH: {final_soh:.3f}  |  "
              f"EoL at cycle: {eol_cycle if not pd.isna(eol_cycle) else 'Not reached'}")

        # Voltage profiles at early, mid, late cycles
        max_cyc    = p["max_cycles"]
        sample_cyc = [1,
                      max_cyc // 4,
                      max_cyc // 2,
                      int(max_cyc * 0.75),
                      max_cyc]
        df_volt = generate_voltage_profile(battery_id, sample_cyc)
        all_voltages.append(df_volt)

        if save:
            df_cyc.to_csv(BATT_DIR / f"{battery_id}_cycles.csv", index=False)
            df_volt.to_csv(BATT_DIR / f"{battery_id}_voltage_profiles.csv", index=False)

        print()

    df_cycles   = pd.concat(all_cycles,   ignore_index=True)
    df_voltages = pd.concat(all_voltages, ignore_index=True)

    if save:
        df_cycles.to_csv(  BATT_DIR / "all_batteries_cycles.csv",   index=False)
        df_voltages.to_csv(BATT_DIR / "all_batteries_voltage.csv",  index=False)
        print(f"  💾  Cycle data saved    → {BATT_DIR / 'all_batteries_cycles.csv'}")
        print(f"  💾  Voltage data saved  → {BATT_DIR / 'all_batteries_voltage.csv'}")

    print(f"\n  📊  Cycles dataset:   {df_cycles.shape[0]:,} rows × {df_cycles.shape[1]} cols")
    print(f"  📊  Voltage dataset:  {df_voltages.shape[0]:,} rows × {df_voltages.shape[1]} cols")
    print(f"{'='*55}\n")

    return df_cycles, df_voltages


# ─────────────────────────────────────────────────────────────
# Run directly
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ROOT_DIR = Path(__file__).resolve().parent
    BATT_DIR = ROOT_DIR / "data" / "raw" / "battery"
    BATT_DIR.mkdir(parents=True, exist_ok=True)

    df_cycles, df_voltages = generate_all_batteries(save=True)

    print("Sample cycle data:")
    print(df_cycles.head(5).to_string(index=False))
    print("\nSoH at end of life per battery:")
    print(df_cycles.groupby("battery_id")["state_of_health"].agg(["first","last"]).round(4))
