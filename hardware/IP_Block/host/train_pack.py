#!/usr/bin/env python3
"""
train_pack.py -- train a new model pack for the FPGA platform from battery discharge data.

The reservoir (Win, W, bias, tanh table) stays fixed: it is the verified one inside every pack. Only the
input scaling, the two Q4.14 readouts (SOC, SOH) and the EKF/UKF tables are fitted, so a new pack
needs no new bitstream.

  # NASA PCoE .mat files (B0005.mat ...), train on every cell:
  python train_pack.py --mat-dir Battery --out packs/my_pack
  # hold one cell out and also write its test CSV for esn_host.py:
  python train_pack.py --mat-dir Battery --holdout B0047 --out packs/my_B0047
  # your own data: one CSV, one row per sample, columns
  #   cell, cycle, time, voltage, current, temperature, [current_load], capacity
  python train_pack.py --csv mycells.csv --ekf-cells CELL_A,CELL_B --out packs/my_cells

Data rules (same as the paper and the shipped packs):
  * discharge current negative; each discharge ends at its last sample with current < -0.25 A
  * a discharge is skipped if it has < 16 loaded samples, no capacity (or < 0.2 Ah), or its capacity
    differs from the integrated charge by more than 10 %
  * SOC label = 1 - Coulomb-counted charge / that discharge's capacity (starts at 1)
  * SOH label = capacity / median of the cell's first three valid capacities; cells with any SOH label
    outside --soh-range are left out of the SOH readout only
  * each discharge is resampled to 64 steps; inputs: voltage, current, temperature, load current
Model selection: inner cross-validation over groups of training CELLS, scored on the quantised (chip)
readout; ridge regression, optional PCA folded into one linear map.
Needs numpy, scikit-learn, and scipy for .mat files.
"""
import os, sys, glob, json, csv, argparse, shutil
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, H + "/golden"]
import ekf_fixed, ukf_fixed
from ekf_fit import fit_ekf_baseline
from sklearn.linear_model import Ridge
from sklearn.decomposition import PCA

N = 64; TRIM_A = 0.25; FEAT = ["voltage_measured", "current_measured", "temperature_measured", "current_load"]
rd = lambda p: [int(x, 16) for x in open(p).read().split()]
s16 = lambda v: v - 65536 if v >= 32768 else v
rs = lambda a: np.interp(np.linspace(0, 1, N), np.linspace(0, 1, len(a)), a)


def make_cycle(cell, k, t, v, i, T, il, cap):
    """Trim, check and resample one discharge. Returns a dict (ok flag + reason)."""
    n = min(len(t), len(v), len(i), len(T), len(il)); t, v, i, T, il = t[:n], v[:n], i[:n], T[:n], il[:n]
    if n > 1 and (i < -TRIM_A).any():
        n = int(np.where(i < -TRIM_A)[0][-1]) + 1; t, v, i, T, il = t[:n], v[:n], i[:n], T[:n], il[:n]
    reason = None
    if n < 16: reason = "too few samples"
    elif not np.all(np.diff(t) > 0): reason = "time not increasing"
    elif not np.isfinite(cap) or cap < 0.2: reason = "capacity missing/<0.2Ah"
    q = np.concatenate([[0], np.cumsum((np.abs(i[1:]) + np.abs(i[:-1])) / 2 * np.diff(t))]) / 3600 if n > 1 else np.zeros(n)
    if reason is None and abs(q[-1] / cap - 1) > 0.10: reason = "capacity != integrated charge (>10%)"
    if reason is None and not ((np.median(i[i < -0.05]) if (i < -0.05).any() else 0) < -0.5): reason = "no sustained discharge current"
    c = dict(cell=cell, k=k, cap=cap, ok=reason is None, reason=reason)
    if reason is None:
        c.update(X=np.stack([rs(v), rs(i), rs(T), rs(il)], 1), soc=rs(np.clip(1 - q / cap, 0, 1)),
                 dt=float(t[-1] - t[0]) / (N - 1), raw=(t, v, i, T, il, np.clip(1 - q / cap, 0, 1)))
    return c


def load_mat_dir(d):
    import scipy.io as sio
    out = []
    for f in sorted(glob.glob(os.path.join(d, "*.mat"))):
        b = os.path.splitext(os.path.basename(f))[0]
        dis = [c for c in sio.loadmat(f, struct_as_record=False, squeeze_me=True)[b].cycle if c.type == "discharge"]
        for k, c in enumerate(dis):
            x = c.data; g = lambda a: np.atleast_1d(a).astype(float)
            cap = float(np.atleast_1d(x.Capacity)[0]) if np.size(x.Capacity) else np.nan
            out.append(make_cycle(b, k, g(x.Time), g(x.Voltage_measured), g(x.Current_measured),
                                  g(x.Temperature_measured), g(x.Current_load), cap))
    return out


def load_csv(path):
    rows = list(csv.DictReader(open(path, newline="")))
    key = lambda r, *ns: next((r[n] for n in ns if n in r and r[n] != ""), None)
    groups = {}
    for r in rows:
        r = {k.strip().lower(): v for k, v in r.items()}
        groups.setdefault((r["cell"], int(float(r["cycle"]))), []).append(r)
    out = []
    for (cell, k), rr in sorted(groups.items()):
        f = lambda *ns: np.array([float(key(r, *ns)) for r in rr])
        i = f("current", "current_measured")
        il = f("current_load", "load_current") if key(rr[0], "current_load", "load_current") is not None else np.abs(i)
        out.append(make_cycle(cell, k, f("time"), f("voltage", "voltage_measured"), i, f("temperature", "temperature_measured"),
                              il, float(key(rr[0], "capacity"))))
    return out


def q18(v):
    q = np.round(np.asarray(v, float) * (1 << 14)).astype(np.int64)
    return np.clip(q, -(1 << 17), (1 << 17) - 1), int(np.sum(np.abs(q) >= (1 << 17)))


def fold_linear(Z, y, pca_k, alpha):
    if pca_k:
        p = PCA(pca_k).fit(Z); m = Ridge(alpha=alpha).fit(p.transform(Z), y)
        w = p.components_.T @ m.coef_; return w, float(m.intercept_ - w @ p.mean_)
    m = Ridge(alpha=alpha).fit(Z, y); return m.coef_, float(m.intercept_)


def hw_soc(Sx, w, c):
    (wq, _), (cq, _) = q18(w), q18([c])
    return np.clip(((Sx @ wq + 512) >> 10) + cq[0], -32768, 32767) / 16384.0


def hw_soh(Sx, w, c):
    (wq, _), (cq, _) = q18(w), q18([c])
    return np.clip((((Sx @ wq).sum(axis=1) + (1 << 15)) >> 16) + cq[0], -32768, 32767) / 16384.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--mat-dir", help="folder of NASA PCoE .mat files"); src.add_argument("--csv", help="your own data, see above")
    ap.add_argument("--out", required=True); ap.add_argument("--holdout", help="cell left out of training (its test CSV is written)")
    ap.add_argument("--min-windows", type=int, default=1, help="cells with fewer valid discharges are not used")
    ap.add_argument("--ekf-cells", default="B0005,B0006,B0007,B0018", help="cells used to calibrate the EKF/UKF OCV and R0 (missing ones are ignored; none left -> all training cells)")
    ap.add_argument("--soh-range", type=float, nargs=2, default=[0.5, 1.15])
    ap.add_argument("--base-pack", default=H + "/packs/general_32cells", help="pack whose reservoir and tanh table are reused")
    ap.add_argument("--rated-ah", type=float, default=2.0, help="cap_nominal written to the pack")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    allc = load_mat_dir(a.mat_dir) if a.mat_dir else load_csv(a.csv)
    cyc = [c for c in allc if c["ok"]]
    print(f"{len(allc)} discharges read, {len(cyc)} valid after trimming and quality checks")
    for b in sorted({c['cell'] for c in cyc}):            # SOH labels per cell
        v = [c for c in cyc if c["cell"] == b]; ref = float(np.median([c["cap"] for c in v[:3]]))
        for c in v: c["soh"] = c["cap"] / ref
    cells = sorted({c["cell"] for c in cyc}); by = {b: [i for i, c in enumerate(cyc) if c["cell"] == b] for b in cells}
    tr = [b for b in cells if b != a.holdout and len(by[b]) >= a.min_windows]
    if len(tr) < 2: raise SystemExit("need at least two training cells")
    X = np.array([c["X"] for c in cyc]); Y = np.array([c["soc"] for c in cyc]); Hs = np.array([c["soh"] for c in cyc])
    soh_ok = {b: bool(np.all((Hs[by[b]] >= a.soh_range[0]) & (Hs[by[b]] <= a.soh_range[1]))) for b in cells}

    base = a.base_pack
    WIN = np.array([s16(v) for v in rd(base + "/win_bram.mem")], np.int64).reshape(100, 4)
    W = np.array([s16(v) for v in rd(base + "/w_bram.mem")], np.int64).reshape(100, 100)
    BIAS = np.array([s16(v) for v in rd(base + "/bias_bram.mem")], np.int64); LUT = np.array([s16(v) for v in rd(base + "/tanh.mem")], np.int64)
    Z = X[[i for b in tr for i in by[b]]].reshape(-1, 4); mn, mx = Z.min(0), Z.max(0)
    U = np.clip(np.round((X - mn) / (mx - mn) * 1024), -32768, 32767).astype(np.int64)
    x = np.zeros((len(U), 100), np.int64); S = np.empty((len(U), N, 100), np.int64)
    for t in range(N):                                    # bit-exact Q6.10 reservoir (same as the chip)
        acc = (U[:, t].astype(float) @ WIN.T.astype(float) + x.astype(float) @ W.T.astype(float)).astype(np.int64)
        s = np.clip(np.clip((acc + 512) >> 10, -32768, 32767) + BIAS, -5120, 5120)
        mag = LUT[np.abs(s)]; x = np.clip(np.where(s < 0, -mag, mag), -32768, 32767); S[:, t] = x

    rng = np.random.default_rng(a.seed); perm = list(rng.permutation(tr)); G = min(4, len(tr)); inner = [perm[j::G] for j in range(G)]
    pool = lambda cs: [i for b in cs for i in by[b]]; spool = lambda cs: [i for b in cs if soh_ok[b] for i in by[b]]
    def select(kind, grid):
        sc = []
        for cfg in grid:
            err = []
            for val in inner:
                fit = [b for b in tr if b not in val]
                if kind == "soc":
                    A, V = pool(fit), pool(val)
                    if not V: continue
                    w, c = fold_linear(S[A].reshape(-1, 100) / 1024, Y[A].ravel(), *cfg); err.append(np.mean((hw_soc(S[V], w, c) - Y[V]) ** 2))
                else:
                    A, V = spool(fit), spool(val)
                    if not V or len(A) < 20: continue
                    w, c = fold_linear(S[A].mean(1) / 1024, Hs[A], *cfg); err.append(np.mean((hw_soh(S[V], w, c) - Hs[V]) ** 2))
            sc.append(np.sqrt(np.mean(err)) if err else np.inf)
        return grid[int(np.argmin(sc))]
    soc_cfg = select("soc", [(k, al) for k in (None, 50) for al in (1e-3, 1e-2, 1e-1, 1, 10)])
    soh_cfg = select("soh", [(k, al) for k in (5, 8, 12) for al in (1e-3, 1e-2, 1e-1, 1)])
    A = pool(tr); ws, cs = fold_linear(S[A].reshape(-1, 100) / 1024, Y[A].ravel(), *soc_cfg)
    A = spool(tr); wh, ch = fold_linear(S[A].mean(1) / 1024, Hs[A], *soh_cfg)

    os.makedirs(a.out, exist_ok=True); clipped = 0
    for nm, (w, c) in (("soc", (ws, cs)), ("soh", (wh, ch))):
        (wq, k1), (cq, k2) = q18(w), q18([c]); clipped += k1 + k2
        open(f"{a.out}/readout_{nm}.mem", "w").write("\n".join(format(int(v) & 0x3FFFF, "05x") for v in list(wq) + [cq[0]]) + "\n")
    ek = [b for b in a.ekf_cells.split(",") if b in tr] or tr
    p = fit_ekf_baseline([dict(soc_true=float(cyc[i]["soc"][t]), voltage_measured=float(cyc[i]["X"][t, 0]), current_measured=float(cyc[i]["X"][t, 1]))
                          for b in ek for i in by[b] for t in range(N)])
    h = lambda v: f"{v & 0xFFFFFFFF:08x}"
    eo, es = ekf_fixed.build_luts(p["ocv_poly"]); uo, us = ukf_fixed.build_lut(p["ocv_poly"])
    for n, l in [("ekf_ocv", eo), ("ekf_slope", es), ("ukf_ocv", uo), ("ukf_slope", us)]:
        open(f"{a.out}/{n}.mem", "w").write("\n".join(h(v) for v in l) + "\n")
    for f in ("win_bram", "w_bram", "bias_bram", "tanh"): shutil.copy(f"{base}/{f}.mem", f"{a.out}/{f}.mem")
    json.dump(dict(name=f"model trained on {len(tr)} cells" + (f", held-out {a.holdout}" if a.holdout else ""), trained_on=tr, features=FEAT,
                   scaler_min=dict(zip(FEAT, map(float, mn))), scaler_max=dict(zip(FEAT, map(float, mx))), input_scale=1024,
                   ocv_poly=[float(c) for c in p["ocv_poly"].coeffs], r0=p["r0"], r1=p["r1"], c1=p["c1"], cap_nominal=a.rated_ah,
                   ekf_calibration=ek, window_rule="discharge only: ends at last sample with current < -0.25 A",
                   soc_cfg=list(soc_cfg), soh_cfg=list(soh_cfg), n_in=4, n_res=100, t_steps=N), open(f"{a.out}/pack.json", "w"), indent=1)
    if a.holdout:
        if a.holdout not in by: raise SystemExit(f"--holdout {a.holdout}: no valid discharges for that cell")
        idx = by[a.holdout]; e = hw_soc(S[idx], ws, cs) - Y[idx]
        print(f"held-out {a.holdout}: {len(idx)} discharges, ESN SOC MAE {np.mean(np.abs(e)):.4f} (chip readout, bit-exact path)")
        with open(f"{a.out}/{a.holdout}_cycles.csv", "w", newline="") as fh:
            wr = csv.writer(fh); wr.writerow(["time", "voltage_measured", "current_measured", "temperature_measured", "current_load", "cycle", "soc", "capacity"])
            for i in idx:
                t, v, cur, T, il, soc = cyc[i]["raw"]
                for r in zip(t, v, cur, T, il, [cyc[i]["k"]] * len(t), soc, [cyc[i]["cap"]] * len(t)): wr.writerow(r)
    print(f"pack -> {a.out} | trained on {len(tr)} cells | SOC cfg {soc_cfg} SOH cfg {soh_cfg} | EKF calibration {ek}"
          + (f" | WARNING {clipped} readout weight(s) clipped to the Q4.14 range" if clipped else ""))


if __name__ == "__main__":
    main()
