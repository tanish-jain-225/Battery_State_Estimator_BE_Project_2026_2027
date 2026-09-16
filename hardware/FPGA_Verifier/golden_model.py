#!/usr/bin/env python3
"""
golden_model.py
───────────────
Bit-exact Python Golden Reference Model for the FPGA-based Q6.10 ESN.

Simulates the exact RTL fixed-point datapath:
  - 16-bit signed Q6.10 multiplier (mult_q6_10.v)
  - 40-bit wide accumulator with round-half-up (mac_accum_q6_10.v)
  - Bias addition and [-5120, +5120] clipping (esn_neuron.v)
  - Symmetrical odd-parity tanh lookup table (tanh_lut.v using tanh.mem)

Supports both:
  1. --tiny : 2-input, 2-neuron, 3-timestep test matching tb_esn_top_tiny.v
  2. --full : 4-input, 100-neuron, multi-timestep test using active .coe files
"""

import os
import sys
import csv
import argparse
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TANH_MEM_PATH = os.path.join(BASE_DIR, "tanh.mem")


def to_hex_signed(val, nbits):
    """Formats signed integer into lower-case fixed-width hex."""
    mask = (1 << nbits) - 1
    ndigits = -(-nbits // 4)
    return format(int(val) & mask, 'x').zfill(ndigits)


def load_tanh_mem(filepath=TANH_MEM_PATH):
    """Loads 5121-entry tanh.mem lookup table."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"LUT file not found: {filepath}")
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    lut = [int(x, 16) for x in lines]
    if len(lut) < 5121:
        raise ValueError(f"tanh.mem incomplete: expected >= 5121 entries, found {len(lut)}")
    return lut


def parse_coe_file(filepath):
    """Parses Xilinx .coe memory initialization file (radix 10 or 16)."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"COE file not found: {filepath}")
    radix = 10
    values = []
    in_vector = False
    with open(filepath, 'r') as f:
        for line in f:
            clean = line.strip()
            if not clean or clean.startswith(';'):
                continue
            if 'memory_initialization_radix' in clean:
                radix_str = clean.split('=')[1].replace(';', '').strip()
                radix = int(radix_str)
                continue
            if 'memory_initialization_vector' in clean:
                in_vector = True
                vec_part = clean.split('=')[1].strip()
                tokens = vec_part.replace(';', '').replace(',', ' ').split()
                for tok in tokens:
                    if tok:
                        val = int(tok, radix)
                        if radix == 16 and val >= 32768:
                            val -= 65536
                        values.append(val)
                continue
            if in_vector:
                tokens = clean.replace(';', '').replace(',', ' ').split()
                for tok in tokens:
                    if tok:
                        val = int(tok, radix)
                        if radix == 16 and val >= 32768:
                            val -= 65536
                        values.append(val)
    return values


class GoldenESN:
    def __init__(self, n_in, n_res, Win, W, bias, lut=None):
        self.n_in = n_in
        self.n_res = n_res
        self.Win = np.array(Win, dtype=np.int64).reshape(n_res, n_in)
        self.W = np.array(W, dtype=np.int64).reshape(n_res, n_res)
        self.bias = np.array(bias, dtype=np.int64).reshape(n_res)
        self.lut = lut if lut is not None else load_tanh_mem()
        self.x = np.zeros(n_res, dtype=np.int64)

    def reset(self):
        self.x = np.zeros(self.n_res, dtype=np.int64)

    def step(self, u_vec, pass_idx):
        """
        Executes one timestep of the ESN matching RTL stage by stage.
        Returns a list of dicts for each neuron.
        """
        u_arr = np.array(u_vec, dtype=np.int64)
        x_old = self.x.copy()
        x_next = np.zeros(self.n_res, dtype=np.int64)
        records = []

        for i in range(self.n_res):
            # Accumulator in RTL is 40-bit signed
            acc = 0

            # Win.u products
            for k in range(self.n_in):
                acc += int(self.Win[i, k]) * int(u_arr[k])

            # W.x products
            for j in range(self.n_res):
                acc += int(self.W[i, j]) * int(x_old[j])

            # Round-half-up: (acc + 512) >>> 10
            rounded = (acc + (1 << 9)) >> 10
            # 16-bit saturation
            mac_result = max(-32768, min(32767, rounded))

            # Bias addition: 18-bit signed
            b_val = int(self.bias[i])
            neuron_sum = mac_result + b_val

            # Clipping to [-5120, +5120] ([-5.0, +5.0] in Q6.10)
            tanh_input = max(-5120, min(5120, neuron_sum))

            # Hardware tanh LUT
            sign = 1 if tanh_input < 0 else 0
            abs_addr = -tanh_input if sign else tanh_input
            rom_val = self.lut[abs_addr]

            # Interpret rom_val as signed 16-bit
            if rom_val >= 32768:
                rom_signed = rom_val - 65536
            else:
                rom_signed = rom_val

            tanh_output = -rom_signed if sign else rom_signed
            # Ensure within 16-bit signed
            tanh_output = max(-32768, min(32767, tanh_output))
            x_next[i] = tanh_output

            records.append({
                'pass': pass_idx,
                'neuron': i,
                'mac': to_hex_signed(mac_result, 16),
                'bias': to_hex_signed(b_val, 16),
                'sum': to_hex_signed(neuron_sum, 18),
                'tanh_in': to_hex_signed(tanh_input, 16),
                'tanh_out': to_hex_signed(tanh_output, 16),
                'mac_dec': mac_result,
                'bias_dec': b_val,
                'sum_dec': neuron_sum,
                'out_dec': tanh_output,
                'out_real': tanh_output / 1024.0
            })

        self.x = x_next
        return records


def run_tiny():
    print("=" * 60)
    print("RUNNING GOLDEN MODEL: TINY CONFIGURATION (N_IN=2, N_RES=2, T=3)")
    print("=" * 60)

    # Weights from tiny_bram_models.v
    Win = [
        [512, 0],
        [0, 512]
    ]
    W = [
        [205, 0],
        [0, 205]
    ]
    bias = [0, 0]

    u_seq = [
        [1024, 2048],  # u(0) = [1.0, 2.0]
        [3072, 4096],  # u(1) = [3.0, 4.0]
        [5120, 6144]   # u(2) = [5.0, 6.0]
    ]

    esn = GoldenESN(n_in=2, n_res=2, Win=Win, W=W, bias=bias)
    all_records = []

    for t in range(3):
        rec = esn.step(u_seq[t], pass_idx=t)
        all_records.extend(rec)
        vals = [f"{r['out_real']:.4f}" for r in rec]
        hexs = [f"0x{r['tanh_out']}" for r in rec]
        print(f"PASS {t+1} (t={t}): x({t+1}) = {vals}  [raw={hexs}]")

    return all_records


def run_full(timesteps=None):
    print("=" * 60)
    print("RUNNING GOLDEN MODEL: FULL CONFIGURATION (N_IN=4, N_RES=100)")
    print("=" * 60)

    win_raw = parse_coe_file(os.path.join(BASE_DIR, "win_bram.coe"))
    w_raw = parse_coe_file(os.path.join(BASE_DIR, "w_bram.coe"))
    bias_path = os.path.join(BASE_DIR, "bias.coe") if os.path.exists(os.path.join(BASE_DIR, "bias.coe")) else os.path.join(BASE_DIR, "bias_bram.coe")
    bias_raw = parse_coe_file(bias_path)
    input_raw = parse_coe_file(os.path.join(BASE_DIR, "input_bram.coe"))

    n_in = 4
    n_res = 100
    available_steps = len(input_raw) // n_in

    if timesteps is None or timesteps > available_steps:
        timesteps = available_steps

    print(f"Loaded {len(win_raw)} Win weights, {len(w_raw)} W weights, {len(bias_raw)} biases")
    print(f"Dataset has {available_steps} timesteps ({len(input_raw)} input values). Simulating {timesteps} steps.")

    Win = np.array(win_raw[:n_res * n_in]).reshape(n_res, n_in)
    W = np.array(w_raw[:n_res * n_res]).reshape(n_res, n_res)
    bias = np.array(bias_raw[:n_res])

    u_seq = []
    for t in range(timesteps):
        u_seq.append(input_raw[t * n_in : (t + 1) * n_in])

    esn = GoldenESN(n_in=n_in, n_res=n_res, Win=Win, W=W, bias=bias)
    all_records = []

    for t in range(timesteps):
        rec = esn.step(u_seq[t], pass_idx=t)
        all_records.extend(rec)
        if t < 5 or t == timesteps - 1:
            mean_state = np.mean([r['out_real'] for r in rec])
            print(f"PASS {t+1} (t={t}): 100 neurons updated, mean reservoir state = {mean_state:.4f}")

    return all_records


def save_csv(records, filename):
    filepath = os.path.join(BASE_DIR, filename)
    fieldnames = ['pass', 'neuron', 'mac', 'bias', 'sum', 'tanh_in', 'tanh_out']
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        w.writerows(records)
    print(f"Wrote {len(records)} golden records to {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Bit-exact Python Golden Model for ESN FPGA Verifier")
    parser.add_argument("--tiny", action="store_true", help="Run tiny test (2-in, 2-res, 3-steps)")
    parser.add_argument("--full", action="store_true", help="Run full test (4-in, 100-res, multi-steps)")
    parser.add_argument("--steps", type=int, default=None, help="Number of timesteps to simulate")
    parser.add_argument("--out", type=str, default=None, help="Output CSV filename")
    args = parser.parse_args()

    if args.tiny:
        records = run_tiny()
        out_file = args.out or "golden_tiny.csv"
        save_csv(records, out_file)
    else:
        # Default to full 100-neuron model
        records = run_full(timesteps=args.steps)
        out_file = args.out or "golden_results.csv"
        save_csv(records, out_file)
        if out_file == "golden_results.csv":
            save_csv(records, "golden.csv")
    print("Golden model execution complete.")


if __name__ == "__main__":
    main()
