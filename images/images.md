# 📊 Visual Interface & Dashboard Guide

This document provides a comprehensive overview of the two key web-based interfaces in the **Cyber-Physical Battery State Estimator** ecosystem. These interfaces enable real-time battery simulation, safety-critical fault injection, and state-of-charge (SOC) / state-of-health (SOH) estimation comparison.

---

## ⚡ 1. BMS Physical Simulator (`http://localhost:8000`)

The **BMS Physical Simulator** acts as the high-fidelity cyber-physical cell. It models the actual physical battery pack using a first-order equivalent circuit model (ECM) with dual RC branches, thermal feedback, degradation profiles, and a fault injector.

### Interface Walkthrough

Below are screenshots captured during different phases of the physical simulation.

#### A. Active Simulation & Telemetry Injection
At startup, the simulator generates real-time telemetry based on the selected drive cycle. In this state, it streams continuous battery variables (voltage, current, temperature, and true states) to MongoDB.

![BMS Physical Simulator - Active Drive Cycle (UDDS)](assets/Screenshot%202026-06-25%20095034.png)

**Key Features Shown in the Screenshot:**
1. **Telemetry Playback Controls**: Interactive controls allowing users to `Start`, `Pause`, `Stop`, and `Reset` the telemetry generator.
2. **Configuration Profiles**:
   - **Battery Cell Chemistry**: Selectable battery chemistries (e.g., `Li-Ion NMC — 3S Pack (11.1 V)`).
   - **Current Excitation Drive Cycle**: Dynamic drive cycle profiles including the standard **Urban Driving Schedule (UDDS)** and **US06**.
   - **Accelerated SOH Aging**: A toggle that scales physical battery degradation by $1500\times$ for rapid capacity fade and internal resistance growth testing.
3. **Environment & Faults Panel**:
   - **Ambient Temperature Slider**: Dynamically adjusts ambient temperatures from $-20^\circ\text{C}$ to $50^\circ\text{C}$, directly impacting internal temperatures and degradation rate.
   - **Fault Injectors**: Toggles to inject safety-critical anomalies:
     - **Internal Micro-Short**: Injects a $0.8\text{ A}$ internal self-discharge bypass current.
     - **Thermal Runaway Spike**: Simulates exponential exothermic runaway heat generation.
     - **Sensor Dropout Fault**: Forces measured voltage and current to 0 to test estimator robustness.
4. **Live Telemetry Feed**:
   - Displays current simulation parameters: **Elapsed Time**, **Terminal Voltage**, **Load Current**, and **Cell Temperature**.
   - Showcases the **True SOC** ($100.0\%$) and **True SOH** ($99.6\%$) values calculated directly by the physics engine.
   - Displays the telemetry transmission link status (`TRANSMITTING`) and the count of records pushed to the database.

---

#### B. Progressed Aging & Thermal Response
As the simulation continues, physical processes like capacity fade and temperature-dependent resistance growth evolve. Below is the simulator state at a later time step:

![BMS Physical Simulator - Progressed Aging & Telemetry Feed](assets/Screenshot%202026-06-25%20095148.png)

**Observations from the Progressed State:**
- **Simulation Time**: Progressed to $115\text{ s}$ under the active UDDS cycle.
- **State of Health (SOH) Degradation**: Due to **Accelerated SOH Aging** being active, the **True SOH** has dropped to $93.2\%$, showing noticeable cell degradation over a short duration.
- **Dynamic Load Profile**: The load current shifts to a negative value ($-0.23\text{ A}$), demonstrating regenerative braking charging telemetry.
- **Thermal Development**: Cell temperature has risen to $30.7^\circ\text{C}$ due to $I^2 R$ resistive heating under dynamic loads.

---

## 📈 2. Battery State Estimator Operator Console (`http://localhost:5000`)

The **Operator Comparative Dashboard** acts as the primary engineering cockpit. It pulls the physical ground truth from MongoDB or local simulator threads and runs estimation observers in parallel: **Coulomb Counting (CC)**, the **Extended Kalman Filter (EKF)**, and a trained **Echo State Network (ESN / Reservoir Computing)** model.

### Interface Walkthrough

#### A. Comprehensive Operator Dashboard Layout
This glassmorphic dashboard provides side-by-side comparative diagnostics to validate traditional estimators against machine learning alternatives.

![Battery State Estimator Dashboard - Overview](assets/Screenshot%202026-06-25%20095057.png)

**Key Features Shown in the Screenshot:**
1. **System Health Status Bar**:
   - Real-time connection indicators: `Sim Service: Online`, `MongoDB: Connected`, `Chemistry: Li-ion NMC`, and `ESN Model: Active`.
   - **Historical Scrubbing Tracker**: Displays the current playback time index ($53\text{ s}$) with a button to `Resume Live` streaming.
2. **Estimator Parameters (Left Column)**:
   - **EKF Parameter Mismatch**: Dropdown to simulate model mismatch (e.g., incorrect capacity or resistance assumptions) to evaluate EKF robustness.
   - **ML Quantization Precision**: Dropdown to switch model precision (e.g., `Float32` standard vs. `Q15 Fixed-Point` integer math matching the STM32 edge MCU implementation).
3. **Live Stats Grid**:
   - Displays active cell measurements and derived metrics: **Terminal Voltage**, **Load Current**, **Cell Temp**, **State of Energy (SOE)**, **State of Power (SOP)**, and **Remaining Useful Life (RUL)**.
4. **State of Charge (SOC) Estimation Card**:
   - Compares the physical ground truth ($99.4\%$) to the **EKF + CC Estimation** ($99.7\%$, error: $0.25\%$) and **ESN Reservoir ML** ($96.5\%$, error: $2.88\%$).
5. **State of Health (SOH) Estimation Card**:
   - Compares the physical ground truth ($97.8\%$) to the traditional **EKF Resistance Tracker** ($94.2\%$, error: $3.61\%$) and the data-driven **ESN Reservoir ML** ($94.3\%$, error: $3.50\%$).
6. **Model Retraining Panel (Lower Left)**:
   - Contains a trigger button to `Retrain ESN Weights` asynchronously with an embedded training log console.

---

#### B. Comparative Estimation Charts & Error Analysis
A detailed view of the estimation tracking curves highlights the differences in convergence rates and robustness between EKF and Reservoir Computing.

![Battery State Estimator Dashboard - Charts Close-up](assets/Screenshot%202026-06-25%20095127.png)

**Insights from Close-up Charts:**
- **SOC Tracking**:
  - The EKF + CC estimator aligns closely with the **True SOC (Reference)** curve.
  - The **ESN Reservoir ML** tracker follows the trend but displays minor deviation peaks (dropping to $85.4\%$ SOC vs. $99.1\%$ Ground Truth) under aggressive transient current changes. This demonstrates the typical trade-off between structural stability (Kalman Filters) and purely data-driven estimators (ESNs) on out-of-distribution dynamic cycles.
- **SOH Tracking**:
  - Both the EKF resistance observer ($94.3\%$) and ESN estimator ($94.4\%$) accurately converge toward the **True SOH (Reference)** ($96.9\%$), validating the SOH monitoring loops.
