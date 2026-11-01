# Reference Directory: Academic Manuscripts & Literature Base

[← Back to Main Repository](../README.md) · [Publications Hub](../docs/Publications/README.md) · [Project Poster](../docs/Poster/README.md)

---

## 📌 Overview

This directory acts as the academic repository hub containing both our project's **authored manuscripts** and the **foundational peer-reviewed literature** that underpins our cyber-physical battery state estimator architecture.

---

## ✍️ Authored Project Manuscripts (BE Capstone 2026–2027)

These manuscripts represent the core academic contributions produced by our project team at VESIT:

| Document | Target Venue | Format | File Links | Description |
| :--- | :--- | :---: | :--- | :--- |
| **Original Research Paper** | IEEE / Q3 Scopus Journal on Industrial Electronics / CPS | PDF & Markdown | [`Research_Paper.pdf`](Research_Paper.pdf)<br/>[`paper.md`](paper.md) | Co-designed 2-RC physics, 6.7× CSR SpMV speedup, Q15 fixed-point LUT, 200/200 FPGA Verilog RTL parity. |
| **Comprehensive Review Paper** | IEEE Transactions / Q3 Scopus Review Journal | PDF & Markdown | [`Review_Paper.pdf`](Review_Paper.pdf)<br/>[`review_paper.md`](review_paper.md) | 29-page review comparing classical observers, deep learning, SNNs, and reservoir computing on edge neuromorphic hardware. |

*Note: Canonical publications are also tracked in the documentation directory under [`docs/Publications/`](../docs/Publications/README.md).*

---

## 📚 Foundational Literature & Benchmark Papers

These external papers provided the theoretical baselines and mathematical benchmarks for our Kalman filters and Echo State Networks:

| Reference File | Citation & Title | Role in Project Architecture |
| :--- | :--- | :--- |
| [`paper_ekf_soc_soh.pdf`](paper_ekf_soc_soh.pdf) | **Li et al. (2020)**<br/>*Joint estimation of SOC and SOH for lithium-ion batteries based on EKF multiple time scales* | Guided our decoupled dual-timescale observer: microscale EKF for SOC ($T_s=1\text{ s}$) and macroscale RLS for SOH. |
| [`paper_rc_soc_soh.pdf`](paper_rc_soc_soh.pdf) | **Rigutini et al. (2020)**<br/>*State-of-charge estimation of lithium-ion batteries using reservoir computing* | Benchmark baseline for Echo State Network reservoir topology, spectral radius bounds ($\rho=0.95$), and leak rate ($\alpha=0.3$). |

---

## 🔬 Key Mathematical Foundations

* **2-RC Equivalent Circuit Model (ECM):**
  $$V_t(t) = OCV(\text{SOC}) - I R_0 - V_1(t) - V_2(t)$$
* **Arrhenius Parameter Scaling:**
  $$\theta(T) = \theta(T_{\text{ref}}) \cdot \exp\left[\frac{E_a}{R_{\text{gas}}} \left(\frac{1}{T} - \frac{1}{T_{\text{ref}}}\right)\right]$$
* **Leaky Reservoir Dynamics:**
  $$\tilde{x}_t = \tanh\left(\mathbf{W}_{\text{in}} [1; u_t] + \mathbf{W}_{\text{res}} x_{t-1}\right), \quad x_t = (1 - \alpha) x_{t-1} + \alpha \tilde{x}_t$$

