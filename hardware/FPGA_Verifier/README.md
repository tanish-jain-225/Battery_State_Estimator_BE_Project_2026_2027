[← Back to README](../../README.md) · [← Back to Hardware](../hardware.md)

# FPGA-Based Q6.10 Echo State Network

## Current Status

A fixed-point Echo State Network has been implemented in Verilog and verified using Vivado/XSim and Python reference models.

### Architecture

- **Input dimension ($N_{IN}$)**: 4 (Full model) / 2 (Tiny model)
- **Reservoir size ($N_{RES}$)**: 100 (Full model) / 2 (Tiny model)
- **Sequence steps ($T_{MAX}$)**: 64 (Full battery dataset) / 3 (Tiny test)
- **Fixed-point format**: Q6.10 signed (16-bit word, 10 fraction bits)
- **Datapath Pipeline**:
  $$\text{Win} \cdot u + W \cdot x \text{ MAC} \longrightarrow \text{Bias Addition} \longrightarrow \text{Saturation Clipping} \longrightarrow \text{Tanh LUT}$$
- **Memory Architecture**: Double-buffered (ping-pong) dual-port BRAM state memory ensuring synchronous $x(k+1) = \tanh(W x(k) + \text{Win} u(k) + b)$ updates.

---

## Verification Suite

The RTL is verified against an independent, bit-exact Python golden reference model ([`golden_model.py`](golden_model.py)).

### 1. Tiny Sequence Verification (`tb_esn_top_tiny.v`)
- Tests sequence processing across 3 distinct sequential inputs $u(0) \to u(1) \to u(2)$ on a 2-neuron network using behavioral memory models ([`tiny_bram_models.v`](tiny_bram_models.v)).
- Confirms multi-timestep sequence address indexing (`u_addr = timestep * N_IN + feature_idx`).
- Bit-exact numerical outputs verified:
  - **Pass 1 ($t=0$)**: $x(1) = [0.4619, 0.7617]$
  - **Pass 2 ($t=1$)**: $x(2) = [0.9209, 0.9736]$
  - **Pass 3 ($t=2$)**: $x(3) = [0.9912, 0.9971]$

### 2. Full 100-Neuron Model Verification (`tb_esn_top.v`)
- Evaluates full 100-neuron reservoir updates using active BRAM initialization files (`win_bram.coe`, `w_bram.coe`, `bias_bram.coe`, `input_bram.coe`).
- Stage-by-stage bit-exact matching:
  - MAC Stage: 100% matched
  - Bias Stage: 100% matched
  - Sum Stage: 100% matched
  - Tanh Input / Output Stages: 100% matched

---

## Project Structure

```text
hardware/FPGA_Verifier/
│
├── README.md                      # FPGA module documentation
│
├── RTL (Verilog HDL):
│   ├── esn_top.v                  # Top-level Verilog ESN wrapper with multi-timestep support
│   ├── esn_neuron.v               # Single neuron datapath module & FSM
│   ├── reservoir_controller.v     # Recurrent execution state machine
│   ├── address_generator.v        # Memory base address generator
│   ├── mac_accum_q6_10.v          # Q6.10 fixed-point MAC accumulator (40-bit internal)
│   ├── mult_q6_10.v               # Q6.10 fixed-point multiplier (32-bit exact product)
│   └── tanh_lut.v                 # Hardware odd-symmetry tanh LUT
│
├── Testbenches:
│   ├── tb_esn_top_tiny.v          # 2-input, 2-neuron, 3-timestep sequence verification
│   ├── tiny_bram_models.v         # Behavioral BRAM models for tiny simulation
│   └── tb_esn_top.v               # Full 100-neuron testbench
│
├── Memory Files:
│   ├── input_bram.coe             # Real NASA B0005 battery dataset (64 steps x 4 features, Radix 10)
│   ├── win_bram.coe               # Input weight matrix (Radix 10)
│   ├── w_bram.coe                 # Recurrent weight matrix (Radix 10)
│   ├── bias_bram.coe              # Bias vector (Radix 10)
│   ├── state_bram.coe             # Initial state conditions (Radix 10)
│   └── tanh.mem                   # 5,121-entry Q6.10 tanh lookup table
│
└── Python Verification:
    ├── golden_model.py            # Dynamic, bit-exact golden reference generator (--tiny / --full)
    ├── compare_results.py         # Automated bit-exact parity verifier
    ├── golden_results.csv         # Generated reference outputs
    └── vivado_esn_results.csv     # Vivado / XSim simulation outputs
```

---

## Running Verification

### Step 1: Generate Golden Reference
```bash
# For Tiny Test (tb_esn_top_tiny)
python golden_model.py --tiny

# For Full 100-Neuron Model (up to 64 steps)
python golden_model.py --full --steps 64
```

### Step 2: Compare Vivado Simulation Output
```bash
# For Full 100-Neuron Model (default)
python compare_results.py

# For Tiny Test Model
python compare_results.py --tiny
```
