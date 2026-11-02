#!/usr/bin/env python3
"""Floating-point UKF reference for the same 1-RC Thevenin model as the EKF.

Additive-noise UKF. The process model is linear, so the time update is the
exact linear one (identical to the EKF's). Sigma points are then drawn from
(x_pred, P_pred) for the measurement update (the standard additive-noise form
that re-draws sigma points after adding Q).

Sigma-point set: Julier's original choice kappa = 3 - n (n = 2 -> kappa = 1):
    gamma = sqrt(n + kappa) = sqrt(3),  W0 = kappa/(n+kappa) = 1/3,  Wi = 1/6
(same weights for mean and covariance). All weights are positive, which also
keeps every weight inside the Q2.30 range used by the fixed-point version.
"""
import numpy as np

N, KAPPA = 2, 1.0
GAMMA = np.sqrt(N + KAPPA)
W0, WI = KAPPA / (N + KAPPA), 1.0 / (2 * (N + KAPPA))
W = np.array([W0, WI, WI, WI, WI])


def run_ukf_on_cycle(cycle_rows, params, q_soc=1e-6, q_v1=1e-6, r_meas=1e-3, capacity_ah=2.0, p0=1e-4):
    ocv = params["ocv_poly"]
    r0, r1, c1 = params["r0"], params["r1"], params["c1"]
    tau = r1 * c1
    x = np.array([cycle_rows[0]["soc_true"], 0.0])
    P = np.diag([p0, p0])
    Q = np.diag([q_soc, q_v1])
    out = []
    for row in cycle_rows:
        i_k, v_meas, dt = row["current_measured"], row["voltage_measured"], row["dt"]
        a = np.exp(-dt / tau)
        F = np.array([[1.0, 0.0], [0.0, a]])
        xp = np.array([x[0] + i_k * dt / (capacity_ah * 3600.0), x[1] * a + i_k * r1 * (1 - a)])
        Pp = F @ P @ F.T + Q
        L = np.linalg.cholesky(Pp)
        X = np.column_stack([xp, xp + GAMMA * L[:, 0], xp + GAMMA * L[:, 1],
                             xp - GAMMA * L[:, 0], xp - GAMMA * L[:, 1]])
        Y = ocv(X[0]) + i_k * r0 + X[1]
        yh = W @ Y
        dY = Y - yh
        dX = X - xp[:, None]
        Pyy = W @ (dY * dY) + r_meas
        Pxy = (dX * dY) @ W
        K = Pxy / Pyy
        x = xp + K * (v_meas - yh)
        x[0] = np.clip(x[0], 0.0, 1.0)
        P = Pp - np.outer(K, Pxy)
        out.append(x[0])
    return np.array(out)
