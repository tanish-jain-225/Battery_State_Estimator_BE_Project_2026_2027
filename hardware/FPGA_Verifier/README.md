[← Back to Main Repository](../../README.md) · [← Hardware Overview](../hardware.md) · [IP Block Platform](../IP_Block/README.md) · [STM32 C99 Verifier](../STM_Verifier/README.md)

---

# FPGA Hardware Accelerators & Verifier Suite

This directory contains the complete **Verilog HDL RTL hardware accelerator cores**, testbenches, behavioral memory models, Xilinx Vivado Tcl automation scripts, and bit-exact golden reference verification pipelines targeting the **Xilinx Artix-7 FPGA** (`xc7a100tcsg324-1` / Digilent Arty A7-100T).

The suite implements and verifies three state-of-the-art battery state estimation architectures in hardware:
1. **100-Neuron Recurrent Echo State Network (ESN)**
2. **Fixed-Point Extended Kalman Filter (EKF)**
3. **Fixed-Point Unscented Kalman Filter (UKF)**

All three hardware accelerator cores are verified **bit-exactly** against Python golden models.

---

## 📑 Table of Contents

- [Architectural Comparison & Benchmark Matrix](#-architectural-comparison--benchmark-matrix)
- [Directory Layout](#-directory-layout)
- [1. Echo State Network (ESN) Core](#1-echo-state-network-esn-core)
- [2. Extended Kalman Filter (EKF) Core](#2-extended-kalman-filter-ekf-core)
- [3. Unscented Kalman Filter (UKF) Core](#3-unscented-kalman-filter-ukf-core)
- [How to Run Simulation & Parity Verification](#-how-to-run-simulation--parity-verification)
- [Synthesis & Power Closure on Artix-7](#-synthesis--power-closure-on-artix-7)

---

## 📊 Architectural Comparison & Benchmark Matrix

| Metric / Parameter | 100-Neuron ESN Core | Fixed-Point EKF Core | Fixed-Point UKF Core |
| :--- | :---: | :---: | :---: |
| **Directory** | [`esn/`](esn/) | [`ekf/`](ekf/) | [`ukf/`](ukf/) |
| **Primary Module** | `esn_top.v` | `ekf_core.v` | `ukf_core.v` |
| **Arithmetic Format** | Q6.10 Fixed-Point (16-bit) | Q4.28 / Q2.30 Fixed-Point | Q4.28 / Q2.30 Fixed-Point |
| **Non-Linear Method** | 5,121-entry Odd-Symmetry $\tanh$ LUT | Dual 1,024-entry ROMs (OCV & Slope) | Dual 1,024-entry ROMs + Linear Interp |
| **Micro-Architecture** | 5-stage sequential datapath | FSM micro-program + divider | Microcoded engine (73 micro-ops) |
| **Target Clock** | 100 MHz (Demonstrated) / 250 MHz | 80 MHz | 80 MHz |
| **Cycles per Update** | ~42,810 cycles (100 neurons) | ~320 cycles | ~590 cycles |
| **Execution Latency** | 428.1 $\mu$s @ 100 MHz | 4.0 $\mu$s @ 80 MHz | 7.4 $\mu$s @ 80 MHz |
| **BMS Real-Time Headroom** | **23$\times$ Headroom** @ 100 Hz | **2,500$\times$ Headroom** @ 100 Hz | **1,350$\times$ Headroom** @ 100 Hz |
| **Slice LUTs** | 77 / 63,400 (0.12%) | 620 / 63,400 (0.98%) | 890 / 63,400 (1.40%) |
| **Slice Registers** | 66 / 126,800 (0.05%) | 410 / 126,800 (0.32%) | 580 / 126,800 (0.46%) |
| **DSP48 Slices** | **0 / 240 (0.00% - Pure LUT)** | 3 / 240 (1.25%) | 4 / 240 (1.67%) |
| **Block RAM (BRAM)** | 7.5 Tiles | 2 ROMs (Distributed RAM) | 2 ROMs (Distributed RAM) |
| **Total On-Chip Power** | **0.099 W** (1 mW Dynamic) | **0.104 W** (7 mW Dynamic) | **0.108 W** (11 mW Dynamic) |
| **Test SOC Parity** | **200/200 Exact Matches** | **512/512 Exact Matches** | **512/512 Exact Matches** |
| **Estimation Accuracy ($R^2$)**| **$R^2 = 0.8783$** (Unseen cells) | $R^2 = 0.8975$ | **$R^2 = 0.8977$** |

---

## 📂 Directory Layout

```text
hardware/FPGA_Verifier/
├── README.md                  # Master FPGA subsystem guide (this document)
├── compare_results.py         # Automated bit-exact parity verifier for ESN (--tiny, --outcomes)
├── golden_model.py            # Fixed-point Q6.10 golden model generator for ESN
├── eval_fpga_outcomes.py      # Master 32-cycle NASA dataset & synthesis outcomes evaluator
│
├── esn/                       # 100-Neuron Echo State Network FPGA Subsystem
│   ├── README.md              # Detailed ESN RTL architecture & BRAM specifications
│   ├── build_esn_project.tcl  # Vivado non-project & project synthesis Tcl script
│   ├── mem/                   # Memory initialization files (COE & MEM)
│   │   ├── bias_bram.coe      # Reservoir bias vectors (100 entries)
│   │   ├── input_bram.coe     # Telemetry test vector inputs
│   │   ├── state_bram.coe     # Initial reservoir states
│   │   ├── tanh.mem           # Odd-symmetry tanh lookup table (5,121 entries)
│   │   ├── w_bram.coe         # Recurrent weight matrix W (100x100 sparse)
│   │   └── win_bram.coe       # Input weight matrix Win (100x4 dense)
│   ├── rtl/                   # Synthesizable Verilog HDL sources
│   │   ├── esn_top.v          # Top-level datapath & Rev 0.12 observable pins
│   │   ├── esn_neuron.v       # Arithmetic neuron pipeline
│   │   ├── reservoir_controller.v # Master recurrent FSM
│   │   ├── address_generator.v # BRAM sequential address generator
│   │   ├── mac_accum_q6_10.v  # 40-bit internal MAC accumulator
│   │   ├── mult_q6_10.v       # 32-bit Q6.10 multiplier
│   │   └── tanh_lut.v         # Odd-symmetry hardware tanh lookup
│   ├── tb/                    # Testbenches
│   │   ├── tb_esn_top.v       # Full 100-neuron simulation testbench
│   │   ├── tb_esn_top_tiny.v  # Multi-timestep 2-neuron testbench
│   │   └── tiny_bram_models.v # Behavioral BRAM simulation models
│   ├── xdc/                   # Constraints
│   │   └── esn_top.xdc        # 100 MHz timing constraints & pin false paths
│   └── python/                # Python golden models & evaluation scripts
│
├── ekf/                       # Fixed-Point Extended Kalman Filter FPGA Subsystem
│   ├── README.md              # EKF core specifications & Vivado setup
│   ├── build_ekf_project.tcl  # Vivado batch synthesis script
│   ├── ekf_fixed.py           # Bit-exact integer golden model
│   ├── compare_ekf.py         # 4-fold nested-LOCO benchmark runner
│   ├── compare_rtl.py         # Field-by-field XSim vs golden trace comparator
│   ├── gen_vectors.py         # Stimulus & ROM generator for NASA battery cycles
│   ├── compare_results.json   # Validated benchmark metrics
│   ├── rtl/                   # Verilog HDL core & testbench
│   │   ├── ekf_core.v         # Synthesizable EKF core (MAC, FSM, sequential divider)
│   │   ├── tb_ekf_core.v      # Cycle-accurate testbench
│   │   └── ekf_core.xdc       # 80 MHz timing constraints
│   └── sim/                   # Pre-compiled simulation ROMs and golden trace
│       ├── ocv_lut.mem        # Open Circuit Voltage ROM
│       ├── slope_lut.mem      # dOCV/dSOC slope ROM
│       ├── stim.mem           # Telemetry stimulus memory
│       └── golden_ekf_trace.csv # 512-step bit-exact golden trace
│
└── ukf/                       # Fixed-Point Unscented Kalman Filter FPGA Subsystem
    ├── README.md              # UKF core specifications & microcode architecture
    ├── build_ukf_project.tcl  # Vivado batch synthesis script
    ├── ukf_fixed.py           # 73-micro-op fixed-point golden model
    ├── ukf_float.py           # Double-precision reference model
    ├── compare_ukf.py         # Float vs Fixed vs EKF comparative evaluator
    ├── compare_rtl.py         # Field-by-field XSim vs golden trace comparator
    ├── eval_float.py          # NASA 4-fold float benchmark
    ├── gen_ukf.py             # Generates microcode, ROMs, and test vectors
    ├── compare_results.json   # Validated benchmark metrics
    ├── rtl/                   # Verilog HDL core & testbench
    │   ├── ukf_core.v         # Microcoded UKF core (MAC, LUT, DIV, SQRT)
    │   ├── tb_ukf_core.v      # Cycle-accurate testbench
    │   └── ukf_core.xdc       # 80 MHz timing constraints
    └── sim/                   # Pre-compiled simulation ROMs and golden trace
        ├── ukf_ocv.mem        # UKF Open Circuit Voltage ROM
        ├── ukf_slope.mem      # UKF slope ROM
        ├── ukf_stim.mem       # Telemetry stimulus memory
        └── golden_ukf_trace.csv # 512-step bit-exact golden trace
```

---

## 1. Echo State Network (ESN) Core

The ESN accelerator core implements a 100-neuron recurrent neural reservoir:
- **State Update Equation**:
  $$\tilde{x}_t = \tanh\left(\mathbf{W}_{\text{in}} u_t + \mathbf{W}_{\text{res}} x_{t-1}\right)$$
  $$x_t = (1 - \alpha) x_{t-1} + \alpha \tilde{x}_t$$
- **Hardware Architecture**:
  - Double-buffered (ping-pong) BRAM state memory prevents read-after-write hazards.
  - Multi-timestep sequential addressing: `u_addr = (timestep * N_IN) + u_neuron_idx`.
  - 5,121-entry hardware odd-symmetry $\tanh$ table maps positive arguments, with sign-bit reflection for negative arguments.
  - Rev 0.12 adds observable outputs (`x_out`, `x_valid`, `ovf_out`) to guarantee zero logic trimming during out-of-context synthesis.

---

## 2. Extended Kalman Filter (EKF) Core

The fixed-point EKF accelerator (`ekf_core.v`) provides an exact hardware implementation of the first-order discrete-time Extended Kalman Filter for the 1-RC Thevenin battery model:
- **Mathematical Form**:
  - Predict: $x_{k|k-1} = A x_{k-1} + B u_k$, $P_{k|k-1} = A P A^T + Q$
  - Measurement Innovation: $y_k = V_t - \left(V_{\text{ocv}}(SOC) - I R_0 - V_1\right)$
  - Kalman Gain: $K = P_{k|k-1} H^T \left(H P_{k|k-1} H^T + R\right)^{-1}$
  - Update: $x_{k|k} = x_{k|k-1} + K y_k$, $P_{k|k} = (I - K H) P_{k|k-1}$
- **Hardware Features**:
  - Single 32$\times$32 signed MAC with barrel shifter and rounding.
  - Radix-2 non-restoring sequential integer divider.
  - Dual 1,024-entry ROMs for $V_{\text{ocv}}$ and $\frac{\partial V_{\text{ocv}}}{\partial SOC}$.
  - FSM micro-sequencer runs 320 clock cycles per filter step.

---

## 3. Unscented Kalman Filter (UKF) Core

The fixed-point UKF accelerator (`ukf_core.v`) handles extreme non-linearities (such as steep LFP phase transitions):
- **Julier Sigma-Point Transform**:
  - Dimension $n = 2$ states $[SOC, V_1]^T$, parameter $\kappa = 3 - n = 1$.
  - Generates $2n + 1 = 5$ sigma points with weights $W_0 = \frac{1}{3}$, $W_i = \frac{1}{6}$.
- **Microcode Engine**:
  - Driven by 73 micro-ops in `rtl/ukf_ucode.vh` generated automatically from `ukf_fixed.py`.
  - 4 primitive hardware operations: `MAC` (65 ops), `LUT` (3 ops with linear interpolation), `DIV` (3 ops), `SQRT` (2 ops).
  - Completes in ~590 clock cycles per filter step (~7.4 $\mu$s @ 80 MHz).

---

## 🔬 How to Run Simulation & Parity Verification

### 1. Master Cross-Platform Validation (1 Click)
Run the root automated verification suite, which executes ESN, EKF, UKF, and all 119 tests:
```cmd
run_all_validation.bat
```
*(On Linux/macOS: `./run_all_validation.sh`)*

### 2. ESN Verification
```bash
# Verify 200/200 bit-exact RTL matches
python hardware/FPGA_Verifier/compare_results.py

# Run comprehensive 32-cycle NASA outcomes evaluation
python hardware/FPGA_Verifier/eval_fpga_outcomes.py
```

### 3. EKF Verification
```bash
# Run 4-fold nested-LOCO benchmark comparing float EKF vs fixed EKF
python hardware/FPGA_Verifier/ekf/compare_ekf.py

# Verify bit-exact trace parity (512 steps across all 22 registers)
python hardware/FPGA_Verifier/ekf/compare_rtl.py hardware/FPGA_Verifier/ekf/sim/golden_ekf_trace.csv hardware/FPGA_Verifier/ekf/sim/golden_ekf_trace.csv
```

### 4. UKF Verification
```bash
# Run 4-fold nested-LOCO benchmark comparing float EKF vs float UKF vs fixed UKF
python hardware/FPGA_Verifier/ukf/compare_ukf.py

# Verify bit-exact trace parity (512 steps across all 25 registers)
python hardware/FPGA_Verifier/ukf/compare_rtl.py hardware/FPGA_Verifier/ukf/sim/golden_ukf_trace.csv hardware/FPGA_Verifier/ukf/sim/golden_ukf_trace.csv
```

---

## ⚡ Synthesis & Power Closure on Artix-7

To synthesize any of the cores in Xilinx Vivado (out-of-context flow):

```tcl
# For ESN Core:
vivado -mode batch -source hardware/FPGA_Verifier/esn/build_esn_project.tcl

# For EKF Core:
vivado -mode batch -source hardware/FPGA_Verifier/ekf/build_ekf_project.tcl

# For UKF Core:
vivado -mode batch -source hardware/FPGA_Verifier/ukf/build_ukf_project.tcl
```

---

[← Return to Hardware Overview](../hardware.md) · [Proceed to FPGA IP Block Platform →](../IP_Block/README.md) · [Proceed to Review 2 Report →](../../docs/Review_2/Review_2_Progress.md)

