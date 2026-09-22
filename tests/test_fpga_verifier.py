import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

fpga_dir = os.path.join(root_dir, "hardware", "FPGA_Verifier")
if fpga_dir not in sys.path:
    sys.path.insert(0, fpga_dir)

from golden_model import (
    load_tanh_mem,
    run_tiny,
    to_hex_signed
)
from compare_results import load_csv


def test_tanh_lut_loading():
    lut = load_tanh_mem()
    assert len(lut) >= 5121
    # Check tanh(0) = 0
    assert lut[0] == 0
    # Check saturation near 5.0 (index 5120): tanh(5.0) ~ 1.0 -> 1024 (0x400)
    assert 1020 <= lut[5120] <= 1024


def test_to_hex_signed():
    assert to_hex_signed(0, 16) == "0000"
    assert to_hex_signed(396, 16) == "018c"
    assert to_hex_signed(-10, 16) == "fff6"
    assert to_hex_signed(-10, 18) == "3fff6"


def test_tiny_golden_model():
    records = run_tiny()
    assert len(records) == 6  # 3 timesteps * 2 neurons
    # Check pass 0 neuron 0 and 1 output values
    assert records[0]['pass'] == 0
    assert records[0]['neuron'] == 0
    assert records[0]['tanh_out'] == "01d9"
    assert records[1]['tanh_out'] == "030c"
    # Check pass 1
    assert records[2]['tanh_out'] == "03af"
    assert records[3]['tanh_out'] == "03e5"
    # Check pass 2
    assert records[4]['tanh_out'] == "03f7"
    assert records[5]['tanh_out'] == "03fd"


def test_full_model_golden_parity():
    golden_path = os.path.join(fpga_dir, "golden_results.csv")
    vivado_path = os.path.join(fpga_dir, "vivado_esn_results.csv")

    assert os.path.exists(golden_path), f"Missing {golden_path}"
    assert os.path.exists(vivado_path), f"Missing {vivado_path}"

    golden_map, golden_rows = load_csv(golden_path, default_key_pass='pass')
    vivado_map, vivado_rows = load_csv(vivado_path, default_key_pass='passbuf')

    assert len(golden_map) == 200
    assert len(vivado_map) == 200

    stages = ['mac', 'bias', 'sum', 'tanh_in', 'tanh_out']
    for k in golden_map.keys():
        assert k in vivado_map, f"Key {k} missing in vivado results"
        for stg in stages:
            g_val = golden_map[k][stg].strip().lower().lstrip('0') or '0'
            v_val = vivado_map[k][stg].strip().lower().lstrip('0') or '0'
            assert g_val == v_val, f"Mismatch at pass={k[0]} neuron={k[1]} stage={stg}: golden={g_val} vs vivado={v_val}"


def test_generate_reservoir_weights_seed42():
    from golden_model import generate_reservoir_weights
    Win_q, W_q, b_q, Win_f, W_f = generate_reservoir_weights(n_in=4, n_res=100, seed=42)
    assert Win_q.shape == (100, 4)
    assert W_q.shape == (100, 100)
    assert b_q.shape == (100,)
    assert (b_q == 0).all()


def test_nasa_dataset_generation():
    from eval_fpga_outcomes import generate_nasa_battery_dataset
    raw_data, meta = generate_nasa_battery_dataset()
    assert len(raw_data) == 2048  # 32 cycles * 64 timesteps
    assert set(meta.keys()) == {'B0005', 'B0006', 'B0007', 'B0018'}


def test_fpga_outcomes_evaluation():
    from eval_fpga_outcomes import evaluate_fpga_outcomes
    success = evaluate_fpga_outcomes()
    assert success is True

