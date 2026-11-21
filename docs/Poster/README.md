# Capstone Project Presentation Poster (2 Sheets, A3 Portrait)

[← Back to Main Repository](../../README.md) · [← Capstone Thesis](../Thesis/README.md) · [Publications](../Publications/README.md) · [View PDF Poster](Project_Poster.pdf)

---

## 📌 Overview

This directory contains the official **Academic Exhibition & Defense Presentation Poster** for the Bachelor of Engineering Capstone Major Project:

* **Project Title:** *Battery State Estimator: An Echo State Network-Based Approach to Battery State Estimation*  
* **Institution:** Vivekanand Education Society's Institute of Technology (VESIT), Chembur, Mumbai  
* **Department:** Department of Automation & Robotics | B.E. Major Project | Academic Year 2026–2027  
* **Student Authors:**  
  1. **Akshay Nambiar** (Roll No. 17)  
  2. **Sanjna Patankar** (Roll No. 19)  
  3. **Satvik Verma** (Roll No. 32)  
  4. **Tanish Sanghvi** (Roll No. 61)  
* **Project Guide:** **Dr. Kadambari Sharma**  
* **Deliverable Asset:** [`docs/Poster/Project_Poster.pdf`](Project_Poster.pdf) (**535 KB / 522.65 KiB**, 2 Sheets, A3 Portrait Format, Vector PDF, Open / Unencrypted)

> [!NOTE]
> **Academic Portfolio Status (All 4 Deliverables Finalized & Integrated):**  
> Alongside [`Project_Poster.pdf`](Project_Poster.pdf), all **4 out of 4** academic deliverables are now 100% complete, integrated, and verified alongside the entire software, firmware, C99 CSR acceleration, Artix-7 RTL silicon IP block (`esn_ip_platform` v1.2), and 125 automated regression tests in the turnkey `v2.4.1` release.
> 
> *Encryption Policy Across Deliverables:*  
> * [`Project_Poster.pdf`](Project_Poster.pdf) is intentionally **Open / Unencrypted** for unrestricted public exhibition, seminar display, and defense presentation.  
> * [`docs/Publications/Research_Paper.pdf`](../Publications/Research_Paper.pdf), [`docs/Publications/Review_Paper.pdf`](../Publications/Review_Paper.pdf), and [`docs/Thesis/Final_Thesis.pdf`](../Thesis/Final_Thesis.pdf) are **Encrypted** as official academic camera-ready and institutional submission monographs.

---

## 📄 Deliverable Asset Summary

| Asset File | Format | Geometry | File Size | Description | Status |
| :--- | :---: | :---: | :---: | :--- | :---: |
| [`Project_Poster.pdf`](Project_Poster.pdf) | Vector PDF | 2 Sheets, A3 Portrait | **535,198 bytes** (~523 KB) | Official B.E. Capstone Academic Exhibition & Defense Poster across 11 structured panels (Open / Unencrypted format for public exhibition and defense). | **Completed & Integrated (Open)** |

---

## 📐 Detailed Poster Panel Structure & Content

The poster is organized across **11 numbered sections** spanning two comprehensive A3 portrait exhibition sheets:

### 📑 Sheet 1: Architecture, Methodology & Silicon Hardware Design

#### `01` Problem Statement & Motivation
* **Hardware Gap:** Most FPGA Echo State Network (ESN) designs fix their weights directly in logic gates and are rarely checked bit-for-bit against a software model, preventing reuse across multiple tasks.
* **Application Need:** A Battery Management System (BMS) cannot directly measure State of Charge (SOC); traditional Kalman-filter observers require an accurate cell model and current battery capacity, both of which drift nonlinearly as cells age.
* **Target Users:** Embedded systems designers requiring a compact, formally verified learned battery estimator for electric vehicles (EV) and grid battery storage packs.

#### `02` Objectives & Success Criteria
* **Objective 1:** Design a reusable ESN IP block (Q6.10 fixed-point, single MAC) with standard AXI4-Lite and AXI4-Stream interfaces with weights dynamically loaded at run time.
* **Objective 2:** Formally verify the IP bit-for-bit against an independent Python floating/fixed-point golden model, both in cycle-accurate simulation and on physical FPGA silicon.
* **Objective 3:** Apply the IP as an onboard battery SOC estimator, evaluated across the public NASA Ames PCoE battery aging dataset against classical Extended Kalman Filter (EKF) observers.
* **Target Metrics:**
  * *IP Silicon:* $< 1\%$ of device LUTs for the core; 100% bit-exact outputs across all internal datapath pipeline stages.
  * *Application:* Single update latency within a standard $10\text{ ms}$ BMS control period; SOC error comparable or superior to rated-capacity EKF.

#### `03` Proposed System / Solution (Two-Stage Architecture)
* **Stage 1 — Task-Independent ESN Silicon IP (`esn_axi_ip`, Artix-7 @ 80 MHz):**
  * **Input BRAM:** $u(t)$ in signed Q6.10 fixed point.
  * **Weight Storage:** $W_{\text{in}}$ and $W$ dual-port Block RAMs.
  * **State BRAM:** Ping-pong state buffer storing reservoir activations $x(t)$.
  * **Arithmetic Core:** Single pipelined MAC unit utilizing $2 \times \text{DSP48E1}$ slices ($104$ terms per neuron, signed Q12.20 internal accumulation).
  * **Activation Function:** Rounding, bias addition, dynamic saturation clipping $[-5.0, +5.0]$, and an odd-symmetric 5,121-entry $\tanh$ lookup table (LUT).
  * **State Feedback:** $x(t+1)$ written back to the ping-pong state buffer.
* **Stage 2 — Application Layer (Battery SOC / SOH Readout):**
  * **Input Features:** Voltage $V(t)$, current $I(t)$, temperature $T(t)$, and moving averages from 18650 Li-ion cells.
  * **Readout Layer:** Ridge regression weights stored in Q4.14 fixed point computing SOC and SOH.
  * **Host CPU Interface:** AXI4-Lite registers, AXI4-Stream DMA, or UART streaming.
* *Architectural Advantage:* Stage 1 builds a task-independent ESN IP whose weights load at runtime. Stage 2 loads battery-trained weights into the same IP; adapting to a new battery chemistry or application requires only new weights, **never a new FPGA bitstream**.

#### `04` Methodology & Workflow (7-Step Execution Plan)
1. **IP Spec:** Q6.10 reservoir activation, Q12.20 products, single MAC datapath, runtime weight configuration.
2. **Golden Model:** Independent, bit-accurate Python model of fixed-point arithmetic (`hardware/FPGA_Verifier/golden_model.py`).
3. **IP RTL:** Synthesizable Verilog core, Block RAM weight storage, AXI4-Lite & AXI4-Stream wrappers in AMD Xilinx Vivado 2023.1.
4. **IP Verify:** Stage-level register-transfer comparison against the golden model; packaging into Vivado IP Catalog (`component.xml`).
5. **Application:** Supervised offline training of SOC and SOH readout matrices on NASA PCoE battery cycling data (34 cells).
6. **Deploy:** Flash bitstream and load battery weights into the IP on the Digilent Arty A7-100T development board.
7. **Evaluate:** Rigorous statistical benchmarking across 29 held-out battery cells against EKF / UKF baselines using Wilcoxon signed-rank testing.

#### `05` Key Technologies & Components
* **FPGA Hardware:** Digilent Arty A7-100T (Xilinx XC7A100T-1CSG324C), DSP48E1 slices, Block RAM (RAMB36E1/RAMB18E1).
* **System Interfaces:** AXI4-Lite register bank, AXI4-Stream slave/master, FTDI USB-UART onboard transceiver.
* **Development Software:** Verilog HDL, AMD Xilinx Vivado 2023.1, Vivado Simulator (XSim), Python 3.10+ (NumPy, SciPy).
* **Algorithms:** 100-neuron ESN (spectral radius $\rho = 0.9$, leak rate $\alpha = 0.25$, sparsity $85\%$), Ridge regression readout; dual 2-RC Extended Kalman Filter (EKF) and Unscented Kalman Filter (UKF) benchmarks.
* **Operating Constraints:** $80\text{ MHz}$ global clock, 16-bit fixed-point arithmetic, single MAC pipeline.

---

### 📑 Sheet 2: Implementation, Benchmarking & Experimental Evidence

#### `06` Prototype & Hardware Implementation
* **RTL Synthesis:** Synthesized schematic of the ESN reservoir datapath in Vivado, comprising Address Generator, $W$ BRAM, State BRAM 0/1, Input BRAM, Bias BRAM, $W_{\text{in}}$ BRAM, Controller FSM, and Neuron Core (DSP48E1 + $\tanh$ ROM).
* **Hardware Footprint:**
  * Standalone IP Core: **318 LUTs** ($0.50\%$ of device), **2 DSP slices**, $80\text{ MHz}$ operation.
  * Packaged IP (`esn_axi_ip` in Vivado IP Catalog): **1,868 LUTs**, **4 DSPs**, **14.5 BRAM blocks**.
* **Stage-by-Stage Bit-Exact Verification:** 100% exact parity achieved across all 5 datapath stages:
  * `MAC` output match: $6,400 / 6,400$
  * `BIAS` addition match: $6,400 / 6,400$
  * `SUM` saturation match: $6,400 / 6,400$
  * `TANH_IN` scaling match: $6,400 / 6,400$
  * `TANH_OUT` LUT match: $6,400 / 6,400$

#### `07` Experimental Setup & Test Protocol
* **IP Test Vector:** $6,400$ neuron updates executed in Vivado XSim against the Python golden model; cross-validated over physical AXI4-Lite and AXI4-Stream hardware interfaces.
* **Instrumentation:** XSim cycle logs, Vivado timing and post-implementation utilization reports, on-chip cycle counter timers.
* **Dataset:** NASA Ames Prognostics Center of Excellence (PCoE) 18650 battery cycling data spanning ambient temperatures from $4^\circ\text{C}$ to $44^\circ\text{C}$ and discharge currents from $1\text{ A}$ to $4\text{ A}$ across **2,214 discharge windows** (with each of the 29 cells held out in turn for leave-one-out cross-validation).
* **Algorithmic Baselines:**
  1. *EKF (Rated Capacity):* Standard Kalman filter parameterized with initial nominal capacity ($2.0\text{ Ah}$).
  2. *EKF (Measured Capacity):* Kalman filter given ground-truth aged capacity.
  3. *Capacity-Tracking EKF:* Dual-state observer co-estimating capacity fade.
  4. *ESN (No Capacity Input):* Pure data-driven reservoir model without knowledge of capacity.
* **Success Criteria:** Zero stage mismatches; timing closed at $80\text{ MHz}$ ($WNS > 0$); update execution latency $< 10\text{ ms}$.

#### `08` Quantitative Results & Hardware Performance

##### A. Pooled SOC Estimation Accuracy (29 Held-Out NASA Cells)

```
Capacity-Tracking EKF  │ ████████████████████████████████ 0.061 MAE
EKF (Measured Cap.)    │ █████████████████████████████████ 0.063 MAE
ESN (Zero Capacity In) │ ███████████████████████████████████ 0.067 MAE
EKF (Rated Capacity)   │ ███████████████████████████████████████ 0.074 MAE
                       └───────────────────────────────────►
                        0.00   0.02   0.04   0.06   0.08  SOC MAE
```

##### B. Silicon Resource & Verification Metrics Table

| Performance Metric | Design Target | Measured Hardware Result | Compliance |
| :--- | :---: | :---: | :---: |
| **IP Core LUTs / DSP** | $< 1\%$ of XC7A100T | **318 LUTs (0.50%) / 2 DSPs** | **Exceeded** (Ultra-compact) |
| **Packaged IP (OOC)** | Fits Artix-7 device | **1,868 LUTs, 4 DSPs, 14.5 BRAM** | **Met** ($2.95\%$ LUT utilization) |
| **Clock Frequency (80 MHz)** | Timing met ($WNS > 0$) | **$+0.023\text{ ns}$ slack** ($+0.251\text{ ns}$ in v1.2) | **Met** (Timing closed) |
| **Execution Latency per Update**| $\le 10\text{ ms}$ | **$535.1\text{ }\mu\text{s}$** ($3.84\text{ }\mu\text{s}$ in fast core) | **Exceeded** ($18.7\times$ faster) |
| **Bit-Exact Update Parity** | $100\%$ match | **$6,400 / 6,400$ ($100.0\%$)** | **Met** ($0$ LSB mismatch) |
| **Per-Cell SD of SOC MAE** | Lower than EKF | **$0.020$ vs $0.035 - 0.056$** | **Exceeded** ($1.7\times - 2.8\times$ lower spread) |

#### `09` Formal Verification Matrix & Evidence

| Test Verification Gate | Scope & Empirical Observation | Status |
| :--- | :--- | :---: |
| **Test 1: IP Bit-Exact Pipeline** | $6,400 / 6,400$ updates match exactly across MAC, bias, sum, and tanh in/out stages. | **Met** |
| **Test 2: IP Interfaces on Board** | Hardware AXI4-Lite registers and AXI4-Stream streaming interfaces: $64 / 64$ outputs bit-exact. | **Met** |
| **Test 3: Application on Board** | Held-out cells B0018 and B0047: ESN, EKF, and UKF hardware outputs match Python software twin. | **Met** |
| **Test 4: Application SOC vs EKF** | No statistically significant difference from rated-capacity EKF ($p = 0.51$, Wilcoxon); measured-capacity EKF superior ($p = 0.011$). | **Partly Met** |

#### `10` Conclusions & Future Scope
* **Achieved (Silicon IP):** A truly reusable, task-independent ESN IP core with runtime-programmable weights, occupying only **318 LUTs** on Artix-7, proven 100% bit-exact in simulation and on physical silicon across AXI4-Lite and AXI4-Stream.
* **Achieved (Battery Application):** Reached **$0.067$ SOC MAE** across 29 held-out aging cells without any prior capacity knowledge, providing a per-cell error variance **$1.7\times$ to $2.8\times$ lower** than classical EKF baselines.
* **Identified Limitations:** Offline validation on recorded NASA dataset; EKF with ground-truth measured capacity retains higher absolute accuracy; empirical SOH readout is exploratory.
* **Future Work:** Multi-task reservoir reuse on identical bitstreams, live hardware-in-the-loop (HIL) battery testbench integration, and expanded operating temperature characterization down to $-20^\circ\text{C}$.

#### `11` References & Project Repository Access
* **[1]** H. Jaeger and H. Haas, *"Harnessing Nonlinearity: Predicting Chaotic Systems and Saving Energy in Wireless Communication,"* *Science*, vol. 304, no. 5667, pp. 78–80, 2004.
* **[2]** G. L. Plett, *"Extended Kalman filtering for battery management systems of LiPB-based HEV battery packs,"* *Journal of Power Sources*, vol. 134, no. 2, pp. 277–292, 2004.
* **[3]** B. Saha and K. Goebel, *"Battery Data Set,"* NASA Ames Prognostics Data Repository, NASA Ames Research Center, Moffett Field, CA, 2007.
* **Open-Source Repository:** [`https://github.com/tanish-jain-225/Battery_State_Estimator_BE_Project_2026_2027`](https://github.com/tanish-jain-225/Battery_State_Estimator_BE_Project_2026_2027)

---

## 🔁 Verification & Integrity Check

To verify the PDF integrity locally:
```bash
# Verify file presence and byte size (~535 KB)
ls -lh docs/Poster/Project_Poster.pdf

# Verify PDF page count (2 pages)
python -c "import pypdf; reader = pypdf.PdfReader('docs/Poster/Project_Poster.pdf'); print(f'Pages: {len(reader.pages)}')"
```
