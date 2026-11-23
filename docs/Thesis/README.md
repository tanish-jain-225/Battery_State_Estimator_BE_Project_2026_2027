# B.E. Capstone Final Thesis / Dissertation

[← Back to Main Repository](../../README.md) · [← Review 2](../Review_2/Review_2_Progress.md) · [← FPGA IP Block](../../hardware/IP_Block/README.md) · [Capstone Thesis (Current)] · [Publications →](../Publications/README.md) · [Poster →](../Poster/README.md) · [View Thesis PDF](Final_Thesis.pdf)

---

## 📌 Executive Overview

This directory hosts the official **Final Year Bachelor of Engineering (B.E.) Capstone Project Dissertation Report**:

* **Project Title:** *Battery State Estimator: An Echo State Network-Based Approach to Battery State Estimation*
* **Degree:** Bachelor of Engineering (B.E.) in Automation and Robotics
* **Institute:** Vivekanand Education Society's Institute of Technology (VESIT), Hashu Advani Memorial Complex, Chembur, Mumbai – 400074
* **Affiliation:** University of Mumbai
* **Academic Year:** 2026–2027
* **Project Team & Authors:**
  * **Satvik Verma** — Roll No. 32
  * **Tanish Sanghvi** — Roll No. 61
  * **Sanjna Patankar** — Roll No. 19
  * **Akshay Nambiar** — Roll No. 17
* **Supervisor / Project Guide:** Dr. Kadambari Sharma
* **Head of Department:** Dr. Sangeeta Prasannaram
* **Principal:** Dr. (Mrs.) J. M. Nair
* **Deliverable Status:** **Completed & Fully Integrated on Disk (Deliverable 4 of 4 Finalized — 100% Turnkey Capstone Reached)**

---

## 📄 Deliverable Asset Metadata

| Asset Field | Value / Ground Truth |
| :--- | :--- |
| **File Path** | [`docs/Thesis/Final_Thesis.pdf`](Final_Thesis.pdf) |
| **Document Format** | Standard University of Mumbai B.E. Dissertation (A4 Portrait, Vector PDF) |
| **File Size** | **5,314,078 bytes (5.07 MB)** |
| **Page Count** | **41 Pages** (Full academic monograph with Certificate, Declarations, 8 Chapters, 3 Appendices & Literature Cited) |
| **Encryption Status** | **Encrypted** (Official institutional submission format with password security permissions) |
| **Status** | **Completed & Integrated (Turnkey v2.4.2 Capstone)** |

---

## 📖 Abstract & Keywords

### Abstract
> Lithium-ion batteries power electric vehicles and stationary storage, but safe operation depends on internal quantities that cannot be measured directly. State of charge (SOC) is the remaining charge relative to usable capacity, and state of health (SOH) is degradation relative to a reference condition. Both are hard to estimate because open-circuit voltage is nonlinear and the cell responds to temperature, load transients, sensor noise, parameter variation and ageing. This project builds and evaluates a software-to-hardware estimation framework around an Echo State Network (ESN), with conventional observers as baselines and embedded implementations used to study deployment.
> 
> The software side has a two-resistor–two-capacitor (2-RC) equivalent-circuit model with electro-thermal behaviour and capacity degradation, which generates voltage, current, temperature and reference-state telemetry under drive-cycle and fault conditions. Coulomb Counting (CC), an Extended Kalman Filter (EKF) and an Unscented Kalman Filter (UKF) are the baselines. The ESN keeps its reservoir weights fixed and trains only a readout, and Recursive Least Squares (RLS) adapts the readout as the battery changes. A Flask layer visualises telemetry and estimator behaviour. The hardware side has a C99 inference path (floating point, fixed point and compressed sparse row storage) and Verilog RTL for a 100-neuron fixed-point ESN on an Artix-7 FPGA, compared stage by stage with a Python golden model. The Review 2 record reports 62 passing automated tests and 200 of 200 matching datapath evaluations, alongside simulator benchmarks. The datapath is also packaged as an AXI4 IP block that passed functional tests on an Arty A7-100T board.
> 
> On NASA PCoE cells B0005, B0006, B0007 and B0018, eight discharge cycles per cell were evaluated with nested leave-one-cell-out validation, so the held-out cell was never used for normalisation, model selection or fitting. Against an EKF refitted in every fold, the quantized ESN reached a pooled SOC $R^2$ of 0.922 versus 0.898 (RMSE 0.088 versus 0.101, 21% lower MAE), though the advantage varied by cell. Per-cycle SOH reached a pooled $R^2$ of 0.782. Post-route results for the Q6.10 datapath on an XC7A100T (Vivado 2023.1) are 318 LUTs, 311 registers, 11.5 block-RAM tiles and two DSP slices, with timing closed at 80 MHz and 535.1 µs per reservoir update. The 0.120 W power figure is a vectorless estimate, the evaluation is offline, and operation with a live battery pack has not been shown.

### Keywords
`Battery management system`, `state of charge`, `state of health`, `lithium-ion battery`, `equivalent-circuit model`, `Echo State Network`, `reservoir computing`, `Recursive Least Squares`, `embedded inference`, `fixed-point arithmetic`, `FPGA verification`, `AXI4 IP block`.

---

## 📑 Complete Dissertation Chapter Breakdown

The final dissertation comprises 41 pages structured into formal preliminary endorsements, 8 core chapters, 3 technical appendices, and references:

### Preliminaries (Pages i–x)
* **Cover Page (Page 1)**: Departmental submission header, title, student roll numbers, supervisor credentials, and institutional seals.
* **Certificate of Bonafide Work (Page 2 / ii)**: Official project endorsement signed by Project Supervisor Dr. Kadambari Sharma, Head of Department Dr. Sangeeta Prasannaram, Principal Dr. (Mrs.) J. M. Nair, and External Examiner.
* **Declaration of Academic Honesty and Integrity (Page 3 / iii)**: Explicit anti-plagiarism declaration endorsed by all four student investigators.
* **Acknowledgements (Page 4 / iv)**: Institutional recognition of faculty mentorship, laboratory support, and department resources.
* **Abstract & Keywords (Page 5 / v)**: Comprehensive summary of goals, methods, and quantitative findings.
* **Table of Contents (Pages 6–7 / vi–vii)**: Detailed pagination of all 8 chapters, subsections, and appendices.
* **List of Figures & List of Tables (Page 8 / viii)**: Comprehensive visual figure and empirical data table index.
* **Abbreviations, Notation and Nomenclature (Pages 9–10 / ix–x)**: Definitions of mathematical symbols ($V_t, I_L, T_{\text{cell}}, \rho, W_{\text{in}}, W_{\text{res}}, W_{\text{out}}, \lambda$) and engineering acronyms (BMS, ECM, ESN, EKF, UKF, RLS, CSR, SpMV, AXI4).

---

### Chapter 1: Introduction (Pages 11–13 / 1–3)
* **1.1 Background and Motivation**: The criticality of SOC/SOH in EV range estimation, safety limits, and fast charging; shortcomings of Coulomb Counting (drift) and Kalman filters (parameter drift under aging).
* **1.2 Problem Statement**: Addressing the computational and modeling trade-offs in automotive battery state estimation through reservoir computing.
* **1.3 Aim and Objectives**: Developing a complete software-to-hardware pipeline: 2-RC physics twin, multi-observer comparator, C99 CSR firmware, and 100-neuron Q6.10 FPGA accelerator.
* **1.4 Scope and Limitations**: Clear delineation of offline NASA dataset validation, laboratory test setups, and vectorless power estimation boundaries.
* **1.5 Project Contributions**: Open-source 318-LUT ESN IP core, bit-exact verification, and reproducible battery state estimation benchmark.
* **1.6 Organisation of the Report**: Chapter-by-chapter roadmap.

---

### Chapter 2: Review of Literature (Pages 14–15 / 4–5)
* **2.1 Battery State Estimation as an Observability Problem**: Non-linear open-circuit voltage curves, hysteresis, and electrochemical state observability.
* **2.2 Coulomb Counting**: Error accumulation from sensor offsets, current integration noise, and lack of initial condition self-recovery.
* **2.3 Equivalent-Circuit Models and Kalman Filters**: 1-RC and 2-RC ECM formulations, Extended Kalman Filtering, Unscented Kalman Filtering, and recalibration challenges.
* **2.4 Data-Driven Battery Estimation**: Feedforward neural networks, LSTMs, and GRUs; their computational costs and recurrent backpropagation overhead.
* **2.5 Reservoir Computing and Echo State Networks**: Random fixed sparse recurrent reservoirs, Echo State Property ($\rho < 1$), and linear closed-form readout training.
* **2.6 Recursive Least Squares Adaptation**: Online parameter and readout tracking with Variable Forgetting Factors (VFF).
* **2.7 Embedded Optimisation and Digital Hardware**: Fixed-point quantization, Compressed Sparse Row (CSR) matrix multiplication, and FPGA accelerator architectures.
* **2.8 Research Gap and Project Positioning**: Absence of open-source, bit-exact, fixed-weight FPGA ESN IP cores for real-time BMS deployment.

---

### Chapter 3: Problem Analysis and Requirements (Pages 16–17 / 6–7)
* **3.1 Stakeholders and Operating Context**: Automotive OEMs, BMS firmware engineers, and edge AI researchers.
* **3.2 Functional Requirements**: Telemetry generation, multi-observer execution, live dashboard telemetry, C99 firmware inference, and FPGA AXI4 streaming.
* **3.3 Non-Functional Requirements**: Real-time update deadline ($\le 10\text{ ms}$), memory footprint constraints ($\le 8\text{ KB}$ RAM on microcontroller), and timing closure at 80 MHz.
* **3.4 System Boundaries and Assumptions**: Operating temperatures ($4^\circ\text{C}$ to $44^\circ\text{C}$), discharge rates ($1\text{ A}$ to $4\text{ A}$), and sensor noise parameters.
* **3.5 Evaluation Metrics**: Root Mean Squared Error (RMSE), Mean Absolute Error (MAE), Coefficient of Determination ($R^2$), clock cycles, and post-route resource utilization.
* **3.6 Requirement Traceability**: Traceability matrix linking user requirements to test verification evidence.

---

### Chapter 4: System Design and Methodology (Pages 18–22 / 8–12)
* **4.1 Overall Architecture**: High-level block diagram connecting the Cyber-Physical 2-RC twin, multi-observer comparator, embedded verifier, and FPGA accelerator.
* **4.2 Two-RC Equivalent-Circuit Model**: State equations for $V_1, V_2$, and terminal voltage $V_t = V_{\text{OCV}}(\text{SOC}) - I_L R_0 - V_1 - V_2$.
* **4.3 Thermal and Ageing Representation**: Lumped single-node thermal model with Arrhenius degradation coupling internal resistance $R_0$ and capacity $Q$.
* **4.4 Baseline Estimators**: Mathematical formulation of Coulomb Counting, 2-RC Extended Kalman Filter (EKF), and Unscented Kalman Filter (UKF).
* **4.5 Echo State Network Estimator**: Leaky-integrator reservoir formulation $\mathbf{x}[k] = (1-\alpha)\mathbf{x}[k-1] + \alpha \tanh(W_{\text{in}}\mathbf{u}[k] + W_{\text{res}}\mathbf{x}[k-1] + \mathbf{b})$, Ridge regression readout training, and online RLS adaptation.
* **4.6 Embedded and FPGA Design Principles**: Q6.10 integer arithmetic, piecewise linear / LUT $\tanh$ activation, and sparse CSR storage.
* **4.7 AXI-Packaged ESN IP Block**: Register-mapped AXI4-Lite control, AXI4-Stream data channels, memory addressing, and operation modes.
* **4.8 Dashboard and Data Flow**: Decoupled Flask microservices, MongoDB telemetry store, and real-time Chart.js visualization.

---

### Chapter 5: Implementation and Integration (Pages 23–26 / 13–16)
* **5.1 Repository Organization**: Clean modular directory structure (`software/`, `hardware/`, `docs/`, `tests/`).
* **5.2 Battery Simulator and Chemistry Data**: 5 real-world chemistry profiles (LFP, NMC, LCO, NCA, Lead-Acid) and active fault injection engine.
* **5.3 Estimator Pipeline Integration**: Decoupled pub/sub telemetry exchange with sub-millisecond indexed delta streaming.
* **5.4 ESN Training and Adaptation**: Python training script exporting model weights to CSR pickled objects, C headers, and FPGA COE files.
* **5.5 Web Application and Visualisation**: Fast-path render skipping and Page Visibility API throttling for zero idle CPU usage.
* **5.6 C99 Embedded Inference**: MISRA-C compliant firmware with static buffer allocation and CSR SpMV vector acceleration.
* **5.7 FPGA RTL Datapath**: 100-neuron pipelined Verilog RTL with BRAM table integration and 5-stage pipeline registers.
* **5.8 Synthesis, Resources and Timing**: Vivado 2023.1 synthesis and implementation achieving $+0.023\text{ ns}$ slack at 80 MHz.
* **5.9 IP Packaging, Driver and Integration**: IEEE 1685 IP-XACT `component.xml`, header-only C driver `driver/esn_ip.h`, and RV32I soft-core co-simulation.
* **5.10 Continuous Integration and Reproducibility**: Automated regression test suite and cross-platform master validation runners (`run_all_validation.bat` / `.sh`).
* **5.11 Security, Fault Handling and Operational Limits**: Safe state fallbacks, SHA-256 API authentication, and static memory bounds.

---

### Chapter 6: Testing and Verification (Pages 27–29 / 17–19)
* **6.1 Verification Strategy**: Multi-tiered verification covering unit tests, integration tests, embedded C99 benchmarks, and hardware-in-the-loop co-simulation.
* **6.2 Battery Model Tests**: Physical conservation of energy, OCV monotonicity, and thermal equilibrium tests.
* **6.3 Estimator Tests**: Observability recovery under initial SOC error and sensor noise robustness.
* **6.4 API and Dashboard Tests**: REST endpoint status codes, Keep-Alive connection pooling, and BSON ObjectId serialization.
* **6.5 C99 and Fixed-Point Tests**: Numerical parity between floating-point and Q15/Q12 integer firmware implementations.
* **6.6 FPGA Golden-Model Verification**: 5-stage bit-exact verification against the Python golden model (200/200 matching neuron outputs; 6,400 XSim updates).
* **6.7 Real-Cell Evaluation Protocol (NASA PCoE)**: Nested leave-one-cell-out validation across 29 held-out battery cells.
* **6.8 Verification of the AXI IP Block**: Functional test execution on the Digilent Arty A7-100T FPGA board across register, stream, and soft-core modes.
* **6.9 Automated Regression Suite**: Complete pytest suite (125 tests passing, 88.60% coverage on `software/shared`).
* **6.10 Reproducibility Protocol**: One-click reproduction commands and artifact validation checksums.

---

### Chapter 7: Results and Discussions (Pages 30–35 / 20–25)
* **7.1 Evidence Available in the Repository**: Verification logs, synthesis reports, and golden result CSVs.
* **7.2 Estimator Benchmark Reported by the Project**: SOC RMSE comparison (ESN: 0.088 vs EKF: 0.101, 21% MAE reduction).
* **7.3 Online Adaptation and Embedded-Oriented Results**: Real-time RLS weight tracking under capacity fade; C99 firmware execution in 6.7× fewer cycles.
* **7.4 FPGA Verification Results**: 100% bit-exact datapath parity across all 5 intermediate pipeline stages.
* **7.5 Real-Cell SOC Estimation (NASA PCoE)**: Pooled SOC $R^2$ of 0.922 across held-out cells; per-cell SD of 0.020 vs 0.035–0.056 for EKF.
* **7.6 Ablation and Seed Variability**: Reservoir spectral radius ($\rho$), input scaling, and reservoir size sensitivity analyses.
* **7.7 Real-Cell SOH Estimation and Overfitting**: SOH pooled $R^2$ of 0.782 using linear readout from end-of-discharge reservoir states.
* **7.8 Synthesis, Power and Timing Results**: 
  - Core Utilization: **318 LUTs** ($0.50\%$), **311 Registers**, **11.5 BRAM tiles**, **2 DSP slices**.
  - Packaged IP Platform: 1,868 LUTs, 4 DSP, 14.5 BRAM.
  - Timing: **80 MHz** with **$+0.023\text{ ns}$ slack**; **535.1 µs** per reservoir update.
  - Power: **0.120 W** total estimated power (0.021 W dynamic).
* **7.9 AXI IP Block Results**: Successful register-mode, stream-mode, and soft-core execution on Arty A7-100T.
* **7.10 Automated Test Results**: 125/125 passing tests with zero test failures.
* **7.11 Visualization and Interpretability**: Telemetry plots, multi-observer tracking waveforms, and residual error histograms.
* **7.12 Requirement Verification Summary**: Matrix confirming all functional and non-functional requirements met.
* **7.13 Threats to Validity**: Offline dataset limitations, room-temperature cell constraints, and sensor drift boundaries.
* **7.14 Discussion**: Trade-offs between computational simplicity and non-linear adaptability.

---

### Chapter 8: Conclusions and Future Work (Pages 36–37 / 26–27)
* **8.1 Conclusion**: Synthesis of software-to-hardware achievements, demonstrator maturity, and validation on Artix-7 FPGA.
* **8.2 Achievement Against Objectives**: Comprehensive accounting of all 7 project objectives completed.
* **8.3 Limitations**: Discussion of offline validation scope and need for live pack testing.
* **8.4 Future Work**: 11-point roadmap covering multi-temperature drive-cycle testing, ASIC tape-out feasibility, and live BMS integration.
* **8.5 Final Statement**: Clear positioning of the repository as an open-source, bit-exact research demonstrator for hardware-accelerated reservoir computing.

---

### Appendices & References (Pages 38–41 / 28–31)
* **Appendix I: Reproducibility and Execution Notes (Page 38)**: Exact execution commands for `pytest`, `compare_results.py`, and master validation scripts.
* **Appendix II: Evidence Inventory and Open Validation Items (Pages 38–39)**: Structured evidence table mapping project artifacts to evaluation actions.
* **Appendix III: Register Map and Driver Interface of the ESN IP (Page 40)**: Complete AXI4-Lite memory map (13 memory-mapped registers: `0x00 ID` through `0x30 MEM_DATA`) and C driver API (`esn_present()`, `esn_load()`, `esn_clear()`, `esn_step()`).
* **Literature Cited (Page 41)**: 17 peer-reviewed and foundational academic references ([1] Hannan et al. 2021 to [17] Saha & Goebel 2007).

---

## 🏛️ Academic Integrity & Verification Sign-Off

The dissertation report has been authored and compiled in strict accordance with the University of Mumbai and VESIT academic dissertation format specifications, incorporating all institutional review comments and defense feedback.

```
================================================================================
VESIT B.E. CAPSTONE DISSERTATION VERIFICATION:
• File: docs/Thesis/Final_Thesis.pdf (5,314,078 bytes / 5.07 MB encrypted)
• Status: 100% COMPLETE & VERIFIED (Deliverable 4 of 4)
• Turnkey Release: v2.4.2 Turnkey Capstone Reached
================================================================================
```

---

[← Return to FPGA IP Block](../../hardware/IP_Block/README.md) · [Proceed to Academic Publications →](../Publications/README.md) · [Proceed to Capstone Poster →](../Poster/README.md)
