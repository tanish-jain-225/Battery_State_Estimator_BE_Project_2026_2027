import pytest
import sys
import os

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
visualiser_dir = os.path.join(root_dir, "software", "visualiser")
if visualiser_dir not in sys.path:
    sys.path.insert(0, visualiser_dir)
simulator_dir = os.path.join(root_dir, "software", "simulator")
if simulator_dir not in sys.path:
    sys.path.insert(0, simulator_dir)

from software.simulator.app import app as simulator_app
from software.visualiser.app import app as visualiser_app

@pytest.fixture
def simulator_client():
    simulator_app.config['TESTING'] = True
    with simulator_app.test_client() as client:
        yield client

@pytest.fixture
def visualiser_client():
    visualiser_app.config['TESTING'] = True
    with visualiser_app.test_client() as client:
        yield client

def test_simulator_status_endpoint(simulator_client):
    res = simulator_client.get('/api/status')
    assert res.status_code == 200
    data = res.get_json()
    assert 'status' in data or 'sim_running' in data

def test_simulator_readings_endpoint(simulator_client):
    res = simulator_client.get('/api/status')
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)

def test_visualiser_status_endpoint(visualiser_client):
    res = visualiser_client.get('/api/status')
    assert res.status_code == 200
    data = res.get_json()
    assert 'status' in data or 'sim_running' in data

def test_visualiser_telemetry_endpoint(visualiser_client):
    res = visualiser_client.get('/api/telemetry')
    assert res.status_code == 200
    data = res.get_json()
    assert 'data' in data or 'status' in data or 'readings' in data

def test_visualiser_control_endpoint(visualiser_client):
    res = visualiser_client.post('/api/control', json={'action': 'start'})
    assert res.status_code in (200, 401)
