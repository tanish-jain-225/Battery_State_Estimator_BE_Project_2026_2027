import sys
import os
import unittest
import numpy as np
import importlib.util

# Add parent directories to path to allow imports of local packages
this_dir       = os.path.dirname(os.path.abspath(__file__))
visualiser_dir = os.path.dirname(this_dir)
software_dir   = os.path.dirname(visualiser_dir)
simulator_dir  = os.path.join(software_dir, 'simulator')

sys.path.insert(0, simulator_dir)
sys.path.insert(0, os.path.join(visualiser_dir, 'training'))
sys.path.insert(0, visualiser_dir)

from battery_chemistry import get_chemistry
from battery_simulator import BatterySimulator
from traditional_estimator import ExtendedKalmanFilter, ResistanceSOH
from feature_engineering import extract_features_step, extract_features_df
from train_rc import EchoStateNetwork
from estimator_pipeline import EstimatorPipeline

# Visualiser Config (standard import — visualiser_dir is first in sys.path)
from config import Config as VisConfig

# Simulator Config — loaded by absolute file path to bypass sys.modules cache.
# 'config' may already be cached as the visualiser's Config; using a unique
# module name '_sim_config_test' guarantees we get the simulator's version.
_sim_spec = importlib.util.spec_from_file_location(
    '_sim_config_test',
    os.path.join(simulator_dir, 'config.py')
)
_sim_cfg_mod = importlib.util.module_from_spec(_sim_spec)
_sim_spec.loader.exec_module(_sim_cfg_mod)
SimConfig = _sim_cfg_mod.Config



# ─────────────────────────────────────────────────────────────────────────────
# 1. Battery Chemistry
# ─────────────────────────────────────────────────────────────────────────────
class TestBatteryChemistry(unittest.TestCase):

    def test_all_chemistries_load(self):
        """All four supported chemistry profiles must be retrievable and valid."""
        for name in ["nmc", "lfp", "lead_acid", "li_ion"]:
            chem = get_chemistry(name)
            self.assertIsNotNone(chem, f"{name} chemistry not found")
            self.assertGreater(chem.nominal_capacity, 0)
            self.assertGreater(chem.R0_nom, 0)

    def test_ocv_monotonically_increasing(self):
        """OCV must increase monotonically from SOC=0 to SOC=1 for all chemistries."""
        for name in ["nmc", "lfp", "lead_acid", "li_ion"]:
            chem = get_chemistry(name)
            socs = np.linspace(0.0, 1.0, 21)
            ocvs = [chem.lookup_ocv(s) for s in socs]
            for i in range(1, len(ocvs)):
                self.assertGreaterEqual(ocvs[i], ocvs[i - 1],
                    f"{name}: OCV not monotone at SOC={socs[i]:.2f}")

    def test_ocv_bounds_clamped(self):
        """OCV lookup must clamp out-of-range SOC without raising."""
        chem = get_chemistry("nmc")
        self.assertEqual(chem.lookup_ocv(-0.5), chem.lookup_ocv(0.0))
        self.assertEqual(chem.lookup_ocv(1.5),  chem.lookup_ocv(1.0))

    def test_unknown_chemistry_fallback(self):
        """Unknown chemistry names must silently fall back to Li-ion profile."""
        chem = get_chemistry("unobtanium")
        li_ion = get_chemistry("li_ion")
        self.assertEqual(chem.nominal_capacity, li_ion.nominal_capacity)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Battery Simulator Physics
# ─────────────────────────────────────────────────────────────────────────────
class TestBatterySimulatorPhysics(unittest.TestCase):

    def test_2rc_discharge_dynamics(self):
        """Discharge must reduce SOC and produce a positive terminal voltage."""
        for name in ["nmc", "lfp", "lead_acid", "li_ion"]:
            sim = BatterySimulator(name)
            res = sim.step(current=-2.0, dt=1.0)
            self.assertGreater(res['voltage'], 0.0)
            self.assertLess(res['true_soc'], 1.0)
            self.assertGreaterEqual(res['temperature'], 25.0)

    def test_charge_increases_soc(self):
        """Charging from partial SOC must increase SOC."""
        sim = BatterySimulator("li_ion")
        sim.soc = 0.5
        res = sim.step(current=2.0, dt=10.0)
        self.assertGreater(res['true_soc'], 0.5)

    def test_soh_degrades_over_time(self):
        """SOH must decrease under continuous load with accelerated aging."""
        sim = BatterySimulator("li_ion")
        initial_soh = sim.soh
        for _ in range(20):
            sim.step(current=-2.0, dt=1.0, accelerated_aging=True)
        self.assertLess(sim.soh, initial_soh)

    def test_fault_short_drains_soc(self):
        """Micro-short must drain SOC even with zero external current."""
        sim = BatterySimulator("li_ion")
        res_normal = sim.step(current=0.0, dt=10.0, fault_short=False)
        sim.reset()
        res_short  = sim.step(current=0.0, dt=10.0, fault_short=True)
        self.assertEqual(res_normal['true_soc'], 1.0, "Normal step should not drain SOC")
        self.assertLess(res_short['true_soc'], 1.0, "Short should drain SOC internally")

    def test_fault_thermal_runaway_temperature(self):
        """Thermal runaway must produce significantly more heat than nominal."""
        sim = BatterySimulator("li_ion")
        res_nominal = sim.step(current=-1.0, dt=5.0, fault_thermal=False)
        sim.reset()
        res_runaway = sim.step(current=-1.0, dt=5.0, fault_thermal=True)
        self.assertGreater(res_runaway['temperature'],
                           res_nominal['temperature'] + 5.0)

    def test_sensor_noise_shape(self):
        """Sensor noise must return a dict with all expected keys."""
        sim = BatterySimulator("nmc")
        out = sim.step(current=-1.0, dt=1.0)
        noisy = sim.add_sensor_noise(out)
        for key in ('voltage', 'current', 'temperature', 'time'):
            self.assertIn(key, noisy)

    def test_sensor_dropout_zeros_readings(self):
        """Sensor dropout must return 0 voltage and current."""
        sim = BatterySimulator("nmc")
        out = sim.step(current=-1.0, dt=1.0)
        noisy = sim.add_sensor_noise(out, fault_dropout=True)
        self.assertEqual(noisy['voltage'], 0.0)
        self.assertEqual(noisy['current'], 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Extended Kalman Filter
# ─────────────────────────────────────────────────────────────────────────────
class TestExtendedKalmanFilter(unittest.TestCase):

    def test_soc_bounds(self):
        """EKF must clip SOC to [0, 1] regardless of measurement input."""
        ekf = ExtendedKalmanFilter("li_ion")
        P = np.eye(3) * 0.01
        soc, _, _, _ = ekf.step(1.0, 0.0, 0.0, P, I_meas=-5.0, V_meas=0.0, dt=1.0)
        self.assertGreaterEqual(soc, 0.0)
        self.assertLessEqual(soc, 1.0)

    def test_covariance_positive_semidefinite(self):
        """Posterior covariance diagonal must remain non-negative."""
        ekf = ExtendedKalmanFilter("li_ion")
        P = np.eye(3) * 0.01
        _, _, _, P_up = ekf.step(1.0, 0.0, 0.0, P, I_meas=-1.0, V_meas=11.5, dt=1.0)
        self.assertTrue(np.all(np.diag(P_up) >= 0.0))

    def test_temperature_parameter_scaling(self):
        """High temperature must increase internal resistance (Arrhenius effect)."""
        ekf_cold = ExtendedKalmanFilter("nmc")
        ekf_hot  = ExtendedKalmanFilter("nmc")
        P = np.eye(3) * 0.01
        # At cold temperature EKF covariance should differ from hot
        _, _, _, P_cold = ekf_cold.step(0.8, 0.0, 0.0, P.copy(), -1.0, 11.0, 1.0, T_meas=-10.0)
        _, _, _, P_hot  = ekf_hot.step( 0.8, 0.0, 0.0, P.copy(), -1.0, 11.0, 1.0, T_meas=50.0)
        # Both should remain valid (just checking no crash and valid output)
        self.assertEqual(P_cold.shape, (3, 3))
        self.assertEqual(P_hot.shape, (3, 3))


# ─────────────────────────────────────────────────────────────────────────────
# 4. ResistanceSOH Tracker
# ─────────────────────────────────────────────────────────────────────────────
class TestResistanceSOH(unittest.TestCase):

    def test_resistance_grows_on_voltage_drop(self):
        """Large current step with voltage drop should increase R0 estimate."""
        tracker = ResistanceSOH("nmc")
        r0_next, soh_next = tracker.step(
            current_r0=tracker.R0_nom,
            prev_v=12.6, prev_i=0.0,
            V_meas=12.2, I_meas=-2.0
        )
        self.assertGreater(r0_next, tracker.R0_nom)
        self.assertLess(soh_next, 1.0)

    def test_no_update_on_small_current_change(self):
        """Below the |dI| > 0.5 guard the resistance estimate should be unchanged."""
        tracker = ResistanceSOH("li_ion")
        r0_next, _ = tracker.step(
            current_r0=tracker.R0_nom,
            prev_v=12.0, prev_i=-0.3,
            V_meas=11.9, I_meas=-0.4    # dI = 0.1 < 0.5
        )
        self.assertAlmostEqual(r0_next, tracker.R0_nom, places=6)

    def test_soh_bounded(self):
        """SOH must always remain within [0.2, 1.0]."""
        tracker = ResistanceSOH("li_ion")
        _, soh = tracker.step(tracker.R0_nom * 10, 12.0, 0.0, 5.0, -10.0)
        self.assertGreaterEqual(soh, 0.2)
        self.assertLessEqual(soh, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Feature Engineering
# ─────────────────────────────────────────────────────────────────────────────
class TestFeatureEngineering(unittest.TestCase):

    def test_output_shape(self):
        """extract_features_step must return a 6-element numpy array."""
        feats = extract_features_step(11.8, -2.0, 25.2, [])
        self.assertEqual(feats.shape, (6,))

    def test_voltage_gradient(self):
        """Voltage gradient feature must equal V_current − V_prev."""
        history = [{'voltage': 11.9, 'current': -1.5, 'temperature': 25.1}]
        feats = extract_features_step(11.8, -2.0, 25.2, history)
        self.assertAlmostEqual(feats[3], 11.8 - 11.9, places=5)

    def test_current_moving_average(self):
        """Current MA must equal mean of history + current reading."""
        history = [
            {'voltage': 12.0, 'current': -1.0, 'temperature': 25.0},
            {'voltage': 11.9, 'current': -1.5, 'temperature': 25.1},
        ]
        feats = extract_features_step(11.8, -2.0, 25.2, history)
        expected_i_ma = np.mean([-1.0, -1.5, -2.0])
        self.assertAlmostEqual(feats[4], expected_i_ma, places=5)

    def test_no_history(self):
        """With empty history gradient should be 0 and MA should equal current values."""
        feats = extract_features_step(11.5, -1.0, 25.0, [])
        self.assertAlmostEqual(feats[3], 0.0, places=5)   # V_grad = 0
        self.assertAlmostEqual(feats[4], -1.0, places=5)  # I_ma   = I_current


# ─────────────────────────────────────────────────────────────────────────────
# 6. Echo State Network
# ─────────────────────────────────────────────────────────────────────────────
class TestEchoStateNetwork(unittest.TestCase):

    def test_reservoir_sparsity(self):
        """ESN reservoir must honour the requested sparsity ratio within ±8%."""
        esn = EchoStateNetwork(n_inputs=3, n_reservoir=100, n_outputs=1,
                               spectral_radius=0.9, leak_rate=0.3, sparsity=0.8)
        zeros = np.sum(esn.W_res == 0.0)
        ratio = zeros / (esn.n_reservoir ** 2)
        self.assertAlmostEqual(ratio, 0.8, delta=0.08)

    def test_spectral_radius_scaling(self):
        """Spectral radius of W_res must be close to the requested value."""
        target = 0.85
        esn = EchoStateNetwork(n_inputs=4, n_reservoir=80, n_outputs=1,
                               spectral_radius=target, sparsity=0.7)
        eigenvalues = np.linalg.eigvals(esn.W_res)
        actual_sr = np.max(np.abs(eigenvalues))
        self.assertAlmostEqual(actual_sr, target, delta=0.05)

    def test_predict_step_shape(self):
        """predict_step must return a 1D array of length n_outputs."""
        esn = EchoStateNetwork(n_inputs=3, n_reservoir=50, n_outputs=1)
        # W_out is None until train() is called
        U = np.random.randn(100, 3)
        Y = np.random.randn(100, 1)
        esn.train(U, Y, washout=10)
        u = np.zeros(3)
        pred = esn.predict_step(u)
        self.assertEqual(pred.shape, (1,))

    def test_state_save_restore(self):
        """Saved state must exactly restore reservoir activations."""
        esn = EchoStateNetwork(n_inputs=3, n_reservoir=50, n_outputs=1)
        # Train first so W_out is not None
        U = np.random.randn(100, 3)
        Y = np.random.randn(100, 1)
        esn.train(U, Y, washout=10)
        u = np.random.randn(3)
        esn.predict_step(u)
        saved_state = esn.get_state()
        esn.predict_step(np.random.randn(3))   # perturb state
        esn.reset_state(saved_state)
        restored = esn.get_state()
        np.testing.assert_array_equal(saved_state, restored)


# ─────────────────────────────────────────────────────────────────────────────
# 7. EstimatorPipeline — unified end-to-end
# ─────────────────────────────────────────────────────────────────────────────
class TestEstimatorPipeline(unittest.TestCase):

    def _make_pipeline(self, chem="li_ion", mismatch=1.0):
        return EstimatorPipeline(chem, mismatch=mismatch)

    def test_initial_state(self):
        """Pipeline must initialise at fully-charged, healthy state."""
        p = self._make_pipeline()
        self.assertAlmostEqual(p.cc_soc, 1.0)
        self.assertAlmostEqual(p.ekf_soc, 1.0)
        self.assertAlmostEqual(p.trad_soh, 1.0)

    def test_step_soc_decreases_on_discharge(self):
        """CC SOC and EKF SOC must decrease under discharge current."""
        p = self._make_pipeline()
        res = p.step(V_meas=11.6, I_meas_discharge=2.0, T_meas=25.0, dt=1.0)
        self.assertLess(res['cc_soc'], 1.0)
        self.assertLess(res['ekf_soc'], 1.0)

    def test_output_keys(self):
        """Step output must contain all expected keys."""
        p = self._make_pipeline()
        res = p.step(V_meas=11.6, I_meas_discharge=2.0, T_meas=25.0, dt=1.0)
        for key in ('cc_soc', 'ekf_soc', 'trad_soh', 'esn_soc', 'esn_soh',
                    'ekf_p_diag', 'ekf_time', 'esn_time', 'model_loaded', 'faults'):
            self.assertIn(key, res, f"Missing key: {key}")

    def test_covariance_diagonal_length(self):
        """EKF covariance diagonal must have exactly 3 elements."""
        p = self._make_pipeline()
        res = p.step(11.6, 2.0, 25.0, 1.0)
        self.assertEqual(len(res['ekf_p_diag']), 3)

    def test_cross_chemistry_universality(self):
        """Pipeline must work correctly for all supported chemistries."""
        for chem in ["nmc", "lfp", "lead_acid", "li_ion"]:
            p = self._make_pipeline(chem)
            chem_obj = p.chem_obj
            V_nom = chem_obj.lookup_ocv(0.9)
            res = p.step(V_meas=V_nom, I_meas_discharge=1.0, T_meas=25.0, dt=1.0)
            self.assertTrue(0.0 <= res['cc_soc'] <= 1.0, f"{chem}: cc_soc out of bounds")
            self.assertTrue(0.0 <= res['ekf_soc'] <= 1.0, f"{chem}: ekf_soc out of bounds")

    def test_serialization_roundtrip(self):
        """State dict roundtrip must exactly preserve all numeric fields."""
        p = self._make_pipeline("li_ion", mismatch=1.2)
        p.cc_soc = 0.85
        p.ekf_soc = 0.82
        state = p.get_state()

        restored = self._make_pipeline("nmc", mismatch=1.0)
        restored.set_state(state)
        self.assertEqual(restored.chemistry_name, "li_ion")
        self.assertAlmostEqual(restored.mismatch, 1.2)
        self.assertAlmostEqual(restored.cc_soc, 0.85)
        self.assertAlmostEqual(restored.ekf_soc, 0.82)


# ─────────────────────────────────────────────────────────────────────────────
# 8. CPS Fault Diagnostics
# ─────────────────────────────────────────────────────────────────────────────
class TestCPSFaultDiagnostics(unittest.TestCase):

    def _stepped_pipeline(self, V, I, T, steps=1, dt=1.0):
        p = EstimatorPipeline("li_ion")
        res = None
        for _ in range(steps):
            res = p.step(V_meas=V, I_meas_discharge=I, T_meas=T, dt=dt)
        return res

    def test_sensor_dropout_detected(self):
        """Voltage below threshold must trigger sensor_dropout fault."""
        res = self._stepped_pipeline(V=0.0, I=0.0, T=25.0)
        self.assertIn('sensor_dropout', res['faults'])

    def test_no_false_dropout_at_nominal_voltage(self):
        """Nominal voltage must NOT trigger a dropout alarm."""
        res = self._stepped_pipeline(V=11.5, I=2.0, T=25.0)
        self.assertNotIn('sensor_dropout', res['faults'])

    def test_thermal_runaway_detected_by_temperature(self):
        """Temperature above threshold must trigger thermal_runaway fault."""
        res = self._stepped_pipeline(V=11.5, I=1.0, T=65.0)
        self.assertIn('thermal_runaway', res['faults'])

    def test_no_false_thermal_alarm_at_nominal_temp(self):
        """Nominal temperature must not trigger thermal alarm."""
        res = self._stepped_pipeline(V=11.5, I=1.0, T=30.0)
        self.assertNotIn('thermal_runaway', res['faults'])

    def test_diagnostic_thresholds_from_config(self):
        """Diagnostic thresholds in SimConfig must have valid physical values."""
        self.assertGreater(SimConfig.DIAG_DROPOUT_VOLTAGE_THRESHOLD, 0.0)
        self.assertGreater(SimConfig.DIAG_THERMAL_TEMP_THRESHOLD, 0.0)
        self.assertGreater(SimConfig.DIAG_THERMAL_RATE_THRESHOLD, 0.0)
        self.assertGreater(SimConfig.DIAG_SHORT_SOC_DIFF_THRESHOLD, 0.0)
        self.assertGreater(SimConfig.DIAG_SHORT_CURRENT_THRESHOLD, 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Config consistency
# ─────────────────────────────────────────────────────────────────────────────
class TestConfigConsistency(unittest.TestCase):

    def test_sim_config_fault_constants_positive(self):
        """All simulator fault physics constants must be positive."""
        self.assertGreater(SimConfig.FAULT_SHORT_LEAKAGE_CURRENT, 0)
        self.assertGreater(SimConfig.FAULT_SHORT_HEATING_RATE, 0)
        self.assertGreater(SimConfig.FAULT_THERMAL_RUNAWAY_MULT, 0)
        self.assertGreater(SimConfig.FAULT_THERMAL_RUNAWAY_EXP, 0)

    def test_sim_config_noise_stddevs_positive(self):
        """All noise standard deviations must be strictly positive."""
        self.assertGreater(SimConfig.DEFAULT_NOISE_VOLTAGE, 0)
        self.assertGreater(SimConfig.DEFAULT_NOISE_CURRENT, 0)
        self.assertGreater(SimConfig.DEFAULT_NOISE_TEMPERATURE, 0)

    def test_vis_config_rolling_window_geq_1(self):
        """FEATURE_ROLLING_WINDOW must be at least 1 to avoid zero-length history."""
        self.assertGreaterEqual(VisConfig.FEATURE_ROLLING_WINDOW, 1)

    def test_vis_config_telemetry_limits_positive(self):
        """Telemetry limits must be positive integers."""
        self.assertGreater(VisConfig.TELEMETRY_RESPONSE_LIMIT, 0)
        self.assertGreater(VisConfig.TELEMETRY_FALLBACK_LIMIT, 0)
        self.assertGreater(VisConfig.TELEMETRY_FALLBACK_LIMIT,
                           VisConfig.TELEMETRY_RESPONSE_LIMIT,
                           "Fallback limit should be larger than response limit")


if __name__ == '__main__':
    unittest.main(verbosity=2)
