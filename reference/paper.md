[← Back to README](../README.md) · [Camera-Ready IEEE Research Paper (Synced v2.4.0)](../docs/Publications/Research_Paper.pdf) · [Review Paper Deliverable (Pending v2.4.1)](../docs/Publications/Review_Paper.pdf)

# Edge-Based Sparse Reservoir Computing and State Observers for Real-Time Battery Diagnostics in Cyber-Physical Systems

**Sanjna Patankar, Akshay Nambiar, Satvik Verma, Tanish Sanghvi, and Kadambari Sharma**  
*Department of Automation and Robotics / Instrumentation, VESIT, Mumbai, India*  
*Emails: {2023.sanjna.patankar, 2023.akshay.nambiar, 2023.satvik.verma, 2023.tanish.sanghvi}@ves.ac.in*  
**Target Publication Venues:** IEEE Transactions on Industrial Electronics / IEEE Access / IEEE Potentials (Student Journal) / Q3 Scopus-Indexed CPS Journals

---

**Abstract** — Reliable estimation of State of Charge (SOC) and State of Health (SOH) in Lithium-Ion batteries is critical for electric vehicles (EVs) and smart grids. Traditional observers, such as the Extended Kalman Filter (EKF), rely on high-fidelity physical models but degrade under unmodeled dynamics and cell aging. Conversely, deep recurrent neural networks present high computational costs that prevent edge deployment. This paper presents a co-designed cyber-physical system combining a 2-RC Equivalent Circuit Model (ECM) simulator, multi-timescale EKF observers, and Leaky-Integrator Echo State Networks (ESNs) for joint state tracking. Building upon the foundational multi-timescale estimation principles of **Li et al. (2020)** and the reservoir computing paradigms of **Rigutini et al. (2020)** and **Kamarudin et al. (2026)**, we implement an optimized, edge-capable ESN classifier on an ARM Cortex-M microcontroller and an IEEE 1685 IP-XACT plug-and-play FPGA IP block. By introducing Compressed Sparse Row (CSR) sparse matrix-vector multiplication (SpMV) and fixed-point Q12/Q15 integer arithmetic with lookup table (LUT) linear interpolation, we achieve a **6.7× execution speedup** and save **~10 KB of Flash memory**, while maintaining classification accuracy at **98.40%** under dynamic drive cycles. We also detail our academic dissemination plan targeting IEEE Transactions and peer-reviewed student journals.

---

## I. Introduction
Battery state estimators must accurately estimate internal cell states that cannot be measured directly. State of Charge (SOC) represents the remaining chemical energy, whereas State of Health (SOH) represents the capacity fade and resistance growth due to electrochemical degradation.

Historically, observers like the Extended Kalman Filter (EKF) have dominated battery state estimation implementations. By linearizing cell voltage equations around the current operating point, EKF dynamically corrects coulomb-counting errors. However, parameter drift under thermal variation and accelerated aging degrades EKF accuracy. To overcome this, joint estimation frameworks of SOC and SOH have been developed. Notably, **Li et al. [1] ([`paper_ekf_soc_soh.pdf`](paper_ekf_soc_soh.pdf))** formulated a seminal multi-time scale EKF observer design that decouples SOC estimation at a microscopic timescale ($T_s = 1\text{ s}$) from slowly changing capacity (SOH) estimation at a macroscopic timescale, preventing gradient instability and establishing the analytical benchmark for our comparative physics pipeline.

In parallel, machine learning approaches have emerged to capture unmodeled cell dynamics. While deep recurrent models (e.g., LSTMs and GRUs) offer sequence tracking, their computational cost, iterative matrix recalculations, and backpropagation-through-time (BPTT) overhead prevent edge deployment on low-power microcontrollers. Recently, **Rigutini et al. [5]** and **Kamarudin et al. [2] ([`paper_rc_soc_soh.pdf`](paper_rc_soc_soh.pdf))** demonstrated that Reservoir Computing (RC) and Reservoir Spiking Neural Networks (RSNNs) provide exceptional temporal feature extraction with minimal computational burden by fixing the high-dimensional recurrent reservoir and training only a linear output readout layer. 

In this work, we present a co-designed cyber-physical system building directly upon the theoretical foundations established by Li et al. [1] and Rigutini / Kamarudin et al. [2]. We implement a dual-timescale estimator pipeline combining a physics-based EKF with online Recursive Least Squares (RLS) parameter identification, alongside a continuous-time leaky-integrator Echo State Network (ESN) as a high-performance, edge-deployable alternative. Furthermore, we deploy an optimized, sparse, fixed-point version of the ESN classifier directly on low-power ARM Cortex-M microcontrollers and synthesize a bit-exact plug-and-play AXI4 IP block (`esn_axi_ip`) for FPGA acceleration.

---

## II. System Architecture & Methodology

The system is structured as a modular cyber-physical loop. It consists of a physics-based simulator modeling cell electro-thermal dynamics and fault states, an observer dashboard running EKF, UKF, and ESN estimators, and optimized embedded diagnostic firmware.

### A. Battery Physics Simulation
The battery cell is represented by a 2-RC Equivalent Circuit Model (ECM), modeling polarization voltage dynamics ($V_1, V_2$), ohmic losses ($I \cdot R_0$), convective cooling and capacity fade. Parameter values depend on temperature ($T$) via Arrhenius equations:
$$\theta(T) = \theta(T_{\text{ref}}) \cdot \exp\left[\frac{E_a}{R_{\text{gas}}} \left(\frac{1}{T} - \frac{1}{T_{\text{ref}}}\right)\right]$$

### B. Extended Kalman Filter Observer (Li et al. Baseline)
The state vector is $x_k = [\text{SOC}_k, V_{1,k}, V_{2,k}]^T$. EKF estimates SOC by matching measured terminal voltage ($V_m$) against predicted voltage ($V_p$):
$$\hat{y}_k = OCV(\hat{\text{SOC}}_{k|k-1}) + I_k R_0 + \hat{V}_{1,k|k-1} + \hat{V}_{2,k|k-1}$$
$$\mathbf{H}_k = \begin{bmatrix} \left.\frac{dOCV}{d\text{SOC}}\right|_{\hat{\text{SOC}}_{k|k-1}} & 1 & 1 \end{bmatrix}$$
$$\hat{x}_{k|k} = \hat{x}_{k|k-1} + \mathbf{K}_k (y_k - \hat{y}_k)$$

In our cyber-physical architecture, the SOC and SOH estimators are decoupled following the multi-timescale principles of **Li et al. [1] ([`paper_ekf_soc_soh.pdf`](paper_ekf_soc_soh.pdf))**. The state transition and measurement updates for SOC run at the microscale ($T_s = 1\text{ s}$), while cell capacity and aging resistance growth are updated at the macroscale using the SOH resistance observer and Recursive Least Squares (RLS).

### C. Reservoir Computing Estimator (Rigutini & Kamarudin Paradigm)
Guided by the reservoir topology, spectral radius bounds ($\rho < 1.0$), and fading memory characteristics analyzed by **Rigutini et al. [5]** and **Kamarudin et al. [2] ([`paper_rc_soc_soh.pdf`](paper_rc_soc_soh.pdf))**, the ESN utilizes a reservoir of $N_r$ leaky-integrator nodes. The recurrent reservoir states $x_t \in \mathbb{R}^{N_r}$ evolve as:
$$\tilde{x}_t = \tanh\left(\mathbf{W}_{\text{in}} [1; u_t] + \mathbf{W}_{\text{res}} x_{t-1}\right)$$
$$x_t = (1 - \alpha) x_{t-1} + \alpha \tilde{x}_t$$

The output weights $\mathbf{W}_{\text{out}}$ are trained offline using single-shot Ridge Regression ($L_2$ regularization $\lambda$):
$$\mathbf{W}_{\text{out}} = \mathbf{Y}_{\text{target}} \mathbf{X}^T \left(\mathbf{X} \mathbf{X}^T + \lambda \mathbf{I}\right)^{-1}$$

Mirroring the findings on data efficiency and temporal representation capability in [2], our non-spiking leaky-integrator reservoir mapping offers rich fading memory of input histories without backpropagation. For safety classification at the edge, the reservoir output is passed through a dense layer representing Normal, Warning, and Critical thermal safety states.

---

## III. Embedded Optimizations & Hardware Co-Design

To compile the reservoir mapping onto resource-constrained microcontrollers and FPGAs, three key optimizations are implemented:

### A. Compressed Sparse Row (CSR) SpMV
A dense recurrent matrix $\mathbf{W}_{\text{res}}$ of size $50 \times 50$ requires $2,500$ floating-point multiplies per update. We force $85\%$ sparsity during reservoir generation. To eliminate multiplications by zero, $\mathbf{W}_{\text{res}}$ is compressed into three 1D arrays:
- `esn_W_res_val` ($375$ non-zero elements)
- `esn_W_res_col` ($375$ column indices)
- `esn_W_res_row_ptr` ($51$ row start offsets)

This reduces reservoir computations to only $375$ multiplications, yielding a **6.7× speedup** in clock execution cycles and shrinking the memory footprint by approximately **10 KB of Flash storage**.

### B. Low-Power Fixed-Point Math (`ESN_FIXED_POINT 1`)
We implement a pure integer execution path for microcontrollers lacking hardware floating-point units:
1. **Quantization Scaling**: Inputs are quantized into Q12 format ($S = 4096$) and reservoir states and weights are stored in Q15 format ($S = 32768$).
2. **Fixed-Point Lookup Table**: The transcendental activation function ($\tanh$) is replaced with a high-speed 33-point lookup table combined with linear interpolation:
   $$\tanh(x_{\text{Q15}}) = \text{sign}(x_{\text{Q15}}) \cdot \frac{(1024 - \text{frac}) \cdot \text{LUT}[\text{index}] + \text{frac} \cdot \text{LUT}[\text{index} + 1]}{1024}$$
   Where $\text{frac} = |x_{\text{Q15}}| \pmod{1024}$ and $\text{index} = |x_{\text{Q15}}| \gg 10$.

### C. Plug-and-Play FPGA AXI4 IP Block (`esn_axi_ip`)
To provide modular hardware acceleration, the ESN reservoir datapath is packaged as a reusable AXI4-Lite control and AXI4-Stream data IP core (`component.xml` under IEEE 1685 IP-XACT). The IP core supports runtime weight reconfigurability for Win, W, bias, and readout weights, serving arbitrary battery chemistries without resynthesis. On an Arty A7-100T FPGA, the core executes a complete 100-neuron evaluation in 42,905 cycles ($536\ \mu\text{s}$ at 80 MHz) at only 0.124 W total power.

---

## IV. Experimental Results & Performance Analysis

The system was validated under simulated and empirical drive cycles, including the Urban Dynamometer Driving Schedule (UDDS), Highway Fuel Economy Test (HWFET), and high-dynamic US06 profiles, as well as 32 aging cycles from the NASA battery dataset.

### A. State Estimation Accuracy
The estimator pipeline yields high-fidelity tracking metrics. Table I summarizes the Root Mean Square Error (RMSE) values for the different estimators:

#### Table I: State Estimation RMSE Comparison Across Drive Cycles
| Drive Cycle Profile | EKF SOC RMSE | ESN SOC RMSE | Coulomb Counting SOC RMSE | SOH Observer RMSE |
| :--- | :---: | :---: | :---: | :---: |
| **UDDS** | 1.15% | 1.05% | 4.80% (Drifting) | 0.45% |
| **HWFET** | 1.30% | 1.12% | 5.20% (Drifting) | 0.52% |
| **US06** | 1.48% | 1.18% | 6.55% (Drifting) | 0.78% |

Compared to EKF, the ESN estimator shows superior robustness against sensor calibration errors and ambient temperature noise, as the reservoir states filter high-frequency disturbances.

### B. Embedded Performance and Optimization Footprint
The MCU execution metrics were verified on an ARM Cortex-M class microcontroller. Table II details the CPU execution time and memory footprints across the different execution modes:

#### Table II: Embedded Resource Utilization and Speedups (50-Node Reservoir)
| Model Mode / Representation | Inference Speed (μs) | CSR Speedup | Flash Footprint | RAM Footprint | Diagnostic Accuracy |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Dense Floating-Point** | 268 μs | 1.0× (Baseline) | ~22.0 KB | ~4.5 KB | 98.40% |
| **CSR Sparse Floating-Point** | 40 μs | 6.7× | ~12.2 KB | ~1.8 KB | 98.40% |
| **CSR Fixed-Point (Q12/Q15)** | 35 μs | 7.6× | ~11.5 KB | ~1.6 KB | 98.15% |

---

## V. Academic Dissemination & Journal Publication Plan

To translate our undergraduate capstone engineering innovations into the formal scientific record, our team has established a comprehensive **Two-Paper Journal Publication Roadmap**:

### A. Dual Publication Strategy
Our project bifurcates its academic contributions into two complementary, high-impact manuscripts:

1. **Target Paper 1: Original Experimental Research Paper** (This Manuscript):
   - **Focus:** Co-designed cyber-physical system, Compressed Sparse Row (CSR) ESN inference, 6.7× microcontroller execution speedup, Q15 fixed-point LUT math, and plug-and-play FPGA IP block.
   - **Primary Venues:** *IEEE Transactions on Industrial Electronics*, *IEEE Transactions on Transportation Electrification*, *IEEE Access*, or *IEEE Embedded Systems Letters*.
   - **Student Journal Track:** *IEEE Potentials* (flagship IEEE publication for student and young professionals) or the *VESIT Journal of Technology & Innovation*, providing an accessible avenue for capstone undergraduate dissemination.

2. **Target Paper 2: Comprehensive Literature Review & Survey Paper** ([`docs/Publications/Review_Paper.pdf`](../docs/Publications/Review_Paper.pdf)):
   - **Title:** *Neuromorphic Computing for Intelligent Battery Management Systems: A Comprehensive Review of Spiking Neural Networks, Reservoir Computing and Edge AI*
   - **Focus:** Extensive 29-page survey (11 sections, 90+ citations) tracing BMS estimation from Coulomb counting and Kalman filters (EKF, UKF) through deep learning (LSTM, Transformers) to neuromorphic hardware (Intel Loihi 2, BrainChip Akida, SpiNNaker2, and FPGA accelerators).
   - **Target Venues:** IEEE Transactions / Q3 Scopus-indexed review journal.

### B. Theoretical Linkage to Benchmarks
Our publications explicitly build upon and cite:
- **Li et al. [1] ([`paper_ekf_soc_soh.pdf`](paper_ekf_soc_soh.pdf))** as the analytical gold standard for multi-timescale EKF decoupled state observation.
- **Rigutini et al. [5]** and **Kamarudin et al. [2] ([`paper_rc_soc_soh.pdf`](paper_rc_soc_soh.pdf))** as the empirical justification for reservoir computing and spiking architectures in battery diagnostics.

### C. Evaluation Policy & Submission Tracking (20 Marks)
As part of our Bachelor of Engineering evaluation criteria at VESIT, 20 Marks are strictly allocated to peer-reviewed publication deliverables:
- **10 Marks:** Verified proof of manuscript submission (submission receipt and tracking Paper ID logged in [`docs/Paper_Proof/`](../docs/Paper_Proof/README.md)).
- **10 Marks:** Official peer-reviewed paper acceptance letter.

---

## VI. Conclusion & Future Outlook
We have presented an edge-optimized Echo State Network (ESN) reservoir computing framework as a data-driven alternative to traditional observers (EKF and Coulomb Counting). Benchmarking against the multi-timescale EKF formulation of Li et al. [1] and the reservoir computing principles of Rigutini et al. [5] and Kamarudin et al. [2], our system achieves sub-1.5% estimation errors without requiring tedious electrochemical parameter recalibration. Furthermore, compiling ESNs with CSR matrix compression and Q12/Q15 fixed-point LUT math delivers a 6.7× speedup on microcontrollers and enables bit-exact FPGA hardware acceleration via a plug-and-play IP block. Future work will expand our online RLS weight adaptation to multi-cell pack balance and finalize formal peer-reviewed journal archival.

---

## References
1. **Li, P., Wang, H., Xing, Z., Ye, K., & Li, Q.** (2020). *Joint estimation of SOC and SOH for lithium-ion batteries based on EKF multiple time scales*. Journal of Intelligent Manufacturing and Special Equipment, 1(1), 107-120. [PDF Document](paper_ekf_soc_soh.pdf)
2. **Kamarudin, M. R., Mispan, M. S., Zainudin, M. N. S., & Sofian, H.** (2026). *Reservoir Spiking Neural Networks for Accurate State-of-Charge Estimation in Battery Management Systems*. Turkish Journal of Engineering, 10(2), 407-417. [PDF Document](paper_rc_soc_soh.pdf)
3. **Plett, G. L.** (2004). *Extended Kalman filtering for battery management systems of LiPB-based HEV battery packs*. Journal of Power Sources, 134(2), 252-261.
4. **Jaeger, H.** (2001). *The "echo state" approach to analysing and training recurrent neural networks*. GMD Report 148, German National Research Center for Information Technology.
5. **Rigutini, L., et al.** (2020). *State-of-charge estimation of lithium-ion batteries using reservoir computing*. IEEE Transactions on Industrial Electronics.
