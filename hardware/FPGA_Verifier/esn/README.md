[← Back to FPGA Verifier Overview](../README.md)

# 100-Neuron Echo State Network (ESN) Hardware Subsystem

This directory contains the Verilog HDL RTL datapath, behavioral BRAM memory models, Vivado constraints, synthesis scripts, and Python verification models for the **100-Neuron Echo State Network (ESN)** hardware accelerator targeting the **Xilinx Artix-7 FPGA** (`xc7a100tcsg324-1`).

---

## 📑 Table of Contents

- [Architectural Specifications](#architectural-specifications)
- [Module Hierarchy](#module-hierarchy)
- [Memory Layout & COE Initialization](#memory-layout--coe-initialization)
- [Observable Synthesis Datapath (Rev 0.12)](#observable-synthesis-datapath-rev-012)
- [Running Vivado Behavioral Simulation](#running-vivado-behavioral-simulation)
- [Bit-Exact Parity Audit Results](#bit-exact-parity-audit-results)

---

## ⚡ Architectural Specifications

- **Reservoir Dimension**: $N = 100$ recurrent neurons
- **Input Dimensionality**: $M = 4$ telemetry features (`voltage_measured`, `current_measured`, `temperature_measured`, `current_load`)
- **Arithmetic Precision**: Q6.10 signed fixed-point (1 sign bit, 5 integer bits, 10 fractional bits)
- **Spectral Radius**: $\rho = 0.900$ (rescaled from Gaussian initialization, 10% connection density)
- **Leak Rate**: Leaky integration with parameter $\alpha = 0.3$
- **Non-Linearity**: 5,121-entry hardware odd-symmetry $\tanh$ lookup table (stored in `tanh.mem`)
- **Memory Buffering**: Ping-pong double-buffered BRAM state memory prevents Gauss-Seidel hazards

---

## 🏗️ Module Hierarchy

```text
esn/
├── build_esn_project.tcl       # Automated Vivado project & synthesis script
├── xdc/
│   └── esn_top.xdc             # 100 MHz clock & I/O false path timing constraints
├── mem/
│   ├── bias_bram.coe           # 100-element reservoir bias vector (zero vector)
│   ├── input_bram.coe          # 256-word telemetry stimulus memory (64 steps * 4 features)
│   ├── state_bram.coe          # Initial reservoir state memory
│   ├── tanh.mem                # 5,121-entry Q6.10 tanh lookup table
│   ├── w_bram.coe              # 100x100 sparse recurrent weight matrix
│   └── win_bram.coe            # 100x4 dense input weight matrix
├── rtl/
│   ├── esn_top.v               # Top-level module with Rev 0.12 observable pins
│   ├── esn_neuron.v            # Single neuron pipeline datapath & arithmetic core
│   ├── reservoir_controller.v  # Master sequential recurrent state machine
│   ├── address_generator.v     # BRAM address indexing generator
│   ├── mac_accum_q6_10.v       # 40-bit internal MAC accumulator with overflow clamping
│   ├── mult_q6_10.v            # Q6.10 fixed-point multiplier (32-bit exact product)
│   └── tanh_lut.v              # Odd-symmetry hardware tanh lookup ROM
├── tb/
│   ├── tb_esn_top.v            # Master 100-neuron testbench for Vivado XSim
│   ├── tb_esn_top_tiny.v       # 2-neuron multi-timestep testbench
│   └── tiny_bram_models.v      # Behavioral BRAM models for standalone simulation
└── python/
    ├── compare_results.py      # Automated stage-by-stage bit-exact comparator
    ├── golden_model.py         # Bit-exact Python fixed-point reference model
    ├── eval_fpga_outcomes.py   # Comprehensive 32-cycle NASA outcomes evaluation
    ├── real_ekf_baseline.py    # 1RC Thevenin EKF comparison baseline
    └── real_nasa_dataset.py    # NASA Ames battery telemetry loader & fallback
```

---

## 💾 Memory Layout & COE Initialization

The ESN accelerator loads pre-trained fixed-point weights and activation tables from Xilinx `.coe` and `.mem` memory files:

1. **`win_bram.coe`**: Holds the $100 \times 4$ input projection matrix $\mathbf{W}_{\text{in}}$. Each row contains 4 Q6.10 16-bit words.
2. **`w_bram.coe`**: Holds the $100 \times 100$ sparse recurrent matrix $\mathbf{W}_{\text{res}}$. Compressed to non-zero connections for resource savings.
3. **`bias_bram.coe`**: Holds the 100 reservoir bias values in Q6.10.
4. **`tanh.mem`**: Contains 5,121 hex words representing $\tanh(x)$ for $x \in [0, 5.0]$ with step $\Delta x = \frac{1}{1024}$. Negative inputs utilize odd symmetry:
   $$\tanh(-x) = -\tanh(x)$$

---

## 🔍 Observable Synthesis Datapath (Rev 0.12)

In Revision 0.12, the top-level module `esn_top.v` exposes internal datapath pins to prevent Vivado from trimming arithmetic registers during out-of-context synthesis:

```verilog
module esn_top (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,
    output wire                 done,
    // Rev 0.12: observable datapath outputs
    output wire signed [DW-1:0] x_out,    // x_i(t+1), valid when x_valid = 1
    output wire                 x_valid,  // high on cycle state is committed
    output wire                 ovf_out   // MAC saturation flag
);
```

---

## 🚀 Running Vivado Behavioral Simulation

To run behavioral simulation in Xilinx Vivado:

```bash
# Generate the full golden CSV reference
python hardware/FPGA_Verifier/golden_model.py --full --out hardware/FPGA_Verifier/golden_results.csv

# Launch Vivado XSim with tb_esn_top
vivado -mode batch -source hardware/FPGA_Verifier/esn/build_esn_project.tcl

# Compare results bit-exactly
python hardware/FPGA_Verifier/compare_results.py
```

---

## 📈 Bit-Exact Parity Audit Results

Across 200 stage evaluations (2 complete passes of the 100-neuron reservoir):

- **MAC Stage**: 200 / 200 matched (100.0%)
- **Bias Stage**: 200 / 200 matched (100.0%)
- **Sum Stage**: 200 / 200 matched (100.0%)
- **Tanh_in Stage**: 200 / 200 matched (100.0%)
- **Tanh_out Stage**: 200 / 200 matched (100.0%)

**Final Parity Verification: 100% BIT-EXACT MATCH (0 ERRORS)**.

