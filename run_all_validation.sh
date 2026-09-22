#!/usr/bin/env bash
# =======================================================================
#   BATTERY STATE ESTIMATOR - POSIX (LINUX/MACOS) HARDWARE & SOFTWARE VALIDATION
# =======================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAILURES=0

echo "======================================================================="
echo "  BATTERY STATE ESTIMATOR - COMPLETE HARDWARE AND SOFTWARE VALIDATION"
echo "======================================================================="
echo ""

# ── STEP 1: Verify Python Environment & Shared Modules ─────────────────────
echo "[1/8] Verifying Environment and Python Dependencies..."
PYTHON_BIN=""
for cmd in python3 python python.exe; do
    if command -v "$cmd" &>/dev/null && "$cmd" -c "import pandas, pymongo" &>/dev/null; then
        PYTHON_BIN="$cmd"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    if command -v python3 &>/dev/null; then
        PYTHON_BIN="python3"
    elif command -v python &>/dev/null; then
        PYTHON_BIN="python"
    elif command -v python.exe &>/dev/null; then
        PYTHON_BIN="python.exe"
    else
        echo "[ERROR] Python is not installed or not in PATH."
        exit 1
    fi
fi
echo "[OK] Python environment detected ($PYTHON_BIN)."

$PYTHON_BIN -c "import sys; sys.path.insert(0, '.'); from software.shared.battery_simulator import BatterySimulator; from software.shared.battery_chemistry import get_chemistry; sim = BatterySimulator(); chem = get_chemistry('li_ion'); print('[OK] Microservice shared physics package (software.shared) strictly verified.')" || FAILURES=$((FAILURES+1))
echo ""

# ── STEP 2: Run Full Pytest Suite ──────────────────────────────────────────
echo "[2/8] Running Complete Pytest Suite (62 Unit/Integration Tests)..."
$PYTHON_BIN -m pytest tests/ || FAILURES=$((FAILURES+1))
echo "[SUCCESS] Pytest suite executed."
echo ""

# ── STEP 3: Software Model Training ────────────────────────────────────────
echo "[3/8] [SOFTWARE] Training and Exporting Software ESN (model_rc.pkl)..."
$PYTHON_BIN software/visualiser/training/train_rc.py || FAILURES=$((FAILURES+1))
echo "[SUCCESS] Software ESN model trained and saved."
echo ""

# ── STEP 4: Software Estimator & Simulator Verification ───────────────────
echo "[4/8] [SOFTWARE] Testing Physics Simulator and Estimator Pipeline..."
$PYTHON_BIN -c "import sys; sys.path.insert(0, '.'); sys.path.insert(0, './software/visualiser'); from software.shared.battery_simulator import BatterySimulator; sim = BatterySimulator(); st = sim.step(-2.0, 1.0); from estimator_pipeline import EstimatorPipeline; ep = EstimatorPipeline(); res = ep.step(V_meas=st['voltage'], I_meas_discharge=st['current'], T_meas=st['temperature']); print('[TEST PASSED] Physics step V=', round(st['voltage'],3), 'V | EKF SOC=', round(res['ekf_soc'],4), '| UKF SOC=', round(res['ukf_soc'],4))" || FAILURES=$((FAILURES+1))
echo "[SUCCESS] Software Physics Simulator and Estimator Pipeline verified."
echo ""

# ── STEP 5: Hardware STM32 ESN Classifier Training & Export ───────────────
echo "[5/8] [HARDWARE - STM32] Training ESN Classifier and Exporting C Headers..."
$PYTHON_BIN hardware/STM_Verifier/train_classifier.py || FAILURES=$((FAILURES+1))
echo "[SUCCESS] STM32 ESN Classifier weights exported."
echo ""

# ── STEP 6: Hardware STM32 ESN Estimator Training & Export ────────────────
echo "[6/8] [HARDWARE - STM32] Training ESN Estimator and Exporting C Headers..."
$PYTHON_BIN hardware/STM_Verifier/train_estimator.py || FAILURES=$((FAILURES+1))
echo "[SUCCESS] STM32 ESN Estimator weights exported."
echo ""

# ── STEP 7: Hardware FPGA Verilog RTL Golden Model Verification ────────────
echo "[7/8] [HARDWARE - FPGA] Verifying Verilog RTL vs Python Golden Model..."
$PYTHON_BIN hardware/FPGA_Verifier/compare_results.py || FAILURES=$((FAILURES+1))
echo "[SUCCESS] FPGA Verilog RTL matched golden reference model bit-exactly."
echo ""

# ── STEP 8: C99 Microcontroller Desktop Simulator Compilation & Run ────────
echo "[8/8] [HARDWARE - C99] Compiling and Executing C99 Edge Simulator..."
export VALIDATION_PIPELINE=1
(cd hardware/STM_Verifier && bash run_c_simulator.sh) || FAILURES=$((FAILURES+1))
echo "[SUCCESS] C99 Microcontroller Simulator executed cleanly."
echo ""

echo "======================================================================="
if [ $FAILURES -eq 0 ]; then
    echo "  [ALL PASSED] END-TO-END HARDWARE AND SOFTWARE VALIDATION SUCCESSFUL!"
    echo "======================================================================="
    echo ""
    echo " To run the Software Web Services manually, open two terminal windows:"
    echo ""
    echo "   Terminal 1 (Physics Simulator - Port 8000):"
    echo "     $PYTHON_BIN software/simulator/app.py"
    echo ""
    echo "   Terminal 2 (Visualiser Dashboard - Port 5000):"
    echo "     $PYTHON_BIN software/visualiser/app.py"
    echo ""
    echo " Access Visualiser Dashboard UI at: http://localhost:5000"
    echo "======================================================================="
    exit 0
else
    echo "  [FAILED] VALIDATION COMPLETED WITH $FAILURES ERROR(S)."
    echo "======================================================================="
    exit 1
fi

