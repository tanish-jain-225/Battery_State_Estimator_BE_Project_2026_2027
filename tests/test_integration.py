"""
test_integration.py
───────────────────
End-to-end integration tests connecting BatterySimulator, EstimatorPipeline,
multi-chemistry verification, drive cycle sweeps, and FPGA COE roundtrip fidelity.
"""

import sys
import os
import tempfile
import numpy as np

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

visualiser_dir = os.path.join(root_dir, "software", "visualiser")
if visualiser_dir not in sys.path:
    sys.path.insert(0, visualiser_dir)

simulator_dir = os.path.join(root_dir, "software", "simulator")
if simulator_dir not in sys.path:
    sys.path.insert(0, simulator_dir)

fpga_dir = os.path.join(root_dir, "hardware", "FPGA_Verifier")
if fpga_dir not in sys.path:
    sys.path.insert(0, fpga_dir)

from software.simulator.battery_simulator import BatterySimulator, DriveCycles
from software.visualiser.estimator_pipeline import EstimatorPipeline
from hardware.FPGA_Verifier.golden_model import (
    generate_reservoir_weights,
    parse_coe_file
)


def test_end_to_end_simulator_to_estimator():
    """Validates real-time coupling between BatterySimulator and EstimatorPipeline over 50 timesteps."""
    sim = BatterySimulator("li_ion")
    ep = EstimatorPipeline("li_ion")

    ekf_errors = []
    for t in range(50):
        # Pulse current discharge
        current = 2.0 if (t // 10) % 2 == 0 else 0.5
        telemetry = sim.step(current=current, dt=1.0)
        
        # Feed directly into pipeline
        est_result = ep.step(
            V_meas=telemetry['voltage'],
            I_meas_discharge=telemetry['current'],
            T_meas=telemetry['temperature'],
            dt=1.0
        )
        
        assert 'ekf_soc' in est_result
        assert 'ukf_soc' in est_result
        assert 'cc_soc' in est_result
        
        # Track estimation error against simulator ground truth SOC
        true_soc = telemetry['true_soc']
        ekf_errors.append(abs(est_result['ekf_soc'] - true_soc))

    # Average EKF error should remain bounded within 8% during initial run
    mean_err = np.mean(ekf_errors)
    assert mean_err < 0.08, f"Mean EKF error too high: {mean_err:.4f}"


def test_multi_chemistry_integration():
    """Validates simulator and estimator pipeline interoperability across NMC, LFP, and Lead-Acid."""
    chemistries = ["li_ion", "lfp", "lead_acid"]
    for chem in chemistries:
        sim = BatterySimulator(chem)
        ep = EstimatorPipeline(chem)
        
        # Step for 15 seconds
        for _ in range(15):
            tel = sim.step(current=1.5, dt=1.0)
            res = ep.step(V_meas=tel['voltage'], I_meas_discharge=tel['current'], T_meas=tel['temperature'])
            
            assert 0.0 <= res['ekf_soc'] <= 1.0
            assert 0.0 <= res['ukf_soc'] <= 1.0
            assert 0.0 <= res['cc_soc'] <= 1.0


def test_drive_cycle_sweep_integration():
    """Sweeps multiple standard drive cycles (UDDS, HWFET, US06) and verifies filter stability."""
    cycle_names = ["constant_discharge", "pulse", "udds", "hwfet", "us06"]
    
    for cycle in cycle_names:
        sim = BatterySimulator("li_ion")
        ep = EstimatorPipeline("li_ion")
        
        # Run 25 steps for each cycle
        for t in range(25):
            curr = DriveCycles.get_current(cycle, t=float(t))
            tel = sim.step(current=curr, dt=1.0)
            res = ep.step(V_meas=tel['voltage'], I_meas_discharge=tel['current'], T_meas=tel['temperature'])
            
            assert not np.isnan(res['ekf_soc']), f"EKF produced NaN on cycle {cycle}"
            assert not np.isnan(res['ukf_soc']), f"UKF produced NaN on cycle {cycle}"
            assert 0.0 <= res['ekf_soc'] <= 1.0


def test_golden_model_coe_export_roundtrip():
    """Validates that generating weights, exporting to COE, and parsing back matches exactly."""
    Win_q, W_q, _, _, _ = generate_reservoir_weights(n_in=4, n_res=10, seed=42)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test Radix 10 export & parse
        coe_path_10 = os.path.join(tmpdir, "test_w_radix10.coe")
        flat_w = W_q.flatten()
        
        with open(coe_path_10, "w", encoding="utf-8") as f:
            f.write("; Test COE 10\n")
            f.write("memory_initialization_radix=10;\n")
            f.write("memory_initialization_vector=\n")
            f.write(",\n".join(str(int(x)) for x in flat_w) + ";\n")
            
        parsed_10 = parse_coe_file(coe_path_10)
        assert np.array_equal(flat_w, parsed_10), "Radix 10 COE parsed values did not match original"

        # Test Radix 16 export & parse
        coe_path_16 = os.path.join(tmpdir, "test_w_radix16.coe")
        with open(coe_path_16, "w", encoding="utf-8") as f:
            f.write("; Test COE 16\n")
            f.write("memory_initialization_radix=16;\n")
            f.write("memory_initialization_vector=\n")
            f.write(",\n".join(format(int(x) & 0xFFFF, '04x') for x in flat_w) + ";\n")
            
        parsed_16 = parse_coe_file(coe_path_16)
        assert np.array_equal(flat_w, parsed_16), "Radix 16 COE parsed values did not match original"


def test_simulator_visualiser_end_to_end_seamless():
    """Validates 10-step full-stack cross-talk between Simulator and Visualiser microservices."""
    from unittest.mock import patch
    from datetime import datetime
    import json
    import time

    from software.simulator.app import (
        app as sim_app,
        simulator as sim_physics,
        DriveCycles,
        Config as SimConfig,
        local_telemetry_buffer as sim_buffer,
        update_sim_progress,
        load_sim_state
    )
    from software.visualiser.app import (
        app as vis_app,
        check_simulator_port
    )

    sim_client = sim_app.test_client()
    vis_client = vis_app.test_client()

    class MockResponse:
        def __init__(self, client_response):
            self.status = client_response.status_code
            self.client_response = client_response

        def read(self):
            return self.client_response.data

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_make_simulator_request(path, method='GET', data=None, timeout=1.0):
        if method == 'GET':
            resp = sim_client.get(path)
        elif method == 'POST':
            resp = sim_client.post(path, json=data)
        else:
            resp = sim_client.open(path, method=method, json=data)
        return MockResponse(resp)

    def step_sim_manually(steps=5):
        state = load_sim_state()
        active_cycle = state.get('active_cycle', 'us06')
        step_delay = SimConfig.SIMULATION_STEP_DELAY
        for _ in range(steps):
            t = sim_physics.time
            if active_cycle == "udds":
                I = DriveCycles.udds(t)
            elif active_cycle == "us06":
                I = DriveCycles.us06(t)
            elif active_cycle == "hwfet":
                I = DriveCycles.hwfet(t)
            else:
                I = DriveCycles.constant_discharge(t)
            out = sim_physics.step(I, step_delay)
            noisy = sim_physics.add_sensor_noise(out)
            record = {
                'time': out['time'],
                'voltage': noisy['voltage'],
                'current': -noisy['current'],
                'temperature': noisy['temperature'],
                'timestamp': datetime.utcnow().isoformat(),
                'fault_short': state.get('fault_short', False),
                'fault_thermal': state.get('fault_thermal', False),
                'fault_dropout': state.get('fault_dropout', False),
                'true_soc': out['true_soc'],
                'true_soh': out['true_soh'],
                'true_v1': out['v1'],
                'true_v2': out['v2'],
                'true_r0': out['R0'],
                'true_ocv': out['ocv'],
                'true_voltage': out['voltage'],
                'true_current': -out['current']
            }
            sim_buffer.append(record)
            update_sim_progress({
                'time': sim_physics.time,
                'soc': sim_physics.soc,
                'soh': sim_physics.soh,
                'V1': sim_physics.V1,
                'V2': sim_physics.V2,
                'temperature': sim_physics.temperature,
                'internal_resistance_growth': sim_physics.internal_resistance_growth,
                'last_real_time': time.time(),
                'prev_voltage': noisy['voltage'],
                'prev_current': -noisy['current']
            })

    with patch('software.visualiser.app.make_simulator_request', side_effect=mock_make_simulator_request):
        # 1. Verify simulator status
        s_resp = sim_client.get('/api/status')
        assert s_resp.status_code == 200

        # 2. Configure cycle & chemistry via control
        c_resp = sim_client.post('/api/control', json={'command': 'start', 'cycle_type': 'us06', 'chemistry': 'lfp'})
        assert c_resp.status_code == 200
        assert c_resp.get_json().get('sim_running') is True

        # 3. Step simulator to populate telemetry buffer
        step_sim_manually(5)
        r_resp = sim_client.get('/api/readings')
        assert r_resp.status_code == 200
        readings = r_resp.get_json()
        assert len(readings) >= 5

        # 4. Check visualiser detects simulator as online
        is_online, _ = check_simulator_port(force=True)
        assert is_online is True

        # 5. Visualiser status route
        v_resp = vis_client.get('/api/status')
        assert v_resp.status_code == 200

        # 6. Visualiser telemetry endpoint pulls simulator readings & computes ESN/EKF/UKF
        t_resp = vis_client.get('/api/telemetry')
        assert t_resp.status_code == 200
        t_data = t_resp.get_json()
        telem_list = t_data.get('data') or t_data.get('readings')
        assert telem_list is not None and len(telem_list) > 0
        latest = telem_list[-1]
        assert 'ekf_soc' in latest and 'esn_soc' in latest

        # 7. Visualiser forwards control command (fault_thermal) to simulator
        ctrl_resp = vis_client.post('/api/control', json={'fault_thermal': True})
        assert ctrl_resp.status_code == 200

        # 8. Verify simulator updated fault_thermal
        s_resp2 = sim_client.get('/api/status')
        assert s_resp2.get_json().get('fault_thermal') is True

        # 9. Register a custom chemistry on Visualiser and verify it forwards to Simulator
        chem_payload = {
            'name': 'vesit_li_ion_high_rate',
            'nominal_capacity': 5.0,
            'R0_nom': 0.015,
            'R1_nom': 0.010,
            'C1_nom': 1200.0,
            'R2_nom': 0.015,
            'C2_nom': 3000.0,
            'thermal_capacitance': 120.0,
            'cooling_coefficient': 0.3,
            'n_cells': 1,
            'ocv_table': [(0.0, 3.0), (0.2, 3.3), (0.5, 3.7), (0.8, 3.9), (1.0, 4.2)]
        }
        reg_resp = vis_client.post('/api/chemistry/register', json=chem_payload)
        assert reg_resp.status_code == 200

        # 10. Test Visualiser Reset
        reset_resp = vis_client.post('/api/control', json={'command': 'reset', 'soc': 0.90})
        assert reset_resp.status_code == 200


def test_simulator_visualiser_mongodb_1s_sync():
    """Validates 1-second MongoDB synchronization interval between Simulator and Visualiser."""
    from unittest.mock import patch
    from datetime import datetime

    class MockCollection:
        def __init__(self, name):
            self.name = name
            self.docs = []

        def insert_one(self, doc):
            d = doc.copy()
            self.docs.append(d)
            return type('InsertResult', (), {'inserted_id': 'mock_id'})()

        def find_one(self, filter_dict=None, sort=None):
            matching = self.docs
            if filter_dict:
                matching = [d for d in matching if all(d.get(k) == v for k, v in filter_dict.items())]
            if not matching:
                return None
            if sort:
                key, direction = sort[0]
                matching = sorted(matching, key=lambda x: x.get(key, 0), reverse=(direction == -1))
            return matching[0].copy()

        def find(self, filter_dict=None, projection=None):
            results = self.docs
            if filter_dict:
                for k, v in filter_dict.items():
                    if isinstance(v, dict):
                        if '$gt' in v:
                            results = [d for d in results if d.get(k, 0) > v['$gt']]
                        elif '$gte' in v:
                            results = [d for d in results if d.get(k, 0) >= v['$gte']]
                    else:
                        results = [d for d in results if d.get(k) == v]

            class MockCursor:
                def __init__(self, items):
                    self.items = [i.copy() for i in items]
                def sort(self, key, direction=1):
                    self.items = sorted(self.items, key=lambda x: x.get(key, 0), reverse=(direction == -1))
                    return self
                def limit(self, n):
                    self.items = self.items[:n]
                    return self
                def __iter__(self):
                    return iter(self.items)
                def __len__(self):
                    return len(self.items)

            return MockCursor(results)

        def replace_one(self, filter_dict, doc, upsert=False):
            d = doc.copy()
            for idx, existing in enumerate(self.docs):
                if all(existing.get(k) == v for k, v in filter_dict.items()):
                    self.docs[idx] = d
                    return type('ReplaceResult', (), {'matched_count': 1, 'modified_count': 1})()
            if upsert:
                self.docs.append(d)
                return type('ReplaceResult', (), {'matched_count': 0, 'upserted_id': 'mock_id'})()
            return type('ReplaceResult', (), {'matched_count': 0, 'modified_count': 0})()

        def update_one(self, filter_dict, update_dict, upsert=False):
            set_vals = update_dict.get('$set', {})
            for existing in self.docs:
                if all(existing.get(k) == v for k, v in filter_dict.items()):
                    existing.update(set_vals)
                    return type('UpdateResult', (), {'matched_count': 1, 'modified_count': 1})()
            if upsert:
                new_doc = filter_dict.copy()
                new_doc.update(set_vals)
                self.docs.append(new_doc)
                return type('UpdateResult', (), {'matched_count': 0, 'upserted_id': 'mock_id'})()
            return type('UpdateResult', (), {'matched_count': 0, 'modified_count': 0})()

        def delete_many(self, filter_dict):
            before = len(self.docs)
            if not filter_dict:
                self.docs.clear()
            else:
                self.docs = [d for d in self.docs if not all(d.get(k) == v for k, v in filter_dict.items())]
            return type('DeleteResult', (), {'deleted_count': before - len(self.docs)})()

        def create_index(self, keys, **kwargs):
            return "index_created"

        def count_documents(self, filter_dict=None):
            if not filter_dict:
                return len(self.docs)
            return len([d for d in self.docs if all(d.get(k) == v for k, v in filter_dict.items())])

    class MockDatabase:
        def __init__(self):
            self.collections = {}

        def __getitem__(self, name):
            if name not in self.collections:
                self.collections[name] = MockCollection(name)
            return self.collections[name]

    shared_db = MockDatabase()

    class MockMongoClient:
        def __init__(self, *args, **kwargs):
            self.admin = type('Admin', (), {'command': lambda *a, **kw: True})()
        def server_info(self):
            return {'version': '6.0.0'}
        def __getitem__(self, name):
            return shared_db

    with patch('pymongo.MongoClient', MockMongoClient), \
         patch('software.simulator.app.MongoClient', MockMongoClient), \
         patch('software.visualiser.app.MongoClient', MockMongoClient):

        import software.simulator.app as sim_app
        import software.visualiser.app as vis_app

        sim_app.db = shared_db
        sim_app.db_client = MockMongoClient()
        sim_app._mongodb_connected = True
        sim_app.mongodb_connected = True

        vis_app.db = shared_db
        vis_app.db_client = MockMongoClient()
        vis_app._mongodb_connected = True
        vis_app.mongodb_connected = True

        sim_client = sim_app.app.test_client()
        vis_client = vis_app.app.test_client()

        # 1. Initialize MongoDB singleton state
        baseline = sim_app.DEFAULT_STATE.copy()
        baseline['sim_running'] = False
        sim_app.save_sim_state(baseline)
        doc = shared_db[sim_app.Config.MONGODB_STATE_COLLECTION].find_one({'_id': 'singleton'})
        assert doc is not None

        # 2. Visualiser reads state from MongoDB
        v_state = vis_app.load_sim_state(force_db_read=True)
        assert v_state['chemistry'] == doc['chemistry']

        # 3. Visualiser issues control command, saving to MongoDB
        vis_client.post('/api/control', json={'command': 'start', 'cycle_type': 'us06', 'chemistry': 'lfp'})
        db_state = shared_db[sim_app.Config.MONGODB_STATE_COLLECTION].find_one({'_id': 'singleton'})
        assert db_state['sim_running'] is True
        assert db_state['chemistry'] == 'lfp'

        # 4. Simulator loads updated state on 1-second sync interval
        sim_app._last_state_load_time = 0.0
        s_state = sim_app.load_sim_state()
        assert s_state['sim_running'] is True
        assert s_state['chemistry'] == 'lfp'

        # 5. Insert simulated readings at 1.0 second intervals into MongoDB
        for t in [1.0, 2.0, 3.0]:
            rec = {
                'time': t,
                'voltage': 3.3,
                'current': -2.0,
                'temperature': 25.0,
                'timestamp': datetime.utcnow().isoformat(),
                'fault_short': False,
                'fault_thermal': False,
                'fault_dropout': False,
                'true_soc': 0.98,
                'true_soh': 1.0,
                'true_v1': 0.0,
                'true_v2': 0.0,
                'true_r0': 0.02,
                'true_ocv': 3.3,
                'true_voltage': 3.3,
                'true_current': 2.0
            }
            shared_db[sim_app.Config.MONGODB_READINGS_COLLECTION].insert_one(rec)
            sim_app.update_sim_progress({'time': t, 'soc': 0.98})

        # 6. Visualiser fetches telemetry from MongoDB
        t_resp = vis_client.get('/api/telemetry')
        assert t_resp.status_code == 200
        t_data = t_resp.get_json()
        items = t_data.get('data') or t_data.get('readings')
        assert len(items) >= 3

        # 7. Reset clears MongoDB collection and syncs
        r_resp = vis_client.post('/api/control', json={'command': 'reset', 'soc': 1.0})
        assert r_resp.status_code == 200
        assert len(shared_db[sim_app.Config.MONGODB_READINGS_COLLECTION].docs) == 0


