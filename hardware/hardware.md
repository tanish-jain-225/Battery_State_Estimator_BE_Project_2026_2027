# Hardware Subsystem

This folder contains the embedded ESN classifier, training scripts, generated C
headers, and a desktop C simulator for validating the firmware logic before
flashing a microcontroller.

## Contents

| Path | Purpose |
| --- | --- |
| `main.c` | C99 classifier runtime for STM32-style targets and desktop simulation. |
| `main.h` | Host-side HAL shims used by the desktop simulator. |
| `train.py` | Echo State Network implementation used by hardware training scripts. |
| `train_classifier.py` | Trains the 3-class thermal safety ESN and exports CSR C weights. |
| `train_estimator.py` | Trains SOC/SOH ESN estimators and exports C weights. |
| `export_weights.py` | Helper exporter for estimator weight headers. |
| `config.py` | Environment-driven configuration for datasets, ESN dimensions, and thresholds. |
| `esn_classifier_weights.h` | Generated sparse classifier weights consumed by `main.c`. |
| `esn_estimator_weights.h` | Generated estimator weights for embedded experiments. |
| `original_ev_battery_dataset_multiclass.csv` | Training data for safety classification. |
| `run_c_simulator.bat` | Windows build-and-run script. |
| `run_c_simulator.sh` | Linux/macOS build-and-run script. |

## Classifier Inputs and Outputs

Input vector:

```text
[terminal_voltage, load_current, cell_temperature]
```

Output classes:

```text
0 = Normal
1 = Warning
2 = Critical
```

Default thermal thresholds:

| Class | Temperature Range | LED Behavior |
| --- | --- | --- |
| Normal | `< 35 C` | `PA5` off |
| Warning | `35 C <= T < 45 C` | `PA5` blinking |
| Critical | `>= 45 C` | `PA5` on |

## Embedded Optimizations

- CSR sparse reservoir representation reduces recurrent work from 2,500 dense
  multiplies to about 375 non-zero multiplies for a 50-node reservoir.
- Optional Q12/Q15 fixed-point mode avoids most runtime floating-point work.
- A 33-point tanh lookup table with interpolation replaces expensive activation
  calls in the fixed-point path.

## Train Weights

```bash
python hardware/train_classifier.py
python hardware/train_estimator.py
```

## Run Desktop C Simulation

Windows:

```bash
hardware/run_c_simulator.bat
```

Linux/macOS:

```bash
chmod +x hardware/run_c_simulator.sh
hardware/run_c_simulator.sh
```

## Configuration

Use `hardware/.env.example` as the documented template for local overrides.
Commit only the example file, never a real `.env`.
