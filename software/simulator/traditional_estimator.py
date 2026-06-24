import numpy as np

try:
    from battery_chemistry import get_chemistry
except ImportError:
    from simulator.battery_chemistry import get_chemistry

class ExtendedKalmanFilter:
    def __init__(self, chemistry_name="li_ion", mismatch=1.0, adaptive_r=True):
        self.chemistry_name = chemistry_name
        self.chemistry = get_chemistry(chemistry_name)
        self.adaptive_r = adaptive_r
        
        # Load nominal parameters from chemistry scaled by mismatch factor
        self.Cn_nom = self.chemistry.nominal_capacity  # Ah
        self.R0_nom = self.chemistry.R0_nom * mismatch  # Ohms
        self.R1_nom = self.chemistry.R1_nom * mismatch  # Ohms
        self.C1_nom = self.chemistry.C1_nom * mismatch  # Farads
        self.R2_nom = self.chemistry.R2_nom * mismatch  # Ohms
        self.C2_nom = self.chemistry.C2_nom * mismatch  # Farads

        # Keep for backward compatibility if accessed directly
        self.Cn = self.Cn_nom
        self.R0 = self.R0_nom
        self.R1 = self.R1_nom
        self.C1 = self.C1_nom
        self.R2 = self.R2_nom
        self.C2 = self.C2_nom

        # Process noise covariance Q (states: SOC, V1, V2)
        self.Q = np.diag([1e-7, 1e-6, 1e-6])
        
        # Measurement noise covariance R (will adapt dynamically if adaptive_r is True)
        self.R_meas = 0.01
        
    def step(self, soc, v1, v2, P, I_meas, V_meas, dt, T_meas=25.0, soh_est=1.0, rls_r0=None, rls_r1=None, rls_c1=None):
        """
        Runs one prediction-correction 2RC EKF step, with adaptive noise adjustment and RLS parameter injection.
        Note: Current I_meas is positive for charge, negative for discharge.
        :param P: 3x3 numpy covariance matrix
        :param T_meas: Measured cell temperature (°C)
        :param soh_est: Estimated State of Health (0.0 to 1.0)
        :param rls_r0: Optional dynamically identified internal resistance (RLS)
        :param rls_r1: Optional dynamically identified transient resistance (RLS)
        :param rls_c1: Optional dynamically identified transient capacitance (RLS)
        :returns: updated (soc, v1, v2, P_updated_3x3)
        """
        # Dynamic parameter updates based on Temperature and SOH
        T_c = max(-20.0, min(60.0, T_meas))
        temp_kelvin = T_c + 273.15
        temp_ref_kelvin = 25.0 + 273.15
        
        # Arrhenius temperature dependence
        temp_effect = np.exp(1500.0 * (1.0 / temp_kelvin - 1.0 / temp_ref_kelvin))
        
        # Capacity derating at lower temperatures (drops to 66% at -20°C)
        temp_cap_factor = 1.0 - 0.0075 * (25.0 - T_c) if T_c < 25.0 else 1.0
        Cn_active = self.Cn_nom * soh_est * temp_cap_factor
        
        # Resistance growth based on SOH
        resistance_growth = 1.0 + (1.0 - soh_est) * 1.5
        
        # Compute active parameter values (favoring dynamically identified parameters when available)
        if rls_r0 is not None:
            R0 = rls_r0
        else:
            R0 = self.R0_nom * resistance_growth * temp_effect
            
        if rls_r1 is not None:
            R1 = rls_r1
        else:
            R1 = self.R1_nom * temp_effect
            
        if rls_c1 is not None:
            C1 = rls_c1
        else:
            C1 = self.C1_nom / temp_effect
            
        R2 = self.R2_nom * temp_effect
        C2 = self.C2_nom / temp_effect

        x = np.array([[soc], [v1], [v2]])

        # 1. State Transition Matrices for 2RC
        tau1 = R1 * C1
        tau2 = R2 * C2
        
        a1 = np.exp(-dt / tau1) if tau1 > 0 else 0.0
        b1 = R1 * (1.0 - a1)
        
        a2 = np.exp(-dt / tau2) if tau2 > 0 else 0.0
        b2 = R2 * (1.0 - a2)
        
        F = np.array([[1.0, 0.0, 0.0],
                      [0.0, a1, 0.0],
                      [0.0, 0.0, a2]])
        
        # 2. Prediction Step
        # SOC prediction (Coulomb Counting using Cn_active)
        soc_pred = soc + (I_meas * dt) / (Cn_active * 3600.0)
        soc_pred = np.clip(soc_pred, 0.0, 1.0)
        
        # Polarization voltages predictions
        v1_pred = a1 * v1 + b1 * I_meas
        v2_pred = a2 * v2 + b2 * I_meas
        
        x_pred = np.array([[soc_pred], [v1_pred], [v2_pred]])
        P_pred = np.dot(np.dot(F, P), F.T) + self.Q
        
        # 3. Measurement Prediction
        ocv = self.chemistry.lookup_ocv(soc_pred)
        # Predicted terminal voltage: Vt = OCV(SOC) + I * R0 + V1 + V2
        V_pred = ocv + I_meas * R0 + v1_pred + v2_pred
        
        # 4. Measurement Jacobian H = [dOCV/dSOC, 1, 1]
        eps = 0.001
        ocv_plus = self.chemistry.lookup_ocv(soc_pred + eps)
        ocv_minus = self.chemistry.lookup_ocv(soc_pred - eps)
        dOCV = (ocv_plus - ocv_minus) / (2.0 * eps)
        
        H = np.array([[dOCV, 1.0, 1.0]])
        
        # 5. Innovation / Correction Step
        residual = V_meas - V_pred
        
        # Dynamically adapt measurement noise covariance R_meas using innovation sequence (Sage-Husa)
        if self.adaptive_r:
            H_P_HT = float(np.dot(np.dot(H, P_pred), H.T))
            # Sage-Husa adaptation update with learning factor alpha = 0.95
            R_est = 0.95 * self.R_meas + 0.05 * (residual**2 - H_P_HT)
            self.R_meas = float(np.clip(R_est, 0.0001, 1.0))
            
        S = np.dot(np.dot(H, P_pred), H.T) + self.R_meas
        K = np.dot(P_pred, H.T) / S[0, 0]
        
        x_updated = x_pred + K * residual
        soc_updated = float(np.clip(x_updated[0, 0], 0.0, 1.0))
        v1_updated = float(x_updated[1, 0])
        v2_updated = float(x_updated[2, 0])
        
        I_mat = np.eye(3)
        P_updated = np.dot((I_mat - np.dot(K, H)), P_pred)
        
        return soc_updated, v1_updated, v2_updated, P_updated

class ResistanceSOH:
    def __init__(self, chemistry_name="li_ion", alpha=0.02):
        self.chemistry_name = chemistry_name
        self.chemistry = get_chemistry(chemistry_name)
        self.R0_nom = self.chemistry.R0_nom
        self.alpha = alpha  # low-pass filter coefficient
        
    def step(self, current_r0, prev_v, prev_i, V_meas, I_meas, soc_est=1.0, v1=0.0, v2=0.0, T_meas=25.0, elapsed_time=0.0):
        """
        Estimates SOH based on dynamic transient and static internal resistance calculations.
        Returns: updated (current_r0, soh_estimate)
        """
        # Calculate temperature effect using Arrhenius equation
        T_c = max(-20.0, min(60.0, T_meas))
        temp_kelvin = T_c + 273.15
        temp_ref_kelvin = 25.0 + 273.15
        temp_effect = np.exp(1500.0 * (1.0 / temp_kelvin - 1.0 / temp_ref_kelvin))
        
        dI = I_meas - prev_i
        dV = V_meas - prev_v
        
        r0_est = current_r0
        updated = False
        
        # 1. Dynamic transient resistance calculation (requires step current change)
        if abs(dI) > 0.2:
            r0_calc = abs(dV) / abs(dI)
            r0_calc_comp = r0_calc / temp_effect
            if 0.3 * self.R0_nom < r0_calc_comp < 5.0 * self.R0_nom:
                r0_est = (1.0 - self.alpha) * current_r0 + self.alpha * r0_calc_comp
                updated = True
                
        # 2. Static resistance observer (fallback when current is stable, active load exists, and state has converged)
        if not updated and abs(I_meas) > 0.2 and elapsed_time > 30.0:
            ocv = self.chemistry.lookup_ocv(soc_est)
            r0_static = abs(ocv + v1 + v2 - V_meas) / abs(I_meas)
            r0_static_comp = r0_static / temp_effect
            if 0.3 * self.R0_nom < r0_static_comp < 5.0 * self.R0_nom:
                # Use slower filter coefficient for static observer to absorb measurement noise
                r0_est = (1.0 - 0.2 * self.alpha) * current_r0 + (0.2 * self.alpha) * r0_static_comp
                
        # Invert the resistance growth formula: R = R0_nom * (1 + 1.5 * (1 - SOH))
        soh_est = 1.0 - ((r0_est / self.R0_nom) - 1.0) / 1.5
        soh_est = np.clip(soh_est, 0.2, 1.0)
        
        return float(r0_est), float(soh_est)

class RecursiveLeastSquares:
    def __init__(self, dt=1.0, lmbda=0.995):
        """
        Recursive Least Squares (RLS) parameter identification for 1RC ECM.
        :param dt: Telemetry time step (s)
        :param lmbda: Forgetting factor (0.95 to 0.999)
        """
        self.dt = dt
        self.lmbda = lmbda
        
        # Parameter vector theta = [a1, b0, b1]^T
        # Initialize to nominal Li-ion matching weights
        self.theta = np.array([[-0.99], [0.075], [0.010]])
        
        # Covariance matrix P (3x3)
        self.P = np.eye(3) * 10.0
        
        # History buffers for regression
        self.prev_y = None
        self.prev_i = None
        
        # Convergence metrics
        self.r0 = 0.075
        self.r1 = 0.045
        self.c1 = 1000.0
        self.converged = False
        self.steps = 0

    def step(self, V_meas, I_meas_ekf, ocv):
        """
        Updates RLS parameter estimation.
        :param V_meas: Measured cell terminal voltage (V)
        :param I_meas_ekf: Current matching EKF sign convention (positive = charge, negative = discharge)
        :param ocv: Estimated Open Circuit Voltage (V)
        """
        y = V_meas - ocv
        
        if self.prev_y is None or self.prev_i is None:
            self.prev_y = y
            self.prev_i = I_meas_ekf
            return self.r0, self.r1, self.c1, self.converged

        # Regressor vector phi(k) = [-y(k-1), I(k), I(k-1)]^T
        phi = np.array([[-self.prev_y], [I_meas_ekf], [self.prev_i]])
        
        # Error prediction: e(k) = y(k) - theta^T * phi(k)
        y_pred = float(np.dot(self.theta.T, phi))
        e = y - y_pred
        
        # Gain vector K(k) = P * phi / (lambda + phi^T * P * phi)
        P_phi = np.dot(self.P, phi)
        denom = self.lmbda + float(np.dot(phi.T, P_phi))
        K = P_phi / max(denom, 1e-6)
        
        # Parameter update: theta = theta + K * e
        self.theta += K * e
        
        # Covariance update: P = (P - K * phi^T * P) / lambda
        self.P = (self.P - np.dot(K, np.dot(phi.T, self.P))) / self.lmbda
        
        # Guard covariance from exploding or losing symmetry
        if np.any(np.isnan(self.P)) or np.any(np.isinf(self.P)):
            self.P = np.eye(3) * 10.0
            
        self.prev_y = y
        self.prev_i = I_meas_ekf
        self.steps += 1
        
        # Extract physical variables from theta = [theta1, theta2, theta3]^T = [a1, b0, b1]^T
        theta1 = float(self.theta[0, 0])
        theta2 = float(self.theta[1, 0])
        theta3 = float(self.theta[2, 0])
        
        # Physical constraints checking
        # 1. Pole must be stable: -1 < theta1 < 0
        if -0.9999 < theta1 < -0.01:
            tau = -self.dt / np.log(-theta1)
            r0 = theta2
            # b1 = r1 * (1 + a1) + r0 * a1
            # theta3 = r1 * (1 + theta1) + r0 * theta1
            # r1 = (theta3 - theta2 * theta1) / (1 + theta1)
            r1 = (theta3 - theta2 * theta1) / (1.0 + theta1)
            
            # Ensure physical parameter bounds are sane
            if 0.001 < r0 < 1.0 and 0.001 < r1 < 1.0:
                self.r0 = r0
                self.r1 = r1
                self.c1 = max(10.0, min(50000.0, tau / r1))
                if self.steps > 50:
                    self.converged = True
                    
        return self.r0, self.r1, self.c1, self.converged
