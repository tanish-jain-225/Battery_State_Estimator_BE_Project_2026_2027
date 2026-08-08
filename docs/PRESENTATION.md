[← Back to README](../README.md)

# PowerPoint Presentation Plan: First Progress Review

**Project Title**: BATTERY STATE ESTIMATOR: AN ESN-BASED ALTERNATIVE TO EKF AND COULOMB COUNTING

This document serves as an end-to-end slide-by-slide blueprint for your first capstone project review. It strictly adheres to the requested 5-slide format, presents an evidence-based progress summary divided by phases (Completed, In Progress, End Goal), clarifies that software is the final product while hardware acts as the testing loop, and includes academic publishing and thesis targets.

---

## ⏱️ Presentation Timing Overview
* **Total Duration**: ~5 Minutes (4:30 to 5:00 minutes)
* **Slide Budget**:
  * **Slide 1 (Title & Team)**: 25 Seconds
  * **Slide 2 (Introduction & Scope)**: 65 Seconds
  * **Slide 3 (Phase 1: Completed Work)**: 80 Seconds
  * **Slide 4 (Phase 2: In Progress Work)**: 80 Seconds
  * **Slide 5 (Phase 3: End Goal & Roadmaps)**: 50 Seconds

---

## 🎴 Slide-by-Slide PPT Content & Layout

### Slide 1: Title & Team Details
* **Slide Title**: Project Review I: BATTERY STATE ESTIMATOR
* **Slide Objective**: Introduce the project title, team members, department, and project guide.
* **Slide Bullet Points (On-Screen Text)**:
  * **Title**: **BATTERY STATE ESTIMATOR: AN ESN-BASED ALTERNATIVE TO EKF AND COULOMB COUNTING**
  * **Team Members**:
    * Tanish Sanghvi (Branch: Automation & Robotics | Email: 2023.tanish.sanghvi@ves.ac.in)
    * Akshay Nambiar (Branch: Automation & Robotics | Email: 2023.akshay.nambiar@ves.ac.in)
    * Sanjana Patankar (Branch: Automation & Robotics | Email: 2023.sanjana.patankar@ves.ac.in)
    * Satvik Verma (Branch: Automation & Robotics | Email: 2023.satvik.verma@ves.ac.in)
  * **Project Guide**: Dr. Kadambari Sharma
  * **Department**: Department of Automation and Robotics
  * **Institute**: VESIT, Mumbai
* **Visual Layout & Aesthetics**:
  * Clean, academic-themed high-contrast layout (dark slate background with gold or teal highlights).
  * VESIT logo positioned in the top-right corner.
  * GitHub repository link and Live Visualiser URL featured in the slide footer.
* **Speaker Delivery Notes**: "Good morning respected evaluators. We are team members Tanish, Akshay, Sanjana, and Satvik from the Automation and Robotics department. Our project is titled 'Battery State Estimator: An ESN-based Alternative to EKF and Coulomb Counting', supervised by Dr. Kadambari Sharma. Today, we will present our first progress review."

---

### Slide 2: Project Introduction & Design Scope
* **Slide Title**: Project Motivation & Design Objectives
* **Slide Objective**: Define the limitations of existing estimators, introduce the ESN-based solution, and clarify the project's software/hardware scope boundaries.
* **Slide Bullet Points (On-Screen Text)**:
  * **Limitations of Existing Observers**:
    * *Coulomb Counting (CC)*: Susceptible to continuous integration drift over time due to sensor measurement noise and offsets.
    * *Extended Kalman Filter (EKF)*: Computationally expensive, requires complex parameter characterization, and degrades with cell aging.
  * **Proposed ESN Solution (The End Product)**:
    * Standalone Echo State Network (ESN) software algorithm trained for non-linear regression of SOC and SOH.
    * Only the linear readout weights are trained, eliminating backpropagation-through-time, preserving computational resources.
  * **Core Scope & Deliverable Separation**:
    * **Software (End Product)**: The primary project outcome. Includes ESN SOC/SOH estimation models, physics-based 2-RC simulators, and Flask visualizer dashboard.
    * **Hardware (Testing & Verification Loop)**: The C99 embedded firmware and Verilog modules are strictly verification environments to test reservoir computing execution feasibility under microcontroller constraints.
* **Visual Layout & Aesthetics**:
  * Two-column split layout.
  * **Left Side**: Bulleted points detailing the problem, solution, and clear scope division.
  * **Right Side**: High-level block diagram showing the data flow where EKF and Coulomb Counting act strictly as baseline benchmarks for the ESN:
    ```mermaid
    flowchart TD
        Data[Battery Telemetry: V, I, T] --> CC[Coulomb Counting Baseline]
        Data --> EKF[Sage-Husa EKF Baseline]
        Data --> ESN[Proposed ESN Estimator]
        CC & EKF -->|Comparison metrics| Dash[Visualiser Dashboard]
        ESN -->|Proposed Alg Output| Dash
    ```
* **Speaker Delivery Notes**: "Existing battery state estimation approaches rely heavily on Coulomb Counting or EKF, which degrade under battery aging. We propose a data-driven Echo State Network. Crucially, the final deliverable is the software ESN SOC/SOH estimation algorithm, while our hardware C99 port and Verilog simulations serve strictly as a testing loop to prove execution feasibility on edge MCUs."

---

### Slide 3: Current Status - Phase 1: Completed Work
* **Slide Title**: Current Status: Phase 1 (Completed Work)
* **Slide Objective**: Present the completed deliverables in both the primary software development and the hardware verification loop.
* **Slide Bullet Points (On-Screen Text)**:
  * **Software Core (End Product progress)**:
    * Developed **2-RC Electro-Thermal Battery Simulator** solving dynamic polarization state equations ($V_{RC1}, V_{RC2}$) and thermal heat generation.
    * Implemented **Traditional Observers**: Sage-Husa Adaptive EKF (with covariance trace guards protecting $P$ from divergence), Coulomb Counting, and SOH RLS trackers.
    * Trained **Python Echo State Network (ESN)** models using experimental EV drive-cycle databases.
    * Created and deployed **Flask Dashboard & Telemetry DB** on Render with full comparative visualization.
  * **Hardware Testing Loop (Verification progress)**:
    * Ported the trained ESN model to **standalone C99 code** for embedded targets.
    * Compressed the reservoir matrix using **Compressed Sparse Row (CSR)** format, achieving a **6.7x speedup** by skipping zero-value multiplications.
    * Implemented **Q12/Q15 fixed-point math** with linear lookup table (LUT) approximation of $\tanh$.
    * Designed and simulated ESN arithmetic blocks in **Verilog HDL** for hardware-level RTL proof.
* **Visual Layout & Aesthetics**:
  * Grid layout featuring a screenshot of the deployed Flask Visualizer Dashboard alongside key validation metrics (e.g., ESN accuracy and execution latency).
* **Speaker Delivery Notes**: "Under Phase 1, we have fully completed the software simulator, baseline EKF/CC observers, ESN model training, and the Flask dashboard, all deployed on Render. In the hardware testing loop, we ported the ESN model to C99, optimized it with CSR compression for a 6.7x speedup, implemented integer fixed-point math with a tanh LUT, and successfully simulated the RTL in Verilog."

---

### Slide 4: Current Status - Phase 2: In Progress Work
* **Slide Title**: Current Status: Phase 2 (In Progress Work)
* **Slide Objective**: Outline what tasks are currently active in software refinement and hardware testing.
* **Slide Bullet Points (On-Screen Text)**:
  * **Software Core (Active Development)**:
    * **Online Readout Adaptation**: Integrating online Recursive Least Squares (RLS) or gradient descent into the ESN readout layer to dynamically adapt to cell aging and capacity fade in real-time.
    * **Deep Learning Benchmarking**: Building and training LSTM and GRU neural networks strictly as software baseline comparisons to verify ESN's computational advantage.
    * **Dynamic Workload Testing**: Running validations of ESN SOC/SOH accuracy under varying EV-style drive-cycles (DST, US06, FUDS).
  * **Hardware Testing Loop (Active Integration)**:
    * **STM32 Target Flashing**: Flashing the C99 ESN classifier code to a physical STM32 Nucleo microcontroller.
    * **Execution Profiling**: Measuring real-time CPU cycle counts, latency, and RAM/Flash memory footprint on the MCU.
    * **UART Telemetry Loop**: Setting up serial communication to stream simulator data directly to the STM32 and read back diagnostics.
* **Visual Layout & Aesthetics**:
  * Bullet points with progress icons (e.g., loading symbols) beside code block snippets or execution diagrams demonstrating STM32 serial interface connections.
* **Speaker Delivery Notes**: "We are currently in Phase 2. On the software side, we are active on online weight adaptation using RLS for cell aging, and training LSTM/GRU models to benchmark ESN's efficiency. On the hardware testing loop, we are flashing the C99 code onto a physical STM32 Nucleo board to profile its execution footprint and setting up serial playback to verify on-chip execution."

---

### Slide 5: Milestones & Deadlines - Phase 3: End Goal
* **Slide Title**: Semester Roadmap & Academic Deliverables
* **Slide Objective**: Present a clear timeline of the remaining targets, establishing the final end product goals and academic deliverables (review paper and thesis).
* **Slide Bullet Points (On-Screen Text)**:
  * **Phase 3: End Goal Deliverables**:
    * **Software End Product (Oct 15, 2026)**: Fully integrated and validated online-adaptive ESN battery SOC/SOH estimation algorithm, simulator, and comparison dashboard.
    * **Hardware Verification (Oct 25, 2026)**: Completed HIL test bench using the STM32 board and serial telemetry logging.
  * **Academic Outcomes (End Goal)**:
    * **Literature Review Paper (Aug 31, 2026)**: Finalizing and submitting our literature survey paper to a peer-reviewed conference/journal (Targeting IEEE).
    * **Capstone Project Thesis (Nov 20, 2026)**: Complete thesis documentation compiling model designs, simulator equations, ESN performance evaluations, and hardware validation results.
  * **Key Presentation Reviews**:
    * *Mid-Sem Progress Review (Review II)*: 3rd Week of October 2026.
* **Visual Layout & Aesthetics**:
  * Horizontal timeline or Gantt chart illustrating the transition from Completed (August) to In Progress (September) and End Goal milestones (October/November), marking the Review II, Paper, and Thesis milestones.
* **Speaker Delivery Notes**: "To conclude, our Phase 3 End Goal targets the final delivery of the online-adaptive ESN software estimator by mid-October, followed by full HIL testing. Academically, we are writing a literature review paper for IEEE submission by the end of August, and we will compile our complete capstone project thesis by November. This keeps us on track for our Review II in October."
