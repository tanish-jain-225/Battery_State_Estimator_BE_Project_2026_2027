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
| `train_estimator.py` | Single source of truth: trains SOC/SOH ESN estimators and exports C weights. |
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

## Hardware Wiring & Pinout Reference

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
| --- | --- | --- | --- | --- |
| `PA2` | `USART2_TX` | Output | 3.3V Logic | Diagnostic telemetry transmitter |
| `PA3` | `USART2_RX` | Input | 3.3V Logic | Control command receiver |
| `PA5` | `GPIO_Output` | Output | 3.3V, max 20mA | Status Indicator LED (Normal/Warning/Critical) |
| `PC0` | `ADC_IN10` | Input | Analog, 0V - 3.3V | Raw cell voltage/temperature monitoring |
| `GND` | `Ground` | Power | 0V | Ground reference |
