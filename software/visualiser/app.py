import sys
import os
import time
import urllib.request
import json
import pickle
import threading
from datetime import datetime
import numpy as np
import pandas as pd

# Add local directories to path for clean imports
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)
training_dir = os.path.join(base_dir, 'training')
if training_dir not in sys.path:
    sys.path.append(training_dir)

from flask import Flask, jsonify, request, render_template
from pymongo import MongoClient
try:
    from software.visualiser.config import Config
except ImportError:
    from config import Config
from train_rc import EchoStateNetwork
sys.modules['__main__'].EchoStateNetwork = EchoStateNetwork

# Dynamic imports from local modules
from battery_simulator import BatterySimulator, DriveCycles
from battery_chemistry import get_chemistry, register_chemistry
from estimator_pipeline import EstimatorPipeline

# System resource monitor fallback
try:
    import psutil
    def get_system_metrics():
        process = psutil.Process(os.getpid())
        return process.cpu_percent(), process.memory_info().rss / (1024 * 1024)
except Exception:
    def get_system_metrics():
        return 1.2, 48.5

app = Flask(__name__)

def get_shared_secret():
    secret = os.environ.get("API_KEY", getattr(Config, "API_KEY", None))
    if secret and secret != "change_this_to_a_secure_random_key_in_production":
        return secret
    return None

def verify_request_auth():
    # Loopback addresses (localhost) bypass auth checks in dev/local environments
    remote = request.remote_addr
    if remote in ('127.0.0.1', '::1', 'localhost'):
        return True
        
    secret = get_shared_secret()
    if not secret:
        is_prod = os.environ.get('RENDER') == 'true' or os.environ.get('SERVERLESS') == '1'
        return not is_prod
    
    # Check header
    header_key = request.headers.get("X-API-Key")
    if header_key == secret:
        return True
        
    # Check query param as fallback
    query_key = request.args.get("api_key")
    if query_key == secret:
        return True
        
    return False


def make_simulator_request(path, method='GET', data=None, timeout=1.0):
    url = f"{Config.SIMULATOR_URL}{path}"
    headers = {}
    
    secret = get_shared_secret()
    if secret:
        headers["X-API-Key"] = secret
        
    encoded_data = None
    if data is not None:
        encoded_data = json.dumps(data).encode('utf-8')
        headers["Content-Type"] = "application/json"
        
    req = urllib.request.Request(
        url,
        data=encoded_data,
        headers=headers,
        method=method
    )
    return urllib.request.urlopen(req, timeout=timeout)

import atexit
import tempfile

# Serverless support detection
IS_SERVERLESS = os.environ.get('SERVERLESS') == '1'

# Non-blocking async cache variables
_simulator_port_online = False
_simulator_port_data = None
_mongodb_connected = False

mongodb_uri = Config.MONGODB_URI
db_client = None
db = None
mongodb_connected = False

_last_db_ping_time = 0.0

def check_db_connected():
    global db_client, db, mongodb_connected, _last_db_ping_time
    now = time.time()
    if mongodb_connected and db is not None:
        # Rate-limit database pings to once every 10 seconds to eliminate HTTP blocking lag
        if now - _last_db_ping_time < 10.0:
            return True
        try:
            db_client.admin.command('ping')
            _last_db_ping_time = now
            return True
        except Exception:
            mongodb_connected = False
            db_client = None
            db = None
            
    try:
        db_client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=2000)
        db_client.admin.command('ping')
        _last_db_ping_time = now
        db = db_client[Config.MONGODB_DB_NAME]
        mongodb_connected = True
        return True
    except Exception as e:
        print(f"Visualiser Database connection failed: {e}")
        mongodb_connected = False
        db_client = None
        db = None
        return False

# Establish connection at startup
check_db_connected()

# Default state parameters for fallback
DEFAULT_SIM_STATE = {
    'chemistry': 'li_ion',
    'time': 0.0,
    'soc': 1.0,
    'soh': 1.0,
    'sim_running': False,
    'active_cycle': 'udds',
    'accelerated_aging': False,
    'ekf_mismatch': 1.0,
    'quantize_mode': 'float32',
    'ekf_q_soc': 1e-7,
    'ekf_q_v1': 1e-6,
    'ekf_q_v2': 1e-6,
    'ekf_r_meas': 0.01,
    'fault_short_leakage': 0.8,
    'fault_thermal_runaway_mult': 4.0,
}

# Load trained Reservoir Computing model
model_loaded = False
esn_soc = None
esn_soh = None
input_means = None
input_stds = None
model_path = Config.MODEL_PATH
loaded_soc_rmse = None
loaded_soh_rmse = None
_last_fetched_df = None  # Cache for last successfully fetched/generated dataset for fallback

def init_previous_data():
    """Fetch/load previous dataset into memory on start always."""
    global _last_fetched_df
    if _last_fetched_df is not None and not _last_fetched_df.empty:
        return _last_fetched_df

    csv_path = Config.CSV_PATH
    if os.path.exists(csv_path):
        try:
            _last_fetched_df = pd.read_csv(csv_path)
            training_status['training_source'] = 'Previously Loaded Data'
            print(f"[STARTUP] Loaded previous dataset into memory from {csv_path} ({len(_last_fetched_df)} rows).")
            return _last_fetched_df
        except Exception as e:
            print(f"[STARTUP] Could not read local CSV at startup: {e}")

    try:
        from train_rc import generate_full_range_dataset
        _last_fetched_df = generate_full_range_dataset()
        training_status['training_source'] = 'Previously Loaded Data'
        print(f"[STARTUP] Generated initial previous dataset in memory ({len(_last_fetched_df)} rows).")
        return _last_fetched_df
    except Exception as e:
        print(f"[STARTUP] Could not generate initial dataset: {e}")
        return None

# Shared state for background ESN training
training_status = {
    'status': 'idle',
    'logs': '',
    'soc_rmse': 0.0,
    'soh_rmse': 0.0,
    'timestamp': None,
    'training_source': None   # 'Doc Link Data' | 'Previously Loaded Data' | 'Local Trained File Data'
}

# Incremental pipeline state cache for /api/telemetry
# Avoids re-running the full estimator history on every poll (O(N) → O(new))
_telemetry_cache = {
    'key':       None,   # cache_key string — invalidated on config change
    'pipeline':  None,   # EstimatorPipeline instance with warm state
    'processed': [],     # list of already-processed output records
    'n_cached':  0       # number of raw_readings already processed
}

class SafeUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if name == "EchoStateNetwork":
            return EchoStateNetwork
        # Remap numpy._core -> numpy.core (handles loading NumPy 2.x pickles on NumPy 1.x environments)
        if module.startswith("numpy._core"):
            module = module.replace("numpy._core", "numpy.core")
        # Remap numpy.core -> numpy._core (handles loading older pickles on environments where numpy.core is missing)
        elif module.startswith("numpy.core"):
            try:
                import numpy._core
                module = module.replace("numpy.core", "numpy._core")
            except ImportError:
                pass
        return super().find_class(module, name)

def safe_pickle_loads(data):
    import io
    return SafeUnpickler(io.BytesIO(data)).load()

def safe_pickle_load(fileobj):
    return SafeUnpickler(fileobj).load()

def _model_score(soc_rmse, soh_rmse):
    soc_val = float(soc_rmse) if soc_rmse is not None else float('inf')
    soh_val = float(soh_rmse) if soh_rmse is not None else float('inf')
    return soc_val + soh_val

def load_ml_model():
    global esn_soc, esn_soh, input_means, input_stds, model_loaded, loaded_soc_rmse, loaded_soh_rmse

    candidates = []
    
    # First: Try to load from MongoDB Registry (supports serverless read-only filesystem)
    if check_db_connected():
        try:
            print(f"[DEBUG] MongoDB collections found: {db.list_collection_names()}")
            print(f"[DEBUG] Documents in model_weights: {list(db['model_weights'].find({}, {'pickle_data': False}))}")
            db_model = db['model_weights'].find_one({'_id': 'esn_package'})
            if db_model is not None:
                package = safe_pickle_loads(db_model['pickle_data'])
                candidates.append({
                    'source': 'MongoDB model registry',
                    'package': package,
                    'soc_rmse': db_model.get('soc_rmse', package.get('soc_rmse')),
                    'soh_rmse': db_model.get('soh_rmse', package.get('soh_rmse')),
                })
            else:
                print("MongoDB model registry is empty. Falling back to local model if available.")
        except Exception as e:
            print(f"Error loading model from MongoDB registry: {e}")

    # Fallback: Load from local pickle file as well, then choose the best available package.
    if os.path.exists(model_path):
        try:
            with open(model_path, 'rb') as f:
                package = safe_pickle_load(f)
                candidates.append({
                    'source': 'local file',
                    'package': package,
                    'soc_rmse': package.get('soc_rmse'),
                    'soh_rmse': package.get('soh_rmse'),
                })
        except Exception as e:
            print(f"Error loading local model file: {e}")

    if candidates:
        best_candidate = min(candidates, key=lambda item: _model_score(item['soc_rmse'], item['soh_rmse']))
        package = best_candidate['package']
        esn_soc = package['esn_soc']
        esn_soh = package['esn_soh']
        input_means = package['input_means']
        input_stds = package['input_stds']
        model_loaded = True
        loaded_soc_rmse = best_candidate['soc_rmse']
        loaded_soh_rmse = best_candidate['soh_rmse']
        print(f"Echo State Networks loaded successfully from {best_candidate['source']} (score={_model_score(loaded_soc_rmse, loaded_soh_rmse):.6f}).")
        return

    else:
        esn_soc = None
        esn_soh = None
        input_means = None
        input_stds = None
        model_loaded = False
        loaded_soc_rmse = None
        loaded_soh_rmse = None
        print("Warning: Model not found locally or on DB. Running with blank weights.")

_last_sim_port_check_time = 0.0

def check_simulator_port(force=False):
    global _simulator_port_online, _simulator_port_data, _last_sim_port_check_time
    now = time.time()
    check_interval = 20.0 if IS_SERVERLESS else 1.5
    if force or (now - _last_sim_port_check_time >= check_interval):
        _last_sim_port_check_time = now
        try:
            with make_simulator_request("/api/status", timeout=0.8) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    _simulator_port_online = True
                    _simulator_port_data = data
                    return True, data
        except Exception:
            pass
        _simulator_port_online = False
        _simulator_port_data = None
        return False, None
        
    return _simulator_port_online, _simulator_port_data

# Shared state memory
local_sim_state = DEFAULT_SIM_STATE.copy()
visualiser_simulator = BatterySimulator()
current_chemistry = None
local_telemetry_buffer = []

def load_sim_state():
    if check_db_connected():
        try:
            state = db[Config.MONGODB_STATE_COLLECTION].find_one({'_id': 'singleton'})
            if state is not None:
                state.pop('_id', None)
                local_sim_state.update(state)
                return state
        except Exception as e:
            print(f"Error loading state from MongoDB: {e}")
    return local_sim_state

def save_sim_state(state):
    global local_sim_state
    local_sim_state = state
    if check_db_connected():
        try:
            state_copy = state.copy()
            state_copy['_id'] = 'singleton'
            db[Config.MONGODB_STATE_COLLECTION].replace_one({'_id': 'singleton'}, state_copy, upsert=True)
        except Exception as e:
            print(f"Error saving state to MongoDB: {e}")

def update_sim_progress(progress_dict):
    local_sim_state.update(progress_dict)
    if check_db_connected():
        try:
            db[Config.MONGODB_STATE_COLLECTION].update_one(
                {'_id': 'singleton'},
                {'$set': progress_dict},
                upsert=True
            )
        except Exception as e:
            print(f"Error updating simulation progress in MongoDB: {e}")

def sync_simulation_locally():
    global current_chemistry
    if not IS_SERVERLESS:
        return
        
    state = load_sim_state()
    sim_running = state.get('sim_running', False)
    if not sim_running:
        if state.get('time', 0.0) == 0.0 and visualiser_simulator.time != 0.0:
            chemistry_name = state.get('chemistry', 'li_ion')
            visualiser_simulator.reset(chemistry_name)
            current_chemistry = chemistry_name
        return

    last_real_time = state.get('last_real_time')
    if not last_real_time:
        update_sim_progress({'last_real_time': time.time()})
        return

    now = time.time()
    step_delay = Config.SIMULATION_STEP_DELAY
    elapsed = now - last_real_time
    steps = int(elapsed / step_delay)

    if steps <= 0:
        return

    # Cap steps to protect performance
    steps = min(steps, 50)

    chemistry_name = state.get('chemistry', 'li_ion')
    if chemistry_name != current_chemistry:
        if state.get('time', 0.0) == 0.0:
            visualiser_simulator.reset(chemistry_name)
        else:
            visualiser_simulator.change_chemistry(chemistry_name)
        current_chemistry = chemistry_name

    # Load starting physical states
    visualiser_simulator.time = state.get('time', 0.0)
    visualiser_simulator.soc = state.get('soc', 1.0)
    visualiser_simulator.soh = state.get('soh', 1.0)
    visualiser_simulator.V1 = state.get('V1', 0.0)
    visualiser_simulator.V2 = state.get('V2', 0.0)
    visualiser_simulator.temperature = state.get('temperature', 25.0)
    visualiser_simulator.internal_resistance_growth = state.get('internal_resistance_growth', 1.0)
    visualiser_simulator.T_ambient = state.get('T_ambient', 25.0)

    active_cycle = state.get('active_cycle', 'udds')
    accelerated_aging = state.get('accelerated_aging', False)
    fault_thermal = state.get('fault_thermal', False)
    fault_dropout = state.get('fault_dropout', False)
    fault_short = state.get('fault_short', False)

    V_meas, I_meas = 0.0, 0.0

    for _ in range(steps):
        t = visualiser_simulator.time
        if active_cycle == "udds":
            I = DriveCycles.udds(t)
        elif active_cycle == "hwfet":
            I = DriveCycles.hwfet(t)
        elif active_cycle == "us06":
            I = DriveCycles.us06(t)
        elif active_cycle == "constant":
            I = DriveCycles.constant_discharge(t)
        elif active_cycle == "charge":
            I = DriveCycles.cccv_charge(t, visualiser_simulator.soc)
        else:
            I = 0.0

        out = visualiser_simulator.step(
            I, step_delay,
            accelerated_aging=accelerated_aging,
            fault_thermal=fault_thermal,
            fault_dropout=fault_dropout,
            fault_short=fault_short
        )

        noisy = visualiser_simulator.add_sensor_noise(
            out,
            v_noise=Config.DEFAULT_NOISE_VOLTAGE,
            i_noise=Config.DEFAULT_NOISE_CURRENT,
            t_noise=Config.DEFAULT_NOISE_TEMPERATURE,
            fault_dropout=fault_dropout
        )

        V_meas = noisy['voltage']
        I_meas = noisy['current']
        T_meas = noisy['temperature']

        record = {
            'time': out['time'],
            'voltage': V_meas,
            'current': -I_meas,
            'temperature': T_meas,
            'timestamp': datetime.utcnow().isoformat(),
            'fault_short': fault_short,
            'fault_thermal': fault_thermal,
            'fault_dropout': fault_dropout,
            'true_soc': out['true_soc'],
            'true_soh': out['true_soh'],
            'true_v1': out['v1'],
            'true_v2': out['v2'],
            'true_r0': out['R0'],
            'true_ocv': out['ocv'],
            'true_voltage': out['voltage'],
            'true_current': -out['current']
        }

        if check_db_connected():
            # Check if this reading already exists to prevent duplicate inserts from concurrent workers/instances
            exists = db[Config.MONGODB_READINGS_COLLECTION].find_one({'time': out['time']})
            if not exists:
                db[Config.MONGODB_READINGS_COLLECTION].insert_one(record)
        else:
            # Make sure we don't duplicate locally either
            if not any(r['time'] == record['time'] for r in local_telemetry_buffer):
                local_telemetry_buffer.append(record)
                if len(local_telemetry_buffer) > Config.TELEMETRY_FALLBACK_LIMIT:
                    local_telemetry_buffer.pop(0)

    update_sim_progress({
        'time': visualiser_simulator.time,
        'soc': visualiser_simulator.soc,
        'soh': visualiser_simulator.soh,
        'V1': visualiser_simulator.V1,
        'V2': visualiser_simulator.V2,
        'temperature': visualiser_simulator.temperature,
        'internal_resistance_growth': visualiser_simulator.internal_resistance_growth,
        'last_real_time': last_real_time + steps * step_delay,
        'prev_voltage': V_meas,
        'prev_current': -I_meas
    })

# ── Asynchronous Status Checker & Simulation Threads (Standalone mode) ──

def status_checker_loop():
    global _simulator_port_online, _simulator_port_data, _mongodb_connected, db_client, db
    print("Visualizer background status checker thread active.")
    
    # Try initial mongo connection
    try:
        db_client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=2000)
        db_client.server_info()
        db = db_client[Config.MONGODB_DB_NAME]
        _mongodb_connected = True
        try:
            db[Config.MONGODB_READINGS_COLLECTION].create_index([("time", 1)])
        except Exception:
            pass
    except Exception:
        _mongodb_connected = False
        db_client = None
        db = None

    while True:
        # 1. Asynchronously check Simulator Port
        try:
            with make_simulator_request("/api/status", timeout=1.0) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    _simulator_port_online = True
                    _simulator_port_data = data
                else:
                    _simulator_port_online = False
                    _simulator_port_data = None
        except Exception:
            _simulator_port_online = False
            _simulator_port_data = None

        # 2. Asynchronously check MongoDB Connection
        if not _mongodb_connected or db_client is None:
            try:
                db_client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=2000)
                db_client.server_info()
                db = db_client[Config.MONGODB_DB_NAME]
                _mongodb_connected = True
                try:
                    db[Config.MONGODB_READINGS_COLLECTION].create_index([("time", 1)])
                except Exception:
                    pass
            except Exception:
                _mongodb_connected = False
                db_client = None
                db = None
        else:
            try:
                db_client.server_info()
                _mongodb_connected = True
            except Exception:
                _mongodb_connected = False
                db_client = None
                db = None

        time.sleep(3.0)

def local_generator_loop():
    global current_chemistry
    print("Visualizer local simulator background thread active.")
    last_loop_time = time.time()
    
    while True:
        try:
            # If the simulator server port is online, let it generate the data
            port_online, _ = check_simulator_port()
            if port_online:
                time.sleep(1.0)
                last_loop_time = time.time()
                continue
                
            state = load_sim_state()
            sim_running = state.get('sim_running', False)
            chemistry_name = state.get('chemistry', 'li_ion')
            active_cycle = state.get('active_cycle', 'udds')
            accelerated_aging = state.get('accelerated_aging', False)
            T_ambient = state.get('T_ambient', 25.0)
            fault_thermal = state.get('fault_thermal', False)
            fault_dropout = state.get('fault_dropout', False)
            fault_short = state.get('fault_short', False)
            step_delay = Config.SIMULATION_STEP_DELAY
            
            # Sync chemistry
            if chemistry_name != current_chemistry:
                if state.get('time', 0.0) == 0.0:
                    visualiser_simulator.reset(chemistry_name)
                else:
                    visualiser_simulator.change_chemistry(chemistry_name)
                current_chemistry = chemistry_name
                print(f"Local simulator chemistry loaded: {chemistry_name.upper()}")
                
            if sim_running:
                # Sync physical parameters
                visualiser_simulator.time = state.get('time', 0.0)
                visualiser_simulator.soc = state.get('soc', 1.0)
                visualiser_simulator.soh = state.get('soh', 1.0)
                visualiser_simulator.V1 = state.get('V1', 0.0)
                visualiser_simulator.V2 = state.get('V2', 0.0)
                visualiser_simulator.temperature = state.get('temperature', 25.0)
                visualiser_simulator.internal_resistance_growth = state.get('internal_resistance_growth', 1.0)
                visualiser_simulator.T_ambient = T_ambient
                
                # Retrieve cycle current excitation (I)
                t = visualiser_simulator.time
                if active_cycle == "udds":
                    I = DriveCycles.udds(t)
                elif active_cycle == "hwfet":
                    I = DriveCycles.hwfet(t)
                elif active_cycle == "us06":
                    I = DriveCycles.us06(t)
                elif active_cycle == "constant":
                    I = DriveCycles.constant_discharge(t)
                elif active_cycle == "charge":
                    I = DriveCycles.cccv_charge(t, visualiser_simulator.soc)
                else:
                    I = 0.0
                    
                # Step physics
                out = visualiser_simulator.step(
                    I, step_delay, 
                    accelerated_aging=accelerated_aging,
                    fault_thermal=fault_thermal,
                    fault_dropout=fault_dropout,
                    fault_short=fault_short
                )
                
                # Apply nominal noise bounds
                noisy = visualiser_simulator.add_sensor_noise(
                    out,
                    v_noise=Config.DEFAULT_NOISE_VOLTAGE,
                    i_noise=Config.DEFAULT_NOISE_CURRENT,
                    t_noise=Config.DEFAULT_NOISE_TEMPERATURE,
                    fault_dropout=fault_dropout
                )
                
                V_meas = noisy['voltage']
                I_meas = noisy['current']
                T_meas = noisy['temperature']
                
                record = {
                    'time': out['time'],
                    'voltage': V_meas,
                    'current': -I_meas,  # positive = discharge, negative = charge
                    'temperature': T_meas,
                    'timestamp': datetime.utcnow().isoformat(),
                    'fault_short': fault_short,
                    'fault_thermal': fault_thermal,
                    'fault_dropout': fault_dropout,
                    
                    # True ground truth reference properties
                    'true_soc': out['true_soc'],
                    'true_soh': out['true_soh'],
                    'true_v1': out['v1'],
                    'true_v2': out['v2'],
                    'true_r0': out['R0'],
                    'true_ocv': out['ocv'],
                    'true_voltage': out['voltage'],
                    'true_current': -out['current']
                }
                
                # Push record to readings collection
                if check_db_connected():
                    db[Config.MONGODB_READINGS_COLLECTION].insert_one(record)
                else:
                    local_telemetry_buffer.append(record)
                    if len(local_telemetry_buffer) > Config.TELEMETRY_FALLBACK_LIMIT:
                        local_telemetry_buffer.pop(0)
                    
                # Update configuration document
                update_sim_progress({
                    'time': visualiser_simulator.time,
                    'soc': visualiser_simulator.soc,
                    'soh': visualiser_simulator.soh,
                    'V1': visualiser_simulator.V1,
                    'V2': visualiser_simulator.V2,
                    'temperature': visualiser_simulator.temperature,
                    'internal_resistance_growth': visualiser_simulator.internal_resistance_growth,
                    'last_real_time': time.time(),
                    'prev_voltage': V_meas,
                    'prev_current': -I_meas
                })
                
                # Sleep interval
                now = time.time()
                elapsed = now - last_loop_time
                sleep_time = max(0.02, step_delay - elapsed)
                time.sleep(sleep_time)
                last_loop_time = time.time()
            else:
                # Idle reset check
                if state.get('time', 0.0) == 0.0 and visualiser_simulator.time != 0.0:
                    visualiser_simulator.reset(chemistry_name)
                    print("Local simulator baseline states reset.")
                time.sleep(0.5)
                last_loop_time = time.time()
        except Exception as e:
            print(f"Local simulator thread exception: {e}")
            time.sleep(1.0)

LOCK_FILE = os.path.join(tempfile.gettempdir(), 'visualiser_simulator_thread.lock')

def _is_pid_alive(pid):
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
        return True
    except (OSError, SystemError):
        return False
    except (AttributeError, ValueError):
        try:
            import subprocess
            out = subprocess.check_output(f'tasklist /FI "PID eq {pid}"', shell=True, stderr=subprocess.DEVNULL)
            return str(pid) in out.decode()
        except Exception:
            return True

def _acquire_lock():
    pid = os.getpid()
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, 'w') as f:
            f.write(str(pid))
        return True
    except FileExistsError:
        try:
            with open(LOCK_FILE, 'r') as f:
                holder_pid = int(f.read().strip())
        except Exception:
            holder_pid = None

        if holder_pid is None:
            try:
                os.remove(LOCK_FILE)
            except Exception:
                pass
            return _acquire_lock()

        if not _is_pid_alive(holder_pid):
            try:
                os.remove(LOCK_FILE)
            except Exception:
                pass
            return _acquire_lock()
        else:
            return False

def _release_lock():
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, 'r') as f:
                holder_pid = int(f.read().strip())
            if holder_pid == os.getpid():
                os.remove(LOCK_FILE)
    except Exception:
        pass

atexit.register(_release_lock)

_local_threads_started = False
_checker_thread_started = False

def _start_background_threads():
    global _local_threads_started, _checker_thread_started
    if IS_SERVERLESS:
        return
        
    # Start status checker thread unconditionally for every process/worker
    if not _checker_thread_started:
        _checker_thread_started = True
        checker = threading.Thread(target=status_checker_loop, daemon=True)
        checker.start()
        
    # Start local generator fallback simulator ONLY if we acquire the lock
    if not _local_threads_started:
        if _acquire_lock():
            _local_threads_started = True
            sim_thread = threading.Thread(target=local_generator_loop, daemon=True)
            sim_thread.start()
            print(f"Visualizer local simulator thread active (PID: {os.getpid()}).")

# Lazy-start threads on first HTTP request when running under WSGI servers like Gunicorn
_lazy_initialized = False
_lazy_lock = threading.Lock()

@app.before_request
def _lazy_init():
    global _lazy_initialized
    if not _lazy_initialized:
        with _lazy_lock:
            if not _lazy_initialized:
                _start_background_threads()
                _lazy_initialized = True


# ── ESN Model Retraining Background Worker ────────────────────────────
def run_training_async():
    global esn_soc, esn_soh, input_means, input_stds, model_loaded, loaded_soc_rmse, loaded_soh_rmse, _last_fetched_df
    training_status['status'] = 'running'
    training_status['logs'] = 'Checking training dataset paths...\n'
    current_model_score = _model_score(loaded_soc_rmse, loaded_soh_rmse)
    
    start_time = time.time()
    timeout_limit = getattr(Config, 'ONLINE_TRAINING_TIMEOUT', 60.0)

    def check_timeout():
        if (time.time() - start_time) >= timeout_limit:
            raise TimeoutError(f"Online training exceeded time limit of {timeout_limit:.2f} seconds.")

    try:
        check_timeout()
        from train_rc import EchoStateNetwork, generate_full_range_dataset
        from feature_engineering import extract_features_df
        
        csv_path = Config.CSV_PATH
        csv_url  = Config.CSV_URL

        df = None
        source_name = None

        # Priority 1: Doc Link (if CSV_URL is configured and accessible)
        if csv_url:
            rem = timeout_limit - (time.time() - start_time)
            if rem <= 0:
                raise TimeoutError(f"Online training exceeded time limit of {timeout_limit:.2f} seconds.")
            req_timeout = min(10.0, max(0.1, rem))
            training_status['logs'] += f"Checking doc link accessibility ({csv_url}, timeout: {req_timeout:.1f}s)...\n"
            try:
                import io
                import requests
                response = requests.get(csv_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=req_timeout)
                if response.status_code == 200:
                    csv_data = response.text
                    if "<html" not in csv_data.lower() and "<!doctype" not in csv_data.lower():
                        loaded_df = pd.read_csv(io.StringIO(csv_data))
                        if not loaded_df.empty:
                            df = loaded_df
                            source_name = "Doc Link Data"
                            training_status['logs'] += f"Doc link accessible! Loaded dataset ({len(df)} rows).\n"
                            # Store doc link data as latest loaded data!
                            _last_fetched_df = df.copy()
                            training_status['logs'] += "Stored doc link data as latest loaded dataset.\n"
                    else:
                        training_status['logs'] += "Doc link returned HTML page instead of raw CSV data.\n"
                else:
                    training_status['logs'] += f"Doc link HTTP error status: {response.status_code}.\n"
            except Exception as url_err:
                training_status['logs'] += f"Doc link not accessible: {url_err}.\n"

        # Priority 2: Doc link not accessible -> use previously loaded data
        if df is None and _last_fetched_df is not None and not _last_fetched_df.empty:
            df = _last_fetched_df.copy()
            source_name = "Previously Loaded Data"
            training_status['logs'] += f"Doc link not available. Using previously loaded dataset from memory ({len(df)} rows).\n"

        # Priority 3: Both doc link and previously loaded data not accessible -> use local trained file data
        if df is None:
            if os.path.exists(csv_path):
                training_status['logs'] += f"Loading local trained file data from {csv_path}...\n"
                try:
                    df = pd.read_csv(csv_path)
                    source_name = "Local Trained File Data"
                    training_status['logs'] += f"Local trained file data loaded successfully ({len(df)} rows).\n"
                    _last_fetched_df = df.copy()
                except Exception as local_err:
                    training_status['logs'] += f"Local trained file load failed: {local_err}.\n"

        # Fallback to physical simulator dataset generator if local file also fails
        if df is None:
            training_status['logs'] += "Generating high-fidelity dataset from physical battery simulator...\n"
            try:
                check_timeout()
                df = generate_full_range_dataset(timeout_check=check_timeout)
                source_name = "Local Trained File Data"
                training_status['logs'] += f"Simulator dataset generated successfully: {len(df)} rows.\n"
                _last_fetched_df = df.copy()
            except Exception as gen_err:
                training_status['logs'] += f"Backup dataset generator failed: {gen_err}.\n"
                raise RuntimeError("No training data source available.") from gen_err

        training_status['training_source'] = source_name
        training_status['logs'] += f"[DATA SOURCE] Training model using: {source_name}\n"

        check_timeout()

        if df is not None:
            # Recover if CSV was pasted into a single column
            if len(df.columns) == 1 and ',' in str(df.columns[0]):
                col_name = df.columns[0]
                new_cols = [c.strip() for c in col_name.split(',')]
                split_data = df[col_name].astype(str).str.split(',', expand=True)
                if split_data.shape[1] == len(new_cols):
                    split_data.columns = new_cols
                    df = split_data.apply(pd.to_numeric, errors='coerce')
                    
            df.columns = [str(col).strip() for col in df.columns]
            rename_dict = {}
            for col in df.columns:
                col_lower = col.lower()
                if col_lower == 'voltage':
                    rename_dict[col] = 'Voltage'
                elif col_lower == 'current':
                    rename_dict[col] = 'Current'
                elif col_lower == 'temperature':
                    rename_dict[col] = 'Temperature'
                elif col_lower == 'soc':
                    rename_dict[col] = 'SOC'
                elif col_lower == 'soh':
                    rename_dict[col] = 'SOH'
                elif col_lower == 'time':
                    rename_dict[col] = 'Time'
            df.rename(columns=rename_dict, inplace=True)

            # Coerce numeric columns, drop NaNs, and normalize percentage values
            req_cols = ['Voltage', 'Current', 'Temperature', 'SOC']
            for col in req_cols + (['SOH'] if 'SOH' in df.columns else []):
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df.dropna(subset=[c for c in req_cols if c in df.columns], inplace=True)
            if 'SOH' not in df.columns:
                df['SOH'] = 1.0

            # Auto-normalize SOC / SOH if provided in percentage (0-100%) scale
            if df['SOC'].max() > 1.5:
                df['SOC'] = df['SOC'] / 100.0
            if df['SOH'].max() > 1.5:
                df['SOH'] = df['SOH'] / 100.0
            df.reset_index(drop=True, inplace=True)

        # Dynamic decimation: Caps training dataset in production, for cloud URLs, or when dataset size > limit to guarantee sub-5s training
        is_production = Config.is_production()
        limit = Config.PRODUCTION_DECIMATION_LIMIT
        if (is_production or csv_url or len(df) > limit) and len(df) > limit:
            step = int(np.ceil(len(df) / limit))
            df = df.iloc[::step].reset_index(drop=True)
            training_status['logs'] += f"Dynamically decimated dataset (sampled every {step}th row) to {len(df)} rows for cloud optimization.\n"
            
        training_status['logs'] += "Extracting features & scaling rolling MA features...\n"
        U_raw = extract_features_df(df)
        selected_indices = Config.ESN_SELECTED_FEATURE_INDICES
        U_raw = U_raw[:, selected_indices]
        n_features = len(selected_indices)
        
        input_means = U_raw.mean(axis=0)
        input_stds = U_raw.std(axis=0)
        input_stds[input_stds == 0.0] = 1.0
        
        U_scaled = (U_raw - input_means) / input_stds
        Y_soc = df[['SOC']].values
        Y_soh = df[['SOH']].values

        check_timeout()

        training_status['logs'] += f"Initializing Reservoir (nodes={Config.ESN_SOC_RESERVOIR}, radius={Config.ESN_SOC_SPECTRAL_RADIUS}) for SOC prediction...\n"
        local_esn_soc = EchoStateNetwork(
            n_inputs=n_features,
            n_reservoir=Config.ESN_SOC_RESERVOIR,
            n_outputs=1,
            spectral_radius=Config.ESN_SOC_SPECTRAL_RADIUS,
            leak_rate=Config.ESN_SOC_LEAK_RATE,
            input_scaling=Config.ESN_SOC_INPUT_SCALING,
            ridge_param=Config.ESN_SOC_RIDGE_PARAM,
            sparsity=Config.ESN_SOC_SPARSITY
        )
        training_status['logs'] += "Fitting Readout weights via Ridge Regression (SOC)...\n"
        pred_soc_washout = local_esn_soc.train(U_scaled, Y_soc, washout=Config.ESN_WASHOUT_STEPS, timeout_check=check_timeout)
        soc_rmse = float(np.sqrt(np.mean((Y_soc[Config.ESN_WASHOUT_STEPS:].flatten() - pred_soc_washout.flatten()) ** 2)))
        training_status['logs'] += f"  SOC RMSE post-washout: {soc_rmse:.6f}\n"

        check_timeout()

        training_status['logs'] += f"Initializing Reservoir (nodes={Config.ESN_SOH_RESERVOIR}, radius={Config.ESN_SOH_SPECTRAL_RADIUS}) for SOH prediction...\n"
        local_esn_soh = EchoStateNetwork(
            n_inputs=n_features,
            n_reservoir=Config.ESN_SOH_RESERVOIR,
            n_outputs=1,
            spectral_radius=Config.ESN_SOH_SPECTRAL_RADIUS,
            leak_rate=Config.ESN_SOH_LEAK_RATE,
            input_scaling=Config.ESN_SOH_INPUT_SCALING,
            ridge_param=Config.ESN_SOH_RIDGE_PARAM,
            sparsity=Config.ESN_SOH_SPARSITY
        )
        training_status['logs'] += "Fitting Readout weights via Ridge Regression (SOH)...\n"
        pred_soh_washout = local_esn_soh.train(U_scaled, Y_soh, washout=Config.ESN_WASHOUT_STEPS, timeout_check=check_timeout)
        soh_rmse = float(np.sqrt(np.mean((Y_soh[Config.ESN_WASHOUT_STEPS:].flatten() - pred_soh_washout.flatten()) ** 2)))
        training_status['logs'] += f"  SOH RMSE post-washout: {soh_rmse:.6f}\n"

        package = {
            'esn_soc': local_esn_soc,
            'esn_soh': local_esn_soh,
            'input_means': input_means,
            'input_stds': input_stds,
            'soc_rmse': soc_rmse,
            'soh_rmse': soh_rmse
        }

        new_model_score = _model_score(soc_rmse, soh_rmse)
        if current_model_score < float('inf') and new_model_score > current_model_score:
            training_status['status'] = 'completed'
            training_status['soc_rmse'] = loaded_soc_rmse
            training_status['soh_rmse'] = loaded_soh_rmse
            training_status['timestamp'] = datetime.utcnow().isoformat()
            training_status['logs'] += (
                f"Candidate ESN score {new_model_score:.6f} was worse than the active model score "
                f"{current_model_score:.6f}; keeping the current model.\n"
            )
            return

        # 1. Try to save locally (development environment)
        try:
            training_status['logs'] += "Saving trained ESN to local file model_rc.pkl...\n"
            with open(model_path, 'wb') as f:
                pickle.dump(package, f)
            training_status['logs'] += "Model saved locally successfully.\n"
        except Exception as local_err:
            training_status['logs'] += f"Local save skipped (read-only filesystem): {local_err}\n"

        # 2. Try to save to MongoDB (production model registry)
        if check_db_connected():
            training_status['logs'] += "Uploading package to MongoDB registry cluster...\n"
            db['model_weights'].replace_one(
                {'_id': 'esn_package'},
                {
                    '_id': 'esn_package',
                    'pickle_data': pickle.dumps(package),
                    'soc_rmse': soc_rmse,
                    'soh_rmse': soh_rmse,
                    'updated_at': datetime.utcnow().isoformat()
                },
                upsert=True
            )
            training_status['logs'] += "Model saved to MongoDB successfully!\n"

        training_status['status'] = 'completed'
        training_status['soc_rmse'] = soc_rmse
        training_status['soh_rmse'] = soh_rmse
        training_status['timestamp'] = datetime.utcnow().isoformat()
        training_status['logs'] += "Echo State Network retraining finished successfully.\n"
        
        # Hydrate active ESN components in global scope
        esn_soc = local_esn_soc
        esn_soh = local_esn_soh
        # input_means / input_stds already assigned via global above
        loaded_soc_rmse = soc_rmse
        loaded_soh_rmse = soh_rmse
        model_loaded = True
        
        # Invalidate telemetry cache to apply the newly trained ESN weights retroactively
        _telemetry_cache.update({'key': None, 'pipeline': None, 'processed': [], 'n_cached': 0})

    except Exception as err:
        elapsed = time.time() - start_time
        if isinstance(err, TimeoutError) or elapsed >= timeout_limit:
            training_status['logs'] += f"\n[TIMEOUT] Online training exceeded time limit ({int(timeout_limit)}s).\n"
            if model_loaded and esn_soc is not None:
                training_status['status'] = 'completed'
                training_status['soc_rmse'] = loaded_soc_rmse if loaded_soc_rmse is not None else 0.0
                training_status['soh_rmse'] = loaded_soh_rmse if loaded_soh_rmse is not None else 0.0
                training_status['timestamp'] = datetime.utcnow().isoformat()
                training_status['logs'] += "Safely preserved and fell back to the last active ESN model weights & fetched state.\n"
                print(f"Online training timed out after {int(elapsed)}s. Preserved last active model weights.")
                return
        training_status['status'] = 'failed'
        training_status['logs'] += f"\nTRAINING FAILURE ENCOUNTERED: {err}\n"
        print(f"ESN Training failed: {err}")

# ── API Routes ────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    try:
        if not model_loaded:
            load_ml_model()
            
        port_online, port_data = check_simulator_port()
        
        # If the simulator service is offline, step the simulation inside the visualizer process
        if not port_online:
            sync_simulation_locally()

        state = load_sim_state()
        
        # Check simulator state fields
        sim_running = state.get('sim_running', False)
        active_cycle = state.get('active_cycle', 'udds')
        accelerated_aging = state.get('accelerated_aging', False)
        chemistry = state.get('chemistry', 'li_ion')
        
        # Default environment / fault status
        T_ambient = state.get('T_ambient', 25.0)
        fault_thermal = state.get('fault_thermal', False)
        fault_dropout = state.get('fault_dropout', False)
        fault_short = state.get('fault_short', False)
        
        # Override with live port state if online (always when simulator is online)
        if port_online and port_data:
            sim_running = port_data.get('sim_running', sim_running)
            active_cycle = port_data.get('active_cycle', active_cycle)
            accelerated_aging = port_data.get('accelerated_aging', accelerated_aging)
            chemistry = port_data.get('chemistry', chemistry)
            T_ambient = port_data.get('T_ambient', T_ambient)
            fault_thermal = port_data.get('fault_thermal', fault_thermal)
            fault_dropout = port_data.get('fault_dropout', fault_dropout)
            fault_short = port_data.get('fault_short', fault_short)
            
            # Sync back to local/database state ONLY if we are not connected to a shared MongoDB.
            # If MongoDB is connected, the DB is the single source of truth and the simulator
            # already writes its status directly to it. Overwriting it here causes race conditions
            # due to cached port status lag.
            config_changed = False
            if not check_db_connected():
                for key in ['chemistry', 'active_cycle', 'accelerated_aging', 'T_ambient', 'fault_thermal', 'fault_dropout', 'fault_short', 'sim_running']:
                    val = port_data.get(key)
                    if val is not None and state.get(key) != val:
                        state[key] = val
                        config_changed = True
                
                prog_changed = False
                prog_mappings = {
                    'time': 'time',
                    'soc': 'soc',
                    'soh': 'soh',
                    'temperature': 'temperature',
                    'voltage': 'prev_voltage',
                    'current': 'prev_current'
                }
                for port_key, state_key in prog_mappings.items():
                    val = port_data.get(port_key)
                    if val is not None and state.get(state_key) != val:
                        state[state_key] = val
                        prog_changed = True
                        
                if config_changed or prog_changed:
                    save_sim_state(state)
            if config_changed:
                # Invalidate telemetry cache so next GET /api/telemetry updates configs
                _telemetry_cache.update({'key': None, 'pipeline': None, 'processed': [], 'n_cached': 0})

        return jsonify({
            'sim_running': sim_running,
            'active_cycle': active_cycle,
            'accelerated_aging': accelerated_aging,
            'model_loaded': model_loaded,
            'mongodb_connected': check_db_connected(),
            'battery_time': state.get('time', 0.0),
            'chemistry': chemistry,
            'ekf_mismatch': 1.0,
            'quantize_mode': 'float32',
            'ekf_q_soc': 1e-7,
            'ekf_q_v1': 1e-6,
            'ekf_q_v2': 1e-6,
            'ekf_r_meas': 0.01,
            'fault_short_leakage': 0.8,
            'fault_thermal_runaway_mult': 4.0,
            'simulator_port_online': port_online,
            'simulator_url': Config.SIMULATOR_URL,
            'T_ambient': T_ambient,
            'fault_thermal': fault_thermal,
            'fault_dropout': fault_dropout,
            'fault_short': fault_short,
            'soc_rmse': loaded_soc_rmse,
            'soh_rmse': loaded_soh_rmse,
            'graph_slice_limit': Config.GRAPH_SLICE_LIMIT,
            'csv_url_configured': bool(Config.CSV_URL),
            'training_available': bool(Config.CSV_URL) or os.path.exists(Config.CSV_PATH) or (_last_fetched_df is not None and not _last_fetched_df.empty),
            'training_source': (
                training_status.get('training_source') or (
                    "Doc Link Data" if Config.CSV_URL
                    else ("Previously Loaded Data" if _last_fetched_df is not None and not _last_fetched_df.empty
                          else ("Local Trained File Data" if os.path.exists(Config.CSV_PATH) else None))
                )
            ),
            'esn_converged': (
                getattr(_telemetry_cache.get('pipeline'), '_esn_step_count', 0) >= Config.ESN_CONVERGENCE_STEPS
            )
        })
    except Exception as e:
        print(f"Error in /api/status: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/control', methods=['POST'])
def control_simulation():
    try:
        data = request.json or {}
        state = load_sim_state()
        
        # Save local parameter modifications (ignored under standard approach)
        pass
            
        # Store other config inputs
        for key in ['chemistry', 'active_cycle', 'accelerated_aging', 'T_ambient', 'fault_thermal', 'fault_dropout', 'fault_short']:
            if key in data:
                if key == 'T_ambient':
                    state[key] = float(data[key])
                elif key in ['accelerated_aging', 'fault_dropout', 'fault_short']:
                    state[key] = bool(data[key])
                elif key == 'fault_thermal':
                    was_thermal = state.get('fault_thermal', False)
                    is_thermal = bool(data[key])
                    state['fault_thermal'] = is_thermal
                    if was_thermal and not is_thermal:
                        state['temperature'] = state.get('T_ambient', 25.0)
                else:
                    state[key] = data[key]
        if 'cycle_type' in data:
            state['active_cycle'] = data['cycle_type']

        command = data.get('command')
        if command == 'start':
            state['sim_running'] = True
            state['last_real_time'] = time.time()
        elif command == 'stop' or command == 'pause':
            state['sim_running'] = False
        elif command == 'reset':
            state['sim_running'] = False
            if 'chemistry' not in data:
                state['chemistry'] = 'li_ion'
            state['active_cycle'] = 'udds'
            state['accelerated_aging'] = False
            state['T_ambient'] = 25.0
            state['fault_thermal'] = False
            state['fault_dropout'] = False
            state['fault_short'] = False
            
            state['time'] = 0.0
            
            # Detect if ESN is loaded with narrow range CSV dataset
            is_narrow_dataset = False
            if model_loaded and input_means is not None:
                if len(input_means) > 0 and input_means[0] < 10.2:
                    is_narrow_dataset = True
                    
            if is_narrow_dataset:
                state['soc'] = 0.1156
                state['soh'] = 0.90
            else:
                state['soc'] = 1.0
                state['soh'] = 1.0
                
            state['V1'] = 0.0
            state['V2'] = 0.0
            state['temperature'] = 25.0
            state['internal_resistance_growth'] = 1.0
            state['last_real_time'] = None
            
            chem_obj = get_chemistry(state['chemistry'])
            state['prev_voltage'] = chem_obj.lookup_ocv(state['soc'])
            state['prev_current'] = 0.0
            
            # Clear local buffer
            local_telemetry_buffer.clear()
            if check_db_connected():
                try:
                    db[Config.MONGODB_READINGS_COLLECTION].delete_many({})
                except Exception as db_err:
                    print(f"Error purging database in visualizer: {db_err}")
            
        save_sim_state(state)

        # Invalidate telemetry cache whenever control state or command changes to ensure immediate UI sync
        _telemetry_cache.update({'key': None, 'pipeline': None, 'processed': [], 'n_cached': 0})
        
        # Forward control payload to Config.SIMULATOR_URL if online (force live check)
        port_online, _ = check_simulator_port(force=True)
        if port_online:
            try:
                sim_data = data.copy()
                sim_data['soc'] = state['soc']
                sim_data['soh'] = state['soh']
                if 'active_cycle' in sim_data:
                    sim_data['cycle_type'] = sim_data.pop('active_cycle')
                
                # Increased timeout to 1.5s to prevent false timeouts on Render
                with make_simulator_request("/api/control", method='POST', data=sim_data, timeout=1.5) as response:
                    if response.status == 200:
                        sim_resp = json.loads(response.read().decode())
                        # Update cache with the simulator's updated status values
                        global _simulator_port_online, _simulator_port_data
                        _simulator_port_online = True
                        _simulator_port_data = {
                            'sim_running': sim_resp.get('sim_running', False),
                            'chemistry': sim_resp.get('chemistry', 'li_ion'),
                            'active_cycle': sim_resp.get('active_cycle', 'udds'),
                            'accelerated_aging': sim_resp.get('accelerated_aging', False),
                            'T_ambient': sim_resp.get('T_ambient', 25.0),
                            'fault_thermal': sim_resp.get('fault_thermal', False),
                            'fault_dropout': sim_resp.get('fault_dropout', False),
                            'fault_short': sim_resp.get('fault_short', False),
                            'time': sim_resp.get('time', 0.0)
                        }
            except Exception as forward_err:
                print(f"Failed to forward control to simulator: {forward_err}")
                
        # Invalidate visualizer status cache check time so next status poll triggers a fresh live query
        global _last_sim_check_time
        _last_sim_check_time = 0.0
                
        return jsonify({
            'status': 'ok',
            'ekf_mismatch': state.get('ekf_mismatch', 1.0),
            'quantize_mode': state.get('quantize_mode', 'float32'),
            'T_ambient': state.get('T_ambient', 25.0),
            'fault_thermal': state.get('fault_thermal', False),
            'fault_dropout': state.get('fault_dropout', False),
            'fault_short': state.get('fault_short', False)
        })
    except Exception as e:
        print(f"Error in /api/control: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/train', methods=['POST'])
def trigger_training():
    # In serverless / read-only-filesystem environments, retraining requires
    # a remote dataset source. Block only if neither local CSV nor CSV_URL is set.
    if IS_SERVERLESS and not os.path.exists(Config.CSV_PATH) and not Config.CSV_URL and (_last_fetched_df is None or _last_fetched_df.empty):
        return jsonify({
            'status': 'unsupported',
            'message': 'No training data source available.'
        }), 501

    if training_status['status'] == 'running':
        return jsonify({'status': 'running', 'message': 'Model retraining is already executing.'})

    is_sync = request.args.get('sync', '').lower() in ('true', '1', 'yes') or IS_SERVERLESS
    if is_sync:
        run_training_async()
        return jsonify(training_status)
        
    thread = threading.Thread(target=run_training_async, daemon=True)
    thread.start()
    return jsonify({'status': 'started', 'message': 'ESN Training thread launched.'})

@app.route('/api/train/status', methods=['GET'])
def get_training_status():
    return jsonify(training_status)

@app.route('/api/chemistry/register', methods=['POST'])
def post_register_chemistry():
    try:
        data = request.json or {}
        name = data.get('name')
        nominal_capacity = data.get('nominal_capacity')
        R0_nom = data.get('R0_nom')
        R1_nom = data.get('R1_nom')
        C1_nom = data.get('C1_nom')
        R2_nom = data.get('R2_nom')
        C2_nom = data.get('C2_nom')
        thermal_capacitance = data.get('thermal_capacitance')
        cooling_coefficient = data.get('cooling_coefficient')
        ocv_table = data.get('ocv_table')
        n_cells = data.get('n_cells', 1)
        
        if not name or not nominal_capacity or not ocv_table:
            return jsonify({'status': 'error', 'message': 'Missing required fields (name, nominal_capacity, ocv_table)'}), 400
            
        chem = register_chemistry(
            name=name,
            nominal_capacity=nominal_capacity,
            R0_nom=R0_nom or 0.02,
            R1_nom=R1_nom or 0.01,
            C1_nom=C1_nom or 1000,
            R2_nom=R2_nom or 0.015,
            C2_nom=C2_nom or 4000,
            thermal_capacitance=thermal_capacitance or 80.0,
            cooling_coefficient=cooling_coefficient or 0.25,
            ocv_table=ocv_table,
            n_cells=n_cells
        )
        
        # Forward to simulator port if online
        port_online, _ = check_simulator_port()
        if port_online:
            try:
                with make_simulator_request("/api/chemistry/register", method='POST', data=data, timeout=1.0) as response:
                    pass
            except Exception as e:
                print(f"Warning: Failed to forward registered chemistry to simulator: {e}")
                
        return jsonify({
            'status': 'ok',
            'message': f"Chemistry '{chem.name}' registered successfully.",
            'chemistry': {
                'name': chem.name,
                'nominal_capacity': chem.nominal_capacity,
                'n_cells': chem.n_cells
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    try:
        if not model_loaded:
            load_ml_model()

        state = load_sim_state()
        chemistry_name = state.get('chemistry', 'li_ion')
        ekf_mismatch   = 1.0
        quantize_mode  = 'float32'
        
        # Override with live port state if simulator is online
        port_online, port_data = check_simulator_port()
        if port_online and port_data:
            chemistry_name = port_data.get('chemistry', chemistry_name)

        # ── Incremental pipeline cache ──────────────────────────────────────────
        # Key that identifies the current estimator configuration
        cache_key = f"{chemistry_name}_{ekf_mismatch}_{quantize_mode}"
        cache      = _telemetry_cache

        # Invalidate cache when chemistry / mismatch / mode changes
        if cache['key'] != cache_key:
            cache.update({
                'key':       cache_key,
                'pipeline':  EstimatorPipeline(
                    chemistry_name=chemistry_name,
                    mismatch=ekf_mismatch,
                    esn_soc=esn_soc,
                    esn_soh=esn_soh,
                    input_means=input_means,
                    input_stds=input_stds
                ),
                'processed': [],
                'n_cached':  0
            })

        pipeline         = cache['pipeline']
        pipeline.load_model(esn_soc, esn_soh, input_means, input_stds)
        
        ekf_q_soc = 1e-7
        ekf_q_v1  = 1e-6
        ekf_q_v2  = 1e-6
        ekf_r_meas = 0.01
        pipeline.update_ekf_noise(ekf_q_soc, ekf_q_v1, ekf_q_v2, ekf_r_meas)
        
        already_cached   = cache['n_cached']
        
        new_readings = []
        prev_time = None
        if already_cached > 0 and len(cache['processed']) > 0:
            prev_time = cache['processed'][-1]['time']

        if check_db_connected():
            try:
                # Fast indexed lookup for database purge or reset detection (takes < 0.001s)
                latest_record = db[Config.MONGODB_READINGS_COLLECTION].find_one(sort=[('time', -1)])
                if latest_record is None or (prev_time is not None and latest_record['time'] < prev_time):
                    cache.update({
                        'key':       None,
                        'pipeline':  None,
                        'processed': [],
                        'n_cached':  0
                    })
                    already_cached = 0
                    prev_time = None
                
                if prev_time is not None:
                    cursor = db[Config.MONGODB_READINGS_COLLECTION].find({'time': {'$gt': prev_time}}, {'_id': False}).sort('time', 1)
                    new_readings = list(cursor)
                else:
                    # Cap initial fetch to the most recent 500 records to prevent CPU/memory starvation on first load
                    limit_val = 500
                    cursor = db[Config.MONGODB_READINGS_COLLECTION].find({}, {'_id': False}).sort('time', -1).limit(limit_val)
                    new_readings = list(cursor)
                    new_readings.reverse() # Restore chronological order
                    already_cached = max(0, len(new_readings))
                    
                cache['n_cached'] = already_cached + len(new_readings)
            except Exception as db_err:
                print(f"Error querying database in get_telemetry: {db_err}")
                new_readings = []
        else:
            # Fallback when database is offline
            port_online, _ = check_simulator_port()
            raw_readings = []
            if port_online:
                try:
                    with make_simulator_request("/api/readings", timeout=1.5) as response:
                        if response.status == 200:
                            raw_readings = json.loads(response.read().decode())
                except Exception as e:
                    print(f"Error fetching readings from simulator: {e}")
            else:
                raw_readings = list(local_telemetry_buffer)
            
            # Invalidate cache if local buffer was cleared / truncated
            if len(raw_readings) < already_cached:
                cache.update({
                    'key':       None,
                    'pipeline':  None,
                    'processed': [],
                    'n_cached':  0
                })
                already_cached = 0
            
            new_readings = raw_readings[already_cached:]
            cache['n_cached'] = len(raw_readings)

        cpu_usage, mem_usage = get_system_metrics()
        prev_time = None

        # Determine dt for the first new reading based on last cached entry
        if already_cached > 0 and len(cache['processed']) > 0:
            prev_time = cache['processed'][-1]['time']

        for record in new_readings:
            t_curr = record['time']
            if prev_time is None:
                dt = Config.SIMULATION_STEP_DELAY
            else:
                dt = max(0.01, t_curr - prev_time)
            prev_time = t_curr

            est_output = pipeline.step(
                V_meas=float(record.get('voltage', 3.7)),
                I_meas_discharge=float(record.get('current', 0.0)),
                T_meas=float(record.get('temperature', 25.0)),
                dt=dt,
                quantize_mode=quantize_mode,
                dataset_dt=Config.DATASET_TIME_STEP,
                selected_indices=Config.ESN_SELECTED_FEATURE_INDICES,
                fault_short=record.get('fault_short', False),
                fault_thermal=record.get('fault_thermal', False),
                fault_dropout=record.get('fault_dropout', False)
            )

            processed_record = record.copy()
            processed_record.update({
                'ekf_soc':    est_output['ekf_soc'],
                'esn_soc':    est_output['esn_soc'],
                'ekf_soh':    est_output['trad_soh'],
                'esn_soh':    est_output['esn_soh'],
                'ekf_v1':     est_output['ekf_v1'],
                'ekf_v2':     est_output['ekf_v2'],
                'ekf_p_diag': est_output['ekf_p_diag'],
                'esn_features': est_output['esn_features'],
                'ekf_time':   est_output['ekf_time'],
                'esn_time':   est_output['esn_time'],
                'cpu_usage':  cpu_usage,
                'mem_usage':  mem_usage,
                'faults':     est_output.get('faults', []),
                'sop_charge_curr': est_output.get('sop_charge_curr', 0.0),
                'sop_discharge_curr': est_output.get('sop_discharge_curr', 0.0),
                'sop_charge_pwr': est_output.get('sop_charge_pwr', 0.0),
                'sop_discharge_pwr': est_output.get('sop_discharge_pwr', 0.0),
                'ekf_soe': est_output.get('ekf_soe', 1.0),
                'esn_soe': est_output.get('esn_soe', 1.0),
                'ekf_rul_cycles': est_output.get('ekf_rul_cycles', 1000.0),
                'esn_rul_cycles': est_output.get('esn_rul_cycles', 1000.0),
                'energy_remaining_wh': est_output.get('energy_remaining_wh', 0.0),
                'rls_r0':        est_output.get('rls_r0', 0.075),
                'rls_r1':        est_output.get('rls_r1', 0.045),
                'rls_c1':        est_output.get('rls_c1', 1000.0),
                'rls_converged': est_output.get('rls_converged', False),
                'innovation':    est_output.get('innovation', 0.0)
            })
            cache['processed'].append(processed_record)

        # Update cache watermark is handled inside the fetch branches

        # Return the most-recent window only
        limit = Config.TELEMETRY_RESPONSE_LIMIT
        return jsonify({
            'model_loaded': model_loaded,
            'data': cache['processed'][-limit:]
        })

    except Exception as e:
        print(f"Error in /api/telemetry: {e}")
        # Invalidate cache on unexpected error so next call starts fresh
        _telemetry_cache.update({'key': None, 'pipeline': None, 'processed': [], 'n_cached': 0})
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Battery State Estimator — load ESN model & initialize dataset at startup
try:
    load_ml_model()
    init_previous_data()
except Exception as _startup_err:
    print(f"Battery State Estimator — ESN model cold-start load skipped: {_startup_err}")

if not model_loaded and (os.path.exists(Config.CSV_PATH) or Config.CSV_URL):
    print("Battery State Estimator — no trained ESN loaded at startup; retraining from available data.")
    try:
        run_training_async()
    except Exception as _startup_retrain_err:
        print(f"Battery State Estimator — startup retraining failed: {_startup_retrain_err}")

if __name__ == '__main__':
    _start_background_threads()
    if not Config.FLASK_DEBUG or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print(f"Visualizer Running on http://localhost:{Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.FLASK_DEBUG)
