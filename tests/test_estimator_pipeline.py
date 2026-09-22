import sys
import os

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
visualiser_dir = os.path.join(root_dir, "software", "visualiser")
if visualiser_dir not in sys.path:
    sys.path.insert(0, visualiser_dir)

from software.visualiser.estimator_pipeline import EstimatorPipeline

def test_estimator_pipeline_initialization():
    ep = EstimatorPipeline()
    assert ep.ekf_soc == 1.0
    assert ep.ukf_soc == 1.0
    assert ep.cc_soc == 1.0

def test_estimator_pipeline_step():
    ep = EstimatorPipeline()
    res = ep.step(V_meas=3.7, I_meas_discharge=2.0, T_meas=25.0)
    
    assert 'ekf_soc' in res
    assert 'ukf_soc' in res
    assert 'cc_soc' in res
    assert 'esn_soc' in res
    assert 0.0 <= res['ekf_soc'] <= 1.0
    assert 0.0 <= res['ukf_soc'] <= 1.0
    assert 0.0 <= res['cc_soc'] <= 1.0

def test_rolling_history_accumulation():
    ep = EstimatorPipeline()
    assert len(ep.rolling_history) == 0
    for i in range(10):
        ep.step(V_meas=3.7 - 0.01*i, I_meas_discharge=2.0, T_meas=25.0 + 0.1*i)
    assert len(ep.rolling_history) == 10

def test_fault_diagnostics():
    ep = EstimatorPipeline()
    # Sensor dropout fault (V_meas = 0V)
    res_dropout = ep.step(V_meas=0.0, I_meas_discharge=0.0, T_meas=25.0)
    assert 'sensor_dropout' in res_dropout['faults']
    
    # Thermal runaway fault
    res_thermal = ep.step(V_meas=3.7, I_meas_discharge=2.0, T_meas=80.0, fault_thermal=True)
    assert 'thermal_runaway' in res_thermal['faults']


def test_estimator_pipeline_state_serialization():
    ep = EstimatorPipeline()
    ep.step(V_meas=3.65, I_meas_discharge=3.0, T_meas=28.0)
    state = ep.get_state()
    
    assert 'ukf_soc' in state
    assert 'ukf_p' in state
    assert 'ekf_soc' in state
    assert 'rls_r0' in state
    
    ep_restored = EstimatorPipeline()
    ep_restored.set_state(state)
    
    assert ep_restored.ukf_soc == ep.ukf_soc
    assert ep_restored.ekf_soc == ep.ekf_soc
    assert ep_restored.cc_soc == ep.cc_soc
    assert ep_restored.trad_r0 == ep.trad_r0


def test_soe_calculation():
    """Validates State of Energy (SOE) output is bounded and monotonic with SOC."""
    ep = EstimatorPipeline()
    soe_full = ep.calculate_soe(1.0)
    soe_half = ep.calculate_soe(0.5)
    soe_empty = ep.calculate_soe(0.0)
    
    assert 0.99 <= soe_full <= 1.0, f"SOE at SOC=1.0 should be ~1.0, got {soe_full}"
    assert soe_empty == 0.0, "SOE at SOC=0.0 should be 0.0"
    assert soe_half < soe_full, "SOE should decrease with lower SOC"
    assert soe_empty < soe_half, "SOE should be monotonically increasing with SOC"


def test_sop_calculation():
    """Validates State of Power (SOP) charge/discharge limits are non-negative."""
    ep = EstimatorPipeline()
    res = ep.step(V_meas=3.7, I_meas_discharge=2.0, T_meas=25.0)
    
    assert 'sop_charge_curr' in res
    assert 'sop_discharge_curr' in res
    assert 'sop_charge_pwr' in res
    assert 'sop_discharge_pwr' in res
    assert res['sop_charge_curr'] >= 0.0
    assert res['sop_discharge_curr'] >= 0.0
    assert res['sop_charge_pwr'] >= 0.0
    assert res['sop_discharge_pwr'] >= 0.0


def test_rul_calculation():
    """Validates Remaining Useful Life (RUL) output is present and non-negative."""
    ep = EstimatorPipeline()
    res = ep.step(V_meas=3.7, I_meas_discharge=1.0, T_meas=25.0)
    
    assert 'ekf_rul_cycles' in res
    assert 'esn_rul_cycles' in res
    assert res['ekf_rul_cycles'] >= 0.0
    assert res['esn_rul_cycles'] >= 0.0


def test_chemistry_switching():
    """Validates the estimator pipeline works correctly with non-default chemistries."""
    for chem in ['lfp', 'lead_acid', 'nmc']:
        ep = EstimatorPipeline(chemistry_name=chem)
        res = ep.step(V_meas=3.2, I_meas_discharge=1.0, T_meas=25.0)
        assert 0.0 <= res['ekf_soc'] <= 1.0, f"EKF SOC out of bounds for {chem}"
        assert 0.0 <= res['ukf_soc'] <= 1.0, f"UKF SOC out of bounds for {chem}"
        assert 0.0 <= res['cc_soc'] <= 1.0, f"CC SOC out of bounds for {chem}"


