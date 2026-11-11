# Changelog

All notable changes to the **Battery State Estimator** project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v2.4.0] - 2026-11-11 (Active & Synced Today - IP Block v1.2, IEEE Research Paper, Optimization & Decoupled Sync)

### 🚀 Highlights (v2.4.0)
- **Decoupled MongoDB 1.0s Real-Time Intermediate Pipeline**:
  - Locked simulator state heartbeat to strict 1.0s stepping (`time.monotonic()` target stepping eliminating clock drift).
  - Sub-millisecond indexed delta telemetry queries (`readings.find({'time': {'$gt': prev_time}})` in $< 0.5\,\text{ms}$) via MongoDB B-Tree index on `time`.
  - Zero-latency simulation reset synchronization in `software/visualiser/app.py` catching resets in the exact same polling cycle.
  - Persistent HTTP Keep-Alive connection pooling via singleton `requests.Session()` and Gunicorn `keepalive = 65`, slashing cross-service WAN roundtrip latency from 300ms down to 15ms.
- **Browser Anti-Freeze & Power Throttling Architecture**:
  - Implemented fast-path render skipping in `software/visualiser/static/js/dashboard.js` (`if (currentTime === lastRenderedTime) return;`), dropping idle browser CPU consumption to **0.0%**.
  - Integrated Page Visibility API (`document.hidden`) throttling telemetry polling from 500ms to 3000ms when minimized or in background tabs.
- **Automated Regression Test Suite Expansion (119 Passing Tests)**:
  - Added [`tests/test_flask_api_comprehensive.py`](tests/test_flask_api_comprehensive.py) regression tests covering CORS preflight `OPTIONS` handling, Keep-Alive headers, sub-second delta streaming, and cryptographic API key authentication.
  - **119 / 119 tests passing in `21.60s`** with **`88.60%`** `software/shared` coverage (`19.12s` without coverage instrumentation).
- **Complete Indian E-Mobility Web Research Synthesis**:
  - Expanded [`docs/Resources/WEB_RESEARCH.md`](docs/Resources/WEB_RESEARCH.md) to audit AIS-156 Amendment 3 Phase 2 (5-min thermal runaway warning, IPX7 monsoon water ingress), Section 3(k) Indian Patents Act compliance, and comprehensive industrial research synthesis.
  - Mapped national engineering competitions: Smart India Hackathon (SIH), KPIT Sparkle, Formula Bharat (FSAE-E), and Indian deep-tech grants (DST NIDHI-PRAYAS, SISFS).
- **Integrated Camera-Ready IEEE Research Paper (Deliverable 1 of 4 Finalized)**:
  - Replaced preprint draft with the official 6-page camera-ready manuscript: *"A Bit-Exact Fixed-Point FPGA Echo State Network for Lithium-Ion Battery SOC Estimation with an Exploratory SOH Readout"* ([`docs/Publications/Research_Paper.pdf`](docs/Publications/Research_Paper.pdf), 668 KB).
  - Documents 100-neuron Q6.10 ESN on Artix-7 FPGA (318 LUTs, 2 DSP slices, 80 MHz, 535.1 µs latency), 200/200 bit-exact verification, and 29-cell NASA PCoE cross-validation (2,201 windows, 140,864 held-out steps, SOC MAE 0.067, RMSE 0.086).
  - Advances repository to `v2.4.0` synced baseline — only **3 deliverables remain** for `v2.4.1` (Poster, Review Paper, Thesis).
- **Upgraded Plug-and-Play FPGA IP Block to `esn_ip_platform` v1.2 ([`hardware/IP_Block/`](hardware/IP_Block/README.md))**:
  - Replaced flat v1.0 layout with structured v1.2 engineering hierarchy (`rtl/`, `mem/`, `xdc/`, `scripts/`, `tb/`, `verify/`, `test_data/`, `driver/`, `docs/`, `host/`) while preserving baseline IEEE 1685 [`component.xml`](hardware/IP_Block/component.xml), Arty A7-100T [`esn_platform_top.bit`](hardware/IP_Block/esn_platform_top.bit), and routed v1.0 reports in `reports_v10/`.
  - Added [`rtl/esn_core_fast.v`](hardware/IP_Block/rtl/esn_core_fast.v) (`FAST=1, P=10, K=24` parallel sparse ELL reservoir executing in **307 cycles / 3.84 µs** at 80 MHz vs 42,902 serial cycles) and [`rtl/ekf_core.v`](hardware/IP_Block/rtl/ekf_core.v) **Rev 0.5** with optional same-step ESN fusion (`FUSE=1`, 477 cycles).
  - Integrated `host/packs/general_32cells/`, all **29 held-out NASA PCoE cell packs** (`host/packs/heldout/`), self-contained `host/train_pack.py`, `host/reproduce_paper.py` (pooled SOC MAE 0.0667 ESN), `host/narma_board.py` (NARMA-10 dual-application packs), `host/replay_board.py`, causal/fused replay vectors (`test_data/sim_causal_b47`, `sim_fused_b47`), and dual-core Verilator 5.028 **10/10 PASS** regression logs (`docs/regression_2026-11-11.txt`).
- **Repository Storage, Memory & Performance Optimization Pass**:
  - Removed 316 redundant/superseded files across `hardware/IP_Block/host/legacy_oct2026/`, `hardware/IP_Block/backup_rev04/`, duplicate pack `.mem`/`.txt`/`.csv` assets (via shared canonical pack & dataset fallbacks in `esn_host.py`, `narma_board.py`, and `STM_Verifier/config.py`), and duplicate root `FPGA_Verifier/` copies (saving **17.24 MB / 16.45 MiB** on disk, from 799 to 483 tracked files).
  - Upgraded `EchoStateNetwork` with `scipy.sparse.csr_matrix` recurrent matvec caching, symmetric `np.linalg.solve` Ridge solve, and lossless zlib-compressed CSR pickle serialization (`software/visualiser/model_rc.pkl` reduced from `3.33 MB` to `602 KB` with 81.9% compression), alongside fast scalar `math`/tuple hotpaths across `battery_chemistry.py`, `battery_simulator.py`, `traditional_estimator.py`, and `estimator_pipeline.py`, halving full `pytest` + coverage runtime from `48.80s` to `21.60s` (`19.12s` without coverage).

---

## [v2.4.1] - Planned Turnkey Release (Only 3 Pending Academic Deliverables Remaining)

### 🎯 Remaining Scope for `v2.4.1` (Post-`v2.4.0`)
- **A1 Presentation Poster** *(Pending 1/3)*: Compiling and integrating print-ready vector poster [`docs/Poster/Project_Poster.pdf`](docs/Poster/Project_Poster.pdf).
- **Academic Review Paper** *(Pending 2/3)*: Compiling and integrating final peer-review PDF [`docs/Publications/Review_Paper.pdf`](docs/Publications/Review_Paper.pdf).
- **B.E. Capstone Final Thesis** *(Pending 3/3)*: Compiling and integrating 100+ page University of Mumbai dissertation [`docs/Thesis/Final_Thesis.pdf`](docs/Thesis/Final_Thesis.pdf).
- **Already Completed & Synced in `v2.4.0`**: [`docs/Publications/Research_Paper.pdf`](docs/Publications/Research_Paper.pdf) (camera-ready 6-page IEEE PDF), `hardware/IP_Block/` (`esn_ip_platform` v1.2), all software/firmware/RTL modules, and `119/119` passing tests.
- **Official Transition Plan & Runbook**: Detailed drop-in and verification runbook documented in [`docs/Resources/TRANSITION_PLAN_V2.4.1.md`](docs/Resources/TRANSITION_PLAN_V2.4.1.md).

---

## [v2.3.0] - 2026-11-03 (Plug-and-Play FPGA ESN IP Block & Real Research Paper Release)

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
- **Unified 1-Click System Launcher**: Added cross-platform `start_system.py`, `start_system.bat`, and `start_system.sh` enabling developers and common users to boot both Physics Simulator (Port 8000) and Web Visualiser (Port 5000) simultaneously with automatic browser launching and clean shutdown.
- **Open-Source Repository Standards**: Integrated `.editorconfig`, `.env.example`, `.github/CODEOWNERS`, `.github/pull_request_template.md`, `.github/dependabot.yml`, and YAML issue forms (`bug_report.yml`, `feature_request.yml`).
- **Comprehensive Subsystem Guides**: Added [`hardware/STM_Verifier/README.md`](hardware/STM_Verifier/README.md) for C99 CSR SpMV firmware and [`tests/README.md`](tests/README.md) for the 15-module automated test inventory.
- **Narrative Flow & Developmental Continuity**: Formally unified root `README.md` and `docs/README.md` with a 5-Act story arc, chronological milestone diagrams, and bidirectional breadcrumb links across all 36+ Markdown documents.

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
