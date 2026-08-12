[← Back to README](../../README.md)

# PowerPoint Presentation Plan: First Progress Review

**Project Title**: ESN-Based Battery SOC/SOH Estimation with Embedded Hardware Validation  
**Subtitle**: Software Estimator + Embedded / FPGA Hardware Validation  

This document serves as an end-to-end slide-by-slide blueprint for your first capstone project review. It strictly adheres to the 5-slide presentation format, presents an evidence-based progress summary divided by phases (Completed, In Progress, Final Goal), clarifies that software is the final product while hardware acts as the testing/verification loop, and includes academic publishing and thesis targets.

---

## ⏱️ Presentation Timing Overview
* **Total Duration**: ~5 Minutes (4:30 to 5:00 minutes)
* **Slide Budget**:
  * **Slide 1 (Title & Team Details)**: 30 Seconds
  * **Slide 2 (Problem & Proposed Solution)**: 60 Seconds
  * **Slide 3 (Phase 1 — Completed)**: 90 Seconds
  * **Slide 4 (Phase 2 — In Progress)**: 75 Seconds
  * **Slide 5 (Phase 3 — Final Goal & Timeline)**: 45 Seconds

---

## 🎴 Slide-by-Slide PPT Content & Layout

### Slide 1: Progress Review — Title & Team Details
* **Slide Title**: Progress Review: ESN-Based Battery SOC/SOH Estimation with Embedded Hardware Validation
* **Slide Subtitle**: Software Estimator + Embedded / FPGA Hardware Validation
* **Slide Objective**: Introduce the project title, team members, guide, department, and institute.
* **Slide Bullet Points (On-Screen Text)**:
  * **Title**: **ESN-Based Battery SOC/SOH Estimation with Embedded Hardware Validation**
  * **Subtitle**: Software Estimator + Embedded / FPGA Hardware Validation
  * **Team**:
    1. Sanjna Patankar
    2. Akshay Nambiar
    3. Satvik Verma
    4. Tanish Sanghvi
  * **Guide**: Dr. Kadambari Sharma
  * **Department**: Automation and Robotics
  * **Institute**: Vivekanand Education Society's Institute of Technology (VESIT), Mumbai
* **Visual Layout & Aesthetics**:
  * Modern dark slate background with cyan and teal accent cards.
  * Right panel highlighting Guide, Department, and Institute metadata.
* **Speaker Delivery Notes**: "Good morning respected evaluators. We are team members Sanjna Patankar, Akshay Nambiar, Satvik Verma, and Tanish Sanghvi from the Department of Automation and Robotics at VESIT. Our project is titled 'ESN-Based Battery SOC/SOH Estimation with Embedded Hardware Validation', guided by Dr. Kadambari Sharma. Today we will present our first progress review."

---

### Slide 2: Problem & Proposed Solution
* **Slide Title**: Problem & Proposed Solution
* **Slide Subtitle**: Why existing SOC/SOH estimation falls short, and what we propose instead
* **Slide Objective**: Define limitations of Coulomb Counting and EKF, introduce the ESN alternative, and establish software vs hardware scope.
* **Slide Bullet Points (On-Screen Text)**:
  * **The Problem**:
    * **Coulomb Counting**: Open-loop integration accumulates drift and error over time.
    * **Extended Kalman Filter (EKF)**: Strongly model-dependent and computationally heavy for embedded use.
  * **Proposed Solution**:
    * **Echo State Network (ESN)**: A lightweight reservoir-computing estimator for battery SOC/SOH — trained once, cheap to run, and well suited to embedded and hardware deployment.
    * **Software Scope**: Final estimator / product.
    * **Hardware Scope**: Embedded implementation & verification platform.
  * **Data Flow**:
    `Battery Data` ➔ `Data Processing` ➔ `ESN` ➔ `SOC / SOH` ➔ `Embedded Deployment (ARTIX A7100T | RTL / HIL)`
* **Visual Layout & Aesthetics**:
  * Two-column comparison: Left box detailing problem points with warning icons, Right box detailing ESN advantages in teal.
  * Bottom flowchart showing data flow from battery telemetry through ESN to ARTIX A7100T RTL/HIL deployment.
* **Speaker Delivery Notes**: "Traditional observers like Coulomb Counting suffer from drift over time, while Extended Kalman Filters are model-dependent and heavy for embedded chips. We propose an Echo State Network, which uses fixed reservoir weights and trains only the linear output layer. Our software algorithm represents the final product, while embedded C99 firmware and FPGA hardware serve as our verification and testing loop."

---

### Slide 3: Phase 1 — Completed Work
* **Slide Title**: Phase 1 — Completed
* **Slide Subtitle**: Software estimator and embedded hardware, both verified
* **Slide Objective**: Present completed software development and hardware RTL verification results.
* **Slide Bullet Points (On-Screen Text)**:
  * **Battery / Software**:
    * ✓ 2-RC battery simulator
    * ✓ EKF + Coulomb Counting + SOH tracking
    * ✓ ESN training pipeline
    * ✓ Flask dashboard deployed
    * ✓ C99 ESN implementation
    * ✓ CSR optimization — 6.7× speedup
  * **Embedded / Hardware**:
    * ✓ Q6.10 fixed-point ESN datapath
    * ✓ Hardware tanh LUT (odd-symmetry, positive half only)
    * ✓ Verilog ESN RTL — 100-neuron reservoir
    * ✓ BRAM-based weight / input / state storage
    * ✓ Double-buffered recurrent state memory
    * ✓ $\text{Win}\cdot u + W\cdot x \text{ MAC} \rightarrow \text{bias} \rightarrow \text{clip} \rightarrow \tanh$ pipeline
    * ✓ Vivado / XSim two-pass verification (ARTIX A7100T target)
  * **Highlight Box**: **200 / 200 neuron updates matched bit-exactly against the Python golden model**
* **Visual Layout & Aesthetics**:
  * Two-card split for Battery/Software (teal) and Embedded/Hardware (dark navy).
  * Prominent highlighted result pill at the bottom confirming 200/200 bit-exact match against Python golden model.
* **Speaker Delivery Notes**: "In Phase 1, we completed our software foundation: a 2-RC electro-thermal battery simulator, EKF/CC baselines, ESN training pipelines, Flask dashboard, and C99 CSR implementation yielding 6.7x speedup. On hardware, we implemented a 100-neuron Q6.10 fixed-point ESN RTL in Verilog with double-buffered memory and tanh LUT. In Vivado/XSim targeting the ARTIX A7100T FPGA, 200 out of 200 neuron updates matched our Python golden model bit-exactly."

---

### Slide 4: Phase 2 — In Progress Work
* **Slide Title**: Phase 2 — In Progress
* **Slide Subtitle**: Current work on the ESN estimator and its hardware validation
* **Slide Objective**: Outline ongoing tasks in online software adaptation and multi-timestep hardware verification.
* **Slide Bullet Points (On-Screen Text)**:
  * **ESN / Software**:
    * Online ESN adaptation using RLS / gradient descent
    * LSTM / GRU benchmarking
    * Testing across different EV drive cycles (DST, US06, FUDS)
    * C99 deployment refinement
  * **Hardware / Embedded (5-Step Roadmap)**:
    1. **Multi-timestep sequence input**: Extend the verified single-step design (reused $u(0)$) to full sequences $u(0)\dots u(T)$.
    2. **FPGA sequence-level verification**: Python golden model vs. Vivado/XSim, bit-exact comparison, on ARTIX A7100T.
    3. **ARTIX A7100T deployment**: On-board resource utilization and inference latency profiling.
    4. **Hardware-in-the-loop interface**: UART link between the battery simulator and the FPGA board.
    5. **End-to-end estimation**: Drive-cycle data ➔ ESN ➔ SOC / SOH on hardware.
* **Visual Layout & Aesthetics**:
  * Split view with ESN software focus items on the left and a numbered 5-stage Hardware roadmap on the right.
* **Speaker Delivery Notes**: "Phase 2 is currently active. For software, we are implementing online readout adaptation using RLS for cell aging, benchmarking against LSTM/GRU models, and running dynamic EV drive cycle tests. On hardware, we are expanding our verified single-step FPGA design to multi-timestep sequence inputs $u(0)\dots u(T)$, performing sequence-level Vivado verification on the ARTIX A7100T, and building a UART Hardware-in-the-Loop interface."

---

### Slide 5: Phase 3 — Final Goal & Timeline
* **Slide Title**: Phase 3 — Final Goal & Timeline
* **Slide Subtitle**: Final Goal & Timeline
* **Slide Objective**: State the final project deliverable and map out semester milestones to completion.
* **Slide Bullet Points (On-Screen Text)**:
  * **Final Goal**: Deploy and validate a lightweight ESN-based SOC/SOH estimator on embedded hardware (ARTIX A7100T) using real / representative battery drive-cycle data.
  * **Final Architecture**:
    `Battery Dataset` ➔ `2-RC / Battery Model` ➔ `ESN Estimator` ➔ `SOC / SOH` ➔ `Embedded System (ARTIX A7100T | RTL / HIL Validation)`
  * **Timeline Milestones**:
    * **Aug 31**: Literature review / IEEE target
    * **Oct 15**: Final ESN software
    * **3rd wk Oct**: Review II
    * **Oct 25**: Hardware HIL validation
    * **Nov 20**: Final thesis
* **Visual Layout & Aesthetics**:
  * Top banner framing the final goal statement.
  * Center architecture flow block.
  * Bottom timeline axis with green milestone markers from August through November.
* **Speaker Delivery Notes**: "Our final goal for Phase 3 is to deploy and validate the lightweight ESN SOC/SOH estimator on ARTIX A7100T FPGA hardware using representative drive-cycle data. Our timeline targets completing our literature review paper for IEEE by August 31st, delivering final ESN software by October 15th, hardware HIL validation by October 25th, and submitting our capstone thesis by November 20th."
