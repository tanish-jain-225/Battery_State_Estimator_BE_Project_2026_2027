# Battery Estimator Evaluation Dashboard (True Physics vs. EKF+CC vs. ML-ESN)

An end-to-end Python, Machine Learning, and Flask-based Battery State Estimator comparison and evaluation platform. This project simulates complex lithium-ion battery cell chemistry dynamics, logs real-time telemetry, and compares **Traditional Battery State Estimators (Extended Kalman Filter + Coulomb Counting)** side-by-side against **Modern Data-Driven Machine Learning (Reservoir Computing - Echo State Network)** models relative to the **True physical ground truth** of the cell simulator in real-time.

---

## 📖 Table of Contents
1. [Motivation & Background](#-motivation--background)
2. [Visualiser Directory Structure](#-visualiser-directory-structure)
3. [Battery State Estimator Architecture & Data Flow](#-battery-state-estimator-architecture--data-flow)
4. [Deep Dive: Battery Physics Simulator](#-deep-dive-battery-physics-simulator)
5. [Deep Dive: Traditional Estimators (EKF & SOH)](#-deep-dive-traditional-estimators-ekf--soh)
6. [Deep Dive: Echo State Networks (Reservoir ML)](#-deep-dive-echo-state-networks-reservoir-ml)
7. [Feature Engineering & Datasets](#-feature-engineering--datasets)
8. [API Documentation](#-api-documentation)
9. [Configuration & Tuning Parameters](#-configuration--tuning-parameters)
10. [UI/UX Interface & Interactive Elements](#-uiux-interface--interactive-elements)
11. [Setup & Running Instructions](#-setup--running-instructions)
12. [Serverless Compliance](#serverless-compliance)

---

## 💡 Motivation & Background

Accurate state estimation of Lithium-ion batteries is critical for safe operation, range estimation, and life cycle maximization in Electric Vehicles (EVs) and Grid Storage. The core states are:
- **State of Charge (SOC)**: The remaining capacity relative to the nominal maximum capacity (similar to a fuel gauge).
- **State of Health (SOH)**: The current maximum capacity relative to its brand-new capacity (indicating degradation).

### The Challenge:
Batteries are highly non-linear, time-varying electrochemical systems. Their characteristics shift dynamically under different temperatures, discharge cycles, and degradation states.
- **Traditional Methods**: Standard Coulomb Counting (CC) drifts due to sensor noise. Extended Kalman Filters (EKF) resolve drift but require precise parameters (Equivalent Circuit Models) which are difficult to extract and vary over cell lifetimes.
- **Data-Driven ML**: Machine Learning can map these curves from data. However, traditional recurrent models (LSTMs, GRUs) are computationally too heavy for low-power edge microcontrollers in real-time.
- **The Solution (Reservoir Computing)**: Echo State Networks (ESNs) project input patterns into a high-dimensional recurrent space (the reservoir) through fixed random weights. Only the linear output layer (readout) is trained. This yields high recurrent representation capacity with extremely low computational cost, making it ideal for edge battery state estimator microcontrollers.

This dashboard provides an evaluation sandbox to compare EKF and ESN estimators side-by-side against the absolute true physical state of the battery pack under diverse dynamic load cycles.

---

## 📂 Visualiser Directory Structure

The visualizer's code and assets are organized as follows:

| **[app.py](app.py)** | Main web server Flask application. Exposes endpoints for controls and telemetry, handles local catch-up simulation cycles, and manages background retraining threads. |
| **[config.py](config.py)** | Application configurations, ESN hyperparameters, noise thresholds, fault injection rules, and database connection settings. |
| **[requirements.txt](requirements.txt)** | Python package dependencies for database connection, dashboard observers, and neural network calculations. |
| **[model_rc.pkl](model_rc.pkl)** | Pickled pre-trained ESN model package (contains weights for SOC & SOH estimators, alongside feature normalization factors). |
| **[datasets/](datasets/)** | Time-series datasets (Voltage, Current, Temp, SOC, SOH) used to train the Reservoir ML estimators. |
| **[training/](training/)** | Offline ESN model training scripts and online/offline feature engineering extraction routines. |
| **[simulator/](simulator/)** | Subsystem representing equivalent circuit physics modeling, EKF observers, SOH observers, and unified estimation pipelines. |
| **[static/](static/)** | Client-side dashboard assets (glassmorphic styling, animation assets, JavaScript visual controllers). |
| **[templates/](templates/)** | HTML structure for the Flask comparative evaluation interface. |
| **[tests/](tests/)** | Extensive Unit Test suites validating chemistry tables, equivalent circuit step physics, EKF diagonal stability, and ESN quantization mappings. |

---

## 🏗️ Battery State Estimator Architecture & Data Flow

The platform utilizes a hybrid architecture: a Python simulation engine, a document database (or memory array), and a real-time glassmorphic visualization interface.

```
                   ┌──────────────────────────────┐
                   │   Browser: dashboard.js      │
                   └──────┬────────────────▲──────┘
              POST /api/control            │ GET /api/telemetry
                          │                │
                          ▼                │
                   ┌───────────────────────┴──────┐
                   │    Visualiser Backend:       │
                   │          app.py              │
                   └──────┬────────────────▲──────┘
              Read/Write  │                │ Hydrate classes
              Sim State   ▼                │ & prime reservoir
                   ┌───────────────────────┴──────┐
                   │   Data Store: MongoDB / RAM  │
                   └──────────────────────────────┘
                          │
                          ├─► Battery Physics Simulator (simulator/battery_simulator.py)
                          ├─► 2RC EKF & SOH Estimators (simulator/traditional_estimator.py)
                          └─► Echo State Network ML (training/train_rc.py)
```

1. **Control Actions**: The user issues playback controls (start, pause, reset, drive cycle, chemistry, aging).
2. **On-Demand Synchronization**: The server acts stateless. When a request is received, the backend check loops determine if a simulator is running on port 8000. If online, the visualiser pulls state telemetry directly from the simulator. If offline, the visualiser catch-up loop (`sync_simulation_locally()`) runs the bundled physics model and estimators, saving results back to local state or MongoDB.
3. **ML Inference**: During each simulation step, raw measurements are run through online feature engineering and fed into the ESN model.
4. **Telemetry Logging**: Every tick logs true values, EKF values, ESN values, latency, and system memory consumption.
5. **Interactive Visualization**: The browser polls telemetry and renders it on custom Chart.js curves and a dynamic battery wavefront container.

---

## 🔋 Deep Dive: Battery Physics Simulator

Located in **[battery_simulator.py](simulator/battery_simulator.py)**. It models a **3S (3 Cells in Series)** pack (or 6S for Lead-Acid) using a **first-order Equivalent Circuit Model (ECM)** with two polarization RC branches.

### 1. Electrical Model Dynamics
The terminal voltage is calculated using:
$$V_{\text{terminal}} = V_{\text{OCV}}(SOC) + I \cdot R_0 + V_1 + V_2$$

Where:
- $V_{\text{OCV}}(SOC)$ is the Open Circuit Voltage interpolated from a chemistry-specific OCV-SOC lookup table.
- $I$ is the applied current (Positive = Charging, Negative = Discharging).
- $R_0$ is the internal ohmic resistance.
- $V_1, V_2$ are the polarization voltage drops across the transient RC branches.

The transient RC branches govern the diffusion processes:
$$\frac{dV_1}{dt} = \frac{I - \frac{V_1}{R_1}}{C_1}, \quad \frac{dV_2}{dt} = \frac{I - \frac{V_2}{R_2}}{C_2}$$

### 2. Thermal Model Dynamics
Ohmic and polarization losses generate heat. The cell temperature $T$ is governed by Joule heating and convective cooling:
$$\frac{dT}{dt} = \frac{(I^2 \cdot R_0 + |I \cdot V_1| + |I \cdot V_2|) - h \cdot (T - T_{\text{ambient}})}{C_{\text{thermal}}}$$
Where:
- $h$ is the convection cooling coefficient.
- $C_{\text{thermal}}$ is the cell's thermal capacitance.

### 3. Degradation Model (State of Health)
SOH represents the maximum available capacity fade and internal resistance growth. The capacity degradation rate depends on current amplitude and temperature (Arrhenius relation):
$$\Delta SOH = -1.2 \times 10^{-7} \cdot |I|^{1.3} \cdot e^{0.06(T-25)} \cdot \Delta t$$
To accelerate this effect for testing, toggling "Accelerated Aging" scales $\Delta SOH$ by $\times 1500$.

The internal ohmic resistance increases as capacity fades:
$$R_0(t) = R_{0,\text{nom}} \cdot \left[1.0 + 1.5 \cdot (1.0 - SOH)\right]$$

### 4. Chemistry Models
Configurations are stored in **[battery_chemistry.py](simulator/battery_chemistry.py)**:
- **NMC (Lithium Nickel Manganese Cobalt Oxide)**: Nominal 11.1V (3S), 2.5 Ah capacity. Standard curve.
- **LFP (Lithium Iron Phosphate)**: Nominal 9.6V (3S), 3.0 Ah capacity. Extremely flat OCV curve between 20% and 80% SOC.
- **Lead-Acid**: Nominal 12.0V (6S), 7.0 Ah capacity. High internal resistance, heavy thermal mass.

---

## 🎛️ Deep Dive: Traditional Estimators (EKF & SOH)

Located in **[traditional_estimator.py](simulator/traditional_estimator.py)**.

### 1. Extended Kalman Filter (SOC, $V_1$, $V_2$ Estimation)
The EKF treats the battery as a stochastic linear state-space system around the current state. The state vector is:
$$\mathbf{x} = \begin{bmatrix} SOC & V_1 & V_2 \end{bmatrix}^T$$

#### A. Prediction Step
The state update equations are advanced using:
$$\hat{\mathbf{x}}_{k|k-1} = \mathbf{F} \hat{\mathbf{x}}_{k-1|k-1} + \mathbf{B} I_k$$
$$\mathbf{P}_{k|k-1} = \mathbf{F} \mathbf{P}_{k-1|k-1} \mathbf{F}^T + \mathbf{Q}$$

Where:
- $\mathbf{F}$ is the state transition matrix mapping the RC decay:
  $$\mathbf{F} = \begin{bmatrix} 1 & 0 & 0 \\ 0 & e^{-\Delta t / R_1 C_1} & 0 \\ 0 & 0 & e^{-\Delta t / R_2 C_2} \end{bmatrix}$$
- $\mathbf{Q}$ is the process noise covariance matrix representing model uncertainty:
  $$\mathbf{Q} = \text{diag}([10^{-7}, 10^{-6}, 10^{-6}])$$
- $\mathbf{P}$ is the state estimation covariance.

#### B. Measurement Update (Correction)
Using the terminal voltage measurement $V_{\text{meas}}$, the innovation is calculated:
$$\tilde{y}_k = V_{\text{meas}, k} - \left( V_{\text{OCV}}(\hat{SOC}_{k|k-1}) + I_k R_0 + \hat{V}_{1, k|k-1} + \hat{V}_{2, k|k-1} \right)$$

The measurement Jacobian $\mathbf{H}$ represents the sensitivities of the terminal voltage to the states:
$$\mathbf{H} = \begin{bmatrix} \frac{\partial V_{\text{OCV}}}{\partial SOC} & 1 & 1 \end{bmatrix}$$
The dOCV/dSOC gradient is computed at run-time using central finite differences:
$$\frac{\partial V_{\text{OCV}}}{\partial SOC} \approx \frac{V_{\text{OCV}}(SOC + \epsilon) - V_{\text{OCV}}(SOC - \epsilon)}{2\epsilon}$$

The Kalman Gain $\mathbf{K}$ and updated state $\hat{\mathbf{x}}_{k|k}$ are calculated:
$$\mathbf{S}_k = \mathbf{H} \mathbf{P}_{k|k-1} \mathbf{H}^T + R_{\text{meas}}$$
$$\mathbf{K}_k = \mathbf{P}_{k|k-1} \mathbf{H}^T \mathbf{S}_k^{-1}$$
$$\hat{\mathbf{x}}_{k|k} = \hat{\mathbf{x}}_{k|k-1} + \mathbf{K}_k \tilde{y}_k$$
$$\mathbf{P}_{k|k} = (\mathbf{I} - \mathbf{K}_k \mathbf{H}) \mathbf{P}_{k|k-1}$$

### 2. Traditional SOH & Temperature-Compensated Resistance Tracker
The SOH tracking module estimates resistance growth from step voltage changes and steady-state conditions:
- **Arrhenius Temperature Correction**: Estimates are compensated for temperature variations to prevent cold temperatures or self-heating spikes from biasing SOH calculations:
  $$\text{temp\_effect} = \exp\left(1500.0 \cdot \left(\frac{1}{T_{\text{meas}} + 273.15} - \frac{1}{298.15}\right)\right)$$
  Estimated resistances are divided by $\text{temp\_effect}$ before filtering.
- **Dynamic Transient Observer**: Updates the internal resistance $R_0$ during load current steps ($|\Delta I| > 0.2$ A):
  $$R_{0,\text{calc}} = \frac{|\Delta V|}{|\Delta I|}$$
- **Static Observer**: Enables continuous resistance tracking under steady-state loads ($|I| > 0.2$ A and stable current) after a 30-second startup convergence delay (resolves startup transient drift):
  $$R_{0,\text{static}} = \frac{|OCV(SOC) + V_1 + V_2 - V_t|}{|I|}$$
- **Capacity Estimation**: The SOH is computed by inverting the ohmic resistance growth relation:
  $$SOH_{\text{est}} = 1.0 - \frac{\frac{R_0}{R_{0,\text{nom}}} - 1.0}{1.5}$$

---

## 🧠 Deep Dive: Echo State Networks (Reservoir ML)

Located in **[train_rc.py](training/train_rc.py)**. ESNs utilize high-dimensional temporal representations.

### 1. Reservoir Initialization
- **Input Weights ($\mathbf{W}_{\text{in}}$)**: Randomly generated within range $[-input\_scaling, input\_scaling]$. Dimension: $N_{\text{reservoir}} \times (1 + N_{\text{inputs}})$.
- **Reservoir Weights ($\mathbf{W}_{\text{res}}$)**: Sparse random matrix scaled to ensure a spectral radius $\rho < 1$, guaranteeing the **Echo State Property** (reservoir dynamics fade out after a certain time, preventing state divergence). Dimension: $N_{\text{reservoir}} \times N_{\text{reservoir}}$.

### 2. Reservoir State Update
For an input vector $\mathbf{u}(t)$:
$$\mathbf{x}(t) = (1 - \alpha)\mathbf{x}(t-1) + \alpha \tanh\left(\mathbf{W}_{\text{in}} [1; \mathbf{u}(t)] + \mathbf{W}_{\text{res}} \mathbf{x}(t-1)\right)$$
Where:
- $\alpha$ is the leak rate (controls the temporal state integration rate).
- $[1; \mathbf{u}(t)]$ is the input vector with a bias term.

### 3. Readout Training (Ridge Regression)
The readout weights $\mathbf{W}_{\text{out}}$ map the states to the outputs:
$$\mathbf{y}(t) = \mathbf{W}_{\text{out}} [1; \mathbf{u}(t); \mathbf{x}(t)]$$
Given training sequences of inputs $\mathbf{U}$ and target metrics $\mathbf{Y}$ (SOC, SOH):
1. **Washout Phase**: The reservoir is driven with the first $50$ inputs (`Config.ESN_WASHOUT_STEPS`) to clear arbitrary zero-initialization states.
2. **Collect States**: Remaining reservoir states are stacked into a matrix $\mathbf{X}$.
3. **Regularized Fit**: Solve using Ridge Regression (Tikhonov Regularization) to avoid overfitting:
   $$\mathbf{W}_{\text{out}} = \mathbf{Y} \mathbf{X}^T (\mathbf{X} \mathbf{X}^T + \lambda \mathbf{I})^{-1}$$
   Where $\lambda$ is the ridge parameter (regularization factor).

### 4. Online Priming (Cold Start Solution)
To resolve startup estimation error on cold-start (where the reservoir states are empty but the battery is already partially charged):
- Upon reset/start, the backend feeds the initial OCV voltage and zero current to the model for `Config.ESN_PRIMING_STEPS` ($50$ steps). This pre-populates the recurrent reservoir states with initial battery voltage properties before live predictions begin.

### 5. Hybrid SOH and RUL Estimator
To correct the time-resolution mismatch between ESN training (1ms step sizes) and online execution (1s step sizes), the ESN SOH prediction dynamically blends the ESN reservoir output with the physics-informed EKF traditional SOH estimate:
$$\text{esn\_soh\_pred} = 0.02 \cdot \text{esn\_soh\_pred\_raw} + 0.98 \cdot \text{trad\_soh}$$
This guarantees a highly accurate, noise-filtered ESN Remaining Useful Life (RUL) cycle output that correctly tracks battery degradation.

---

## 📊 Feature Engineering & Datasets

### 1. Raw Training Data
The ESN models are trained using training files in `datasets/`:
- `Voltage`: Dynamic terminal voltage.
- `Current`: Dynamically applied charge and discharge.
- `Temperature`: Cell thermal gradients.
- `SOC / SOH`: Ground truth indices.

### 2. Feature Extraction
Features are extracted offline in **[feature_engineering.py](training/feature_engineering.py)** and replicated online at runtime:
1. **Voltage**: Terminal voltage $V$.
2. **Current**: Load current $I$.
3. **Temperature**: Cell temperature $T$ (excluded from selected ESN inputs to prevent out-of-distribution thermal bias).
4. **Voltage Gradient ($dV/dt$)**: Difference between successive voltage ticks:
   $$\text{Voltage Gradient} = V_k - V_{k-1}$$
   *Note: At runtime, this gradient is normalized by $(Config.DATASET\_TIME\_STEP / Config.SIMULATION\_STEP\_DELAY)$ to align simulator timing resolutions with the training CSV dataset.*
5. **Current Moving Average ($I_{\text{MA}}$)**: A rolling average window (default window size $5$) representing energy density integration.

---

## 📡 API Documentation

### 1. `GET /api/status`
Fetches connection, simulation states, and model load flags.
- **Response**:
```json
{
  "sim_running": true,
  "active_cycle": "udds",
  "accelerated_aging": false,
  "model_loaded": true,
  "mongodb_connected": true,
  "battery_time": 45.0,
  "chemistry": "nmc",
  "ekf_mismatch": 1.0,
  "quantize_mode": "float32",
  "simulator_port_online": true,
  "T_ambient": 25.0,
  "fault_thermal": false,
  "fault_dropout": false,
  "fault_short": false,
  "soc_rmse": 0.000589,
  "soh_rmse": 0.004211
}
```

### 2. `POST /api/control`
Sends commands to direct the simulator configuration and state.
- **Request Body Options**:
  - `command`: `"start"`, `"stop"`, `"pause"`, or `"reset"`
  - `chemistry`: `"nmc"`, `"lfp"`, `"lead_acid"`, or `"li_ion"`
  - `active_cycle`: `"udds"`, `"hwfet"`, `"us06"`, `"constant"`, or `"charge"`
  - `accelerated_aging`: `true` or `false`
  - `T_ambient`: `float`
  - `fault_thermal`: `true` or `false`
  - `fault_dropout`: `true` or `false`
  - `fault_short`: `true` or `false`
  - `ekf_mismatch`: `float`
  - `quantize_mode`: `"float32"`, `"int16"`, or `"int8"`
- **Response**: Returns the updated status configuration.

### 3. `GET /api/telemetry`
Returns the historical records of the simulation run.
- **Response**:
```json
{
  "model_loaded": true,
  "data": [
    {
      "time": 0.0,
      "voltage": 12.6,
      "current": 0.0,
      "temperature": 25.0,
      "ekf_soc": 1.0,
      "ekf_soh": 1.0,
      "esn_soc": 1.0,
      "esn_soh": 1.0,
      "cc_soc": 1.0,
      "trad_soh": 1.0,
      "true_soc": 1.0,
      "true_soh": 1.0,
      "ekf_time": 0.08,
      "esn_time": 1.25,
      "cpu_usage": 0.5,
      "mem_usage": 48.2,
      "faults": [],
      "sop_charge_curr": 49.5,
      "sop_discharge_curr": 44.6,
      "sop_charge_pwr": 60.0,
      "sop_discharge_pwr": 446.0,
      "ekf_soe": 1.0,
      "esn_soe": 1.0,
      "ekf_rul_cycles": 1000.0,
      "esn_rul_cycles": 1000.0,
      "energy_remaining_wh": 28.2
    }
  ]
}
```

---

## ⚙️ Configuration & Tuning Parameters

All settings are configured inside **[config.py](config.py)** and can be overriden via environment variables:

| Setting | Default Value | Description |
| :--- | :--- | :--- |
| `MONGODB_URI` | `"mongodb://localhost:27017/"` | Database host string. Falls back to RAM store if offline. |
| `SIMULATION_STEP_DELAY` | `1.0` | Simulator tick interval (seconds). |
| `TELEMETRY_RESPONSE_LIMIT` | `150` | Maximum points sent to the browser to prevent lag. |
| `ESN_SELECTED_FEATURE_INDICES` | `[0, 1, 3, 4]` | Features maps: `[V, I, dV/dt, I_MA]`. |
| `ESN_SOC_RESERVOIR` | `300` | Number of recurrent nodes in the SOC ESN. |
| `ESN_SOC_SPECTRAL_RADIUS` | `0.90` | Spectral radius of the SOC ESN (reservoir memory). |
| `ESN_SOC_LEAK_RATE` | `0.3` | Leak rate of the SOC ESN. |
| `ESN_SOC_RIDGE_PARAM` | `1e-4` | Overfitting regularization parameter ($\lambda$). |
| `ESN_SOH_RESERVOIR` | `200` | Number of recurrent nodes in the SOH ESN. |
| `ESN_SOH_SPECTRAL_RADIUS` | `0.70` | Spectral radius of the SOH ESN (slower transients). |
| `ESN_SOH_LEAK_RATE` | `0.05` | Leak rate of the SOH ESN. |

---

## 🎨 UI/UX Interface & Interactive Elements

The frontend is built using a custom light-mode glassmorphic design system:

1. **Ambient Light Glassmorphism**: Cards are designed with translucent white layers (`rgba(255, 255, 255, 0.72)`) overlaying multi-layered soft shadows, creating premium visual hierarchy.
2. **Battery Wavefront Container**:
   - Displays the true physical SOC level inside a liquid wave animation.
   - Triggers dynamic floating bubble particles when charging.
   - Alters OCV border coloring based on charge depletion.
3. **Side-by-Side Dual Deviation Curves**: Visualizes estimation errors $|True - EKF|$ and $|True - ESN|$ simultaneously.
4. **Interactive Action Toggles**: Smooth transitions, buttons with offset scales, and custom select fields.
5. **Educational Tooltips**: Provides context about estimator algorithms on hover.

---

## 🚀 Setup & Running Instructions

The platform is designed to be highly flexible:
1. **Visualizer App (`app.py`)**: Can run entirely self-contained using its bundled physics simulator if the standalone simulator is offline (ideal for serverless/stateless cloud deployments).
2. **Segregated Mode**: If the standalone simulator (under `software/simulator`) is run on Port 8000, `app.py` automatically detects it, halts local simulation catch-ups, and pulls real-time synchronized telemetry.

### Step 1: Install Dependencies
```bash
pip install -r software/visualiser/requirements.txt
```

### Step 2: Set Up Database (Optional)
Start a local MongoDB instance at `mongodb://localhost:27017/`. If MongoDB is disconnected, the visualiser will silently fall back to local memory data storage.

### Step 3: Run Unit Tests (Recommended Verification)
To verify calculations, observers, and ESN quantization operations:
```bash
python -m unittest software/visualiser/tests/test_estimators.py
```

### Step 4: Train ESN Models (Optional)
If `model_rc.pkl` is missing or needs retraining:
```bash
python software/visualiser/training/train_rc.py
```
This trains the SOC and SOH ESNs on the `datasets/training_ev_battery_dataset_multiclass.csv` EV data and registers weights locally and to MongoDB.

### Step 5: Launch Web Visualizer
Start the Flask web visualizer:
```bash
python software/visualiser/app.py
```
*Navigate to `http://localhost:5000/` to open the comparison dashboard.*

---

## ☁️ Serverless Compliance

Standard simulators require stateful background threads. Since serverless deployments (like Lambdas) terminate execution between HTTP requests, background threads cannot be utilized.

To run 100% serverlessly:
- **On-Demand Synchronization**: Inside `sync_simulation_locally()`, the server checks the elapsed real-world time since the last API request.
- **Catch-up Ticks**: The simulator runs exactly the number of ticks that *should* have occurred during that elapsed time.
- **Lag Caps**: To prevent "catch-up lag storms" on cold start, if the server has been inactive for a long time, the catch-up loop limits the maximum number of ticks to run.
- **Stateless Persistence**: Hydrates simulator and estimator classes directly from MongoDB/memory payloads during each request, making the system 100% stateless.
- **Weights Registry**: ESN model package is serialized and cached dynamically inside a MongoDB model registry (`model_weights` collection), avoiding local file write blocks on serverless read-only partitions.
