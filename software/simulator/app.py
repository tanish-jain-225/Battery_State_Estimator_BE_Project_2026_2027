import sys
import os
import time
import threading
import logging
from datetime import datetime
from pymongo import MongoClient
from flask import Flask, jsonify, request, render_template

# Add local directory to path to allow clean imports
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from battery_simulator import BatterySimulator, DriveCycles
from battery_chemistry import get_chemistry, register_chemistry
from config import Config

# Suppress Flask startup banner and logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
app_start_time = time.time()

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

@app.before_request
def enforce_api_key():
    if request.path.startswith('/api/') and request.method == 'POST':
        if not verify_request_auth():
            return jsonify({'status': 'error', 'message': 'Unauthorized: Invalid API Key.'}), 401



# Default generator config
DEFAULT_STATE = {
    'chemistry': 'li_ion',
    'time': 0.0,
    'soc': 1.0,
    'soh': 1.0,
    'V1': 0.0,
    'V2': 0.0,
    'temperature': 25.0,
    'internal_resistance_growth': 1.0,
    'sim_running': False,
    'active_cycle': 'udds',
    'accelerated_aging': False,
    'T_ambient': 25.0,
    'fault_thermal': False,
    'fault_dropout': False,
    'fault_short': False,
    'last_real_time': None,
    'prev_voltage': 3.7 * 3,
    'prev_current': 0.0
}

# Serverless support detection
IS_SERVERLESS = os.environ.get('SERVERLESS') == '1'

# Shared state memory
local_state = DEFAULT_STATE.copy()
local_telemetry_buffer = []
mongodb_connected = False
db_client = None
db = None

# Non-blocking async cache variables
_mongodb_connected = False
_mongodb_error = None

def _ensure_db():
    global mongodb_connected, db_client, db
    if IS_SERVERLESS:
        if mongodb_connected and db is not None:
            return True
        try:
            db_client = MongoClient(Config.MONGODB_URI)
            db_client.server_info()
            db = db_client[Config.MONGODB_DB_NAME]
            mongodb_connected = True
            print("Battery State Estimator — Physics Engine connected to MongoDB Atlas.")
            return True
        except Exception as e:
            mongodb_connected = False
            print(f"Battery State Estimator — MongoDB connection attempt failed: {e}")
            return False
            
    return _mongodb_connected and db is not None

def load_sim_state():
    global local_state
    if _ensure_db():
        try:
            doc = db[Config.MONGODB_STATE_COLLECTION].find_one({'_id': 'singleton'})
            if doc:
                doc.pop('_id', None)
                return doc
        except Exception as e:
            print(f"Battery State Estimator — Error loading state from MongoDB: {e}")
    return local_state

def save_sim_state(state):
    global local_state
    local_state = state
    if _ensure_db():
        try:
            doc_copy = state.copy()
            doc_copy['_id'] = 'singleton'
            db[Config.MONGODB_STATE_COLLECTION].replace_one({'_id': 'singleton'}, doc_copy, upsert=True)
        except Exception as e:
            print(f"Battery State Estimator — Error saving state to MongoDB: {e}")

def update_sim_progress(progress_dict):
    global local_state
    local_state.update(progress_dict)
    if _ensure_db():
        try:
            db[Config.MONGODB_STATE_COLLECTION].update_one(
                {'_id': 'singleton'},
                {'$set': progress_dict},
                upsert=True
            )
        except Exception as e:
            print(f"Battery State Estimator — Error updating simulation progress: {e}")

# Spawns physical battery simulator
simulator = BatterySimulator()
current_chemistry = None

def generator_loop():
    global current_chemistry, simulator
    print("Simulator background thread active.")
    last_loop_time = time.time()
    
    while True:
        try:
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
                    simulator.reset(chemistry_name)
                else:
                    simulator.change_chemistry(chemistry_name)
                current_chemistry = chemistry_name
                print(f"BMS Physics profile loaded: {chemistry_name.upper()}")
                
            if sim_running:
                # Sync physical parameters
                simulator.time = state.get('time', 0.0)
                simulator.soc = state.get('soc', 1.0)
                simulator.soh = state.get('soh', 1.0)
                simulator.V1 = state.get('V1', 0.0)
                simulator.V2 = state.get('V2', 0.0)
                simulator.temperature = state.get('temperature', 25.0)
                simulator.internal_resistance_growth = state.get('internal_resistance_growth', 1.0)
                simulator.T_ambient = T_ambient
                
                # Retrieve cycle current excitation (I)
                t = simulator.time
                if active_cycle == "udds":
                    I = DriveCycles.udds(t)
                elif active_cycle == "hwfet":
                    I = DriveCycles.hwfet(t)
                elif active_cycle == "us06":
                    I = DriveCycles.us06(t)
                elif active_cycle == "constant":
                    I = DriveCycles.constant_discharge(t)
                elif active_cycle == "charge":
                    I = DriveCycles.cccv_charge(t, simulator.soc)
                else:
                    I = 0.0
                    
                # Step physics
                out = simulator.step(
                    I, step_delay, 
                    accelerated_aging=accelerated_aging,
                    fault_thermal=fault_thermal,
                    fault_dropout=fault_dropout,
                    fault_short=fault_short
                )
                
                # Apply nominal noise bounds
                noisy = simulator.add_sensor_noise(
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
                if _ensure_db():
                    db[Config.MONGODB_READINGS_COLLECTION].insert_one(record)
                else:
                    local_telemetry_buffer.append(record)
                    limit = getattr(Config, 'TELEMETRY_FALLBACK_LIMIT', 1000)
                    if len(local_telemetry_buffer) > limit:
                        local_telemetry_buffer.pop(0)
                    
                # Update configuration document
                update_sim_progress({
                    'time': simulator.time,
                    'soc': simulator.soc,
                    'soh': simulator.soh,
                    'V1': simulator.V1,
                    'V2': simulator.V2,
                    'temperature': simulator.temperature,
                    'internal_resistance_growth': simulator.internal_resistance_growth,
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
                if state.get('time', 0.0) == 0.0 and simulator.time != 0.0:
                    simulator.reset(chemistry_name)
                    print("Simulator baseline states reset.")
                time.sleep(0.5)
                last_loop_time = time.time()
        except Exception as e:
            print(f"Simulator thread exception: {e}")
            time.sleep(1.0)

# Serverless support detection
IS_SERVERLESS = os.environ.get('SERVERLESS') == '1'

def sync_simulation_on_demand():
    global current_chemistry, simulator, local_telemetry_buffer
    if not IS_SERVERLESS:
        return
        
    state = load_sim_state()
    sim_running = state.get('sim_running', False)
    if not sim_running:
        if state.get('time', 0.0) == 0.0 and simulator.time != 0.0:
            chemistry_name = state.get('chemistry', 'li_ion')
            simulator.reset(chemistry_name)
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

    # Cap steps to protect serverless performance execution bounds
    steps = min(steps, 50)

    chemistry_name = state.get('chemistry', 'li_ion')
    if chemistry_name != current_chemistry:
        if state.get('time', 0.0) == 0.0:
            simulator.reset(chemistry_name)
        else:
            simulator.change_chemistry(chemistry_name)
        current_chemistry = chemistry_name

    # Load starting physical states
    simulator.time = state.get('time', 0.0)
    simulator.soc = state.get('soc', 1.0)
    simulator.soh = state.get('soh', 1.0)
    simulator.V1 = state.get('V1', 0.0)
    simulator.V2 = state.get('V2', 0.0)
    simulator.temperature = state.get('temperature', 25.0)
    simulator.internal_resistance_growth = state.get('internal_resistance_growth', 1.0)
    simulator.T_ambient = state.get('T_ambient', 25.0)

    active_cycle = state.get('active_cycle', 'udds')
    accelerated_aging = state.get('accelerated_aging', False)
    fault_thermal = state.get('fault_thermal', False)
    fault_dropout = state.get('fault_dropout', False)
    fault_short = state.get('fault_short', False)

    V_meas, I_meas = 0.0, 0.0

    for _ in range(steps):
        t = simulator.time
        if active_cycle == "udds":
            I = DriveCycles.udds(t)
        elif active_cycle == "hwfet":
            I = DriveCycles.hwfet(t)
        elif active_cycle == "us06":
            I = DriveCycles.us06(t)
        elif active_cycle == "constant":
            I = DriveCycles.constant_discharge(t)
        elif active_cycle == "charge":
            I = DriveCycles.cccv_charge(t, simulator.soc)
        else:
            I = 0.0

        out = simulator.step(
            I, step_delay,
            accelerated_aging=accelerated_aging,
            fault_thermal=fault_thermal,
            fault_dropout=fault_dropout,
            fault_short=fault_short
        )

        noisy = simulator.add_sensor_noise(
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

        if _ensure_db():
            # Check if this reading already exists to prevent duplicate inserts from concurrent workers/instances
            exists = db[Config.MONGODB_READINGS_COLLECTION].find_one({'time': out['time']})
            if not exists:
                db[Config.MONGODB_READINGS_COLLECTION].insert_one(record)
        else:
            # Make sure we don't duplicate locally either
            if not any(r['time'] == record['time'] for r in local_telemetry_buffer):
                local_telemetry_buffer.append(record)
                limit = getattr(Config, 'TELEMETRY_FALLBACK_LIMIT', 1000)
                if len(local_telemetry_buffer) > limit:
                    local_telemetry_buffer.pop(0)

    # Save final simulator state back to state dict
    update_sim_progress({
        'time': simulator.time,
        'soc': simulator.soc,
        'soh': simulator.soh,
        'V1': simulator.V1,
        'V2': simulator.V2,
        'temperature': simulator.temperature,
        'internal_resistance_growth': simulator.internal_resistance_growth,
        'last_real_time': last_real_time + steps * step_delay,
        'prev_voltage': V_meas,
        'prev_current': -I_meas
    })

# Endpoints
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/readings', methods=['GET'])
def get_readings():
    sync_simulation_on_demand()
    return jsonify(local_telemetry_buffer)

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

@app.route('/api/health', methods=['GET'])
def get_health():
    sync_simulation_on_demand()
    state = load_sim_state()
    db_ready = False
    points_count = 0
    try:
        db_ready = _ensure_db()
        if db_ready:
            points_count = db[Config.MONGODB_READINGS_COLLECTION].count_documents({})
    except Exception:
        db_ready = False

    return jsonify({
        'service': 'battery-simulator',
        'ready': True,
        'uptime_seconds': round(time.time() - app_start_time, 2),
        'database': {
            'connected': db_ready,
            'readings_count': points_count
        },
        'status': {
            'sim_running': state.get('sim_running', False),
            'chemistry': state.get('chemistry', 'li_ion'),
            'active_cycle': state.get('active_cycle', 'udds'),
            'accelerated_aging': state.get('accelerated_aging', False),
            'T_ambient': state.get('T_ambient', 25.0),
            'fault_thermal': state.get('fault_thermal', False),
            'fault_dropout': state.get('fault_dropout', False),
            'fault_short': state.get('fault_short', False),
            'time': state.get('time', 0.0),
            'soc': state.get('soc', 1.0),
            'soh': state.get('soh', 1.0),
            'voltage': state.get('prev_voltage', 12.6),
            'current': state.get('prev_current', 0.0),
            'temperature': state.get('temperature', 25.0)
        }
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    sync_simulation_on_demand()
    state = load_sim_state()
    points_count = 0
    if _ensure_db():
        try:
            points_count = db[Config.MONGODB_READINGS_COLLECTION].count_documents({})
        except Exception:
            pass
            
    return jsonify({
        'sim_running': state.get('sim_running', False),
        'chemistry': state.get('chemistry', 'li_ion'),
        'active_cycle': state.get('active_cycle', 'udds'),
        'accelerated_aging': state.get('accelerated_aging', False),
        'T_ambient': state.get('T_ambient', 25.0),
        'fault_thermal': state.get('fault_thermal', False),
        'fault_dropout': state.get('fault_dropout', False),
        'fault_short': state.get('fault_short', False),
        'time': state.get('time', 0.0),
        'soc': state.get('soc', 1.0),
        'soh': state.get('soh', 1.0),
        'voltage': state.get('prev_voltage', 12.6),
        'current': state.get('prev_current', 0.0),
        'temperature': state.get('temperature', 25.0),
        'telemetry_count': points_count,
        'mongodb_connected': _ensure_db()
    })

@app.route('/api/control', methods=['POST'])
def post_control():
    sync_simulation_on_demand()
    try:
        data = request.json or {}
        command = data.get('command')
        chemistry = data.get('chemistry')
        cycle_type = data.get('cycle_type')
        accelerated_aging = data.get('accelerated_aging')
        T_ambient = data.get('T_ambient')
        fault_thermal = data.get('fault_thermal')
        fault_dropout = data.get('fault_dropout')
        fault_short = data.get('fault_short')
        
        state = load_sim_state()
        
        if chemistry is not None:
            state['chemistry'] = chemistry
            
        if command == 'start':
            state['sim_running'] = True
            state['last_real_time'] = time.time()
        elif command == 'stop' or command == 'pause':
            state['sim_running'] = False
        elif command == 'reset':
            state['sim_running'] = False
            if chemistry is None:
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
            
            local_telemetry_buffer.clear()
            # Clear Battery State Estimator readings collection
            if _ensure_db():
                try:
                    db[Config.MONGODB_READINGS_COLLECTION].delete_many({})
                except Exception as db_err:
                    print(f"Battery State Estimator — Error purging readings: {db_err}")
                    
        if cycle_type is not None:
            state['active_cycle'] = cycle_type
            
        if accelerated_aging is not None:
            state['accelerated_aging'] = bool(accelerated_aging)

        if T_ambient is not None:
            state['T_ambient'] = float(T_ambient)

        if fault_thermal is not None:
            was_thermal = state.get('fault_thermal', False)
            is_thermal = bool(fault_thermal)
            state['fault_thermal'] = is_thermal
            if was_thermal and not is_thermal:
                state['temperature'] = state.get('T_ambient', 25.0)

        if fault_dropout is not None:
            state['fault_dropout'] = bool(fault_dropout)

        if fault_short is not None:
            state['fault_short'] = bool(fault_short)
            
        save_sim_state(state)
        return jsonify({
            'status': 'ok',
            'sim_running': state['sim_running'],
            'chemistry': state['chemistry'],
            'active_cycle': state['active_cycle'],
            'accelerated_aging': state['accelerated_aging'],
            'T_ambient': state.get('T_ambient', 25.0),
            'fault_thermal': state.get('fault_thermal', False),
            'fault_dropout': state.get('fault_dropout', False),
            'fault_short': state.get('fault_short', False),
            'time': state['time']
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


import atexit
import tempfile

LOCK_FILE = os.path.join(tempfile.gettempdir(), 'battery_simulator_thread.lock')

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


def db_checker_loop():
    global _mongodb_connected, db_client, db, _mongodb_error
    while True:
        if not _mongodb_connected or db_client is None:
            try:
                db_client = MongoClient(Config.MONGODB_URI)
                db_client.server_info()
                db = db_client[Config.MONGODB_DB_NAME]
                _mongodb_connected = True
                _mongodb_error = None
            except Exception as e:
                _mongodb_connected = False
                db_client = None
                db = None
                _mongodb_error = str(e)
        else:
            try:
                db_client.server_info()
                _mongodb_connected = True
                _mongodb_error = None
            except Exception as e:
                _mongodb_connected = False
                db_client = None
                db = None
                _mongodb_error = str(e)
        time.sleep(3.0)

# Battery State Estimator — Physics Engine startup
# Thread starts at module level so it works under gunicorn AND direct execution.
# _start_sim_thread() checks lock file to ensure only one worker runs
_sim_thread_started = False
_db_thread_started = False

def _start_sim_thread():
    global _sim_thread_started, _db_thread_started
    if IS_SERVERLESS:
        return
    
    # Start DB checker thread for this process if not already started
    if not _db_thread_started:
        _db_thread_started = True
        db_checker = threading.Thread(target=db_checker_loop, daemon=True)
        db_checker.start()
        
    # Start generator thread if lock is acquired and generator not already running in this process
    if not _sim_thread_started:
        if _acquire_lock():
            _sim_thread_started = True
            t = threading.Thread(target=generator_loop, daemon=True)
            t.start()

# Lazy-start threads on first HTTP request when running under WSGI servers like Gunicorn
_lazy_initialized = False
_lazy_lock = threading.Lock()

@app.before_request
def _lazy_init():
    global _lazy_initialized
    if not _lazy_initialized:
        with _lazy_lock:
            if not _lazy_initialized:
                _start_sim_thread()
                _lazy_initialized = True

if __name__ == '__main__':
    _start_sim_thread()
    # Wait for the first asynchronous database check to complete (up to 5.0 seconds)
    start_wait = time.time()
    while not _mongodb_connected and (time.time() - start_wait) < 5.0:
        time.sleep(0.05)

    # Initialize config singleton in MongoDB if connected
    if _mongodb_connected and db is not None:
        try:
            if db[Config.MONGODB_STATE_COLLECTION].find_one({'_id': 'singleton'}) is None:
                baseline = DEFAULT_STATE.copy()
                baseline['_id'] = 'singleton'
                db[Config.MONGODB_STATE_COLLECTION].insert_one(baseline)
        except Exception:
            pass

    print("\nBMS Physical Simulator")
    print(f"Hardware-in-the-Loop Telemetry Generator • http://localhost:{Config.PORT}\n")
    sim_status = "Running" if local_state.get('sim_running') else "Idle"
    print(f"Simulator: {sim_status}")
    if _mongodb_connected:
        print("MongoDB: Connected\n")
    else:
        print("MongoDB: Connection Failed")
        if _mongodb_error:
            print(f"  └─ Connection Error: {_mongodb_error}")
        print("  └─ Note: Check internet connection, credentials in .env, or MongoDB Atlas IP Access List whitelist.\n")

    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.FLASK_DEBUG)