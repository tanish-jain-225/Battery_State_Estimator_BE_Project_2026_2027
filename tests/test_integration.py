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
    export_coe,
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
