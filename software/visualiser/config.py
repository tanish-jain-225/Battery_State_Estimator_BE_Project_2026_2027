import os
from dotenv import load_dotenv

# Load environmental variables from .env file explicitly using absolute path
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, '.env'))

class Config:
    # -------------------------------------------------------------------------
    # MongoDB configuration (Atlas URI in production, Localhost in development)
    # -------------------------------------------------------------------------
    MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "battery_estimation_db")
    MONGODB_READINGS_COLLECTION = os.environ.get("MONGODB_READINGS_COLLECTION", "readings")
    MONGODB_STATE_COLLECTION = os.environ.get("MONGODB_STATE_COLLECTION", "sim_state")

    # -------------------------------------------------------------------------
    # Flask server settings
    # -------------------------------------------------------------------------
    PORT = int(os.environ.get("PORT", 5000))
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "t", "yes")
    SIMULATOR_URL = os.environ.get("SIMULATOR_URL", "http://127.0.0.1:8000")

    # -------------------------------------------------------------------------
    # File paths
    # -------------------------------------------------------------------------
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    model_env = os.environ.get("MODEL_PATH", "model_rc.pkl")
    MODEL_PATH = model_env if os.path.isabs(model_env) else os.path.join(BASE_DIR, model_env)

    csv_env = os.environ.get("CSV_PATH", os.path.join("datasets", "training_ev_battery_dataset_multiclass.csv"))
    CSV_PATH = csv_env if os.path.isabs(csv_env) else os.path.join(BASE_DIR, csv_env)

    # -------------------------------------------------------------------------
    # Physical battery simulator parameters
    # -------------------------------------------------------------------------
    # Time step between simulator ticks (seconds). Controls real-time pacing.
    SIMULATION_STEP_DELAY = float(os.environ.get("SIMULATION_STEP_DELAY", 1.0))

    # -------------------------------------------------------------------------
    # Telemetry storage limits
    # -------------------------------------------------------------------------
    # Maximum readings returned per /api/telemetry call (prevents large browser payloads)
    TELEMETRY_RESPONSE_LIMIT = int(os.environ.get("TELEMETRY_RESPONSE_LIMIT", 150))

    # Rolling points limit for dashboard graph visualization
    GRAPH_SLICE_LIMIT = int(os.environ.get("GRAPH_SLICE_LIMIT", 120))

    # Maximum in-memory fallback list size when MongoDB is offline
    TELEMETRY_FALLBACK_LIMIT = int(os.environ.get("TELEMETRY_FALLBACK_LIMIT", 1000))

    # -------------------------------------------------------------------------
    # Feature engineering parameters
    # -------------------------------------------------------------------------
    # Rolling window size for moving-average features (Current_ma, Temp_ma).
    # Must be consistent between offline training and online inference.
    FEATURE_ROLLING_WINDOW = int(os.environ.get("FEATURE_ROLLING_WINDOW", 5))

    # Time resolution (seconds per row) of the training CSV dataset.
    # Used to normalise the Voltage_grad feature so training and runtime units match.
    DATASET_TIME_STEP = float(os.environ.get("DATASET_TIME_STEP", 0.001))

    # Indices into the 6-element raw feature vector [Voltage, Current, Temperature,
    # Voltage_grad, Current_ma, Temp_ma] to select for ESN input.
    # Default: [0, 1, 3, 4] = Voltage, Current, Voltage_grad, Current_ma
    # (Temperature features excluded to prevent out-of-distribution bias)
    ESN_SELECTED_FEATURE_INDICES = [0, 1, 3, 4]

    # -------------------------------------------------------------------------
    # ESN reservoir priming & training washout
    # -------------------------------------------------------------------------
    # Steps to run before recording reservoir states during training.
    # Discards the uninitialised zero-state phase so readout weights are fitted
    # only on settled reservoir activations.
    ESN_WASHOUT_STEPS = int(os.environ.get("ESN_WASHOUT_STEPS", 50))

    # Steps to drive the reservoir at startup/reset before going live.
    # Eliminates the 30-50 second convergence lag at simulation start.
    ESN_PRIMING_STEPS = int(os.environ.get("ESN_PRIMING_STEPS", 50))

    # -------------------------------------------------------------------------
    # SOC Echo State Network hyperparameters
    # -------------------------------------------------------------------------
    ESN_SOC_RESERVOIR    = int(os.environ.get("ESN_SOC_RESERVOIR", 300))
    ESN_SOC_SPECTRAL_RADIUS = float(os.environ.get("ESN_SOC_SPECTRAL_RADIUS", 0.90))
    ESN_SOC_LEAK_RATE    = float(os.environ.get("ESN_SOC_LEAK_RATE", 0.3))
    ESN_SOC_INPUT_SCALING = float(os.environ.get("ESN_SOC_INPUT_SCALING", 0.8))
    ESN_SOC_RIDGE_PARAM  = float(os.environ.get("ESN_SOC_RIDGE_PARAM", 1e-4))
    ESN_SOC_SPARSITY     = float(os.environ.get("ESN_SOC_SPARSITY", 0.85))

    # -------------------------------------------------------------------------
    # SOH Echo State Network hyperparameters
    # -------------------------------------------------------------------------
    ESN_SOH_RESERVOIR    = int(os.environ.get("ESN_SOH_RESERVOIR", 200))
    ESN_SOH_SPECTRAL_RADIUS = float(os.environ.get("ESN_SOH_SPECTRAL_RADIUS", 0.70))
    ESN_SOH_LEAK_RATE    = float(os.environ.get("ESN_SOH_LEAK_RATE", 0.05))
    ESN_SOH_INPUT_SCALING = float(os.environ.get("ESN_SOH_INPUT_SCALING", 0.4))
    ESN_SOH_RIDGE_PARAM  = float(os.environ.get("ESN_SOH_RIDGE_PARAM", 1e-3))
    ESN_SOH_SPARSITY     = float(os.environ.get("ESN_SOH_SPARSITY", 0.85))

    # -------------------------------------------------------------------------
    # BMS Sensor Noise Base Standard Deviations
    # -------------------------------------------------------------------------
    DEFAULT_NOISE_VOLTAGE = float(os.environ.get("DEFAULT_NOISE_VOLTAGE", 0.005))       # Volts
    DEFAULT_NOISE_CURRENT = float(os.environ.get("DEFAULT_NOISE_CURRENT", 0.05))        # Amperes
    DEFAULT_NOISE_TEMPERATURE = float(os.environ.get("DEFAULT_NOISE_TEMPERATURE", 0.2)) # °C

    # -------------------------------------------------------------------------
    # CPS Fault Injection Parameters
    # -------------------------------------------------------------------------
    FAULT_SHORT_LEAKAGE_CURRENT = float(os.environ.get("FAULT_SHORT_LEAKAGE_CURRENT", 0.8))  # Amperes
    FAULT_SHORT_HEATING_RATE = float(os.environ.get("FAULT_SHORT_HEATING_RATE", 4.5))        # Watts (Joule heating term)
    FAULT_THERMAL_RUNAWAY_MULT = float(os.environ.get("FAULT_THERMAL_RUNAWAY_MULT", 4.0))    # Rate multiplier
    FAULT_THERMAL_RUNAWAY_EXP = float(os.environ.get("FAULT_THERMAL_RUNAWAY_EXP", 0.09))     # Exponential factor
