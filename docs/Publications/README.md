# Academic Publications & Manuscripts

[← Back to Main Repository](../../README.md) · [← Capstone Thesis](../Thesis/README.md) · [Submission Proofs (20 Marks)](../Paper_Proof/README.md) · [Project Poster](../Poster/README.md)

---

**Project Mentor:** Dr. Kadambari Sharma  
**Project Guide / Coordinator:** Mr. Gopalkrishnan Narayan  
**Department:** Department of Automation and Robotics / Instrumentation, VESIT, Mumbai  

> [!IMPORTANT]
> **Active Deliverables Status (2 of 4 Finalized — 2 Pending):**  
> While the codebase, models, firmware, RTL, bitstream, and 119 automated tests are **100% complete and passing**, both [`Research_Paper.pdf`](Research_Paper.pdf) (6 pages, 674 KB encrypted, IEEE camera-ready) and [`Review_Paper.pdf`](Review_Paper.pdf) (12 pages, 231 KB, 77 references, Elsevier camera-ready) have been **fully finalized, compiled, and integrated**. [`Project_Poster.pdf`](../Poster/Project_Poster.pdf) and [`Final_Thesis.pdf`](../Thesis/Final_Thesis.pdf) currently remain as the only **2 pending** deliverables awaiting final drop-in for the v2.4.1 turnkey release.  

---

## 🎓 Overview & Evaluation Policy

As part of the BE Capstone project evaluation criteria, **20 Marks** are strictly allocated to peer-reviewed publication deliverables:
* **10 Marks:** Verified proof of manuscript submission (submission receipt and tracking Paper ID).
* **10 Marks:** Official proof of paper publication acceptance.

Target venues are peer-reviewed **IEEE Transactions / Q3 Scopus-Indexed Journals** and **Elsevier / ScienceDirect Review Journals**.

---

## 📑 Tracked Manuscripts & Deliverables

| Target Paper | Focus / Scope | PDF Deliverable | Markdown Manuscript | Target Venue | Evaluation Marks | Deliverable Status |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: |
| **Paper 1: Comprehensive Review** | Hardware architectures for learned battery SOC estimation: recurrent & reservoir computing accelerators vs BMS requirements (8 SOC & 6 FPGA implementations, 77 citations) | [`Review_Paper.pdf`](Review_Paper.pdf) | [`docs/Review_2/Outcomes/Neuromorphic-BMS-Review-Paper-Draft.pdf`](../Review_2/Outcomes/Neuromorphic-BMS-Review-Paper-Draft.pdf) | Elsevier / ScienceDirect / Q3 Scopus Review Journal | 10 Marks (Submission) + 10 Marks (Acceptance) | **Completed & Camera-Ready Integrated (Deliverable 2 of 4)** |
| **Paper 2: Original Experimental Research** | Bit-exact fixed-point FPGA ESN reservoir (Q6.10), 2,201 NASA PCoE windows, 29-cell cross validation, Artix-7 RTL | [`Research_Paper.pdf`](Research_Paper.pdf) | [`reference/paper.md`](../../reference/paper.md) | IEEE / Q3 Scopus Journal on Industrial Electronics / CPS | 10 Marks (Submission) + 10 Marks (Acceptance) | **Completed & Camera-Ready Integrated (Deliverable 1 of 4)** |

---

## 📄 Target Paper 1: Comprehensive Review Paper

* **Title:** *Hardware architectures for learned battery state-of-charge estimation: A review of recurrent and reservoir computing accelerators against battery management requirements*
* **Authors:** Akshay Nambiar, Satvik Verma, Tanish Sanghvi, Sanjna Patankar, Kadambari Sharma, and Sangeetha Prasanna Ram
* **Affiliation:** Department of Automation and Robotics, VES Institute of Technology, Mumbai, India
* **Format:** Elsevier / ScienceDirect 2-Column Camera-Ready PDF (12 Pages, 231 KB, 77 References)
* **Status:** **Completed & Integrated (Deliverable 2 of 4 Finalized)**
* **Scope & Highlights:**
  * Examines hardware architectures for learned battery SOC estimation and judges trade-offs against BMS requirements.
  * Connects three literatures: data-driven SOC estimation, FPGA recurrent-network accelerators, and reservoir computing.
  * Side-by-side comparison of 8 embedded/hardware SOC implementations and 6 FPGA recurrent-network accelerators.
  * Systematic analysis of arithmetic and storage cost per sample, fixed-point error in recurrent state, and BMS timing headroom.
  * Formulates a reporting checklist and research agenda for reproducible learned battery hardware estimators.
* **Deliverable Files:**
  * Camera-Ready PDF: [`Review_Paper.pdf`](Review_Paper.pdf) (12 Pages, 231 KB, 77 Citations)
  * Milestone Outcome Draft: [`docs/Review_2/Outcomes/Neuromorphic-BMS-Review-Paper-Draft.pdf`](../Review_2/Outcomes/Neuromorphic-BMS-Review-Paper-Draft.pdf) (29 Pages)

---

## 📄 Target Paper 2: Original Experimental Research Paper

* **Title:** *A Bit-Exact Fixed-Point FPGA Echo State Network for Lithium-Ion Battery SOC Estimation with an Exploratory SOH Readout*
* **Authors:** Akshay Nambiar, Sanjna Patankar, Satvik Verma, Tanish Sanghvi, Kadambari Sharma, and Nilima Warke
* **Affiliation:** Department of Automation and Robotics / Instrumentation, VESIT, Mumbai, India
* **Format:** IEEE Transactions / Conference 2-Column Camera-Ready PDF (6 Pages, 668 KB)
* **Status:** **Completed & Integrated (Deliverable 1 of 4 Finalized)**
* **Scope & Highlights:**
  * Non-spiking, fixed-point ESN (Q6.10 reservoir) with closed-form ridge readouts in Q4.14 for SOC with an exploratory SOH readout.
  * **Resource-Efficient Artix-7 Implementation:** One time-multiplexed multiply-accumulate (MAC) core, BRAM weights, double-buffered state memory, and lookup-table tanh using **318 LUTs and 2 DSP slices** closing timing at 80 MHz.
  * **Bit-Exact Verification:** 100% verified against an independent golden model across all 5 datapath stages in simulation (6,400 updates) and on programmed Digilent Arty A7-100T hardware.
  * **29-Cell Cross-Validation:** Evaluated on **2,201 discharge windows (140,864 held-out steps)** across 29 NASA PCoE cells (4°C–44°C) with each evaluation cell held out in turn.
  * **Superior Cross-Cell Consistency:** Achieves SOC MAE 0.067, RMSE 0.086 with **1.7–2.8× lower inter-cell standard deviation** of per-cell MAE than EKF configurations ($p \le 0.007$).
* **Deliverable Files:**
  * Camera-Ready IEEE PDF: [`Research_Paper.pdf`](Research_Paper.pdf) (668 KB, 6 Pages)
  * Markdown Reference Manuscript: [`reference/paper.md`](../../reference/paper.md)
  * FPGA RTL Verification Report: [`docs/Review_2/Outcomes/FPGA-Based-Echo-State-Network-for-Battery-SOC-SOH-Estimation-Outcomes.pdf`](../Review_2/Outcomes/FPGA-Based-Echo-State-Network-for-Battery-SOC-SOH-Estimation-Outcomes.pdf)

---

## 🔁 Updating or Replacing Deliverables

When camera-ready PDFs are compiled from LaTeX (Overleaf) or IEEE Word templates:
1. Drop the finalized compiled [`Review_Paper.pdf`](Review_Paper.pdf) into `docs/Publications/` ([`Research_Paper.pdf`](Research_Paper.pdf) is already camera-ready integrated).
2. Log official submission acknowledgement emails or tracking letters in [`docs/Paper_Proof/`](../Paper_Proof/README.md).

