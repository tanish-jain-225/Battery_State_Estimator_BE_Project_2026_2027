[← Back to README](../README.md) · [Research Paper Manuscript (IEEE / Q3 Scopus Target)](paper.md)

# Neuromorphic Computing for Intelligent Battery Management Systems: A Comprehensive Review of Spiking Neural Networks, Reservoir Computing and Edge AI

**Sanjna Patankar, Akshay Nambiar, Satvik Verma, Tanish Sanghvi, and Kadambari Sharma**  
*Department of Automation and Robotics / Instrumentation, Vivekanand Education Society's Institute of Technology (VESIT), Mumbai, India*  
*Emails: {2023.sanjna.patankar, 2023.akshay.nambiar, 2023.satvik.verma, 2023.tanish.sanghvi}@ves.ac.in*  
**Target Publication:** IEEE Transactions / Q3 Scopus-Indexed Review Journal (Comprehensive 11-Section Review Article)  
**Publication Date:** September 2026

---

**Abstract** — Lithium-ion battery packs sit at the centre of two of the fastest-growing segments of the electrical economy, electric vehicles and grid-scale energy storage and every safety, control and prognostic function of a Battery Management System (BMS) depends on accurate, real-time estimates of State of Charge (SOC), State of Health (SOH), State of Power (SOP) and Remaining Useful Life (RUL), none of which can be measured directly. This review traces the field from classical model-based estimators (Coulomb counting, OCV mapping, equivalent-circuit models, Kalman-filter variants) through conventional deep learning (feedforward, recurrent, convolutional and Transformer architectures) to neuromorphic computing, Spiking Neural Networks (SNNs), reservoir computing and Liquid State Machines, together with the hardware (Intel Loihi 2, SpiNNaker2, BrainChip Akida, IBM TrueNorth, memristive and FPGA platforms) and event-driven sensing schemes required to deploy them at the edge. A multi-dimensional benchmarking framework is adopted spanning accuracy, energy per inference, training cost and data efficiency, latency, hardware maturity and robustness across operating conditions. The benchmark concludes that while neuromorphic approaches are architecturally well motivated for the sparse, temporally native character of battery signals, the evidence base remains largely at the simulation stage: standardised, hardware-measured, cross-chemistry benchmarking against conventional deep learning is the critical next step before neuromorphic BMS techniques can be recommended for production deployment.

**Keywords** — battery management system; state of charge; state of health; remaining useful life; spiking neural networks; reservoir computing; Liquid State Machine; neuromorphic hardware; event-driven sensing; edge AI.

---

## 1. Introduction

Lithium-ion battery packs supervise an ever-larger share of the world's mobile and stationary energy. As pack counts, cell counts per pack and total deployed capacity climb, the BMS that supervises each pack must do more work within a similar, or shrinking, power and silicon budget. A BMS is only as good as its estimate of four internal states that cannot be measured directly: State of Charge (SOC), State of Health (SOH), State of Power (SOP) and Remaining Useful Life (RUL). These estimates feed monitoring, safety, diagnostics, control and prognostics, so estimation accuracy and estimation efficiency are not separate concerns: an estimator that is accurate but too slow or power-hungry to run continuously is not deployable, while one that is cheap but inaccurate introduces safety risk. This dual requirement is the central tension around which this review is organised.

Sections 3–4 trace the field's trajectory from classical model-based and shallow machine-learning estimators toward deep learning, which delivers real accuracy gains at a rising computational cost, larger models, longer training times and inference workloads that exceed what a low-power automotive microcontroller can sustain continuously. Because BMS inference must run for the operational life of every cell in a pack, even a modest per-inference energy cost compounds into a meaningful drain on usable capacity.

Neuromorphic computing is examined here as a candidate response. Spiking Neural Networks (SNNs, Section 5) and reservoir computing (Section 6, including Liquid State Machines and Echo State Networks) process information as sparse, event-driven spikes rather than dense, clocked activations, so their energy cost scales with how much the signal is actually changing rather than with a fixed sampling clock. Battery voltage, current and temperature signals are slowly varying or quiescent for much of an operating cycle, a property exploited directly by the event-driven sensing schemes of Section 8, making the sparsity assumption behind neuromorphic computation a natural fit. These architectures are also temporally native, carrying an internal notion of time and memory rather than reconstructing it from stacked input windows, matching the inherently time-dependent nature of degradation and charge dynamics (Section 2).

The review covers SNNs, reservoir computing/LSMs and the neuromorphic hardware capable of executing them, Intel Loihi, SpiNNaker, BrainChip Akida, IBM TrueNorth and FPGA accelerators, each evaluated against SOC/SOH/SOP/RUL and benchmarked against the conventional (Section 3) and deep-learning (Section 4) baselines that dominate production BMS design today. Section 9 consolidates the comparison into a multi-dimensional benchmark, Section 10 identifies open problems and a horizon-based research agenda and Section 11 concludes.

---

## 2. Battery Management Systems: Estimation Tasks and Requirements

A BMS functions as the central control intelligence keeping a lithium-ion pack within its safe operating envelope while maximising efficiency and preserving usable life. Because SOC, SOH, SOP and RUL cannot be read from a dedicated sensor, the BMS must estimate them dynamically from terminal voltage, current and surface temperature alone. Estimator accuracy underpins five downstream functions: monitoring (communicating remaining energy and capability), safety (triggering cutoffs that prevent thermal runaway and over-charge/discharge), diagnostics (flagging anomalous behaviour or fade), control (enforcing dynamic current limits) and prognostics (forecasting degradation for maintenance and second-life decisions).

### 2.1 State of Charge (SOC)

SOC expresses remaining electrochemical energy as a percentage of usable capacity. No sensor measures it directly; nonlinear resistance, C-rate shifts, capacity fade and voltage transients all distort real-time accuracy. Table 1 summarises the deployment requirements that any SOC estimator, classical, deep, or neuromorphic, must satisfy.

#### Table 1. SOC estimation requirements.

| Metric | Target / Constraint | Significance |
| :--- | :--- | :--- |
| **Accuracy** | $\le \pm 2–5\%$ error | Prevents premature shutdown under aggressive drive cycles |
| **Latency** | Sub-second updates | Real-time compatibility with traction control |
| **Noise tolerance** | Resilient to bias/drift | Prevents long-horizon error accumulation |
| **Adaptability** | Auto-corrects for decay | Precision across multi-year degradation |
| **Compute overhead** | Fits embedded MCU RAM/ROM | Runs on standard automotive-grade hardware |

### 2.2 State of Health (SOH), State of Power (SOP) and Remaining Useful Life (RUL)

SOH tracks structural degradation, most commonly via capacity retention ($\text{SOH} = C_{\text{present}}/C_{\text{rated}} \times 100\%$) or resistance growth. Degradation proceeds via calendar ageing (rest-driven) and cycle ageing (charge–discharge stress). Capacity-based indicators need full cycles for high baseline accuracy; resistance-based indicators work from brief pulses but are noise- and temperature-sensitive; multi-indicator fusion is more robust but adds model complexity; data-driven approaches capture cell-to-cell scatter but need large, clean training corpora.

SOP estimates peak deliverable/absorbable power over a short horizon (e.g., 2–10 s), computed as the tightest of four simultaneous limits: voltage, current, thermal and SOC headroom. Because SOP is derived downstream of SOC and SOH, errors in either propagate directly into the power estimate. RUL predicts the number of cycles or hours remaining before a cell reaches a failure threshold (typically 70–80% of rated capacity). Unlike SOH, which describes present conditions, RUL forecasts a future trajectory under uncertain future usage; because prediction error compounds over a multi-cycle horizon, recent frameworks move away from treating SOC, SOH and RUL as isolated single-state problems and instead co-estimate them simultaneously using attention mechanisms operating across dual time scales: intra-cycle dynamics coupled with inter-cycle ageing.

### 2.3 Shared Operational Challenges and Benchmark Data

All four tasks share recurring distortions (Table 2). A cell's instantaneous response also depends on cycling history and rest duration, not just present inputs; memoryless algorithms discard this context. Modern architectures therefore use a dual time-scale framework: a fast, intra-cycle scale for second-by-second voltage/current dynamics and a slow, inter-cycle scale for capacity loss and resistance growth; capturing both at once requires a model with explicit temporal memory.

#### Table 2. Operational challenges across all estimation tasks.

| Distortion | Description |
| :--- | :--- |
| **Electrochemical nonlinearity** | Voltage response near charge/discharge limits is strongly nonlinear |
| **Thermal dependence** | Reaction rates, internal resistance and available capacity all shift with ambient temperature |
| **Dynamic load variation** | High-frequency, erratic current demand accelerates noise accumulation relative to constant-current lab tests |
| **Sensor noise and bias** | Small current-sensor offsets accumulate into large integration drift over time |
| **Cell imbalance** | Manufacturing variation causes cells within a series string to drift apart in capacity and resistance |
| **Hysteresis and ageing drift** | OCV curves shift between charge/discharge direction and shift further as the cell ages |

Four open-access datasets anchor algorithm benchmarking in this literature (Table 3): NASA PCoE (18650 NCA end-of-life cycling), CALCE (prismatic LCO ageing under CC/CV protocols), Oxford (pouch-cell long-term cycling, used for cross-dataset validation) and Panasonic (cylindrical NMC real-world drive-cycle data). Common error metrics across these benchmarks are RMSE, MAE, MAPE, maximum peak error and target-microcontroller runtime.

#### Table 3. Benchmark dataset summary.

| Dataset | Format / Chemistry | Signals | Focus |
| :--- | :--- | :--- | :--- |
| **NASA PCoE** | 18650 NCA | V, I, T, impedance, capacity | SOH/RUL trajectory forecasting |
| **CALCE** | Prismatic LCO | V, I, T, impedance, capacity, energy | Capacity-fade modelling |
| **Oxford** | Pouch cell | V, I, T | Cross-chemistry ageing validation |
| **Panasonic** | Cylindrical NMC | V, I, T (dynamic profiles) | Real-world dynamic SOC |

Conventional estimation relies on simplified equivalent-circuit or physics-based electrochemical models: the former execute quickly but struggle with temperature, hysteresis and dynamic loads; the latter are more accurate but computationally prohibitive on automotive microcontrollers. Existing methods lack an efficient way to extract nonlinear, multi-scale temporal patterns directly from field data, the gap that motivates the learning-based and neuromorphic estimators developed in later sections.

---

## 3. Conventional Estimation Methods

Classical estimation splits into physics-based methods (explicit state-space or electrochemical models tracked via filters or observers) and data-driven methods.

### 3.1 Coulomb counting and OCV mapping

Coulomb counting integrates net load current against a known baseline capacity. It requires no structural model and near-zero compute, making it the default commercial baseline, but its open-loop nature makes it vulnerable to current-sensor bias, integration-noise accumulation and irrecoverable initial-state errors. Open-circuit voltage (OCV) mapping exploits the monotonic relationship between a rested cell's equilibrium voltage and its remaining capacity via calibrated look-up tables. It requires an extended rest period (unusable online during active charge/discharge), suffers on LFP chemistries with a flat mid-charge OCV plateau and is subject to charge/discharge hysteresis and thermal dependence (Table 4).

#### Table 4. Coulomb counting vs. OCV mapping.

| Property | Coulomb Counting | OCV Mapping |
| :--- | :--- | :--- |
| **Model dependency** | None | Calibrated OCV–SOC map |
| **Real-time capable** | Yes | No (needs rest/relaxation) |
| **Primary error driver** | Sensor-bias accumulation | Hysteresis, flat-voltage regions |
| **Role in BMS** | Inter-cycle recalibration baseline | Primary intra-cycle estimator |

### 3.2 Equivalent-circuit and electrochemical models

Equivalent circuit models (ECMs) represent electrochemical dynamics with lumped networks (voltage source, ohmic resistor, one or more RC pairs) and dominate online estimation by balancing physical fidelity against real-time execution. Higher-order RC structures improve training-set fit but do not necessarily generalise better to unseen drive cycles or aged packs; parameters are typically identified online via recursive least squares (RLS) or offline via particle swarm optimisation. Electrochemical models capture spatial transport, solid-phase diffusion and reaction kinetics via coupled PDEs, directly tracking safety-critical internal states such as lithium-plating boundaries and SEI growth. Full-order models require dozens of hard-to-identify parameters, making online use on embedded hardware impractical.

### 3.3 Stochastic estimation: Kalman filters and observers

Kalman filter variants are the dominant stochastic framework (Table 5): the linear KF is inapplicable to the battery's strong OCV–SOC nonlinearity; the Extended KF (EKF) linearises via first-order Taylor expansion; the Unscented KF (UKF) uses the sigma-point unscented transform for higher accuracy at greater compute cost; adaptive/H$\infty$ variants add robustness against sensor uncertainty at added tuning complexity.

#### Table 5. Kalman-filter variant comparison.

| Variant | Nonlinearity mechanism | Key advantage | Primary limitation |
| :--- | :--- | :--- | :--- |
| **EKF** | First-order Taylor linearisation | Low compute cost; simple setup | Prone to divergence near strong nonlinearity |
| **UKF** | Sigma-point unscented transform | No Jacobian calculation; higher accuracy | Increased execution overhead |
| **Adaptive / H$\infty$** | Linearisation + H$\infty$ gain | Robust against sensor uncertainty | Complex tuning |

Observer-based methods construct a deterministic closed-loop model that drives the voltage-residual estimation error toward zero using calculated feedback gains: Luenberger observers are classical linear observers with static gains, a basic structural reference that struggles with nonlinear voltage behaviour, while sliding-mode observers (SMOs) use high-frequency discontinuous switching control to force system states toward a defined sliding surface, giving strong robustness to model uncertainty at the cost of chattering artefacts that require boundary-layer smoothing.

### 3.4 Optimisation-based identification and traditional machine learning

Optimisation-based parameter identification is used primarily to identify model parameters, RC component values, capacity limits, that support the state estimators above rather than to estimate SOC/SOH directly. Recursive Least Squares (RLS) is an online technique; a forgetting factor lets RLS track slowly time-varying parameters such as ohmic resistance ($R_0$) and polarisation capacitance ($C_p$) in real time. Particle Swarm Optimisation (PSO) and its multi-swarm variant (MPSO) are widely applied offline for global parameter search across nonlinear ECM/electrochemical objective surfaces.

Traditional machine-learning methods model battery behaviour directly from measured data (V, I, T), bypassing explicit circuit or electrochemical equations. Support Vector Machines (SVMs) map nonlinear input features into a high-dimensional space via kernel functions, tracking SOC accurately under structured drive cycles, but training scales poorly with large time-series datasets. Gaussian Process Regression (GPR) offers a probabilistic, non-parametric alternative that additionally yields calibrated uncertainty estimates around each prediction, valuable for safety-margin decisions, at the cost of cubic-time training complexity that limits scalability to large fleets or long cycling histories.

#### Table 6. Comparative summary of conventional estimators.

| Family | Accuracy | Real-time | Cost | Noise resilience | Ageing tolerance | Primary limitation |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Coulomb counting** | Low–Medium | Excellent | Minimal | Poor (unbounded drift) | None | Uncorrected sensor-bias drift |
| **OCV mapping** | Medium | Poor (needs rest) | Minimal | High (steep regions) | Low | Requires long rest periods |
| **ECM + Kalman/Observer** | Good | Good | Moderate | Good | Moderate | Model-order/accuracy trade-off |
| **Electrochemical (P2D)** | High | Poor | High | Good | Moderate | Parameter identification under ageing |
| **Traditional ML** | Good (in-distribution) | Good | Moderate | Moderate | Low | Poor out-of-distribution generalisation |

A systematic reading of this literature surfaces four recurring bottlenecks: (1) an accuracy-vs-complexity trade-off, in which higher-order ECMs and full-order electrochemical models exceed automotive-microcontroller memory and processing limits; (2) generalisation bottlenecks across chemistries and unseen drive cycles; (3) reliance on hand-crafted structures and precise parameter tuning (Kalman noise covariances, RLS forgetting factors); and (4) an inability to jointly and efficiently capture the nonlinear, multi-scale temporal patterns that dominate real-world degradation. These limitations directly motivate the shift to deep learning covered in Section 4.

---

## 4. Deep Learning Approaches for BMS

### 4.1 Feedforward baselines

Feedforward/MLP baselines treat the cell as a black-box mapping from terminal signals to internal states, avoiding explicit electrochemical parameterisation. Representative results (Table 7) include joint SOC/SOE estimation via multi-layer feedforward networks, pulse-train injection for SOC (maximum error $< 2\%$), deep MLPs with mRMR feature selection over 24 candidate signals on 72 real-world BMW i3 trips (RMSE 0.84%/2.36% across seasons) and cross-temperature validation on Panasonic/Turnigy cells from $-10\text{ }^\circ\text{C}$ to $25\text{ }^\circ\text{C}$ (RMSE 0.76–0.81%). Feedforward networks remain indispensable for real-time deployability but cannot natively capture long-horizon temporal dependencies.

#### Table 7. Feedforward/MLP SOC estimator comparison.

| Study | Input features | Architecture | Platform / Chemistry | Key innovation |
| :--- | :--- | :--- | :--- | :--- |
| **Sharma et al.** | V, I, T, P | 2-hidden-layer ML-FNN | Panasonic NCR18650 | Cumulative power feature; joint SoC+SoE |
| **Wang et al.** | Pulse-train | 2-layer FNN | NMC / LixV3O8 | Pulse injection for SoC |
| **Lin** | 24 candidate signals (mRMR-selected) | Deep MLP (64-128-64, ReLU) | BMW i3 (real trips) | Feature selection across environment/vehicle/battery signals |
| **Vidal et al.** | V, I, T | Recurrent / non-recurrent NN | Panasonic / Turnigy | Cross-temperature validation, $-10$ to $25\text{ }^\circ\text{C}$ |

### 4.2 Recurrent architectures

Recurrent architectures (LSTM/GRU) carry hidden state across time steps, suiting the slow, nonlinear temporal process of degradation. A spatio-temporal-attention LSTM (STL-LSTM) achieved RMSE 0.0038 on NASA B5/B6; standard and lightweight-gated LSTM/GRU variants reached $R^2 > 0.99$ with training times of 16.85 s and 150.06 s respectively; a hybrid LSTM–GRU balanced long- and short-term dependency for smart-device deployment (9.26 MB footprint). A recurring finding is that GRU/LSTM can introduce unnecessary complexity for direct cycle-to-capacity mapping unless paired with explicit temporal feature engineering or attention.

#### Table 8. Representative recurrent-architecture results.

| Reference | Architecture | Dataset | RMSE | $R^2$ | Training time / size |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Xu et al.** | STL-LSTM | NASA B5/B6 | 0.0038 | - | - |
| **Bairwa et al.** | Standard LSTM | NASA B0005 | 0.0076 | 0.9944 | 16.85 s |
| **Bairwa et al.** | Lightweight GRU | NASA B0005 | 0.0160 | 0.9754 | 150.06 s |
| **Wu et al.** | Hybrid LSTM–GRU | NASA B0005 | 0.6903% | - | 9.26 MB (size) |

### 4.3 Convolutional and Transformer models

CNN and CNN-hybrid approaches extract shift-invariant features from voltage–capacity, incremental-capacity (dQ/dV), or differential-voltage curves, one-dimensional electrochemical curves that carry ageing signatures. Sensitivity analysis via input–output partial derivatives shows an SOH-CNN attending mainly to the first half of the voltage curve while a companion $\Delta$SOH-CNN focuses on the latter half and the historical trajectory. Because the two estimates are correlated, a random-forest regressor fuses them to mitigate multicollinearity while retaining complementary information. On a 124-cell fast-discharging LFP dataset the RF-CNN hybrid achieved an MAE of 0.85%, a 35% improvement over the individual models.

Transformer/attention-based models rely on self-attention to capture global dependencies in parallel rather than sequentially, avoiding the memory constraints of recurrent networks on long sequences (Table 9). Representative combinations include a dual-encoder Transformer with an adaptive observer ($< 1\%$ maximum error on LiFePO4), a CNN front end with a Transformer and sigma-point Kalman filter and a Cross-Attention Multitask Transformer (CA-MT-BHP) jointly estimating SOC and SOH via two task-specific pathways motivated by their physical coupling.

#### Table 9. Representative Transformer-based results.

| Methodology | Dataset | RMSE | MAE |
| :--- | :--- | :---: | :---: |
| **Transformer + SSL (Hannan et al.)** | LG 18650HG2 | 0.9–1.9% | 0.44–0.7% |
| **2-Encoder Transformer + I&I Observer (Shen et al.)** | LiFePO4 | $< 1\%$ | - |
| **TTSNet + Kalman Filter (Bao et al.)** | Open vehicle datasets | 0.69% | 0.50% |
| **Comparative Study (Yilmaz et al.)** | NASA, BMW, Stanford, Musoshi | 0.99% | - |
| **DAE $\rightarrow$ Transformer** | NASA / CALCE | 0.07–0.08 | 0.06–0.07 |
| **Vision Transformer (ViT)** | NASA / CALCE | 0.46–0.47% | 0.36–0.37% |

### 4.4 Joint estimation and physics-informed learning

Joint SOC–SOH estimation models (DRSN-CW-LSTM, CNN-SAM-LSTM, Multi-Depth Expert Networks, Robust RC–CEEUKF, PSO-BiLSTM-EKF) consistently reach $R^2 > 98.7\%$ on both tasks simultaneously (Table 10), reflecting growing recognition of SOC/SOH interdependence.

#### Table 10. Joint SOC–SOH comparison.

| Model | SOC MAE (%) | SOC RMSE (%) | SOC $R^2$ (%) | SOH MAE (%) | SOH RMSE (%) | SOH $R^2$ (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **DRSN-CW-LSTM** | 0.010 | 0.015 | 99.4 | 0.011 | 0.016 | 99.3 |
| **CNN-SAM-LSTM** | 0.011 | 0.016 | 99.3 | 0.012 | 0.017 | 99.2 |
| **Multi-Depth Expert** | 0.009 | 0.013 | 99.5 | 0.010 | 0.014 | 99.4 |
| **Robust RC–CEEUKF** | 0.018 | - | 99.1 | 0.015 | 0.020 | 98.9 |
| **Feature Fusion Model** | 0.014 | 0.020 | 98.9 | 0.016 | 0.022 | 98.7 |
| **PSO-BiLSTM-EKF** | 0.012 | 0.017 | 99.2 | 0.0145 | 0.0196 | 98.95 |
| **Adaptive SOC-OCV Mapping + EKF** | 0.0125 | 0.0178 | 99.15 | - | - | - |

Physics-informed deep learning (PINNs) embeds physical constraints directly into training rather than running physics and ML pipelines independently (Table 11). Singh et al. built a PINN around the single-particle model (SPM), incorporating Fick's second law of diffusion for solid-phase Li-ion concentration directly into training and approximating the dimensionless concentration $C(x,\tau)$ with a small feedforward network ($4\text{ layers} \times 10\text{ neurons}$, tanh activation) under Neumann boundary conditions. A separate framework validated across 387 batteries (XJTU, TJU, MIT, HUST datasets) reported overall MAPE 0.87%; in small-sample regimes (training on just one to four batteries) the PINN consistently outperformed MLP and CNN counterparts, with the gap widening as training data shrank and fine-tuning on a single target battery often outperformed training a target-domain model from scratch on two batteries. A related Neural-ODE framework has been validated for “state of mission” (SOM), a sequential encoder processes historical V/I/T to estimate an initial state, after which an ODE solver propagates it forward through a mission profile, expressing SOM as a binary feasibility flag, probabilistic score, or continuous 0–100% readiness metric folding terrain, power profile and ambient conditions into a single figure beyond conventional SOC.

#### Table 11. Comparative analysis of physics-informed architectures.

| Study | Core NN | Physical constraint | Target state | Validation |
| :--- | :--- | :--- | :--- | :--- |
| **Singh et al.** | Small feedforward ($4\times 10$, tanh) | Fick's second law (SPM diffusion) | Solid-phase concentration $\rightarrow$ SOC | Single-particle-model simulation |
| **Cross-dataset PINN** | MLP/CNN comparison backbone | Electrochemical residual loss | SOH / capacity fade | 387 batteries: XJTU, TJU, MIT, HUST |
| **Ozkan & Ozkan** | Neural-ODE encoder + solver | Mission-profile state propagation | State of Mission (SOM) | Feasibility/readiness scoring |

### 4.5 The edge-deployment limit

Across all deep-learning families, on-device adaptation remains the binding constraint: quantisation-aware training (QAT) and neural architecture search (NAS, e.g., APQ, with search spaces exceeding $10^{34}$ architectures) reduce inference cost but require heavy retraining overhead, while backpropagation-based on-device fine-tuning needs memory and compute far beyond microcontroller-class RAM (Table 12). This “deployability problem”, accurate models that are too power- and memory-hungry for continuous embedded execution, is the direct motivation for the neuromorphic alternatives reviewed in Sections 5–8.

#### Table 12. Conventional vs. neuromorphic edge-AI paradigms.

| Dimension | Conventional Edge AI | Neuromorphic Alternative (SNNs) | Key limitation driving exploration |
| :--- | :--- | :--- | :--- |
| **On-device adaptation** | Backpropagation + QAT/pruning; NAS search spaces $> 10^{34}$ architectures | Local, event-driven update rules (STDP) | Backprop needs memory/compute beyond microcontroller RAM |
| **Retraining overhead** | High (thousands of QAT iterations) | Low, but algorithms remain immature | Immature training pipelines; superiority over optimised conventional pipelines not yet demonstrated |
| **Deployment risk** | Lower (mature toolchains) | Higher (nascent ecosystem) | Algorithm–hardware co-design still required |

---

## 5. Spiking Neural Networks for BMS

### 5.1 Fundamentals

SNNs, often called the third generation of neural network models, represent information as discrete spike events rather than continuous activations, replacing synchronous multiply-accumulate (MAC) operations with sparse, event-driven accumulate (AC) updates. The Leaky Integrate-and-Fire (LIF) neuron is the default building block; variants trade complexity for biological plausibility and capability (Table 13): the simplest Integrate-and-Fire (IF) neuron omits the leak term; Adaptive LIF (ALIF) adds spike-frequency adaptation for better sequence processing; Exponential/Adaptive-Exponential IF give sharper spike onset and richer firing patterns at added parameter-tuning cost; Hodgkin–Huxley (HH) offers gold-standard biological fidelity at very high computational cost.

#### Table 13. Neuron-model comparison.

| Neuron model | Biological plausibility | Complexity | Key advantage | Main challenge |
| :--- | :---: | :---: | :--- | :--- |
| **IF** | Low | Minimal | Simplicity | Unrealistic temporal integration |
| **LIF** | Moderate | Low–Moderate | Good balance of fidelity and cost | Leak/threshold tuning |
| **ALIF** | Moderate | Moderate | Spike-frequency adaptation; better temporal credit assignment | Extra state/parameters; tuning sensitivity |
| **EIF / AdEx** | Moderate–High | Moderate–High | Sharp, smooth spike onset; richer firing patterns | Parameter calibration; numerical/hardware calibration |
| **HH** | Very High | Very High | Gold-standard biological fidelity | Computationally very expensive |

### 5.2 Spike encoding

Real-valued sensor data must be converted to spike trains via rate coding (information in firing frequency), temporal coding (information in spike timing, e.g., time-to-first-spike), or population coding (information distributed across an ensemble). Benchmark comparisons of encoders found step-forward (SF) coding gave the lowest reconstruction error and highest energy efficiency overall; the Bens-Spiker-Algorithm (BSA) gave the best rectangular-wave reconstruction (MSE 0.064) but at much higher runtime/energy cost; LIF-based encoding handled irregular high-frequency signals well but showed bias on trended signals.

Temporal codes such as TSC achieve 30–60$\times$ lower spike counts/operations than rate coding for comparable accuracy (93.63% top-1 on VGG-16/CIFAR-10). For asynchronous neuromorphic event streams, First-Spike (FS) coding determines the predicted class from whichever output neuron fires earliest, trained via a surrogate-gradient scheme that propagates error from the first-spike time through a Gaussian window. Beyond single-neuron temporal codes, population encoding (e.g., Gaussian-receptive-field bin encoders) spreads information across neuronal bins, increasing representational capacity for settings such as reinforcement-learning state spaces where a single scalar temporal code cannot capture a complex feature.

### 5.3 Training paradigms

The non-differentiable spike function precludes direct backpropagation, yielding three paradigms (Table 14): surrogate-gradient (SG) direct training (smooths the spike derivative for backpropagation-through-time); ANN-to-SNN conversion (maps a pretrained ANN's activations onto spike rates, competitive accuracy, ~98.1%/89.3% on MNIST/CIFAR-10, but requiring ~20,000 spikes/inference, ~20 ms latency and inapplicable to native event-based data); and STDP-based unsupervised learning (biologically grounded Hebbian plasticity, most energy-efficient at ~5 mJ/inference and ~4,000 spikes, but lowest accuracy, ~74.2% on CIFAR-10).

#### Table 14. Multi-metric SNN training comparison.

| Model | MNIST Acc. | CIFAR-10 Acc. | Latency | Energy/Inf. | Spike Count |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **ANN (CNN)** | 99.2% | 92.0% | 45 ms | 200 mJ | 0 |
| **Converted SNN** | 98.1% | 89.3% | 20 ms | 20 mJ | ~20,000 |
| **Surrogate-Gradient SNN** | 97.8% | 85.7% | 10 ms | 15 mJ | ~12,000 |
| **STDP-based SNN** | 95.5% | 74.2% | 15 ms | 5 mJ | ~4,000 |

### 5.4 Architectures applied to SOC/SOH

Feedforward SNNs are the most mature BMS application: SpikeSOH reduced energy usage by up to 99.2% and accelerated inference over 280$\times$ versus CNN-LSTM/Encoder-LSTM/GRU-CNN/Tiny-CNN baselines, at 0.36 mJ per inference. Convolutional SNNs (CSNNs) combining Poisson spike input, convolution/pooling layers and probabilistic STDP reached 98.3% on Caltech Faces/Motorbikes with memristor-compatible, event-driven updates. Spiking-Transformer hybrids (e.g., A2OS2A) use binary query, non-negative ReLU key and ternary value activations so the query–key transpose ($Q\cdot K^T$) attention product reduces to addition rather than multiplication, eliminating softmax/scaling and achieving 96.42%/78.66% on CIFAR-10/ImageNet-1K with fully addition-only, MAC-free attention.

### 5.5 SNN vs. conventional deep learning

On shallow tasks (MNIST) the accuracy gap has nearly closed (ANN 98.23% vs. surrogate-gradient SNN 98.10% at 8 timesteps); on deeper tasks (CIFAR-10, VGG7) the gap widens modestly (ANN 83.6% vs. best SNN 83.0% at 2 timesteps). The dominant SNN advantage is energy: GPU operation-count proxies show ANN MNIST inference at $1.1355\times 10^{-3}\text{ J/sample}$ versus $10^{-5}–10^{-6}\text{ J}$ for optimised SNNs (10–100$\times$ reduction). At the hardware level, digital neuromorphic chips (Loihi 2, TrueNorth) report ~23.6 and ~26 pJ/OP respectively, while analog neuromorphic implementations reach 1.2–4 fJ/SOP, versus ~27 pJ/OP for GPU MACs and ~330 pJ/OP for the STM32N6 (Table 15). The literature converges on a tunable accuracy–energy trade-off governed by neuron model, encoding, threshold and time-step choice: adaptive neurons with direct/rate coding and surrogate-gradient training suit accuracy-critical deployments; simple IF/LIF neurons with sparse encoding or STDP suit severely energy-constrained edge nodes.

#### Table 15. Hardware energy/area efficiency.

| Implementation | Type | Model | Energy Eff. | Area Eff. | Node |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **GPU MAC** | Digital | DNN MAC | ~27 pJ/OP | ~53.3 $\mu\text{m}^2/\text{OP}$ | 16 nm |
| **STM32N6** | Digital | DNN MAC | ~330 pJ/OP | - | 16 nm |
| **TrueNorth** | Digital | LIF | ~26 pJ/OP | ~0.079 $\mu\text{m}^2/\text{OP}$ | 28 nm |
| **Loihi 2** | Digital | LIF | ~23.6 pJ/OP | ~0.029 $\mu\text{m}^2/\text{OP}$ | 14 nm |
| **Danneville et al.** | Analog | LIF | ~2 fJ/SOP | ~31 $\mu\text{m}^2/\text{neuron}$ | 65 nm |
| **Besrour et al.** | Analog | LIF | ~1.2 fJ/SOP | ~34 $\mu\text{m}^2/\text{neuron}$ | 28 nm |

### 5.6 Simulation frameworks

BindsNET (PyTorch-based, object-oriented Network/Nodes/Connections/Monitors with RL-pipeline support) and snnTorch (treats neurons as recurrent PyTorch activation units, offering plug-and-play LIF/Lapicque models and surrogate-gradient functions) dominate ML-oriented SNN research; Brian2 supports larger biologically realistic single-node simulations but does not scale across clusters or export to neuromorphic hardware; Intel's Lava, backed by Loihi 2, offers orders-of-magnitude better energy-per-spike and scales to billion-neuron systems but only on Loihi-class hardware within its asynchronous, event-driven programming constraints (Table 16). For BMS-scale problems, BindsNET/snnTorch suit research and rapid prototyping, while Lava is the appropriate target once genuine on-chip deployment is the goal.

#### Table 16. Simulation-framework comparison.

| Feature | BindsNET | snnTorch | Brian2 | Lava (Loihi 2) |
| :--- | :--- | :--- | :--- | :--- |
| **GPU acceleration** | Native (PyTorch) | Native (PyTorch) | Via GeNN | Simulation only |
| **Neuromorphic HW export** | No | No | No (NIR export) | Loihi 1/2 |
| **Learning rules** | Hebbian, STDP, MSTDP, SGD | Surrogate BPTT, QAT | User-defined, custom | STDP, 3-factor (on-chip) |
| **Arbitrary ODEs** | No (fixed models) | Yes | No (fixed models) | Limited (microcode on Loihi 2) |
| **RL/agent support** | Native pipeline | Manual | Manual | Manual |

---

## 6. Reservoir Computing and Liquid State Machines

### 6.1 Principles

Reservoir computing (RC) is a brain-inspired paradigm in which a fixed, randomly connected recurrent network (the “reservoir”) nonlinearly projects inputs into a high-dimensional state space, while only a linear readout layer is trained. Introduced independently by Jaeger (Echo State Networks, ESNs) in the early 2000s, RC's echo-state property (ESP) requires the asymptotic reservoir state to depend only on input history, not initial conditions, guaranteed when the recurrent weight matrix's largest singular value is below one. Best performance often occurs near the “edge of chaos.” Limitations include heuristic reservoir design (no complete recipe for the optimal architecture for a given task) and an early-stage universal-approximation theory focused on existence proofs rather than design guidance.

### 6.2 ESNs vs. spiking reservoirs (RSNNs)

Both share the fixed-reservoir/trainable-readout paradigm but differ in neuron model: ESNs use continuous (tanh/sigmoid) artificial neurons with synchronous updates, while RSNNs use spiking LIF-type neurons communicating via discrete events (Table 17). RSNNs are more biologically plausible and natively suited to neuromorphic hardware, but require spike encoding and more complex structural tuning to reach adequate spike diversity. For near-term deployment on conventional embedded processors, ESNs currently offer the more practical trade-off; RSNNs are the better long-term fit for neuromorphic silicon.

#### Table 17. ESN vs. spiking reservoir (RSNN).

| Property | ESN | RSNN |
| :--- | :--- | :--- |
| **Neuron model** | Continuous activation (tanh/sigmoid) | Spiking (LIF-type) |
| **Update mode** | Synchronous | Event-driven, asynchronous |
| **Biological plausibility** | Low (abstracts away temporal precision) | Substantially higher |
| **Neuromorphic HW fit** | Poor | Native |
| **Training/deployment simplicity** | Simple, fast, conventional hardware | Requires spike encoding, structural tuning |
| **Near-term BMS practicality** | Higher | Lower (but better long-term hardware fit) |

### 6.3 Liquid State Machines

Introduced by Maass et al. (2002), the Liquid State Machine (LSM) is a spiking-reservoir architecture explicitly modelled on cortical microcircuits with mixed excitatory/inhibitory recurrent connectivity. LSMs pair naturally with event-based sensors (dynamic vision sensors) that already output spike-like streams; on the SpiNNaker neuromorphic processor, an LSM achieved 94.43% accuracy on the event-based N-MNIST benchmark, a state-of-the-art LSM result. Direct LSM applications to battery time series remain comparatively nascent in the reviewed literature.

### 6.4 RSNNs for SOC/SOH

RSNN architectures typically comprise an input layer (encoded battery features), a reservoir of 50–500 LIF neurons with sparse recurrent connectivity (20–100% density tested) and mixed excitatory/inhibitory synapses and a feedforward readout. Kamarudin et al. (2025/2026) systematically evaluated reservoir configurations for SOH prediction, achieving an optimised RMSE of 0.029, comparable to or exceeding many conventional deep-learning approaches with substantially fewer computational resources. RSNNs show strong promise for embedded BMS deployment: low inference latency (12–26 ms per input iteration, depending on the time-step window), training time comparable to or faster than feedforward networks and small memory footprints.

### 6.5 Physical and hardware reservoirs

Physical (as opposed to simulated) reservoirs are motivated by three imperatives: reducing data-transfer energy between sensing, storage and compute; exploiting the intrinsic nonlinear dynamics of physical materials directly as computation, avoiding software simulation; and reaching ultra-low power. Physical systems naturally supply the required reservoir properties, nonlinearity from material response curves, fading memory from transient relaxation and high dimensionality from spatial distribution across the substrate. Memristive/nanoscale-device reservoirs have demonstrated speech-recognition-class tasks, with the emergent collective dynamics of nanoscale memristive elements supplying the nonlinear interaction and memory needed for temporal processing; optoelectronic and photonic reservoirs offer raw processing speed but lag in integration density; spintronic approaches offer non-volatility but face scalability challenges. This diversity of physical substrates underscores that reservoir computing's core requirements, nonlinearity, fading memory, high dimensionality, can, in principle, be satisfied by almost any sufficiently rich dynamical medium, which is precisely what makes hardware reservoirs an attractive long-term path to ultra-low-power, always-on BMS inference.

### 6.6 Trade-offs

Increasing reservoir size generally improves feature richness with diminishing returns. RC's linear, closed-form readout training (no iterative backpropagation) is a critical advantage for battery applications, where large labelled degradation datasets are expensive to acquire, ESNs can be trained in a single-shot closed-form solution, enabling rapid adaptation to new battery units from minimal data. Generalisation across chemistries remains a significant open challenge, since most RSNN studies validate exclusively on the NASA LCO dataset (Table 18). The literature's central finding: ESNs offer the best near-term trade-off for battery BMS, combining state-of-the-art accuracy at low simulation cost, while RSNNs and physical reservoirs represent the longer-term path to genuinely ultra-low-power, hardware-native inference.

#### Table 18. RC deployment trade-off summary.

| Dimension | ESN (software) | RSNN (software) | Physical reservoir |
| :--- | :--- | :--- | :--- |
| **Inference latency** | Low (matrix–vector multiply) | Low–moderate (12–26 ms/input) | Ultra-low (ns–$\mu$s) |
| **Energy per inference** | Moderate | Low (~150 nJ) | Ultra-low (aJ–$\mu$W) |
| **Hardware requirements** | Standard processor | Neuromorphic chip preferred | Specialised fabrication |
| **Deployment maturity** | High | Low (simulation-only) | Low–moderate |

---

## 7. Neuromorphic Hardware Platforms

Moving from simulation to hardware is the critical inflection point at which theoretical neuromorphic energy/latency advantages must be validated.

### 7.1 Platform survey

Intel Loihi 2 integrates up to 128 fully asynchronous neuromorphic cores per chip, supporting thousands of programmable spiking neurons per core; edge configurations offer up to 1 million neurons and 120 million synapses per chip at 30–80 mW static power per core, with larger multi-chip systems (Alia Point: 128 chips; Hala Point: 1,152 chips) targeting datacenter-scale neuromorphic computing. Python-based Lava/LavaDL provide the software stack.

SpiNNaker/SpiNNaker2 take a fundamentally different approach, a massive array of conventional ARM cores optimised for real-time software simulation of spiking networks rather than custom analog/mixed-signal neuron circuits. SpiNNaker2 adds dynamic voltage/frequency scaling and adaptive body biasing for per-core power management that scales with neural activity, plus dedicated accelerators for exponential/logarithm functions, MAC arrays for DNN tasks and 2D convolution engines, alongside on-chip SRAM and in-package LPDDR4 memory.

BrainChip Akida is the most commercially mature neuromorphic processor for edge AI, available as both a standalone chip and licensable IP, already deployed in vision, industrial IoT and wearable products. It implements a feedforward pipeline of event-driven convolutional/pooling/spiking-activation nodes, supports rate- and temporal-coded spikes with programmable LIF-type neuron models and targets sub-10 mW always-on power envelopes, but its feedforward architecture is not natively suited to the recurrent temporal processing SOC/SOH estimation requires, so algorithm–hardware co-design is essential.

IBM TrueNorth uses a Globally Asynchronous Locally Synchronous (GALS) design with fully asynchronous inter-core spike communication over a 2D mesh; it consumes roughly 70 mW, about 1/10,000th the power density of a conventional processor. Memristor/RRAM accelerators exploit Ohm's-law/Kirchhoff's-law in-place multiply-accumulate, eliminating separate MAC units; commercial discovery boards (Knowm) and RRAM AI accelerators (Crossbar) are available. FPGAs allow custom neuron models, spike routing and plasticity mechanisms unconstrained by fixed commercial architectures, with demonstrated sub-millisecond inference latency for small-to-medium SNNs at hundreds-of-milliwatts power, a flexible near-term prototyping route ahead of committing to a fixed ASIC.

### 7.2 Comparative positioning

Across all platforms, the general pattern is a trade-off between programmability/research maturity (Loihi 2, SpiNNaker2) and commercial deployability (Akida), with digital designs (Loihi, SpiNNaker, Akida, TrueNorth) currently far ahead of analog/memristive and FPGA alternatives in software-ecosystem maturity, even though the latter promise lower fundamental energy-per-operation once fabrication and integration-density challenges are overcome (Table 19). For near-term BMS deployment, Akida offers the most viable path given commercial availability and a software ecosystem compatible with standard deep-learning frameworks; Loihi 2/Lava and FPGA prototyping remain the natural route where recurrent, reservoir-style temporal processing is required. The choice between neuromorphic and conventional edge AI ultimately depends on the specific estimation task, the importance of event-driven temporal sparsity and the maturity of the algorithm–hardware ecosystem at the time of deployment.

#### Table 19. Neuromorphic-hardware comparison.

| Platform | Approach | Power | Deployment maturity | BMS suitability note |
| :--- | :--- | :---: | :---: | :--- |
| **Loihi 2** | Digital async, custom neurons | 30–80 mW/core | Research | High neuron/synapse density; edge-scale |
| **SpiNNaker2** | ARM-core software simulation | Scalable, DVFS-managed | Research | Flexible, but not custom-silicon efficient |
| **BrainChip Akida** | Digital, feedforward, commercial | $< 10\text{ mW}$ | Commercial | Most viable near-term; needs recurrence co-design |
| **TrueNorth** | Digital, GALS | ~70 mW | Research (mature demo) | High efficiency, limited on-chip learning |
| **Memristor/RRAM** | Analog in-memory | Very low | Early / lab-scale | Promising; integration-density challenges |
| **FPGA** | Reconfigurable digital | 100s mW | Prototyping | Best near-term flexibility for custom SNN/RC designs |

---

## 8. Event-Driven Sensing for Battery Monitoring

### 8.1 Principle and reported gains

Commercial BMS designs couple a fixed-frequency ADC to a microcontroller executing periodic acquisition, running the estimation routine at the same cadence regardless of algorithmic need. This is attractive for its determinism but wasteful, since most acquired data corresponds to near-zero signal change, avoidable overhead rather than an intrinsic accuracy or safety requirement. Event-based sensing concepts, most mature in neuromorphic vision, generate output only from elements whose signal has changed by more than a threshold rather than sampling a full frame at a fixed rate. Applying this “delta” principle to battery channels (voltage, current, temperature) is conceptually straightforward but not yet demonstrated end-to-end on real BMS hardware in the reviewed literature.

Sigma-delta ($\Sigma-\Delta$) modulation, already the dominant conversion architecture in high-precision commercial analog front ends, is structurally relevant because it embodies a change-based principle at the circuit level (oversampling plus noise-shaped quantisation), even though it is not “event-driven” in the strict level-crossing sense. Across the event-driven SOC-estimation literature, a consistent quantitative claim is a reduction in processed samples/ADC conversions/estimator updates by roughly one to two orders of magnitude relative to fixed-rate Coulomb counting, concentrated in rest, storage, or light-load operating regimes, with the reduction narrowing substantially under high-dynamics (fast-charge, aggressive-driving) profiles. Combining event-driven acquisition of fast channels (voltage, current) with periodic or condition-triggered execution of a slower capacity/SOH prediction model is the most defensible latency strategy identified in current research (Table 20).

#### Table 20. Conventional vs. event-driven sensing.

| Parameter | Fixed-Rate Sampling | Event-Driven Sensing |
| :--- | :--- | :--- |
| **Hardware complexity** | Mature ADC + MCU pipeline | Needs level-crossing/delta front end or neuromorphic device |
| **Determinism / testability** | High; matched to safety-case argumentation | Lower; variable timing complicates safety-case design |
| **Suitability for BMS (current)** | High, incumbent, certified, widely deployed | Promising for SOC/Coulomb-counting efficiency; not yet mature |

#### Table 21. Comparison with neuromorphic sensing approaches.

| Technology | Event-generation mechanism | Platform | Relevance to BMS | Maturity on battery signals |
| :--- | :--- | :--- | :--- | :--- |
| **Dynamic vision sensor (DVS)** | Log-intensity change threshold per pixel | Silicon retina / DVS chip | Conceptual template for level-crossing V/I/T encoding | Demonstrated only for vision; not evaluated on battery signals |
| **Artificial sensory neuron (e.g., epitaxial VO2)** | Threshold-switching instability | Device-level spike-encoding neuron | Calibratable multisensory transduction | Demonstrated on generic (non-battery) stimulus only |
| **Sigma-delta ($\Sigma-\Delta$) ADC** | Oversampling + noise-shaped quantisation | Standard analog front end | Already deployed in commercial BMS AFEs | Not “event-driven” in the level-crossing sense |

### 8.2 Integration challenges

Event-driven Coulomb counting and event-triggered SOC studies are almost exclusively evaluated in simulation rather than on real sensor noise, EMI and switched-mode charging/balancing ripple present in real BMS hardware. Threshold selection is the most pervasive open issue: no reviewed method demonstrates threshold-adaptive behaviour validated across the wide temperature range of an automotive or grid-storage battery, nor characterises device drift over multi-year deployment. Replacing a mature fixed-rate ADC-plus-MCU pipeline with a level-crossing front end, event encoder and event-triggered processing stage introduces new circuit design-space dimensions (comparator hysteresis, event-timestamp resolution, asynchronous digital logic) that current work only partially characterises.

A further latency subtlety concerns slow, cumulative trends: an event-driven scheme tuned to flag only rapid changes can be systematically slower to detect a gradual capacity trend than a fixed-rate scheme that logs the same change incrementally. Event-driven, machine-learning-based capacity-prediction approaches partially address this by combining event-driven acquisition of fast channels with periodic or condition-triggered execution of a slower prediction model for capacity and SOH, the hybrid strategy this review finds most defensible given the current evidence.

The connection between neuromorphic sensing and battery monitoring can be made concrete by mapping each BMS channel onto a threshold-crossing spike-generation rule of the kind used in dynamic vision sensors: for voltage, the natural analogue of a DVS pixel's log-intensity-change threshold is a voltage-change threshold; similar mappings apply to current and temperature. The near-term research roadmap favours reimplementing this principle with conventional or level-crossing-ADC circuitry on battery-relevant channels, deferring harder device-level (physical neuromorphic sensor) integration to a longer horizon and combining event-driven fast channels with a scheduled minimum-rate fallback during high-dynamics regimes to avoid missing slow, cumulative trends.

---

## 9. Comparative Analysis and Benchmarking

### 9.1 A multi-dimensional framework

Reviews of battery estimation methods have historically ranked approaches primarily by point accuracy (MAE, RMSE, MAPE, $R^2$). This is insufficient for deployment decisions, where an estimator must also fit a fixed energy budget, a millisecond-to-second control loop and an MCU/ASIC/neuromorphic-chip compute envelope and remain trustworthy across field conditions. This review instead adopts a multi-dimensional benchmarking framework (Table 22) spanning accuracy, energy/power, training cost and data efficiency, latency and real-time suitability, hardware-deployment feasibility and robustness across operating conditions, since field batteries rarely operate at the single condition used to train a model.

#### Table 22. Benchmarking dimensions.

| Dimension | What it captures | Why it matters for BMS deployment |
| :--- | :--- | :--- |
| **Accuracy (MAE/RMSE/MAPE/$R^2$)** | Point-estimate correctness | Baseline comparability across studies |
| **Energy/power per inference** | Sustained operating cost | Determines feasibility of continuous, per-cell monitoring |
| **Training cost & data efficiency** | Effort/data needed to reach deployment accuracy | Battery degradation datasets are expensive to collect |
| **Latency & real-time suitability** | Response time relative to control-loop cadence | Sub-second traction-control compatibility |
| **Hardware-deployment feasibility** | Chip readiness from research device to deployable product | Time-to-production and certification path |
| **Robustness across conditions** | Performance vs. temperature, ageing, C-rate | Field batteries rarely match training conditions |

### 9.2 Accuracy

Four families are represented: classical/model-based, conventional ML, conventional deep learning and neuromorphic approaches (SNN, RC, reservoir-SNN hybrids, spiking-attention). Because studies cited across the surveys use different chemistries, cycling protocols and temperatures, results are not collapsed into a single ranked table; representative neuromorphic studies are summarised qualitatively in Table 23. Across all three primary neuromorphic studies, the recurring qualitative claims are (a) lower energy consumption from event/spike-driven computation, (b) improved noise robustness from spike-based encoding and (c) strong spatiotemporal feature extraction from spiking-attention or reservoir dynamics. These are architectural/theoretical arguments consistent with the broader neuromorphic-computing literature rather than measured, battery-specific energy or latency results in every case.

#### Table 23. Neuromorphic studies in the reviewed corpus (qualitative summary).

| Study | Task | Reported accuracy | Reported energy | Note |
| :--- | :--- | :--- | :--- | :--- |
| **SSA-Net (spiking spatiotemporal attention)** | SOH/RUL (full-life-cycle EIS) | Qualitative claim of competitive accuracy vs. ANN baselines | Not reported | Chemistry/conditions not specified |
| **SpikeSOH** | SOC/SOH (cross-temperature) | Up to 99.2% energy reduction and $>280\times$ speedup vs. CNN-LSTM/Encoder-LSTM/GRU-CNN/Tiny-CNN | 0.36 mJ/inference | Feedforward SNN; software evaluation |
| **Reservoir SNN (TDSRC vs. SRC)** | SOH | Comparable or lower error than SRC using fewer reservoir neurons | Not reported (architectural-complexity proxy only) | Model-size finding, not sample-count finding |

### 9.3 Energy and power

Energy claims in the neuromorphic BMS literature are frequently made at the level of general principle (event-driven computation is inherently cheaper than dense, synchronous computation) rather than as a reported, hardware-measured number at a specified operating point (Table 24). Several supplied studies (SSA-Net, SpikeSOH, TDSRC/reservoir-SNN) do not specify the target hardware, so their energy advantage remains architectural/theoretical rather than independently verified for battery applications.

#### Table 24. Energy reporting in neuromorphic BMS studies.

| Method | Architecture | Energy metric | Hardware specified? |
| :--- | :--- | :--- | :---: |
| **SSA-Net** | Spiking spatiotemporal attention | Energy/inference, not reported | No |
| **SpikeSOH** | SNN, cross-temperature | Energy/inference: 0.36 mJ (software evaluation) | No |
| **TDSRC vs. SRC** | Reservoir SNN | Energy/inference proxied only by architectural complexity (fewer neurons) | No |

Where neuromorphic approaches currently win: Two defensible, literature-supported points favour neuromorphic approaches within this corpus. First, motivational and architectural robustness to noise: spike-based encoding is argued to be less susceptible to signal noise than continuous-valued ANN inputs, relevant to field-deployed sensors with imperfect signal conditioning, though this remains an architectural claim rather than a measured, head-to-head noise-robustness comparison against conventional DL on the same battery dataset. Second, model-size efficiency: where directly compared, reservoir and spiking architectures have achieved comparable accuracy to conventional deep-learning baselines with substantially fewer parameters and shorter or comparable training times (Sections 5.4, 6.4), a genuine and reproducible advantage even where absolute energy-per-inference figures are not separately reported.

### 9.4 Training time, data efficiency and latency

Reduced training-data requirements are a plausible, but only partially evidenced, advantage for neuromorphic methods: the one relevant data point in the corpus (a time-delayed spiking-reservoir configuration matching accuracy with fewer neurons than a standard spiking reservoir) is a model-size finding, not a sample-count finding, so the claim that SNNs need fewer labelled training samples is not yet independently supported by the reviewed literature.

A conventional DL pipeline follows a fixed path ($\text{sample} \rightarrow \text{ADC} \rightarrow \text{preprocess} \rightarrow \text{dense inference} \rightarrow \text{prediction}$) at a regular interval regardless of whether the signal is changing; an event-driven neuromorphic pipeline instead follows $\text{sample} \rightarrow \text{change-detect} \rightarrow \text{spike-encode} \rightarrow \text{SNN/reservoir inference}$. However, most neuromorphic BMS studies in the corpus report no hardware latency measurement at all, evaluating purely in simulation.

### 9.5 Overall positioning and critical gaps

Table 25 consolidates the qualitative positioning of the four method families across the six benchmarking dimensions.

#### Table 25. Overall qualitative positioning (+ favourable, $-$ unfavourable).

| Family | Accuracy | Energy cost | Training cost | Hardware maturity | Overall assessment |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Model-based (KF/ECM/Observer)** | ++ (drifts with age/temp) | +++ (no training) | N/A | +++ | Mature, low-cost baseline; accuracy ceiling limits standalone use |
| **Conventional ML (SVM/GPR)** | + | ++ | ++ | ++ | Competitive with engineered features; superseded by DL on raw sequences |
| **Conventional DL (LSTM/Transformer)** | +++ (best raw accuracy) | $-$ (rising with model size) | $--$ (heavy) | + | Best raw accuracy; deployability problem at the edge |
| **Neuromorphic (SNN/RC)** | ++ (claimed, partly verified) | ++ (claimed, partly verified) | + (claimed) | + | Architecturally well motivated; evidence largely simulation-stage |

The most consequential gaps identified are: (1) no controlled, same-cell/same-chemistry/same-temperature benchmark suite comparing SNN/RC methods directly against LSTM/GRU baselines; (2) no complete sensor-to-inference energy accounting (sensing + communication + compute) for any reviewed neuromorphic BMS study, the figure that actually determines system-level impact; and (3) single-dataset validation (mostly NASA LCO) with no hardware-measured latency for most neuromorphic BMS studies (Table 26). Addressing these suggests a natural roadmap: near-term work should prioritise standardised reporting (energy per inference on named hardware, same-dataset accuracy comparisons); medium-term work should validate on multi-chemistry, multi-temperature datasets beyond NASA/CALCE and longer-term work should demonstrate full sensor-to-spike-to-decision pipelines on physical neuromorphic hardware rather than in software simulation alone.

#### Table 26. Critical research gaps.

| Research gap | Why it matters | Required experiment |
| :--- | :--- | :--- |
| **No controlled SNN-vs-LSTM/GRU benchmark suite for batteries** | Cross-family superiority claims are currently unverifiable | Same cells, chemistry, temperature and train/test split across families |
| **No complete sensor-to-inference energy accounting** | System-level energy (sensing + communication + compute) determines real BMS impact | End-to-end pipeline energy measurement including sensing and communication, not just compute kernel |
| **Single-dataset validation (mostly NASA LCO); no hardware-measured latency** | Generalisation across chemistry/ageing/temperature is unverified | Multi-chemistry, multi-temperature validation studies; named-hardware latency measurement |

#### Table 27. Outlook summary by horizon.

| Horizon | Priority | Rationale |
| :--- | :--- | :--- |
| **Near-term** | Standardised reporting: energy/inference on named hardware; same-dataset accuracy comparisons | Closes the largest evidence gap identified in Section 9 |
| **Medium-term** | Multi-chemistry, multi-temperature validation beyond NASA/CALCE | Addresses the generalisation bottleneck common to classical and neuromorphic estimators alike |
| **Long-term** | Full sensor-to-spike-to-decision pipelines on physical neuromorphic hardware | Moves the field from simulation-stage demonstration to deployable product |

---

## 10. Challenges, Open Problems and Outlook

### 10.1 Encoding–accuracy–energy trade-off

No single spike-encoding scheme dominates every axis (Section 5.2): rate coding is robust and simple but spike-inefficient; temporal codes cut spike counts and energy substantially but are more sensitive to jitter and noise; population coding spreads representational load across more neurons at a corresponding memory cost. Selecting an encoding scheme is therefore a deployment-specific design decision, not a solved problem.

### 10.2 Simulation-to-hardware gap

Most reported SNN/RC battery results (Sections 5, 6, 9) are software simulations rather than measurements on physical neuromorphic chips or research-stage memristor-crossbar accelerators. Closing this gap requires battery-specific studies reporting measured, not simulated, energy and latency figures from real neuromorphic hardware under realistic sensor noise and switching-circuit interference.

### 10.3 Generalisation across chemistries, ageing states and conditions

SOH indicators already trade off differently by chemistry (Section 2.2) and classical estimators show recurring generalisation bottlenecks (Section 3); the same pattern reappears for neuromorphic methods, most of which are validated on a single dataset rather than across chemistries and temperature ranges.

### 10.4 Integration path, ASIC/FPGA co-design

Connecting an event-driven sensing front end to a neuromorphic processing core inside real pack electronics (Section 8) remains a practical sensor-to-spike pipeline challenge. FPGA-based acceleration is currently the most flexible near-term route for prototyping SNN and reservoir designs before committing to a fixed ASIC and the comparative hardware assessment (Section 7) suggests Akida-class commercial chips and Loihi 2/Lava research platforms as the most likely near-term integration targets, contingent on algorithm–hardware co-design for the recurrent processing SOC/SOH estimation requires. Taken together, these open problems point toward a research agenda centred on standardised, hardware-measured, cross-chemistry benchmarking, the same deployment-readiness bar that conventional BMS estimators have already had to clear.

---

## 11. Conclusion

Sections 5 through 9 support a consistent conclusion: spiking neural networks and reservoir computing offer a theoretically well-motivated and, on the evidence gathered in Section 9, only partially demonstrated, route to lower-energy, temporally native battery state estimation. The literature reviewed here is still predominantly at the algorithmic and simulation stage rather than the validated-hardware-deployment stage. Conventional deep learning (Section 4) currently delivers the best raw accuracy on SOC/SOH/RUL estimation but carries a real and growing “deployability problem” at the edge, larger models, longer training and inference costs that strain embedded compute and energy budgets as monitoring scales across every cell in a pack.

Neuromorphic computing's architectural case is strong: event-driven sparsity is a natural match for slowly varying battery signals and SNN/RC architectures are temporally native in a way that suits the multi-scale dynamics of charge and degradation. But the evidence base supporting that case, within this corpus, remains largely simulation-only, validated on a narrow set of chemistries and datasets and rarely accompanied by measured, hardware-level energy or latency figures specific to battery applications. Closing this gap, standardised same-cell benchmarking against conventional DL baselines, full sensor-to-inference energy accounting and demonstrated multi-chemistry generalisation on physical neuromorphic hardware, would let the next generation of this literature test the promise documented here against the same deployment-readiness bar that conventional BMS estimators have already had to clear.

---

## Selected References

- **Section 2**:
  - [1] Lyu, Wu, Lyu, Yang & Li (2024), *J. Energy Storage* 101:113827.
  - [2] Nazim et al. (2025), *ICT Express* 11:769–789.
  - [3] Saha, Goebel, Poll & Christophersen (2007), *AUTOTESTCON*.
  - [4] Cai, Qin, Chen & Wu (2022), arXiv:2210.11941.
  - [7] Guo & Shen (2024), arXiv:2404.12774.
  - [11] Zhuo, Zou, Liao & Cai (2024), *Sci. Rep.*
  - [12] Thelen et al. (2024), *npj Materials Sustainability*.
- **Section 3**:
  - [17] Zhao, Duncan & Howey (2020), *IEEE Trans. Control Syst. Technol.*
  - [19] Allam & Onori (2020), arXiv:2008.10467.
  - [22] Wu et al. (2022), *Int. J. Energy Res.*
  - [23] Hu, Li & Peng (2012), *J. Power Sources* 198:359–367.
  - [24] Antón et al. (2013), *IEEE Trans. Power Electron.* 28(12):5919.
  - [25] He, Qin, Sun & Shui (2013), *Energies* 6:5088–5100.
  - [28] Guo, Liu & Zhu (2023), *Front. Energy Res.* 10:998002.
- **Section 4**:
  - [30] Sharma, Saxena & Arya (2022), *Proc. IEEE PEDES*.
  - [32] Lin (2024), *Heliyon* 10(15).
  - [33] Vidal, Kollmeyer, Chemali & Emadi (2022), *J. Energy Storage* 47.
  - [34] Xu, Xu & Zhu (2024), *PLOS ONE* 19(12):e0312856.
  - [35] Bairwa, Pareek & Jadoun (2025), *Sci. Rep.* 15:37078.
  - [42] Vaswani et al. (2017), *NeurIPS* 30.
  - [43] Hannan et al. (2021), *Sci. Rep.* 11:19541.
  - [44] Shen et al. (2022), *J. Energy Storage* 45:103768.
  - [49] Bao et al. (2024), *IEEE Trans. Veh. Technol.* 73:7838–7851.
  - [65] Indumathi & Gopalakrishnan (2026), *AIP Advances* 16:045009.
  - [73] Singh, Ebongue & Rael (2023), *Batteries* 9:301.
  - [74] Wang et al. (2024), *Nature Commun.* 15:4332.
  - [75] Ozkan & Ozkan (2025), *iScience* 28:113593.
- **Section 5**:
  - [79] Ayasi et al. (2025), *Eng* 6(11):304.
  - [85] Aribe (2025), *Int. J. Eng. Trends Technol.* 73(10):32–48.
  - [86] Ferreira et al. (2025), *Front. Neurosci.* 19:1676570.
  - [87] Hazan et al. (2018), *Front. Neuroinform.* 12:89.
  - [88] Stimberg, Brette & Goodman (2019), *eLife* 8:e47314.
  - [89] Eshraghian et al. (2023), *Proc. IEEE* 111(9):1016–1054.
  - [90] Intel Labs (2021), *Lava software framework*.
  - [91] Davies et al. (2018), *IEEE Micro* 38(1):82–99.
- **Section 6**:
  - Jaeger (2001/2002), *Echo State Networks*.
  - Maass, Natschläger & Markram (2002), *Liquid State Machines*.
  - Kamarudin, Mispan, Zainudin & Sofian (2026), *Turkish J. Eng.* 10(2):407–417.
  - Cucchi et al. (2022), *Neuromorphic Comput. Eng.* 2(3):032002.
  - Paquot et al. (2012), *Sci. Rep.* 2:287.
  - Lugnan et al. (2020), *APL Photonics* 5(2):020901.
  - Tanaka et al. (2022), *Phys. Rev. Res.* 4:L032014.
  - Gaurav, Stewart & Yi (2023), *Front. Comput. Neurosci.* 17:1148284.
  - Milano et al. (2025), *Nature Commun.* 16:58741.
  - Yamazaki & Kinoshita (2023), *Adv. Sci.* 10(33):2304804.
  - Danneville et al., analog LIF, ~2 fJ/SOP, 65 nm.
  - Besrour et al., analog LIF, ~1.2 fJ/SOP, 28 nm.
  - Patino-Saucedo et al., LSMs on SpiNNaker, 94.43% on event-based N-MNIST.
- **Section 7**:
  - Davies et al. (2018), *IEEE Micro* 38(1):82–99.
  - Modha et al. (2023), *Science* 382(6671):329–335.
  - Xu et al., memristor-based Transformer accelerators.
  - Intel Newsroom / lava-nc.org, Loihi 2 specifications.
  - BrainChip technical documentation, Akida architecture.
- **Section 8**: Event-driven Coulomb-counting & event-triggered SOC studies, level-crossing ADC front ends, dynamic vision sensors, epitaxial-$\text{VO}_2$ artificial sensory neurons.
- **Section 9**: Comprehensive BMS estimation survey literature & comparative positioning matrices.
