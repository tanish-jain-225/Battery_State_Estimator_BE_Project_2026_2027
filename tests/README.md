# Automated Regression Test Suite (119 Tests)

[← Back to Main Repository](../README.md) · [Software Subsystem](../software/software.md) · [Hardware Subsystem](../hardware/hardware.md) · [Operations Guide](../docs/Resources/OPERATIONS.md)

---

## 📌 Overview

The repository features a rigorous, multi-layered automated regression test suite comprising **119 automated tests** across 15 specialized test modules, achieving **94.49% code coverage** on core shared physics and estimator packages.

Every test executes in-memory with zero network or database dependencies (utilizing mock MongoDB fixtures in [`conftest.py`](conftest.py)).

---

## 📑 Test Module Inventory & Coverage Map

| Test Module | Test Count | Focus & Verification Scope | Key Assertions / Invariants |
| :--- | :---: | :--- | :--- |
| [`test_battery_chemistry.py`](test_battery_chemistry.py) | **3** | Electrochemical parameters for Lithium-ion (NMC), LFP, and Lead-Acid chemistries. | OCV-SOC curve strictly monotonic; valid cell nominal voltages ($V_{\text{nom}} \in [2.0, 4.2]\text{ V}$). |
| [`test_battery_simulator.py`](test_battery_simulator.py) | **10** | 2-RC transient state space equations, Arrhenius electro-thermal solver, fault injection. | Temperature rise under high discharge; micro-short leakage current; thermal runaway trigger. |
| [`test_esn_model.py`](test_esn_model.py) | **5** | Echo State Network (ESN) reservoir dynamics, spectral radius, and echo state property. | Spectral radius $\rho < 1.0$; reservoir state fading memory; stable continuous-time updates. |
| [`test_estimator_pipeline.py`](test_estimator_pipeline.py) | **9** | Multi-observer state hydration, state serialization, and CPS safety diagnostics. | Sensor dropout detection ($V < 1.0\text{ V}$); micro-short divergence alarm; pipeline reset. |
| [`test_estimator_pipeline_advanced.py`](test_estimator_pipeline_advanced.py) | **11** | Cross-chemistry estimation, sensor noise tolerance, and hybrid observer switching. | Stable tracking under Gaussian noise; non-divergence under abrupt load changes. |
| [`test_flask_api.py`](test_flask_api.py) | **5** | Flask REST routes, cryptographic API key authentication, and control endpoints. | 401 Unauthorized on invalid key; valid JSON payloads on `/api/telemetry` and `/api/control`. |
| [`test_flask_api_comprehensive.py`](test_flask_api_comprehensive.py) | **16** | Comprehensive API parameter fuzzing, CORS OPTIONS preflights, HTTP Keep-Alive, sub-second delta streaming, and API key auth. | In-memory fallback on database drop; 200 OK on drive cycle switching; graceful error responses. |
| [`test_fpga_ekf_ukf.py`](test_fpga_ekf_ukf.py) | **7** | Fixed-point Q15 arithmetic and bit-exact RTL parity for hardware EKF and UKF cores. | 512/512 exact matches vs. golden references; Cholesky positive-definiteness guards. |
| [`test_fpga_verifier.py`](test_fpga_verifier.py) | **7** | 100-neuron Verilog RTL datapath, radix-16 COE parsing, and odd-symmetric $\tanh$ LUT. | 200/200 bit-exact stage matches; two's-complement signed hex parsing without corruption. |
| [`test_fpga_verifier_extended.py`](test_fpga_verifier_extended.py) | **9** | Vivado XSim dump parsing, extended multi-cycle stimulus, and outcomes evaluator CLI. | Verifies `eval_fpga_outcomes.py` across 32 NASA cycles; timing closure metrics (0.099 W). |
| [`test_hardware_training_and_export.py`](test_hardware_training_and_export.py) | **7** | Embedded CSR sparse weight export and Q12/Q15 quantization pipelines. | CSR matrix decompression equals dense matrix; C header syntax validity. |
| [`test_integration.py`](test_integration.py) | **6** | End-to-end multi-timestep simulation loop (Simulator $\to$ Pipeline $\to$ Visualiser). | 100 consecutive timesteps execute without NaN, memory leaks, or state corruption. |
| [`test_ip_block.py`](test_ip_block.py) | **5** | IEEE 1685 IP-XACT descriptor (`component.xml`), AXI4 register maps, and pre-compiled bitstream. | Packaging XML schema validity; register address boundaries; bitstream file integrity (3.7 MB). |
| [`test_online_training.py`](test_online_training.py) | **9** | Dynamic online Recursive Least Squares (RLS) adaptive readout weight filter. | Tracks capacity degradation over 32 cycles; SOC RMSE remains below 1.0%. |
| [`test_traditional_estimator.py`](test_traditional_estimator.py) | **10** | Baseline Extended Kalman Filter (EKF), Unscented Kalman Filter (UKF), and Coulomb Counting. | EKF covariance Riccati updates; UKF Merwe sigma points; Coulomb integration drift. |
| **Total Suite** | **119** | **Complete Full-Stack Coverage** | **100% Pass Rate** |

---

## 🚀 How to Run Tests

### Run All 119 Tests:
```bash
python -m pytest tests/
```

### Run with Code Coverage Report:
```bash
pytest tests/ --cov=software/shared --cov=software/visualiser --cov-report=term-missing
```

### Run Specific Test Modules:
```bash
# Test FPGA accelerators and bit-exact parity:
pytest tests/test_fpga_verifier.py tests/test_fpga_ekf_ukf.py tests/test_ip_block.py -v

# Test Multi-Observer Estimator Pipeline:
pytest tests/test_estimator_pipeline.py tests/test_traditional_estimator.py tests/test_online_training.py -v

# Test REST APIs and Microservices:
pytest tests/test_flask_api.py tests/test_flask_api_comprehensive.py -v
```

