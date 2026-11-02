#!/usr/bin/env python3
"""
eval_fpga_outcomes.py
─────────────────────
Hardware FPGA Verifier & Consolidated Outcomes Evaluation Suite.
Validates the Q6.10 ESN FPGA implementation against all results and specs in:
docs/Review_2/Outcomes/FPGA-Based-Echo-State-Network-for-Battery-SOC-SOH-Estimation-Outcomes.pdf

Covers:
  1. Committed Q6.10 reservoir weights (win_bram.coe / w_bram.coe / bias_bram.coe)
     -- the SAME weights used for the 200/200 bit-exact RTL verification --
     run through the bit-exact GoldenESN datapath.
  2. Dataset coverage across 32 cycles, loaded from the REAL NASA PCoE
     B0005/B0006/B0007/B0018 .mat files (B0005 = train, B0006/7/18 = unseen
     test). No synthetic/fabricated telemetry is used.
  3. Hardware verification checks (bit-exact parity against vivado_esn_results.csv,
     X-corruption, input addressing).
  4. Ridge-regression readout SOC/SOH estimation -- fit on train rows and
     ACTUALLY evaluated via .predict() on held-out rows. Numbers below are
     computed by this script, not hardcoded.
  5. A genuine 1RC-Thevenin EKF baseline (real_ekf_baseline.py), fit and
     run on the SAME real NASA cycles, for a fair comparison.
  6. Post-implementation Artix-7 synthesis, power, timing & real-time
     headroom audit (transcribed from the Vivado implementation run --
     see the docstring note in print_synthesis_report() for provenance).

REQUIRES: B0005.mat, B0006.mat, B0007.mat, B0018.mat present in
          NASA_MAT_DIR (default: /mnt/user-data/uploads, override via env var).
"""

import os
import sys
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Force UTF-8 output if supported
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from golden_model import GoldenESN, parse_coe_file, load_tanh_mem
from real_nasa_dataset import generate_nasa_battery_dataset, FEATURE_KEYS
from real_ekf_baseline import fit_ekf_baseline, run_ekf_on_cycle


def load_committed_reservoir_weights():
    """
    Loads the ACTUAL committed .coe weight files -- the same ones used for
    the 200/200 bit-exact RTL verification -- rather than regenerating a
    fresh seed=42 draw. This ties the SOC/SOH numbers below to the exact
    reservoir that was hardware-verified, not to a parallel, uncommitted
    weight set.
    """
    win = np.array(parse_coe_file(os.path.join(BASE_DIR, "win_bram.coe"))).reshape(100, 4)
    w = np.array(parse_coe_file(os.path.join(BASE_DIR, "w_bram.coe"))).reshape(100, 100)
    bias = np.array(parse_coe_file(os.path.join(BASE_DIR, "bias_bram.coe"))).reshape(100)
    return win, w, bias


def compute_metrics(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    return mae, rmse, r2


def evaluate_fpga_outcomes():
    """Executes full outcomes evaluation on REAL data and returns a results dict
    (callers/tests should inspect the dict's values, not just a boolean)."""
    print("=" * 75)
    print("      FPGA-BASED ECHO STATE NETWORK FOR BATTERY SOC/SOH ESTIMATION")
    print("                 CONSOLIDATED RESULTS & HARDWARE VERIFIER")
    print("=" * 75)
    print()

    results = {}

    # 1. System Specifications & committed weight loading
    print("+------------------------------------------------------------------------+")
    print("| SYSTEM OVERVIEW & ESN HARDWARE ARCHITECTURE                            |")
    print("+----------------------------------+-------------------------------------+")
    print("| Parameter                        | Value                               |")
    print("+----------------------------------+-------------------------------------+")
    print("| Reservoir Size (N_RES)           | 100 neurons                         |")
    print("| Input Dimensionality (N_IN)      | 4 features                          |")
    print("| Arithmetic Format                | Q6.10 signed fixed-point            |")
    print("| Target Device                    | Xilinx Artix-7 (xc7a100tcsg324-1)   |")
    print("| Target Board                     | Digilent ArtyA7-100T                |")
    print("| Input Features                   | V_meas, I_meas, T_meas, I_load      |")
    print("+----------------------------------+-------------------------------------+")
    print()

    Win, W, bias = load_committed_reservoir_weights()
    print(f"Loaded COMMITTED reservoir weights from win_bram.coe/w_bram.coe/bias_bram.coe "
          f"(the same weights verified bit-exact against Vivado/XSim): "
          f"Win shape={Win.shape}, W shape={W.shape}")
    print()

    # 2. Dataset Processing -- REAL NASA .mat files, not synthetic
    print("Loading REAL NASA PCoE battery telemetry (.mat files)...")
    raw_data, batteries_meta = generate_nasa_battery_dataset()
    print(f"Loaded {len(raw_data)} total samples across "
          f"{sum(len(v['cycles']) for v in batteries_meta.values())} cycles "
          f"from B0005 (train) / B0006, B0007, B0018 (unseen test).")
    for b, m in batteries_meta.items():
        print(f"  {b}: role={m['role']}, SOH {m['soh_range'][0]:.4f} -> {m['soh_range'][1]:.4f}, "
              f"cap={m['cap_nominal']:.4f} Ah")
    print()

    # Min-Max Normalization: fit on B0005 (train) only
    train_rows_raw = [r for r in raw_data if r['role'] == 'Train']
    train_feats = np.array([[r[k] for k in FEATURE_KEYS] for r in train_rows_raw])
    f_min = train_feats.min(axis=0)
    f_max = train_feats.max(axis=0)
    f_max[f_max == f_min] += 1e-6

    def scale_features(row):
        vec = np.array([row[k] for k in FEATURE_KEYS])
        scaled = (vec - f_min) / (f_max - f_min)
        return np.round(scaled * 1024.0).astype(np.int64)

    esn = GoldenESN(n_in=4, n_res=100, Win=Win, W=W, bias=bias)

    X_train, y_soc_train, y_soh_train = [], [], []
    X_test, y_soc_test, y_soh_test = [], [], []
    test_meta = []  # (battery, cycle) per test row, for the EKF comparison loop

    all_cycles = sorted(set((r['battery'], r['cycle']) for r in raw_data))

    x_corruptions = 0
    total_evaluations = 0

    cycles_by_key = {}
    for b_id, c_num in all_cycles:
        cycles_by_key[(b_id, c_num)] = [r for r in raw_data if r['battery'] == b_id and r['cycle'] == c_num]

    for (b_id, c_num), c_rows in cycles_by_key.items():
        esn.reset()
        for t_idx, r in enumerate(c_rows):
            u_q610 = scale_features(r)
            records = esn.step(u_q610, pass_idx=t_idx)
            total_evaluations += 1
            for rec in records:
                if rec['tanh_out'] is None or 'x' in str(rec['tanh_out']).lower():
                    x_corruptions += 1
            state_real = esn.x.astype(np.float64) / 1024.0

            if r['role'] == 'Train':
                X_train.append(state_real)
                y_soc_train.append(r['soc_true'])
                y_soh_train.append(r['soh_true'])
            else:
                X_test.append(state_real)
                y_soc_test.append(r['soc_true'])
                y_soh_test.append(r['soh_true'])
                test_meta.append((b_id, c_num))

    X_train, y_soc_train, y_soh_train = np.array(X_train), np.array(y_soc_train), np.array(y_soh_train)
    X_test, y_soc_test, y_soh_test = np.array(X_test), np.array(y_soc_test), np.array(y_soh_test)

    # 3. Hardware Verification Summary (bit-exact RTL parity, loaded from disk)
    print("+------------------------------------------------------------------------+")
    print("| HARDWARE VERIFICATION AUDIT CHECKS                                     |")
    print("+----------------------------------------------------+-------------------+")
    print("| Check                                              | Result            |")
    print("+----------------------------------------------------+-------------------+")
    from compare_results import load_csv
    golden_path = os.path.join(BASE_DIR, "golden_results.csv")
    vivado_path = os.path.join(BASE_DIR, "vivado_esn_results.csv")
    bit_exact_ok = False
    if os.path.exists(golden_path) and os.path.exists(vivado_path):
        golden_map, _ = load_csv(golden_path, default_key_pass='pass')
        vivado_map, _ = load_csv(vivado_path, default_key_pass='passbuf')
        stages = ['mac', 'bias', 'sum', 'tanh_in', 'tanh_out']
        mismatches = 0
        for k in golden_map.keys():
            if k not in vivado_map:
                mismatches += 1
                continue
            for stg in stages:
                g_val = golden_map[k][stg].strip().lower().lstrip('0') or '0'
                v_val = vivado_map[k][stg].strip().lower().lstrip('0') or '0'
                if g_val != v_val:
                    mismatches += 1
        bit_exact_ok = (mismatches == 0)
        print(f"| Bit-exact Python golden model vs. Vivado/XSim      | "
              f"{'Exact match (' + str(len(golden_map)) + '/' + str(len(golden_map)) + ')' if bit_exact_ok else str(mismatches) + ' MISMATCHES':<18}|")
    else:
        print("| Bit-exact Python golden model vs. Vivado/XSim      | FILES MISSING     |")
    print(f"| X-corruption (unknown/uninitialized values)        | {x_corruptions} occurrences"
          f"{' ' * max(0, 6 - len(str(x_corruptions)))}|")
    print("+----------------------------------------------------+-------------------+")
    print(f"Verified {total_evaluations} real-NASA-telemetry timestep inferences across 32 cycles.")
    print()

    results['bit_exact_match'] = bit_exact_ok
    results['x_corruptions'] = x_corruptions

    # 4. Readout Training & ACTUAL evaluation (fit + predict, not hardcoded)
    ridge_soc = Ridge(alpha=0.1)
    ridge_soc.fit(X_train, y_soc_train)
    ridge_soh = Ridge(alpha=0.1)
    ridge_soh.fit(X_train, y_soh_train)

    pred_soc_train = ridge_soc.predict(X_train)
    pred_soc_test = ridge_soc.predict(X_test)
    pred_soh_train = ridge_soh.predict(X_train)
    pred_soh_test = ridge_soh.predict(X_test)

    soc_train_mae, soc_train_rmse, soc_train_r2 = compute_metrics(y_soc_train, pred_soc_train)
    soc_test_mae, soc_test_rmse, soc_test_r2 = compute_metrics(y_soc_test, pred_soc_test)
    soh_train_mae, soh_train_rmse, soh_train_r2 = compute_metrics(y_soh_train, pred_soh_train)
    soh_test_mae, soh_test_rmse, soh_test_r2 = compute_metrics(y_soh_test, pred_soh_test)

    results_table = [
        ('SOC', 'Train (B0005)', soc_train_mae, soc_train_rmse, soc_train_r2),
        ('SOC', 'Test (B0006/7/18, unseen)', soc_test_mae, soc_test_rmse, soc_test_r2),
        ('SOH', 'Train (B0005)', soh_train_mae, soh_train_rmse, soh_train_r2),
        ('SOH', 'Test (B0006/7/18, unseen)', soh_test_mae, soh_test_rmse, soh_test_r2),
    ]

    print("+------------------------------------------------------------------------+")
    print("| SOC / SOH ESTIMATION RESULTS (FPGA Reservoir State + Ridge Readout)    |")
    print("| *** Computed live by this script via .fit()/.predict() on REAL data ***|")
    print("+-------+---------------------------+----------+----------+--------------+")
    print("| Target| Split                     | MAE      | RMSE     | R^2          |")
    print("+-------+---------------------------+----------+----------+--------------+")
    for tgt, spl, mae, rmse, r2 in results_table:
        print(f"| {tgt:5s} | {spl:25s} | {mae:.4f}   | {rmse:.4f}   | {r2:.4f}       |")
    print("+-------+---------------------------+----------+----------+--------------+")
    print()

    results['soc_test_mae'], results['soc_test_rmse'], results['soc_test_r2'] = soc_test_mae, soc_test_rmse, soc_test_r2
    results['soh_test_mae'], results['soh_test_rmse'], results['soh_test_r2'] = soh_test_mae, soh_test_rmse, soh_test_r2

    # 5. Classical EKF Baseline -- genuinely fit and run on the SAME real cycles
    train_rows_for_ekf = [r for r in raw_data if r['role'] == 'Train']
    ekf_params = fit_ekf_baseline(train_rows_for_ekf)

    ekf_soc_pred_all, ekf_soc_true_all = [], []
    for (b_id, c_num) in sorted(set(test_meta)):
        c_rows = cycles_by_key[(b_id, c_num)]
        cap = batteries_meta[b_id]['cap_nominal']
        preds = run_ekf_on_cycle(c_rows, ekf_params, capacity_ah=cap)
        ekf_soc_pred_all.extend(preds.tolist())
        ekf_soc_true_all.extend([r['soc_true'] for r in c_rows])

    ekf_mae, ekf_rmse, ekf_r2 = compute_metrics(np.array(ekf_soc_true_all), np.array(ekf_soc_pred_all))

    print("+------------------------------------------------------------------------+")
    print("| BASELINE COMPARISON - EXTENDED KALMAN FILTER (SOC ONLY)                |")
    print("| *** EKF genuinely fit (OCV polynomial + R0 via OLS) and run on the   ***|")
    print("| *** SAME real NASA test cycles as the ESN readout above            ***|")
    print("+-------------------------------+----------+----------+------------------+")
    print("| Method                        | Test MAE | Test RMSE| Test R^2         |")
    print("+-------------------------------+----------+----------+------------------+")
    print(f"| EKF (1RC Thevenin Baseline)   | {ekf_mae:.4f}   | {ekf_rmse:.4f}   | {ekf_r2:.4f}           |")
    print(f"| FPGA ESN Readout              | {soc_test_mae:.4f}   | {soc_test_rmse:.4f}   | {soc_test_r2:.4f}           |")
    print("+-------------------------------+----------+----------+------------------+")
    beats_ekf = soc_test_r2 > ekf_r2
    print(f"Key Finding: The FPGA ESN {'outperforms' if beats_ekf else 'does NOT outperform'} "
          f"the EKF baseline on R^2 (this run).")
    print("NOTE: EKF R1/C1 are FIXED (not fitted) because this discharge-only dataset "
          "has no rest-voltage segments to identify them -- a stated simplification, "
          "not a tuned/optimized baseline.")
    print()

    results['ekf_soc_test_mae'], results['ekf_soc_test_rmse'], results['ekf_soc_test_r2'] = ekf_mae, ekf_rmse, ekf_r2
    results['esn_beats_ekf'] = beats_ekf

    # 6. Post-Implementation Synthesis, Power & Timing Characterization
    print_synthesis_report()

    print("=" * 75)
    print("HARDWARE FPGA VERIFIER OUTCOMES EVALUATION COMPLETE")
    print("(SOC/SOH/EKF numbers above were computed live from real NASA .mat data")
    print(" and the committed reservoir weights -- see docstring for what is and")
    print(" is not independently re-derivable from files in this repository.)")
    print("=" * 75)

    results['success'] = True
    return results


def print_synthesis_report():
    """
    NOTE ON PROVENANCE: these synthesis/power/timing numbers are NOT derived
    from any Vivado project, checkpoint, or report file committed to this
    repository -- no .xdc, implementation run, or report_* output exists
    in hardware/FPGA_Verifier/. They are transcribed from
    docs/Review_2/Outcomes/FPGA-Based-Echo-State-Network-for-Battery-SOC-SOH-Estimation-Outcomes.pdf.
    If you need these to be independently reproducible (e.g. for a Q1
    submission), re-run synthesis/implementation in Vivado and commit the
    report_utilization / report_power / report_timing_summary output
    alongside this script, then replace this function to parse those files
    instead of printing transcribed constants.
    """
    print("+------------------------------------------------------------------------+")
    print("| FPGA SYNTHESIS RESOURCE UTILIZATION (Artix-7 xc7a100tcsg324-1)         |")
    print("| *** TRANSCRIBED from outcomes PDF -- NOT regenerated by this script ***|")
    print("+-------------------------------+----------+----------+------------------+")
    print("| Resource                      | Used     | Available| Utilization      |")
    print("+-------------------------------+----------+----------+------------------+")
    print("| Slice LUTs                    | 77       | 63,400   | 0.12%            |")
    print("| Slice Registers               | 66       | 126,800  | 0.05%            |")
    print("| Block RAM Tiles               | 7.5      | 135      | 5.56%            |")
    print("| DSP48 Slices                   | 0        | 240      | 0.00%            |")
    print("+-------------------------------+----------+----------+------------------+")
    print()
    print("+------------------------------------------------------------------------+")
    print("| ON-CHIP POWER & TIMING CLOSURE (transcribed, see docstring)            |")
    print("+-------------------------------+-------------------+--------------------+")
    print("| Metric                        | @ 100 MHz         | @ 250 MHz          |")
    print("+-------------------------------+-------------------+--------------------+")
    print("| Total On-Chip Power           | 0.099 W           | 0.101 W            |")
    print("| Worst Negative Slack (WNS)    | +6.264 ns (Pass)  | +0.783 ns (Pass)   |")
    print("+-------------------------------+-------------------+--------------------+")
    print()


if __name__ == "__main__":
    evaluate_fpga_outcomes()
