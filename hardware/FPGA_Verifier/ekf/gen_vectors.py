#!/usr/bin/env python3
"""Generate RTL test vectors + golden trace for one nested-LOCO fold.

usage: python3 gen_vectors.py [TEST_CELL] [OUT_DIR]     (default B0018, ./sim)
Writes: ocv_lut.mem, slope_lut.mem, stim.mem, golden_ekf_trace.csv
The EKF is fitted on the three other cells, exactly as in the paper.
"""
import sys, os
from collections import OrderedDict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "../repo_fixed/hardware/FPGA_Verifier")]
from real_nasa_dataset import generate_nasa_battery_dataset
from real_ekf_baseline import fit_ekf_baseline
from ekf_fixed import build_luts, build_consts, run_ekf_fixed, q, F28, F30

tc = sys.argv[1] if len(sys.argv) > 1 else "B0018"
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "sim")
os.makedirs(out, exist_ok=True)
h = lambda v: f"{v & 0xFFFFFFFF:08x}"

rows, meta = generate_nasa_battery_dataset()
cyc = OrderedDict()
for r in rows:
    cyc.setdefault((r["battery"], r["cycle"]), []).append(r)
p = fit_ekf_baseline([r for r in rows if r["battery"] != tc])
ocv, slope = build_luts(p["ocv_poly"])
cap = meta[tc]["cap_nominal"]
keys = [k for k in cyc if k[0] == tc]

open(os.path.join(out, "ocv_lut.mem"), "w").write("\n".join(h(v) for v in ocv) + "\n")
open(os.path.join(out, "slope_lut.mem"), "w").write("\n".join(h(v) for v in slope) + "\n")

stim = [len(keys), len(cyc[keys[0]])]
trace = []
for k in keys:
    rr = cyc[k]
    c = build_consts(p, cap, rr[0]["dt"])
    stim += [c["a"], c["b"], c["kcc"], c["r0"], c["q0"], c["q1"], c["r"], c["p0"], q(rr[0]["soc_true"], F30)]
    for r in rr:
        stim += [q(r["current_measured"], F28), q(r["voltage_measured"], F28)]
    run_ekf_fixed(rr, c, ocv, slope, trace)
open(os.path.join(out, "stim.mem"), "w").write("\n".join(h(v) for v in stim) + "\n")

cols = ["i", "vm", "x0p", "v1p", "p00p", "p01p", "p11p", "idx", "ocv", "h0", "yp", "inn", "ph0", "ph1",
        "s", "k0", "k1", "x0", "v1", "p00", "p01", "p11"]
with open(os.path.join(out, "golden_ekf_trace.csv"), "w") as f:
    f.write("step,t," + ",".join(cols) + "\n")
    for n, d in enumerate(trace):
        f.write(f"{n},{d['t']}," + ",".join(str(d[c]) if c == "idx" else h(d[c]) for c in cols) + "\n")
print(f"{tc}: {len(keys)} cycles, {len(trace)} steps -> {out}")
