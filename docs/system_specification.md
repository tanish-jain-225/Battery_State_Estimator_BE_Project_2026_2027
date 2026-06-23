# Cyber-Physical Battery Estimator System Specification

This specification documents the interfaces, data flows, APIs, and pinout configurations that bridge the hardware and software components of the integrated Battery State Estimator system.

---

## 1. Cyber-Physical Data Flows

The system operates in a closed loop, processing real-time electrical transients into predictive state vectors (SOC, SOH) and diagnostic safety evaluations.

```
       🔋 PHYSICAL BATTERY
               │
               ▼ Sensor telemetry (V, I, T)
      ╔═══════════════════════════╗
      ║ STM32 Edge Classifier     ║ ◄─── Off-line Ridge Regression training
      ║  - Sparse Reservoir (CSR) ║
      ║  - Fixed-Point (LUT Tanh) ║
      ╚═══════════════════════════╝
               │
               ├─────── GPIO PA5 status LED 🟡/🟢/🔴
               │
               ▼ UART ST-Link Virtual COM stream
      ╔═══════════════════════════╗
      ║ software/simulator        ║ ◄─── REST APIs (Port 8000)
      ║  - 2RC Electro-Thermal    ║
      ║  - Noise & fault injector ║
      ╚═══════════════════════════╝
               │
               ├─── MongoDB logs (telemetry_data)
               │
               ▼ Web WebSockets / AJAX
      ╔═══════════════════════════╗
      ║ software/visualiser       ║ ◄─── comparative dashboard (Port 5000)
      ║  - EKF vs ESN Estimators  ║
      ║  - Glassmorphic UI        ║
      ╚═══════════════════════════╝
```

---

## 2. Software Subsystem Specification

### A. Battery Physics Simulator (Port `8000`)
The simulator server is a standalone Python Flask microservice that implements a high-fidelity 2-RC equivalent circuit physical model.

* **API Endpoints**:
  * `POST /step`: Advances the physical model by step size `dt`.
    - *Request Body*: `{"current": -2.5, "accelerated_aging": false, "fault_thermal": false, "fault_dropout": false, "fault_short": false}`
    - *Response*: Telemetry frame containing `voltage`, `current`, `temperature`, `true_soc`, `true_soh`, `v1`, `v2`, `R0`.
  * `POST /config/chemistry`: Switch active chemistry profile.
    - *Request Body*: `{"chemistry": "li_ion"}` or `{"chemistry": "lfp"}`.
  * `GET /state`: Retrieve current internal physical values.
  * `POST /reset`: Reinitialise cell parameters to nominal state.

* **MongoDB Database Integration**:
  * **Database Name**: `battery_monitor`
  * **Collection**: `telemetry_data`
  * **Document Schema**:
    ```json
    {
      "_id": "ObjectId",
      "timestamp": "ISODate",
      "time": "double (seconds)",
      "voltage": "double (Volts)",
      "current": "double (Amperes)",
      "temperature": "double (°C)",
      "true_soc": "double (0.0 to 1.0)",
      "true_soh": "double (0.0 to 1.0)"
    }
    ```

### B. Visualiser Dashboard (Port `5000`)
The visualiser dashboard serves as the central operator control center. It runs EKF (Kalman Filter) and ESN (Echo State Network) observers simultaneously to estimate states from noisy sensor inputs.

* **Sidebar Diagnostics**:
  - **Sim Service Badge**: Scans Port 8000 asynchronously. Status transitions: `Online` (green), `Offline` (orange).
  - **MongoDB Badge**: Background connection check. Status transitions: `Connected` (green), `In-Memory` (blue, falling back to local list buffers).
* **Fault Injection Console**:
  - Toggles active physical faults (Thermal Runaway, Sensor Dropout, Micro-Short Circuit) on the simulator via `/step` payload flags.

---

## 3. Hardware Subsystem Specification

The edge diagnostic subsystem compiles to standard C99 code running on a low-power STM32 Nucleo board (or compiled locally on a desktop PC).

### A. MCU Pin Mapping (STM32 Nucleo H7)
* **GPIO Output (`PA5` / Nucleo Green LED)**:
  Used for immediate visual alert indicators depending on ESN argmax state:
  * 🟢 **Normal State (0)**: `PA5` is kept `LOW` (LED Off). Represents nominal temperatures ($T < 35^{\circ}\text{C}$).
  * 🟡 **Warning State (1)**: `PA5` is toggled at $20\text{Hz}$ (LED Blinking). Represents temperature warning range ($35^{\circ}\text{C} \le T < 45^{\circ}\text{C}$).
  * 🔴 **Critical State (2)**: `PA5` is kept `HIGH` (LED On). Represents thermal threat ($T \ge 45^{\circ}\text{C}$).
* **UART2 Tx/Rx Pins (`PA2` / `PA3` / ST-Link Virtual COM)**:
  Transmits character streams at `115200` baud rate, 8 data bits, 1 stop bit, no parity (`115200 8N1`) to the PC host dashboard.

### B. Fixed-Point ESN Network Matrix Shapes
* **Input Layer ($N_u = 3$)**: Voltage, Current, Temperature.
* **Reservoir Layer ($N_r = 50$)**: Sparse CSR recurrent matrix ($85\%$ sparsity $\rightarrow 375$ NNZ).
* **Output Readout Layer ($N_y = 3$)**: Normalized classifier confidence score for [Normal, Warning, Critical].
* **Lookup Table Dimensions**: 33-point lookup table mapping positive quadrant `tanh` float mappings into Q15 format.

---

## 4. Consolidated Workspace Tree

The unified directory layout below shows where all component files reside in the workspace:

```text
Battery_State_Estimator_BE_Project_2026_2027/
│
├── README.md                          # Global Capstone template
│
├── docs/                              # Project technical files
│   ├── literature_survey.md           # Theoretical review & equations
│   └── system_specification.md        # [THIS FILE] Interface specification
│
├── hardware/                          # STM32 C Firmware & Python trainers
│   ├── main.c                         # Inference engine & mock host
│   ├── main.h                         # HAL mocks & target structures
│   ├── train.py                       # Core ESN Python class
│   ├── train_classifier.py            # Generates esn_classifier_weights.h
│   ├── train_estimator.py             # Generates esn_estimator_weights.h
│   ├── esn_classifier_weights.h       # Quantized CSR classifier weights
│   ├── esn_estimator_weights.h        # Dense regression estimator weights
│   ├── original_ev_battery_dataset... # Synthetic EV battery CSV
│   ├── run_c_simulator.bat            # Windows MSVC/MinGW runner
│   └── run_c_simulator.sh             # Linux/macOS GCC compile runner
│
├── software/
│   ├── simulator/                     # Port 8000 Physics Simulator
│   │   ├── app.py                     # Flask server with async DB checker
│   │   ├── battery_simulator.py       # 2-RC dynamic physics equations
│   │   └── traditional_estimator.py   # EKF prediction-correction loops
│   │
│   └── visualiser/                    # Port 5000 comparative dashboard
│       ├── app.py                     # Web dashboard with async paced checker
│       └── training/
│           ├── train_rc.py            # Train visualiser model_rc.pkl
│           └── model_rc.pkl           # Packed weights & RMSE bounds
│
└── reference/
    └── paper.md                       # Academic draft of the research
```