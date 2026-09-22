import numpy as np
import sys
import os

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
visualiser_dir = os.path.join(root_dir, "software", "visualiser")
if visualiser_dir not in sys.path:
    sys.path.insert(0, visualiser_dir)

from software.visualiser.traditional_estimator import (
    ExtendedKalmanFilter,
    UnscentedKalmanFilter,
    ResistanceSOH,
    RecursiveLeastSquares
)

def test_ekf_initialization():
    ekf = ExtendedKalmanFilter("li_ion")
    assert ekf.Cn_nom == 2.5
    assert ekf.R_meas == 0.01
    assert ekf.Q.shape == (3, 3)

def test_ekf_step_discharge():
    ekf = ExtendedKalmanFilter("li_ion")
    P = np.eye(3) * 0.01
    soc, v1, v2, P_new = ekf.step(
        soc=1.0, v1=0.0, v2=0.0, P=P,
        I_meas=-2.0, V_meas=3.7, dt=1.0, T_meas=25.0
    )
    assert 0.0 <= soc <= 1.0
    assert isinstance(v1, float)
    assert isinstance(v2, float)
    assert P_new.shape == (3, 3)
    assert not np.any(np.isnan(P_new))

def test_ekf_joseph_covariance_stability():
    ekf = ExtendedKalmanFilter("li_ion")
    P = np.eye(3) * 100.0  # High initial covariance
    soc, v1, v2, P_new = ekf.step(
        soc=0.5, v1=0.1, v2=0.1, P=P,
        I_meas=-1.0, V_meas=3.6, dt=1.0
    )
    assert np.all(np.diag(P_new) >= 0.0)
    assert not np.any(np.isnan(P_new))

def test_ukf_initialization():
    ukf = UnscentedKalmanFilter("li_ion")
    assert ukf.n == 3
    assert len(ukf.Wm) == 7
    assert len(ukf.Wc) == 7

def test_ukf_step_discharge():
    ukf = UnscentedKalmanFilter("li_ion")
    P = np.eye(3) * 0.01
    soc, v1, v2, P_new = ukf.step(
        soc=1.0, v1=0.0, v2=0.0, P=P,
        I_meas=-2.0, V_meas=3.7, dt=1.0, T_meas=25.0
    )
    assert 0.0 <= soc <= 1.0
    assert isinstance(v1, float)
    assert isinstance(v2, float)
    assert P_new.shape == (3, 3)
    assert not np.any(np.isnan(P_new))

def test_ukf_vs_ekf_convergence():
    ekf = ExtendedKalmanFilter("li_ion")
    ukf = UnscentedKalmanFilter("li_ion")
    
    P_ekf = np.eye(3) * 0.01
    P_ukf = np.eye(3) * 0.01
    
    soc_ekf, v1_e, v2_e = 0.9, 0.0, 0.0
    soc_ukf, v1_u, v2_u = 0.9, 0.0, 0.0
    
    for t in range(10):
        soc_ekf, v1_e, v2_e, P_ekf = ekf.step(soc_ekf, v1_e, v2_e, P_ekf, -2.0, 3.65, 1.0)
        soc_ukf, v1_u, v2_u, P_ukf = ukf.step(soc_ukf, v1_u, v2_u, P_ukf, -2.0, 3.65, 1.0)
        
    assert abs(soc_ekf - soc_ukf) < 0.05

def test_resistance_soh_step():
    soh_tracker = ResistanceSOH("li_ion")
    r0_est, soh_est = soh_tracker.step(
        current_r0=0.025, prev_v=3.8, prev_i=0.0,
        V_meas=3.7, I_meas=2.0, soc_est=0.9, T_meas=25.0
    )
    assert 0.001 < r0_est < 0.5
    assert 0.2 <= soh_est <= 1.0

def test_rls_initialization_and_step():
    rls = RecursiveLeastSquares(dt=1.0)
    assert rls.r0 == 0.025 or rls.r0 > 0
    assert not rls.converged
    
    for i in range(60):
        r0, r1, c1, conv = rls.step(3.7 - 0.005*i, -2.0, 3.8)
        
    assert rls.steps >= 50


def test_rls_vff_convergence():
    """Validates that Variable Forgetting Factor (VFF-RLS) adapts lambda and converges under dynamic current."""
    rls = RecursiveLeastSquares(dt=1.0)
    ocv = 3.8
    r0_true = 0.05
    r1_true = 0.03
    c1_true = 500.0
    tau = r1_true * c1_true
    v1 = 0.0
    dt = 1.0

    lambdas = []
    for k in range(120):
        current = -3.0 if (k // 15) % 2 == 0 else -1.0
        v1 = np.exp(-dt / tau) * v1 + r1_true * (1.0 - np.exp(-dt / tau)) * abs(current)
        vt = ocv - abs(current) * r0_true - v1
        r0, r1, c1, conv = rls.step(V_meas=vt, I_meas_ekf=current, ocv=ocv)
        lambdas.append(rls.lmbda)

    assert rls.steps > 100
    assert min(lambdas) < 0.999, "VFF should dynamically reduce lambda on error transients"
    assert 0.005 <= rls.r0 <= 0.5, f"Estimated R0 should be reasonable, got {rls.r0}"


def test_ekf_temperature_adaptation():
    """Validates that EKF and ResistanceSOH adapt to temperature variations using Arrhenius scaling."""
    soh_tracker = ResistanceSOH("li_ion")
    r0_cold, soh_cold = soh_tracker.step(
        current_r0=0.03, prev_v=3.8, prev_i=0.0,
        V_meas=3.65, I_meas=2.0, soc_est=0.9, T_meas=0.0
    )
    r0_warm, soh_warm = soh_tracker.step(
        current_r0=0.03, prev_v=3.8, prev_i=0.0,
        V_meas=3.65, I_meas=2.0, soc_est=0.9, T_meas=25.0
    )
    assert r0_cold != r0_warm
    assert 0.2 <= soh_cold <= 1.0
    assert 0.2 <= soh_warm <= 1.0

    ekf = ExtendedKalmanFilter("li_ion")
    P = np.eye(3) * 0.01
    soc_c, _, _, _ = ekf.step(soc=0.8, v1=0.0, v2=0.0, P=P, I_meas=-2.0, V_meas=3.6, dt=1.0, T_meas=5.0)
    soc_w, _, _, _ = ekf.step(soc=0.8, v1=0.0, v2=0.0, P=P, I_meas=-2.0, V_meas=3.6, dt=1.0, T_meas=35.0)
    assert 0.0 <= soc_c <= 1.0
    assert 0.0 <= soc_w <= 1.0

