[← Back to README](../README.md)

# Hardware Subsystem

This document provides a technical guide to the hardware subsystem, covering both the **C99 Embedded Microcontroller Firmware** (CSR matrix representation, fixed-point math, MCU pinouts) and the **Verilog HDL FPGA Hardware Verifier** targeting the **ARTIX A7100T FPGA** ([`FPGA_Verifier/README.md`](FPGA_Verifier/README.md)).

> [!IMPORTANT]
> **Project Scope & Feasibility Validation**: The primary deliverable of this project is a data-driven ESN estimator (software-validated for SOC/SOH), not a physical hardware product. The embedded C99 firmware and Verilog FPGA RTL modules serve strictly as a **testing and verification platform** to prove that the reservoir-computing execution pipeline is deployable under strict memory and computational constraints.

---

## 📑 Table of Contents
1. [Hardware Subsystem Overview](#hardware-subsystem-overview)
2. [Hardware Folder Structure](#-hardware-folder-structure)
3. [FPGA Verilog ESN Verifier (ARTIX A7100T Target)](#-fpga-verilog-esn-verifier-artix-a7100t-target)
4. [ESN Classifier Interface Specifications](#-esn-classifier-interface-specifications)
5. [Embedded Optimizations (C99 Firmware)](#-embedded-optimizations)
6. [Offline Model Export Pipeline](#️-offline-model-export-pipeline)
7. [Hardware Wiring & Pinout Reference](#-hardware-wiring--pinout-reference)
8. [Running the Desktop Verification Simulator](#-running-the-desktop-verification-simulator)

---

## 📂 Hardware Folder Structure

The layout below maps out the key modules within the hardware directory:

```text
hardware/
├── hardware.md                                  # This hardware documentation
├── STM_Verifier/                                # C99 embedded firmware and training scripts
│   ├── main.c                                   # C99 classifier runtime & test simulation
│   ├── main.h                                   # Host-side HAL shims & microcontroller config
│   ├── train.py                                 # Core ESN Python implementation
│   ├── train_classifier.py                      # Trains the 3-class ESN & exports C weights
│   ├── train_estimator.py                       # Trains the SOC/SOH ESN & exports weights
│   ├── config.py                                # Dimensions, thresholds and dataset settings
│   ├── esn_classifier_weights.h                 # Generated sparse classifier weight arrays
│   ├── esn_estimator_weights.h                  # Generated sparse estimator weight arrays
│   ├── original_ev_battery_dataset_multiclass.csv   # Synthesized multiclass drive-cycle data
│   ├── run_c_simulator.bat                      # Windows build-and-run script
│   └── run_c_simulator.sh                       # Linux/macOS build-and-run script
└── FPGA_Verifier/                               # Verilog RTL FPGA verification module
    ├── README.md                                # FPGA module documentation
    ├── esn_top.v                                # Top-level Verilog ESN wrapper
    ├── esn_neuron.v                             # Neuron datapath module
    ├── reservoir_controller.v                   # Recurrent execution state machine
    ├── address_generator.v                      # Memory address indexing logic
    ├── mac_accum_q6_10.v                        # Q6.10 fixed-point MAC accumulator
    ├── mult_q6_10.v                             # Q6.10 fixed-point multiplier
    ├── tanh_lut.v                               # Hardware tanh lookup table module
    ├── tb_esn_top.v                             # Testbench for Vivado / XSim simulation
    ├── golden.py                                # Independent Python golden reference model
    └── compare_results.py                       # Verifies Vivado CSV output against golden model
```

---

## ⚡ FPGA Verilog ESN Verifier (ARTIX A7100T Target)

The hardware subsystem includes a fully verified Verilog HDL Echo State Network targeting the **ARTIX A7100T FPGA** platform:

### RTL Design Specifications
- **Reservoir Size**: 100 neurons ($N=100$)
- **Input Dimension**: 4 features ($M=4$)
- **Fixed-Point Data Format**: Q6.10 fixed point (6 integer bits, 10 fractional bits)
- **Pipeline Stages**: $\text{Win}\cdot u + W\cdot x \text{ MAC} \rightarrow \text{bias addition} \rightarrow \text{saturation clipping} \rightarrow \text{tanh LUT}$
- **Memory Architecture**: BRAM-based weight and state storage with double-buffered recurrent reservoir state memory.
- **Activation Function**: Hardware odd-symmetry $\tanh$ lookup table (LUT, positive half only).

### Verification Results
Tested via two-pass recurrent state transitions ($x(0)\rightarrow x(1)$ and $x(1)\rightarrow x(2)$) in **Vivado / XSim**:
- **Total Neuron Updates Evaluated**: 200
- **MAC Stage**: 200 / 200 matched
- **Bias Stage**: 200 / 200 matched
- **Sum Stage**: 200 / 200 matched
- **Tanh Input/Output Stages**: 200 / 200 matched
- **Result**: **100% bit-exact match between Vivado XSim simulation and Python golden reference.**

---

## 📈 ESN Classifier Interface Specifications

### Input Vector
The edge classifier consumes a 3-element time-series telemetry frame at each timestep:
$$u_t = [\text{Terminal Voltage (V)}, \text{Load Current (I)}, \text{Cell Temperature (T)}]^T$$

### Output Class Diagnostic Safety States
The network classifies inputs into three safety zones matching the status LED on Pin `PA5`:

| Diagnostic Class ID | State Name | Temperature Condition | GPIO `PA5` LED State |
| :---: | :--- | :--- | :--- |
| **`0`** | Normal | $T < 35\text{ }^\circ\text{C}$ | **LED OFF** |
| **`1`** | Warning | $35\text{ }^\circ\text{C} \le T < 45\text{ }^\circ\text{C}$ | **LED BLINKING** (1 Hz) |
| **`2`** | Critical | $T \ge 45\text{ }^\circ\text{C}$ | **LED STEADY ON** |

---

## ⚡ Embedded Optimizations

Low-power microcontrollers (such as an ARM Cortex-M4 or M7) have strict constraints on processing speed and memory size. To deploy an Echo State Network on the edge, we implement two primary optimizations in [`STM_Verifier/main.c`](STM_Verifier/main.c).

### A. Compressed Sparse Row (CSR) Sparse Matrix-Vector Multiplication (SpMV)
A dense recurrent weight matrix $\mathbf{W}_{\text{res}}$ of size $50 \times 50$ requires $2,500$ multiplications. By introducing $85\%$ sparsity during reservoir generation ($\mathbf{W}_{\text{res}}$ entries set to zero), non-zero elements (NNZ) reduce to only $375$ operations.

To save RAM and bypass multiplication by zero, we compress $\mathbf{W}_{\text{res}}$ using CSR representation into three 1D arrays:
1. `val`: Storing non-zero float values (size = NNZ).
2. `col`: Storing the column index of each non-zero element (size = NNZ).
3. `row_ptr`: Storing index offsets in `val` and `col` where each row begins (size = $N_{\text{reservoir}} + 1$).

#### 📊 CSR Example Visualization
Consider a simple $3 \times 3$ sparse matrix with $3$ non-zero elements (NNZ = 3):
```text
Dense Matrix (W_res):
[  0.0   -0.45    0.0  ]  -> Row 0 contains -0.45 at Col 1
[  0.81    0.0     0.0  ]  -> Row 1 contains 0.81 at Col 0
[  0.0     0.0    0.32  ]  -> Row 2 contains 0.32 at Col 2

Compressed Sparse Row Arrays:
val     = [ -0.45,  0.81,  0.32 ]   # Holds all non-zero values
col     = [     1,     0,     2 ]   # Holds column indices of those values
row_ptr = [  0,  1,  2,  3 ]        # Marks index boundaries of rows (0 to 1, 1 to 2, 2 to 3)
```

The Sparse Matrix-Vector multiplication (SpMV) loop in C99 is written as:
```c
for (int i = 0; i < N_RESERVOIR; i++) {
    float sum = bias_input_terms[i];
    uint16_t start = row_ptr[i];
    uint16_t end = row_ptr[i + 1];
    for (uint16_t k = start; k < end; k++) {
        sum += val[k] * x[col[k]];
    }
    arg[i] = sum;
}
```

### B. Fixed-Point Q12/Q15 Arithmetic
To support low-power microcontrollers lacking a floating-point unit (FPU), the inference code can run using pure integer calculations:
- **Quantization Scaling**:
  - Inputs are scaled to Q12 format ($S_{\text{in}} = 2^{12} = 4096$).
  - Weights and reservoir states are stored in Q15 format ($S_{\text{weights}} = 2^{15} = 32768$).
- **Fixed-Point Tanh Lookup Table**:
  Instead of compiling costly floating-point transcendental library math (`tanhf`), a 33-point lookup table maps inputs from $[0, 1]$ in Q15 format. Values are resolved via linear interpolation:
  $$\text{frac} = |x_{\text{Q15}}| \pmod{1024}$$
  $$\text{index} = |x_{\text{Q15}}| \gg 10$$
  $$\tanh(x_{\text{Q15}}) = \text{sign}(x_{\text{Q15}}) \cdot \frac{(1024 - \text{frac}) \cdot \text{LUT}[\text{index}] + \text{frac} \cdot \text{LUT}[\text{index} + 1]}{1024}$$

---

## 🛠️ Offline Model Export Pipeline

To retrain the ESN models and export updated header configurations, run:

```bash
# Trains classification model and generates esn_classifier_weights.h
python hardware/STM_Verifier/train_classifier.py
# Run with hyperparameter grid search:
python hardware/STM_Verifier/train_classifier.py --grid-search

# Trains estimator model and generates esn_estimator_weights.h
python hardware/STM_Verifier/train_estimator.py
# Run with hyperparameter grid search:
python hardware/STM_Verifier/train_estimator.py --grid-search
```

* **Unified 3-Tier Data Fallback**: Hardware training scripts independently execute the identical 3-tier data loading logic (`Doc Link Data` via `CSV_URL` $\rightarrow$ `Previously Loaded Data` $\rightarrow$ `Local Trained File Data` via `CSV_FILE` / simulator generator), ensuring perfect data parity with the software web visualizer.
* **Grid Search**: Adding the `--grid-search` switch triggers a programmatic sweep over spectral radii, leak rates and regularization penalties, selecting parameters that optimize validation classification accuracy or minimize SOC/SOH RMSE.

---

## 🔌 Hardware Wiring & Pinout Reference

When deploying to a physical STM32 Nucleo board (e.g., STM32F401RE / STM32F446RE), connect the peripherals according to the pinout schematic below:

```text
               +-------------------------------------------+
               |              STM32 NUCLEO BOARD           |
               |                                           |
               |      [ PA2 ] ------------------> TX       | --> UART2 Serial Output
               |      [ PA3 ] <------------------ RX       |     (115200 Baud, 8N1)
               |                                           |
               |      [ PA5 ] ----[ R_220 ]----( LED )--+  | --> Status LED Output
               |                               |           |     (Blinks/ON for Warnings)
               |                               GND         |
               |                                           |
               |      [ PC0 ] <--------- Analog Input      | --> Optional ADC Channel 
               |                         (Cell Temp / Volt)|     for real-world sensors
               |                                           |
               |      [ GND ] --------------------------   | --> Common Ground Reference
               +-------------------------------------------+
```

### Pin Description Table

| Pin Name | Function | Direction | Electrical Specification | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`PA2`** | `USART2_TX` | Output | 3.3V Logic | Diagnostic telemetry transmitter |
| **`PA3`** | `USART2_RX` | Input | 3.3V Logic | Control command receiver |
| **`PA5`** | `GPIO_Output` | Output | 3.3V, max 20mA | Status Indicator LED (Normal/Warning/Critical) |
| **`PC0`** | `ADC_IN10` | Input | Analog, 0V - 3.3V | Raw cell voltage/temperature monitoring |
| **`GND`** | `Ground` | Power | 0V | Common Ground Reference |

---

## 💻 Running the Desktop Verification Simulator

To test the edge diagnostic runtime logic locally and benchmark execution paths on your developer machine:

- **On Windows (CMD/PowerShell):**
  ```powershell
  hardware/STM_Verifier/run_c_simulator.bat
  ```
- **On Linux or macOS:**
  ```bash
  chmod +x hardware/STM_Verifier/run_c_simulator.sh
  ./hardware/STM_Verifier/run_c_simulator.sh
  ```

### Comparative Benchmarking & Profiling
When compiled under the `HOST_SIMULATION` define, the desktop simulator runs both the **floating-point** and **fixed-point** ESN execution paths side-by-side. It prints the step outputs and displays a final benchmark report comparing:
- **Inference Accuracy**: Classification matching accuracy post-washout.
- **Quantization Deviation RMSE**: Root-mean-square error discrepancy of output states:
  $$\text{RMSE} = \sqrt{\frac{1}{M}\sum (y_{\text{float}} - y_{\text{fixed}})^2}$$
- **Execution Speed**: Inference execution time (in milliseconds) and microseconds per sample, revealing fixed-point integer speedups.
