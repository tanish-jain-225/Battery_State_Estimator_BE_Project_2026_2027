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

# Add bundled simulator subdirectory to path for clean imports
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, 'simulator'))                 # Bundled simulator
sys.path.append(os.path.join(base_dir, 'training'))

from flask import Flask, jsonify, request, render_template
from pymongo import MongoClient
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
    import hashlib
    # Read database connection URI which is already required and configured
    uri = os.environ.get("MONGODB_URI", Config.MONGODB_URI)
    if not uri or "localhost" in uri or "127.0.0.1" in uri:
        return None
    # Hash the connection URI to create a secure 64-character secret
    return hashlib.sha256(uri.encode('utf-8')).hexdigest()

def verify_request_auth():
    # Loopback addresses (localhost) bypass auth checks in dev/local environments
    remote = request.remote_addr
    if remote in ('127.0.0.1', '::1', 'localhost'):
        return True
        
    secret = get_shared_secret()
    if not secret:
        return True # Fails-open for local developer runs
    
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
        db_client = MongoClient(mongodb_uri)
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

# Shared state for background ESN training
training_status = {
    'status': 'idle',
    'logs': '',
    'soc_rmse': 0.0,
    'soh_rmse': 0.0,
    'timestamp': None,
    'training_source': None   # 'local_csv' | 'remote_url' | None
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

def load_ml_model():
    global esn_soc, esn_soh, input_means, input_stds, model_loaded, loaded_soc_rmse, loaded_soh_rmse
    
    # First: Try to load from MongoDB Registry (supports serverless read-only filesystem)
    if check_db_connected():
        try:
            print(f"[DEBUG] MongoDB collections found: {db.list_collection_names()}")
            print(f"[DEBUG] Documents in model_weights: {list(db['model_weights'].find({}, {'pickle_data': False}))}")
            db_model = db['model_weights'].find_one({'_id': 'esn_package'})
            if db_model is not None:
                package = safe_pickle_loads(db_model['pickle_data'])
                esn_soc = package['esn_soc']
                esn_soh = package['esn_soh']
                input_means = package['input_means']
                input_stds = package['input_stds']
                model_loaded = True
                loaded_soc_rmse = db_model.get('soc_rmse')
                loaded_soh_rmse = db_model.get('soh_rmse')
                print("Echo State Networks loaded successfully from MongoDB model registry.")
                return
            else:
                # MongoDB connected but empty -> run with blank weights
                esn_soc = None
                esn_soh = None
                input_means = None
                input_stds = None
                model_loaded = False
                loaded_soc_rmse = None
                loaded_soh_rmse = None
                print("MongoDB model registry is empty. Running with blank weights.")
                return
        except Exception as e:
            print(f"Error loading model from MongoDB registry: {e}")

    # Fallback: Load from local pickle file only if MongoDB connection failed
    if os.path.exists(model_path):
        try:
            with open(model_path, 'rb') as f:
                package = safe_pickle_load(f)
                esn_soc = package['esn_soc']
                esn_soh = package['esn_soh']
                input_means = package['input_means']
                input_stds = package['input_stds']
                model_loaded = True
                loaded_soc_rmse = package.get('soc_rmse')
                loaded_soh_rmse = package.get('soh_rmse')
                print("Echo State Networks loaded successfully from local file.")
        except Exception as e:
            print(f"Error loading local model file: {e}")
            model_loaded = False
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
    if IS_SERVERLESS:
        # Rate limit status port check in serverless mode to once every 20 seconds to prevent thread block lag
        if not force and (now - _last_sim_port_check_time < 20.0):
            return _simulator_port_online, _simulator_port_data
            
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
    global local_sim_state
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
    global local_sim_state
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
    global current_chemistry, visualiser_simulator, local_telemetry_buffer
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
        db_client = MongoClient(mongodb_uri)
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
                db_client = MongoClient(mongodb_uri)
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
    global current_chemistry, visualiser_simulator, local_telemetry_buffer
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
    global training_status, esn_soc, esn_soh, input_means, input_stds, model_loaded, loaded_soc_rmse, loaded_soh_rmse
    training_status['status'] = 'running'
    training_status['logs'] = 'Checking training dataset paths...\n'
    
    try:
        from train_rc import EchoStateNetwork
        from feature_engineering import extract_features_df
        
        csv_path = Config.CSV_PATH
        csv_url  = Config.CSV_URL

        if csv_url:
            # Remote dataset via Google Sheets / public CSV URL (Prioritized in Production)
            training_status['training_source'] = 'remote_url'
            training_status['logs'] += f"Fetching remote dataset from URL (timeout: 10s)...\n"
            try:
                import io
                import requests
                response = requests.get(csv_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10.0)
                response.raise_for_status()
                csv_data = response.text
                if "<html" in csv_data.lower() or "<!doctype" in csv_data.lower():
                    raise ValueError("URL returned an HTML webpage instead of raw CSV data. Ensure the link format ends with /export?format=csv")
                df = pd.read_csv(io.StringIO(csv_data))
                training_status['logs'] += f"Remote dataset loaded ({len(df)} rows).\n"
            except Exception as url_err:
                if os.path.exists(csv_path):
                    training_status['training_source'] = 'local_csv'
                    training_status['logs'] += f"Remote CSV load failed: {url_err}. Falling back to local CSV...\n"
                    df = pd.read_csv(csv_path)
                else:
                    raise RuntimeError(
                        f"Failed to load remote CSV from CSV_URL: {url_err}. "
                        "Ensure the Google Sheet is shared as 'Anyone with the link can view' "
                        "and the URL ends with export?format=csv"
                    ) from url_err
        elif os.path.exists(csv_path):
            # Local dataset available (development / self-hosted environment)
            training_status['training_source'] = 'local_csv'
            training_status['logs'] += "Dataset found. Loading ev battery dataframe into memory...\n"
            df = pd.read_csv(csv_path)
        else:
            raise FileNotFoundError(
                f"No training data source available.\n"
                f"  • Local path '{csv_path}' does not exist.\n"
                f"  • CSV_URL env var is not set.\n"
                f"Set CSV_URL to your Google Sheets export URL to enable production retraining."
            )
        
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
        local_esn_soc.train(U_scaled, Y_soc, washout=Config.ESN_WASHOUT_STEPS)
        pred_soc = local_esn_soc.predict(U_scaled)
        soc_rmse = float(np.sqrt(np.mean((Y_soc[Config.ESN_WASHOUT_STEPS:] - pred_soc[Config.ESN_WASHOUT_STEPS:]) ** 2)))
        training_status['logs'] += f"  SOC RMSE post-washout: {soc_rmse:.6f}\n"

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
        local_esn_soh.train(U_scaled, Y_soh, washout=Config.ESN_WASHOUT_STEPS)
        pred_soh = local_esn_soh.predict(U_scaled)
        soh_rmse = float(np.sqrt(np.mean((Y_soh[Config.ESN_WASHOUT_STEPS:] - pred_soh[Config.ESN_WASHOUT_STEPS:]) ** 2)))
        training_status['logs'] += f"  SOH RMSE post-washout: {soh_rmse:.6f}\n"

        package = {
            'esn_soc': local_esn_soc,
            'esn_soh': local_esn_soh,
            'input_means': input_means,
            'input_stds': input_stds,
            'soc_rmse': soc_rmse,
            'soh_rmse': soh_rmse
        }

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
        global model_loaded
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
            'ekf_mismatch': state.get('ekf_mismatch', 1.0),
            'quantize_mode': state.get('quantize_mode', 'float32'),
            'simulator_port_online': port_online,
            'simulator_url': Config.SIMULATOR_URL,
            'T_ambient': T_ambient,
            'fault_thermal': fault_thermal,
            'fault_dropout': fault_dropout,
            'fault_short': fault_short,
            'soc_rmse': loaded_soc_rmse,
            'soh_rmse': loaded_soh_rmse,
            'graph_slice_limit': Config.GRAPH_SLICE_LIMIT,
            # Training data source info
            'csv_url_configured': bool(Config.CSV_URL),
            'training_available': os.path.exists(Config.CSV_PATH) or bool(Config.CSV_URL),
            'training_source': (
                'remote_url' if Config.CSV_URL
                else ('local_csv' if os.path.exists(Config.CSV_PATH) else None)
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
        
        # Save local parameter modifications
        if 'ekf_mismatch' in data:
            state['ekf_mismatch'] = float(data['ekf_mismatch'])
        if 'quantize_mode' in data:
            state['quantize_mode'] = str(data['quantize_mode'])
            
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
            state['soc'] = 1.0
            state['soh'] = 1.0
            state['V1'] = 0.0
            state['V2'] = 0.0
            state['temperature'] = 25.0
            state['internal_resistance_growth'] = 1.0
            state['last_real_time'] = None
            
            chem_obj = get_chemistry(state['chemistry'])
            state['prev_voltage'] = chem_obj.lookup_ocv(1.0)
            state['prev_current'] = 0.0
            
            # Clear local buffer
            local_telemetry_buffer.clear()
            if check_db_connected():
                try:
                    db[Config.MONGODB_READINGS_COLLECTION].delete_many({})
                except Exception as db_err:
                    print(f"Error purging database in visualizer: {db_err}")
            
        save_sim_state(state)

        # Invalidate telemetry cache if configuration has structurally changed
        reset_trigger = data.get('command') == 'reset' or 'chemistry' in data
        if reset_trigger or 'ekf_mismatch' in data or 'quantize_mode' in data:
            _telemetry_cache.update({'key': None, 'pipeline': None, 'processed': [], 'n_cached': 0})
        
        # Forward control payload to Config.SIMULATOR_URL if online (force live check)
        port_online, _ = check_simulator_port(force=True)
        if port_online:
            try:
                sim_data = data.copy()
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
    global training_status

    # In serverless / read-only-filesystem environments, retraining requires
    # a remote dataset source. Block only if neither local CSV nor CSV_URL is set.
    if IS_SERVERLESS and not os.path.exists(Config.CSV_PATH) and not Config.CSV_URL:
        return jsonify({
            'status': 'unsupported',
            'message': 'No training data source available in serverless mode. '
                       'Set the CSV_URL environment variable to a public Google Sheets export URL '
                       '(File → Share → Publish to web → CSV) to enable production retraining.'
        }), 501

    if training_status['status'] == 'running':
        return jsonify({'status': 'running', 'message': 'Model retraining is already executing.'})
        
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
    global model_loaded
    try:
        if not model_loaded:
            load_ml_model()

        state = load_sim_state()
        chemistry_name = state.get('chemistry', 'li_ion')
        ekf_mismatch   = state.get('ekf_mismatch', 1.0)
        quantize_mode  = state.get('quantize_mode', 'float32')
        
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
                V_meas=record['voltage'],
                I_meas_discharge=record['current'],
                T_meas=record['temperature'],
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
                'rls_converged': est_output.get('rls_converged', False)
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

# Battery State Estimator — load ESN model at startup (lazy retry on first /api/status if this fails)
try:
    load_ml_model()
except Exception as _startup_err:
    print(f"Battery State Estimator — ESN model cold-start load skipped: {_startup_err}")

if __name__ == '__main__':
    _start_background_threads()
    if not Config.FLASK_DEBUG or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print(f"Visualizer Running on http://localhost:{Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.FLASK_DEBUG)
