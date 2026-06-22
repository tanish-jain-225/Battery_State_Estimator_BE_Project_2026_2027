import os
from dotenv import load_dotenv

# Load environmental variables from .env file in the simulator directory
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, '.env'))

class Config:
    # -------------------------------------------------------------------------
    # MongoDB configuration
    # -------------------------------------------------------------------------
    MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "battery_estimation_db")
    MONGODB_READINGS_COLLECTION = os.environ.get("MONGODB_READINGS_COLLECTION", "readings")
    MONGODB_STATE_COLLECTION = os.environ.get("MONGODB_STATE_COLLECTION", "sim_state")

    # -------------------------------------------------------------------------
    # Flask server settings
    # -------------------------------------------------------------------------
    PORT = int(os.environ.get("PORT", 8000))
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "t", "yes")

    # -------------------------------------------------------------------------
    # Simulation step timing
    # -------------------------------------------------------------------------
    # Real-time pacing interval (seconds per simulated second)
    SIMULATION_STEP_DELAY = float(os.environ.get("SIMULATION_STEP_DELAY", 1.0))

    # -------------------------------------------------------------------------
    # BMS Sensor Noise Standard Deviations
    # -------------------------------------------------------------------------
    DEFAULT_NOISE_VOLTAGE     = float(os.environ.get("DEFAULT_NOISE_VOLTAGE", 0.005))   # Volts
    DEFAULT_NOISE_CURRENT     = float(os.environ.get("DEFAULT_NOISE_CURRENT", 0.05))    # Amperes
    DEFAULT_NOISE_TEMPERATURE = float(os.environ.get("DEFAULT_NOISE_TEMPERATURE", 0.2)) # °C

    # -------------------------------------------------------------------------
    # Fault injection physics constants
    # -------------------------------------------------------------------------
    FAULT_SHORT_LEAKAGE_CURRENT    = float(os.environ.get("FAULT_SHORT_LEAKAGE_CURRENT", 0.8))   # A
    FAULT_SHORT_HEATING_RATE       = float(os.environ.get("FAULT_SHORT_HEATING_RATE", 4.5))       # W
    FAULT_THERMAL_RUNAWAY_MULT     = float(os.environ.get("FAULT_THERMAL_RUNAWAY_MULT", 4.0))     # multiplier
    FAULT_THERMAL_RUNAWAY_EXP      = float(os.environ.get("FAULT_THERMAL_RUNAWAY_EXP", 0.09))     # exponential factor

    # -------------------------------------------------------------------------
    # CPS Diagnostic fault-detection thresholds
    # -------------------------------------------------------------------------
    # Voltage below this is treated as sensor dropout (V)
    DIAG_DROPOUT_VOLTAGE_THRESHOLD  = float(os.environ.get("DIAG_DROPOUT_VOLTAGE_THRESHOLD", 1.0))
    # Cell temperature above this triggers thermal runaway alarm (°C)
    DIAG_THERMAL_TEMP_THRESHOLD     = float(os.environ.get("DIAG_THERMAL_TEMP_THRESHOLD", 60.0))
    # Rate-of-temperature-change above this triggers thermal runaway alarm (°C/s)
    DIAG_THERMAL_RATE_THRESHOLD     = float(os.environ.get("DIAG_THERMAL_RATE_THRESHOLD", 2.0))
    # SOC divergence (CC minus EKF) above this, at near-zero current, signals micro-short (ratio)
    DIAG_SHORT_SOC_DIFF_THRESHOLD   = float(os.environ.get("DIAG_SHORT_SOC_DIFF_THRESHOLD", 0.08))
    # Maximum absolute current for the micro-short diagnostic to trigger (A)
    DIAG_SHORT_CURRENT_THRESHOLD    = float(os.environ.get("DIAG_SHORT_CURRENT_THRESHOLD", 0.1))

    # -------------------------------------------------------------------------
    # ESN feature engineering
    # -------------------------------------------------------------------------
    # Rolling window size for moving-average features; must match training config
    FEATURE_ROLLING_WINDOW = int(os.environ.get("FEATURE_ROLLING_WINDOW", 5))

