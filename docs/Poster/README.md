# Capstone Project Presentation Poster

[← Back to Main Repository](../../README.md) · [View PDF Poster](Project_Poster.pdf) · [Publications](../Publications/README.md)

---

## 📌 Overview

This directory contains the official **Academic Exhibition & Defense Presentation Poster** for the BE Capstone Project:

**Project Title:** *Battery State Estimator: An ESN-Based Alternative to EKF and Coulomb Counting*  
**Department:** Automation and Robotics / Instrumentation, VESIT, Mumbai  
**Academic Year:** 2026–2027  
**Team Members:** Sanjna Patankar, Akshay Nambiar, Satvik Verma, Tanish Sanghvi  
**Project Guide:** Dr. Kadambari Sharma  
**Coordinator:** Prof. Gopalakrishnan Narayanan  

---

## 📄 Deliverable Assets

| Asset File | Format | Target Size | Description | Status |
| :--- | :---: | :---: | :--- | :---: |
| [`Project_Poster.pdf`](Project_Poster.pdf) | PDF | A1 / A4 Landscape | Complete exhibition poster containing problem statement, 2-RC physics, cyber-physical architecture, C99 CSR SpMV, FPGA RTL, and benchmarks. | **Active Deliverable** |

---

## 📐 Poster Specifications & Design Guidelines

* **Target Physical Print Size:** Standard A1 Poster (594 × 841 mm / 23.4 × 33.1 inches), high-resolution 300 DPI.
* **Layout Structure:**
  1. **Header Banner:** Institute emblem, VESIT department header, full capstone project title, student authors, guide, and academic year.
  2. **Column 1 — Problem Statement & Physics:** Limitations of Coulomb Counting and pure EKF under thermal variation; 2-RC Equivalent Circuit Model (ECM) with Arrhenius thermal equations.
  3. **Column 2 — Cyber-Physical Architecture:** Dual-timescale estimation decoupling fast SOC tracking from slow SOH capacity fade; Leaky-Integrator ESN state dynamics and Ridge regression.
  4. **Column 3 — Embedded Microcontroller & FPGA Acceleration:** C99 ARM Cortex-M optimization using Compressed Sparse Row (CSR) SpMV; 256-entry Q15 tanh LUT; 5-stage pipelined Xilinx Artix-7 Verilog RTL.
  5. **Column 4 — Benchmarks & Live Verification:** 6.7× execution speedup, 10 KB Flash memory savings, 98.40% thermal diagnostic accuracy, 200/200 bit-exact FPGA parity, and live Render cloud links.
  6. **Footer Bar:** QR codes and URLs for Live Visualiser UI, Physics Simulator, and GitHub repository.

---

## 🔁 How to Update or Rebuild

To regenerate the vector PDF poster placeholder from source:

```bash
# From repository root:
python scripts/build_project_documents.py
```

To replace with the final camera-ready poster from Figma/Illustrator/Canva:
1. Export your design as a high-resolution PDF (PDF/X-1a or standard PDF 1.7).
2. Save or overwrite [`docs/Poster/Project_Poster.pdf`](Project_Poster.pdf).
3. Commit the updated asset to Git.

