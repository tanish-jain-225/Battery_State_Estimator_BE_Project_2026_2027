#!/usr/bin/env python3
"""
ekf_fixed.py -- bit-exact golden model of the fixed-point EKF core (ekf_core.v)

Same 1-RC Thevenin EKF as real_ekf_baseline.py (state x = [SOC, V1],
NASA sign convention: discharge current I < 0), rewritten as the exact
integer operation sequence the RTL executes.

Number formats (all 32-bit signed two's complement):
    Q2.30  (F30): SOC, covariance P, Q, R, S, a = exp(-dt/tau), b = R1(1-a),
                  kcc = dt/(3600*C), R0
    Q4.28  (F28): currents, voltages (Vmeas, OCV, V1, y_pred, innovation),
                  OCV slope h0 (V per unit SOC), Kalman gains K0, K1

One ALU micro-op (one multiplier, one adder -- the same MAC idea as the ESN):
    MAC(a, b, c, s, sub) = sat32( c + rnd(a*b, s) )   (sub=0)
                         = sat32( c - rnd(a*b, s) )   (sub=1)
    rnd(p, s) = (p + 2^(s-1)) >>> s                   (round-half-up, as in the ESN)
Other ops: OCV/slope LUT read, 32-bit signed division, clamp.

Per-cycle constants (a, b, kcc) are computed on the host and loaded like
weights, because dt is constant within each resampled discharge cycle.
OCV(SOC) and dOCV/dSOC are 1024-entry ROMs indexed by the top 10 fraction
bits of SOC (entry k holds the value at SOC = (k + 0.5)/1024).
"""
import math

import numpy as np

F30, F28 = 30, 28
ONE30 = 1 << F30
LUT_BITS = 10
N_LUT = 1 << LUT_BITS
I32_MIN, I32_MAX = -(1 << 31), (1 << 31) - 1


def sat32(v):
    return I32_MIN if v < I32_MIN else I32_MAX if v > I32_MAX else v


def q(x, f):
    """Real -> signed fixed-point integer (round to nearest), saturated."""
    return sat32(int(round(x * (1 << f))))


def rnd(p, s):
    return (p + (1 << (s - 1))) >> s           # Python >> is arithmetic


def mac(a, b, c, s, sub=0):
    r = rnd(a * b, s)
    return sat32(c - r if sub else c + r)


def sdiv(n, d, f):
    """(n << f) / d, truncated toward zero, saturated (sequential divider)."""
    num = abs(n) << f
    qq = num // abs(d)
    if (n < 0) != (d < 0):
        qq = -qq
    return sat32(qq)


def build_luts(ocv_poly):
    d = ocv_poly.deriv()
    soc = (np.arange(N_LUT) + 0.5) / N_LUT
    ocv = [q(float(v), F28) for v in ocv_poly(soc)]
    slope = [q(float(v), F28) for v in d(soc)]
    return ocv, slope


def build_consts(params, capacity_ah, dt, q_soc=1e-6, q_v1=1e-6, r_meas=1e-3, p0=1e-4):
    tau = params["r1"] * params["c1"]
    a = math.exp(-dt / tau)
    return {
        "a": q(a, F30),
        "b": q(params["r1"] * (1 - a), F30),
        "kcc": q(dt / (capacity_ah * 3600.0), F30),
        "r0": q(params["r0"], F30),
        "q0": q(q_soc, F30), "q1": q(q_v1, F30), "r": q(r_meas, F30),
        "p0": q(p0, F30),
    }


def lut_index(soc30):
    k = soc30 >> (F30 - LUT_BITS)
    return 0 if k < 0 else N_LUT - 1 if k > N_LUT - 1 else k


def run_ekf_fixed(cycle_rows, consts, ocv_lut, slope_lut, trace=None):
    """Returns SOC estimates (float) for each step; optionally appends a dict
    of every intermediate integer per step to `trace`."""
    c = consts
    x0 = q(cycle_rows[0]["soc_true"], F30)       # same init as the float EKF
    v1 = 0
    p00, p01, p11 = c["p0"], 0, c["p0"]
    out = []
    for t, row in enumerate(cycle_rows):
        i_k = q(row["current_measured"], F28)
        vm = q(row["voltage_measured"], F28)
        # ---- predict ----
        x0p = mac(c["kcc"], i_k, x0, 28)            # Q2.30
        tmp = mac(c["a"], v1, 0, 30)                # Q4.28
        v1p = mac(c["b"], i_k, tmp, 30)             # Q4.28
        p00p = mac(p00, ONE30, c["q0"], 30)         # P00 + Q0
        p01p = mac(c["a"], p01, 0, 30)              # a*P01
        tmp = mac(c["a"], p11, 0, 30)
        p11p = mac(c["a"], tmp, c["q1"], 30)        # a*a*P11 + Q1
        # ---- update ----
        k = lut_index(x0p)
        ocv, h0 = ocv_lut[k], slope_lut[k]          # Q4.28
        tmp = mac(c["r0"], i_k, ocv, 30)            # OCV + R0*I
        yp = mac(v1p, ONE30, tmp, 30)               # + V1
        inn = mac(yp, ONE30, vm, 30, sub=1)         # Vmeas - y_pred
        ph0 = mac(p00p, h0, p01p, 28)               # P00*h0 + P01   (Q2.30)
        ph1 = mac(p01p, h0, p11p, 28)               # P01*h0 + P11
        tmp = mac(h0, ph0, ph1, 28)                 # h0*PH0 + PH1
        s_ = mac(tmp, ONE30, c["r"], 30)            # + R
        k0 = sdiv(ph0, s_, F28)                     # Q4.28
        k1 = sdiv(ph1, s_, F28)
        x0n = mac(k0, inn, x0p, 26)                 # Q2.30
        x0 = 0 if x0n < 0 else ONE30 if x0n > ONE30 else x0n
        v1 = mac(k1, inn, v1p, 28)                  # Q4.28
        p00 = mac(k0, ph0, p00p, 28, sub=1)
        p01 = mac(k0, ph1, p01p, 28, sub=1)
        p11 = mac(k1, ph1, p11p, 28, sub=1)
        out.append(x0 / ONE30)
        if trace is not None:
            trace.append(dict(t=t, i=i_k, vm=vm, x0p=x0p, v1p=v1p, p00p=p00p, p01p=p01p,
                              p11p=p11p, idx=k, ocv=ocv, h0=h0, yp=yp, inn=inn, ph0=ph0,
                              ph1=ph1, s=s_, k0=k0, k1=k1, x0=x0, v1=v1, p00=p00, p01=p01,
                              p11=p11))
    return np.array(out)
