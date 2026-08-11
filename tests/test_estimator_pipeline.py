import pytest
import numpy as np
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
