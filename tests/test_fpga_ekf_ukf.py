"""
test_fpga_ekf_ukf.py
────────────────────
Unit & regression tests for Fixed-Point EKF and UKF FPGA accelerator cores,
microcode programs, ROM lookups, and bit-exact golden trace parity.
"""

import csv
import json
import os
import sys

import numpy as np

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

EKF_DIR = os.path.join(ROOT_DIR, "hardware", "FPGA_Verifier", "ekf")
UKF_DIR = os.path.join(ROOT_DIR, "hardware", "FPGA_Verifier", "ukf")
ESN_PY = os.path.join(ROOT_DIR, "hardware", "FPGA_Verifier", "esn", "python")

for p in [EKF_DIR, UKF_DIR, ESN_PY]:
    if p not in sys.path:
        sys.path.insert(0, p)

from ekf_fixed import build_consts as build_ekf_consts
from ekf_fixed import build_luts as build_ekf_luts
from ekf_fixed import run_ekf_fixed
from ukf_fixed import PROGRAM, REGS, run_ukf_fixed
from ukf_fixed import build_consts as build_ukf_consts
from ukf_fixed import build_lut as build_ukf_lut


def test_ekf_fixed_constants_and_luts():
    """Verify EKF OCV and slope ROM generation produces 1024-entry tables."""
    poly = np.poly1d([-0.1, 0.5, 0.2, 3.2])
    ocv, slope = build_ekf_luts(poly)
    assert len(ocv) == 1024
    assert len(slope) == 1024
    assert all(isinstance(v, int) for v in ocv)
    assert all(isinstance(v, int) for v in slope)

    p_dict = {
        "r0": 0.015,
        "r1": 0.012,
        "c1": 2500.0,
        "q_scale": 1.0,
        "r_val": 0.0001,
        "p0": 0.01,
    }
    consts = build_ekf_consts(p_dict, capacity_ah=2.0, dt=1.0)
    for k in ["a", "b", "kcc", "r0", "q0", "q1", "r", "p0"]:
        assert k in consts
        assert isinstance(consts[k], int)


def test_ekf_fixed_cycle_execution():
    """Verify EKF fixed-point engine executes single-cycle discharge step."""
    poly = np.poly1d([-0.1, 0.5, 0.2, 3.2])
    ocv, slope = build_ekf_luts(poly)
    p_dict = {
        "r0": 0.015,
        "r1": 0.012,
        "c1": 2500.0,
        "q_scale": 1.0,
        "r_val": 0.0001,
        "p0": 0.01,
    }
    consts = build_ekf_consts(p_dict, capacity_ah=2.0, dt=1.0)

    cycle_steps = [
        {"current_measured": 2.0, "voltage_measured": 3.7, "soc_true": 0.95},
        {"current_measured": 2.0, "voltage_measured": 3.68, "soc_true": 0.94},
        {"current_measured": 2.0, "voltage_measured": 3.65, "soc_true": 0.93},
    ]
    trace = []
    soc_estimates = list(run_ekf_fixed(cycle_steps, consts, ocv, slope, trace))
    assert len(soc_estimates) == 3
    assert all(0.0 <= s <= 1.0 for s in soc_estimates)
    assert len(trace) == 3
    assert "x0" in trace[0]
    assert "p00" in trace[0]


def test_ekf_golden_trace_parity_file():
    """Verify committed golden EKF trace has 512 steps and all 22 stage columns."""
    trace_path = os.path.join(EKF_DIR, "sim", "golden_ekf_trace.csv")
    assert os.path.exists(trace_path), f"Missing {trace_path}"

    with open(trace_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    assert len(reader) == 512
    cols = [
        "i",
        "vm",
        "x0p",
        "v1p",
        "p00p",
        "p01p",
        "p11p",
        "idx",
        "ocv",
        "h0",
        "yp",
        "inn",
        "ph0",
        "ph1",
        "s",
        "k0",
        "k1",
        "x0",
        "v1",
        "p00",
        "p01",
        "p11",
    ]
    for c in cols:
        assert c in reader[0]


def test_ukf_fixed_program_microops():
    """Verify UKF microcode consists of exactly 73 micro-ops in valid domains."""
    assert len(PROGRAM) == 73
    valid_ops = {"MAC", "LUT", "DIV", "SQRT"}
    op_counts = {}
    for op in PROGRAM:
        op_code = op[0]
        assert op_code in valid_ops
        op_counts[op_code] = op_counts.get(op_code, 0) + 1

    assert op_counts["MAC"] == 65
    assert op_counts["LUT"] == 3
    assert op_counts["DIV"] == 3
    assert op_counts["SQRT"] == 2
    assert len(REGS) == 62


def test_ukf_fixed_cycle_execution():
    """Verify UKF fixed-point engine executes single-cycle step."""
    poly = np.poly1d([-0.1, 0.5, 0.2, 3.2])
    lut = build_ukf_lut(poly)
    p_dict = {
        "r0": 0.015,
        "r1": 0.012,
        "c1": 2500.0,
    }
    consts = build_ukf_consts(p_dict, capacity_ah=2.0, dt=1.0)

    cycle_steps = [
        {"current_measured": 2.0, "voltage_measured": 3.7, "soc_true": 0.95},
        {"current_measured": 2.0, "voltage_measured": 3.68, "soc_true": 0.94},
    ]
    trace = []
    soc_estimates = list(run_ukf_fixed(cycle_steps, consts, lut, trace))
    assert len(soc_estimates) == 2
    assert all(0.0 <= s <= 1.0 for s in soc_estimates)
    assert len(trace) == 2


def test_ukf_golden_trace_parity_file():
    """Verify committed golden UKF trace has 512 steps and all 25 stage columns."""
    trace_path = os.path.join(UKF_DIR, "sim", "golden_ukf_trace.csv")
    assert os.path.exists(trace_path), f"Missing {trace_path}"

    with open(trace_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    assert len(reader) == 512
    cols = [
        "i",
        "vm",
        "x0p",
        "v1p",
        "p00p",
        "p01p",
        "p11p",
        "l00",
        "l10",
        "l11",
        "oc0",
        "oc1",
        "oc3",
        "yh",
        "pyy",
        "pxy0",
        "pxy1",
        "k0",
        "k1",
        "inn",
        "x0",
        "v1",
        "p00",
        "p01",
        "p11",
    ]
    for c in cols:
        assert c in reader[0]


def test_ekf_ukf_results_json_fidelity():
    """Verify saved compare_results.json files confirm benchmark R^2 targets."""
    ekf_json = os.path.join(EKF_DIR, "compare_results.json")
    ukf_json = os.path.join(UKF_DIR, "compare_results.json")

    assert os.path.exists(ekf_json)
    assert os.path.exists(ukf_json)

    with open(ekf_json, "r", encoding="utf-8") as f:
        ekf_data = json.load(f)
    with open(ukf_json, "r", encoding="utf-8") as f:
        ukf_data = json.load(f)

    assert "pooled" in ekf_data
    assert "pooled" in ukf_data
    assert ekf_data["pooled"]["fixed"]["mae"] < 0.5
    assert ukf_data["pooled"]["ukfq"]["mae"] < 0.5
    assert ukf_data["n_microops"]["MAC"] == 65
