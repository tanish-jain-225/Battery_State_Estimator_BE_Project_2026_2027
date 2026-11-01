# Changelog

All notable changes to the **Battery State Estimator** project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v2.2.0] - 2026-11-01 (Autonomous Pub/Sub Decoupling & Document Safeguards Release)

### 🚀 Highlights (v2.2.0)
- **Autonomous Microservice Decoupling**: Completely decoupled Physics Simulator and Visualiser via MongoDB Atlas singleton state and telemetry pub/sub. The Simulator writes telemetry at 1.0s cadence and auto-prunes records older than the latest 1,000 samples ($O(1)$ indexed scans). The Visualiser independently polls for new readings every 1.0s without HTTP ping coupling or duplicate physics generators.
- **Document Builder Safety Protection**: Implemented non-destructive guards across all ReportLab PDF generators in [`scripts/build_project_documents.py`](scripts/build_project_documents.py), ensuring existing custom PDFs (>10 KB) are strictly preserved while still supporting clean builds and opt-in `--force` regeneration.
- **Expanded Pytest Regression Suite**: Expanded automated suite to **107 passing tests** across 14 test modules (100% pass rate in ~77s) with 94% coverage on `software/shared`, including regression tests for PDF preservation and zero-load database access.

---

## [v2.1.0] - 2026-11-01 (Publications, Poster & Academic Architecture Release)

### 🚀 Highlights (v2.1.0)
- **Comprehensive Test Suite Expansion**: Expanded automated pytest regression suite from 62 to **104 passing tests** across 14 test modules (100% pass rate) covering document compilation, advanced estimator pipeline priming/hybrid observers, comprehensive Flask REST APIs, FPGA COE parser/extended CLI, and hardware CSR/quantization edge training.
- **Strict Warning-Free C99 Compilation**: Resolved GCC `-Wtype-limits` and `-Wunused-parameter` warnings under `-Wall -Wextra -pedantic -std=c99` with full MISRA-C compliance.
- **Pipeline Safe Self-Sufficiency**: Added `create_with_model()`, `load_saved_model()` and `PipelineSafeUnpickler` to `EstimatorPipeline` enabling zero-configuration model loading and robust NumPy 1.x / 2.x interoperability.
- **Microservice Isolation**: Enforced fully-qualified package namespaces across `software.visualiser`, `software.shared`, and `hardware.STM_Verifier` preventing configuration cross-shadowing.
- **Academic Publication Architecture**: Restructured the repository to host dedicated publication, poster, and verification directories (`docs/Poster/`, `docs/Publications/`, `docs/Paper_Proof/`).
- **Capstone Presentation Poster**: Generated official high-resolution vector exhibition poster ([`Project_Poster.pdf`](docs/Poster/Project_Poster.pdf)) adhering to A1 exhibition board standards.
- **Preprint Paper Deliverables**: Built publication-grade preprint PDFs for both the Comprehensive Review Paper ([`Review_Paper.pdf`](docs/Publications/Review_Paper.pdf)) and the Original Experimental Research Paper ([`Research_Paper.pdf`](docs/Publications/Research_Paper.pdf)).
- **Automated Document Generator**: Added [`scripts/build_project_documents.py`](scripts/build_project_documents.py) utilizing ReportLab to programmatically generate vector IEEE and poster assets.
- **Evaluation Proofs Registry**: Scaffolded [`docs/Paper_Proof/README.md`](docs/Paper_Proof/README.md) establishing the 20 Marks evaluation tracking protocol (10 Marks submission proof + 10 Marks acceptance letter).
- **Open-Source & Academic Governance Suite**: Added official open-source [`LICENSE`](LICENSE) (MIT License with academic attribution clause), [`AUTHORS.md`](AUTHORS.md) (comprehensive team, guide, coordinator, and VESIT institutional credits), [`CITATION.cff`](CITATION.cff) (GitHub-native BibTeX and APA citation metadata), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), and [`SECURITY.md`](SECURITY.md) (vulnerability disclosure and secrets policy).

---

## [v2.0.0] - 2026-10-10 (Review 2 Milestone Deliverable)

### 🚀 Highlights (v2.0.0)
- **Online ESN Adaptation**: Integrated Recursive Least Squares (RLS) adaptive readout filter reducing dynamic SOC tracking error to $<0.8\%$ under battery aging.
- **UKF Non-Linear Benchmark**: Added Unscented Kalman Filter with Merwe scaled transform as a rigorous non-linear baseline.
- **Embedded C99 CSR SpMV Acceleration**: MISRA-C compliant dual-mode firmware (Float32 vs Fixed-Point Q15) delivering a **6.7× inference speedup** and saving 82.4% RAM.
- **100-Neuron Artix-7 FPGA RTL**: Bit-exact stage parity (**200/200 matched evaluations**) between Vivado XSim and Python golden model; 0 DSP48 slices and 77 LUTs utilization at 0.099 W.
- **NASA Aging Dataset Cross-Validation**: Evaluated across 32 cycles (2,048 timesteps) with Test SOC $R^2 = 0.8783$ beating classical EKF (0.7818).
- **Automated Verification**: Expanded test suite to **62 automated unit/integration tests (100% pass rate in ~80s)** and master 8-step cross-platform validation runner (`run_all_validation.bat` / `.sh`).
- **Academic Manuscripts**: Authored 29-page Neuromorphic BMS review manuscript (11 sections, 90+ citations) and original experimental research paper for IEEE / Q3 Scopus targets.

### 🌟 Added
- **Online Adaptive ESN**: Formulation and unit tests in `software/visualiser/training/train_rc.py` and `tests/test_online_training.py`.
- **UKF Implementation**: Merwe sigma-point formulation in `software/visualiser/traditional_estimator.py` and `tests/test_traditional_estimator.py`.
- **Variable Forgetting Factor RLS (VFF-RLS)**: Dynamic identification of $R_0, R_1, C_1$ parameters under current steps.
- **Fixed-Point Arithmetic Engine**: Q12 input / Q15 weight fixed-point datapath with a 33-point linear interpolated $\tanh$ lookup table (`q15_tanh`) in `hardware/STM_Verifier/main.c`.
- **ARM Cortex-M4 Cross-Compilation**: `hardware/STM_Verifier/Makefile.arm` targeting STM32F4/F7 bare-metal and RTOS deployments.
- **Multi-Timestep Addressing in Verilog RTL**: `u_addr = (timestep * N_IN) + u_neuron_idx` in `hardware/FPGA_Verifier/esn_top.v` and `tb_esn_top_tiny.v`.
- **Double-Buffered State Memory**: Ping-pong BRAM architecture preventing Gauss-Seidel read-after-write hazards in FPGA datapath.
- **Comprehensive Outcomes Evaluator**: `hardware/FPGA_Verifier/eval_fpga_outcomes.py` checking parity, X-corruption, and synthesis closure.
- **Automated CI/CD**: `.github/workflows/ci.yml` running linting, test suites, and validation scripts on Ubuntu and Windows.
- **Academic Manuscripts**: `reference/review_paper.md` and `reference/paper.md` targeting IEEE Transactions and Q3 Scopus journals.
- **Review 2 Deliverables**: Slide deck `docs/Review_2/Review_2_PPT.pdf` and progress report `docs/Review_2/Review_2_Progress.md`.

### 🔄 Changed
- **Shared Physics Library**: Unified `software/shared/battery_simulator.py` and `software/shared/battery_chemistry.py` across microservices.
- **Estimator Pipeline Hydration**: Preserved UKF covariance (`ukf_p`) and states (`ukf_soc`, `ukf_v1`, `ukf_v2`) during catch-up deserialization.
- **CSV Encoding Standardization**: Enforced `utf-8-sig` across all data loaders to eliminate Windows PowerShell BOM headers.
- **Documentation Overhaul**: Synchronized all 19 repository markdown documents with verified Review 2 figures and department timelines.

### 🐛 Fixed
- **COE Radix-16 Parsing**: Added two's complement sign conversion for negative hexadecimal values in `parse_coe_file()`.
- **Controller Edge Detection**: Switched buffer swapping from level-sensitive `done` to single-cycle edge `done_pulse` to eliminate ping-pong corruption.
- **Golden Reference Separation**: Split tiny sequence test to `golden_tiny.csv` and full 100-neuron model to `golden_results.csv`, preventing file clobbering.

---

## [v1.0.0] - 2026-09-21 (Review 1 Baseline Deliverable)

### 🚀 Highlights (v1.0.0)
- **2-RC Electro-Thermal Simulator**: Baseline simulation engine supporting UDDS driving profiles, OCV lookups, and thermal dynamics.
- **Baseline Observers**: Initial implementation of Extended Kalman Filter (EKF), Coulomb Counting, and Resistance SOH observer.
- **Proof-of-Concept ESN**: 50-neuron offline-trained Echo State Network for SOC estimation.
- **Web Dashboard**: Flask REST backend and Chart.js frontend for real-time visualization.
- **Initial Embedded & RTL Design**: Baseline dense C99 runtime and preliminary single-step Verilog ESN module.
