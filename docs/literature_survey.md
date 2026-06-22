# Theoretical Foundations of Cyber-Physical Battery State Estimation

This document provides a comprehensive theoretical review of the electro-chemical, control-theoretic, and machine learning methods implemented in the cyber-physical battery state estimator system. 

---

## 1. Electro-Thermal Battery Physics & Modeling (2-RC ECM)

To predict battery behavior in real-time, the system leverages a **2-RC Equivalent Circuit Model (ECM)**. This model balances computational simplicity with the dynamic representation of polarization losses and charge transfer dynamics.

### Equivalent Circuit Representation
The circuit consists of:
* An open-circuit voltage source ($V_{\text{oc}}$ or $OCV$) as a function of the State of Charge (SOC).
* An ohmic internal resistance ($R_0$) representing electrolyte and contact resistances.
* Two parallel Resistor-Capacitor (RC) branches representing short-term charge transfer ($R_1, C_1$) and long-term diffusion dynamics ($R_2, C_2$).

```
           ┌───[ R1 ]───┐      ┌───[ R2 ]───┐
     ┌─────┤            ├──────┤            ├─────[ R0 ]──────┐ (+)
     │     └───[ C1 ]───┘      └───[ C2 ]───┘                 │
     │                                                        │
   [ OCV ] (f(SOC))                                       Terminal
     │                                                     Voltage
     │                                                       (Vt)
     └────────────────────────────────────────────────────────┘ (-)
```

### Governing Equations
The electrical state of the cell at tick $t$ is governed by the following state space equations:

1. **State of Charge (SOC)** update via Coulomb Counting:
   $$\frac{d\text{SOC}(t)}{dt} = \frac{I(t)}{C_n \cdot 3600}$$
   * $I(t)$ is the current in Amperes (positive for charging, negative for discharging).
   * $C_n$ is the active cell capacity in Ampere-hours (Ah).
   
2. **Polarization Voltage Branches**:
   $$\frac{dV_1(t)}{dt} = \frac{I(t)}{C_1} - \frac{V_1(t)}{R_1 C_1}$$
   $$\frac{dV_2(t)}{dt} = \frac{I(t)}{C_2} - \frac{V_2(t)}{R_2 C_2}$$
   * $V_1$ and $V_2$ represent the polarization voltage drops across the respective RC branches.

3. **Terminal Voltage Equation**:
   $$V_t(t) = OCV(\text{SOC}(t)) + I(t)R_0 + V_1(t) + V_2(t)$$

### Thermal Coupling & Arrhenius Temperature Dependence
The internal resistances ($R_0, R_1, R_2$) and capacitances ($C_1, C_2$) vary dynamically with cell temperature ($T$) governed by the **Arrhenius relation**:
$$\theta(T) = \theta(T_{\text{ref}}) \cdot \exp\left[\frac{E_a}{R_{\text{gas}}} \left(\frac{1}{T} - \frac{1}{T_{\text{ref}}}\right)\right]$$
* $\theta$ represents the resistance or capacitance parameter.
* $E_a$ is the activation energy (set to $1500\text{ J/mol}$).
* $R_{\text{gas}}$ is the universal gas constant.
* $T$ and $T_{\text{ref}}$ are in Kelvin.

### Capacity Fade & Aging Dynamics
State of Health (SOH) capacity fade and internal resistance growth are coupled to temperature transients and current amplitude:
$$\Delta\text{SOH} = -k_{\text{aging}} \cdot |I|^{1.3} \cdot \exp\left[0.06 \cdot (T - 25.0)\right] \cdot \Delta t$$
$$R_0(t) = R_{0, \text{nom}} \cdot \left[1.0 + 1.5 \cdot (1.0 - \text{SOH}(t))\right]$$

---

## 2. State Estimation via Extended Kalman Filtering (EKF)

The Extended Kalman Filter (EKF) serves as the control-theoretic observer to filter sensor noise and track internal battery states.

### State Space Formulation
The discrete-time state vector is defined as $x_k = [\text{SOC}_k, V_{1,k}, V_{2,k}]^T$. The discrete state transition function $f(x_k, u_k)$ updates the states:
$$x_{k+1} = \mathbf{F}_k x_k + \mathbf{B}_k u_k + w_k$$
$$y_k = h(x_k, u_k) + v_k$$
* $u_k = I_k$ is the current input.
* $w_k \sim \mathcal{N}(0, \mathbf{Q})$ represents process noise.
* $v_k \sim \mathcal{N}(0, R)$ represents measurement noise.

The discrete state transition matrices are computed using zero-order hold discretization:
$$\mathbf{F}_k = \begin{bmatrix} 1 & 0 & 0 \\ 0 & \exp\left(-\frac{\Delta t}{R_1 C_1}\right) & 0 \\ 0 & 0 & \exp\left(-\frac{\Delta t}{R_2 C_2}\right) \end{bmatrix}$$
$$\mathbf{B}_k = \begin{bmatrix} \frac{\Delta t}{C_n \cdot 3600} \\ R_1 \left[1 - \exp\left(-\frac{\Delta t}{R_1 C_1}\right)\right] \\ R_2 \left[1 - \exp\left(-\frac{\Delta t}{R_2 C_2}\right)\right] \end{bmatrix}$$

### EKF Execution Steps
At each simulation tick $k$, the EKF executes prediction and correction stages:

1. **Prediction Stage**:
   $$\hat{x}_{k|k-1} = \mathbf{F}_{k-1} \hat{x}_{k-1|k-1} + \mathbf{B}_{k-1} u_{k-1}$$
   $$\mathbf{P}_{k|k-1} = \mathbf{F}_{k-1} \mathbf{P}_{k-1|k-1} \mathbf{F}_{k-1}^T + \mathbf{Q}$$

2. **Measurement Prediction**:
   $$\hat{y}_k = OCV(\hat{\text{SOC}}_{k|k-1}) + u_k R_0 + \hat{V}_{1,k|k-1} + \hat{V}_{2,k|k-1}$$

3. **Measurement Jacobian**:
   The measurement matrix $\mathbf{H}_k = \left.\frac{\partial h}{\partial x}\right|_{\hat{x}_{k|k-1}}$ is evaluated:
   $$\mathbf{H}_k = \begin{bmatrix} \left.\frac{dOCV}{d\text{SOC}}\right|_{\hat{\text{SOC}}_{k|k-1}} & 1 & 1 \end{bmatrix}$$

4. **Correction Stage**:
   $$\mathbf{S}_k = \mathbf{H}_k \mathbf{P}_{k|k-1} \mathbf{H}_k^T + R$$
   $$\mathbf{K}_k = \mathbf{P}_{k|k-1} \mathbf{H}_k^T \mathbf{S}_k^{-1}$$
   $$\hat{x}_{k|k} = \hat{x}_{k|k-1} + \mathbf{K}_k (y_k - \hat{y}_k)$$
   $$\mathbf{P}_{k|k} = (\mathbf{I} - \mathbf{K}_k \mathbf{H}_k) \mathbf{P}_{k|k-1}$$

---

## 3. Data-Driven Estimation via Echo State Networks (ESN)

Reservoir Computing (RC), specifically **Echo State Networks (ESN)**, is utilized for non-linear, data-driven regression (SOC/SOH tracking) and classification (thermal safety diagnostic status).

### Echo State Network Formulation
Unlike standard Recurrent Neural Networks (RNNs) or Long Short-Term Memory (LSTM) networks, ESNs project input signals into a high-dimensional, fixed, recurrent state space (the "reservoir") and only train the linear output readout weights. This drastically reduces training costs and enables real-time adaptation.

```
                  ┌──────────────────────────────────────────────┐
                  │            ESN Reservoir (x_t)               │
                  │   - Recurrent connection matrix W_res       │
                  │   - Leak Rate (α = 0.3)                      │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
  ┌──────────────────────┐               │                 ┌──────────────────────┐
  │ Inputs (u_t)         ├───────────────┼────────────────►│ Linear Readout W_out │
  │ - Voltage            │               │                 │                      │
  │ - Current            │               ▼                 │ - Linear combination │
  │ - Temperature        ├────────────────────────────────►│   for SOC / SOH      │
  └──────────────────────┘                                 └──────────────────────┘
```

The reservoir update equation at time step $t$ is:
$$\tilde{x}_t = \tanh\left(\mathbf{W}_{\text{in}} [1; u_t] + \mathbf{W}_{\text{res}} x_{t-1}\right)$$
$$x_t = (1 - \alpha) x_{t-1} + \alpha \tilde{x}_t$$
* $u_t$ is the input vector (e.g., scaled voltage, current, and temperature).
* $\mathbf{W}_{\text{in}} \in \mathbb{R}^{N_r \times (1 + N_u)}$ is the input weight matrix.
* $\mathbf{W}_{\text{res}} \in \mathbb{R}^{N_r \times N_r}$ is the recurrent reservoir matrix.
* $\alpha \in (0, 1]$ is the leak rate, adjusting the temporal rate of state evolution.
* $N_r$ is the reservoir size (e.g., $50$ nodes for hardware classifier, $300$ for SOC estimator).

### Echo State Property (ESP) and Spectral Radius
To ensure the network exhibits the *echo state property* (meaning the reservoir state is a fading memory of the input history, independent of initial state conditions), the spectral radius $\rho$ of the reservoir matrix $\mathbf{W}_{\text{res}}$ must be strictly bounded:
$$\rho(\mathbf{W}_{\text{res}}) = \max_i \{|\lambda_i|\} < 1$$
Where $\lambda_i$ are the eigenvalues of $\mathbf{W}_{\text{res}}$. Typical values reside in the range $0.70$ to $0.95$ to capture slow thermal transients.

### Readout Training via Ridge Regression
The output readout matrix $\mathbf{W}_{\text{out}}$ maps the combined input-reservoir state vectors to the target labels:
$$y_t = \mathbf{W}_{\text{out}} [1; u_t; x_t]$$

Given a collection of states gathered during the training phase (after discarding initial washout states to settle recurrent cold-start conditions), the readout weights are solved analytically using Ridge Regression (L2 regularization):
$$\mathbf{W}_{\text{out}} = \mathbf{Y}_{\text{target}} \mathbf{X}^T \left(\mathbf{X} \mathbf{X}^T + \lambda \mathbf{I}\right)^{-1}$$
* $\mathbf{X}$ is the matrix of state histories.
* $\mathbf{Y}_{\text{target}}$ is the target telemetry values.
* $\lambda$ is the L2 regularisation coefficient (e.g., $10^{-4}$), preventing overfitting.

---

## 4. Embedded Edge Optimizations

For resource-constrained edge hardware (e.g., STM32 H7 dual-core ARM Cortex-M), the firmware implements specific architectural optimizations:

### 1. Compressed Sparse Row (CSR) SpMV
A $50 \times 50$ reservoir matrix has $2,500$ floating-point multiplication operations. By introducing $85\%$ sparsity during reservoir generation ($\mathbf{W}_{\text{res}}$ entries set to zero), non-zero elements (NNZ) reduce to only $375$ operations.

To save RAM/Flash and bypass multiplication by zero, we compress $\mathbf{W}_{\text{res}}$ using CSR representation into three 1D arrays:
1. `val` (size $375$): Non-zero float values.
2. `col` (size $375$): Column index corresponding to each value.
3. `row_ptr` (size $51$): Indirection marking the starting offset of each row in `val` and `col`.

The Sparse Matrix-Vector multiplication (SpMV) loop is executed as:
```c
for (int i = 0; i < N_RESERVOIR; i++) {
    float sum = bias_input_terms[i];
    uint16_t start = row_ptr[i];
    uint16_t end = row_ptr[i + 1];
    for (uint16_t k = start; k < end; k++) {
        sum += val[k] * x[col[k]];
    }
    arg[i] = sum;
}
```

### 2. Fixed-Point Q12/Q15 Mathematics
To support microcontrollers lacking a floating-point unit (FPU), the inference can execute using pure integer arithmetic:
* **Quantized Scaling**:
  - Inputs scaled to Q12 format ($S_{\text{in}} = 4096$).
  - Weights and states represented in Q15 format ($S_{\text{weights}} = 32768$).
* **Fixed-point Tanh Look-Up Table (LUT)**:
  Instead of compiling transcendental float math (`tanhf`), a 33-point lookup table maps values in the range $[0.0, 1.0]$. The value is resolved via linear interpolation:
  $$\text{frac} = |x_{\text{Q15}}| \pmod{1024}$$
  $$\text{index} = |x_{\text{Q15}}| \gg 10$$
  $$\tanh(x_{\text{Q15}}) = \text{sign}(x_{\text{Q15}}) \cdot \frac{(1024 - \text{frac}) \cdot \text{LUT}[\text{index}] + \text{frac} \cdot \text{LUT}[\text{index} + 1]}{1024}$$

---

## 5. References & Literature Survey

1. **Plett, G. L.** (2004). *Extended Kalman filtering for battery management systems of LiPB-based HEV battery packs*. Journal of Power Sources, 134(2), 252-261.
2. **Jaeger, H., & Haas, H.** (2004). *Harnessing nonlinearity: Predicting chaotic systems and saving energy in wireless communication*. Science, 304(5667), 78-80.
3. **Rigutini, L., et al.** (2020). *State-of-charge estimation of lithium-ion batteries using reservoir computing*. IEEE Transactions on Industrial Electronics, 68(8), 7112-7121.
4. **Compressed Sparse Row (CSR) algorithms**: *Templates for the Solution of Linear Systems: Building Blocks for Iterative Methods*, SIAM Publication.
