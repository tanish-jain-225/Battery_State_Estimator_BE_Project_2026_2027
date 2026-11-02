import os
import sys

import pytest

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

fpga_dir = os.path.join(root_dir, "hardware", "FPGA_Verifier")
if fpga_dir not in sys.path:
    sys.path.insert(0, fpga_dir)

from hardware.FPGA_Verifier.compare_results import load_csv
from hardware.FPGA_Verifier.golden_model import parse_coe_file, run_full, to_hex_signed


def test_parse_coe_radix10_and_16():
    """Verify parse_coe_file handles both radix 10 and radix 16 formats."""
    # Test existing bias_bram.coe
    bias_path = os.path.join(fpga_dir, "bias_bram.coe")
    if os.path.exists(bias_path):
        biases = parse_coe_file(bias_path)
        assert len(biases) == 100
        assert all(isinstance(b, int) for b in biases)

    # Test existing input_bram.coe
    input_path = os.path.join(fpga_dir, "input_bram.coe")
    if os.path.exists(input_path):
        inputs = parse_coe_file(input_path)
        assert len(inputs) == 256
        assert all(isinstance(val, int) for val in inputs)


def test_parse_coe_file_not_found():
    """Verify parse_coe_file raises FileNotFoundError for missing paths."""
    with pytest.raises(FileNotFoundError):
        parse_coe_file("non_existent_bram_file.coe")


def test_to_hex_signed_various_widths():
    """Verify signed two's-complement hex formatting for various bitwidths."""
    assert to_hex_signed(0, 16) == "0000"
    assert to_hex_signed(1, 16) == "0001"
    assert to_hex_signed(-1, 16) == "ffff"
    assert to_hex_signed(-1, 8) == "ff"
    assert to_hex_signed(255, 8) == "ff"
    assert to_hex_signed(-512, 16) == "fe00"


def test_run_full_golden_model_timesteps():
    """Verify run_full executes multi-timestep pipeline and returns records."""
    records = run_full(timesteps=2)
    # 2 timesteps * 100 neurons = 200 records
    assert len(records) == 200
    r0 = records[0]
    assert 'pass' in r0
    assert 'neuron' in r0
    assert 'tanh_out' in r0
    assert 'out_real' in r0
    assert r0['neuron'] == 0
    assert r0['pass'] == 0


def test_load_csv_missing_file():
    """Verify load_csv raises FileNotFoundError when given non-existent CSV path."""
    with pytest.raises(FileNotFoundError):
        load_csv("non_existent_results.csv")


def test_compare_golden_and_vivado_data():
    """Verify golden_results.csv and vivado_esn_results.csv load and match neuron count."""
    golden_path = os.path.join(fpga_dir, "golden_results.csv")
    vivado_path = os.path.join(fpga_dir, "vivado_esn_results.csv")

    g_map, g_rows = load_csv(golden_path, default_key_pass='pass')
    v_map, v_rows = load_csv(vivado_path, default_key_pass='passbuf')

    assert len(g_map) == 200
    assert len(v_map) == 200

    # Check that pass 0, neuron 0 matches exactly in tanh_out
    assert g_map[(0, 0)]['tanh_out'].strip().lower() == v_map[(0, 0)]['tanh_out'].strip().lower()


def test_compare_results_main_success(monkeypatch):
    """Verify compare_results.main() succeeds when comparing default golden and vivado files."""
    from hardware.FPGA_Verifier import compare_results
    monkeypatch.setattr(sys, "argv", ["compare_results.py"])
    with pytest.raises(SystemExit) as exc:
        compare_results.main()
    assert exc.value.code == 0


def test_compare_results_main_missing_golden(monkeypatch):
    """Verify compare_results.main() exits with code 1 if golden file is missing."""
    from hardware.FPGA_Verifier import compare_results
    monkeypatch.setattr(sys, "argv", ["compare_results.py", "--golden", "non_existent.csv", "--vivado", "vivado_esn_results.csv"])
    with pytest.raises(SystemExit) as exc:
        compare_results.main()
    assert exc.value.code == 1


def test_compare_results_main_outcomes(monkeypatch):
    """Verify compare_results.main() with --outcomes executes evaluation."""
    from hardware.FPGA_Verifier import compare_results
    monkeypatch.setattr(sys, "argv", ["compare_results.py", "--outcomes"])
    with pytest.raises(SystemExit) as exc:
        compare_results.main()
    assert exc.value.code == 0

