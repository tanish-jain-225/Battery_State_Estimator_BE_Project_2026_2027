"""EKF/UKF calibration used for every model pack (same as the research code's real_ekf_baseline.fit_ekf_baseline).

OCV(SOC): degree-5 polynomial fitted to (SOC, terminal voltage) of the calibration windows (a pseudo-OCV).
R0: least squares on V - OCV = I * R0 (NASA sign: discharge current negative).
R1, C1: fixed (10 mOhm, 3000 F); discharge-only windows contain no relaxation to identify them.
"""
import numpy as np


def fit_ekf_baseline(rows):
    """rows: dicts with soc_true, voltage_measured, current_measured. Returns ocv_poly, r0, r1, c1."""
    soc = np.array([r["soc_true"] for r in rows]); v = np.array([r["voltage_measured"] for r in rows])
    i = np.array([r["current_measured"] for r in rows])
    ocv = np.poly1d(np.polyfit(soc, v, 5))
    m = np.abs(i) > 0.05
    r0 = 0.08 if m.sum() < 5 else float(np.sum(i[m] * (v[m] - ocv(soc[m]))) / np.sum(i[m] * i[m]))
    return {"ocv_poly": ocv, "r0": r0, "r1": 0.01, "c1": 3000.0}
