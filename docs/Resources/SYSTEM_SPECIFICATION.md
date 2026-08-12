[← Back to README](../../README.md)

# System Specification

This document defines the interfaces, state flow, runtime modes, API payloads and validation scope for the Battery State Estimator.

---

## 📑 Table of Contents
1. [System Goal](#system-goal)
2. [Runtime Components](#runtime-components)
3. [Data Flow & Architecture](#data-flow--architecture)
4. [Telemetry Schema](#telemetry-schema)
5. [Detailed API Endpoints Spec](#detailed-api-endpoints-spec)
6. [Security & Authentication](#security--authentication)
7. [Estimator Pipeline Architecture](#estimator-pipeline-architecture)
8. [Edge Classifier Specification](#edge-classifier-specification)
9. [Validation Scope](#validation-scope)

## System Goal

The primary deliverable of this project is a data-driven **Echo State Network (ESN)** estimator designed as a direct, standalone replacement for traditional observers (EKF and Coulomb Counting) for SOC and SOH tracking. EKF and Coulomb Counting are implemented strictly as baseline benchmarks for comparison. The software estimator algorithm represents the final product, while embedded C99 microcontrollers and an **ARTIX A7100T FPGA** hardware RTL environment (`hardware/FPGA_Verifier`) serve as the testing and verification platform.

---

## Runtime Components

The table below outlines the key software and hardware components of the system:

| Component | Location | Responsibility |
| :--- | :--- | :--- |
| **Physics Simulator** | [`software/simulator/app.py`](../software/simulator/app.py) | Generates 2-RC ECM telemetry, thermal behavior, aging and injected faults. |
| **Visualiser Dashboard** | [`software/visualiser/app.py`](../software/visualiser/app.py) | Presents telemetry, estimator outputs, diagnostics and controls. |
| **Estimator Pipeline** | [`software/visualiser/estimator_pipeline.py`](../software/visualiser/estimator_pipeline.py) | Runs EKF, Coulomb Counting, ESN and CPS diagnostics. |
| **Hardware Classifier (C99)** | [`hardware/STM_Verifier/main.c`](../hardware/STM_Verifier/main.c) | Runs sparse ESN inference (CSR 6.7× speedup) for edge safety state classification. |
| **FPGA Verilog ESN Verifier** | [`hardware/FPGA_Verifier/`](../hardware/FPGA_Verifier/README.md) | 100-neuron Q6.10 fixed-point ESN RTL targeting **ARTIX A7100T FPGA**, matched 200/200 bit-exactly against Python golden model in Vivado/XSim. |
| **Training & Export Pipelines** | [`hardware/STM_Verifier/train_classifier.py`](../hardware/STM_Verifier/train_classifier.py)<br>[`hardware/STM_Verifier/train_estimator.py`](../hardware/STM_Verifier/train_estimator.py) | Train ESN models and export Python/C weight headers. |

---

## Data Flow & Architecture

The sequence diagram below visualizes the interactive data loops, including authentication checks and local fallback mechanisms when MongoDB is offline:

```mermaid
sequenceDiagram
    autonumber
    actor Operator
    participant Dashboard as Visualiser Dashboard (Port 5000)
    participant Simulator as Physics Simulator (Port 8000)
    participant DB as MongoDB Atlas / Local Buffer
    participant Edge as STM32 Edge Classifier / C Sim

    Operator->>Simulator: Control simulation or toggle faults (via Simulator Dashboard Port 8000)
    Simulator->>Simulator: Update runtime state variables
    
    loop Physics Loop (1 Hz Thread)
        Simulator->>Simulator: Solve 2-RC ECM & Thermal Equations
        alt MongoDB Connected
            Simulator->>DB: Insert Telemetry Document
        else Offline Fallback
            Simulator->>Simulator: Append to Local Circular Buffer
        end
    end

    loop Telemetry Visualisation
        Dashboard->>DB: Fetch latest telemetry frames
        DB-->>Dashboard: Telemetry readings
        Dashboard->>Dashboard: Run EKF (SOC), CC (SOC), RLS (SOH) and ESN estimators
        Dashboard->>Dashboard: Run cyber-physical diagnostic fault checks
        Dashboard->>Operator: Render updated charts & status widgets
    end

    loop Edge Inference Loop
        Simulator->>Edge: Telemetry input path [V, I, T]
        Edge->>Edge: Sparse CSR Matrix-Vector Multiplication (CSR SpMV)
        Edge->>Edge: Quantized Q12/Q15 Activation (Lookup Table)
        Edge->>Operator: Serial USART Status Logs & Toggle Pin PA5 LED
    end
```

---

## Telemetry Schema

The database document schema for each telemetry frame is detailed below:

| Field | Type | Unit | Meaning |
| :--- | :--- | :--- | :--- |
| `time` | Double | seconds | Simulation time index since start. |
| `voltage` | Double | Volts | Measured terminal voltage (with sensor noise). |
| `current` | Double | Amperes | Measured load current (positive for discharge, negative for charge). |
| `temperature` | Double | Celsius | Measured cell temperature. |
| `true_soc` | Double | Ratio [0, 1] | Physics-model state of charge. |
| `true_soh` | Double | Ratio [0, 1] | Physics-model state of health (capacity fade). |
| `true_v1` | Double | Volts | Transient polarization voltage drop (branch 1). |
| `true_v2` | Double | Volts | Transient polarization voltage drop (branch 2). |
| `true_r0` | Double | Ohms | Physics-model ohmic internal resistance (increases with aging). |
| `fault_short` | Boolean | - | Flag indicating active internal micro-short injection. |
| `fault_thermal` | Boolean | - | Flag indicating active thermal runaway simulation. |
| `fault_dropout` | Boolean | - | Flag indicating active voltage sensor dropout fault. |

---

## Detailed API Endpoints Spec

### 1. Simulator Service (`software/simulator`)

#### `GET /api/status`
Retrieves the simulator state, running configurations, active fault indicators and latest metrics.
* **Response Payload (JSON):**
  ```json
  {
    "sim_running": true,
    "chemistry": "li_ion",
    "active_cycle": "udds",
    "accelerated_aging": false,
    "T_ambient": 25.0,
    "fault_thermal": false,
    "fault_dropout": false,
    "fault_short": false,
    "time": 320.0,
    "soc": 0.892,
    "soh": 0.999,
    "voltage": 12.14,
    "current": 1.25,
    "temperature": 27.4,
    "telemetry_count": 320,
    "mongodb_connected": true
  }
  ```

#### `POST /api/control`
Executes simulation actions or modifies active faults and system configs. Requires standard cryptographic API headers.
* **Request Payload (JSON):**
  ```json
  {
    "command": "start",
    "chemistry": "li_ion",
    "cycle_type": "udds",
    "accelerated_aging": false,
    "T_ambient": 25.0,
    "fault_thermal": false,
    "fault_dropout": false,
    "fault_short": false
  }
  ```
* **Response Payload (JSON):**
  ```json
  {
    "status": "success",
    "state": {
      "sim_running": true,
      "chemistry": "li_ion",
      "active_cycle": "udds",
      "accelerated_aging": false,
      "T_ambient": 25.0,
      "fault_thermal": false,
      "fault_dropout": false,
      "fault_short": false,
      "time": 320.0,
      "soc": 0.892,
      "soh": 0.999,
      "voltage": 12.14,
      "current": 1.25,
      "temperature": 27.4
    }
  }
  ```

#### `POST /api/chemistry/register`
Registers a new OCV curve and chemical characteristics parameter file.
* **Request Payload (JSON):**
  ```json
  {
    "name": "lfp_custom",
    "capacity_ah": 2.5,
    "r0": 0.05,
    "r1": 0.02,
    "c1": 1500,
    "r2": 0.03,
    "c2": 25000,
    "ocv_lut": [
      [0.0, 2.5], [0.1, 3.1], [0.5, 3.2], [0.9, 3.3], [1.0, 3.6]
    ]
  }
  ```
* **Response Payload (JSON):**
  ```json
  {
    "status": "success",
    "message": "Chemistry lfp_custom registered successfully"
  }
  ```

---

### 2. Visualiser Service (`software/visualiser`)

#### `GET /api/status`
Retrieves backend execution indicators, connection targets, active ESN model state, dynamic noise parameters and safety fault magnitudes.
* **Response Payload (JSON):**
  ```json
  {
    "visualiser_status": "active",
    "simulator_url": "http://localhost:8000",
    "mongodb_status": "connected",
    "model_loaded": true,
    "model_source": "mongodb_registry",
    "ekf_mismatch": 1.0,
    "quantize_mode": "float32",
    "ekf_q_soc": 1e-7,
    "ekf_q_v1": 1e-6,
    "ekf_q_v2": 1e-6,
    "ekf_r_meas": 0.01,
    "fault_short_leakage": 0.8,
    "fault_thermal_runaway_mult": 4.0
  }
  ```

#### `GET /api/telemetry`
Retrieves time-series data augmented with the estimators pipeline outputs (EKF, Coulomb Counting, ESN), identified parameters and innovation.
* **Response Payload (JSON):**
  ```json
  [
    {
      "time": 320.0,
      "voltage": 3.86,
      "current": 1.25,
      "temperature": 27.4,
      "true_soc": 0.892,
      "ekf_soc": 0.894,
      "esn_soc": 0.891,
      "cc_soc": 0.895,
      "true_soh": 0.999,
      "ekf_soh": 0.998,
      "esn_soh": 0.999,
      "diagnostic_status": "NORMAL",
      "ekf_p_diag": [0.001, 0.0, 0.0],
      "rls_r0": 0.0249,
      "rls_r1": 0.0148,
      "rls_c1": 1205.0,
      "rls_converged": true,
      "innovation": 0.00045
    }
  ]
  ```

#### `POST /api/train`
Triggers an asynchronous training pipeline run to update ESN weights.
* **Response Payload (JSON):**
  ```json
  {
    "status": "training_initiated",
    "task_id": "esn_train_20260708_1925"
  }
  ```

---

## Security & Authentication

If the `MONGODB_URI` environment variable points to a remote cluster (anything other than `localhost` or `127.0.0.1`), security endpoints are locked automatically to prevent public manipulation of simulated parameters.

### Token Derivation
A dynamic API signature key is computed at server boot to authenticate inter-service requests:
$$\text{Key} = \text{SHA-256}(\text{MONGODB\_URI})$$

### HTTP Headers Authorization
- **Header Field**: `X-API-Key`
- **Fallback URL Query**: `?api_key=<token>`
- **Unauthorized Output**: `401 Unauthorized`

---

## Estimator Pipeline Architecture

The visualiser enriches telemetry data with dynamic state observations computed in the background, implementing EKF and CC strictly as baseline benchmarks to quantify the ESN's standalone performance:
- **State of Charge (SOC)**: Runs Coulomb Counting (CC) and a Sage-Husa Adaptive Extended Kalman Filter (EKF) concurrently purely as accuracy baselines, compared side-by-side with the proposed production Echo State Network (ESN) estimator.
- **State of Health (SOH)**: Decoupled to track slowly varying capacity and internal resistance trends via online RLS resistance-growth parameters identification (baseline benchmarking) compared against the proposed data-driven ESN SOH model.
- **Diagnostics Outputs**: Monitors anomalies to classify faults:
  - `DIAG_DROPOUT_VOLTAGE_THRESHOLD` (< 1.0 V) -> **Sensor Dropout**.
  - `DIAG_THERMAL_TEMP_THRESHOLD` (> 60 °C) or rate of rise (> 2.0 °C/s) -> **Thermal Runaway Warning**.
  - `DIAG_SHORT_SOC_DIFF_THRESHOLD` (> 0.08 SOC divergence under low-current idle) -> **Internal Micro-Short**.

---

## Edge Classifier Specification

The embedded classifier running on the STM32 microcontroller serves as a feasibility check to validate that the ESN's reservoir-computing architecture is deployable within real-time, low-power microcontroller constraints. It consumes real-time telemetry inputs to flag thermal hazard classes. Success is defined by algorithmic accuracy and efficiency, rather than the hardware demo itself (while the SOC/SOH estimator itself remains software-validated, with hardware porting reserved for future work).

* **Network Dimensions**: 3 Inputs $\rightarrow$ 50 Reservoir Nodes (CSR format) $\rightarrow$ 3 Output Classes.
* **Target Classes**:
  - `Class 0 (Normal)`: Temperature $< 35\text{ }^\circ\text{C}$ (Indicator LED Pin `PA5` Off).
  - `Class 1 (Warning)`: $35\text{ }^\circ\text{C} \le \text{Temperature} < 45\text{ }^\circ\text{C}$ (Indicator LED Pin `PA5` Blinking).
  - `Class 2 (Critical)`: Temperature $\ge 45\text{ }^\circ\text{C}$ (Indicator LED Pin `PA5` Steady On).

---

## Validation Scope

Robustness and estimation accuracy limits are verified using automated unit suites:
- Chemistry loading correctness & OCV curve monotonicity checks.
- Dynamic 2-RC transient equations solvers accuracy.
- Observer convergence bounds and covariance matrix health tests.
- High-noise and drop-out fault resilience validation.

Run the test runner locally using:
```bash
python software/visualiser/training/train_rc.py
```

```bash
python hardware/STM_Verifier/train_classifier.py
```
