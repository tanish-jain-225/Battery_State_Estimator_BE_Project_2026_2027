import csv
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

ip_dir = os.path.join(root_dir, "hardware", "IP_Block")
if ip_dir not in sys.path:
    sys.path.insert(0, ip_dir)

from hardware.IP_Block.esn_host import (  # noqa: E402
    Pack,
    load_csv,
    make_window,
    split_windows,
    twin_window,
)


def test_ip_block_files_present():
    """Verify all critical IP block deliverables exist on disk."""
    required = [
        "component.xml",
        "esn_axi_ip.v",
        "esn_platform_top.v",
        "esn_platform_top.bit",
        "package_esn_ip.tcl",
        "build_platform.tcl",
        "esn_ip.h",
        "esn_ip_example.c",
        "pack.json",
        "golden_readout.csv",
        "B0018_fold_cycles.csv",
    ]
    for fn in required:
        fp = os.path.join(ip_dir, fn)
        assert os.path.isfile(fp), f"Missing required IP_Block deliverable: {fn}"


def test_ip_block_component_xml_integrity():
    """Verify IP-XACT IEEE 1685 component.xml packaging metadata and bus interfaces."""
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


def test_ip_block_pack_loading():
    """Verify Pack loader correctly reads weights, biases, and lookup tables."""
    pack = Pack(ip_dir)
    assert pack.nres == 100
    assert pack.nin == 4
    assert len(pack.win) == 400
    assert len(pack.w) == 10000
    assert len(pack.bias) == 100
    assert len(pack.ro_soc) == 101
    assert len(pack.ro_soh) == 101
    for lut in ("ekf_ocv", "ekf_slope", "ukf_ocv", "ukf_slope"):
        assert len(pack.luts[lut]) == 1024


def test_ip_block_twin_pipeline_execution():
    """Verify end-to-end multi-observer pipeline (ESN, EKF, UKF) on NASA discharge cycles."""
    pack = Pack(ip_dir)
    csv_path = os.path.join(ip_dir, "B0018_fold_cycles.csv")
    data = load_csv(csv_path)
    wins = split_windows(data)
    assert len(wins) >= 1

    # Evaluate cycle 0
    cycle_name, win_data = wins[0]
    w = make_window(win_data, "1.0")
    tw = twin_window(pack, w, cap=2.0)

    # Validate output vector dimensions and ranges
    assert len(tw["soc_esn"]) == 64
    assert len(tw["soc_ekf"]) == 64
    assert len(tw["soc_ukf"]) == 64

    # ESN SOC starts charged and ends depleted
    esn_soc = tw["soc_esn"] / 16384.0
    assert 0.90 <= esn_soc[0] <= 1.05
    assert esn_soc[-1] < 0.20

    # SOH is reasonable capacity health ratio
    esn_soh = tw["soh"] / 16384.0
    assert 0.70 <= esn_soh <= 1.05

    # EKF and UKF track closely
    ekf_soc = np.array(tw["soc_ekf"])
    ukf_soc = np.array(tw["soc_ukf"])
    np.testing.assert_allclose(ekf_soc, ukf_soc, atol=0.01)


def test_ip_block_golden_readout_parity():
    """Verify bit-exact golden readout matching hardware simulation expectations."""
    golden_path = os.path.join(ip_dir, "golden_readout.csv")
    with open(golden_path, "r", newline="") as f:
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
