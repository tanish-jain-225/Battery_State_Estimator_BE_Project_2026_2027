[← Back to README](../../README.md)

# ESN-Based Battery SOC/SOH Estimation with Embedded Hardware Validation

**Department:** Department of Automation and Robotics / Instrumentation  
**Institute:** Vivekanand Education Society's Institute of Technology (VESIT), Mumbai  
**Guide:** Dr. Kadambari Sharma  
**Team Members:** Sanjna Patankar, Akshay Nambiar, Satvik Verma, Tanish Sanghvi  
**Document Path:** [`docs/Review_1/Review_1_Progress.md`](file:///d:/_Deployed_Projects_Vercel/Battery_State_Estimator_BE_Project_2026_2027/docs/Review_1/Review_1_Progress.md)

---

## 📌 Problem & Proposed Solution

### The Problem
* **Coulomb Counting**: Open-loop integration accumulates drift and error over time.
* **Extended Kalman Filter (EKF)**: Strongly model-dependent and computationally heavy for embedded use.

### Proposed Solution
* **Echo State Network (ESN)**: A lightweight reservoir-computing estimator for battery SOC/SOH — trained once, cheap to run, and well suited to embedded and hardware deployment.
  * **Software**: Final estimator / product
  * **Hardware**: Embedded implementation & verification platform (Artix A7100T | RTL / HIL)

---

## ✅ Phase 1 — Completed (Review 1 Deliverables)

### Battery / Software
* ✔️ 2-RC battery simulator
* ✔️ EKF + Coulomb Counting + SOH tracking
* ✔️ ESN training pipeline
* ✔️ Flask dashboard deployed
* ✔️ C99 ESN implementation
* ✔️ CSR optimization — 6.7× speedup

### Embedded / Hardware
* ✔️ Q6.10 fixed-point ESN datapath
* ✔️ Hardware tanh LUT (odd-symmetry, positive half only)
* ✔️ Verilog ESN RTL — 100-neuron reservoir
* ✔️ BRAM-based weight / input / state storage
* ✔️ Double-buffered recurrent state memory
* ✔️ $W_{in} \cdot u + W \cdot x$ MAC $\rightarrow$ bias $\rightarrow$ clip $\rightarrow$ tanh pipeline
* ✔️ Vivado / XSim two-pass verification (Artix A7100T target)
* *(200 / 200 neuron updates matched bit-exactly against Python golden model)*

---

## 🔄 Phase 2 — In Progress (Targets Before Review 2)

### ESN / Software
* 🔵 Online ESN adaptation using RLS / gradient descent
* 🔵 **LSTM / GRU benchmarking**
* 🔵 Testing across different EV drive cycles
* 🔵 C99 deployment refinement

### Hardware / Embedded
1. **Multi-timestep sequence input**: Extend verified single-step design ($u(0)$) to full sequences ($u(0) \dots u(T)$).
2. **FPGA sequence-level verification**: Python golden model vs. Vivado/XSim bit-exact comparison on Artix A7100T.
3. **Artix A7100T deployment**: On-board resource utilization and inference latency profiling.
4. **Hardware-in-the-loop (HIL) interface**: UART link between battery simulator and FPGA board.
5. **End-to-end estimation**: Drive-cycle data $\rightarrow$ ESN $\rightarrow$ SOC / SOH on hardware.

---

## 📅 Phase 3 — Final Goal & Timeline

**Final Goal:** Deploy and validate a lightweight ESN-based SOC/SOH estimator on embedded hardware (Artix A7100T) using real / representative battery drive-cycle data.

* **Aug 31**: Literature review / IEEE target
* **Oct 15**: Final ESN software
* **3rd Wk Oct**: **Review II**
* **Oct 25**: Hardware HIL validation
* **Nov 20**: Final thesis
