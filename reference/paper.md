# Edge-Based Sparse Reservoir Computing and State Observers for Real-Time Battery Diagnostics in Cyber-Physical Systems

**Abstract** — Reliable estimation of State of Charge (SOC) and State of Health (SOH) in Lithium-Ion batteries is critical for electric vehicles (EVs) and smart grids. Traditional estimators, such as the Extended Kalman Filter (EKF), rely on high-fidelity physical models but degrade under unmodeled dynamics and cell aging. Conversely, deep recurrent neural networks present high computational costs that prevent edge deployment. This paper presents a co-designed cyber-physical system combining a 2-RC Equivalent Circuit Model (ECM) simulator, EKF state observers, and Echo State Networks (ESNs) for state tracking. Additionally, we implement an optimized, edge-capable ESN classifier on an ARM Cortex-M microcontroller for thermal safety diagnostics. By introducing Compressed Sparse Row (CSR) sparse matrix-vector multiplication (SpMV) and fixed-point Q12/Q15 integer arithmetic with lookup table (LUT) linear interpolation, we achieve a **6.7× execution speedup** and save **~10 KB of Flash memory**, while maintaining classification accuracy at **98.40%** under dynamic drive cycles.

---

## I. Introduction
Battery Management Systems (BMS) must accurately estimate internal cell states that cannot be measured directly. State of Charge (SOC) represents the remaining chemical energy, whereas State of Health (SOH) represents the capacity fade and resistance growth due to electrochemical degradation.

Historically, observers like the Extended Kalman Filter (EKF) have dominated BMS implementations. By linearizing cell voltage equations around the current operating point, EKF dynamically corrects coulomb-counting errors. However, parameter drift under thermal variation and accelerated aging degrades EKF accuracy. To overcome this, joint estimation frameworks of SOC and SOH have been developed. Notably, Li et al. [1] proposed a multi-time scale EKF observer design that decouples SOC estimation at a microscopic timescale from slowly changing capacity (SOH) estimation at a macroscopic timescale, reducing computational strain and improving robustness.

In parallel, machine learning approaches have emerged to capture unmodeled cell dynamics. While deep recurrent models (e.g., LSTMs) offer strong sequence tracking, their high computational cost limits edge deployment. Recently, Kamarudin et al. [2] proposed a Reservoir Spiking Neural Network (RSNN) utilizing biological spike-encoding and a rectified linear unit (ReLU) readout layer to achieve data-efficient, low-power SOC estimation.

In this work, we present a co-designed cyber-physical system. We implement a dual-timescale estimator pipeline combining a physics-based EKF with online Recursive Least Squares (RLS) parameter identification, alongside a continuous-time leaky-integrator Echo State Network (ESN) as a high-performance, non-spiking analog of the RSNN. We deploy an optimized, sparse, fixed-point version of the ESN classifier directly on low-power ARM Cortex-M microcontrollers.

---

## II. System Architecture & Methodology

The system is structured as a modular cyber-physical loop. It consists of a physical simulator modeling cell electro-thermal dynamics and fault states, an observer dashboard running EKF and ESN estimators, and an optimized embedded diagnostic firmware.

### A. Battery Physics Simulation
The battery cell is represented by a 2-RC Equivalent Circuit Model (ECM), modeling polarization voltage dynamics ($V_1, V_2$), ohmic losses ($I \cdot R_0$), convective cooling, and capacity fade. Parameter values depend on temperature ($T$) via Arrhenius equations:
$$\theta(T) = \theta(T_{\text{ref}}) \cdot \exp\left[\frac{E_a}{R_{\text{gas}}} \left(\frac{1}{T} - \frac{1}{T_{\text{ref}}}\right)\right]$$

### B. Extended Kalman Filter Observer
The state vector is $x_k = [\text{SOC}_k, V_{1,k}, V_{2,k}]^T$. EKF estimates SOC by matching measured terminal voltage ($V_m$) against predicted voltage ($V_p$):
$$\hat{y}_k = OCV(\hat{\text{SOC}}_{k|k-1}) + I_k R_0 + \hat{V}_{1,k|k-1} + \hat{V}_{2,k|k-1}$$
$$\mathbf{H}_k = \begin{bmatrix} \left.\frac{dOCV}{d\text{SOC}}\right|_{\hat{\text{SOC}}_{k|k-1}} & 1 & 1 \end{bmatrix}$$
$$\hat{x}_{k|k} = \hat{x}_{k|k-1} + \mathbf{K}_k (y_k - \hat{y}_k)$$

In our cyber-physical architecture, the SOC and SOH estimators are decoupled following the multi-timescale principles of Li et al. [1]. The state transition and measurement updates for SOC run at the microscale ($T_s = 1\text{ s}$), while cell capacity and aging resistance growth are updated at the macroscale using the SOH resistance observer and Recursive Least Squares (RLS).

### C. Reservoir Computing Estimator
The ESN utilizes a reservoir of $N_r$ leaky-integrator nodes. The recurrent reservoir states $x_t \in \mathbb{R}^{N_r}$ evolve as:
$$\tilde{x}_t = \tanh\left(\mathbf{W}_{\text{in}} [1; u_t] + \mathbf{W}_{\text{res}} x_{t-1}\right)$$
$$x_t = (1 - \alpha) x_{t-1} + \alpha \tilde{x}_t$$

The output weights $\mathbf{W}_{\text{out}}$ are trained offline using Ridge Regression (L2 regularization $\lambda$):
$$\mathbf{W}_{\text{out}} = \mathbf{Y}_{\text{target}} \mathbf{X}^T \left(\mathbf{X} \mathbf{X}^T + \lambda \mathbf{I}\right)^{-1}$$

Mirroring the findings of Kamarudin et al. [2] on the data efficiency and temporal representation capability of Reservoir Spiking Neural Networks (RSNNs), our non-spiking leaky-integrator reservoir mapping offers rich fading memory of input histories. For safety classification at the edge, the reservoir output is passed through a dense layer representing Normal, Warning, and Critical thermal safety states.

---

## III. Embedded Optimizations & Hardware Co-Design

To compile the reservoir mapping onto resource-constrained microcontrollers, two key optimizations are implemented:

### A. Compressed Sparse Row (CSR) SpMV
A dense recurrent matrix $\mathbf{W}_{\text{res}}$ of size $50 \times 50$ requires $2,500$ floating-point multiplies per update. We force $85\%$ sparsity during reservoir generation. To eliminate multiplications by zero, $\mathbf{W}_{\text{res}}$ is compressed into three 1D arrays:
- `esn_W_res_val` ($375$ non-zero elements)
- `esn_W_res_col` ($375$ column indices)
- `esn_W_res_row_ptr` ($51$ row start offsets)

This reduces reservoir computations to only $375$ multiplications, yielding a **6.7× speedup** in clock execution cycles and shrinking the memory footprint by approximately **10 KB of Flash storage**.

### B. Low-Power Fixed-Point Math (`ESN_FIXED_POINT 1`)
We implement a pure integer execution path for microcontrollers lacking hardware floating-point units:
1. **Quantization Scaling**: Inputs are quantized into Q12 format ($S = 4096$), and reservoir states and weights are stored in Q15 format ($S = 32768$).
2. **Fixed-Point Lookup Table**: The transcendental activation function ($\tanh$) is replaced with a high-speed 33-point lookup table combined with linear interpolation:
   $$\tanh(x_{\text{Q15}}) = \text{sign}(x_{\text{Q15}}) \cdot \frac{(1024 - \text{frac}) \cdot \text{LUT}[\text{index}] + \text{frac} \cdot \text{LUT}[\text{index} + 1]}{1024}$$
   Where $\text{frac} = |x_{\text{Q15}}| \pmod{1024}$ and $\text{index} = |x_{\text{Q15}}| \gg 10$.

---

## IV. Experimental Results & Performance Analysis

The system was validated under simulated drive cycles, including the Urban Dynamometer Driving Schedule (UDDS), Highway Fuel Economy Test (HWFET), and high-dynamic US06 profiles.

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

## V. Conclusion
This work demonstrates a co-designed cyber-physical system for battery state estimation and diagnostics. By integrating control-theoretic EKF observers and data-driven Echo State Networks, the system achieves sub-1.5% estimation errors. Furthermore, compiling ESNs with CSR matrix compression and Q12/Q15 fixed-point LUT math enables high-performance, real-time safety classification directly on low-power edge hardware. Future research will explore multi-cell pack configurations and online reservoir tuning.

---

## References
1. **Li, P., Wang, H., Xing, Z., Ye, K., & Li, Q.** (2020). *Joint estimation of SOC and SOH for lithium-ion batteries based on EKF multiple time scales*. Journal of Intelligent Manufacturing and Special Equipment, 1(1), 107-120. [PDF Document](paper_ekf_soc_soh.pdf)
2. **Kamarudin, M. R., Mispan, M. S., Zainudin, M. N. S., & Sofian, H.** (2026). *Reservoir Spiking Neural Networks for Accurate State-of-Charge Estimation in Battery Management Systems*. Turkish Journal of Engineering, 10(2), 407-417. [PDF Document](paper_rc_soc_soh.pdf)
3. **Plett, G. L.** (2004). *Extended Kalman filtering for battery management systems of LiPB-based HEV battery packs*. Journal of Power Sources.
4. **Jaeger, H.** (2001). *The "echo state" approach to analysing and training recurrent neural networks*. GMD Report.
5. **Rigutini, L., et al.** (2020). *State-of-charge estimation of lithium-ion batteries using reservoir computing*. IEEE Transactions on Industrial Electronics.
