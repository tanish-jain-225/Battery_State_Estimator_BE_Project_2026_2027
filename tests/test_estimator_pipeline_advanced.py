import sys
import os
import numpy as np

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from software.visualiser.estimator_pipeline import (
    EstimatorPipeline,
    _trapezoidal_integration,
    extract_features_step
)
from software.visualiser.config import Config


def test_pipeline_load_saved_model():
    """Verify EstimatorPipeline successfully loads the local trained ESN model."""
    ep = EstimatorPipeline()
    success = ep.load_saved_model()
    assert success is True
    assert ep.esn_soc is not None
    assert ep.esn_soh is not None
    assert ep.input_means is not None
    assert ep.input_stds is not None


def test_pipeline_create_with_model_factory():
    """Verify the factory constructor creates an initialized pipeline with model loaded."""
    ep = EstimatorPipeline.create_with_model(chemistry_name="li_ion")
    assert ep.chemistry_name == "li_ion"
    assert ep.esn_soc is not None
    assert ep.esn_soh is not None


def test_pipeline_full_esn_step():
    """Verify that with model loaded, step() performs reservoir updates and predictions."""
    ep = EstimatorPipeline.create_with_model()
    res = ep.step(V_meas=3.7, I_meas_discharge=2.0, T_meas=25.0, dt=1.0)
    
    assert 'esn_soc' in res
    assert 'esn_soh' in res
    assert 0.0 <= res['esn_soc'] <= 1.0
    assert 0.0 <= res['esn_soh'] <= 1.0
    assert res['model_loaded'] is True
    assert res['esn_time'] >= 0.0
    assert isinstance(res['esn_features'], list)
    assert len(res['esn_features']) > 0


def test_pipeline_priming():
    """Verify prime_esn warms up internal reservoir state without crash."""
    ep = EstimatorPipeline.create_with_model()
    assert ep.primed is False
    ep.prime_esn(V_initial=3.8, T_initial=25.0, I_initial=2.0, priming_steps=10)
    assert ep.primed is True
    assert ep.esn_soc_state is not None
    assert ep.esn_soh_state is not None


def test_pipeline_standalone_mode(monkeypatch):
    """Verify standalone mode produces pure data-driven ESN output."""
    monkeypatch.setattr(Config, "ENABLE_ESN_STANDALONE", True)
    ep = EstimatorPipeline.create_with_model()
    res = ep.step(V_meas=3.65, I_meas_discharge=1.5, T_meas=26.0)
    assert 'esn_soc' in res
    assert 0.0 <= res['esn_soc'] <= 1.0


def test_pipeline_multi_chemistries():
    """Verify pipeline functions correctly across all battery chemistry configurations."""
    for chem in ['li_ion', 'nmc', 'lfp', 'lead_acid']:
        ep = EstimatorPipeline.create_with_model(chemistry_name=chem)
        nom_v = ep.chem_obj.lookup_ocv(0.5)
        res = ep.step(V_meas=nom_v, I_meas_discharge=1.0, T_meas=25.0)
        assert 0.0 <= res['ekf_soc'] <= 1.0
        assert 0.0 <= res['ukf_soc'] <= 1.0
        assert 0.0 <= res['esn_soc'] <= 1.0


def test_pipeline_adaptive_rls_online():
    """Verify multiple consecutive steps execute online adaptation without numerical instability."""
    ep = EstimatorPipeline.create_with_model()
    for step_idx in range(15):
        v = 4.0 - 0.02 * step_idx
        i = 2.0 + 0.1 * np.sin(step_idx)
        res = ep.step(V_meas=v, I_meas_discharge=i, T_meas=25.0 + step_idx * 0.2)
        assert not np.isnan(res['esn_soc'])
        assert not np.isnan(res['ekf_soc'])
        assert not np.isnan(res['ukf_soc'])


def test_pipeline_sensor_fault_handling():
    """Verify pipeline detects sensor short and dropout faults gracefully."""
    ep = EstimatorPipeline.create_with_model()
    
    # Normal step
    res_norm = ep.step(V_meas=3.7, I_meas_discharge=2.0, T_meas=25.0)
    assert len(res_norm['faults']) == 0
    
    # Voltage zero dropout
    res_zero = ep.step(V_meas=0.0, I_meas_discharge=0.0, T_meas=25.0)
    assert 'sensor_dropout' in res_zero['faults']
    
    # Explicit short fault
    res_short = ep.step(V_meas=3.7, I_meas_discharge=2.0, T_meas=25.0, fault_short=True)
    assert 'internal_short' in res_short['faults']


def test_pipeline_update_noise_params():
    """Verify noise parameter updates propagate into EKF."""
    ep = EstimatorPipeline()
    ep.update_ekf_noise(q_soc=1e-5, q_v1=1e-5, q_v2=1e-5, r_meas=0.05)
    assert ep.ekf.R_meas == 0.05
    assert ep.ekf.Q[0, 0] == 1e-5


def test_trapezoidal_integration_fallback():
    """Verify trapezoidal integration helper function."""
    x = [0.0, 1.0, 2.0, 3.0]
    y = [0.0, 2.0, 4.0, 6.0]
    # Triangle area = 3 * 6 / 2 = 9.0
    val = _trapezoidal_integration(y, x)
    assert abs(val - 9.0) < 1e-6


def test_extract_features_step_empty_and_populated():
    """Verify extract_features_step handles empty history as well as rolling window history."""
    f_empty = extract_features_step(3.7, 2.0, 25.0, history=[])
    assert len(f_empty) == 6
    assert f_empty[0] == 3.7
    assert f_empty[1] == 2.0
    assert f_empty[2] == 25.0
    assert f_empty[3] == 0.0  # V_grad = 0
    
    history = [
        {'voltage': 3.75, 'current': 2.0, 'temperature': 25.0},
        {'voltage': 3.72, 'current': 2.1, 'temperature': 25.1},
    ]
    f_hist = extract_features_step(3.70, 2.2, 25.2, history=history)
    assert len(f_hist) == 6
    assert abs(f_hist[3] - (-0.02)) < 1e-6  # 3.70 - 3.72
