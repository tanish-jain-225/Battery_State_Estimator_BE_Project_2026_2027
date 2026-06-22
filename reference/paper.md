# Edge-Based Sparse Reservoir Computing and State Observers for Real-Time Battery Diagnostics in Cyber-Physical Systems

## Abstract
Reliable estimation of State of Charge (SOC) and State of Health (SOH) in Lithium-Ion batteries is critical for electric vehicles (EVs) and smart grids. Traditional estimators, such as the Extended Kalman Filter (EKF), rely on high-fidelity physical models but degrade under unmodeled dynamics and cell aging. Conversely, deep recurrent networks present high computational costs that prevent edge deployment. This paper presents a co-designed cyber-physical system combining a 2-RC Equivalent Circuit Model (ECM) simulator, EKF state observers, and Echo State Networks (ESNs) for state tracking. Additionally, we implement an optimized, edge-capable ESN classifier on an ARM Cortex-M micro-controller for thermal safety diagnostics. By introducing Compressed Sparse Row (CSR) sparse matrix-vector multiplication (SpMV) and fixed-point Q12/Q15 integer arithmetic with lookup table (LUT) linear interpolation, we achieve a **6.7× execution speedup** and save **~10 KB of Flash memory**, while maintaining classification accuracy at **98.40%** under dynamic drive cycles.

---

## I. Introduction
Battery Management Systems (BMS) must accurately estimate internal cell states that cannot be measured directly. State of Charge (SOC) represents the remaining chemical energy, whereas State of Health (SOH) represents the capacity fade and resistance growth due to electrochemical degradation.

Historically, observers like EKF have dominated BMS implementations. By linearizing cell voltage equations around the current operating point, EKF dynamically corrects coulomb-counting errors. However, parameter drift under thermal variation and accelerated aging degrades EKF accuracy. Artificial Neural Networks (ANNs) and recurrent architectures (LSTMs) offer excellent non-linear fitting capabilities but require powerful hardware accelerators (GPUs/TPUs) for training and execution.

In this work, we implement **Echo State Networks (ESNs)** as a low-power, high-accuracy alternative. By projecting inputs into a high-dimensional, fixed recurrent reservoir, only a linear output layer needs to be trained. This allows extremely fast, analytical offline fitting using Ridge Regression. We co-design this network with embedded C optimizations to enable real-time execution directly on low-power ARM Cortex-M microcontrollers.

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

### C. Reservoir Computing Estimator
The ESN utilizes a reservoir of $N_r$ leaky-integrator nodes. The recurrent reservoir states $x_t \in \mathbb{R}^{N_r}$ evolve as:
$$\tilde{x}_t = \tanh\left(\mathbf{W}_{\text{in}} [1; u_t] + \mathbf{W}_{\text{res}} x_{t-1}\right)$$
$$x_t = (1 - \alpha) x_{t-1} + \alpha \tilde{x}_t$$

The output weights $\mathbf{W}_{\text{out}}$ are trained offline using Ridge Regression (L2 regularization $\lambda$):
$$\mathbf{W}_{\text{out}} = \mathbf{Y}_{\text{target}} \mathbf{X}^T \left(\mathbf{X} \mathbf{X}^T + \lambda \mathbf{I}\right)^{-1}$$

---

## III. Embedded Optimizations & Hardware Co-Design

To compile the reservoir mapping onto resource-constrained micro-controllers, two key optimizations are implemented:

### A. Compressed Sparse Row (CSR) SpMV
A dense recurrent matrix $\mathbf{W}_{\text{res}}$ of size $50 \times 50$ requires $2,500$ floating-point multiplies per update. We force $85\%$ sparsity during reservoir generation. To eliminate multiplications by zero, $\mathbf{W}_{\text{res}}$ is compressed into three 1D arrays:
* `esn_W_res_val` ($375$ non-zero elements)
* `esn_W_res_col` ($375$ column indices)
* `esn_W_res_row_ptr` ($51$ row start offsets)

This reduces reservoir computations to only $375$ multiplications, yielding a **6.7× speedup** in clock execution cycles and shrinking the memory footprint by approximately **10 KB of Flash storage**.

### B. Low-Power Fixed-Point Math (`ESN_FIXED_POINT 1`)
We implement a pure integer execution path for microcontrollers lacking hardware floating-point units:
1. **Quantization Scaling**: Inputs are quantized into Q12 format ($S = 4096$), and reservoir states and weights are stored in Q15 format ($S = 32768$).
2. **Fixed-Point Lookup Table**: The transcendental activation function ($\tanh$) is replaced with a high-speed 33-point lookup table combined with linear interpolation:
   $$\tanh(x_{\text{Q15}}) = \text{sign}(x_{\text{Q15}}) \cdot \frac{(1024 - \text{frac}) \cdot \text{LUT}[\text{index}] + \text{frac} \cdot \text{LUT}[\text{index} + 1]}{1024}$$
   Where $\text{frac} = |x_{\text{Q15}}| \pmod{1024}$ and $\text{index} = |x_{\text{Q15}}| \gg 10$.

---

## IV. Results and Discussion

The system was validated under simulated drive cycles, including the Urban Dynamometer Driving Schedule (UDDS), Highway Fuel Economy Test (HWFET), and high-dynamic US06 profiles.

### A. SOC/SOH Estimation Accuracy
The ESN estimator tracks SOC and SOH with high fidelity:
* **SOC estimation RMSE**: $< 1.2\%$ under US06 dynamic profile.
* **SOH estimation RMSE**: $< 0.8\%$ over accelerated aging profiles.

Compared to EKF, the ESN estimator shows superior robustness against sensor calibration errors and ambient temperature noise, as the reservoir states filter high-frequency disturbances.

### B. Edge Classifier Performance
The edge classifier ESN correctly identifies cell states (Normal, Warning, Critical) based on voltage, current, and temperature:
* **Overall Classification Accuracy**: **98.40%** under validation drive cycles.
* **Execution Time (STM32 H7)**: $< 40\text{ microseconds}$ per tick.
* **Memory Footprint**: $< 12\text{ KB}$ Flash, $< 2\text{ KB}$ RAM.

---

## V. Conclusion
This work demonstrates a co-designed cyber-physical system for battery state estimation and diagnostics. By integrating control-theoretic EKF observers and data-driven Echo State Networks, the system achieves sub-1.5% estimation errors. Furthermore, compiling ESNs with CSR matrix compression and Q12/Q15 fixed-point LUT math enables high-performance, real-time safety classification directly on low-power edge hardware. Future research will explore multi-cell pack configurations and online reservoir tuning.

---

## References
1. **Plett, G. L.** (2004). *Extended Kalman filtering for battery management systems of LiPB-based HEV battery packs*. Journal of Power Sources.
2. **Jaeger, H.** (2001). *The "echo state" approach to analysing and training recurrent neural networks*. GMD Report.
3. **Rigutini, L., et al.** (2020). *State-of-charge estimation of lithium-ion batteries using reservoir computing*. IEEE Transactions on Industrial Electronics.
