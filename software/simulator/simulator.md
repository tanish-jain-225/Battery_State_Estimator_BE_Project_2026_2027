# Standalone Battery Physics Simulator Server

A high-fidelity real-time Python battery physics engine and simulation server. This component runs a **first-order Equivalent Circuit Model (ECM) with 2RC branches**, dynamic cell thermal models, capacity-fading degradation models, and sensor noise/fault injectors. It serves as the data generation pipeline for the Battery State Estimator comparison platform.

---

## 📖 Table of Contents
1. [Simulator Directory Structure](#-simulator-directory-structure)
2. [Simulation Architecture & Execution Loop](#-simulation-architecture--execution-loop)
3. [Electro-Thermal & Degradation Physics](#-electro-thermal--degradation-physics)
4. [Drive Cycles & Injected Faults](#-drive-cycles--injected-faults)
5. [API Documentation](#-api-documentation)
6. [Configuration & Tuning Parameters](#-configuration--tuning-parameters)
7. [Setup & Running Instructions](#-setup--running-instructions)

---

## 📂 Simulator Directory Structure

The simulator is located in the `software/simulator` folder:

```
simulator/
├── .env (Local environment configurations - MongoDB, debug flags, server ports)
├── .env.example (Template for setting up environment variables)
├── .gitignore (Excludes pycache, env, and local build files)
├── simulator.md (Comprehensive documentation of the battery physics simulation server)
├── app.py (Flask API web server and background simulation pacing thread)
├── config.py (Private database, server, timing, noise, and fault configurations)
├── requirements.txt (Dependencies for Flask, pymongo, and NumPy)
├── battery_simulator.py (Core BatterySimulator physics model and DriveCycles)
├── battery_chemistry.py (BatteryChemistry profiles and OCV lookup tables)
├── traditional_estimator.py (Physics-based EKF and SOH tracker)
├── estimator_pipeline.py (Telemetry runner with safety overrides and state sync)
├── static/
│   ├── css/
│   │   └── style.css (Premium light-mode glassmorphism styling)
│   ├── images/
│   │   ├── favicon.ico (BMS icon favicon)
│   │   └── logo.png (Brand identity logo)
│   └── js/
│       └── generator.js (Developer simulation dashboard javascript controller)
└── templates/
    └── index.html (Developer simulation dashboard HTML dashboard)
```

---

## 🏗️ Simulation Architecture & Execution Loop

The simulator functions as a self-contained cyber-physical generator:

```
           ┌──────────────────────────────────────────────┐
           │              Simulator: app.py               │
           ├──────────────────────┬───────────────────────┤
           │  Background Thread:  │     Flask Server:     │
           │    generator_loop    │     API Endpoints     │
           └──────────┬───────────┴───────────▲───────────┘
                      │                       │ POST /api/control
                 Steps Physics                │
                      ▼                       │
           ┌──────────────────────┐   ┌───────┴───────────┐
           │   BatterySimulator   │   │  Browser / Client │
           └──────────┬───────────┘   └───────────────────┘
                      │ Pushes readings
                      ▼
           ┌──────────────────────┐
           │ MongoDB / Local RAM  │
           └──────────────────────┘
```

### 1. Standalone Generator Loop (`generator_loop`)
- Runs a dedicated background thread on Port 8000.
- When `sim_running` is active, it steps the physics model, applies sensor noise, logs the data records to MongoDB, and updates the shared state in-memory/DB.
- Uses dynamic sleep timers calculated relative to `Config.SIMULATION_STEP_DELAY` to guarantee real-time execution pacing.

### 2. On-Demand Catch-up (`sync_simulation_on_demand`)
- Designed for serverless environments where background threads are disabled.
- Evaluates the real-world time elapsed since the last API poll.
- Steps the physics simulation dynamically by the required number of ticks (capped to avoid lockups) to catch up, maintaining stateless consistency.

---

## 🔋 Electro-Thermal & Degradation Physics

Implemented in [battery_simulator.py](battery_simulator.py).

### 1. Equivalent Circuit Model (ECM)
The cell voltage drop utilizes a 2RC transient branch framework:
$$V_{\text{terminal}} = V_{\text{OCV}}(SOC) + I \cdot R_0 + V_1 + V_2$$

Where:
- $V_{\text{OCV}}$ is OCV lookup from [battery_chemistry.py](battery_chemistry.py).
- $I$ is external current ($I > 0$ for charging, $I < 0$ for discharging).
- $R_0$ is internal ohmic resistance (grows with aging).
- $V_1, V_2$ model the slow and fast diffusion voltages:
  $$\Delta V_i = \left( \frac{I - \frac{V_i}{R_i}}{C_i} \right) \cdot \Delta t$$

### 2. Coupled Thermal Model
Internal losses generate heat, cooled by convection:
$$\Delta T = \left( \frac{(I^2 \cdot R_0 + |I \cdot V_1| + |I \cdot V_2|) - h \cdot (T - T_{\text{ambient}})}{C_{\text{thermal}}} \right) \cdot \Delta t$$

### 3. Capacity Fade Degradation (SOH)
Degradation increases resistance and fades capacity based on load current amplitudes and temperatures:
$$\Delta SOH = -1.2 \times 10^{-7} \cdot |I|^{1.3} \cdot e^{0.06(T - 25)} \cdot \Delta t$$
$$R_0(t) = R_{0,\text{nom}} \cdot \left[1.0 + 1.5 \cdot (1.0 - SOH)\right]$$
*Toggling Accelerated Aging scales capacity fade by $\times 1500$.*

---

## 🎛️ Drive Cycles & Injected Faults

### 1. Excitation Cycles (`DriveCycles`)
- **UDDS (Urban Dynamometer Driving Schedule)**: Standard stop-and-go city driving current profiles.
- **HWFET (Highway Fuel Economy Test)**: Consistent, high-speed highway current profiles.
- **US06**: Aggressive, highly transient acceleration current profiles.
- **Constant**: Continuous discharge load rate at -2.5 A (1C rate equivalent).
- **CCCV Charge**: Constant-Current Constant-Voltage charging cycle profile.

### 2. Injected Faults
- **Thermal Runaway**: Injecting `fault_thermal` triggers self-heating runaway:
  $$\Delta T_{\text{runaway}} = \text{FAULT\_THERMAL\_RUNAWAY\_MULT} \cdot e^{\text{FAULT\_THERMAL\_RUNAWAY\_EXP} \cdot (T - 25.0)} \cdot \Delta t$$
- **Sensor Dropout**: Injecting `fault_dropout` clamps output terminal voltage to 0.0V and current to 0.0A.
- **Internal Micro-Short**: Injecting `fault_short` drains cell SOC internally at `FAULT_SHORT_LEAKAGE_CURRENT` (0.8A) and generates joule heating from leakages, remaining hidden from external current sensors.

---

## 📡 API Documentation

### 1. `GET /api/status`
Fetches connection status, settings, and live state values.
- **Response**:
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
  "time": 105.0,
  "soc": 0.954,
  "soh": 1.0,
  "voltage": 12.35,
  "current": -1.5,
  "temperature": 25.4,
  "telemetry_count": 105,
  "mongodb_connected": true
}
```

### 2. `POST /api/control`
Updates running states and injects faults.
- **Request Body Options**:
  - `command`: `"start"`, `"stop"`, `"pause"`, or `"reset"`
  - `chemistry`: `"nmc"`, `"lfp"`, `"lead_acid"`, or `"li_ion"`
  - `cycle_type`: `"udds"`, `"hwfet"`, `"us06"`, `"constant"`, or `"charge"`
  - `accelerated_aging`: `true` or `false`
  - `T_ambient`: `float`
  - `fault_thermal`: `true` or `false`
  - `fault_dropout`: `true` or `false`
  - `fault_short`: `true` or `false`
- **Response**: Returns the updated config status.

### 3. `GET /api/readings`
Exposes the raw history of measured telemetry records stored in buffer.
- **Response**: List of raw readings containing `time`, `voltage`, `current`, `temperature`, and true physical ground truths (`true_soc`, `true_soh`, `true_v1`, `true_v2`, etc.).

---

## ⚙️ Configuration & Tuning Parameters

Settings are declared in [config.py](config.py):

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `MONGODB_URI` | `"mongodb://localhost:27017/"` | Database host URI. Telemetry is saved locally to RAM if offline. |
| `SIMULATION_STEP_DELAY` | `1.0` | Simulation loop tick pacing (seconds). |
| `DEFAULT_NOISE_VOLTAGE` | `0.005` | Voltage sensor Gaussian standard deviation noise (V). |
| `DEFAULT_NOISE_CURRENT` | `0.05` | Current sensor Gaussian standard deviation noise (A). |
| `DEFAULT_NOISE_TEMPERATURE` | `0.2` | Temperature sensor Gaussian standard deviation noise (°C). |
| `FAULT_SHORT_LEAKAGE_CURRENT` | `0.8` | Drainage current during micro-short fault (A). |
| `FAULT_SHORT_HEATING_RATE` | `4.5` | Self-heating during micro-short fault (W). |
| `FAULT_THERMAL_RUNAWAY_MULT` | `4.0` | Exponential coefficient for thermal runaway. |
| `DIAG_DROPOUT_VOLTAGE_THRESHOLD` | `1.0` | Voltage below this triggers dropout diagnostics (V). |
| `DIAG_THERMAL_TEMP_THRESHOLD` | `60.0` | Temp above this triggers runaway diagnostics (°C). |

---

## 🚀 Setup & Running Instructions

### Step 1: Install Dependencies
Navigate to `software/simulator` and run:
```bash
pip install -r requirements.txt
```

### Step 2: Start MongoDB (Optional)
Ensure a MongoDB service is active on Port 27017. If unavailable, the simulator will log data in-memory fallback arrays.

### Step 3: Run the Server
Launch the Flask simulator server:
```bash
python app.py
```
- The backend pacing loop will initialize and log `Simulator background thread active.`
- The server will listen on port `http://localhost:8000`. You can open this URL directly in a web browser to monitor simulation states in a simplified developer console.
- Once running, the visualizer comparison application (on Port 5000) will automatically detect this port and sync telemetry directly.
