import os
import sys

import pytest

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from software.simulator.app import app as simulator_app
from software.visualiser.app import app as visualiser_app


@pytest.fixture
def sim_client():
    simulator_app.config['TESTING'] = True
    with simulator_app.test_client() as client:
        yield client


@pytest.fixture
def vis_client():
    visualiser_app.config['TESTING'] = True
    with visualiser_app.test_client() as client:
        yield client


def test_simulator_index_route(sim_client):
    res = sim_client.get('/')
    assert res.status_code == 200
    assert b"Battery" in res.data or b"Simulator" in res.data or b"html" in res.data.lower()


def test_simulator_health_route(sim_client):
    res = sim_client.get('/api/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data.get('ready') is True
    assert data.get('service') == 'battery-simulator'
    assert 'status' in data


def test_simulator_status_route(sim_client):
    res = sim_client.get('/api/status')
    assert res.status_code == 200
    data = res.get_json()
    assert 'sim_running' in data
    assert 'chemistry' in data
    assert 'time' in data
    assert 'soc' in data
    assert 'soh' in data


def test_simulator_readings_limit(sim_client):
    res = sim_client.get('/api/readings?limit=5')
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) <= 5


def test_simulator_control_commands(sim_client):
    # Test Start
    res_start = sim_client.post('/api/control', json={'command': 'start'})
    assert res_start.status_code == 200
    assert res_start.get_json()['sim_running'] is True

    # Test Pause
    res_pause = sim_client.post('/api/control', json={'command': 'pause'})
    assert res_pause.status_code == 200
    assert res_pause.get_json()['sim_running'] is False

    # Test Changing Environment Parameters
    res_env = sim_client.post('/api/control', json={
        'chemistry': 'nmc',
        'cycle_type': 'us06',
        'accelerated_aging': True,
        'T_ambient': 35.0,
        'fault_thermal': True
    })
    assert res_env.status_code == 200
    data = res_env.get_json()
    assert data['chemistry'] == 'nmc'
    assert data['active_cycle'] == 'us06'
    assert data['accelerated_aging'] is True
    assert data['T_ambient'] == 35.0
    assert data['fault_thermal'] is True

    # Test Reset
    res_reset = sim_client.post('/api/control', json={'command': 'reset', 'soc': 0.9, 'soh': 0.95})
    assert res_reset.status_code == 200
    data_reset = res_reset.get_json()
    assert data_reset['sim_running'] is False


def test_simulator_chemistry_register(sim_client):
    payload = {
        'name': 'test_sim_chem',
        'nominal_capacity': 3.0,
        'R0_nom': 0.02,
        'R1_nom': 0.015,
        'C1_nom': 800.0,
        'R2_nom': 0.02,
        'C2_nom': 2000.0,
        'ocv_table': [(0.0, 3.0), (0.25, 3.4), (0.5, 3.7), (0.75, 3.9), (1.0, 4.2)]
    }
    res = sim_client.post('/api/chemistry/register', json=payload)
    assert res.status_code in (200, 201)
    data = res.get_json()
    assert data.get('status') == 'ok' or 'success' in data or 'registered' in str(data).lower()


def test_visualiser_index_route(vis_client):
    res = vis_client.get('/')
    assert res.status_code == 200
    assert b"html" in res.data.lower() or b"Dashboard" in res.data or b"Battery" in res.data


def test_visualiser_status_route(vis_client):
    res = vis_client.get('/api/status')
    assert res.status_code == 200
    data = res.get_json()
    assert 'sim_running' in data
    assert 'model_loaded' in data
    assert 'chemistry' in data
    assert 'battery_time' in data


def test_visualiser_control_commands(vis_client):
    # Test Start
    res_start = vis_client.post('/api/control', json={'command': 'start'})
    assert res_start.status_code in (200, 401)

    # Test Set Parameters
    res_params = vis_client.post('/api/control', json={
        'chemistry': 'lfp',
        'cycle_type': 'wltp',
        'T_ambient': 30.0,
        'fault_dropout': True
    })
    assert res_params.status_code in (200, 401)

    # Test Reset
    res_reset = vis_client.post('/api/control', json={'command': 'reset'})
    assert res_reset.status_code in (200, 401)


def test_visualiser_telemetry_endpoint(vis_client):
    res = vis_client.get('/api/telemetry')
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)
    assert 'readings' in data or 'data' in data or 'status' in data


def test_visualiser_train_status_endpoint(vis_client):
    res = vis_client.get('/api/train/status')
    assert res.status_code == 200
    data = res.get_json()
    assert 'is_training' in data or 'training' in data or 'status' in data


def test_visualiser_chemistry_register(vis_client):
    payload = {
        'name': 'test_vis_chem',
        'nominal_capacity': 2.5,
        'R0_nom': 0.025,
        'R1_nom': 0.015,
        'C1_nom': 1000.0,
        'R2_nom': 0.02,
        'C2_nom': 2500.0,
        'ocv_table': [(0.0, 2.8), (0.25, 3.4), (0.5, 3.6), (0.75, 3.8), (1.0, 4.1)]
    }
    res = vis_client.post('/api/chemistry/register', json=payload)
    assert res.status_code in (200, 201)
    data = res.get_json()
    assert data.get('status') == 'ok' or 'success' in data or 'registered' in str(data).lower()
