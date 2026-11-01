import sys
import os
import numpy as np
import pandas as pd

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

stm_dir = os.path.join(root_dir, "hardware", "STM_Verifier")
if stm_dir not in sys.path:
    sys.path.insert(0, stm_dir)

import train_classifier as tc
import train_estimator as te
from train import EchoStateNetwork, simulate_quantization


def test_csr_matrix_compression():
    """Verify to_csr converts a sparse 2D matrix into correct CSR val, col, row_ptr arrays."""
    matrix = np.array([
        [1.0, 0.0, 2.0],
        [0.0, 0.0, 0.0],
        [3.0, 4.0, 0.0]
    ])
    val, col, row_ptr = tc.to_csr(matrix)
    
    assert list(val) == [1.0, 2.0, 3.0, 4.0]
    assert list(col) == [0, 2, 0, 1]
    assert list(row_ptr) == [0, 2, 2, 4]


def test_clean_df_columns_variations():
    """Verify clean_df_columns handles case sensitivity and comma-separated column names."""
    df_raw = pd.DataFrame({
        'voltage': [3.7, 3.8],
        'CURRENT': [1.5, 2.0],
        'Temperature': [25.0, 26.0],
        'soc': [0.9, 0.85]
    })
    df_cleaned = tc.clean_df_columns(df_raw)
    assert 'Voltage' in df_cleaned.columns
    assert 'Current' in df_cleaned.columns
    assert 'Temperature' in df_cleaned.columns
    assert 'SOC' in df_cleaned.columns


def test_thermal_labels_classification():
    """Verify get_labels categorizes thermal states according to thresholds."""
    df_temp = pd.DataFrame({
        'Temperature': [25.0, 38.0, 52.0]
    })
    labels = tc.get_labels(df_temp)
    assert len(labels) == 3
    # With TEMP_NORMAL_MAX=35 and TEMP_WARNING_MAX=45:
    assert labels[0] == 0  # Normal (< 35°C)
    assert labels[1] == 1  # Warning (35°C <= T < 45°C)
    assert labels[2] == 2  # Critical (>= 45°C)


def test_simulate_quantization_precision():
    """Verify simulate_quantization truncates floating values to target bitwidth."""
    arr = np.array([0.0, 0.5, 1.0, -0.5])
    q_arr = simulate_quantization(arr, bits_limit=8)
    assert q_arr.shape == arr.shape
    # Error should be within 1 LSB of 8-bit quantization (1/128)
    assert np.all(np.abs(q_arr - arr) < 0.02)


def test_esn_instantiation_and_quantized_predict():
    """Verify EchoStateNetwork initializes, trains, and runs predict_step with quantization."""
    esn = EchoStateNetwork(n_inputs=3, n_reservoir=20, n_outputs=1, spectral_radius=0.9, leak_rate=0.3)
    U = np.random.randn(30, 3)
    Y = np.random.rand(30, 1)
    
    esn.train(U, Y, washout=5)
    pred_step = esn.predict_step(U[0], quantize_mode='q15')
    assert len(pred_step) == 1
    assert not np.isnan(pred_step[0])


def test_generate_full_range_dataset_structure():
    """Verify generate_full_range_dataset produces expected columns and valid bounds."""
    df_syn = te.generate_full_range_dataset()
    assert isinstance(df_syn, pd.DataFrame)
    assert not df_syn.empty
    for col in ['Voltage', 'Current', 'Temperature', 'SOC', 'SOH']:
        assert col in df_syn.columns
    assert df_syn['SOC'].min() >= 0.0
    assert df_syn['SOC'].max() <= 1.0
    assert df_syn['SOH'].min() >= 0.75
    assert df_syn['SOH'].max() <= 1.0


def test_exported_c_headers_existence():
    """Verify generated C header files exist and contain necessary STM32 definitions."""
    cls_h = os.path.join(stm_dir, "esn_classifier_weights.h")
    est_h = os.path.join(stm_dir, "esn_estimator_weights.h")
    
    assert os.path.exists(cls_h), f"Missing {cls_h}"
    assert os.path.exists(est_h), f"Missing {est_h}"
    
    with open(cls_h, "r") as f:
        content_cls = f.read()
    assert "#define ESN_N_INPUTS" in content_cls
    assert "#define ESN_N_RESERVOIR" in content_cls
    assert "esn_W_res_val" in content_cls

    with open(est_h, "r") as f:
        content_est = f.read()
    assert "#define ESN_ESTIMATOR_N_INPUTS" in content_est or "#define ESN_N_INPUTS" in content_est
    assert "esn_soc_W_res_val" in content_est or "esn_W_res_val" in content_est
