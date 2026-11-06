# Academic Publications & Manuscripts

[← Back to Main Repository](../../README.md) · [← Capstone Thesis](../Thesis/README.md) · [Submission Proofs (20 Marks)](../Paper_Proof/README.md) · [Project Poster](../Poster/README.md)

---

**Project Mentor:** Dr. Kadambari Sharma  
**Project Guide / Coordinator:** Prof. Gopalkrishnan Narayan  
**Department:** Department of Automation and Robotics / Instrumentation, VESIT, Mumbai  

---

## 🎓 Overview & Evaluation Policy

As part of the BE Capstone project evaluation criteria, **20 Marks** are strictly allocated to peer-reviewed publication deliverables:
* **10 Marks:** Verified proof of manuscript submission (submission receipt and tracking Paper ID).
* **10 Marks:** Official proof of paper publication acceptance.

Target venues are peer-reviewed **IEEE Transactions / Q3 Scopus-Indexed Journals**.

---

## 📑 Tracked Manuscripts & Deliverables

| Target Paper | Focus / Scope | PDF Deliverable | Markdown Manuscript | Target Venue | Evaluation Marks |
| :--- | :--- | :---: | :---: | :--- | :---: |
| **Paper 1: Comprehensive Review** | Neuromorphic computing, SNNs, Reservoir Computing, Liquid State Machines & Edge AI for BMS | [`Review_Paper.pdf`](Review_Paper.pdf) | [`docs/Review_2/Outcomes/Neuromorphic-BMS-Review-Paper-Draft.pdf`](../Review_2/Outcomes/Neuromorphic-BMS-Review-Paper-Draft.pdf) | IEEE Transactions / Q3 Scopus Review Journal | 10 Marks (Submission) + 10 Marks (Acceptance) |
| **Paper 2: Original Experimental Research** | Edge-optimized CSR SpMV ESN, 2-RC cyber-physical simulator, Q15 fixed-point LUT, 200/200 FPGA Verilog RTL | [`Research_Paper.pdf`](Research_Paper.pdf) | [`reference/paper.md`](../../reference/paper.md) | IEEE / Q3 Scopus Journal on Industrial Electronics / CPS | 10 Marks (Submission) + 10 Marks (Acceptance) |

---

## 📄 Target Paper 1: Comprehensive Review Paper

* **Title:** *Neuromorphic Computing for Intelligent Battery Management Systems: A Comprehensive Review of Spiking Neural Networks, Reservoir Computing and Edge AI*
* **Authors:** Sanjna Patankar, Akshay Nambiar, Satvik Verma, Tanish Sanghvi, and Kadambari Sharma
* **Affiliation:** Department of Automation and Robotics / Instrumentation, VESIT, Mumbai, India
* **Scope & Highlights:**
  * 11 comprehensive sections spanning 29 pages and 90+ cited state-of-the-art papers.
  * Traces evolution from classical Coulomb counting and Kalman filters (EKF, UKF) through deep learning (LSTM, CNN, Transformers).
  * In-depth analysis of neuromorphic silicon platforms: Intel Loihi 2, SpiNNaker2, BrainChip Akida, IBM TrueNorth, and FPGA accelerators.
  * Formulates a multi-dimensional benchmarking taxonomy across inference energy, latency, parameter complexity, and cross-chemistry robustness.
* **Deliverable Files:**
  * Formatted Preprint PDF: [`Review_Paper.pdf`](Review_Paper.pdf)
  * Milestone Outcome PDF: [`docs/Review_2/Outcomes/Neuromorphic-BMS-Review-Paper-Draft.pdf`](../Review_2/Outcomes/Neuromorphic-BMS-Review-Paper-Draft.pdf)

---

## 📄 Target Paper 2: Original Experimental Research Paper

* **Title:** *A Bit-Exact Fixed-Point FPGA Echo State Network Reservoir for Lithium-Ion Battery SOC and SOH Estimation*
* **Authors:** Akshay Nambiar, Satvik Verma, Tanish Sanghvi, Sanjna Patankar, Kadambari Sharma, and Nilima Warke
* **Affiliation:** Department of Automation and Robotics / Instrumentation, VESIT, Mumbai, India
* **Scope & Highlights:**
  * Co-designed cyber-physical system integrating a 2-RC electro-thermal model, multi-timescale EKF, and continuous-time Leaky ESN.
  * **6.7× Execution Speedup** on ARM Cortex-M microcontrollers via Compressed Sparse Row (CSR) matrix storage.
  * **~10 KB Flash Memory Savings** achieved through sparse integer representation.
  * **98.40% Thermal Safety Accuracy** under dynamic drive cycles using Q15 fixed-point arithmetic and a 256-word tanh lookup table.
  * **200/200 Bit-Exact Verification** on Xilinx Artix-7 FPGA Verilog RTL against Python golden reference models.
* **Deliverable Files:**
  * Formatted Preprint PDF: [`Research_Paper.pdf`](Research_Paper.pdf)
  * Markdown Manuscript: [`reference/paper.md`](../../reference/paper.md)
  * FPGA RTL Verification Report: [`docs/Review_2/Outcomes/FPGA-Based-Echo-State-Network-for-Battery-SOC-SOH-Estimation-Outcomes.pdf`](../Review_2/Outcomes/FPGA-Based-Echo-State-Network-for-Battery-SOC-SOH-Estimation-Outcomes.pdf)

---

## 🔁 Updating or Replacing Deliverables

When camera-ready PDFs are compiled from LaTeX (Overleaf) or IEEE Word templates:
1. Replace [`Review_Paper.pdf`](Review_Paper.pdf) and [`Research_Paper.pdf`](Research_Paper.pdf) with your compiled IEEE PDFs.
2. Log official submission acknowledgement emails or tracking letters in [`docs/Paper_Proof/`](../Paper_Proof/README.md).

