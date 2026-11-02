#!/usr/bin/env python3
"""
ukf_fixed.py -- bit-exact golden model of ukf_core.v

The UKF step is written ONCE, as a list of micro-ops (PROGRAM). The same list
is (a) executed here on 32-bit integers -> golden model, and (b) exported to
Verilog by gen_microcode.py -> ukf_core's micro-program ROM. So the RTL and the
golden model cannot drift apart in operation order.

Micro-ops (all registers 32-bit signed):
  MAC  rd = sat32(rc +/- ((ra*rb + 2^(s-1)) >>> s))  [optional clamp to [0,1] Q2.30]
  LUT  rd = OCV_ROM[k], SL = SLOPE_ROM[k], DL = ra - k*2^20     (k = idx(ra))
       idx = top 10 fraction bits of Q2.30 SOC, clamped to 0..1023; followed by
       MAC rd = rd + SL*DL  -> piecewise-linear interpolation of OCV(SOC).
       (Plain table lookup is too coarse here: the sigma points are only a few
        table steps apart, so their OCV differences need interpolation.)
  DIV  rd = sat32((ra << f) / rb)     truncated toward zero
  SQRT rd = isqrt(max(ra,0) << 30)    Q2.30 -> Q2.30, floor

Formats: Q2.30 for SOC, P, Cholesky factor L, gamma*L (SOC part), weights,
Pyy, Pxy, constants; Q4.28 for I, voltages, V1, sigma-point outputs Y,
deviations D, gamma*L (V1 part, H10/H11), gains K.

Filter: same 1-RC model, Q, R, P0 and initial SOC as the EKF. Additive-noise
UKF, Julier sigma points kappa = 3 - n = 1: gamma = sqrt(3), W0 = 1/3, Wi = 1/6.
The second Cholesky column has no SOC component, so sigma points 0, 2, 4 share
one SOC and need only one OCV lookup (3 lookups instead of 5).
"""
import math

import numpy as np

F30, F28 = 30, 28
ONE30 = 1 << 30
N_LUT, LUT_BITS = 1024, 10
I32_MIN, I32_MAX = -(1 << 31), (1 << 31) - 1

# ---------------- register map (6-bit address) ----------------
REGS = ["X0", "V1", "P00", "P01", "P11",                      # filter state
        "I", "VM",                                            # inputs per step
        "A", "B", "KCC", "R0", "Q0", "Q1", "R", "P0",         # per-cycle/fold constants
        "GAM", "W0", "WI", "ONE", "ZERO",                     # sigma-point constants
        "X0P", "V1P", "P00P", "P01P", "P11P", "T",
        "L00", "L10", "L11", "G00", "G10", "G11", "H10", "H11",
        "S1", "S3", "RI", "RV0", "RV1", "RV3",
        "OC0", "OC1", "OC3", "Y0", "Y1", "Y2", "Y3", "Y4", "YH",
        "D0", "D1", "D2", "D3", "D4", "PYY", "PXY0", "PXY1",
        "K0", "K1", "INN", "SL", "DL"]
R = {n: i for i, n in enumerate(REGS)}
assert len(REGS) <= 64


def MAC(rd, ra, rb, rc, s, sub=0, clamp=0): return ("MAC", rd, ra, rb, rc, s, sub, clamp)
def LUT(rd, ra): return ("LUT", rd, ra)
def DIV(rd, ra, rb, f): return ("DIV", rd, ra, rb, f)
def SQRT(rd, ra): return ("SQRT", rd, ra)


PROGRAM = [
    # ---- time update (linear model: identical to the EKF) ----
    MAC("X0P", "KCC", "I", "X0", 28),
    MAC("T", "A", "V1", "ZERO", 30),
    MAC("V1P", "B", "I", "T", 30),
    MAC("P00P", "P00", "ONE", "Q0", 30),
    MAC("P01P", "A", "P01", "ZERO", 30),
    MAC("T", "A", "P11", "ZERO", 30),
    MAC("P11P", "A", "T", "Q1", 30),
    # ---- Cholesky of P_pred (2x2) ----
    SQRT("L00", "P00P"),
    DIV("L10", "P01P", "L00", 30),
    MAC("T", "L10", "L10", "P11P", 30, sub=1),           # P11 - L10^2
    SQRT("L11", "T"),
    # ---- sigma-point offsets gamma*L ----
    MAC("G00", "GAM", "L00", "ZERO", 30),
    MAC("G10", "GAM", "L10", "ZERO", 30),
    MAC("G11", "GAM", "L11", "ZERO", 30),
    MAC("H10", "G10", "ONE", "ZERO", 32),                 # Q2.30 -> Q4.28 (volts)
    MAC("H11", "G11", "ONE", "ZERO", 32),
    MAC("S1", "G00", "ONE", "X0P", 30),                   # SOC of sigma point 1
    MAC("S3", "G00", "ONE", "X0P", 30, sub=1),            # SOC of sigma point 3
    # ---- measurement function at the 5 sigma points ----
    MAC("RI", "R0", "I", "ZERO", 30),                     # R0*I
    LUT("OC0", "X0P"), MAC("OC0", "SL", "DL", "OC0", 30),
    LUT("OC1", "S1"),  MAC("OC1", "SL", "DL", "OC1", 30),
    LUT("OC3", "S3"),  MAC("OC3", "SL", "DL", "OC3", 30),
    MAC("RV0", "RI", "ONE", "V1P", 30),                   # V1 + R0*I
    MAC("Y0", "OC0", "ONE", "RV0", 30),
    MAC("Y2", "H11", "ONE", "Y0", 30),
    MAC("Y4", "H11", "ONE", "Y0", 30, sub=1),
    MAC("RV1", "H10", "ONE", "RV0", 30),
    MAC("Y1", "OC1", "ONE", "RV1", 30),
    MAC("RV3", "H10", "ONE", "RV0", 30, sub=1),
    MAC("Y3", "OC3", "ONE", "RV3", 30),
    # ---- predicted measurement (weighted mean) ----
    MAC("YH", "W0", "Y0", "ZERO", 30),
    MAC("YH", "WI", "Y1", "YH", 30),
    MAC("YH", "WI", "Y2", "YH", 30),
    MAC("YH", "WI", "Y3", "YH", 30),
    MAC("YH", "WI", "Y4", "YH", 30),
    # ---- deviations ----
    MAC("D0", "YH", "ONE", "Y0", 30, sub=1),
    MAC("D1", "YH", "ONE", "Y1", 30, sub=1),
    MAC("D2", "YH", "ONE", "Y2", 30, sub=1),
    MAC("D3", "YH", "ONE", "Y3", 30, sub=1),
    MAC("D4", "YH", "ONE", "Y4", 30, sub=1),
    # ---- innovation covariance Pyy = R + sum W_i D_i^2 ----
    MAC("T", "D0", "D0", "ZERO", 26), MAC("PYY", "W0", "T", "R", 30),
    MAC("T", "D1", "D1", "ZERO", 26), MAC("PYY", "WI", "T", "PYY", 30),
    MAC("T", "D2", "D2", "ZERO", 26), MAC("PYY", "WI", "T", "PYY", 30),
    MAC("T", "D3", "D3", "ZERO", 26), MAC("PYY", "WI", "T", "PYY", 30),
    MAC("T", "D4", "D4", "ZERO", 26), MAC("PYY", "WI", "T", "PYY", 30),
    # ---- cross covariance Pxy (SOC row uses +/-G00, V1 row +/-H10, +/-H11) ----
    MAC("T", "G00", "D1", "ZERO", 28), MAC("PXY0", "WI", "T", "ZERO", 30),
    MAC("T", "G00", "D3", "ZERO", 28), MAC("PXY0", "WI", "T", "PXY0", 30, sub=1),
    MAC("T", "H10", "D1", "ZERO", 26), MAC("PXY1", "WI", "T", "ZERO", 30),
    MAC("T", "H11", "D2", "ZERO", 26), MAC("PXY1", "WI", "T", "PXY1", 30),
    MAC("T", "H10", "D3", "ZERO", 26), MAC("PXY1", "WI", "T", "PXY1", 30, sub=1),
    MAC("T", "H11", "D4", "ZERO", 26), MAC("PXY1", "WI", "T", "PXY1", 30, sub=1),
    # ---- gain and update ----
    DIV("K0", "PXY0", "PYY", 28),
    DIV("K1", "PXY1", "PYY", 28),
    MAC("INN", "YH", "ONE", "VM", 30, sub=1),
    MAC("X0", "K0", "INN", "X0P", 26, clamp=1),
    MAC("V1", "K1", "INN", "V1P", 28),
    MAC("P00", "K0", "PXY0", "P00P", 28, sub=1),
    MAC("P01", "K0", "PXY1", "P01P", 28, sub=1),
    MAC("P11", "K1", "PXY1", "P11P", 28, sub=1),
]

TRACE = ["X0P", "V1P", "P00P", "P01P", "P11P", "L00", "L10", "L11", "OC0", "OC1", "OC3",
         "YH", "PYY", "PXY0", "PXY1", "K0", "K1", "INN", "X0", "V1", "P00", "P01", "P11"]


def sat32(v): return I32_MIN if v < I32_MIN else I32_MAX if v > I32_MAX else v
def q(x, f): return sat32(int(round(x * (1 << f))))


def lut_index(v):
    k = v >> (F30 - LUT_BITS)
    return 0 if k < 0 else N_LUT - 1 if k > N_LUT - 1 else k


def execute(rf, ocv_lut):
    for op in PROGRAM:
        if op[0] == "MAC":
            _, rd, ra, rb, rc, s, sub, clamp = op
            p = rf[R[ra]] * rf[R[rb]]
            r = (p + (1 << (s - 1))) >> s
            v = sat32(rf[R[rc]] - r if sub else rf[R[rc]] + r)
            if clamp:
                v = 0 if v < 0 else ONE30 if v > ONE30 else v
            rf[R[rd]] = v
        elif op[0] == "LUT":
            v = rf[R[op[2]]]
            k = lut_index(v)
            rf[R[op[1]]] = ocv_lut[0][k]
            rf[R["SL"]] = ocv_lut[1][k]
            rf[R["DL"]] = sat32(v - (k << (F30 - LUT_BITS)))
        elif op[0] == "DIV":
            _, rd, ra, rb, f = op
            n, d = rf[R[ra]], rf[R[rb]]
            qq = (abs(n) << f) // abs(d)
            rf[R[rd]] = sat32(-qq if (n < 0) != (d < 0) else qq)
        else:  # SQRT
            v = rf[R[op[2]]]
            rf[R[op[1]]] = math.isqrt(max(v, 0) << 30)


def build_lut(ocv_poly):
    """(OCV at the left edge k/1024, secant slope to the next edge), both Q4.28.
    Interpolation then passes exactly through the polynomial at every edge."""
    e = np.arange(N_LUT + 1) / N_LUT
    v = ocv_poly(e)
    return ([q(float(x), F28) for x in v[:-1]],
            [q(float(x), F28) for x in (v[1:] - v[:-1]) * N_LUT])


def build_consts(params, capacity_ah, dt, q_soc=1e-6, q_v1=1e-6, r_meas=1e-3, p0=1e-4, kappa=1.0, n=2):
    a = math.exp(-dt / (params["r1"] * params["c1"]))
    return {"A": q(a, F30), "B": q(params["r1"] * (1 - a), F30), "KCC": q(dt / (capacity_ah * 3600.0), F30),
            "R0": q(params["r0"], F30), "Q0": q(q_soc, F30), "Q1": q(q_v1, F30), "R": q(r_meas, F30),
            "P0": q(p0, F30), "GAM": q(math.sqrt(n + kappa), F30),
            "W0": q(kappa / (n + kappa), F30), "WI": q(1.0 / (2 * (n + kappa)), F30)}


def run_ukf_fixed(cycle_rows, consts, ocv_lut, trace=None):
    rf = [0] * 64
    for k, v in consts.items():
        rf[R[k]] = v
    rf[R["ONE"]] = ONE30
    rf[R["X0"]] = q(cycle_rows[0]["soc_true"], F30)
    rf[R["V1"]], rf[R["P00"]], rf[R["P01"]], rf[R["P11"]] = 0, consts["P0"], 0, consts["P0"]
    out = []
    for t, row in enumerate(cycle_rows):
        rf[R["I"]] = q(row["current_measured"], F28)
        rf[R["VM"]] = q(row["voltage_measured"], F28)
        execute(rf, ocv_lut)
        out.append(rf[R["X0"]] / ONE30)
        if trace is not None:
            d = {k: rf[R[k]] for k in TRACE}
            d.update(t=t, I=rf[R["I"]], VM=rf[R["VM"]])
            trace.append(d)
    return np.array(out)
