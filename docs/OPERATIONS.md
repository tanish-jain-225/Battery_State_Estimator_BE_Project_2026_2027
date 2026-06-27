# Operations Guide

This guide describes local setup, environment configuration, training pipelines, visualization services, and edge microcontroller simulation/compilation procedures for the Battery State Estimator.

---

## 💻 1. System Setup & Configuration

### Prerequisites
- Python 3.8 or higher
- C99-compliant compiler (`gcc`, `clang`, or MSVC `cl`)
- Optional: MongoDB local service or MongoDB Atlas cluster

### Installation
1. Clone the repository and navigate to the project directory:
   ```bash
   git clone <repository-url>
   cd Battery_State_Estimator_BE_Project_2026_2027
   ```
2. Install all dependencies from the root requirements file:
   ```bash
   python -m pip install -r requirements.txt
   ```

### Local Environment Variables
Create `.env` files in `software/simulator/` and `software/visualiser/` to match your local setup.

**Simulator (`software/simulator/.env`):**
```text
PORT=8000
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=battery_estimator_db
MONGODB_STATE_COLLECTION=sim_state
MONGODB_READINGS_COLLECTION=telemetry
```

**Visualiser (`software/visualiser/.env`):**
```text
PORT=5000
SIMULATOR_URL=http://localhost:8000
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=battery_estimator_db
MONGODB_READINGS_COLLECTION=telemetry
```

*Note: If no MongoDB connection is found, both applications fallback to local in-memory circular telemetry buffers automatically.*

---

## 📈 2. Model Training Pipeline

Before running the full dashboard or edge microcontroller simulation, train the ESN weights.

1. **Train Software Estimator Model**:
   ```bash
   python software/visualiser/training/train_rc.py
   ```
   This trains the reservoir model for SOC/SOH estimation and creates the `model_rc.pkl` fallback file.

2. **Train Hardware ESN Classifier**:
   ```bash
   python hardware/train_classifier.py
   ```
   This processes the EV battery dataset and generates the `esn_classifier_weights.h` header for the C99 microcontroller firmware.

3. **Train Hardware ESN Estimator (Optional)**:
   ```bash
   python hardware/train_estimator.py
   ```
   This exports sparse estimator weights to `esn_estimator_weights.h` for advanced embedded calculations.

---

## 🖥️ 3. Running Flask Web Services

To observe live physics and estimator dashboards, launch the two Flask servers:

1. **Start the Physics Engine** (Terminal 1):
   ```bash
   python software/simulator/app.py
   ```
   This starts the 2-RC ECM simulator on `http://localhost:8000`.

2. **Start the Operator Dashboard** (Terminal 2):
   ```bash
   python software/visualiser/app.py
   ```
   This starts the visualiser on `http://localhost:5000`.

3. **Interact**:
   - Navigate to `http://localhost:5000` in your web browser.
   - Start/pause telemetry generation, toggle fault injection (thermal runaway, sensor dropout, or micro-shorts), and compare EKF vs ESN estimation plots in real-time.

---

## 🔌 4. Microcontroller Compilation & Simulation

To test the edge diagnostic firmware logic locally without flashing raw hardware, run the desktop C simulation:

### Compile and Run C Simulator

**On Windows:**
Execute the batch script to automatically locate a compiler, compile the code, and print diagnostic results:
```bash
hardware/run_c_simulator.bat
```

**On Linux or macOS:**
```bash
chmod +x hardware/run_c_simulator.sh
hardware/run_c_simulator.sh
```

### Microcontroller Deployment (STM32)
1. Import `hardware/main.c`, `hardware/main.h`, and `hardware/esn_classifier_weights.h` into STM32CubeIDE or Keil uVision.
2. Ensure GPIO `PA5` is configured as a Push-Pull output (controls the status LED).
3. Ensure USART2 is enabled for diagnostic status reporting (115200 baud, 8 data bits, 1 stop bit).
4. Flash the code to your target board (e.g., STM32 Nucleo-F401RE). The status LED (`PA5`) indicates the state:
   - **LED OFF**: Normal thermal safety state ($T < 35^\circ\text{C}$).
   - **LED BLINKING**: Warning thermal state ($35^\circ\text{C} \le T < 45^\circ\text{C}$).
   - **LED ON**: Critical thermal state ($T \ge 45^\circ\text{C}$).
