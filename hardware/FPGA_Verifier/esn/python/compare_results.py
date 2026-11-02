#!/usr/bin/env python3
"""
compare_results.py
──────────────────
Automated bit-exact stage-by-stage verification tool.
Compares RTL simulation output (vivado_esn_results.csv) against the
Python Golden Reference Model (golden_results.csv or golden.csv).

Verifies bit-exact matches across all 5 datapath stages:
  1. MAC      (Q6.10 16-bit rounded MAC accumulator output)
  2. Bias     (Q6.10 16-bit signed bias term)
  3. Sum      (Q8.10 18-bit signed pre-clipped sum)
  4. Tanh_in  (Q6.10 16-bit clipped pre-activation [-5120, +5120])
  5. Tanh_out (Q6.10 16-bit post-LUT activation / state update)
"""

import csv
import os
import sys
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_csv(path, default_key_pass='pass', key_neuron='neuron'):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    rows = []
    with open(path, newline='', encoding='utf-8-sig') as f:
        r = csv.DictReader(f)
        for idx, row in enumerate(r):
            rows.append(row)

    # Determine key for pass / timestep
    sample = rows[0] if rows else {}
    if 'pass' in sample:
        key_pass = 'pass'
    elif 'timestep' in sample:
        key_pass = 'timestep'
    elif 'passbuf' in sample:
        key_pass = 'passbuf'
    else:
        key_pass = default_key_pass

    mapping = {}
    current_pass = 0
    last_neuron = -1

    for idx, row in enumerate(rows):
        neuron = int(row[key_neuron])
        # Detect sequential wrap-around if passbuf rolled over (e.g., 0, 1, 0, 1)
        if key_pass == 'passbuf':
            raw_pass = int(row['passbuf'])
            if idx > 0 and neuron == 0 and last_neuron > 0:
                current_pass += 1
            pass_val = current_pass
        else:
            pass_val = int(row[key_pass])

        last_neuron = neuron
        mapping[(pass_val, neuron)] = row

    return mapping, rows


def main():
    parser = argparse.ArgumentParser(description="Compare RTL Vivado ESN results against Golden Model")
    parser.add_argument("--golden", type=str, default=None, help="Path to golden CSV")
    parser.add_argument("--vivado", type=str, default=None, help="Path to vivado results CSV")
    parser.add_argument("--tiny", action="store_true", help="Compare tiny 2-neuron sequence results")
    parser.add_argument("--outcomes", action="store_true", help="Run full outcomes & dataset verification evaluation")
    args = parser.parse_args()

    if args.outcomes:
        from eval_fpga_outcomes import evaluate_fpga_outcomes
        evaluate_fpga_outcomes()
        sys.exit(0)


    # Determine golden file path
    if args.golden:
        golden_path = os.path.abspath(args.golden)
    elif args.tiny:
        golden_path = os.path.join(BASE_DIR, 'golden_tiny.csv')
        if not os.path.exists(golden_path):
            golden_script = os.path.join(BASE_DIR, 'golden_model.py')
            if os.path.exists(golden_script):
                import subprocess
                print(f"Generating tiny golden reference using {golden_script}...")
                subprocess.run([sys.executable, golden_script, "--tiny", "--out", "golden_tiny.csv"], check=True)
    else:
        candidates = [
            os.path.join(BASE_DIR, 'golden_results.csv'),
            os.path.join(BASE_DIR, 'golden.csv')
        ]
        golden_path = None
        for c in candidates:
            if os.path.exists(c):
                golden_path = c
                break
        if golden_path is None:
            golden_script = os.path.join(BASE_DIR, 'golden_model.py')
            if os.path.exists(golden_script):
                import subprocess
                print(f"Generating golden model reference using {golden_script}...")
                subprocess.run([sys.executable, golden_script, "--full", "--out", "golden_results.csv"], check=True)
                golden_path = candidates[0]

    # Determine vivado file path
    if args.vivado:
        vivado_path = os.path.abspath(args.vivado)
    elif args.tiny:
        vivado_path = os.path.join(BASE_DIR, 'vivado_tiny_results.csv')
    else:
        vivado_path = os.path.join(BASE_DIR, 'vivado_esn_results.csv')

    print("=" * 65)
    print("ESN HARDWARE VERIFIER: BIT-EXACT NUMERICAL COMPARISON")
    print("=" * 65)
    print(f"Golden Reference : {golden_path}")
    print(f"Vivado RTL Output: {vivado_path}")
    print("-" * 65)

    if not os.path.exists(golden_path):
        print(f"ERROR: Golden reference file not found at {golden_path}")
        sys.exit(1)

    if not os.path.exists(vivado_path):
        print(f"ERROR: Vivado results file not found at {vivado_path}")
        print("Run the testbench in Vivado/XSim to generate vivado_esn_results.csv.")
        sys.exit(1)

    golden, golden_raw = load_csv(golden_path, default_key_pass='pass', key_neuron='neuron')
    vivado, vivado_raw = load_csv(vivado_path, default_key_pass='passbuf', key_neuron='neuron')

    stages = ['mac', 'bias', 'sum', 'tanh_in', 'tanh_out']

    keys = sorted(golden.keys())
    common_keys = [k for k in keys if k in vivado]
    missing_in_vivado = [k for k in keys if k not in vivado]
    extra_in_vivado = [k for k in vivado.keys() if k not in golden]

    print(f"Total Golden rows  : {len(golden)}")
    print(f"Total Vivado rows  : {len(vivado)}")
    print(f"Matched evaluations: {len(common_keys)}")
    if missing_in_vivado:
        print(f"Missing in Vivado  : {len(missing_in_vivado)}")
    if extra_in_vivado:
        print(f"Extra in Vivado    : {len(extra_in_vivado)}")
    print()

    stopped_at = None
    all_matched = True

    for stage in stages:
        mismatches = []
        for k in common_keys:
            g = golden[k][stage].strip().lower().lstrip('0') or '0'
            v = vivado[k][stage].strip().lower().lstrip('0') or '0'
            if g != v:
                mismatches.append((k, golden[k][stage], vivado[k][stage]))

        total = len(common_keys)
        ok = total - len(mismatches)
        status = "ALL MATCH" if not mismatches else f"{len(mismatches)} MISMATCHES"
        print(f"[{stage.upper():8s}] {ok:4d}/{total:4d} matched  --  {status}")

        if mismatches:
            all_matched = False
            if stopped_at is None:
                stopped_at = stage
            for k, g_val, v_val in mismatches[:5]:
                print(f"           pass={k[0]} neuron={k[1]}: golden={g_val} vs vivado={v_val}")

    print("=" * 65)
    if all_matched and common_keys:
        print(f"SUCCESS: All {len(stages)} stages match bit-exactly across all {len(common_keys)} evaluations.")
        sys.exit(0)
    else:
        print(f"FAILED: Verification diverged at stage {stopped_at.upper() if stopped_at else 'COUNT_MISMATCH'}.")
        sys.exit(1)


if __name__ == "__main__":
    main()
