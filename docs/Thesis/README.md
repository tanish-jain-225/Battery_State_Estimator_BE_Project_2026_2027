# B.E. Capstone Final Thesis / Dissertation

[← Back to Main Repository](../../README.md) · [← Review 2](../Review_2/Review_2_Progress.md) · [← FPGA IP Block](../../hardware/IP_Block/README.md) · [Capstone Thesis (Current)] · [Publications →](../Publications/README.md) · [Poster →](../Poster/README.md) · [View PDF Shell](Final_Thesis.pdf)

---

## 📌 Overview

This directory hosts the official **Final Year Bachelor of Engineering (B.E.) Capstone Project Dissertation Report**:

* **Project Title:** *Battery State Estimator: An ESN-Based Alternative to Extended Kalman Filter and Coulomb Counting*
* **Department:** Department of Automation and Robotics / Instrumentation
* **Institute:** Vivekanand Education Society's Institute of Technology (VESIT), Chembur, Mumbai
* **Affiliation:** University of Mumbai
* **Academic Year:** 2026–2027
* **Investigators:** Sanjna Patankar, Akshay Nambiar, Satvik Verma, Tanish Sanghvi
* **Project Mentor:** Dr. Kadambari Sharma
* **Project Guide / Coordinator:** Prof. Gopalkrishnan Narayan

---

## 📄 Deliverable Assets

| Asset File | Format | Target Size | Description | Status |
| :--- | :---: | :---: | :--- | :---: |
| [`Final_Thesis.pdf`](Final_Thesis.pdf) | PDF | A4 Portrait | Complete B.E. Capstone Dissertation Report adhering to University of Mumbai and VESIT thesis guidelines. | **Active Deliverable Shell** |

---

## 📑 Dissertation Chapter Structure & Outline

The final dissertation follows standard University of Mumbai academic specifications:

1. **Chapter 1 — Introduction & Problem Formulation**:
   * Critical role of SOC/SOH estimation in electric vehicles and BESS.
   * Drawbacks of Coulomb Counting (drift) and Extended Kalman Filters (parameter recalibration).
   * Motivation for data-driven, neuromorphic reservoir computing.
2. **Chapter 2 — Comprehensive Literature Review**:
   * Foundational multi-timescale EKF observers (*Li et al., 2020*).
   * Neuromorphic Spiking Neural Networks (SNNs) and Reservoir Computing (*Rigutini et al., 2020; Kamarudin et al., 2026*).
   * Edge AI hardware accelerators and benchmarking taxonomy.
3. **Chapter 3 — Cyber-Physical System Modeling**:
   * 2-RC Equivalent Circuit Model (ECM) and non-linear state equations.
   * Arrhenius electrochemical thermal coupling.
   * Multi-chemistry database (NMC, LFP, Lead-Acid) and active fault injection.
4. **Chapter 4 — Echo State Network (ESN) Estimator Design**:
   * Recurrent leaky-integrator reservoir dynamics ($\rho = 0.90–0.95$).
   * Closed-form single-shot Ridge regression readout training.
   * Dynamic battery aging tracking via online Recursive Least Squares (RLS).
5. **Chapter 5 — Embedded Microcontroller Firmware Optimization**:
   * C99 Compressed Sparse Row (CSR) matrix representation.
   * Fixed-point Q12/Q15 integer arithmetic and hardware $\tanh$ lookup tables.
   * Measured 6.7× inference speedup and 82.4% RAM savings on ARM Cortex-M4.
6. **Chapter 6 — FPGA Hardware Accelerator & IP Block**:
   * 100-neuron pipelined Verilog RTL on Xilinx Artix-7 (`xc7a100tcsg324-1`).
   * Plug-and-play AXI4-Lite/Stream IP block packaged to **IEEE 1685 IP-XACT** (`component.xml`).
   * Pre-compiled ready-to-flash bitstream (`esn_platform_top.bit`, 3.7 MB) with 200/200 bit-exact stage parity.
7. **Chapter 7 — Experimental Results & Comparative Validation**:
   * NASA PCoE battery aging dataset evaluation (32 cycles, 2,048 samples).
   * Multi-observer benchmark: ESN vs. UKF vs. EKF vs. Coulomb Counting.
   * 115 automated regression tests with 94.49% code coverage.
8. **Chapter 8 — Conclusion & Industrial Commercialization Roadmap**:
   * Real-time BMS headroom analysis (23× margin @ 100 Hz).
   * Technical trade-offs, patentable claims, and future physical benchtop deployment.

---

## 🔁 How to Update / Finalize Deliverables

To replace this placeholder shell with the final camera-ready dissertation exported from LaTeX or Word:
1. Compile your complete dissertation into a standard PDF (PDF/A compliant).
2. Save or overwrite [`docs/Thesis/Final_Thesis.pdf`](Final_Thesis.pdf).
3. Commit and push the final document to the repository.

---

[← Return to FPGA IP Block](../../hardware/IP_Block/README.md) · [Proceed to Academic Publications →](../Publications/README.md) · [Proceed to Capstone Poster →](../Poster/README.md)

