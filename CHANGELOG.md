# Changelog

All notable changes to the **Battery State Estimator** project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v2.3.1] - Planned / Tomorrow (2026-11-04) (Final Academic Deliverables Release)

### 🎯 Scope & Planned Deliverables
- **Academic Review Paper**: Replacing [`docs/Publications/Review_Paper.pdf`](docs/Publications/Review_Paper.pdf) with the finalized, peer-reviewed 11-section survey manuscript targeting IEEE Potentials / IEEE Transactions on Transportation Electrification.
- **A1 Presentation Poster**: Replacing [`docs/Poster/Project_Poster.pdf`](docs/Poster/Project_Poster.pdf) with the finalized high-resolution 300 DPI vector exhibition poster adhering to official VESIT symposium guidelines.
- **Review 2 Defense Slide Deck**: Replacing [`docs/Review_2/Review_2_PPT.pdf`](docs/Review_2/Review_2_PPT.pdf) with the finalized 26-slide capstone milestone presentation deck.
- **Milestone Completeness**: 100% turn-key academic and engineering closure with zero remaining document shells.

---

## [v2.3.0] - 2026-11-03 (Active Today - Plug-and-Play FPGA ESN IP Block & Real Research Paper Release)

### 🚀 Highlights (v2.3.0)
- **Plug-and-Play FPGA ESN IP Block**: Added the complete commercial-grade [`hardware/IP_Block/`](hardware/IP_Block/) package featuring:
  - **Reusable AXI4 IP Module (`esn_axi_ip.v`)**: Packaged compliant with IEEE 1685 IP-XACT standard in [`component.xml`](hardware/IP_Block/component.xml) under taxonomy `/UserIP` (`vesit.ac.in:user:esn_axi_ip:1.0`), supporting AXI4-Lite memory-mapped control and AXI4-Stream data streaming.
  - **Concurrent Tri-Observer FPGA Platform (`esn_platform_top.v`)**: Concurrently executes 100-neuron ESN, 512-point Fixed-Point EKF, and 512-point Fixed-Point UKF in parallel on incoming UART telemetry (115200 baud).
  - **Runtime Weight & Table Reconfigurability**: Supports arbitrary cell chemistries and ESN models without resynthesizing bitstreams.
  - **Pre-Compiled Ready-to-Program Bitstream (`esn_platform_top.bit`)**: 3.7 MB bitstream ready to flash directly to the Digilent Arty A7-100T FPGA board (`xc7a100tcsg324-1`).
  - **C Driver & Host CLI**: Embedded C driver API (`esn_ip.h`, `esn_ip_example.c`) and Python streaming testbench CLI (`esn_host.py`).
  - **Repository Footprint Optimization**: Purged intermediate Vivado compilation checkpoints (`.dcp`) and binary reports (`.rpx`), saving 36.7 MB while preserving all source RTL, testbenches, constraints, and synthesis reports.
- **Academic Research Paper Integration**: Formally integrated the authored IEEE-formatted Research Paper into [`docs/Publications/Research_Paper.pdf`](docs/Publications/Research_Paper.pdf) (1.8 MB), with Review Paper, Poster, and Review 2 PPT shells positioned for final updates.
- **Automated IP Block Verification Suite**: Added [`tests/test_ip_block.py`](tests/test_ip_block.py) validating IEEE 1685 component XML integrity, weight pack ingestion, bit-exact twin execution, and golden readout parity, expanding the test suite to **115 passing tests** (100% pass rate in ~66s).

---

## [v2.2.0] - 2026-11-01 (Autonomous Pub/Sub Decoupling & Document Safeguards Release)

### 🚀 Highlights (v2.2.0)
- **Autonomous Microservice Decoupling**: Completely decoupled Physics Simulator and Visualiser via MongoDB Atlas singleton state and telemetry pub/sub. The Simulator writes telemetry at 1.0s cadence and auto-prunes records older than the latest 1,000 samples ($O(1)$ indexed scans). The Visualiser independently polls for new readings every 1.0s without HTTP ping coupling or duplicate physics generators.
- **Academic Asset Protection**: Purged legacy testing scripts and automated document generator to strictly safeguard manually authored academic deliverables (`Research_Paper.pdf`, `Review_Paper.pdf`, and `Project_Poster.pdf`) against automated overwrites.
- **Expanded Pytest Regression Suite**: Automated suite validated with **110 passing tests** across 14 test modules (100% pass rate in ~77s) with 94.5% coverage on `software/shared`, including full bit-exact testbenches for Fixed-Point EKF and UKF FPGA accelerator cores and zero-load database access.

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
- **Document Deliverables**: Included publication-grade preprint vector IEEE and poster assets.
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
