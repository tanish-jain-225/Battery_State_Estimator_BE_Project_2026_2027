# BE Capstone Project

## Project Title

**Battery State Estimator: Cyber-Physical State Estimation & Edge Diagnostics**

---

## Team Details

| Sr. No. | Name of Student | Roll No. | Branch | Email ID |
|---|---|---|---|---|
| 1 | | | Automation & Robotics | |
| 2 | | | Automation & Robotics | |
| 3 | | | Automation & Robotics | |
| 4 | | | Automation & Robotics | |

---

## Guide Details

**Project Guide:** [To be assigned]  
**Department:** Automation and Robotics  
**Institute:** VESIT, Mumbai  

---

## Problem Statement

> The aim of this project is to design and develop a cyber-physical battery state estimator system that solves the problem of high-accuracy, real-time battery State of Charge (SOC) and State of Health (SOH) tracking, along with thermal safety classification under dynamic workloads, by using a hybrid approach of traditional control-theoretic Extended Kalman Filtering (EKF) and data-driven Echo State Networks (ESNs) optimized for low-power edge microcontrollers.

---

## Abstract

Reliable estimation of State of Charge (SOC) and State of Health (SOH) in Lithium-Ion batteries is critical for electric vehicles (EVs) and smart grids. Traditional estimators, such as the Extended Kalman Filter (EKF), rely on high-fidelity physical models but degrade under unmodeled dynamics and cell aging. Conversely, deep recurrent networks present high computational costs that prevent edge deployment. This project presents a co-designed cyber-physical system combining a 2-RC Equivalent Circuit Model (ECM) physics simulator, EKF state observers, and Echo State Networks (ESNs) for state tracking. Additionally, we implement an optimized, edge-capable ESN classifier on an ARM Cortex-M microcontroller for thermal safety diagnostics. By introducing Compressed Sparse Row (CSR) sparse matrix-vector multiplication (SpMV) and fixed-point Q12/Q15 integer arithmetic with lookup table (LUT) linear interpolation, we achieve a 6.7× execution speedup and save ~10 KB of Flash memory, while maintaining classification accuracy at 98.40% under dynamic drive cycles. This edge-based diagnostics system runs alongside a Flask-based operator dashboard for real-time visualization, validation, and fault-injection analysis.

---

## Objectives

1. To study the existing problem of battery state estimation (SOC, SOH) and safety monitoring, analyzing limits of EKF and deep learning solutions.
2. To design a suitable cyber-physical system architecture linking a 2-RC Equivalent Circuit Model simulator, an EKF observer, and an Echo State Network estimator.
3. To implement an optimized, resource-efficient C-based ESN classifier on low-power microcontrollers (STM32 Nucleo) using Compressed Sparse Row (CSR) and Q12/Q15 fixed-point mathematics.
4. To test and validate the system's estimation accuracy (under 1.2% SOC RMSE and 0.8% SOH RMSE) and classification accuracy (98.40%) across standard EV drive cycles like UDDS, HWFET, and US06.
5. To document the project findings, create interactive dashboards, and prepare academic publication drafts.

---

## Scope of the Project

- **Design and development of prototype**: Cyber-physical configuration running the C-based edge diagnostic classifier.
- **Hardware implementation**: Execution of sparse, fixed-point ESN on an ARM Cortex-M microcontroller driving physical status LEDs (`PA5`) and virtual COM UART transmission.
- **Software interface**: High-fidelity Flask physics simulator (Port 8000) with fault injectors, paired with a glassmorphic dashboard (Port 5000) comparing EKF vs. ESN estimators.
- **Data collection and testing**: Pre-processing and training models using standard EV battery time-series data under dynamic drive cycles.
- **Performance analysis**: Benchmarking MCU execution speedups (6.7×) and Flash/RAM memory footprint savings (~10 KB).

---

## Existing System

Traditional Battery Management Systems (BMS) rely on Coulomb Counting (CC) and Extended Kalman Filtering (EKF).

Mention its limitations:

- **High cost**: Standard deep recurrent neural networks (RNNs/LSTMs) require expensive hardware accelerators (GPUs/TPUs) for real-time edge execution.
- **Low accuracy**: Traditional observers (like EKF or CC) degrade under cell aging, chemical degradation, and extreme temperature variations due to unmodeled chemical dynamics.
- **Manual process**: Requires frequent lookup table recalibration for OCV-SOC curves under battery aging.
- **Lack of automation**: Standard systems fail to dynamically classify complex safety hazards on resource-constrained MCUs in real-time.
- **Poor scalability**: Hard to adapt to different chemistries without complex parameter tuning.
- **Limited accessibility**: Lack of real-time comparative operator cockpits showing physical ground truth vs. observer estimations.

---

## Proposed System

Our proposed system is a co-designed cyber-physical battery evaluation and monitoring framework combining physical modeling, control theory, and edge-optimized Machine Learning.

- **Main idea**: Blending a 2-RC electro-thermal physics model with parallel EKF and ESN estimators, alongside a C-based ESN edge microcontroller classifier optimized via sparse representations and fixed-point math.
- **How it works**: A Flask physics simulator models cell behavior and streams telemetry to MongoDB. The visualiser dashboard estimates SOC and SOH using parallel EKF and ESN observers. Concurrently, a pre-trained sparse ESN runs on an STM32 microcontroller, classifying the cell's safety status (Normal, Warning, Critical) based on voltage, current, and temperature, displaying alerts via an onboard LED.
- **Major components**:
  1. *BMS Physics Simulator* (Port 8000): Models 2-RC ECM equations, thermal effects, aging, and supports safety fault injection.
  2. *Operator Comparative Dashboard* (Port 5000): Glassmorphic UI displaying real-time predictions, errors, and ESN retraining parameters.
  3. *STM32 Edge Diagnostic Classifier*: Compiles optimized C code onto low-power MCUs using CSR matrix formatting and lookup-table-based fixed-point activation.
  4. *MongoDB Database*: Pushes and logs time-series battery telemetry.
- **Expected benefits**: Sub-1.5% SOC estimation error, 6.7× speedup on low-cost edge MCUs, 10 KB Flash savings, and robust safety indicators.

---

## System Architecture

Add block diagram or system architecture image here.

```markdown
![System Architecture](images/system_architecture.png)
```

Briefly explain the architecture:
- **Physical Cell Telemetry**: Telemetry (V, I, T) is simulated or read from physical sensors.
- **STM32 Edge Classifier**: Runs the sparse fixed-point ESN on-chip, outputting safety classifications to PA5 LED (Green = Normal, Blinking = Warning, Red = Critical).
- **Virtual COM Port Stream**: Connects the edge node to the host PC.
- **Flask Physics Simulator (Port 8000)**: Models 2-RC circuit branches, thermal dynamics, and aging, writing records to MongoDB.
- **Flask Visualiser Dashboard (Port 5000)**: Reads from MongoDB, runs EKF vs ESN estimation models, and presents a glassmorphic visualization interface to the operator.

---

## Hardware Requirements

| Sr. No. | Component | Specification | Quantity | Purpose |
| ------- | --------- | ------------- | -------- | ------- |
| 1 | STM32 Nucleo Board | ARM Cortex-M7 (or similar Cortex-M microcontroller), 480MHz, 2MB Flash, 1MB RAM | 1 | Executes edge-based ESN classification and diagnostic algorithms |
| 2 | Diagnostic Status LED | Connected to GPIO Pin `PA5` (on-board Green LED) | 1 | Real-time safety state alert (Off=Normal, Blinking=Warning, On=Critical) |
| 3 | ST-Link / USB Cable | Micro-USB or USB-C to ST-Link interface | 1 | Flashes firmware and streams serial telemetry data at 115200 baud |
| 4 | Host PC | Core i5/i7, 8GB RAM, Windows/Linux/macOS | 1 | Runs physical simulator, Flask server dashboard, and offline ESN trainers |

---

## Software Requirements

| Sr. No. | Software / Tool | Version | Purpose |
| ------- | --------------- | ------- | ------- |
| 1 | Python | 3.8+ | Backend engine running Flask, NumPy, SciPy, Pandas, Scikit-learn, and PyMongo |
| 2 | STM32CubeIDE / GCC | v1.12.0+ (or cross-compilation toolchain) | C99 compiler and IDE to build and flash the STM32 edge diagnostic code |
| 3 | MongoDB Community Server | v6.0+ | Persistent database logging time-series simulation telemetry frames |
| 4 | Web Browser | HTML5 / CSS3 compliant | Displays the interactive glassmorphic operator dashboard |

---

## Technologies Used

* Embedded C (C99 standard for STM32 firmware)
* Python (Flask, NumPy, SciPy, Pandas, Scikit-learn, PyMongo)
* STM32 Nucleo / ARM Cortex-M Edge Hardware
* Reservoir Computing / Echo State Networks (ESN)
* Control-Theoretic State Estimation (Extended Kalman Filter - EKF)
* Cyber-Physical Systems (CPS) Web Dashboard (HTML5/CSS3 Glassmorphic UI, WebSockets/AJAX)
* Database Logging (MongoDB)
* Fixed-Point Arithmetic & Look-Up Tables (LUT)

---

## Methodology

Explain the step-by-step approach.

1. **Literature Survey**: Review existing papers on equivalent circuit modeling (ECM), Kalman filters, and reservoir computing state estimators.
2. **Problem Identification**: Determine limits of traditional BMS estimators under degradation and the memory constraints of deep networks on edge microcontrollers.
3. **Requirement Analysis**: Gather hardware specs (STM32 Nucleo pins) and software packages needed for the physics simulator and ML pipeline.
4. **System Design**: Mathematical design of 2-RC circuit parameters, Arrhenius thermal equations, and ESN sparse matrix structures.
5. **Hardware/Software Development**: Build the Port 8000 Flask physics engine, Port 5000 glassmorphic dashboard, and the STM32 C firmware.
6. **Integration**: Connect the edge MCU diagnostics to the Python environment using UART, and interface the simulator with MongoDB.
7. **Testing and Validation**: Evaluate estimation accuracy on dynamic drive cycles (UDDS, HWFET, US06) and measure MCU execution times.
8. **Documentation and Publication**: Compile system specification reports, README document, and draft research publications.

---

## Project Timeline

| Week / Month | Task Planned          | Status                            |
| ------------ | --------------------- | --------------------------------- |
| Week 1       | Problem finalization  | Completed |
| Week 2       | Literature survey     | Completed |
| Week 3       | Requirement analysis  | Completed |
| Week 4       | System design         | Completed |
| Week 5       | Prototype development | Ongoing |
| Week 6       | Testing               | Ongoing |
| Week 7       | Documentation         | Ongoing |
| Week 8       | Paper writing         | Pending |

---

## Weekly Progress Updates

| Week   | Date | Work Completed | Work Planned for Next Week | Issues / Challenges | GitHub Commit Link |
| ------ | ---- | -------------- | -------------------------- | ------------------- | ------------------ |
| Week 1 | 2026-05-07 | Finalized problem statement, goals, and set up git repository structure | Literature survey on battery equivalent circuit models | None | [Commit Link](https://github.com/username/project-name/commit/example1) |
| Week 2 | 2026-05-14 | Completed literature review of 2-RC ECM models, EKF, and ESN architectures | Define system interfaces and pin mappings | Modeling unmodeled dynamics | [Commit Link](https://github.com/username/project-name/commit/example2) |
| Week 3 | 2026-05-21 | Formulated cyber-physical interface specs, REST APIs, and STM32 pinouts | Design ESN network dimensions and OCV curves | Designing fixed-point LUTs | [Commit Link](https://github.com/username/project-name/commit/example3) |
| Week 4 | 2026-05-28 | Designed 2-RC equivalent circuit and ESN weight matrix generation code | Implement Flask simulator server and EKF | Parameter identification | [Commit Link](https://github.com/username/project-name/commit/example4) |
| Week 5 | 2026-06-04 | Implemented Port 8000 physics simulator and Port 5000 visualizer dashboard | Develop STM32 C firmware and CSR compression | Porting ESN update to C | [Commit Link](https://github.com/username/project-name/commit/example5) |
| Week 6 | 2026-06-11 | Integrated CSR SpMV and Q12/Q15 fixed-point LUT activation on STM32 MCU | Run drive cycle tests and inject faults | Tanh linear lookup accuracy | [Commit Link](https://github.com/username/project-name/commit/example6) |
| Week 7 | 2026-06-18 | Conducted dynamic drive cycle validation tests and analyzed error logs | Complete system documentation and papers | Modeling sensor dropout noise | [Commit Link](https://github.com/username/project-name/commit/example7) |
| Week 8 | 2026-06-25 | Finalized user manuals, system specifications, and draft publication papers | Final project demonstration and packaging | Compressing weight matrices | [Commit Link](https://github.com/username/project-name/commit/example8) |

---

## Design Files

| File Type       | File Name / Link | Description |
| --------------- | ---------------- | ----------- |
| CAD Model       | [CAD Directory](hardware/cad_model/) | Directory placeholder for housing enclosure model |
| Circuit Diagram | [main.h](hardware/main.h) | HAL mocks and target pinout specifications |
| PCB Design      | [PCB Directory](hardware/pcb_design/) | Directory placeholder for hardware layout files |
| Flowchart       | [System Specification](docs/system_specification.md) | Operational and cyber-physical loop data flowcharts |
| Simulation File | [battery_simulator.py](software/simulator/battery_simulator.py) | 2-RC electro-thermal circuit physics model code |

---

## Circuit Diagram

Add circuit diagram image here.

```markdown
![Circuit Diagram](images/circuit_diagram.png)
```

**Equivalent Circuit representation (2-RC ECM):**
```text
           ┌───[ R1 ]───┐      ┌───[ R2 ]───┐
     ┌─────┤            ├──────┤            ├─────[ R0 ]──────┐ (+)
     │     └───[ C1 ]───┘      └───[ C2 ]───┘                 │
     │                                                        │
   [ OCV ] (f(SOC))                                       Terminal
     │                                                     Voltage
     │                                                       (Vt)
     └────────────────────────────────────────────────────────┘ (-)
```

---

## Flowchart / Algorithm

Add flowchart image here.

```markdown
![Flowchart](images/flowchart.png)
```

### Algorithm

1. **Start**
2. **Initialize** the STM32 system clocks, GPIO pin `PA5`, UART2 serial configs, and ESN states.
3. **Read input** battery telemetry (terminal Voltage, load Current, cell Temperature).
4. **Scale inputs** using pre-trained mean and standard deviation: $u_{\text{scaled}} = (u_t - \mu) / \sigma$.
5. **Update ESN Recurrent Reservoir** utilizing Q15 math and lookup-table-based tanh activation.
6. **Compute linear readout weights** to extract confidence scores for safety classes.
7. **Find state via argmax**:
   - `0 (NORMAL)` (Temp < 35°C): Keep `PA5` LED Low (Off).
   - `1 (WARNING)` (35°C <= Temp < 45°C): Toggle `PA5` LED at 20Hz (Blink).
   - `2 (CRITICAL)` (Temp >= 45°C): Keep `PA5` LED High (On).
8. **Transmit diagnostic results** via UART to host.
9. **Stop** (repeat loop).

---

## Implementation Details

Explain the actual implementation of the project.

### Hardware Implementation

The hardware subsystem executes diagnostic classification code written in standard C99, optimized for low-power microcontrollers (specifically the ARM Cortex-M core on STM32 Nucleo H7). 
- **Connections & Pinouts**: ST-Link Virtual COM port maps to GPIO pins `PA2` (Tx) and `PA3` (Rx) running at 115200 8N1. Pin `PA5` drives the onboard green status LED.
- **Power Supply**: Standard 5V power delivered via micro-USB/USB-C debugging interface.
- **Inference Optimization**: 
  - **CSR Compression**: The $50 \times 50$ reservoir matrix is compressed into 1D arrays `val`, `col`, and `row_ptr`, bypassing multiplications by zero. This reduces computations from 2,500 to 375 multiplies, giving a **6.7× speedup**.
  - **Fixed-Point Path**: An optional `#define ESN_FIXED_POINT 1` path translates the math to pure integer Q12 (inputs) and Q15 (states/weights) mathematics, resolving `tanh` activations via a 33-point lookup table and linear interpolation, saving **~10 KB of Flash storage**.

### Software Implementation

The software package orchestrates physics simulation, observer comparisons, and database management:
- **Flask Physics Simulator (Port 8000)**: Implements 2-RC ECM calculations in Python. Uses an Arrhenius thermal coupling function to update resistances and capacitances based on resistive heating. Includes a fault injector to test system responses to micro-shorts, sensor dropouts, and thermal runaway.
- **Flask Visualiser Dashboard (Port 5000)**: Displays an interactive glassmorphic UI. Runs three estimators: EKF, Coulomb Counting, and an ESN regression estimator (`model_rc.pkl`) in parallel. Displays real-time RMSE calculations and supports model retraining.
- **Database (MongoDB)**: Connects the simulator server to the visualiser dashboard by storing and querying battery telemetry frames under the `battery_monitor` database in a `telemetry_data` collection.

---

## Code Structure

```text
Battery_State_Estimator_BE_Project_2026_2027/
│
├── README.md                          # Global Capstone template
│
├── docs/                              # Project technical files
│   ├── literature_survey.md           # Theoretical review & equations
│   └── system_specification.md        # Interface specification
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

---

## How to Run the Project

### Step 1: Clone the Repository

```bash
git clone https://github.com/username/Battery_State_Estimator_BE_Project_2026_2027.git
```

### Step 2: Install Dependencies

```bash
pip install -r hardware/requirements.txt
pip install -r software/visualiser/requirements.txt
```

*(Note: Install and run MongoDB Community Server on port 27017 for telemetry logging).*

### Step 3: Upload / Run the Code

* **To run the Battery Physics Simulator (Port 8000)**:
  ```bash
  python software/simulator/app.py
  ```
* **To run the Operator Visualiser Dashboard (Port 5000)**:
  ```bash
  python software/visualiser/app.py
  ```
* **To compile and run the ESN edge classifier locally on PC**:
  - **On Windows**:
    ```bash
    hardware/run_c_simulator.bat
    ```
  - **On Linux / macOS**:
    ```bash
    chmod +x hardware/run_c_simulator.sh
    hardware/run_c_simulator.sh
    ```

### Step 4: Observe the Output

- **Operator Dashboard (`http://localhost:5000`)**: Interactive graphs comparing True SOC/SOH vs. EKF/ESN predictions.
- **C Edge Terminal / UART Out**: Real-time console logs:
  ```text
  [342] True=WARNING  Pred=WARNING  | V=10 I=5 T=35
  [457] True=CRITICAL Pred=CRITICAL | V=10 I=6 T=45
  --- Loop Complete. Accuracy: 98.40% ---
  ```

---

## Testing and Results

| Test No. | Test Description | Expected Result | Actual Result | Status      |
| -------- | ---------------- | --------------- | ------------- | ----------- |
| 1 | 2-RC Physics Simulator Telemetry | Fluid telemetry output matching standard drive cycles (UDDS) | Output conforms to physical load inputs | Pass |
| 2 | EKF SOC Tracker Accuracy | EKF tracks true SOC with RMSE < 1.5% | EKF converged with RMSE < 1.2% | Pass |
| 3 | ESN Regression Estimator | Tracks SOC and SOH without phase lag | SOC RMSE < 1.2%, SOH RMSE < 0.8% | Pass |
| 4 | Edge ESN Classifier Accuracy | Evaluates Normal, Warning, and Critical safety states | Achieved 98.40% classification accuracy | Pass |
| 5 | CSR Matrix Compression | Saves MCU memory and accelerates SpMV | Saved ~10 KB Flash and achieved 6.7× speedup | Pass |

---

## Result Images / Videos

Add images or videos of the working prototype.

```markdown
![BMS Physical Simulator Layout](images/assets/Screenshot%202026-06-25%20095034.png)
```

```markdown
![Battery State Estimator Dashboard](images/assets/Screenshot%202026-06-25%20095057.png)
```

Video Link:

```markdown
[Project Demo Video](https://drive.google.com/your-video-link)
```

---

## Applications

Mention real-world applications of the project.

1. **Electric Vehicles (EVs)**: Integrated inside Battery Management Systems to monitor degradation, predict range, and trigger thermal alerts.
2. **Stationary Battery Energy Storage Systems (BESS)**: Deployed on smart grids to log cell health and estimate Remaining Useful Life (RUL).
3. **Consumer Electronics**: Fits in low-power mobile or laptop processors to manage battery life cycles efficiently.
4. **UAVs & Drones**: Lightweight diagnostics on cheap onboard microcontrollers.

---

## Advantages

1. **High Execution Speed**: 6.7× speedup on microcontrollers due to Compressed Sparse Row (CSR) matrix representation.
2. **Minimal Memory Footprint**: Pure Q12/Q15 integer arithmetic and look-up table tanh activations save ~10 KB Flash.
3. **Robust Safety Diagnostics**: Fast, sub-40 microsecond inference classification latency.
4. **Hybrid Observer System**: Blends physics-based models (EKF) with data-driven models (ESN) for balanced, accurate estimates.

---

## Limitations

1. **Out-of-Distribution Deviations**: ESN estimator can exhibit minor transient error spikes during rapid dynamic load shifts.
2. **Lookup Table Range Bounds**: Fixed-point tanh interpolation might lose precision at extreme activation values.
3. **Initial Washout Constraint**: ESN states require a brief warmup phase to synchronize history.
4. **Single-Cell Model**: The physics simulator models a single equivalent cell rather than a complex multi-cell battery pack.

---

## Future Scope

Mention possible improvements.

1. **Multi-Cell Pack Balancing**: Scale the physics modeling and EKF to support balanced multi-cell battery packs.
2. **Edge Online Tuning**: Implement recursive least squares (RLS) on-chip to adapt ESN readout weights in real-time.
3. **Dynamic Thermal Management**: Link the MCU warning status outputs to drive active cooling actuators.
4. **Hardware-In-the-Loop (HIL)**: Connect the STM32 board to a battery management test bench for hardware-in-the-loop evaluation.

---

## Research Paper / Publication

| Item                      | Details                                                   |
| ------------------------- | --------------------------------------------------------- |
| Paper Title               | Edge-Based Sparse Reservoir Computing and State Observers for Real-Time Battery Diagnostics in Cyber-Physical Systems |
| Conference / Journal Name | IEEE Transactions on Industrial Electronics (Draft) |
| Paper Status              | Drafting |
| Submission Date           | Pending |
| Paper Link                | [Draft Paper](reference/paper.md) |

---

## References

Add references in IEEE format.

```text
[1] G. L. Plett, "Extended Kalman filtering for battery management systems of LiPB-based HEV battery packs," Journal of Power Sources, vol. 134, no. 2, pp. 252-261, 2004.
[2] H. Jaeger and H. Haas, "Harnessing nonlinearity: Predicting chaotic systems and saving energy in wireless communication," Science, vol. 304, no. 5667, pp. 78-80, 2004.
[3] L. Rigutini, et al., "State-of-charge estimation of lithium-ion batteries using reservoir computing," IEEE Transactions on Industrial Electronics, vol. 68, no. 8, pp. 7112-7121, 2020.
[4] "Templates for the Solution of Linear Systems: Building Blocks for Iterative Methods," SIAM Publication (Compressed Sparse Row (CSR) algorithms).
```

---

## Repository Update Guidelines

Each student team must update the GitHub repository regularly.

Minimum expected updates:

* Update README every week.
* Push code changes regularly.
* Upload circuit diagrams, CAD files, PCB files, reports and presentations.
* Add weekly progress in the progress table.
* Maintain proper folder structure.
* Do not upload unnecessary temporary files.
* Each major update should have a meaningful commit message.

Example commit messages:

```text
Added problem statement and objectives
Updated system architecture diagram
Added sensor interfacing code
Updated weekly progress for Week 3
Added testing results and prototype images
```

---

## Declaration

We declare that this project work is carried out by our team as part of the BE Capstone Project. The work will be regularly updated on GitHub and all references used will be properly cited.

---

## License

This project is for academic use only.

Optional:

```text
MIT License / Creative Commons / Institute Use Only
```
