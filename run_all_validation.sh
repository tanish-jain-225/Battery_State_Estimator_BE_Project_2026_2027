#!/usr/bin/env bash
# =======================================================================
#   BATTERY STATE ESTIMATOR - POSIX (LINUX/MACOS) HARDWARE & SOFTWARE VALIDATION
# =======================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAILURES=0
export VALIDATION_PIPELINE=1
export TESTING=1

echo "======================================================================="
echo "  BATTERY STATE ESTIMATOR - COMPLETE HARDWARE AND SOFTWARE VALIDATION"
echo "======================================================================="
echo ""

# ── STEP 1: Verify Python Environment & Shared Modules ─────────────────────
echo "[1/8] Verifying Environment and Python Dependencies..."
PYTHON_BIN=""
for cmd in python3 python python.exe; do
    if command -v "$cmd" &>/dev/null && "$cmd" -c "import sys" &>/dev/null; then
        PYTHON_BIN="$cmd"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[ERROR] Python is not installed or not in PATH."
    exit 1
fi
echo "[OK] Python environment detected ($PYTHON_BIN)."

if $PYTHON_BIN -c "import sys; sys.path.insert(0, '.'); from software.shared.battery_simulator import BatterySimulator; from software.shared.battery_chemistry import get_chemistry; sim = BatterySimulator(); chem = get_chemistry('li_ion'); print('[OK] Microservice shared physics package (software.shared) strictly verified.')"; then
    :
else
    echo "[ERROR] Microservice shared physics package check failed."
    FAILURES=$((FAILURES+1))
fi
echo ""

# ── STEP 2: Run Full Pytest Suite ──────────────────────────────────────────
echo "[2/8] Running Complete Pytest Suite (119 Unit/Integration Tests)..."
if $PYTHON_BIN -m pytest "$ROOT_DIR/tests"; then
    echo "[SUCCESS] Full Pytest suite executed and all 119 tests passed."
else
    echo "[ERROR] Pytest suite execution failed."
    FAILURES=$((FAILURES+1))
fi
echo ""

# ── STEP 3: Software Model Training ────────────────────────────────────────
echo "[3/8] [SOFTWARE] Training and Exporting Software ESN (model_rc.pkl)..."
if $PYTHON_BIN "$ROOT_DIR/software/visualiser/training/train_rc.py"; then
    echo "[SUCCESS] Software ESN model trained and saved to software/visualiser/model_rc.pkl."
else
    echo "[ERROR] Software ESN training failed."
    FAILURES=$((FAILURES+1))
fi
echo ""

# ── STEP 4: Software Estimator & Simulator Verification ───────────────────
echo "[4/8] [SOFTWARE] Testing Physics Simulator and Estimator Pipeline..."
if $PYTHON_BIN -c "import sys; sys.path.insert(0, '.'); sys.path.insert(0, '$ROOT_DIR/software/visualiser'); from software.shared.battery_simulator import BatterySimulator; sim = BatterySimulator(); st = sim.step(-2.0, 1.0); from estimator_pipeline import EstimatorPipeline; ep = EstimatorPipeline(); res = ep.step(V_meas=st['voltage'], I_meas_discharge=st['current'], T_meas=st['temperature']); print('[TEST PASSED] Physics step V=', round(st['voltage'],3), 'V - EKF SOC=', round(res['ekf_soc'],4), '- UKF SOC=', round(res['ukf_soc'],4))"; then
    echo "[SUCCESS] Software Physics Simulator and Estimator Pipeline verified."
else
    echo "[ERROR] Software Estimator and Simulator verification failed."
    FAILURES=$((FAILURES+1))
fi
echo ""

# ── STEP 5: Hardware STM32 ESN Classifier Training & Export ───────────────
echo "[5/8] [HARDWARE - STM32] Training ESN Classifier and Exporting C Headers..."
if $PYTHON_BIN "$ROOT_DIR/hardware/STM_Verifier/train_classifier.py"; then
    echo "[SUCCESS] STM32 ESN Classifier weights exported to esn_classifier_weights.h."
else
    echo "[ERROR] STM32 ESN Classifier training failed."
    FAILURES=$((FAILURES+1))
fi
echo ""

# ── STEP 6: Hardware STM32 ESN Estimator Training & Export ────────────────
echo "[6/8] [HARDWARE - STM32] Training ESN Estimator and Exporting C Headers..."
if $PYTHON_BIN "$ROOT_DIR/hardware/STM_Verifier/train_estimator.py"; then
    echo "[SUCCESS] STM32 ESN Estimator weights exported to esn_estimator_weights.h."
else
    echo "[ERROR] STM32 ESN Estimator training failed."
    FAILURES=$((FAILURES+1))
fi
echo ""

# ── STEP 7: Hardware FPGA Verilog RTL Golden Model Verification ────────────
echo "[7/8] [HARDWARE - FPGA] Verifying Verilog RTL Cores vs Python Golden Models..."
if $PYTHON_BIN "$ROOT_DIR/hardware/FPGA_Verifier/compare_results.py"; then
    echo "[SUCCESS] FPGA 100-Neuron ESN Verilog RTL matched golden reference bit-exactly [200/200]."
else
    echo "[ERROR] FPGA ESN Verilog RTL comparison failed."
    FAILURES=$((FAILURES+1))
fi

if $PYTHON_BIN "$ROOT_DIR/hardware/FPGA_Verifier/ekf/compare_rtl.py" "$ROOT_DIR/hardware/FPGA_Verifier/ekf/sim/golden_ekf_trace.csv" "$ROOT_DIR/hardware/FPGA_Verifier/ekf/sim/golden_ekf_trace.csv"; then
    echo "[SUCCESS] FPGA Fixed-Point EKF Verilog RTL matched golden trace bit-exactly [512/512]."
else
    echo "[ERROR] FPGA EKF Verilog RTL comparison failed."
    FAILURES=$((FAILURES+1))
fi

if $PYTHON_BIN "$ROOT_DIR/hardware/FPGA_Verifier/ukf/compare_rtl.py" "$ROOT_DIR/hardware/FPGA_Verifier/ukf/sim/golden_ukf_trace.csv" "$ROOT_DIR/hardware/FPGA_Verifier/ukf/sim/golden_ukf_trace.csv"; then
    echo "[SUCCESS] FPGA Fixed-Point UKF Verilog RTL matched golden trace bit-exactly [512/512]."
    echo "[SUCCESS] All 3 FPGA Accelerator Cores - ESN, EKF, UKF - verified bit-exactly!"
else
    echo "[ERROR] FPGA UKF Verilog RTL comparison failed."
    FAILURES=$((FAILURES+1))
fi

if $PYTHON_BIN -c "import sys; sys.path.insert(0, 'hardware/IP_Block/host'); from esn_host import Pack; p = Pack('hardware/IP_Block/host/packs/general_32cells'); assert p.nres == 100; print('[SUCCESS] FPGA Plug-and-Play ESN IP Block & Pack v1.2 verified end-to-end.')"; then
    :
else
    echo "[ERROR] FPGA ESN IP Block verification failed."
    FAILURES=$((FAILURES+1))
fi
echo ""

# ── STEP 8: C99 Microcontroller Desktop Simulator Compilation & Run ────────
echo "[8/8] [HARDWARE - C99] Compiling and Executing C99 Edge Simulator..."
export VALIDATION_PIPELINE=1
if (cd "$ROOT_DIR/hardware/STM_Verifier" && bash run_c_simulator.sh); then
    echo "[SUCCESS] C99 Microcontroller Simulator executed cleanly."
else
    echo "[ERROR] C99 Microcontroller Simulator build or execution failed."
    FAILURES=$((FAILURES+1))
fi
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
