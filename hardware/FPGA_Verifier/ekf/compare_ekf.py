#!/usr/bin/env python3
"""Float EKF (paper baseline) vs fixed-point EKF golden model, nested-LOCO folds."""
import sys, os, json
from collections import OrderedDict
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "../repo_fixed/hardware/FPGA_Verifier")]
from real_nasa_dataset import generate_nasa_battery_dataset
from real_ekf_baseline import fit_ekf_baseline, run_ekf_on_cycle
from ekf_fixed import build_luts, build_consts, run_ekf_fixed
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

def m(y, p):
    y, p = np.asarray(y), np.asarray(p)
    return dict(mae=round(float(mean_absolute_error(y, p)), 4), rmse=round(float(np.sqrt(mean_squared_error(y, p))), 4),
                r2=round(float(r2_score(y, p)), 4), maxae=round(float(np.max(np.abs(y - p))), 4))

rows, meta = generate_nasa_battery_dataset()
CELLS = ["B0005", "B0006", "B0007", "B0018"]
cyc = OrderedDict()
for r in rows:
    cyc.setdefault((r["battery"], r["cycle"]), []).append(r)

res, Y, PF, PX, DIFF = {}, [], [], [], []
for tc in CELLS:
    p = fit_ekf_baseline([r for r in rows if r["battery"] != tc])
    ocv, slope = build_luts(p["ocv_poly"])
    cap = meta[tc]["cap_nominal"]
    y, pf, px = [], [], []
    for k in [k for k in cyc if k[0] == tc]:
        rr = cyc[k]
        y += [r["soc_true"] for r in rr]
        pf += list(run_ekf_on_cycle(rr, p, capacity_ah=cap))
        px += list(run_ekf_fixed(rr, build_consts(p, cap, rr[0]["dt"]), ocv, slope))
    res[tc] = dict(float=m(y, pf), fixed=m(y, px), max_abs_diff=float(np.max(np.abs(np.array(pf) - np.array(px)))))
    Y += y; PF += pf; PX += px
res["pooled"] = dict(float=m(Y, PF), fixed=m(Y, PX), max_abs_diff=float(np.max(np.abs(np.array(PF) - np.array(PX)))))
print(json.dumps(res, indent=1))
json.dump(res, open(os.path.join(HERE, "compare_results.json"), "w"), indent=1)
