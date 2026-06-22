import time
import numpy as np
import sys
import os
import importlib.util

# Load Config directly from this file's own directory by absolute path.
# This bypasses sys.modules name-collision: when tests run from the project root,
# 'config' may already be cached as the visualiser's Config (which lacks DIAG_*).
# Using a private module name '_simulator_config' guarantees we always get the
# simulator's Config regardless of sys.path or import order.
_this_dir = os.path.dirname(os.path.abspath(__file__))
_config_path = os.path.join(_this_dir, 'config.py')
_spec = importlib.util.spec_from_file_location('_simulator_config', _config_path)
_config_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_config_mod)
Config = _config_mod.Config

try:
    from traditional_estimator import ExtendedKalmanFilter, ResistanceSOH
    from battery_chemistry import get_chemistry
except ImportError:
    from simulator.traditional_estimator import ExtendedKalmanFilter, ResistanceSOH
    from simulator.battery_chemistry import get_chemistry

try:
    _this_dir = os.path.dirname(os.path.abspath(__file__))
    _paths_to_try = [
        os.path.join(os.path.dirname(_this_dir), 'visualiser', 'training'),
        os.path.join(os.path.dirname(os.path.dirname(_this_dir)), 'visualiser', 'training'),
        os.path.join(os.path.dirname(_this_dir), 'training')
    ]
    for _p in _paths_to_try:
        if os.path.exists(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    from feature_engineering import extract_features_step
except ImportError:
    # Fallback feature engineering logic
    def extract_features_step(V_current, I_current, T_current, history, rolling_window=5):
        lookback = rolling_window - 1
        if len(history) == 0:
            V_prev = V_current
            V_history = [V_current]
            I_history = [I_current]
            T_history = [T_current]
        else:
            V_prev = history[-1]['voltage']
            V_history = [r['voltage'] for r in history[-lookback:]] + [V_current]
            I_history = [r['current'] for r in history[-lookback:]] + [I_current]
            T_history = [r['temperature'] for r in history[-lookback:]] + [T_current]
        V_grad = V_current - V_prev
        I_ma = np.mean(I_history)
        T_ma = np.mean(T_history)
        return np.array([V_current, I_current, T_current, V_grad, I_ma, T_ma])

class EstimatorPipeline:
    def __init__(self, chemistry_name="li_ion", mismatch=1.0, esn_soc=None, esn_soh=None, input_means=None, input_stds=None):
        self.chemistry_name = chemistry_name
        self.mismatch = mismatch
        self.esn_soc = esn_soc
        self.esn_soh = esn_soh
        self.input_means = input_means
        self.input_stds = input_stds
        
        self.chem_obj = get_chemistry(chemistry_name)
        self.ekf = ExtendedKalmanFilter(chemistry_name, mismatch=mismatch)
        self.soh_tracker = ResistanceSOH(chemistry_name)
        
        # Reset internal states
        self.reset()

    def reset(self):
        self.cc_soc = 1.0
        self.ekf_soc = 1.0
        self.ekf_v1 = 0.0
        self.ekf_v2 = 0.0
        self.ekf_p = np.array([[0.01, 0.0, 0.0], [0.0, 0.01, 0.0], [0.0, 0.0, 0.01]])
        
        self.trad_r0 = self.chem_obj.R0_nom
        self.trad_soh = 1.0
        self.elapsed_time = 0.0
        
        self.prev_voltage = self.chem_obj.lookup_ocv(1.0)
        self.prev_current = 0.0
        
        self.rolling_history = []
        self.esn_soc_state = None
        self.esn_soh_state = None
        self.primed = False
        
        if self.esn_soc is not None:
            self.esn_soc_state = [0.0] * self.esn_soc.n_reservoir
        if self.esn_soh is not None:
            self.esn_soh_state = [0.0] * self.esn_soh.n_reservoir

    def load_model(self, esn_soc, esn_soh, input_means, input_stds):
        """Load or update ESN model weights"""
        self.esn_soc = esn_soc
        self.esn_soh = esn_soh
        self.input_means = input_means
        self.input_stds = input_stds
        
        if self.esn_soc is not None and self.esn_soc_state is None:
            self.esn_soc_state = [0.0] * self.esn_soc.n_reservoir
        if self.esn_soh is not None and self.esn_soh_state is None:
            self.esn_soh_state = [0.0] * self.esn_soh.n_reservoir

    def get_state(self):
        """Serialize current estimator state to a JSON-serializable dictionary"""
        return {
            'chemistry_name': self.chemistry_name,
            'mismatch': self.mismatch,
            'cc_soc': float(self.cc_soc),
            'ekf_soc': float(self.ekf_soc),
            'ekf_v1': float(self.ekf_v1),
            'ekf_v2': float(self.ekf_v2),
            'ekf_p': self.ekf_p.tolist() if isinstance(self.ekf_p, np.ndarray) else self.ekf_p,
            'trad_r0': float(self.trad_r0),
            'trad_soh': float(self.trad_soh),
            'prev_voltage': float(self.prev_voltage),
            'prev_current': float(self.prev_current),
            'rolling_history': self.rolling_history,
            'esn_soc_state': self.esn_soc_state,
            'esn_soh_state': self.esn_soh_state,
            'primed': bool(self.primed),
            'elapsed_time': float(self.elapsed_time)
        }

    def set_state(self, state_dict):
        """Restore estimator state from a dictionary"""
        if not state_dict:
            return
        
        self.chemistry_name = state_dict.get('chemistry_name', self.chemistry_name)
        self.mismatch = state_dict.get('mismatch', self.mismatch)
        self.chem_obj = get_chemistry(self.chemistry_name)
        self.ekf = ExtendedKalmanFilter(self.chemistry_name, mismatch=self.mismatch)
        self.soh_tracker = ResistanceSOH(self.chemistry_name)
        
        self.cc_soc = state_dict.get('cc_soc', 1.0)
        self.ekf_soc = state_dict.get('ekf_soc', 1.0)
        self.ekf_v1 = state_dict.get('ekf_v1', 0.0)
        self.ekf_v2 = state_dict.get('ekf_v2', 0.0)
        
        ekf_p_val = state_dict.get('ekf_p')
        if ekf_p_val is not None:
            self.ekf_p = np.array(ekf_p_val)
            
        self.trad_r0 = state_dict.get('trad_r0', self.chem_obj.R0_nom)
        self.trad_soh = state_dict.get('trad_soh', 1.0)
        self.elapsed_time = state_dict.get('elapsed_time', 0.0)
        
        self.prev_voltage = state_dict.get('prev_voltage', self.chem_obj.lookup_ocv(1.0))
        self.prev_current = state_dict.get('prev_current', 0.0)
        
        self.rolling_history = state_dict.get('rolling_history', [])
        self.esn_soc_state = state_dict.get('esn_soc_state')
        self.esn_soh_state = state_dict.get('esn_soh_state')
        self.primed = state_dict.get('primed', False)

    def prime_esn(self, V_initial, T_initial=25.0, priming_steps=50, selected_indices=None, dataset_dt=0.001, sim_dt=1.0):
        """Run ESN priming steps to populate reservoir memory from initial state"""
        if self.esn_soc is None or self.esn_soh is None or self.input_means is None or self.input_stds is None:
            return
        
        if selected_indices is None:
            selected_indices = [0, 1, 3, 4]  # V, I, dV/dt, I_MA

        # Map initial voltage to NMC equivalent range
        nmc_chem = get_chemistry('nmc')
        V_min_nmc = nmc_chem.lookup_ocv(0.0)
        V_max_nmc = nmc_chem.lookup_ocv(1.0)
        V_min_c = self.chem_obj.lookup_ocv(0.0)
        V_max_c = self.chem_obj.lookup_ocv(1.0)
        denom_v = V_max_c - V_min_c if V_max_c != V_min_c else 1.0
        V_init_equiv = V_min_nmc + (V_initial - V_min_c) * (V_max_nmc - V_min_nmc) / denom_v

        # Generate priming input: constant voltage, zero current, nominal temperature
        prime_history = []
        u_raw = extract_features_step(V_init_equiv, 0.0, T_initial, prime_history)
        
        # Normalize voltage gradient for sim_dt
        u_raw[3] = u_raw[3] * (dataset_dt / sim_dt)
        u_selected = u_raw[selected_indices]
        u_scaled = (u_selected - self.input_means) / self.input_stds
        
        self.esn_soc.reset_state()
        self.esn_soh.reset_state()
        
        for _ in range(priming_steps):
            self.esn_soc._update(u_scaled.reshape(-1, 1))
            self.esn_soh._update(u_scaled.reshape(-1, 1))
            
        self.esn_soc_state = self.esn_soc.get_state()
        self.esn_soh_state = self.esn_soh.get_state()
        self.primed = True

    def calculate_soe(self, soc):
        """
        Calculates State of Energy (SOE) using numerical integration of the OCV-SOC curve.
        """
        steps = 20
        if soc <= 0.0:
            return 0.0
        
        # Integral from 0 to soc
        s_vals = np.linspace(0.0, soc, steps + 1)
        ocv_vals = [self.chem_obj.lookup_ocv(s) for s in s_vals]
        integral_soc = np.trapz(ocv_vals, s_vals)
        
        # Integral from 0 to 1.0
        s_all = np.linspace(0.0, 1.0, steps + 1)
        ocv_all = [self.chem_obj.lookup_ocv(s) for s in s_all]
        integral_total = np.trapz(ocv_all, s_all)
        
        soe = integral_soc / max(integral_total, 1e-4)
        return float(np.clip(soe, 0.0, 1.0))

    def step(self, V_meas, I_meas_discharge, T_meas, dt, quantize_mode='float32', selected_indices=None, dataset_dt=0.001):
        """
        Execute one prediction-estimation step for all estimators.
        :param V_meas: Noisy voltage measurement (V)
        :param I_meas_discharge: Noisy current measurement (A, positive = discharge, negative = charge)
        :param T_meas: Noisy temperature measurement (°C)
        :param dt: Step interval (s)
        :param quantize_mode: Precision for ESN ('float32', 'int16', 'int8')
        :returns: dict of updated values and latencies
        """
        # EKF/Coulomb Counting expects positive current for charge, negative for discharge
        I_meas_ekf = -I_meas_discharge
        
        # 1. Cyber-Physical System (CPS) Fault Diagnostics FIRST
        faults_detected = []
        
        # Sensor Dropout Diagnostic
        if V_meas < Config.DIAG_DROPOUT_VOLTAGE_THRESHOLD:
            faults_detected.append('sensor_dropout')
            
        # Thermal Runaway Diagnostic
        dT_dt = 0.0
        if len(self.rolling_history) >= 1:
            prev_t_val = self.rolling_history[-1]['temperature']
            dT_dt = (T_meas - prev_t_val) / dt
            
        if T_meas > Config.DIAG_THERMAL_TEMP_THRESHOLD or dT_dt > Config.DIAG_THERMAL_RATE_THRESHOLD:
            faults_detected.append('thermal_runaway')
            
        # Internal Short-Circuit Diagnostic
        soc_diff = self.cc_soc - self.ekf_soc
        if soc_diff > Config.DIAG_SHORT_SOC_DIFF_THRESHOLD and abs(I_meas_discharge) <= Config.DIAG_SHORT_CURRENT_THRESHOLD:
            faults_detected.append('internal_short')
            
        # 2. Update physical/traditional estimators only if sensors are healthy
        ekf_time = 0.0
        if 'sensor_dropout' not in faults_detected:
            self.elapsed_time += dt
            
            # Update Coulomb Counting
            self.cc_soc = self.cc_soc + (I_meas_ekf * dt) / (self.chem_obj.nominal_capacity * 3600.0)
            self.cc_soc = max(0.0, min(1.0, self.cc_soc))
            
            # Update Resistance SOH FIRST so EKF can use the latest updated SOH
            self.trad_r0, self.trad_soh = self.soh_tracker.step(
                self.trad_r0, self.prev_voltage, self.prev_current, V_meas, I_meas_discharge,
                soc_est=self.ekf_soc, v1=self.ekf_v1, v2=self.ekf_v2, T_meas=T_meas, elapsed_time=self.elapsed_time
            )
            
            # Update EKF dynamically adjusting parameters with T_meas and SOH
            t_ekf_start = time.perf_counter()
            self.ekf_soc, self.ekf_v1, self.ekf_v2, self.ekf_p = self.ekf.step(
                self.ekf_soc, self.ekf_v1, self.ekf_v2, self.ekf_p,
                I_meas_ekf, V_meas, dt, T_meas=T_meas, soh_est=self.trad_soh
            )
            ekf_time = (time.perf_counter() - t_ekf_start) * 1000.0 # ms

        # Save previous readings
        if 'sensor_dropout' not in faults_detected:
            self.prev_voltage = V_meas
            self.prev_current = I_meas_discharge
        
        # 3. Update ESN
        esn_time = 0.0
        esn_soc_pred = 1.0
        esn_soh_pred = 1.0
        u_raw_selected_list = [0.0, 0.0, 0.0, 0.0]
        
        model_loaded = (self.esn_soc is not None and self.esn_soh is not None and 
                        self.input_means is not None and self.input_stds is not None)
        
        if 'sensor_dropout' in faults_detected:
            esn_soc_pred = self.ekf_soc
            esn_soh_pred = self.trad_soh
        elif model_loaded:
            # Map measured values to NMC equivalents for ESN
            nmc_chem = get_chemistry('nmc')
            V_min_nmc = nmc_chem.lookup_ocv(0.0)
            V_max_nmc = nmc_chem.lookup_ocv(1.0)
            V_min_c = self.chem_obj.lookup_ocv(0.0)
            V_max_c = self.chem_obj.lookup_ocv(1.0)
            denom_v = V_max_c - V_min_c if V_max_c != V_min_c else 1.0
            
            V_equiv = V_min_nmc + (V_meas - V_min_c) * (V_max_nmc - V_min_nmc) / denom_v
            I_equiv = I_meas_discharge * (nmc_chem.nominal_capacity / self.chem_obj.nominal_capacity)
            
            if not self.primed:
                # Lazy priming at first step
                self.prime_esn(V_meas, T_meas, sim_dt=dt, dataset_dt=dataset_dt)
                
            if selected_indices is None:
                selected_indices = [0, 1, 3, 4]
                
            t_esn_start = time.perf_counter()
            
            # Map rolling history for ESN feature extraction
            esn_history = []
            for r in self.rolling_history:
                r_v_equiv = V_min_nmc + (r['voltage'] - V_min_c) * (V_max_nmc - V_min_nmc) / denom_v
                r_i_equiv = r['current'] * (nmc_chem.nominal_capacity / self.chem_obj.nominal_capacity)
                esn_history.append({'voltage': r_v_equiv, 'current': r_i_equiv, 'temperature': r['temperature']})
            
            # Feature extraction
            u_raw = extract_features_step(V_equiv, I_equiv, T_meas, esn_history)
            u_raw[3] = u_raw[3] * (dataset_dt / dt)
            u_selected = u_raw[selected_indices]
            u_raw_selected_list = u_selected.tolist()
            
            u_scaled = (u_selected - self.input_means) / self.input_stds
            
            # Sync internal model state
            self.esn_soc.reset_state(self.esn_soc_state)
            self.esn_soh.reset_state(self.esn_soh_state)
            
            # Run prediction step
            pred_soc_val = self.esn_soc.predict_step(u_scaled, quantize_mode=quantize_mode)
            pred_soh_val = self.esn_soh.predict_step(u_scaled, quantize_mode=quantize_mode)
            
            # Save updated states
            self.esn_soc_state = self.esn_soc.get_state()
            self.esn_soh_state = self.esn_soh.get_state()
            
            esn_soc_pred = float(np.clip(pred_soc_val[0], 0.0, 1.0))
            # Hybridize SOH estimation: SOH decays slowly and cannot be captured purely by short-term ESN features
            # due to training time-step mismatch (0.001s in training vs 1s in simulator).
            # We use the EKF traditional tracker as the robust baseline.
            esn_soh_pred = 0.02 * float(np.clip(pred_soh_val[0], 0.0, 1.0)) + 0.98 * self.trad_soh
            
            # Update history queue
            self.rolling_history.append({'voltage': V_meas, 'current': I_meas_discharge, 'temperature': T_meas})
            if len(self.rolling_history) > Config.FEATURE_ROLLING_WINDOW - 1:
                self.rolling_history.pop(0)
                
            esn_time = (time.perf_counter() - t_esn_start) * 1000.0 # ms

        # 4. Advanced Battery Estimations (SOP, SOE, RUL)
        V_min = self.chem_obj.lookup_ocv(0.0)
        V_max = self.chem_obj.lookup_ocv(1.0)
        ocv = self.chem_obj.lookup_ocv(self.ekf_soc)
        
        # Safe current limits (Amps, positive values) based on terminal voltage limits (V_min, V_max)
        R0 = max(self.trad_r0, 1e-4)
        sop_charge_curr = float(max(0.0, (V_max - ocv - self.ekf_v1 - self.ekf_v2) / R0))
        sop_discharge_curr = float(max(0.0, (ocv + self.ekf_v1 + self.ekf_v2 - V_min) / R0))
        
        # State of Power (SOP) in Watts
        sop_charge_pwr = float(sop_charge_curr * V_max)
        sop_discharge_pwr = float(sop_discharge_curr * V_min)
        
        # State of Energy (SOE)
        ekf_soe = self.calculate_soe(self.ekf_soc)
        esn_soe = self.calculate_soe(esn_soc_pred)
        
        # Project total and remaining energy in Wh
        s_all = np.linspace(0.0, 1.0, 21)
        ocv_all = [self.chem_obj.lookup_ocv(s) for s in s_all]
        integral_total = np.trapz(ocv_all, s_all)
        energy_total_wh = self.chem_obj.nominal_capacity * self.trad_soh * integral_total
        energy_remaining_wh = float(max(0.0, energy_total_wh * ekf_soe))
        
        # Remaining Useful Life (RUL) in Cycles
        NOMINAL_CYCLE_LIFE = {
            'nmc': 1000,
            'lfp': 2000,
            'lead_acid': 400,
            'li_ion': 1000
        }
        clean_name = str(self.chemistry_name).lower().replace(" ", "_").replace("-", "_")
        nominal_cycles = NOMINAL_CYCLE_LIFE.get(clean_name, 1000)
        
        # Calculate remaining cycle life based on SOH (with 80% SOH as EOL threshold)
        ekf_rul_cycles = float(max(0.0, (self.trad_soh - 0.8) / 0.2 * nominal_cycles))
        esn_rul_cycles = float(max(0.0, (esn_soh_pred - 0.8) / 0.2 * nominal_cycles))

        # 5. Apply Cyber-Physical Safety Overrides
        if 'thermal_runaway' in faults_detected:
            self.trad_soh = 0.2
            esn_soh_pred = 0.2
            sop_charge_curr = 0.0
            sop_discharge_curr = 0.0
            sop_charge_pwr = 0.0
            sop_discharge_pwr = 0.0
            ekf_soe = 0.0
            esn_soe = 0.0
            energy_remaining_wh = 0.0
            ekf_rul_cycles = 0.0
            esn_rul_cycles = 0.0
        elif 'internal_short' in faults_detected:
            self.trad_soh = min(self.trad_soh, 0.5)
            esn_soh_pred = min(esn_soh_pred, 0.5)
            sop_charge_curr = min(sop_charge_curr, 5.0)
            sop_discharge_curr = min(sop_discharge_curr, 5.0)
            sop_charge_pwr = min(sop_charge_pwr, 20.0)
            sop_discharge_pwr = min(sop_discharge_pwr, 20.0)
            ekf_rul_cycles = min(ekf_rul_cycles, 50.0)
            esn_rul_cycles = min(esn_rul_cycles, 50.0)
        elif 'sensor_dropout' in faults_detected:
            self.trad_soh = 0.2
            esn_soh_pred = 0.2
            sop_charge_curr = 0.0
            sop_discharge_curr = 0.0
            sop_charge_pwr = 0.0
            sop_discharge_pwr = 0.0
            ekf_rul_cycles = 0.0
            esn_rul_cycles = 0.0
            
        return {
            'cc_soc': self.cc_soc,
            'ekf_soc': self.ekf_soc,
            'ekf_v1': self.ekf_v1,
            'ekf_v2': self.ekf_v2,
            'ekf_p_diag': [float(self.ekf_p[0, 0]), float(self.ekf_p[1, 1]), float(self.ekf_p[2, 2])],
            'trad_r0': self.trad_r0,
            'trad_soh': self.trad_soh,
            'esn_soc': esn_soc_pred,
            'esn_soh': esn_soh_pred,
            'esn_features': u_raw_selected_list,
            'ekf_time': ekf_time,
            'esn_time': esn_time,
            'model_loaded': model_loaded,
            'faults': faults_detected,
            'sop_charge_curr': sop_charge_curr,
            'sop_discharge_curr': sop_discharge_curr,
            'sop_charge_pwr': sop_charge_pwr,
            'sop_discharge_pwr': sop_discharge_pwr,
            'ekf_soe': ekf_soe,
            'esn_soe': esn_soe,
            'ekf_rul_cycles': ekf_rul_cycles,
            'esn_rul_cycles': esn_rul_cycles,
            'energy_remaining_wh': energy_remaining_wh
        }
