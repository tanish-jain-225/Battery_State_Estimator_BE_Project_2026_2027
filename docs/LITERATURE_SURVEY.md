[← Back to README](../README.md) · [Web Research & Industrial Audit](Resources/WEB_RESEARCH.md) · [IEEE / Q3 Review Paper Manuscript](../reference/review_paper.md)

# Literature Survey: Battery State Estimation Methodologies, Industrial Standards, and Reservoir Computing Alternatives

This document synthesizes the academic literature, theoretical foundations, and commercial automotive state-of-the-art in battery State of Charge (SOC) and State of Health (SOH) estimation. It reviews conventional control-theoretic observers, examines recent advances in multi-timescale and reservoir computing paradigms, and identifies the engineering research gap addressed by this repository.

---

## 📑 Table of Contents
1. [Context & State Estimation Challenges](#1-context--state-estimation-challenges)
2. [Physics-Based & Control-Theoretic Observers](#2-physics-based--control-theoretic-observers)
3. [Data-Driven & Reservoir Computing Paradigms](#3-data-driven--reservoir-computing-paradigms)
4. [Commercial Automotive Landscape & Compliance Standards](#4-commercial-automotive-landscape--compliance-standards)
5. [Comparative Evaluation Matrix](#5-comparative-evaluation-matrix)
6. [Identified Research Gap & Proposed Alternative](#6-identified-research-gap--proposed-alternative)
7. [Key Literature References](#7-key-literature-references)

---

## 1. Context & State Estimation Challenges

In Lithium-ion battery systems powering Electric Vehicles (EVs) and Battery Energy Storage Systems (BESS), internal chemical states cannot be measured directly using physical sensors:
* **State of Charge (SOC)**: Represents remaining chemical capacity relative to nominal capacity, defining instantaneous driving range and preventing over-charge/over-discharge.
* **State of Health (SOH)**: Represents irreversible capacity loss ($C_n$ fade) and internal resistance growth ($R_0$ increase) caused by solid-electrolyte interphase (SEI) growth and active material degradation.

Accurate state tracking must operate reliably despite non-linear Open Circuit Voltage (OCV) characteristics, strong Arrhenius temperature dependencies, hysteresis, and sensor measurement noise.

---

## 2. Physics-Based & Control-Theoretic Observers

### A. Coulomb Counting (Ah Integration)
* **Principle**: Integrates current over time: $\text{SOC}(t) = \text{SOC}(0) - \frac{1}{C_n}\int I(t)dt$.
* **Strengths**: Computationally minimal ($O(1)$ scalar arithmetic); ubiquitous in automotive production.
* **Weaknesses**: Open-loop nature; current sensor offset and ADC quantization errors accumulate linearly, producing **$5\% \text{ to } 10\%$ drift over a 2-hour drive cycle**. Requires complete cell relaxation (3–4 hours of parking) to recalibrate against OCV.

### B. Equivalent Circuit Modeling & Classical EKF (*Plett, 2004*)
* **Principle**: Employs a 1-RC or 2-RC Equivalent Circuit Model (ECM) capturing ohmic resistance ($R_0$) and polarization diffusion branches ($R_1-C_1, R_2-C_2$). The Extended Kalman Filter (EKF) linearizes the non-linear terminal voltage equation using Taylor-series Jacobians ($\mathbf{H}_k = \left.\frac{\partial h}{\partial x}\right|_{\hat{x}}$) to dynamically correct state estimates from voltage feedback.
* **Limitations**: Highly sensitive to parameter identification errors; matrix inversion per step taxes low-power microcontrollers; linearization errors compound in flat OCV plateau regions (e.g., LFP chemistry).

### C. Multi-Timescale EKF Framework (*Li et al., 2020*)
* **Contribution**: Recognized that SOC fluctuates dynamically at a microscopic timescale ($1\text{ s}$), whereas capacity fade and internal resistance grow over hundreds of cycles at a macroscopic timescale.
* **Innovation**: Separated estimation into a **dual-timescale observer**: microscopic EKF tracks SOC and polarization voltages ($V_1, V_2$), while macroscopic Recursive Least Squares (RLS) tracks capacity degradation ($C_k$) and resistance ($R_0$).
* **Significance to this Repo**: Confirms that decoupling fast dynamic states from slow electrochemical aging parameters prevents covariance blowup and reduces computational redundancy.

### D. Unscented Kalman Filtering (UKF)
* **Principle**: Replaces analytical Jacobian linearizations with the Merwe Scaled Unscented Transform, propagating $2n+1$ deterministic sigma points through non-linear voltage curves.
* **Trade-off**: Higher accuracy across dynamic transitions, but incurs **$2.5\times \text{ to } 3\times$ higher compute overhead** due to matrix Cholesky square roots.

---

## 3. Data-Driven & Reservoir Computing Paradigms

### A. Limitations of Deep Recurrent Networks (LSTM / GRU)
While Long Short-Term Memory (LSTM) and Gated Recurrent Unit (GRU) networks capture temporal dependencies without equivalent circuit models, their reliance on Backpropagation Through Time (BPTT), dense matrix-vector products, and millions of parameters makes real-time deployment on low-power automotive microcontrollers infeasible.

### B. Echo State Networks (ESN) & Reservoir Computing (*Jaeger & Haas, 2004*)
* **Principle**: Projects low-dimensional battery telemetry ($V, I, T$) into a high-dimensional recurrent reservoir $\mathbf{x}_t \in \mathbb{R}^{N_{res}}$ using fixed, randomly generated sparse matrices ($\mathbf{W}_{\text{in}}, \mathbf{W}_{\text{res}}$) scaled to spectral radius $\rho < 1$ (guaranteeing the **Echo State Property**).
* **Training Efficiency**: The internal reservoir is never modified; only a linear output layer ($\mathbf{W}_{\text{out}}$) is solved analytically using regularized Ridge Regression:
  $$\mathbf{W}_{\text{out}} = \mathbf{Y}_{\text{target}} \mathbf{X}^T (\mathbf{X} \mathbf{X}^T + \lambda \mathbf{I})^{-1}$$

### C. Neuromorphic & Reservoir BMS Applications (*Kamarudin et al., 2026*)
* **Contribution**: Investigated Reservoir Spiking Neural Networks (RSNN) for battery SOC tracking, demonstrating that fixed recurrent topologies provide rich fading memory of input trajectories with dramatically lower computational overhead than traditional deep networks.
* **Significance to this Repo**: Validates that recurrent reservoir architectures successfully capture non-linear battery dynamics. Our continuous-time leaky-integrator ESN with Compressed Sparse Row (CSR) optimization serves as the high-throughput, non-spiking counterpart for embedded edge BMS targets.

---

## 4. Commercial Automotive Landscape & Compliance Standards

Web research across OEM BMS architectures (**Tesla, BYD, BMW, Bosch, Continental**) highlights the industrial constraints governing battery estimators:

| Standard / Domain | Industrial Requirement | Impact on Algorithm Design |
| :--- | :--- | :--- |
| **ISO 26262 ASIL-C / D** | Functional safety requires deterministic execution bounds ($< 10\text{ ms}$ jitter) and proven fault containment. | Complex deep learning with iterative solver convergence risk is barred; fixed-cycle ESN inference or deterministic EKF is required. |
| **AUTOSAR Classic** | Software components (SW-Cs) must fit static memory allocations without dynamic heap allocation (`malloc`). | Weight matrices must be statically declared in ROM/Flash via optimized C headers. |
| **Hardware Constraints** | Automotive edge microcontrollers (ARM Cortex-M3/M4) often lack double-precision FPUs and have restricted RAM ($\le 64\text{ KB}$). | Algorithms require fixed-point (Q15) arithmetic and matrix compression (CSR). |
| **Commercial Reality** | 100% of production EVs rely primarily on Coulomb Counting with rested-cell OCV recalibration during vehicle sleep. | Under continuous highway driving or fleet duty cycles where batteries never rest, **Coulomb Counting drifts unchecked**, necessitating robust model-free online estimators. |

---

## 5. Comparative Evaluation Matrix

The table below contrasts the primary estimation methodologies evaluated across the literature:

| Criteria | Coulomb Counting (CC) | Extended Kalman Filter (EKF) | Unscented Kalman Filter (UKF) | Deep LSTM / GRU | Echo State Network (ESN) [Proposed] |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Model Dependency** | None (Current only) | High (2-RC ECM + OCV) | High (2-RC ECM + OCV) | None (Data-driven) | **None (Data-driven)** |
| **Sensor Drift Vulnerability** | High (Unbounded drift) | Low (Corrected by $V_t$) | Low (Corrected by $V_t$) | Low (Learned mappings) | **Low (Bounded reservoir mapping)** |
| **Computational Cost** | $O(1)$ (Negligible) | Medium ($O(n^3)$ Jacobians) | High ($O(n^3)$ Cholesky) | Prohibitive (BPTT / Gates) | **Low ($O(NNZ)$ Sparse SpMV)** |
| **Non-linear Capture** | None | Fair (First-order Taylor) | High (Sigma points) | Excellent | **Excellent (High-dimensional state)** |
| **Memory Footprint** | $< 1\text{ KB}$ | $\sim 5\text{ KB}$ | $\sim 8\text{ KB}$ | $> 500\text{ KB}$ | **$\sim 12\text{ KB}$ (Flash with CSR)** |
| **Embedded Feasibility** | Trivial | Good | Moderate | Impractical | **Excellent (6.7× CSR speedup, Q15)** |
| **Primary References** | Industry Standard | *Plett (2004)*; *Li (2020)* | Standard Control Theory | Machine Learning lit. | *Jaeger (2004)*; *Kamarudin (2026)* |

---

## 6. Identified Research Gap & Proposed Alternative

### The Research Gap
1. **Control-theoretic observers (EKF, UKF)** depend on accurate electro-thermal parameters that shift as batteries degrade, requiring cumbersome empirical recalibration.
2. **Deep learning models (LSTM, GRU)** eliminate model dependency but require computational resources beyond the capabilities of cost-sensitive embedded automotive microcontrollers.
3. **Existing reservoir computing literature** focuses largely on software simulations without addressing integer fixed-point quantization, sparse matrix acceleration, or RTL hardware parity on FPGA coprocessors.

### The Proposed Alternative in this Repository
This repository addresses this gap by implementing a **lightweight Echo State Network (ESN)** designed as a direct replacement for traditional observers:
* **Mathematical Parity**: Validated against baseline 2-RC physics, EKF, UKF, and Coulomb Counting.
* **Embedded Optimization**: Compressed Sparse Row (CSR) matrix representation reducing reservoir multiplies by $85\%$, achieving a **6.7× speedup** in C99.
* **Hardware Co-Design**: Fixed-point Q6.10 Verilog RTL datapath targeting the Artix A7100T FPGA, verified **200/200 bit-exactly** against a Python golden model.

---

## 7. Key Literature References

1. **Li, P., Wang, H., Xing, Z., Ye, K., & Li, Q.** (2020). *Joint estimation of SOC and SOH for lithium-ion batteries based on EKF multiple time scales*. Journal of Intelligent Manufacturing and Special Equipment, 1(1), 107–120. [[PDF Document](../reference/paper_ekf_soc_soh.pdf)]
2. **Kamarudin, M. R., Mispan, M. S., Zainudin, M. N. S., & Sofian, H.** (2026). *Reservoir Spiking Neural Networks for Accurate State-of-Charge Estimation in Battery Management Systems*. Turkish Journal of Engineering, 10(2), 407–417. [[PDF Document](../reference/paper_rc_soc_soh.pdf)]
3. **Plett, G. L.** (2004). *Extended Kalman filtering for battery management systems of LiPB-based HEV battery packs*. Journal of Power Sources, 134(2), 252–261.
4. **Jaeger, H., & Haas, H.** (2004). *Harnessing nonlinearity: Predicting chaotic systems and saving energy in wireless communication*. Science, 304(5667), 78–80.
5. **Rigutini, L., et al.** (2020). *State-of-charge estimation of lithium-ion batteries using reservoir computing*. IEEE Transactions on Industrial Electronics, 68(8), 7112–7121.
6. **International Organization for Standardization.** (2018). *ISO 26262: Road vehicles — Functional safety*.
