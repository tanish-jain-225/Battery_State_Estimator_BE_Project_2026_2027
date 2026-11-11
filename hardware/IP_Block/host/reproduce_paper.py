#!/usr/bin/env python3
"""
reproduce_paper.py -- recompute the 29-cell SOC results from the shipped held-out packs, without a board.

  python reproduce_paper.py                 # all packs in packs/heldout
  python reproduce_paper.py --cells B0005 B0047

For each held-out cell it runs the bit-exact software twin (identical to the chip, see esn_host.py) on that
cell's discharge-only windows and reports ESN, EKF with the cell's measured capacity and EKF with the rated
2.0 Ah capacity. Pooled over the 29 cells this gives SOC MAE 0.067 (ESN), 0.063 (EKF measured capacity) and
0.074 (EKF rated capacity), as in the paper. Takes a few minutes (the EKF/UKF twins run step by step).
"""
import os, sys, glob, argparse
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H]
import esn_host as eh


def run_cell(pack_dir, cell):
    pack = eh.Pack(pack_dir)
    wins = eh.split_windows(eh.load_csv(f"{pack_dir}/{cell}_cycles.csv"), "all")
    wins = [(n, w) for n, w in ((n, eh.trim_window(w)[0]) for n, w in wins) if w is not None]
    caps = [float(w["capacity"][0]) for _, w in wins][:3]; cap_meas = float(np.median(caps))
    err = {"ESN": [], "EKF measured cap": [], "EKF rated 2.0 Ah": []}
    for _, win in wins:
        w = eh.make_window(win, "1.0")
        tw = eh.twin_window(pack, w, cap_meas); err["ESN"].append(tw["soc_esn"] / 16384.0 - w["soc_true"])
        err["EKF measured cap"].append(np.asarray(tw["soc_ekf"]) - w["soc_true"])
        U, _ = pack.quantise_inputs(w)
        rows = [dict(current_measured=w["current_measured"][t], voltage_measured=w["voltage_measured"][t], soc_true=w["soc0"]) for t in range(eh.N_STEPS)]
        ekf_r = eh.ekf_fixed.run_ekf_fixed(rows, eh.ekf_fixed.build_consts(pack.params, 2.0, w["dt"]),
                                           [eh.s32(v) for v in pack.luts["ekf_ocv"]], [eh.s32(v) for v in pack.luts["ekf_slope"]])
        err["EKF rated 2.0 Ah"].append(np.asarray(ekf_r) - w["soc_true"])
    return {k: np.concatenate(v) for k, v in err.items()}, len(wins)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--packs", default=H + "/packs/heldout"); ap.add_argument("--cells", nargs="*")
    a = ap.parse_args()
    dirs = sorted(glob.glob(a.packs + "/pack_*"))
    if a.cells: dirs = [d for d in dirs if d.rsplit("_", 1)[1] in a.cells]
    pooled = {}; cellmae = {}
    print(f"{'cell':6} {'windows':>7} | {'ESN':>7} {'EKF meas':>9} {'EKF rated':>9}  (SOC MAE)")
    for d in dirs:
        cell = d.rsplit("_", 1)[1]; e, n = run_cell(d, cell)
        for k, v in e.items(): pooled.setdefault(k, []).append(v); cellmae.setdefault(k, []).append(np.mean(np.abs(v)))
        print(f"{cell:6} {n:7d} | " + " ".join(f"{np.mean(np.abs(v)):>9.4f}" for v in e.values()), flush=True)
    print("-" * 50)
    for k, v in pooled.items():
        a_ = np.abs(np.concatenate(v))
        print(f"{k:18} pooled MAE {a_.mean():.4f}  RMSE {np.sqrt(np.mean(a_ ** 2)):.4f}  P95 {np.percentile(a_, 95):.4f}  "
              f"max {a_.max():.4f}  per-cell SD {np.std(cellmae[k], ddof=1):.4f}  ({len(cellmae[k])} cells)")


if __name__ == "__main__":
    main()
