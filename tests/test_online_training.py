import pytest
import sys
import os
import time
import numpy as np

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
visualiser_dir = os.path.join(root_dir, "software", "visualiser")
if visualiser_dir not in sys.path:
    sys.path.insert(0, visualiser_dir)
training_dir = os.path.join(visualiser_dir, "training")
if training_dir not in sys.path:
    sys.path.insert(0, training_dir)

import software.visualiser.config as visualiser_config
from software.visualiser.app import app as visualiser_app, run_training_async, training_status
from software.visualiser.training.train_rc import EchoStateNetwork, generate_full_range_dataset

Config = visualiser_config.Config

@pytest.fixture
def visualiser_client():
    visualiser_app.config['TESTING'] = True
    with visualiser_app.test_client() as client:
        yield client

def test_production_detection():
    # Test is_production helper method in Config
    old_val = os.environ.get('RENDER')
    try:
        os.environ['RENDER'] = 'true'
        assert Config.is_production() is True
        os.environ.pop('RENDER', None)
        os.environ['SERVERLESS'] = '1'
        assert Config.is_production() is True
    finally:
        if old_val is not None:
            os.environ['RENDER'] = old_val
        else:
            os.environ.pop('RENDER', None)
        os.environ.pop('SERVERLESS', None)

def test_esn_adapt_online_stability():
    esn = EchoStateNetwork(n_inputs=4, n_reservoir=20, n_outputs=1)
    esn.W_out = np.zeros((1, 1 + 4 + 20))
    u = np.array([3.7, 1.2, 0.01, 1.0])
    
    # Test RLS update
    esn.adapt_online(u, y_target=0.8, mode='rls')
    assert not np.any(np.isnan(esn.W_out))
    assert not np.any(np.isinf(esn.W_out))
    
    # Test NLMS update
    esn.adapt_online(u, y_target=0.85, mode='nlms')
    assert not np.any(np.isnan(esn.W_out))
    assert not np.any(np.isinf(esn.W_out))

def test_esn_train_timeout_check():
    esn = EchoStateNetwork(n_inputs=4, n_reservoir=20, n_outputs=1)
    U = np.random.randn(500, 4)
    Y = np.random.randn(500, 1)
    
    def expired_timeout():
        raise TimeoutError("Test timeout limit exceeded.")
        
    with pytest.raises(TimeoutError):
        esn.train(U, Y, washout=10, timeout_check=expired_timeout)

def test_online_training_bounded_execution():
    # Verify training completes within small dataset bound
    orig_timeout = Config.ONLINE_TRAINING_TIMEOUT
    try:
        Config.ONLINE_TRAINING_TIMEOUT = 10.0
        start = time.time()
        run_training_async()
        duration = time.time() - start
        
        assert duration < 15.0
        assert training_status['status'] in ('completed', 'failed')
        assert 'logs' in training_status
    finally:
        Config.ONLINE_TRAINING_TIMEOUT = orig_timeout

def test_online_training_timeout_fallback():
    # Set extremely short timeout to verify graceful TimeoutError catching and status update
    orig_timeout = Config.ONLINE_TRAINING_TIMEOUT
    try:
        Config.ONLINE_TRAINING_TIMEOUT = 0.000001
        time.sleep(0.002)
        run_training_async()
        
        assert training_status['status'] in ('completed', 'failed')
        assert 'TIMEOUT' in training_status['logs'] or 'exceeded' in training_status['logs']
    finally:
        Config.ONLINE_TRAINING_TIMEOUT = orig_timeout

def test_api_train_synchronous_endpoint(visualiser_client):
    res = visualiser_client.post('/api/train?sync=true')
    assert res.status_code == 200
    data = res.get_json()
    assert 'status' in data
    assert data['status'] in ('completed', 'running', 'started', 'failed')

def test_cloud_dataset_online_training_speed():
    # Verify online training completes rapidly (under 10s) when cloud data or large datasets are present
    orig_url = getattr(Config, 'CSV_URL', '')
    try:
        # Simulate cloud dataset URL configured
        Config.CSV_URL = 'http://127.0.0.1:9999/dummy_cloud_data.csv'
        start = time.time()
        run_training_async()
        duration = time.time() - start
        
        # Must complete under 10 seconds (well under 120-second limit)
        assert duration < 10.0
        assert training_status['status'] in ('completed', 'failed')
    finally:
        Config.CSV_URL = orig_url

def test_startup_data_prefetch():
    from software.visualiser.app import init_previous_data, _last_fetched_df
    df = init_previous_data()
    assert df is not None
    assert len(df) > 0

def test_tiered_fallback_logic():
    import software.visualiser.app as app_mod
    orig_url = Config.CSV_URL
    try:
        # Scenario 1: Doc link inaccessible -> uses previously loaded data
        Config.CSV_URL = 'http://127.0.0.1:9999/inaccessible_doc_link.csv'
        app_mod.init_previous_data()
        app_mod.run_training_async()
        assert app_mod.training_status['training_source'] in ('Previously Loaded Data', 'Local Trained File Data')

        # Scenario 2: No doc link and no previous data -> uses local trained file data
        Config.CSV_URL = ''
        app_mod._last_fetched_df = None
        app_mod.run_training_async()
        assert app_mod.training_status['training_source'] == 'Local Trained File Data'
    finally:
        Config.CSV_URL = orig_url

