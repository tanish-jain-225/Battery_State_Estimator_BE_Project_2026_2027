# BE Capstone Project

## Project Title

**Battery State Estimator: Cyber-Physical State Estimation and Edge Diagnostics**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat&logo=python)](https://www.python.org/)
[![Embedded C](https://img.shields.io/badge/Embedded_C-C99-orange?style=flat)](https://en.cppreference.com/w/c/99)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-black?style=flat&logo=flask)](https://flask.palletsprojects.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0%2B-green?style=flat&logo=mongodb)](https://www.mongodb.com/)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen?style=flat)](.github/workflows/ci.yml)

A cyber-physical battery state estimator system that delivers accurate, real-time State of Charge (SOC), State of Health (SOH), State of Energy (SOE), State of Power (SOP), and thermal safety monitoring under dynamic EV-style drive-cycle workloads. It combines a 2-RC physics simulator, traditional observers (Sage-Husa EKF, RLS), Echo State Networks, and low-power embedded C edge diagnostics.

---

## Table of Contents
1. [Team Details](#team-details)
2. [Guide Details](#guide-details)
3. [Problem Statement](#problem-statement)
4. [Abstract](#abstract)
5. [Objectives](#objectives)
6. [Scope of the Project](#scope-of-the-project)
7. [Existing System](#existing-system)
8. [Proposed System](#proposed-system)
9. [System Architecture](#system-architecture)
10. [Hardware Requirements](#hardware-requirements)
11. [Software Requirements](#software-requirements)
12. [Technologies Used](#technologies-used)
13. [Methodology](#methodology)
14. [Security and Data Privacy](#security-and-data-privacy)
15. [Project Timeline](#project-timeline)
16. [Weekly Progress Updates](#weekly-progress-updates)
17. [Design Files](#design-files)
18. [Circuit Diagram](#circuit-diagram)
19. [Flowchart / Algorithm](#flowchart--algorithm)
20. [Implementation Details](#implementation-details)
21. [Code Structure](#code-structure)
22. [How to Run the Project](#how-to-run-the-project)
23. [Testing and Results](#testing-and-results)
24. [Applications](#applications)
25. [Advantages](#advantages)
26. [Limitations](#limitations)
27. [Future Scope](#future-scope)
28. [Research Paper / Publication](#research-paper--publication)
29. [References](#references)
30. [Repository Update Guidelines](#repository-update-guidelines)

---

## Team Details

| Sr. No. | Name of Student | Roll No. | Branch | Email ID |
|---|---|---|---|---|
| 1 | Tanish Sanghvi | 56 | Automation and Robotics | 2023.tanish.sanghvi@ves.ac.in |
| 2 | Akshay Nambiar | 40 | Automation and Robotics | 2023.akshay.nambiar@ves.ac.in |
| 3 | Sanjana Patankar | 47 | Automation and Robotics | 2023.sanjana.patankar@ves.ac.in |
| 4 | Satvik Verma | 60 | Automation and Robotics | 2023.satvik.verma@ves.ac.in |

---

## Guide Details

**Project Guide:** Dr. Kadambari Sharma   
**Department:** Automation and Robotics  
**Institute:** VESIT, Mumbai  

---

## Problem Statement

> The aim of this project is to design and develop a cyber-physical battery state estimator system that solves the problem of accurate, real-time State of Charge (SOC), State of Health (SOH), and thermal safety monitoring under dynamic EV-style workloads by using a hybrid approach of Extended Kalman Filtering, Echo State Networks, and low-power embedded edge diagnostics.

---

## Abstract

Reliable SOC and SOH estimation is essential for electric vehicles, smart grids, and battery-powered systems. Traditional Battery Management Systems often rely on Coulomb Counting or Extended Kalman Filters, which can drift under aging, temperature changes, and unmodeled cell behavior. Deep recurrent neural networks can improve sequence modeling, but they are often too expensive for small microcontrollers. This project implements a cyber-physical battery estimation framework that combines a 2-RC electro-thermal physics simulator, traditional EKF and resistance-based SOH observers, Echo State Network estimators, and an optimized embedded ESN classifier. The software side includes two Flask services: a physics simulator and a comparative visualiser dashboard. The hardware side includes C99 inference code using Compressed Sparse Row reservoir matrices and optional Q12/Q15 fixed-point arithmetic. The system supports fault injection for thermal runaway, sensor dropout, and micro-short conditions, enabling validation of estimator robustness and edge safety classification. Current validation targets include sub-1.5 percent SOC RMSE, sub-1.0 percent SOH RMSE, 98.40 percent thermal safety classification accuracy, and a 6.7x sparse reservoir speedup.

---

## Objectives

1. To study battery SOC, SOH, and thermal safety estimation methods.
2. To design a cyber-physical architecture combining simulation, estimation, visualization, and edge inference.
3. To implement a 2-RC ECM physics simulator with fault injection and telemetry logging.
4. To implement EKF, Coulomb Counting, resistance-based SOH, and ESN estimators.
5. To optimize an ESN classifier for STM32-class edge microcontrollers using CSR and fixed-point techniques.
6. To test and validate estimator accuracy, diagnostic behavior, and deployment readiness.
7. To document the project for academic review, demonstration, and future extension.

---

## Scope of the Project

- Design and development of a working cyber-physical battery estimator prototype.
- Flask-based simulator for battery physics, aging, noise, and fault injection.
- Flask-based visualiser dashboard for SOC, SOH, SOE, SOP, RUL, and fault diagnostics.
- Embedded C ESN classifier for Normal, Warning, and Critical thermal states.
- ESN training scripts, generated C headers, and reproducible artifact policy.
- MongoDB-backed telemetry storage with in-memory fallback for local execution.
- Render deployment support for simulator and visualiser as standalone services.

---

## Existing System

Existing BMS approaches commonly use Coulomb Counting, voltage lookup tables, or Kalman filters. These methods are useful but have limitations:

- **High drift:** Coulomb Counting accumulates error without periodic correction.
- **Model mismatch:** EKF performance depends on accurate battery parameters and OCV-SOC curves.
- **Limited aging awareness:** Basic systems may not adapt well to resistance growth and capacity fade.
- **Heavy ML alternatives:** LSTM/GRU-style models can be too costly for low-power MCUs.
- **Weak safety diagnostics:** Many systems do not classify thermal warning states directly on edge hardware.
- **Limited observability:** Operators often lack a live comparison between ground truth, traditional observers, and ML estimators.

---

## Proposed System

The proposed system combines physics-based modeling, classical observers, and reservoir computing in one integrated workflow.

- **Main idea:** Use a 2-RC electro-thermal simulator as the physical reference, run EKF/CC/ESN estimators in parallel, and deploy an optimized ESN classifier on edge hardware.
- **How it works:** The simulator generates battery telemetry and stores it in MongoDB or an in-memory buffer. The visualiser reads telemetry, estimates SOC/SOH, computes diagnostics, and displays results. The hardware classifier consumes voltage, current, and temperature inputs and classifies the thermal safety state.
- **Major components:** Flask simulator, Flask visualiser, MongoDB, ESN training pipeline, STM32-style C classifier, generated weight headers, and validation tests.
- **Expected benefits:** More robust estimation, clearer operator visibility, lightweight edge diagnostics, and reproducible academic demonstration.

---

## System Architecture

```mermaid
flowchart LR
    Cell["Battery cell or simulator telemetry\nVoltage, current, temperature"]
    Edge["STM32 edge ESN classifier\nCSR reservoir + Q12/Q15 option"]
    Sim["Flask physics simulator\n2-RC ECM, thermal model, faults"]
    DB["MongoDB or in-memory fallback\ntelemetry and shared state"]
    Dash["Flask visualiser dashboard\nEKF, CC, ESN, diagnostics"]

    Cell --> Edge
    Cell --> Sim
    Edge -->|"UART / status LED"| Dash
    Sim --> DB
    DB --> Dash
    Dash -->|"control and fault toggles"| Sim
```

The simulator produces physical telemetry. The visualiser consumes telemetry and runs estimators. MongoDB provides persistence when available. The embedded ESN classifier provides edge safety state inference and can be tested through the desktop C simulator.

---

## Hardware Requirements

| Sr. No. | Component | Specification | Quantity | Purpose |
| ------- | --------- | ------------- | -------- | ------- |
| 1 | STM32 Nucleo Board | ARM Cortex-M class MCU, preferably with UART and GPIO | 1 | Runs edge ESN classifier |
| 2 | On-board / external LED | GPIO `PA5` or equivalent | 1 | Visual safety status output |
| 3 | USB / ST-Link cable | 115200 baud serial support | 1 | Flashing and UART monitoring |
| 4 | Host PC | Windows/Linux/macOS with Python and C compiler | 1 | Runs simulator, visualiser, training, and C simulation |

---

## Software Requirements

| Sr. No. | Software / Tool | Version | Purpose |
| ------- | --------------- | ------- | ------- |
| 1 | Python | 3.8+ | Simulator, visualiser, training, tests |
| 2 | Flask + Gunicorn | Flask 2.0+, Gunicorn 20.1+ | Web services and deployment |
| 3 | NumPy / Pandas / SciPy | See requirements files | Simulation, estimation, model training |
| 4 | MongoDB / MongoDB Atlas | 6.0+ recommended | Persistent telemetry and model registry |
| 5 | GCC / Clang / MSVC | C99 compatible | Desktop C classifier simulation |
| 6 | STM32CubeIDE or equivalent | Current stable version | MCU firmware build and flashing |

---

## Technologies Used

* Embedded C (C99)
* Python
* Flask
* MongoDB
* NumPy, Pandas, SciPy
* Echo State Networks / Reservoir Computing
* Extended Kalman Filter
* Compressed Sparse Row matrix representation
* Q12/Q15 fixed-point arithmetic
* HTML, CSS, JavaScript dashboard
* Render deployment for standalone web services

---

## Methodology

1. Literature survey on battery ECMs, Kalman filtering, SOH estimation, and reservoir computing.
2. Problem identification for robust SOC/SOH estimation and low-power thermal diagnostics.
3. Requirement analysis for software services, data flow, MCU constraints, and deployment.
4. System design for simulator, visualiser, estimator pipeline, and embedded classifier.
5. Hardware/software development using Python Flask services and C99 firmware logic.
6. Integration through MongoDB telemetry, local fallback buffers, and shared model artifacts.
7. Testing and validation through unit tests, simulated faults, and C simulator runs.
8. Documentation, deployment preparation, artifact policy, and academic reporting.

---

## Security and Data Privacy

To support production-grade deployment guidelines, the system implements the following security mechanisms:

* **Zero-Configuration Cryptographic Gating**: Rather than requiring a new, separate secret configuration key, the system automatically derives a secure 64-character SHA-256 signature token from the **pre-existing** `MONGODB_URI` environment connection string.
* **Dynamic API Signature Verification**: Both the Simulator and Visualizer service endpoints (all routes under `/api/*`) dynamically check incoming requests. Requests must present the correct derived SHA-256 signature in the `X-API-Key` HTTP header (or the `api_key` URL query parameter) to succeed.
* **Inter-Service Request Delegation**: The Visualizer features a centralized dispatcher (`make_simulator_request`) that hashes the shared `MONGODB_URI` database string on the fly and automatically signs all outgoing HTTP calls to the physics simulator.
* **Fails-Open Local Development**: If the `MONGODB_URI` contains `localhost` or `127.0.0.1` (the default configurations in local developer `.env` files), the authentication checks are bypassed automatically. This allows seamless out-of-the-box offline runs for the student team.
* **Credentials Sanitization**: Highly sensitive parameters, including MongoDB Atlas connection passwords, are loaded dynamically into runtime memory and are completely omitted from the repository's tracked code history.

---

## Project Timeline

| Week / Month | Task Planned | Status |
| ------------ | ------------ | ------ |
| Week 1 | Problem finalization | Completed |
| Week 2 | Literature survey | Completed |
| Week 3 | Requirement analysis | Completed |
| Week 4 | System design | Completed |
| Week 5 | Prototype development | Completed |
| Week 6 | Testing and validation | In Progress |
| Week 7 | Documentation and deployment polish | In Progress |
| Week 8 | Paper writing and final demonstration | In Progress |

---

## Weekly Progress Updates

| Week | Date | Work Completed | Work Planned for Next Week | Issues / Challenges | GitHub Commit Link |
| ---- | ---- | -------------- | -------------------------- | ------------------- | ------------------ |
| Week 1 | 2026-05-07 | Finalized problem statement and repository structure | Literature review | None | Repository history |
| Week 2 | 2026-05-14 | Reviewed ECM, EKF, and ESN approaches | Define architecture | Parameter modeling | Repository history |
| Week 3 | 2026-05-21 | Defined simulator, dashboard, and MCU responsibilities | Design ESN dimensions | Fixed-point planning | Repository history |
| Week 4 | 2026-05-28 | Designed 2-RC simulator and estimator pipeline | Build simulator/dashboard | OCV and thermal tuning | Repository history |
| Week 5 | 2026-06-04 | Implemented Flask services and dashboard | Edge classifier work | Porting ESN to C | Repository history |
| Week 6 | 2026-06-11 | Added CSR and Q12/Q15 inference paths | Fault testing | LUT accuracy | Repository history |
| Week 7 | 2026-06-18 | Added tests, documentation, and validation flow | Deployment polish | MongoDB fallback behavior | Repository history |
| Week 8 | 2026-06-25 | Added CI, Render guidance, API key security, and tests | Final review | None | Repository history |

---

## Design Files

| File Type | File Name / Link | Description |
| --------- | ---------------- | ----------- |
| System Specification | [docs/system_specification.md](docs/system_specification.md) | Interfaces, data flow, APIs, security, and validation scope |
| Operations Guide | [docs/OPERATIONS.md](docs/OPERATIONS.md) | Local setup, run, security settings, and verification steps |
| Render Deployment | [docs/DEPLOY_RENDER.md](docs/DEPLOY_RENDER.md) | Standalone Render deployment instructions |
| Demo Checklist | [docs/DEMO_CHECKLIST.md](docs/DEMO_CHECKLIST.md) | Review and viva demonstration checklist |
| Circuit / Pinout Reference | [hardware/main.h](hardware/main.h) | Host HAL mocks and STM32-style pin assumptions |
| Simulation File | [software/simulator/battery_simulator.py](software/simulator/battery_simulator.py) | 2-RC electro-thermal battery model |
| Embedded Firmware | [hardware/main.c](hardware/main.c) | C99 ESN edge classifier |

---

## Circuit Diagram

The physical battery is represented using a 2-RC equivalent circuit model:

```text
           +----[ R1 ]----+
           |              |
   OCV ----+----[ C1 ]----+----+----[ R0 ]---- Terminal Voltage
                                |
           +----[ R2 ]----+     |
           |              |     |
           +----[ C2 ]----+-----+
```

The embedded diagnostic output uses GPIO `PA5` for the status LED and UART2 for serial diagnostic output.

---

## Flowchart / Algorithm

```mermaid
flowchart TD
    A["Start"] --> B["Initialize simulator, estimators, model weights, and UI"]
    B --> C["Read or generate voltage, current, and temperature telemetry"]
    C --> D["Store telemetry in MongoDB or in-memory buffer"]
    D --> E["Run EKF, Coulomb Counting, SOH tracker, and ESN estimator"]
    E --> F["Run fault diagnostics and edge safety classification"]
    F --> G["Display dashboard metrics and charts"]
    G --> H["Transmit or log diagnostic output"]
    H --> C
```

### Algorithm

1. Start.
2. Initialize simulator, estimator states, ESN weights, database connection, and dashboard.
3. Generate or read battery voltage, current, and temperature.
4. Apply drive-cycle behavior, noise, aging, and selected fault injection.
5. Store telemetry in MongoDB or local fallback memory.
6. Estimate SOC and SOH using EKF, Coulomb Counting, resistance tracking, and ESN.
7. Classify thermal safety state using the edge ESN classifier.
8. Display, store, and transmit results.
9. Repeat until stopped.

---

## Implementation Details

### Hardware Implementation

The hardware module is implemented in C99 for low-power STM32-style targets (e.g., ARM Cortex-M). Key elements include:
* **ESN Classifier**: Uses a 3-input (Voltage, Current, Temperature) Echo State Network with a 50-node reservoir to classify battery safety into 3 states: `Normal`, `Warning`, and `Critical`.
* **Sparse Matrix Optimization**: To optimize for microcontrollers, the reservoir matrix is stored in Compressed Sparse Row (CSR) format, skipping zero-value multiplications and yielding a 6.7x execution speedup.
* **Fixed-Point Arithmetic Option**: Supports optional Q12 (for inputs) and Q15 (for reservoir states and weights) fixed-point modes, utilizing a lookup-table approximation of the `tanh` activation function to run efficiently without hardware floating-point support.
* **Hardware Visual Output**: Integrates GPIO `PA5` mapping to drive status LEDs for immediate visual fault alarms directly on-chip.

### Software Implementation

The software core is structured as a decoupled cyber-physical architecture composed of:
1. **Physics Simulator Service**: A Flask application modeling 2-RC equivalent circuit model (ECM) cell physics, non-linear open circuit voltage (OCV), thermodynamic heating, capacity fade/resistance aging, sensor noise, and safety fault injection.
2. **Visualiser Dashboard Service**: A Flask web application that serves as the comparison dashboard. It retrieves live/historical telemetry, feeds data through the multi-estimator pipeline, and renders comparative charts.
3. **Database Layer**: Leverages MongoDB Atlas (with automatic in-memory fallback buffers) to persistently store timeseries readings and the serialized machine learning model registry.

### Advanced State Estimators

To ensure state estimation robustness under dynamic load profiles, the visualiser runs a parallel pipeline:
* **State of Charge (SOC)**: Estimated in parallel using Coulomb Counting (CC), a Sage-Husa Adaptive Extended Kalman Filter (EKF), and an Echo State Network (ESN).
* **State of Health (SOH)**: Tracked traditional-style via resistance growth using online Recursive Least Squares (RLS) parameter identification, compared side-by-side with a trained SOH ESN.
* **State of Energy (SOE)**: Computed dynamically by integrating the OCV-SOC curve to calculate remaining Wh energy capacity.
* **State of Power (SOP)**: Estimates instantaneous charge/discharge current/power envelopes based on safe terminal voltage limits and internal cell resistance.
* **Remaining Useful Life (RUL)**: Projects remaining cycle life based on electro-thermal stress and chemistry lookup profiles.

### Cyber-Physical Diagnostics

The visualiser features real-time diagnostics that identify three distinct categories of faults:
* **Sensor Dropout**: Triggered when the measured terminal voltage drops below $1.0\text{ V}$ (`DIAG_DROPOUT_VOLTAGE_THRESHOLD`), indicating a sensor failure or connection loss.
* **Thermal Runaway Warning**: Triggered if the battery temperature exceeds $60^\circ\text{C}$ (`DIAG_THERMAL_TEMP_THRESHOLD`) or if the temperature rise rate exceeds $2.0^\circ\text{C/s}$ (`DIAG_THERMAL_RATE_THRESHOLD`) at elevated temperatures.
* **Internal Short-Circuit**: Triggered when there is a significant discrepancy between the Coulomb Counting SOC and EKF SOC ($>0.08$ difference, `DIAG_SHORT_SOC_DIFF_THRESHOLD`) under low-current idle conditions (`DIAG_SHORT_CURRENT_THRESHOLD`), signalling a micro-short.

---

## Code Structure

```text
Battery_State_Estimator_BE_Project_2026_2027/
|-- .gitignore
|-- README.md
|-- requirements.txt
|-- docs/
|   |-- ARTIFACTS.md
|   |-- DEMO_CHECKLIST.md
|   |-- DEPLOY_RENDER.md
|   |-- OPERATIONS.md
|   |-- literature_survey.md
|   `-- system_specification.md
|-- hardware/
|   |-- main.c
|   |-- main.h
|   |-- train.py
|   |-- train_classifier.py
|   |-- train_estimator.py
|   |-- esn_classifier_weights.h
|   |-- esn_estimator_weights.h
|   `-- original_ev_battery_dataset_multiclass.csv
|-- software/
|   |-- tests/
|   |   |-- test_estimators.py
|   |   |-- test_api_auth.py
|   |   `-- test_production_train.py
|   |-- simulator/
|   |   |-- app.py
|   |   |-- battery_simulator.py
|   |   |-- battery_chemistry.py
|   |   `-- config.py
|   `-- visualiser/
|       |-- app.py
|       |-- config.py
|       |-- battery_chemistry.py
|       |-- battery_simulator.py
|       |-- traditional_estimator.py
|       |-- estimator_pipeline.py
|       |-- model_rc.pkl
|       |-- training/
|       `-- templates/
|-- images/
|   `-- assets/
|-- reference/
|   `-- paper.md
|-- .github/
    `-- workflows/ci.yml
```

---

## How to Run the Project

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Battery_State_Estimator_BE_Project_2026_2027
```

### Step 2: Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### Step 3: Run the Code

Start the physics simulator:

```bash
python software/simulator/app.py
```

Start the visualiser dashboard in a second terminal:

```bash
python software/visualiser/app.py
```

Run the hardware C simulator:

```bash
hardware/run_c_simulator.bat
```

On Linux or macOS:

```bash
chmod +x hardware/run_c_simulator.sh
hardware/run_c_simulator.sh
```

### Step 4: Observe the Output

- Visualiser dashboard: `http://localhost:5000`
- Simulator service: `http://localhost:8000`
- Expected dashboard output: live voltage, current, temperature, SOC, SOH, SOE, SOP, RUL, EKF/ESN comparison, and fault diagnostics.
- Expected C simulator output: Normal, Warning, and Critical safety classification logs with final accuracy.

---

## Testing and Results

Run the validation suite:

```bash
python -m unittest discover -s software/tests
```

| Test No. | Test Description | Expected Result | Actual Result | Status |
| -------- | ---------------- | --------------- | ------------- | ------ |
| 1 | Chemistry profile loading and OCV behavior | Valid profiles and monotonic OCV | Verified via test_estimators.py | Pass |
| 2 | 2-RC simulator dynamics | Charge/discharge, aging, and fault behavior | Verified via test_estimators.py | Pass |
| 3 | EKF and SOH observers | Bounded SOC/SOH and stable covariance | Verified via test_estimators.py | Pass |
| 4 | ESN feature and prediction path | Valid features and estimator outputs | Verified via test_estimators.py | Pass |
| 5 | Edge classifier | Normal/Warning/Critical classification | 98.40 percent reported accuracy | Pass |
| 6 | API Security & Fails-Open Routing | Verify 401 on missing key and 200 on valid credentials or local fallback | Verified via test_api_auth.py | Pass |

Current automated result: `50 tests OK`.

---

## Applications

1. Electric vehicle battery state estimation and diagnostics.
2. Battery energy storage system monitoring.
3. Embedded thermal safety classification for low-power BMS nodes.
4. Academic research on hybrid physics-based and data-driven estimators.
5. Operator training and fault-injection demonstrations.

---

## Advantages

1. Combines physics-based and data-driven estimation instead of relying on one method.
2. Supports real-time dashboard visualization and fault injection.
3. Uses CSR sparse reservoir computation for a 6.7x embedded speedup.
4. Provides optional Q12/Q15 fixed-point inference for low-power microcontrollers.
5. Can run locally or as standalone Render services.

---

## Limitations

1. The simulator models an equivalent cell/pack abstraction, not a fully validated production pack.
2. ESN performance depends on training data coverage and drive-cycle similarity.
3. Render free-tier services may sleep and are not ideal for uninterrupted telemetry generation.
4. Hardware-in-the-loop validation is still required before real safety-critical use.

---

## Future Scope

1. Multi-cell pack modeling and balancing logic.
2. Hardware-in-the-loop testing with real sensors and STM32 deployment.
3. Online adaptive ESN readout tuning using recursive least squares.
4. Thermal actuator control integration for active cooling.
5. More drive cycles, chemistries, and experimental datasets.

---

## Research Paper / Publication

| Item | Details |
| ---- | ------- |
| Paper Title | Edge-Based Sparse Reservoir Computing and State Observers for Real-Time Battery Diagnostics in Cyber-Physical Systems |
| Conference / Journal Name | IEEE-style journal/conference target under review by team |
| Paper Status | Drafting |
| Submission Date | Pending |
| Paper Link | [reference/paper.md](reference/paper.md) |

---

## References

```text
[1] G. L. Plett, "Extended Kalman filtering for battery management systems of LiPB-based HEV battery packs," Journal of Power Sources, vol. 134, no. 2, pp. 252-261, 2004.
[2] H. Jaeger and H. Haas, "Harnessing nonlinearity: Predicting chaotic systems and saving energy in wireless communication," Science, vol. 304, no. 5667, pp. 78-80, 2004.
[3] L. Rigutini et al., "State-of-charge estimation of lithium-ion batteries using reservoir computing," IEEE Transactions on Industrial Electronics, vol. 68, no. 8, pp. 7112-7121, 2020.
[4] R. Barrett et al., "Templates for the Solution of Linear Systems: Building Blocks for Iterative Methods," SIAM, 1994.
```

---

## Repository Update Guidelines

Each student team member should keep the repository current and reviewable.

Minimum expected updates:

* Update README and documentation when behavior changes.
* Push code changes with meaningful commit messages.
* Keep `.env` files, credentials, caches, and compiled binaries out of Git.
* Add tests when changing simulator, estimator, or feature logic.
* Document model, dataset, and generated-header changes in `docs/ARTIFACTS.md`.
* Keep deployment settings documented in `docs/DEPLOY_RENDER.md`.
