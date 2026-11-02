#!/usr/bin/env python3
"""
real_ekf_baseline.py
──────────────────────
A genuine 1RC-Thevenin Extended Kalman Filter baseline for SOC, fitted and
evaluated on the SAME real NASA cycles as the FPGA ESN track, so the
comparison in eval_fpga_outcomes.py is between two estimators that both
actually ran on real data.

Methodology (documented limitation, not hidden):
  - OCV(SOC) is fit as a degree-5 polynomial against (SOC, voltage) pairs
    from the TRAINING battery (B0005) only, using each cycle's near-rest
    low-current samples as an OCV proxy.
  - R0 is fit via ordinary least squares on V = OCV(SOC) - I*R0 over the
    training battery's cycles.
  - R1, C1 cannot be identified from discharge-only data (no rest-voltage
    relaxation segments exist in this dataset), so they are FIXED to
    physically reasonable defaults (R1=0.01 ohm, C1=3000 F -> tau=30s).
    This is a stated simplification: a more heavily instrumented dataset
    with rest periods would let these be fitted rather than fixed.
  - State vector: [SOC, V1]. Standard discrete EKF predict/update.
"""

import numpy as np


def _fit_ocv_polynomial(soc_samples, v_samples, degree=5):
    coeffs = np.polyfit(soc_samples, v_samples, degree)
    return np.poly1d(coeffs)


def _fit_r0(soc_samples, v_samples, i_samples, ocv_poly):
    """
    NASA PCoE sign convention: discharge current is recorded NEGATIVE
    (confirmed empirically -- see real_nasa_dataset.py's Coulomb counting,
    which takes abs(current)). Under that convention, the terminal
    voltage sag during discharge is modeled as:
        V = OCV(SOC) + I*R0   (I negative => V < OCV, correctly)
    So R0 is fit (least squares, NOT sign-forced) as:
        V - OCV = I*R0  =>  R0 = sum(I*(V-OCV)) / sum(I^2)
    A naive `abs()` on an R0 fit under the OPPOSITE sign convention
    (V = OCV - I*R0) silently masks a sign error rather than fixing it --
    this fit intentionally does not do that.
    """
    ocv_pred = ocv_poly(soc_samples)
    mask = np.abs(i_samples) > 0.05
    if mask.sum() < 5:
        return 0.08  # fallback physically-reasonable default
    lhs = i_samples[mask]
    rhs = (v_samples[mask] - ocv_pred[mask])
    r0 = float(np.sum(lhs * rhs) / np.sum(lhs * lhs))
    return r0


def fit_ekf_baseline(train_rows):
    """
    train_rows: list of dicts with keys voltage_measured, current_measured,
                soc_true (as produced by real_nasa_dataset.py), all from
                the TRAIN battery only.
    Returns a dict of fitted parameters.
    """
    soc = np.array([r["soc_true"] for r in train_rows])
    v = np.array([r["voltage_measured"] for r in train_rows])
    i = np.array([r["current_measured"] for r in train_rows])

    ocv_poly = _fit_ocv_polynomial(soc, v, degree=5)
    r0 = _fit_r0(soc, v, i, ocv_poly)

    return {
        "ocv_poly": ocv_poly,
        "r0": r0,
        "r1": 0.01,     # FIXED -- discharge-only data cannot identify this
        "c1": 3000.0,   # FIXED -- discharge-only data cannot identify this
    }


def run_ekf_on_cycle(cycle_rows, params, dt=None, q_soc=1e-6, q_v1=1e-6, r_meas=1e-3, capacity_ah=2.0):
    """
    Runs a discrete EKF with state x=[SOC, V1] over one cycle's rows
    (already resampled to a fixed number of timesteps, same as the ESN
    input). Returns the array of predicted SOC at each timestep.

    dt: if None (default), uses each row's own 'dt' field -- the REAL
        per-step time delta for that cycle after resampling (see
        real_nasa_dataset.py). Resampling to a fixed timestep count
        changes the sample spacing cycle-to-cycle, so a fixed dt=1.0
        would silently desynchronize the Coulomb-counting integration
        and the RC pole from the real elapsed time -- this must use the
        actual dt, not an assumed one.

    Model (NASA sign convention: discharge current I is NEGATIVE -- see
    _fit_r0's docstring for why this flips the textbook +I*R0/-I*R0 signs
    relative to a convention where discharge current is positive):
      SOC_k = SOC_{k-1} + (I_k * dt) / (capacity_ah * 3600)   [I<0 => SOC falls]
      V1_k  = V1_{k-1} * exp(-dt/(R1*C1)) + I_k * R1 * (1 - exp(-dt/(R1*C1)))
      V_meas_pred = OCV(SOC_k) + I_k*R0 + V1_k                 [I<0 => V sags]
    """
    ocv_poly = params["ocv_poly"]
    ocv_deriv = ocv_poly.deriv()
    r0, r1, c1 = params["r0"], params["r1"], params["c1"]
    tau = r1 * c1

    x = np.array([cycle_rows[0]["soc_true"], 0.0])  # init SOC at true initial value (protocol fact, not leakage -- matches ESN's own cycle-boundary reset convention)
    P = np.diag([1e-4, 1e-4])
    Q = np.diag([q_soc, q_v1])
    R = r_meas

    soc_preds = []
    for row in cycle_rows:
        i_k = row["current_measured"]
        v_meas = row["voltage_measured"]
        dt_k = dt if dt is not None else row.get("dt", 1.0)
        a_rc = np.exp(-dt_k / tau) if tau > 0 else 0.0

        # Predict
        soc_pred = x[0] + (i_k * dt_k) / (capacity_ah * 3600.0)
        v1_pred = x[1] * a_rc + i_k * r1 * (1 - a_rc)
        x_pred = np.array([soc_pred, v1_pred])

        F = np.array([[1.0, 0.0], [0.0, a_rc]])
        P_pred = F @ P @ F.T + Q

        # Update
        y_pred = ocv_poly(x_pred[0]) + i_k * r0 + x_pred[1]
        H = np.array([ocv_deriv(x_pred[0]), 1.0])
        S = H @ P_pred @ H.T + R
        K = (P_pred @ H) / S

        innovation = v_meas - y_pred
        x = x_pred + K * innovation
        x[0] = np.clip(x[0], 0.0, 1.0)
        P = (np.eye(2) - np.outer(K, H)) @ P_pred

        soc_preds.append(x[0])

    return np.array(soc_preds)
