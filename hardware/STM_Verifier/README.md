# STM32 C99 Embedded Verifier & Firmware Optimization

[← Back to Main Repository](../../README.md) · [← Hardware Overview](../hardware.md) · [FPGA Verifier →](../FPGA_Verifier/README.md) · [IP Block Platform →](../IP_Block/README.md)

---

## 📌 Overview

This directory contains the **C99 embedded firmware and desktop test harness** developed to validate Echo State Network (ESN) state estimation on resource-constrained microcontrollers (specifically ARM Cortex-M4 / STM32F4 series).

To prove edge feasibility on an automotive microcontroller without hardware floating-point acceleration:
1. **Compressed Sparse Row (CSR) SpMV**: Internal reservoir matrices are compressed into CSR format (values, column indices, row pointers), skipping 90% zero multiplications and yielding a **6.7× inference speedup**.
2. **Fixed-Point Arithmetic (Q12/Q15)**: Integer-only math eliminates hardware FPU requirements, saving **82.4% RAM** and ~10 KB Flash.
3. **Lookup Table (LUT) Tanh**: 33-point piecewise linear interpolation provides high-precision $\tanh$ activation with minimal CPU cycles.

---

## 📂 Directory Contents

| File | Type | Description |
| :--- | :---: | :--- |
| [`main.c`](main.c) | C Source | Core C99 inference engine supporting both Float32 and Fixed-Point Q15 CSR SpMV. |
| [`main.h`](main.h) | C Header | Data structures, CSR matrix definitions, function prototypes, and fixed-point macros. |
| [`Makefile.arm`](Makefile.arm) | Build | Cross-compilation Makefile targeting ARM Cortex-M4 (`arm-none-eabi-gcc`). |
| [`run_c_simulator.bat`](run_c_simulator.bat) | Batch Script | 1-click Windows compilation and execution test harness using GCC/MSVC. |
| [`run_c_simulator.sh`](run_c_simulator.sh) | Shell Script | 1-click Linux/macOS compilation and execution test harness. |
| [`esn_classifier_weights.h`](esn_classifier_weights.h) | C Header | Quantized CSR sparse weights for battery safety state classification. |
| [`esn_estimator_weights.h`](esn_estimator_weights.h) | C Header | Quantized CSR sparse weights for continuous SOC/SOH estimation. |
| [`train_classifier.py`](train_classifier.py) | Python | Trains safety classification ESN and exports C weight headers. |
| [`train_estimator.py`](train_estimator.py) | Python | Trains continuous SOC/SOH ESN and exports C weight headers. |
| [`config.py`](config.py) | Python | Environment configuration and hyperparameter settings. |

---

## ⚙️ Performance Benchmarks (Cortex-M4 vs. Desktop x86)

| Metric | Dense Matrix | Compressed Sparse Row (CSR) | Improvement |
| :--- | :---: | :---: | :---: |
| **Inference Time (per step)** | 4.82 ms | **0.72 ms** | **6.7× Speedup** |
| **Memory Footprint (RAM)** | 42.6 KB | **7.5 KB** | **82.4% Savings** |
| **Arithmetic Mode** | Float32 (FPU required) | **Q15 Integer Math** | Zero FPU dependency |
| **Thermal Diagnostic Accuracy** | 99.80% | **98.40%** | < 1.4% quantization loss |

---

## 🚀 How to Run Embedded Verification

### Windows:
```cmd
hardware\STM_Verifier\run_c_simulator.bat
```

### Linux / macOS:
```bash
bash hardware/STM_Verifier/run_c_simulator.sh
```

### Cross-Compiling for ARM Cortex-M:
```bash
make -f Makefile.arm
```

