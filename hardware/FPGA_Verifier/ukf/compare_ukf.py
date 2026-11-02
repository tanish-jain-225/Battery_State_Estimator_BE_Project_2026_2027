#!/usr/bin/env python3
"""Compare UKF float vs UKF fixed-point and EKF baseline."""
import json
import os
import sys
from collections import OrderedDict

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

H = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(H, "..", "..", ".."))
ESN_PY = os.path.abspath(os.path.join(H, "..", "esn", "python"))
EKF_DIR = os.path.abspath(os.path.join(H, "..", "ekf"))
FPGA_DIR = os.path.abspath(os.path.join(H, ".."))
sys.path[:0] = [H, EKF_DIR, ESN_PY, FPGA_DIR, ROOT_DIR]

from real_ekf_baseline import fit_ekf_baseline, run_ekf_on_cycle
from real_nasa_dataset import generate_nasa_battery_dataset
from ukf_fixed import PROGRAM, build_consts, build_lut, run_ukf_fixed
from ukf_float import run_ukf_on_cycle


def m(y, p):
    y, p = np.asarray(y), np.asarray(p)
    return {
        "mae": round(float(mean_absolute_error(y, p)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y, p))), 4),
        "r2": round(float(r2_score(y, p)), 4),
        "maxae": round(float(np.max(np.abs(y - p))), 4),
    }


rows, meta = generate_nasa_battery_dataset()
cyc = OrderedDict()
for r in rows:
    cyc.setdefault((r["battery"], r["cycle"]), []).append(r)

res = {}
A = {"y": [], "ekf": [], "ukf": [], "ukfq": []}
for tc in ["B0005", "B0006", "B0007", "B0018"]:
    p = fit_ekf_baseline([r for r in rows if r["battery"] != tc])
    cap = meta[tc]["cap_nominal"]
    lut = build_lut(p["ocv_poly"])
    d = {"y": [], "ekf": [], "ukf": [], "ukfq": []}
    for k in [k for k in cyc if k[0] == tc]:
        rr = cyc[k]
        d["y"] += [r["soc_true"] for r in rr]
        d["ekf"] += list(run_ekf_on_cycle(rr, p, capacity_ah=cap))
        d["ukf"] += list(run_ukf_on_cycle(rr, p, capacity_ah=cap))
        d["ukfq"] += list(run_ukf_fixed(rr, build_consts(p, cap, rr[0]["dt"]), lut))
    res[tc] = {k: m(d["y"], d[k]) for k in ["ekf", "ukf", "ukfq"]}
    res[tc]["ukf_fixed_vs_float_maxdiff"] = float(
        np.max(np.abs(np.array(d["ukf"]) - np.array(d["ukfq"])))
    )
    for k in A:
        A[k] += d[k]

res["pooled"] = {k: m(A["y"], A[k]) for k in ["ekf", "ukf", "ukfq"]}
res["pooled"]["ukf_fixed_vs_float_maxdiff"] = float(
    np.max(np.abs(np.array(A["ukf"]) - np.array(A["ukfq"])))
)
res["n_microops"] = {
    t: sum(1 for o in PROGRAM if o[0] == t) for t in ["MAC", "LUT", "DIV", "SQRT"]
}
print(json.dumps(res, indent=1))
with open(os.path.join(H, "compare_results.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1)
