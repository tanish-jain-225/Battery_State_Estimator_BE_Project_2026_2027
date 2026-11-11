import math

import numpy as np
from battery_chemistry import get_chemistry

_TEMP_REF_INV = 1.0 / (25.0 + 273.15)


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

    def update_noise_params(self, q_soc=1e-7, q_v1=1e-6, q_v2=1e-6, r_meas=0.01):
        """Update noise parameters dynamically from the configuration sliders."""
        self.Q = np.diag([q_soc, q_v1, q_v2])
        self.R_meas = r_meas

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
        temp_effect = math.exp(1500.0 * (1.0 / (T_c + 273.15) - _TEMP_REF_INV))

        # Capacity derating at lower temperatures (drops to 66% at -20°C)
        temp_cap_factor = 1.0 - 0.0075 * (25.0 - T_c) if T_c < 25.0 else 1.0
        Cn_active = self.Cn_nom * soh_est * temp_cap_factor

        # Resistance growth based on SOH
        resistance_growth = 1.0 + (1.0 - soh_est) * 1.5

        R0 = rls_r0 if rls_r0 is not None else self.R0_nom * resistance_growth * temp_effect
        R1 = rls_r1 if rls_r1 is not None else self.R1_nom * temp_effect
        C1 = rls_c1 if rls_c1 is not None else self.C1_nom / temp_effect
        R2 = self.R2_nom * temp_effect
        C2 = self.C2_nom / temp_effect

        # 1. State Transition Matrices for 2RC
        tau1 = R1 * C1
        tau2 = R2 * C2

        a1 = math.exp(-dt / tau1) if tau1 > 0.0 else 0.0
        b1 = R1 * (1.0 - a1)

        a2 = math.exp(-dt / tau2) if tau2 > 0.0 else 0.0
        b2 = R2 * (1.0 - a2)

        # 2. Prediction Step
        soc_pred = soc + (I_meas * dt) / (Cn_active * 3600.0)
        if soc_pred < 0.0:
            soc_pred = 0.0
        elif soc_pred > 1.0:
            soc_pred = 1.0

        v1_pred = a1 * v1 + b1 * I_meas
        v2_pred = a2 * v2 + b2 * I_meas

        Q = self.Q
        # Unrolled F @ P @ F.T + Q where F = diag(1, a1, a2)
        p00 = float(P[0, 0]) + float(Q[0, 0])
        p01 = a1 * float(P[0, 1]) + float(Q[0, 1])
        p02 = a2 * float(P[0, 2]) + float(Q[0, 2])
        p10 = a1 * float(P[1, 0]) + float(Q[1, 0])
        p11 = a1 * a1 * float(P[1, 1]) + float(Q[1, 1])
        p12 = a1 * a2 * float(P[1, 2]) + float(Q[1, 2])
        p20 = a2 * float(P[2, 0]) + float(Q[2, 0])
        p21 = a2 * a1 * float(P[2, 1]) + float(Q[2, 1])
        p22 = a2 * a2 * float(P[2, 2]) + float(Q[2, 2])

        # 3. Measurement Prediction
        lookup_ocv = self.chemistry.lookup_ocv
        ocv = lookup_ocv(soc_pred)
        V_pred = ocv + I_meas * R0 + v1_pred + v2_pred

        # 4. Measurement Jacobian H = [dOCV/dSOC, 1, 1]
        eps = 0.001
        dOCV = (lookup_ocv(soc_pred + eps) - lookup_ocv(soc_pred - eps)) / (2.0 * eps)

        # 5. Innovation / Correction Step
        residual = V_meas - V_pred
        ph0 = p00 * dOCV + p01 + p02
        ph1 = p10 * dOCV + p11 + p12
        ph2 = p20 * dOCV + p21 + p22
        H_P_HT = dOCV * ph0 + ph1 + ph2

        # Dynamically adapt measurement noise covariance R_meas using Sage-Husa
        if self.adaptive_r:
            R_est = 0.95 * self.R_meas + 0.05 * (residual * residual - H_P_HT)
            if R_est < 0.0001:
                R_est = 0.0001
            elif R_est > 1.0:
                R_est = 1.0
            self.R_meas = float(R_est)

        R_meas = self.R_meas
        S = H_P_HT + R_meas
        k0 = ph0 / S
        k1 = ph1 / S
        k2 = ph2 / S

        soc_updated = soc_pred + k0 * residual
        if soc_updated < 0.0:
            soc_updated = 0.0
        elif soc_updated > 1.0:
            soc_updated = 1.0
        v1_updated = v1_pred + k1 * residual
        v2_updated = v2_pred + k2 * residual

        # Joseph stabilized form: P = (I-KH)*P_pred*(I-KH)^T + K*R*K^T
        m00, m01, m02 = 1.0 - k0 * dOCV, -k0, -k0
        m10, m11, m12 = -k1 * dOCV, 1.0 - k1, -k1
        m20, m21, m22 = -k2 * dOCV, -k2, 1.0 - k2

        mp00 = m00 * p00 + m01 * p10 + m02 * p20
        mp01 = m00 * p01 + m01 * p11 + m02 * p21
        mp02 = m00 * p02 + m01 * p12 + m02 * p22
        mp10 = m10 * p00 + m11 * p10 + m12 * p20
        mp11 = m10 * p01 + m11 * p11 + m12 * p21
        mp12 = m10 * p02 + m11 * p12 + m12 * p22
        mp20 = m20 * p00 + m21 * p10 + m22 * p20
        mp21 = m20 * p01 + m21 * p11 + m22 * p21
        mp22 = m20 * p02 + m21 * p12 + m22 * p22

        u00 = mp00 * m00 + mp01 * m01 + mp02 * m02 + k0 * k0 * R_meas
        u01 = mp00 * m10 + mp01 * m11 + mp02 * m12 + k0 * k1 * R_meas
        u02 = mp00 * m20 + mp01 * m21 + mp02 * m22 + k0 * k2 * R_meas
        u10 = mp10 * m00 + mp11 * m01 + mp12 * m02 + k1 * k0 * R_meas
        u11 = mp10 * m10 + mp11 * m11 + mp12 * m12 + k1 * k1 * R_meas
        u12 = mp10 * m20 + mp11 * m21 + mp12 * m22 + k1 * k2 * R_meas
        u20 = mp20 * m00 + mp21 * m01 + mp22 * m02 + k2 * k0 * R_meas
        u21 = mp20 * m10 + mp21 * m11 + mp22 * m12 + k2 * k1 * R_meas
        u22 = mp20 * m20 + mp21 * m21 + mp22 * m22 + k2 * k2 * R_meas

        # Trace guard and positive-definite check
        tr = u00 + u11 + u22
        if not (math.isfinite(tr) and 0.0 <= tr <= 10.0 and u00 >= 0.0 and u11 >= 0.0 and u22 >= 0.0
                and math.isfinite(u01) and math.isfinite(u02) and math.isfinite(u12)):
            P_updated = np.diag([0.01, 0.01, 0.01])
        else:
            P_updated = np.array([[u00, u01, u02], [u10, u11, u12], [u20, u21, u22]], dtype=np.float64)

        return float(soc_updated), float(v1_updated), float(v2_updated), P_updated

class UnscentedKalmanFilter:
    def __init__(self, chemistry_name="li_ion", mismatch=1.0, alpha=1e-3, beta=2.0, kappa=0.0):
        self.chemistry_name = chemistry_name
        self.chemistry = get_chemistry(chemistry_name)
        self.Cn_nom = self.chemistry.nominal_capacity
        self.R0_nom = self.chemistry.R0_nom * mismatch
        self.R1_nom = self.chemistry.R1_nom * mismatch
        self.C1_nom = self.chemistry.C1_nom * mismatch
        self.R2_nom = self.chemistry.R2_nom * mismatch
        self.C2_nom = self.chemistry.C2_nom * mismatch

        self.Q = np.diag([1e-7, 1e-6, 1e-6])
        self.R_meas = 0.01

        # Unscented Transform weights
        self.n = 3
        self.alpha = alpha
        self.beta = beta
        self.kappa = kappa

        self.lmbda = (self.alpha ** 2) * (self.n + self.kappa) - self.n
        self.gamma = np.sqrt(self.n + self.lmbda)

        # Weights for mean and covariance
        self.Wm = np.zeros(2 * self.n + 1)
        self.Wc = np.zeros(2 * self.n + 1)

        self.Wm[0] = self.lmbda / (self.n + self.lmbda)
        self.Wc[0] = self.lmbda / (self.n + self.lmbda) + (1.0 - (self.alpha ** 2) + self.beta)

        for i in range(1, 2 * self.n + 1):
            self.Wm[i] = 1.0 / (2.0 * (self.n + self.lmbda))
            self.Wc[i] = 1.0 / (2.0 * (self.n + self.lmbda))

    def update_noise_params(self, q_soc=1e-7, q_v1=1e-6, q_v2=1e-6, r_meas=0.01):
        self.Q = np.diag([q_soc, q_v1, q_v2])
        self.R_meas = r_meas

    def _generate_sigma_points(self, x, P):
        try:
            P_sym = 0.5 * (P + P.T) + np.eye(self.n) * 1e-9
            L = np.linalg.cholesky(P_sym)
        except np.linalg.LinAlgError:
            L = np.diag(np.sqrt(np.maximum(1e-6, np.diag(P))))

        sigmas = np.zeros((self.n, 2 * self.n + 1))
        sigmas[:, 0] = x[:, 0]
        for i in range(self.n):
            sigmas[:, i + 1] = x[:, 0] + self.gamma * L[:, i]
            sigmas[:, i + 1 + self.n] = x[:, 0] - self.gamma * L[:, i]
        return sigmas

    def step(self, soc, v1, v2, P, I_meas, V_meas, dt, T_meas=25.0, soh_est=1.0, rls_r0=None, rls_r1=None, rls_c1=None):
        T_c = max(-20.0, min(60.0, T_meas))
        temp_effect = math.exp(1500.0 * (1.0 / (T_c + 273.15) - _TEMP_REF_INV))
        temp_cap_factor = 1.0 - 0.0075 * (25.0 - T_c) if T_c < 25.0 else 1.0
        Cn_active = self.Cn_nom * soh_est * temp_cap_factor
        resistance_growth = 1.0 + (1.0 - soh_est) * 1.5

        R0 = rls_r0 if rls_r0 is not None else self.R0_nom * resistance_growth * temp_effect
        R1 = rls_r1 if rls_r1 is not None else self.R1_nom * temp_effect
        C1 = rls_c1 if rls_c1 is not None else self.C1_nom / temp_effect
        R2 = self.R2_nom * temp_effect
        C2 = self.C2_nom / temp_effect

        tau1 = R1 * C1
        tau2 = R2 * C2
        a1 = math.exp(-dt / tau1) if tau1 > 0.0 else 0.0
        b1 = R1 * (1.0 - a1)
        a2 = math.exp(-dt / tau2) if tau2 > 0.0 else 0.0
        b2 = R2 * (1.0 - a2)

        x = np.array([[soc], [v1], [v2]])
        sigmas = self._generate_sigma_points(x, P)

        # 1. Vectorized State Prediction across all 2n+1 sigma points
        sigmas_pred = np.empty_like(sigmas)
        sigmas_pred[0] = np.clip(sigmas[0] + (I_meas * dt) / (Cn_active * 3600.0), 0.0, 1.0)
        sigmas_pred[1] = a1 * sigmas[1] + b1 * I_meas
        sigmas_pred[2] = a2 * sigmas[2] + b2 * I_meas

        x_pred_1d = sigmas_pred @ self.Wm
        diff_x = sigmas_pred - x_pred_1d[:, None]
        P_pred = self.Q + (diff_x * self.Wc) @ diff_x.T

        # 2. Vectorized Measurement Prediction
        ocv_vec = self.chemistry.lookup_ocv(sigmas_pred[0])
        Z_sigmas = ocv_vec + (I_meas * R0) + sigmas_pred[1] + sigmas_pred[2]
        z_pred = float(np.dot(self.Wm, Z_sigmas))

        diff_z = Z_sigmas - z_pred
        P_zz = float(self.R_meas + np.dot(self.Wc, diff_z * diff_z))
        P_xz_1d = (diff_x * self.Wc) @ diff_z

        # 3. State & Covariance Update
        K_1d = P_xz_1d / max(P_zz, 1e-9)
        residual = V_meas - z_pred
        x_updated_1d = x_pred_1d + K_1d * residual

        soc_updated = float(max(0.0, min(1.0, x_updated_1d[0])))
        v1_updated = float(x_updated_1d[1])
        v2_updated = float(x_updated_1d[2])

        P_updated = P_pred - np.outer(K_1d, K_1d) * P_zz

        if np.trace(P_updated) > 10.0 or np.any(np.diag(P_updated) < 0) or np.any(np.isnan(P_updated)) or np.any(np.isinf(P_updated)):
            P_updated = np.diag([0.01, 0.01, 0.01])

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
        temp_effect = math.exp(1500.0 * (1.0 / (T_c + 273.15) - _TEMP_REF_INV))

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

        # 2. Static resistance observer (fallback when current is stable, active load exists and state has converged)
        if not updated and abs(I_meas) > 0.2 and elapsed_time > 30.0:
            ocv = self.chemistry.lookup_ocv(soc_est)
            r0_static = abs(ocv + v1 + v2 - V_meas) / abs(I_meas)
            r0_static_comp = r0_static / temp_effect
            if 0.3 * self.R0_nom < r0_static_comp < 5.0 * self.R0_nom:
                # Use slower filter coefficient for static observer to absorb measurement noise
                r0_est = (1.0 - 0.2 * self.alpha) * current_r0 + (0.2 * self.alpha) * r0_static_comp

        # Invert the resistance growth formula: R = R0_nom * (1 + 1.5 * (1 - SOH))
        soh_est = 1.0 - ((r0_est / self.R0_nom) - 1.0) / 1.5
        soh_est = max(0.2, min(1.0, soh_est))

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

        # Guard against covariance windup by skipping parameter updates during low current (idle battery)
        if abs(I_meas_ekf) < 0.1:
            self.prev_y = y
            self.prev_i = I_meas_ekf
            return self.r0, self.r1, self.c1, self.converged

        # Regressor vector phi(k) = [-y(k-1), I(k), I(k-1)]^T
        phi = np.array([[-self.prev_y], [I_meas_ekf], [self.prev_i]])

        # Error prediction: e(k) = y(k) - theta^T * phi(k)
        y_pred = np.dot(self.theta.T, phi).item()
        e = y - y_pred

        # Variable Forgetting Factor update (VFF-RLS)
        # Adapt lambda dynamically based on prediction error to speed up tracking during transitions
        lmbda_min = 0.95
        gamma = 10.0  # Sensitivity factor
        lmbda = lmbda_min + (1.0 - lmbda_min) * math.exp(-gamma * (e * e))
        self.lmbda = 0.95 if lmbda < 0.95 else (0.999 if lmbda > 0.999 else lmbda)

        # Gain vector K(k) = P * phi / (lambda + phi^T * P * phi)
        P_phi = np.dot(self.P, phi)
        denom = self.lmbda + float(np.dot(phi.T, P_phi).item())
        K = P_phi / max(denom, 1e-6)

        # Parameter update: theta = theta + K * e
        self.theta += K * e

        # Covariance update: P = (P - K * phi^T * P) / lambda
        self.P = (self.P - np.dot(K, np.dot(phi.T, self.P))) / self.lmbda

        # Guard covariance from exploding or losing symmetry
        tr_p = float(self.P[0, 0] + self.P[1, 1] + self.P[2, 2])
        if not (math.isfinite(tr_p) and tr_p <= 100.0):
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
            tau = -self.dt / math.log(-theta1)
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
