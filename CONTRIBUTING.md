# Contributing to Battery State Estimator

Thank you for your interest in contributing to the **Battery State Estimator** research and engineering repository. This project is developed as a BE Capstone Project and peer-reviewed research initiative at Vivekanand Education Society's Institute of Technology (VESIT).

---

## 📋 Code of Conduct & Contribution Standards

All contributors are expected to uphold rigorous scientific integrity, clean code practices, and detailed documentation.

### Core Architecture Guidelines
* **Physics Simulation:** Strictly preserve the 2-RC Equivalent Circuit Model (ECM) physics and Arrhenius equations defined in [`software/shared/battery_simulator.py`](software/shared/battery_simulator.py).
* **Observer Pipelines:** Any modification to Kalman filters (EKF/UKF) or Echo State Networks (ESN) must preserve parameter decoupling and run against the 119-test regression suite.
* **Embedded C Firmware:** Maintain C99 compatibility, Q15 fixed-point arithmetic, and Compressed Sparse Row (CSR) memory bounds in [`hardware/STM_Verifier/`](hardware/STM_Verifier/).
* **Verilog RTL:** Keep the 5-stage pipeline in [`hardware/FPGA_Verifier/`](hardware/FPGA_Verifier/) bit-exact with [`golden_model.py`](hardware/FPGA_Verifier/golden_model.py).

---

## 🛠️ Development & Validation Workflow

### 1. Setting Up the Environment
```bash
# Clone the repository
git clone https://github.com/tanish-jain-225/Battery_State_Estimator_BE_Project_2026_2027.git
cd Battery_State_Estimator_BE_Project_2026_2027

# Install dependencies
pip install -r requirements.txt
```

### 2. Running Automated Validation
Before committing any changes, run the master end-to-end validation runner:

* On Windows:
  ```cmd
  run_all_validation.bat
  ```
* On Linux / macOS:
  ```bash
  chmod +x run_all_validation.sh
  ./run_all_validation.sh
  ```

All 119 tests across pytest, model training, C99 compilation, and FPGA RTL bit-exact matching must pass with **0 errors**.

---

## 📑 Paper & Poster Maintenance Guidelines

1. **Authored Manuscripts:**
   * Text source for the Research Paper: [`reference/paper.md`](reference/paper.md)
   * Comprehensive Review Paper Deliverable: [`docs/Publications/Review_Paper.pdf`](docs/Publications/Review_Paper.pdf)
   * When modifying manuscript text, update the markdown document and place the compiled camera-ready PDF deliverables in [`docs/Publications/`](docs/Publications/README.md).
2. **Publications Directory:**
   * Canonical PDF deliverables are located in [`docs/Publications/`](docs/Publications/README.md).
3. **Capstone Poster:**
   * Maintained in [`docs/Poster/`](docs/Poster/README.md). Ensure any layout changes adhere to the A1 exhibition format.
4. **Submission Proofs:**
   * When submitting to IEEE or Scopus journals, log official receipts in [`docs/Paper_Proof/`](docs/Paper_Proof/README.md).

---

## 🏛️ Governance, Attribution & Policies

* **License & Attribution:** See [`LICENSE`](LICENSE) for terms of use and the academic attribution clause.
* **Author Directory & Affiliations:** See [`AUTHORS.md`](AUTHORS.md) for full student, guide, and departmental credits.
* **Citation Records:** See [`CITATION.cff`](CITATION.cff) for BibTeX and APA citation formats.
* **Code of Conduct:** See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for community and academic integrity standards.
* **Security & Vulnerability Reporting:** See [`SECURITY.md`](SECURITY.md) for our security reporting procedure and secrets policy.

---

## 📦 Artifacts & Commit Protocol

Refer to [`docs/Resources/ARTIFACTS.md`](docs/Resources/ARTIFACTS.md) for guidelines on committing model weights (`.pkl`, `.h`), bitstream files (`.coe`), and compiled reports.

