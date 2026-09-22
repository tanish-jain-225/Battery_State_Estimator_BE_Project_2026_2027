[← Back to README](../README.md) · [Web Research & Industrial Audit](Resources/WEB_RESEARCH.md) · [IEEE / Q3 Review Paper Manuscript](../reference/review_paper.md)

# Literature Survey: Neuromorphic Computing, Spiking Networks, and Reservoir Computing for Intelligent Battery Management Systems

This document synthesizes the academic literature, theoretical foundations, and state-of-the-art estimation paradigms for Battery Management Systems (BMS). It traces the field from conventional control-theoretic observers and deep learning architectures to neuromorphic computing, Spiking Neural Networks (SNNs), Reservoir Computing (RC), Liquid State Machines (LSMs), event-driven sensing, and hardware acceleration platforms.

> **Full Manuscript Reference:** [`reference/review_paper.md`](../reference/review_paper.md) — *Neuromorphic Computing for Intelligent Battery Management Systems: A Comprehensive Review of Spiking Neural Networks, Reservoir Computing and Edge AI* (September 2026 Edition).

---

## 📑 Table of Contents
1. [BMS Estimation Tasks & Shared Operational Challenges](#1-bms-estimation-tasks--shared-operational-challenges)
2. [Conventional Estimation Methods (Classical & Observers)](#2-conventional-estimation-methods-classical--observers)
3. [Deep Learning Approaches & The Edge-Deployment Limit](#3-deep-learning-approaches--the-edge-deployment-limit)
4. [Spiking Neural Networks (SNNs) for BMS](#4-spiking-neural-networks-snns-for-bms)
5. [Reservoir Computing (RC) & Liquid State Machines (LSMs)](#5-reservoir-computing-rc--liquid-state-machines-lsms)
6. [Neuromorphic Hardware Platforms & Event-Driven Sensing](#6-neuromorphic-hardware-platforms--event-driven-sensing)
7. [Multi-Dimensional Benchmarking & Research Roadmap](#7-multi-dimensional-benchmarking--research-roadmap)

---

## 1. BMS Estimation Tasks & Shared Operational Challenges

A BMS supervises cell safety, remaining capacity, peak power, and battery longevity by estimating four unmeasurable internal states:
* **State of Charge (SOC)**: Usable chemical energy percentage ($\text{SOC} \in [0, 100\%]$). Target accuracy $\le \pm 2–5\%$ under sub-second real-time constraints.
* **State of Health (SOH)**: Structural capacity retention ($\text{SOH} = C_{\text{present}}/C_{\text{rated}} \times 100\%$) and internal resistance ($R_0$) growth.
* **State of Power (SOP)**: Peak deliverable/absorbable power over short horizons (2–10 s).
* **Remaining Useful Life (RUL)**: Cycle or time horizon forecasting before reaching end-of-life threshold (70–80% retention).

### Operational Distortions Across Benchmarks
Real-world estimation faces electrochemical nonlinearity (steep OCV knees, LFP plateaus), Arrhenius temperature shifts ($-20\text{ }^\circ\text{C} \text{ to } +55\text{ }^\circ\text{C}$), dynamic load variations, sensor noise/bias drift, cell imbalance, and hysteresis. Benchmarks depend on standard corpora: **NASA PCoE** (18650 NCA), **CALCE** (prismatic LCO), **Oxford** (pouch cell), and **Panasonic** (cylindrical NMC dynamic profiles).

---

## 2. Conventional Estimation Methods (Classical & Observers)

* **Coulomb Counting & OCV Mapping**: Coulomb counting integrates net current ($O(1)$ complexity) but drifts $5–10\%$ over a 2-hour drive cycle due to sensor bias. OCV mapping requires extended rest (3–4 hours) and fails during active drive cycles or on flat LFP OCV plateaus.
* **Equivalent Circuit Models (ECM)**: Lumped 1-RC and 2-RC networks balance physical accuracy against real-time execution. Extended Kalman Filters (EKF) linearize non-linear voltage equations via Taylor Jacobians ($\mathbf{H}_k$).
* **Multi-Timescale Decoupling (*Li et al., 2020*)**: Decouples fast intra-cycle SOC tracking ($1\text{ s}$) from slow inter-cycle SOH capacity degradation ($100–1000\text{ s}$), preventing covariance blowup and computational redundancy.
* **Unscented Kalman Filter (UKF)**: Propagates $2n+1$ deterministic sigma points through non-linear voltage curves via Merwe transform, eliminating Jacobians but increasing compute by $2.5\times–3\times$.

---

## 3. Deep Learning Approaches & The Edge-Deployment Limit

* **Feedforward & Recurrent Architectures**: Deep MLPs, LSTMs, GRUs, and Spatio-Temporal Attention LSTMs (STL-LSTM) achieve high accuracy ($R^2 > 0.99$), but Backpropagation Through Time (BPTT) and heavy parameter matrices ($> 500\text{ KB}$) exceed microcontroller RAM.
* **Convolutional & Transformer Hybrids**: 1D-CNNs extract incremental capacity ($\text{d}Q/\text{d}V$) signatures. Dual-encoder Transformers and Cross-Attention Multitask Transformers (CA-MT-BHP) achieve sub-1% SOC/SOH error but strain edge compute budgets.
* **Physics-Informed Neural Networks (PINNs)**: Embed Fick's law of solid-phase diffusion (Single Particle Model) directly into neural network loss functions, outperforming unconstrained MLPs under small-sample training.
* **The Edge-Deployment Limit**: Quantization-Aware Training (QAT) and Neural Architecture Search (NAS) reduce model footprint but require heavy retraining overhead. On-device fine-tuning via backpropagation remains memory-prohibitive for embedded BMS microcontrollers.

---

## 4. Spiking Neural Networks (SNNs) for BMS

SNNs replace continuous activations with sparse, event-driven discrete spikes, shifting execution from synchronous Multiply-Accumulate (MAC) to sparse Accumulate (AC) updates.

* **Neuron Models**: Leaky Integrate-and-Fire (LIF) provides the optimal balance of biological fidelity and execution cost. Adaptive LIF (ALIF) adds spike-frequency adaptation for sequence credit assignment.
* **Spike Encoding**: Step-Forward (SF) rate/temporal encoding cuts operations by $30–60\times$ compared to continuous inputs.
* **Training Paradigms**: Surrogate-Gradient (SG) BPTT (smooths spike derivatives), ANN-to-SNN conversion (~20,000 spikes/inf), and STDP unsupervised Hebbian learning (~5 mJ/inf).
* **BMS Benchmark**: *SpikeSOH* achieved **99.2% energy reduction and $>280\times$ speedup** over CNN-LSTM baselines ($0.36\text{ mJ/inference}$).

---

## 5. Reservoir Computing (RC) & Liquid State Machines (LSMs)

Reservoir Computing projects inputs into a high-dimensional recurrent reservoir ($\mathbf{x}_t \in \mathbb{R}^{N_{res}}$) with **fixed random weights** ($W_{in}, W$) satisfying the **Echo State Property** ($\rho(W) < 1$). Readout weights ($W_{out}$) are trained in a single shot via L2-regularized Ridge Regression without backpropagation:
$$\mathbf{W}_{\text{out}} = \mathbf{Y}_{\text{target}} \mathbf{X}^T (\mathbf{X} \mathbf{X}^T + \lambda \mathbf{I})^{-1}$$

* **ESNs vs Spiking Reservoirs (RSNNs / LSMs)**: ESNs use continuous (tanh/sigmoid) synchronous neurons, ideal for near-term MCU/FPGA deployment. RSNNs/LSMs use spiking LIF neurons, natively suited for neuromorphic hardware.
* **BMS Application (*Kamarudin et al., 2026*)**: RSNNs reached SOH RMSE of 0.029 with $12–26\text{ ms}$ latency. Our fixed-point Q6.10 Echo State Network (100 neurons, 4 inputs, seed=42) achieves $R^2 = 0.8783$ test SOC estimation with zero DSP usage on FPGA fabric.

---

## 6. Neuromorphic Hardware Platforms & Event-Driven Sensing

### Neuromorphic Silicon Survey

| Platform | Type / Architecture | Power Envelope | BMS Suitability Note |
| :--- | :--- | :---: | :--- |
| **Intel Loihi 2** | Digital async, custom LIF cores | 30–80 mW/core | High neuron density; Lava software stack |
| **SpiNNaker2** | ARM-core software simulation | Scalable DVFS | Flexible ARM cluster; software SNN simulation |
| **BrainChip Akida** | Digital feedforward commercial IP | $< 10\text{ mW}$ | Sub-10mW always-on; requires recurrence co-design |
| **IBM TrueNorth** | Digital GALS 2D mesh | ~70 mW | High efficiency; limited on-chip learning |
| **Memristor / RRAM** | Analog in-memory compute | Very low (fJ/SOP) | Analog Ohm/Kirchhoff MAC; lab-stage maturity |
| **FPGA (Artix-7)** | Reconfigurable digital logic | 100s mW | **Best near-term prototyping flexibility for custom ESN/SNN** |

### Event-Driven Sensing
Fixed-rate ADC acquisition samples continuously regardless of signal change. Event-driven level-crossing (delta) sensing generates telemetry spikes only when signals change beyond threshold ($\Delta V, \Delta I, \Delta T$), reducing sample acquisition overhead by 1–2 orders of magnitude during rest and light-load regimes.

---

## 7. Multi-Dimensional Benchmarking & Research Roadmap

### 6-Dimension Evaluation Framework
1. **Accuracy**: MAE, RMSE, $R^2$ across train/test splits.
2. **Energy/Power per Inference**: Sustained operating cost per cell.
3. **Training Cost & Data Efficiency**: Single-shot closed-form ESN readout vs heavy DL backpropagation.
4. **Latency & Real-Time Suitability**: Sub-second control-loop compatibility ($428.1\text{ }\mu\text{s}$ per update on Artix-7).
5. **Hardware-Deployment Feasibility**: Memory footprint (CSR sparse SpMV saving 82.4% RAM) and integer quantization (Q15 / Q6.10).
6. **Robustness Across Conditions**: Generalization to unseen drive cycles, temperatures, and aging fade.

### Research Roadmap Horizons
- **Near-term**: Standardized reporting of energy/inference on named hardware; fixed-point ESN FPGA/MCU verification.
- **Medium-term**: Multi-chemistry, multi-temperature validation beyond NASA/CALCE datasets.
- **Long-term**: End-to-end event-driven sensor-to-spike-to-decision pipelines on physical neuromorphic silicon.
