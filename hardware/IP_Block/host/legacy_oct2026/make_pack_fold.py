#!/usr/bin/env python3
"""Developer tool: build a model pack for ANY leave-one-cell-out fold (same reservoir, fold-specific scaler,
readouts and EKF/UKF OCV fit) plus a test CSV of that cell's 8 discharge cycles.
usage: python3 make_pack_fold.py B0005 OUT_DIR      (needs the NASA .mat files via NASA_MAT_DIR)
Refits exactly like bench/nested_loco.py, asserts equality with bench/loco_results.json, quantises to Q4.14."""
import sys, os, json, csv, shutil
import numpy as np
from collections import OrderedDict
H = os.path.dirname(os.path.abspath(__file__)); S = os.path.abspath(H + "/../..")
sys.path[:0] = [H + "/golden", S + "/repo_fixed/hardware/FPGA_Verifier", S + "/bench"]
from real_nasa_dataset import generate_nasa_battery_dataset, FEATURE_KEYS, BATTERY_CYCLES
from real_ekf_baseline import fit_ekf_baseline
import ekf_fixed, ukf_fixed
from esn_fast import FastESN
from sklearn.linear_model import Ridge
from sklearn.decomposition import PCA
TEST = sys.argv[1]; out = sys.argv[2]; os.makedirs(out, exist_ok=True)
ALL = ["B0005", "B0006", "B0007", "B0018"]; TRAIN = [c for c in ALL if c != TEST]
L = json.load(open(S + "/bench/loco_results.json")); fc = L["folds"][TEST]
rd = lambda p: [int(x, 16) for x in open(p).read().split()]
s16 = lambda v: v - 65536 if v >= 32768 else v
Win = np.array([s16(v) for v in rd(S + "/ip/mem/win_bram.mem")]).reshape(100, 4)
W = np.array([s16(v) for v in rd(S + "/ip/mem/w_bram.mem")]).reshape(100, 100)
B = np.array([s16(v) for v in rd(S + "/ip/mem/bias_bram.mem")])
esn = FastESN(Win, W, B, rd(S + "/ip/mem/tanh.mem"))
rows, meta = generate_nasa_battery_dataset()
cyc = OrderedDict()
for r in rows: cyc.setdefault((r["battery"], r["cycle"]), []).append(r)
tr = [r for r in rows if r["battery"] in TRAIN]
mn = {k: min(r[k] for r in tr) for k in FEATURE_KEYS}; mx = {k: max(r[k] for r in tr) for k in FEATURE_KEYS}
St = {}
for k in cyc:
    esn.reset(); xs = []
    for r in cyc[k]:
        u = [int(round((r[f] - mn[f]) / (mx[f] - mn[f]) * 1024)) for f in FEATURE_KEYS]; xs.append(esn.step(u).copy())
    St[k] = np.array(xs)
trk = [k for k in cyc if k[0] in TRAIN]; tek = [k for k in cyc if k[0] == TEST]
X = np.vstack([St[k] for k in trk]) / 1024.0; y = np.concatenate([[r["soc_true"] for r in cyc[k]] for k in trk])
assert fc["soc_cfg"]["pca"] is None
m = Ridge(alpha=fc["soc_cfg"]["alpha"]).fit(X, y); w_soc, c_soc = m.coef_, float(m.intercept_)
Xs = np.array([St[k].mean(0) / 1024.0 for k in trk]); ys = np.array([cyc[k][0]["soh_true"] for k in trk])
pca = PCA(fc["soh_cfg"]["pca"]).fit(Xs); rm = Ridge(alpha=fc["soh_cfg"]["alpha"]).fit(pca.transform(Xs), ys)
w_soh = pca.components_.T @ rm.coef_; c_soh = float(rm.intercept_ - w_soh @ pca.mean_)
p_soc = np.concatenate([St[k] / 1024.0 @ w_soc + c_soc for k in tek]); p_soh = np.array([St[k].mean(0) / 1024.0 @ w_soh + c_soh for k in tek])
e1 = np.max(np.abs(p_soc - np.array(L["traces"][TEST]["soc_esn"]))); e2 = np.max(np.abs(p_soh - np.array(L["traces"][TEST]["soh_pred"])))
print(f"{TEST}: refit vs published float traces: max SOC diff {e1:.2e}, max SOH diff {e2:.2e}")
assert e1 < 1e-6 and e2 < 1e-6
CLIPPED = []
q18 = lambda v: np.round(np.asarray(v) * (1 << 14)).astype(np.int64)
for nm, wv, cv in (("soc", w_soc, c_soc), ("soh", w_soh, c_soh)):
    q = list(q18(wv)) + [int(q18(cv))]
    big = [v for v in q if abs(v) >= (1 << 17)]
    if big:
        print(f"WARNING {TEST} {nm}: {len(big)} value(s) outside Q4.14 range (max {max(abs(v) for v in q)/16384:.3f}); clipped to +-{((1<<17)-1)/16384:.5f}")
        CLIPPED.append(nm)
        q = [max(-(1 << 17), min((1 << 17) - 1, v)) for v in q]
    open(f"{out}/readout_{nm}.mem", "w").write("\n".join(format(int(v) & 0x3FFFF, "05x") for v in q) + "\n")
def hw_soc(x, wq, cq): return max(-32768, min(32767, ((int(np.dot(wq, x)) + 512) >> 10) + cq))
wq = [int(v) if int(v) < (1 << 17) else int(v) - (1 << 18) for v in (int(t, 16) for t in open(f"{out}/readout_soc.mem").read().split())]
ytrue = np.concatenate([[r["soc_true"] for r in cyc[k]] for k in tek]); hw = np.concatenate([[hw_soc(x, np.array(wq[:-1]), wq[-1]) for x in St[k]] for k in tek]) / 16384.0
print(f"{TEST}: SOC MAE float {np.mean(np.abs(p_soc-ytrue)):.4f}  fixed-point {np.mean(np.abs(hw-ytrue)):.4f}  max |fixed-float| {np.max(np.abs(hw-p_soc)):.4f}")
p = fit_ekf_baseline([r for r in rows if r["battery"] != TEST])
ocv, slope = ekf_fixed.build_luts(p["ocv_poly"]); u_ocv, u_slope = ukf_fixed.build_lut(p["ocv_poly"]); h = lambda v: f"{v & 0xFFFFFFFF:08x}"
for n, l in [("ekf_ocv", ocv), ("ekf_slope", slope), ("ukf_ocv", u_ocv), ("ukf_slope", u_slope)]:
    open(f"{out}/{n}.mem", "w").write("\n".join(h(v) for v in l) + "\n")
for f in ["win_bram", "w_bram", "bias_bram", "tanh"]: shutil.copy(f"{S}/ip/mem/{f}.mem", f"{out}/{f}.mem")
json.dump(dict(name=f"NASA-18650 fold {TEST}", trained_on=TRAIN, features=FEATURE_KEYS, scaler_min=mn, scaler_max=mx, input_scale=1024,
               ocv_poly=[float(c) for c in p["ocv_poly"].coeffs], r0=p["r0"], r1=p["r1"], c1=p["c1"], cap_nominal=meta[TEST]["cap_nominal"],
               n_in=4, n_res=100, t_steps=64), open(f"{out}/pack.json", "w"), indent=1)
# raw test CSV (8 discharge cycles of the held-out cell)
import scipy.io as sio
mat = sio.loadmat(os.environ.get("NASA_MAT_DIR", "/mnt/user-data/uploads") + f"/{TEST}.mat", struct_as_record=False, squeeze_me=True)[TEST].cycle
dis = [c for c in mat if c.type == "discharge"]
w = csv.writer(open(f"{out}/{TEST}_fold_cycles.csv", "w", newline=""))
w.writerow(["time", "voltage_measured", "current_measured", "temperature_measured", "current_load", "cycle", "soc", "capacity"])
for k in BATTERY_CYCLES[TEST]["cycles"]:
    d = dis[k].data; g = lambda a: np.atleast_1d(a).astype(float); t, i = g(d.Time), g(d.Current_measured); cap = float(d.Capacity)
    qq = np.concatenate([[0], np.cumsum((np.abs(i[1:]) + np.abs(i[:-1])) / 2 * np.diff(t))]) / 3600
    for a in zip(t, g(d.Voltage_measured), i, g(d.Temperature_measured), g(d.Current_load), [k] * len(t), np.clip(1 - qq / cap, 0, 1), [cap] * len(t)): w.writerow(a)
print("pack ->", out)
