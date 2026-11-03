# Security Policy

The **Battery State Estimator** research team prioritizes the integrity, reliability, and security of both our cloud-connected microservices and edge microcontroller firmware.

---

## 🛡️ Supported Versions

Only the latest active major releases receive security updates and bug fixes:

| Version | Supported | Release Date | Notes |
| :---: | :---: | :--- | :--- |
| **v2.3.1** | :white_check_mark: | 2026-11-04 (Tomorrow) | Planned release: Final Academic Deliverables (Review Paper, Poster, Review 2 PPT). |
| **v2.3.0** | :white_check_mark: | 2026-11-03 (Today) | Current active release (115 tests, plug-and-play FPGA ESN IP block, IEEE research paper, footprint optimization). |
| **v2.2.x** | :white_check_mark: | 2026-11-01 | Previous release (pub/sub decoupled microservices, FPGA EKF/UKF verification). |
| **v2.1.x** | :white_check_mark: | 2026-11-01 | Academic publications, poster and governance release. |
| **v2.0.x** | :white_check_mark: | 2026-10-10 | Review 2 Milestone baseline (62 tests, FPGA RTL parity). |
| **v1.0.x** | :x: | 2026-09-21 | Review 1 Prototype (Deprecated). |

---

## 🔒 Security Architecture & Practices

### 1. Secrets & Credentials Management
- Never commit actual production secrets, passwords, or private database connection strings to source control.
- Configuration is strictly loaded via environment variables using `.env` files (see `.env.example` templates in [`software/simulator/`](software/simulator/) and [`software/visualiser/`](software/visualiser/)).
- All `.env`, `*.env`, and cloud credential files are excluded from Git via [`.gitignore`](.gitignore).

### 2. Microservice API Authentication & Failsafe
- REST API communication between the Visualiser (`localhost:5000`) and Physics Simulator (`localhost:8000`) uses SHA-256 derived authentication tokens matching the configured `MONGODB_URI`.
- For offline academic evaluation, when `MONGODB_URI` targets `localhost` or `127.0.0.1`, the system activates an offline fallback mode so students can run tests without an active internet connection.

### 3. Firmware Memory Safety & Static Bounds
- Embedded C99 firmware in [`hardware/STM_Verifier/`](hardware/STM_Verifier/) adheres to MISRA-C safety principles:
  - All Compressed Sparse Row (CSR) array iterations are bound-checked against fixed dimension constants (`N_RESERVOIR = 50`, `N_INPUTS = 3`, `N_CLASSES = 3`).
  - No dynamic memory allocation (`malloc`/`free`) is executed in real-time execution loops.
  - Stack variables are statically allocated and fixed-point accumulator arithmetic uses saturation clamping to prevent integer overflow.

---

## 📬 Reporting a Vulnerability

If you discover a security vulnerability, memory safety defect, or credential exposure within this repository:

1. **Do not create a public GitHub issue.**
2. Send an email to the lead student maintainer and project guide:
   - **Tanish Sanghvi:** [2023.tanish.sanghvi@ves.ac.in](mailto:2023.tanish.sanghvi@ves.ac.in)
   - **Dr. Kadambari Sharma:** Project Guide, VESIT ([VESIT Department Portal](https://vesit.ves.ac.in))
3. Include detailed steps to reproduce the issue, sample payload/telemetry, and affected operating system/hardware.
4. The maintainers will respond within 48 hours to acknowledge receipt and coordinate a patch.

