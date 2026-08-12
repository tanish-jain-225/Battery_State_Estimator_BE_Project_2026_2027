[← Back to README](../../README.md)

# BE Project Proposal (Academic Year 2026-2027)

**Submission Date:** 12th August 2026  
**Department:** Instrumentation / Automation and Robotics  
**Institute:** Vivekanand Education Society's Institute of Technology (VESIT), Mumbai  

---

## 1. Project Details

* **Project Title:** Battery State Estimator: An ESN-Based Alternative to EKF and Coulomb Counting
* **Domain:** Cyber-Physical Systems, Embedded Systems, Machine Learning & Battery Management Systems (BMS)
* **Project Guide:** Dr. Kadambari Sharma

---

## 2. Team Members

| Sr. No. | Student Name | Roll No. | Branch | Email ID |
| :---: | :--- | :---: | :---: | :--- |
| 1 | Sanjna Patankar | 2023.sanjna.patankar | Automation and Robotics | 2023.sanjna.patankar@ves.ac.in |
| 2 | Akshay Nambiar | 2023.akshay.nambiar | Automation and Robotics | 2023.akshay.nambiar@ves.ac.in |
| 3 | Satvik Verma | 2023.satvik.verma | Automation and Robotics | 2023.satvik.verma@ves.ac.in |
| 4 | Tanish Sanghvi | 2023.tanish.sanghvi | Automation and Robotics | 2023.tanish.sanghvi@ves.ac.in |

---

## 3. Abstract

Accurate estimation of Battery State of Charge (SOC) and State of Health (SOH) is essential for electric vehicles (EVs) and battery energy storage systems (BESS). Conventional techniques like Coulomb Counting suffer from cumulative integration drift, while Extended Kalman Filtering (EKF) requires precise electro-thermal model parameters and high computational power.

This project proposes an Echo State Network (ESN) based Reservoir Computing observer as a lightweight, data-driven alternative. A 2-RC electro-thermal battery physics simulator generates real-time telemetry (Voltage, Current, Temperature) across standard dynamic drive cycles (DST, US06, FUDS). The ESN is benchmarked against EKF, Coulomb Counting, and VFF-RLS estimators, delivering an SOC RMSE under 1.5%.

For embedded and edge deployment, the ESN inference is optimized using Compressed Sparse Row (CSR) matrix representation and fixed-point math, achieving a 6.7× inference speedup on ARM Cortex-M microcontrollers. Additionally, a 100-neuron Verilog RTL datapath is verified bit-exactly on a Xilinx Artix-7 FPGA target.

---

## 4. Problem Statement & Motivation

Existing Battery Management Systems face two main challenges:
1. **Coulomb Counting Integration Drift:** Sensor inaccuracies accumulate linearly over time, corrupting long-term SOC metrics.
2. **Computational & Recalibration Overhead of EKF:** Matrix inversion per timestep requires heavy CPU processing on microcontrollers, and battery degradation (SOH fade) requires constant parameter recalibration.

**Motivation:** By deploying an Echo State Network (ESN), the recurrent reservoir provides rich temporal memory without requiring complex backpropagation through time. It eliminates the need for battery parameter identification while executing efficiently on low-power edge hardware.

---

## 5. Objectives

1. Develop a 2-RC Electro-Thermal Battery Physics Simulator supporting dynamic load profiles and fault injection (thermal runaway, sensor dropout).
2. Implement conventional estimation observers (EKF, Coulomb Counting, VFF-RLS) alongside an ESN model.
3. Optimize ESN inference for microcontrollers using Compressed Sparse Row (CSR) SpMV and Q12/Q15 fixed-point arithmetic.
4. Synthesize and verify a 100-neuron ESN Verilog RTL datapath on FPGA against a Python golden model.
5. Create a web-based Flask dashboard for real-time telemetry visualization and estimator benchmarking.
6. Publish research findings in a peer-reviewed conference/journal (IEEE target).

---

## 6. Hardware & Software Tools Required

* **Hardware:** ARM Cortex-M Microcontroller (STM32), Xilinx Artix-7 FPGA (ARTIX A7100T), USB-TTL Interface.
* **Software:** Python 3.8+ (NumPy, SciPy, Pandas), Flask, C99 GCC Compiler, Xilinx Vivado & XSim, Git & GitHub.

---

## 7. Deliverables & Expected Outcomes

* Operational Flask Web Dashboard with real-time Chart.js telemetry graphs.
* Optimized C99 firmware with 6.7× CSR SpMV speedup.
* Verilog RTL 100-neuron reservoir datapath verified bit-exactly (200/200 matches).
* Peer-reviewed research paper submission to IEEE conference.
* Comprehensive GitHub repository & GitHub Log Book.
