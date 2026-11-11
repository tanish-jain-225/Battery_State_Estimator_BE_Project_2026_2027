import csv
import json
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

ip_dir = os.path.join(root_dir, "hardware", "IP_Block")
host_dir = os.path.join(ip_dir, "host")
if ip_dir not in sys.path:
    sys.path.insert(0, ip_dir)
if host_dir not in sys.path:
    sys.path.insert(0, host_dir)

from esn_host import (  # noqa: E402
    Pack,
    load_csv,
    make_window,
    split_windows,
    trim_window,
    twin_window,
)


def test_ip_block_files_present():
    """Verify all critical IP Block v1.2 deliverables exist on disk."""
    required = [
        "component.xml",
        "esn_platform_top.bit",
        "RUN_COMMANDS.md",
        "CHANGELOG.md",
        os.path.join("rtl", "esn_axi_ip.v"),
        os.path.join("rtl", "esn_core.v"),
        os.path.join("rtl", "esn_core_fast.v"),
        os.path.join("rtl", "ekf_core.v"),
        os.path.join("rtl", "ukf_core.v"),
        os.path.join("rtl", "esn_platform.v"),
        os.path.join("rtl", "esn_platform_top.v"),
        os.path.join("mem", "tanh.mem"),
        os.path.join("xdc", "esn_platform_top.xdc"),
        os.path.join("scripts", "package_esn_ip.tcl"),
        os.path.join("scripts", "build_platform.tcl"),
        os.path.join("scripts", "regression.sh"),
        os.path.join("driver", "esn_ip.h"),
        os.path.join("driver", "esn_ip_example.c"),
        os.path.join("docs", "register_map.md"),
        os.path.join("docs", "uart_protocol.md"),
        os.path.join("docs", "regression_2026-11-11.txt"),
        os.path.join("verify", "golden_readout.csv"),
        os.path.join("host", "esn_host.py"),
        os.path.join("host", "reproduce_paper.py"),
        os.path.join("host", "replay_board.py"),
        os.path.join("host", "narma_board.py"),
        os.path.join("host", "train_pack.py"),
        os.path.join("host", "packs", "general_32cells", "pack.json"),
        os.path.join("test_data", "sim_fused_b47", "twin.json"),
    ]
    for fn in required:
        fp = os.path.join(ip_dir, fn)
        assert os.path.isfile(fp), f"Missing required IP_Block deliverable: {fn}"


def test_ip_block_component_xml_integrity():
    """Verify IP-XACT IEEE 1685 component.xml metadata and v1.2 RTL parameter interfaces."""
    xml_path = os.path.join(ip_dir, "component.xml")
    tree = ET.parse(xml_path)
    root = tree.getroot()
    xml_str = ET.tostring(root, encoding="utf-8").decode("utf-8")

    # Verify IP identification
    assert "esn_axi_ip" in xml_str
    assert "vesit.ac.in" in xml_str

    # Verify required standard AXI4 interfaces
    assert "s_axi" in xml_str
    assert "s_axis" in xml_str
    assert "m_axis" in xml_str
    assert "aclk" in xml_str
    assert "aresetn" in xml_str

    # Verify v1.2 RTL exposes scalable FAST/P/K generics & Rev 0.5 EKF fusion
    with open(os.path.join(ip_dir, "rtl", "esn_axi_ip.v"), "r", encoding="utf-8") as f:
        axi_rtl = f.read()
    assert "parameter FAST" in axi_rtl
    assert "parameter P" in axi_rtl
    assert "parameter K" in axi_rtl

    with open(os.path.join(ip_dir, "rtl", "ekf_core.v"), "r", encoding="utf-8") as f:
        ekf_rtl = f.read()
    assert "Rev 0.5" in ekf_rtl
    assert "z_valid" in ekf_rtl


def test_ip_block_pack_loading():
    """Verify v1.2 general & held-out packs load properly and satisfy fast-core ELL sparsity (K=24)."""
    general_dir = os.path.join(ip_dir, "host", "packs", "general_32cells")
    pack = Pack(general_dir)
    assert pack.nres == 100
    assert pack.nin == 4
    assert len(pack.win) == 400
    assert len(pack.w) == 10000
    assert len(pack.bias) == 100
    assert len(pack.ro_soc) == 101
    assert len(pack.ro_soh) == 101
    for lut in ("ekf_ocv", "ekf_slope", "ukf_ocv", "ukf_slope"):
        assert len(pack.luts[lut]) == 1024

    # Verify reservoir sparsity matches scalable fast-core constraint (<= K=24 nonzeros/row)
    w_mat = np.array(pack.w, dtype=np.int64).reshape(pack.nres, pack.nres)
    max_nnz_per_row = int((w_mat != 0).sum(axis=1).max())
    assert max_nnz_per_row <= 24


def test_ip_block_twin_pipeline_execution():
    """Verify end-to-end multi-observer v1.2 pipeline (ESN, EKF, UKF) on held-out cell B0047 & fusion vectors."""
    b47_pack_dir = os.path.join(ip_dir, "host", "packs", "heldout", "pack_B0047")
    pack = Pack(b47_pack_dir)
    csv_path = os.path.join(b47_pack_dir, "B0047_cycles.csv")
    data = load_csv(csv_path)
    wins = split_windows(data)
    assert len(wins) >= 1

    # Evaluate first trimmed discharge cycle with v1.2 window trimming rule
    _, win_raw = wins[0]
    win_trimmed, n_loaded = trim_window(win_raw)
    assert win_trimmed is not None and n_loaded >= 16
    w = make_window(win_trimmed, "1.0")
    tw = twin_window(pack, w, cap=w["capacity"])

    # Validate output vector dimensions and ranges
    assert len(tw["soc_esn"]) == 64
    assert len(tw["soc_ekf"]) == 64
    assert len(tw["soc_ukf"]) == 64

    # ESN SOC starts charged and ends depleted on held-out 4 deg C cell B0047
    esn_soc = tw["soc_esn"] / 16384.0
    assert 0.90 <= esn_soc[0] <= 1.05
    assert esn_soc[-1] < 0.15

    # SOH is reasonable capacity health ratio
    esn_soh = tw["soh"] / 16384.0
    assert 0.70 <= esn_soh <= 1.05

    # EKF and UKF track closely
    ekf_soc = np.array(tw["soc_ekf"])
    ukf_soc = np.array(tw["soc_ukf"])
    np.testing.assert_allclose(ekf_soc, ukf_soc, atol=0.01)

    # Verify v1.2 causal fused-EKF golden regression vectors
    with open(os.path.join(ip_dir, "test_data", "sim_fused_b47", "twin.json"), "r", encoding="utf-8") as f:
        fused_tw = json.load(f)
    assert fused_tw["nsteps"] == 1732
    assert len(fused_tw["soc_esn"]) == 1732
    assert len(fused_tw["soc_ekf"]) == 1732


def test_ip_block_golden_readout_parity():
    """Verify bit-exact golden readout matching hardware simulation expectations."""
    golden_path = os.path.join(ip_dir, "verify", "golden_readout.csv")
    with open(golden_path, "r", newline="", encoding="utf-8") as f:
        reader = list(csv.reader(f))

    assert len(reader) == 66  # Header + 64 steps + 1 SOH row
    assert reader[0][0] == "step"
    assert reader[0][1] == "soc_hex"

    # Step 0 initial SOC hex
    assert reader[1][0] == "0"
    assert reader[1][1] == "4042"

    # End-of-window SOH hex: 0x31ad (0.776184)
    assert reader[-1][0] == "SOH"
    assert reader[-1][1].lower() == "31ad"
