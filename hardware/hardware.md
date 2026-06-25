# STM32 Edge Battery State Evaluator & Classifier (Hardware Component)

A highly optimized cyber-physical edge computing subsystem designed to run real-time battery diagnostics directly on low-power microcontrollers (ARM Cortex-M core). This folder contains the offline Python training scripts, feature engineering pipelines, math models, and embedded C firmware executing an optimized [EchoStateNetwork](train.py#L3).

---

## 📂 Hardware Component Overview

The hardware component is structured as follows:

| File / Directory | Description |
| :--- | :--- |
| **[main.c](main.c)** | Firmware entry point for STM32 and desktop host simulation. Executes sparse reservoir computing inference in real-time, processes telemetry arrays, drives GPIO status LED (`PA5`), and outputs diagnostic streams. |
| **[main.h](main.h)** | Mock header enabling desktop/host compilation when not targeting ARM microcontrollers, simulating STM32 HAL variables, types, and functions. |
| **[train.py](train.py)** | Core [EchoStateNetwork](train.py#L3) model class implementing recurrent reservoir dynamics, Ridge Regression readout fitting, and fixed-point quantization simulations (`float32`, `int16`, `int8`). |
| **[train_classifier.py](train_classifier.py)** | Offline pipeline to train the 3-state ESN battery classifier. Scales inputs, generates CSR (Compressed Sparse Row) arrays, and writes [esn_classifier_weights.h](esn_classifier_weights.h). |
| **[train_estimator.py](train_estimator.py)** | Offline script to train dual ESN estimators: SOC Estimator (300 reservoir nodes) and SOH Estimator (200 reservoir nodes). Performs feature engineering and writes dense weights to [esn_estimator_weights.h](esn_estimator_weights.h). |
| **[export_weights.py](export_weights.py)** | Duplicate/helper pipeline identical to [train_estimator.py](train_estimator.py) that trains SOC/SOH estimators and exports weights to the C header structure. |
| **[config.py](config.py)** | Environment-driven centralized pipeline configurations (hyperparameters, database configurations, dataset locations, classification thresholds). |
| **[esn_classifier_weights.h](esn_classifier_weights.h)** | Auto-generated C header representing the 3-state classifier ESN parameters (normalization coefficients, input/readout weights, CSR reservoir representation). |
| **[esn_estimator_weights.h](esn_estimator_weights.h)** | Auto-generated C header representing dense ESN estimators for State of Charge (SOC) and State of Health (SOH) tracking. |
| **[original_ev_battery_dataset_multiclass.csv](original_ev_battery_dataset_multiclass.csv)** | Raw time-series dataset containing simulated electric vehicle (EV) battery parameters (Voltage, Current, Temperature, SOC, SOH). |
| **[requirements.txt](requirements.txt)** | Python dependencies list for ESN training scripts (`numpy`, `pandas`, `scipy`). |
| **[run_c_simulator.bat](run_c_simulator.bat)** / **[run_c_simulator.sh](run_c_simulator.sh)** | Cross-platform build and execution scripts to compile and run the ESN C classifier simulator locally on your PC. |
| **[.env](.env)** / **[.env.example](.env.example)** | Placeholders for overriding ESN structural dimensions and training constraints dynamically. |
| **[.gitignore](.gitignore)** | Git version control ignore rules for compilation objects, virtual environments, and local credentials. |


---

## 🧮 Embedded Echo State Network (ESN) Dynamics

The ESN architecture leverages a high-dimensional recurrent reservoir to map non-linear battery transients into a linearly separable space.

```
                    ┌──────────────────────────────────────────────┐
                    │            ESN Reservoir (x_t)               │
                    │   - Recurrent connection matrix W_res       │
                    │   - Leak Rate (α = 0.3)                      │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
  ┌──────────────────────┐                 │                 ┌──────────────────────┐
  │ Inputs (u_t)         ├─────────────────┼────────────────►│ Linear Readout W_out │
  │ - Voltage            │                 │                 │                      │
  │ - Current            │                 ▼                 │ - Argmax Decision    │
  │ - Temperature        ├──────────────────────────────────►│   (Normal/Warning/   │
  └──────────────────────┘                                   │    Critical)         │
                                                             └──────────┬───────────┘
                                                                        │
                                                                        ▼
                                                             ┌──────────────────────┐
                                                             │ GPIO Control (PA5)   │
                                                             └──────────────────────┘
```

The system executes the following mathematical update pipeline at each tick $t$:

### 1. Z-Score Feature Scaling
To balance input features with varying orders of magnitude (e.g., current transients vs. thermal dynamics), features $u_t$ are normalized using pre-calculated training dataset means ($\mu$) and standard deviations ($\sigma$):
$$u_{\text{scaled}, i} = \frac{u_t[i] - \mu_i}{\sigma_i}$$

### 2. Recurrent Reservoir Update
The reservoir vector $x_t \in \mathbb{R}^{50}$ tracks temporal dependencies of the battery states (leakage rate $\alpha = 0.3$):
$$\tilde{x}_t = \tanh\left(\mathbf{W}_{\text{in}} [1; u_{\text{scaled}}] + \mathbf{W}_{\text{res}} x_{t-1}\right)$$
$$x_t = (1 - \alpha) x_{t-1} + \alpha \tilde{x}_t$$

* $[1; u_{\text{scaled}}]$ represents the input features concatenated with a constant bias.
* $\mathbf{W}_{\text{in}} \in \mathbb{R}^{50 \times 4}$ maps inputs into the reservoir.
* $\mathbf{W}_{\text{res}} \in \mathbb{R}^{50 \times 50}$ controls internal recurrent reservoir loops (initialized with $85\%$ sparsity).

### 3. Readout & Decision Boundary
The output $y_t \in \mathbb{R}^3$ computes the raw activation values for the three battery states:
$$y_t = \mathbf{W}_{\text{out}} [1; u_{\text{scaled}}; x_t]$$
$$\text{state} = \operatorname{argmax}(y_{t, 0}, y_{t, 1}, y_{t, 2})$$

Predicted states correspond to:
* **0 (NORMAL)**: Temperature $< 35^{\circ}\text{C}$
* **1 (WARNING)**: Temperature $35^{\circ}\text{C} \le \text{Temp} < 45^{\circ}\text{C}$
* **2 (CRITICAL)**: Temperature $\ge 45^{\circ}\text{C}$

---

## ⚡ Hardware Optimizations & Memory Footprint

To ensure smooth real-time execution on low-cost ARM Cortex-M microcontrollers, the firmware implements key mathematical optimizations:

### 1. Compressed Sparse Row (CSR) SpMV
Standard dense matrix-vector multiplication (SpMV) for a $50 \times 50$ reservoir requires $2,500$ floating-point multiplies per tick. By forcing $85\%$ sparsity during training, we compress $\mathbf{W}_{\text{res}}$ into three flat 1D arrays:
- `esn_W_res_val` ($375$ elements): Non-zero floating-point weights.
- `esn_W_res_col` ($375$ elements): 16-bit column indices of non-zero entries.
- `esn_W_res_row_ptr` ($51$ elements): Indices marking the start of each row.

This reduces reservoir operations to only $375$ multiplications (a **6.7× execution speedup**) and saves ~10 KB of Flash storage.

### 2. Low-Power Fixed-Point Math ([ESN_FIXED_POINT](main.c#L51))
For ultra-low-power microcontrollers lacking a Hardware Floating-Point Unit (FPU), the firmware provides a pure integer execution path. Toggling `#define ESN_FIXED_POINT 1` compiles the algorithm into integer-only arithmetic:
- **Q12 Format Inputs**: Scaled features are represented in Q12 format ($\pm 8.0$ dynamic range, scaled by $4096$).
- **Q15 Format States & Weights**: All states $x_t$ and matrices $\mathbf{W}_{\text{in}}$, $\mathbf{W}_{\text{res}}$ are converted to Q15 format ($[-1.0, 1.0)$, scaled by $32768$).
- **Look-Up Table (LUT) Tanh Approximation**: Tanh calculations are avoided using a high-speed 33-point lookup table ([tanh_lut](main.c#L74)) combined with linear interpolation:
  $$\text{frac} = |x| \pmod{1024}$$
  $$y = \frac{(1024 - \text{frac}) \cdot \text{LUT}[\text{index}] + \text{frac} \cdot \text{LUT}[\text{index} + 1]}{1024}$$
- **Readout mapping**: Only the final evaluation boundary (the dense readout $\mathbf{W}_{\text{out}}$) is cast back to floats to maintain classification accuracy.

---

## 🚀 Execution & Setup Guide

### 1. Train ESN Models
Run the training pipelines to generate the weights header files:

- **Train ESN Classifier**:
  ```bash
  python hardware/train_classifier.py
  ```
  Generates [esn_classifier_weights.h](esn_classifier_weights.h) (uses 3 features $\rightarrow$ 50 reservoir nodes $\rightarrow$ CSR representation).

- **Train SOC/SOH Estimators**:
  ```bash
  python hardware/train_estimator.py
  ```
  Generates [esn_estimator_weights.h](esn_estimator_weights.h) (uses 4 features $\rightarrow$ 300 & 200 reservoir nodes $\rightarrow$ dense matrices).

### 2. Configure & Build Firmware
1. Open the project in your microcontroller toolchain (e.g., STM32CubeIDE, Keil MDK).
2. Copy [esn_classifier_weights.h](esn_classifier_weights.h) into your compiler's directory headers (include search paths).
3. Open [main.c](main.c) and configure your target math path at line 51:
   - `#define ESN_FIXED_POINT 0` for high-precision standard float math.
   - `#define ESN_FIXED_POINT 1` for integer-optimized low-power fixed-point math.
4. Compile the project and flash the binary onto your board.

### 3. Run Standalone C Simulation (Desktop PC)
You can compile and execute the C code directly on your local computer to verify compilation and reservoir output:
- **Windows**:
  Double-click or run from command terminal:
  ```bash
  hardware/run_c_simulator.bat
  ```
- **Unix / macOS / Linux**:
  Make the shell script executable and run:
  ```bash
  chmod +x hardware/run_c_simulator.sh
  hardware/run_c_simulator.sh
  ```
The compilation script automatically detects GCC, Clang, or MSVC and compiles [main.c](main.c) against the simulated [main.h](main.h) definitions, then runs the test suite.

### 4. Monitor Real-Time Classification
Connect your STM32 development board (e.g., Nucleo) to your PC and open a serial terminal (PuTTY, Tera Term, or `screen`):
- **Port**: ST-Link Virtual COM Port
- **Baud Rate**: `115200`
- **Settings**: 8 Data Bits, 1 Stop Bit, No Parity

The terminal outputs real-time classifications alongside telemetry variables:
```text
System Started

--- Starting ESN Inference Loop (N=500) ---
[  0] True=NORMAL   Pred=NORMAL   | V=11 I=2 T=32
[  1] True=NORMAL   Pred=NORMAL   | V=11 I=2 T=32
...
[342] True=WARNING  Pred=WARNING  | V=10 I=5 T=35
...
[457] True=CRITICAL Pred=CRITICAL | V=10 I=6 T=45
--- Loop Complete. Accuracy: 98.40% ---
```

### 5. Hardware Visual Feedback
The firmware controls the on-board GPIO pin `PA5` (the green LED on standard Nucleo boards) as visual feedback:
- 🟢 **NORMAL**: `PA5` is kept Off (Low).
- 🟡 **WARNING**: `PA5` blinks dynamically (Toggles at 20Hz).
- 🔴 **CRITICAL**: `PA5` is kept On (High).