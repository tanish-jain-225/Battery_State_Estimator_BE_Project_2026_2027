# Operations Guide

This guide describes local setup, environment configuration, training pipelines, running web services, and edge microcontroller simulation or compilation procedures for the Battery State Estimator.

---

## 💻 1. System Setup & Configuration

### Prerequisites
- **Python 3.8+**: Used for simulator, training scripts, and visualiser.
- **C99 Compiler**: (e.g., `gcc`, `clang`, or MSVC `cl.exe`) for running the desktop C diagnostic simulator.
- **Database (Optional)**: A local MongoDB instance or a MongoDB Atlas cloud database. If unavailable, the system defaults to in-memory buffers automatically.

### Local Installation
1. Clone the repository and navigate to the project root:
   ```bash
   git clone <repository-url>
   cd Battery_State_Estimator_BE_Project_2026_2027
   ```
2. Install the necessary Python packages:
   ```bash
   python -m pip install -r requirements.txt
   ```

### Local Environment Settings
Configure local environment settings by creating `.env` files in the respective app directories. 

#### Simulator Environment Configuration
Create [`software/simulator/.env`](../software/simulator/.env) (refer to [`software/simulator/.env.example`](../software/simulator/.env.example)):
```text
PORT=8000
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=battery_estimator_db
MONGODB_STATE_COLLECTION=sim_state
MONGODB_READINGS_COLLECTION=telemetry
```

#### Visualiser Environment Configuration
Create [`software/visualiser/.env`](../software/visualiser/.env) (refer to [`software/visualiser/.env.example`](../software/visualiser/.env.example)):
```text
PORT=5000
SIMULATOR_URL=http://localhost:8000
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=battery_estimator_db
MONGODB_READINGS_COLLECTION=telemetry
```

> [!NOTE]
> When `MONGODB_URI` contains `localhost` or `127.0.0.1`, the security key validation triggers a "Fails-Open" logic to simplify offline student development.

---

## 📈 2. Model Training Pipeline

Before launching the visualiser dashboard or the edge simulation, train the reservoir weights using the offline pipelines.

### A. Train the Software Estimator
Runs the training pipeline to build the ESN models for SOC and SOH estimation, outputting the default pickle file.
```bash
python software/visualiser/training/train_rc.py
```
* **Expected Output:** Console logs detailing training progress, R2 and RMSE scores (validation SOC RMSE < 1.2%), and serialization of `model_rc.pkl` to the visualiser directory.

### B. Train the Hardware ESN Classifier
Trains the 3-class thermal safety classification network using the database records and generates the optimized C headers.
```bash
python hardware/train_classifier.py
```
* **Expected Output:** Logs confirming classification accuracy (typically 98.40%), matrix sparsity details, and code generation of [`hardware/esn_classifier_weights.h`](../hardware/esn_classifier_weights.h).

### C. Train the Hardware ESN Estimator (Optional)
Generates sparse estimator weights for running advanced regressions on-chip.
```bash
python hardware/train_estimator.py
```
* **Expected Output:** Exports weight vectors into [`hardware/esn_estimator_weights.h`](../hardware/esn_estimator_weights.h).

---

## 🖥️ 3. Running Flask Web Services

To view the live physics simulator and visualizer dashboard, launch both Flask servers simultaneously.

### Step 1: Start the Physics Engine
In your first terminal, launch the simulator service:
```bash
python software/simulator/app.py
```
* **Default URL:** `http://localhost:8000`
* **Expected Output:** 
  ```text
  * Running on http://127.0.0.1:8000/ (Press CTRL+C to quit)
  * Starting background telemetry generator thread...
  ```

### Step 2: Start the Visualiser Dashboard
In a second terminal, launch the dashboard:
```bash
python software/visualiser/app.py
```
* **Default URL:** `http://localhost:5000`
* **Expected Output:**
  ```text
  * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
  * Visualiser Observer Pipeline initialized.
  ```

### Step 3: Access the Dashboard
1. Open `http://localhost:5000` in your web browser.
2. Use the controls to start/pause telemetry playback, select active drive cycles (e.g., UDDS, US06), or inject faults.
3. Compare EKF, Coulomb Counting, and ESN estimators side-by-side.

---

## 🔌 4. Microcontroller Compilation & Simulation

To test the edge diagnostic logic locally without hardware flashing, run the desktop C99 simulator.

### Running the Desktop C Simulator
The desktop C simulator runs a verification dataset through the CSR-compressed ESN classification model to output diagnostic logs.

- **On Windows (PowerShell/CMD):**
  ```powershell
  hardware/run_c_simulator.bat
  ```
- **On Linux or macOS:**
  ```bash
  chmod +x hardware/run_c_simulator.sh
  ./hardware/run_c_simulator.sh
  ```

* **Expected Output:**
  ```text
  === ESN Reservoir Classifier Desktop Test ===
  Loading validation data...
  Running CSR sparse evaluation...
  [Tick 10] Volt: 3.72V, Curr: -1.2A, Temp: 28.5C | Output: Normal (0)
  [Tick 120] Volt: 3.65V, Curr: -4.5A, Temp: 36.2C | Output: Warning (1)
  [Tick 240] Volt: 3.51V, Curr: -8.9A, Temp: 46.8C | Output: Critical (2)
  Validation Complete. Classification Accuracy: 98.40%
  ```

### Microcontroller Deployment (STM32)
1. Import [`hardware/main.c`](../hardware/main.c), [`hardware/main.h`](../hardware/main.h), and [`hardware/esn_classifier_weights.h`](../hardware/esn_classifier_weights.h) into STM32CubeIDE.
2. In the pin configuration tool, configure **`PA5`** as a standard digital output pin (maps to the on-board user LED on Nucleo boards).
3. Configure **`USART2`** (pins `PA2`/`PA3`) for UART communication at **115200 baud, 8 data bits, 1 stop bit**.
4. Compile and flash the code.
5. Watch the on-board LED (`PA5`) reflect the thermal classification:
   - **LED OFF**: Normal temperature ($T < 35^\circ\text{C}$).
   - **LED BLINKING**: Warning temperature ($35^\circ\text{C} \le T < 45^\circ\text{C}$).
   - **LED STEADY ON**: Critical temperature/Thermal threat ($T \ge 45^\circ\text{C}$).

---

## ⚠️ 5. Troubleshooting & Solutions

> [!WARNING]
> **Issue: Port 5000 or 8000 already in use**
> - **Cause**: A previous Flask process did not terminate correctly.
> - **Solution**:
>   - *Windows (CMD)*: `netstat -ano | findstr :5000` to find the Process ID (PID), then run `taskkill /F /PID <PID>`.
>   - *Linux/macOS*: `lsof -i :5000` to find the PID, then run `kill -9 <PID>`.
>   - Alternatively, change the port in the `.env` file and update URLs.

> [!IMPORTANT]
> **Issue: C Compiler (gcc/clang) not found on Windows**
> - **Cause**: MinGW/MSYS2 is not installed or not added to your system's environment `PATH`.
> - **Solution**: Install MinGW and ensure the `bin` folder is added to your Windows system Environment Variables. Alternatively, open the "Developer Command Prompt for VS" and run compilation commands manually.

> [!CAUTION]
> **Issue: MongoDB Authentication Fails (401 Unauthorized)**
> - **Cause**: The SHA-256 API Key derived from the `MONGODB_URI` string does not match between the simulator and the visualiser service configurations.
> - **Solution**: Double check that both `software/simulator/.env` and `software/visualiser/.env` contain the exact same `MONGODB_URI` string. If local, check that it contains `localhost` or `127.0.0.1` to bypass gating.
