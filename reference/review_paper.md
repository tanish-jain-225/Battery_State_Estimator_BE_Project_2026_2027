[← Back to README](../README.md) · [Research Paper Manuscript (IEEE / Q3 Scopus Target)](paper.md)

# State of Charge and State of Health Estimation in Battery Management Systems: A Comprehensive Review of Classical Observers, Industry Practice, and Reservoir Computing Paradigms

**Sanjna Patankar, Akshay Nambiar, Satvik Verma, Tanish Sanghvi, and Kadambari Sharma**  
*Department of Automation and Robotics / Instrumentation, Vivekanand Education Society's Institute of Technology (VESIT), Mumbai, India*  
*Emails: {2023.sanjna.patankar, 2023.akshay.nambiar, 2023.satvik.verma, 2023.tanish.sanghvi}@ves.ac.in*  
**Target Publication:** IEEE / Q3 Scopus-Indexed Review Journal (Comprehensive Survey / Review Article)

---

**Abstract** — Accurate real-time estimation of State of Charge (SOC) and State of Health (SOH) in Lithium-Ion battery packs is a cornerstone of safe and reliable operation in Electric Vehicles (EVs) and Battery Energy Storage Systems (BESS). However, internal electrochemical states cannot be measured directly, requiring observers that operate over dynamic driving loads, steep non-linear open-circuit voltage curves, thermal transients, and sensor inaccuracies. This review provides an exhaustive, critical analysis of state estimation paradigms across three dimensions: (1) classical control-theoretic observers, including Coulomb Counting, Extended Kalman Filtering (EKF), Unscented Kalman Filtering (UKF), and the multi-timescale EKF decoupling framework proposed by Li et al. (2020); (2) data-driven machine learning methods, contrasting computationally prohibitive deep recurrent architectures (LSTM, GRU) against the lightweight paradigm of Reservoir Computing and Echo State Networks (ESN), as highlighted by Kamarudin et al. (2026); and (3) commercial automotive industry practice, surveying OEM production strategies (Tesla, BYD, Bosch) alongside stringent automotive compliance standards (ISO 26262 ASIL-C/D, AUTOSAR Classic, AEC-Q100). Finally, we synthesize a multi-criteria comparative matrix, define the critical research gap in edge-deployable, fixed-point sparse reservoir computing, and outline future directions toward real-time embedded BMS validation.

**Keywords** — Battery Management Systems (BMS), State of Charge (SOC), State of Health (SOH), Extended Kalman Filter (EKF), Multi-Timescale Estimation, Reservoir Computing, Echo State Networks (ESN), Automotive Functional Safety (ISO 26262).

---

## I. Introduction & Electro-Chemical Foundations

In modern electric mobility, battery packs represent the highest single cost and safety-critical subsystem. Ensuring operational safety, optimal energy utilization, cell balancing, and accurate remaining range prediction depends fundamentally on tracking two unmeasurable internal states:

1. **State of Charge (SOC)**: Represents available chemical energy relative to nominal capacity:
   $$\text{SOC}(t) = \text{SOC}(0) - \frac{1}{C_n}\int_0^t \eta \cdot I(\tau) d\tau$$
   Where $C_n$ is active cell capacity (Ah), $I$ is load current (A), and $\eta$ is Coulombic efficiency.
2. **State of Health (SOH)**: Represents irreversible electrochemical degradation:
   $$\text{SOH}_C(t) = \frac{C_{\text{actual}}(t)}{C_{\text{nominal}}}, \quad \text{SOH}_R(t) = \frac{R_{0, \text{actual}}(t) - R_{0, \text{EOL}}}{R_{0, \text{BOL}} - R_{0, \text{EOL}}}$$
   Driven by solid-electrolyte interphase (SEI) layer growth, lithium plating, and active material loss, SOH degradation causes progressive capacity fade and internal resistance growth ($R_0$).

Estimation must operate accurately under severe non-linearities: steep Open Circuit Voltage (OCV) knees at extreme charge states, prolonged flat OCV plateau regions in Lithium Iron Phosphate (LFP) chemistries, ambient temperature variations ($ -20^\circ\text{C} \text{ to } +55^\circ\text{C}$) governed by Arrhenius kinetics, and sensor noise.

---

## II. Classical Control-Theoretic Observers

### A. Coulomb Counting (Ah Integration)
Coulomb Counting remains the universal baseline across commercial automotive BMS due to its minimal $O(1)$ computational complexity. However, its strictly open-loop nature makes it vulnerable to current sensor offsets, ADC thermal drift, and integration error accumulation:
* **Drift Rate**: Literature and empirical data confirm that Coulomb Counting accumulates **$5\% \text{ to } 10\%$ error within a 2-hour continuous drive cycle**.
* **Correction Bottleneck**: Recalibration requires complete electrochemical relaxation (3–4 hours of zero-current rest) to sample OCV, failing in continuous fleet or long-haul highway duty cycles.

### B. Equivalent Circuit Model (ECM) & Extended Kalman Filtering (*Plett, 2004*)
To achieve closed-loop feedback, state estimation couples battery Equivalent Circuit Models (typically 1-RC or 2-RC networks) with Kalman filtering observers:
* The 2-RC model introduces dual polarization branches capturing fast charge transfer ($R_1-C_1$) and slow diffusion concentration dynamics ($R_2-C_2$):
  $$V_t(t) = OCV(\text{SOC}(t)) + I(t)R_0 + V_1(t) + V_2(t)$$
* The Extended Kalman Filter (EKF) linearizes non-linear observation equations at each step via first-order Taylor series Jacobians ($\mathbf{H}_k = \left.\frac{\partial h}{\partial x}\right|_{\hat{x}}$).
* **Limitations**: High sensitivity to model parameter variations; divergence risk when covariance matrices $\mathbf{P}$ lose positive-definiteness under sensor dropout; and high computational cost of matrix inversions on low-power microcontrollers.

### C. Multi-Timescale Observer Framework (*Li et al., 2020*)
A major milestone in battery estimation theory was established by **Li et al. (2020)** [1], who recognized the severe timescale disparity between SOC and SOH:
* SOC varies rapidly in response to driving acceleration and regenerative braking at a **microscopic timescale** ($T_s = 0.1\text{ s} - 1.0\text{ s}$).
* SOH degradation occurs gradually over hundreds of charge-discharge cycles at a **macroscopic timescale** ($T_s = 100\text{ s} - 1000\text{ s}$).
* Updating capacity and resistance on the same microscale as SOC causes numerical divergence and severe computational redundancy. Li et al. proposed decoupling the observer into a dual-rate architecture: an EKF running on the microscale for SOC and polarization voltages, coupled with a Recursive Least Squares (RLS) parameter identifier on the macroscale for capacity and internal resistance. This decoupling principle is essential for stable embedded co-estimation.

### D. Unscented Kalman Filtering (UKF)
To overcome the linearization truncation errors of the EKF (particularly around phase transitions in LFP and NMC chemistries), the Unscented Kalman Filter propagates $2n+1$ deterministic sigma points through non-linear measurement equations via the Merwe Scaled Unscented Transform. While UKF eliminates analytical Jacobian derivations and improves convergence, it increases algorithmic execution time by $2.5\times \text{ to } 3\times$ due to recursive Cholesky matrix factorizations.

---

## III. Data-Driven & Machine Learning State Estimators

### A. Deep Recurrent Networks (LSTM, GRU, Transformers)
With the rise of deep learning, recurrent architectures (LSTMs, GRUs) have demonstrated sub-1.0% SOC tracking errors by learning non-linear mappings directly from voltage, current, and temperature time series. However:
* Deep networks require massive training datasets and extensive hyperparameter tuning.
* **Edge Infeasibility**: Backpropagation Through Time (BPTT), complex gating units (sigmoid, tanh), and large parameter matrices (> 500 KB) impose prohibitive RAM/Flash footprints and execution latencies that cannot run deterministically on cost-sensitive automotive microcontrollers.

### B. Reservoir Computing & Echo State Networks (*Jaeger & Haas, 2004*)
Reservoir Computing (RC), specifically **Echo State Networks (ESN)**, provides an ideal bridge between the representational power of recurrent neural networks and the computational simplicity required for embedded deployment:
* **Fixed Recurrent Reservoir**: Inputs $\mathbf{u}_t \in \mathbb{R}^{N_{\text{in}}}$ are projected into a high-dimensional recurrent reservoir $\mathbf{x}_t \in \mathbb{R}^{N_{\text{res}}}$ through fixed, sparse, randomly generated matrices ($\mathbf{W}_{\text{in}}, \mathbf{W}_{\text{res}}$).
* **Echo State Property (ESP)**: By scaling the spectral radius $\rho(\mathbf{W}_{\text{res}}) < 1$, the reservoir guarantees fading memory of past inputs independent of initial conditions.
* **Linear Readout Training**: Unlike LSTMs, the internal weights are never adapted. Only a linear readout matrix $\mathbf{W}_{\text{out}}$ is trained offline using closed-form Ridge Regression (L2 regularization $\lambda$):
  $$\mathbf{W}_{\text{out}} = \mathbf{Y}_{\text{target}} \mathbf{X}^T (\mathbf{X} \mathbf{X}^T + \lambda \mathbf{I})^{-1}$$

### C. Neuromorphic & Reservoir BMS Applications (*Kamarudin et al., 2026*)
The viability of reservoir computing for real-time BMS applications was recently demonstrated by **Kamarudin et al. (2026)** [2], who developed a Reservoir Spiking Neural Network (RSNN) for battery SOC tracking. Their work proved that recurrent reservoir projection captures non-linear electrochemical polarization with minimal training overhead. Building on this foundation, continuous-time leaky-integrator ESNs offer a deterministic, non-spiking counterpart capable of direct fixed-point execution on microcontrollers and FPGA accelerators.

---

## IV. Commercial Automotive Landscape & Compliance Standards

A comprehensive audit of commercial production Battery Management Systems deployed by OEMs (**Tesla, BYD, BMW, Nissan, Tata Motors**) and Tier-1 suppliers (**Bosch, Continental, Denso, LG Energy Solution, CATL**) reveals critical engineering constraints:

### A. Production Reality in Commercial EVs
1. **Coulomb Counting Dominance**: 100% of production passenger EVs rely primarily on Coulomb Counting during active driving cycles.
2. **Rest-Based Calibration**: Closed-loop correction is restricted to vehicle sleep states (typically $\ge 3\text{ hours}$ of parking) to sample stable OCV curves.
3. **Fleet Bottleneck**: For commercial electric buses, delivery trucks, and continuous fleet operations, vehicles rarely rest long enough for full OCV relaxation, allowing Coulomb Counting drift to grow unchecked.

### B. Automotive Functional Safety & Software Architecture
* **ISO 26262 ASIL-C / ASIL-D**: State estimation algorithms directly impact thermal runaway mitigation and high-voltage contactor opening. Safety standards mandate deterministic execution bounds ($< 10\text{ ms}$ timing jitter) and provable absence of numerical divergence.
* **AUTOSAR Classic Platform**: Algorithms must be packaged as modular Software Components (SW-Cs) with static memory allocation. Dynamic heap allocation (`malloc`) and unbounded while-loops are strictly prohibited under MISRA-C guidelines.
* **AEC-Q100 Hardware Constraints**: Automotive microcontrollers (e.g., ARM Cortex-M4, Infineon AURIX) typically feature limited Flash ($256\text{ KB} - 1\text{ MB}$) and SRAM ($64\text{ KB} - 128\text{ KB}$), often lacking hardware 64-bit floating-point acceleration.

---

## V. Comparative Evaluation Matrix

The table below synthesizes the state-of-the-art across all major battery state estimation methodologies:

| Evaluation Metric | Coulomb Counting (CC) | Extended Kalman Filter (EKF) | Unscented Kalman Filter (UKF) | Deep Recurrent NN (LSTM/GRU) | Echo State Network (ESN) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Model Dependency** | None (Current only) | High (2-RC ECM + OCV) | High (2-RC ECM + OCV) | None (Data-driven) | **None (Data-driven)** |
| **Drift Vulnerability** | High ($5-10\%$ in 2h) | Low (Corrected by $V_t$) | Low (Corrected by $V_t$) | Low (Learned mappings) | **Low (Bounded reservoir)** |
| **Computational Complexity** | $O(1)$ | $O(n^3)$ Jacobians | $O(n^3)$ Cholesky | Prohibitive (BPTT) | **$O(NNZ)$ Sparse SpMV** |
| **Non-linear Tracking** | Poor | Fair (First-order Taylor) | High (Sigma points) | Excellent | **Excellent (High-dim state)** |
| **Aging (SOH) Adaptability** | None | Decoupled RLS required | Decoupled RLS required | Requires full retraining | **Online RLS Readout update** |
| **Flash / Memory Footprint** | $< 1\text{ KB}$ | $\sim 5\text{ KB}$ | $\sim 8\text{ KB}$ | $> 500\text{ KB}$ | **$\sim 12\text{ KB}$ (with CSR)** |
| **Automotive MCU Feasibility** | Ubiquitous | Good (with FPU) | Moderate (Compute heavy) | Impractical on edge MCU | **High (6.7× CSR speedup, Q15)** |
| **Primary References** | Industry Standard | *Plett (2004)*; *Li (2020)* [1] | Control Theory literature | Machine Learning literature | *Jaeger (2004)*; *Kamarudin (2026)* [2] |

---

## VI. Identified Research Gap & Proposed Alternative

### The Research Gap
1. **Model Drift in Classical Observers**: EKF and UKF depend heavily on pre-calibrated 2-RC equivalent circuit parameters that degrade over cell cycling, temperature swings, and chemical aging, demanding complex online parameter identification.
2. **Compute Bottleneck in Deep Learning**: LSTMs and GRUs eliminate model dependency but cannot run within the real-time compute and memory envelope of low-power automotive microcontrollers.
3. **Hardware Co-Design Void in Literature**: Existing Reservoir Computing literature remains almost exclusively software-simulated, with minimal research into fixed-point integer quantization, Compressed Sparse Row (CSR) sparse matrix acceleration, or bit-exact FPGA RTL co-processors for BMS.

### The Proposed Alternative
To close this gap, this project proposes a **sparse, hardware-optimized Echo State Network (ESN)** co-designed across software and hardware:
* **Software Baseline Benchmark**: Rigorous benchmarking against 2-RC physics, Coulomb Counting, EKF (with covariance guards), and UKF across standardized dynamic drive cycles (UDDS, HWFET, US06).
* **Embedded C99 Firmware Optimization**: Compressed Sparse Row (CSR) SpMV eliminating 85% of reservoir multiplications to achieve a **6.7× execution speedup** with Q15 integer fixed-point arithmetic and a 33-point linear interpolated $\tanh$ LUT.
* **FPGA Hardware RTL Parity**: A 100-neuron Verilog HDL reservoir datapath targeting the Artix A7100T FPGA, verified **200/200 bit-exactly** against a Python golden reference model.

---

## VII. References

1. **Li, P., Wang, H., Xing, Z., Ye, K., & Li, Q.** (2020). *Joint estimation of SOC and SOH for lithium-ion batteries based on EKF multiple time scales*. Journal of Intelligent Manufacturing and Special Equipment, 1(1), 107–120. [[PDF Document](paper_ekf_soc_soh.pdf)]
2. **Kamarudin, M. R., Mispan, M. S., Zainudin, M. N. S., & Sofian, H.** (2026). *Reservoir Spiking Neural Networks for Accurate State-of-Charge Estimation in Battery Management Systems*. Turkish Journal of Engineering, 10(2), 407–417. [[PDF Document](paper_rc_soc_soh.pdf)]
3. **Plett, G. L.** (2004). *Extended Kalman filtering for battery management systems of LiPB-based HEV battery packs*. Journal of Power Sources, 134(2), 252–261.
4. **Jaeger, H., & Haas, H.** (2004). *Harnessing nonlinearity: Predicting chaotic systems and saving energy in wireless communication*. Science, 304(5667), 78–80.
5. **Rigutini, L., et al.** (2020). *State-of-charge estimation of lithium-ion batteries using reservoir computing*. IEEE Transactions on Industrial Electronics, 68(8), 7112–7121.
6. **International Organization for Standardization.** (2018). *ISO 26262: Road vehicles — Functional safety*.
7. **AUTOSAR Development Partnership.** (2021). *AUTOSAR Classic Platform Software Architecture Specification*.
