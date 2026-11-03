#!/usr/bin/env python3
"""Developer tool: build a deployable 'model pack' (everything the FPGA platform needs for one trained battery model).

usage: python3 make_pack.py PACK_DIR [TEST_CELL=B0018]
Reads the verified project artefacts (ESN weights, readout, NASA fold fit) and writes
PACK_DIR/{pack.json, *.mem}. The pack is what esn_host.py loads onto the FPGA over UART.
For another battery chemistry: train ESN + readout + EKF/UKF OCV fit on its data, put the same files in a pack.
"""
import sys, os, json, shutil
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); S = os.path.abspath(H + "/../..")
sys.path[:0] = [H + "/golden", S + "/repo_fixed/hardware/FPGA_Verifier"]
from real_nasa_dataset import generate_nasa_battery_dataset, FEATURE_KEYS
from real_ekf_baseline import fit_ekf_baseline
import ekf_fixed, ukf_fixed
out = sys.argv[1]; tc = sys.argv[2] if len(sys.argv) > 2 else "B0018"
os.makedirs(out, exist_ok=True)
rows, meta = generate_nasa_battery_dataset()
train = [r for r in rows if r["battery"] != tc]
mn = {k: min(r[k] for r in train if r["battery"] in ("B0005", "B0006", "B0007")) for k in FEATURE_KEYS}
mx = {k: max(r[k] for r in train if r["battery"] in ("B0005", "B0006", "B0007")) for k in FEATURE_KEYS}
p = fit_ekf_baseline(train)
h = lambda v: f"{v & 0xFFFFFFFF:08x}"
ocv, slope = ekf_fixed.build_luts(p["ocv_poly"]); u_ocv, u_slope = ukf_fixed.build_lut(p["ocv_poly"])
for n, l in [("ekf_ocv", ocv), ("ekf_slope", slope), ("ukf_ocv", u_ocv), ("ukf_slope", u_slope)]:
    open(f"{out}/{n}.mem", "w").write("\n".join(h(v) for v in l) + "\n")
for f in ["win_bram", "w_bram", "bias_bram", "readout_soc", "readout_soh", "tanh"]:
    shutil.copy(f"{S}/ip/mem/{f}.mem", f"{out}/{f}.mem")
json.dump(dict(name=f"NASA-18650 fold {tc}", trained_on=["B0005", "B0006", "B0007"] if tc == "B0018" else "see make_pack",
               features=FEATURE_KEYS, scaler_min=mn, scaler_max=mx, input_scale=1024,
               ocv_poly=[float(c) for c in p["ocv_poly"].coeffs], r0=p["r0"], r1=p["r1"], c1=p["c1"],
               cap_nominal=meta[tc]["cap_nominal"], n_in=4, n_res=100, t_steps=64),
          open(f"{out}/pack.json", "w"), indent=1)
print("pack written to", out)
