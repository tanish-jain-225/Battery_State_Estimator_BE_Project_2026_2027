import numpy as np
import sys
import os

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
training_dir = os.path.join(root_dir, "software", "visualiser", "training")
if training_dir not in sys.path:
    sys.path.insert(0, training_dir)

from software.visualiser.training.train_rc import EchoStateNetwork

def test_esn_initialization():
    esn = EchoStateNetwork(n_inputs=3, n_outputs=1, n_reservoir=20)
    assert esn.n_reservoir == 20
    assert esn.W_in.shape == (20, 4)
    assert esn.W_res.shape == (20, 20)
    assert esn.x.shape == (20, 1)

def test_esn_prediction_step():
    esn = EchoStateNetwork(n_inputs=3, n_outputs=1, n_reservoir=20)
    esn.W_out = np.random.randn(1, 1 + 3 + 20) * 0.01
    
    u = np.array([3.7, 2.0, 25.0])
    pred = esn.predict_step(u, quantize_mode='float32')
    
    assert pred.shape == (1,)
    assert 0.0 <= pred[0] <= 1.0

def test_esn_quantized_prediction():
    esn = EchoStateNetwork(n_inputs=3, n_outputs=1, n_reservoir=20)
    esn.W_out = np.random.randn(1, 1 + 3 + 20) * 0.01
    
    u = np.array([3.7, 2.0, 25.0])
    pred_float = esn.predict_step(u, quantize_mode='float32')
    pred_int16 = esn.predict_step(u, quantize_mode='int16')
    
    assert pred_int16.shape == (1,)
    assert abs(pred_float[0] - pred_int16[0]) < 0.2

def test_esn_online_adaptation():
    esn = EchoStateNetwork(n_inputs=3, n_outputs=1, n_reservoir=20)
    esn.W_out = np.zeros((1, 1 + 3 + 20))
    
    u = np.array([3.7, 2.0, 25.0])
    target = 0.8
    
    for _ in range(5):
        esn.adapt_online(u, target, mode='rls')
        
    pred = esn.predict_step(u)
    assert abs(pred[0] - target) < 0.5

def test_generate_full_range_dataset_fallback():
    from software.visualiser.training.train_rc import generate_full_range_dataset as gen_rc
    from hardware.STM_Verifier.train_estimator import generate_full_range_dataset as gen_est

    df_rc = gen_rc(max_rows=50)
    assert not df_rc.empty
    assert set(['Time', 'Voltage', 'Current', 'Temperature', 'SOC', 'SOH']).issubset(df_rc.columns)

    df_est = gen_est()
    assert not df_est.empty
    assert set(['Time', 'Voltage', 'Current', 'Temperature', 'SOC', 'SOH']).issubset(df_est.columns)

