# Master Documentation Hub

[← Back to Main Repository](../README.md) · [Review 1](Review_1/Review_1_Progress.md) · [Review 2](Review_2/Review_2_Progress.md) · [FPGA IP Block](../hardware/IP_Block/README.md) · [Capstone Thesis](Thesis/README.md) · [Publications](Publications/README.md)

---

## 🧭 Master Documentation Directory

Welcome to the central documentation index for the **Battery State Estimator: An ESN-Based Alternative to EKF and Coulomb Counting** BE Capstone project (VESIT 2026–2027).

This repository's documentation is engineered to follow a clear, continuous **Story and Developmental Flow** across four integrated streams:

```
docs/
├── Poster/                        # Academic Exhibition & Defense Poster
│   ├── Project_Poster.pdf         # Formatted Presentation Poster PDF
│   └── README.md                  # Layout specifications and print guidelines
├── Thesis/                        # B.E. Capstone Final Dissertation
│   ├── Final_Thesis.pdf           # Dissertation Document Shell (A4 Portrait)
│   └── README.md                  # University format specs and chapter breakdown
├── Publications/                  # Official Academic Paper Deliverables
│   ├── Research_Paper.pdf         # Original Experimental Research Paper (IEEE Target)
│   ├── Review_Paper.pdf           # Comprehensive Review Paper (29 Pages, 11 Sections)
│   └── README.md                  # Publication abstracts, authorship, and scopes
├── Paper_Proof/                   # 20 Marks Evaluation Submission/Acceptance Records
│   └── README.md                  # Proof logging registry & mark criteria checklist
├── Review_1/                      # Review 1 Milestone Documentation
│   ├── Review_1_PPT.pdf           # Milestone 1 Presentation Slides
│   └── Review_1_Progress.md       # Scope, initial 2-RC model, and preliminary results
├── Review_2/                      # Review 2 Milestone Documentation
│   ├── Review_2_PPT.pdf           # Milestone 2 Presentation Slides (16:9 Widescreen)
│   ├── Review_2_Progress.md       # End-to-end milestone report (10/10 Verification)
│   └── Outcomes/                  # Validated deliverables and evaluation reports
│       ├── FPGA-Based-Echo-State-Network-...pdf
│       └── Neuromorphic-BMS-Review-Paper-Draft.pdf
├── Resources/                     # Engineering Guides & Technical References
│   ├── ARTIFACTS.md               # Model parameters and dataset versioning policy
│   ├── DEMO_CHECKLIST.md          # 10-minute presentation & viva defense checklist
│   ├── DEPLOY_RENDER.md           # Cloud deployment runbook for Render.com
│   ├── OPERATIONS.md              # Local execution runbook & port configurations
│   ├── PRESENTATION.md            # Defense slide talking points & speaker notes
│   ├── PROJECT_PROPOSAL.md        # Official BE project proposal & methodology
│   ├── SYSTEM_SPECIFICATION.md    # Circuit parameters, sensor noise & observer math
│   └── WEB_RESEARCH.md            # Automotive BMS landscape & ISO 26262 audit
└── literature_survey.md           # Detailed literature survey & academic taxonomy
```

---

## 🌊 The Four Documentation Streams (Story & Development Flow)

### 1. 📖 The Scientific Story Stream
*Foundations, literature synthesis, and mathematical formulations:*
1. **Academic Literature Survey:** [`docs/literature_survey.md`](literature_survey.md) — Comprehensive survey of SNNs, Reservoir Computing, and BMS edge limits.
2. **System Specification:** [`docs/Resources/SYSTEM_SPECIFICATION.md`](Resources/SYSTEM_SPECIFICATION.md) — Mathematical formulas, 2-RC state equations, noise models, and observer matrices.
3. **Industrial Landscape & ISO 26262 Audit:** [`docs/Resources/WEB_RESEARCH.md`](Resources/WEB_RESEARCH.md) — Commercial automotive BMS benchmark against TI, NXP, Analog Devices, and AutoSAR standards.
4. **Tracked Model Weights & Datasets:** [`docs/Resources/ARTIFACTS.md`](Resources/ARTIFACTS.md) — Artifact registry for NASA PCoE datasets, COE files, and C weight headers.

### 2. 🚀 The Developmental Milestones Stream
*Chronological evolution from proposal through defense:*
1. **Project Proposal (Aug 2026):** [`docs/Resources/PROJECT_PROPOSAL.md`](Resources/PROJECT_PROPOSAL.md) — Initial project problem statement, objectives, and departmental submission.
2. **Review 1 Defense (Sep 2026):** [`docs/Review_1/Review_1_Progress.md`](Review_1/Review_1_Progress.md) · [Slide Deck](Review_1/Review_1_PPT.pdf) — Baseline 2-RC physics, initial EKF & Coulomb Counting, C99 CSR logic.
3. **Review 2 Defense (Nov 2026):** [`docs/Review_2/Review_2_Progress.md`](Review_2/Review_2_Progress.md) · [16:9 Deck](Review_2/Review_2_PPT.pdf) · [FPGA Outcomes Report](Review_2/Outcomes/FPGA-Based-Echo-State-Network-for-Battery-SOC-SOH-Estimation-Outcomes.pdf) — Online RLS adaptation, UKF benchmark, 200/200 bit-exact FPGA parity, and NASA 32-cycle evaluation.
4. **Hardware Acceleration & Commercial IP Block (v2.3.0):** [`hardware/IP_Block/README.md`](../hardware/IP_Block/README.md) — IEEE 1685 IP-XACT AXI4 IP block, ready-to-flash 3.7 MB bitstream, and 115200-baud UART HIL interface.
5. **Final B.E. Capstone Dissertation (v2.3.1):** [`docs/Thesis/Final_Thesis.pdf`](Thesis/Final_Thesis.pdf) · [Thesis Guide](Thesis/README.md) — Official University of Mumbai / VESIT 8-chapter capstone thesis.

### 3. ⚙️ The Engineering & Software Stream
*Implementation, algorithms, and verification harnesses:*
1. **Software Subsystem Architecture:** [`software/software.md`](../software/software.md) — Complete overview of Flask microservices, decoupled MongoDB pub/sub, and estimator pipeline.
2. **Physics Simulator Guide:** [`software/simulator/simulator.md`](../software/simulator/simulator.md) — 2-RC ECM transient dynamics, thermal solver, and fault injection API.
3. **Visualiser & Estimator Pipeline Guide:** [`software/visualiser/visualiser.md`](../software/visualiser/visualiser.md) — Multi-observer comparative engine (ESN vs EKF vs UKF vs CC).
4. **Hardware Subsystem Architecture:** [`hardware/hardware.md`](../hardware/hardware.md) — Comprehensive guide to embedded C99 firmware and FPGA Verilog accelerators.
5. **STM32 Embedded C99 Verifier:** [`hardware/STM_Verifier/README.md`](../hardware/STM_Verifier/README.md) — CSR SpMV 6.7× speedup, Q12/Q15 integer arithmetic, and LUT Tanh.
6. **FPGA RTL Verifier & Subsystems:** [`hardware/FPGA_Verifier/README.md`](../hardware/FPGA_Verifier/README.md) — Bit-exact Verilog RTL for 100-neuron ESN, fixed-point EKF, and fixed-point UKF.
7. **Automated Regression Suite (115 Tests):** [`tests/README.md`](../tests/README.md) — 15 specialized test modules with 94.49% coverage across physics, estimators, and hardware.

### 4. 🎓 The Defense & Academic Marks Stream
*Exhibition, presentation, and university evaluation criteria:*
1. **Academic Publications Hub (20 Marks):** [`docs/Publications/README.md`](Publications/README.md)
   * **Experimental Research Paper:** [`docs/Publications/Research_Paper.pdf`](Publications/Research_Paper.pdf) (Authored IEEE Preprint)
   * **Comprehensive Review Paper:** [`docs/Publications/Review_Paper.pdf`](Publications/Review_Paper.pdf) (29 Pages, 11 Sections, 90+ Citations)
2. **Publication Proofs & Evaluation Registry (20 Marks):** [`docs/Paper_Proof/README.md`](Paper_Proof/README.md) — 10 Marks submission receipt + 10 Marks acceptance letter tracking.
3. **Academic Exhibition Poster:** [`docs/Poster/Project_Poster.pdf`](Poster/Project_Poster.pdf) · [Poster Guide](Poster/README.md) — Official A1 symposium poster.
4. **Live Viva Demo Checklist:** [`docs/Resources/DEMO_CHECKLIST.md`](Resources/DEMO_CHECKLIST.md) — 10-minute presentation and demonstration walkthrough.
5. **Speaker Notes & Defense Talking Points:** [`docs/Resources/PRESENTATION.md`](Resources/PRESENTATION.md) — Comprehensive slide-by-slide script for Review viva.

---

## 🏛️ Governance, Attribution & Compliance

* **Open-Source License:** [`LICENSE`](../LICENSE) (MIT License with academic citation clause)
* **Authors & Mentors:** [`AUTHORS.md`](../AUTHORS.md) (Detailed team, guide, and institutional ownership)
* **Academic Citation File:** [`CITATION.cff`](../CITATION.cff) (Machine-readable BibTeX / APA citation metadata)
* **Contributing Guidelines:** [`CONTRIBUTING.md`](../CONTRIBUTING.md) (Code standards and PR guidelines)
* **Security & Failsafe Policy:** [`SECURITY.md`](../SECURITY.md) (Vulnerability reporting and credential policy)
* **Code of Conduct:** [`CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) (Scientific integrity and community standards)
