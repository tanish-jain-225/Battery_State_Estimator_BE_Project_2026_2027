@echo off
setlocal enabledelayedexpansion

echo =======================================================================
echo   BATTERY STATE ESTIMATOR - COMPLETE HARDWARE AND SOFTWARE VALIDATION
echo =======================================================================
echo.

set FAILURES=0
set "ROOT_DIR=%~dp0"

:: ── STEP 1: Verify Python Environment ────────────────────────────────────
echo [1/8] Verifying Environment and Python Dependencies...
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    set /a FAILURES+=1
    goto summary
)
echo [OK] Python environment detected.
python -c "import sys; sys.path.insert(0, '.'); from software.shared.battery_simulator import BatterySimulator; from software.shared.battery_chemistry import get_chemistry; sim = BatterySimulator(); chem = get_chemistry('li_ion'); print('[OK] Microservice shared physics package (software.shared) strictly verified.')"
if !errorlevel! neq 0 (
    echo [ERROR] Microservice shared physics package check failed.
    set /a FAILURES+=1
)
echo.

:: ── STEP 2: Run Full Pytest Suite ──────────────────────────────────────────
echo [2/8] Running Complete Pytest Suite (46 Unit/Integration Tests)...
python -m pytest "%ROOT_DIR%tests"
if !errorlevel! neq 0 (
    echo [ERROR] Pytest suite execution failed.
    set /a FAILURES+=1
) else (
    echo [SUCCESS] Full Pytest suite executed and all tests passed.
)
echo.

:: ── STEP 3: Software Model Training ──────────────────────────────────────
echo [3/8] [SOFTWARE] Training and Exporting Software ESN (model_rc.pkl)...
python "%ROOT_DIR%software\visualiser\training\train_rc.py"
if !errorlevel! neq 0 (
    echo [ERROR] Software ESN training failed.
    set /a FAILURES+=1
) else (
    echo [SUCCESS] Software ESN model trained and saved to software/visualiser/model_rc.pkl.
)
echo.

:: ── STEP 4: Software Estimator & Simulator Verification ─────────────────
echo [4/8] [SOFTWARE] Testing Physics Simulator and Estimator Pipeline...
python -c "import sys; sys.path.insert(0, '.'); sys.path.insert(0, 'software/visualiser'); from software.shared.battery_simulator import BatterySimulator; sim = BatterySimulator(); st = sim.step(-2.0, 1.0); from estimator_pipeline import EstimatorPipeline; ep = EstimatorPipeline(); res = ep.step(V_meas=st['voltage'], I_meas_discharge=st['current'], T_meas=st['temperature']); print('[TEST PASSED] Physics step V=', round(st['voltage'],3), 'V | EKF SOC=', round(res['ekf_soc'],4), '| UKF SOC=', round(res['ukf_soc'],4))"
if !errorlevel! neq 0 (
    echo [ERROR] Software Estimator and Simulator verification failed.
    set /a FAILURES+=1
) else (
    echo [SUCCESS] Software Physics Simulator and Estimator Pipeline verified.
)
echo.

:: ── STEP 5: Hardware STM32 ESN Classifier Training & Export ─────────────
echo [5/8] [HARDWARE - STM32] Training ESN Classifier and Exporting C Headers...
python "%ROOT_DIR%hardware\STM_Verifier\train_classifier.py"
if !errorlevel! neq 0 (
    echo [ERROR] STM32 ESN Classifier training failed.
    set /a FAILURES+=1
) else (
    echo [SUCCESS] STM32 ESN Classifier weights exported to esn_classifier_weights.h.
)
echo.

:: ── STEP 6: Hardware STM32 ESN Estimator Training & Export ──────────────
echo [6/8] [HARDWARE - STM32] Training ESN Estimator and Exporting C Headers...
python "%ROOT_DIR%hardware\STM_Verifier\train_estimator.py"
if !errorlevel! neq 0 (
    echo [ERROR] STM32 ESN Estimator training failed.
    set /a FAILURES+=1
) else (
    echo [SUCCESS] STM32 ESN Estimator weights exported to esn_estimator_weights.h.
)
echo.

:: ── STEP 7: Hardware FPGA Verilog RTL Golden Model Verification ──────────
echo [7/8] [HARDWARE - FPGA] Verifying Verilog RTL vs Python Golden Model...
python "%ROOT_DIR%hardware\FPGA_Verifier\compare_results.py"
if !errorlevel! neq 0 (
    echo [ERROR] FPGA Verilog RTL comparison failed.
    set /a FAILURES+=1
) else (
    echo [SUCCESS] FPGA Verilog RTL matched golden reference model bit-exactly.
)
echo.

:: ── STEP 8: C99 Microcontroller Desktop Simulator Compilation & Run ──────
echo [8/8] [HARDWARE - C99] Compiling and Executing C99 Edge Simulator...
set VALIDATION_PIPELINE=1
call "%ROOT_DIR%hardware\STM_Verifier\run_c_simulator.bat"
if !errorlevel! neq 0 (
    echo [ERROR] C99 Microcontroller Simulator build or execution failed.
    set /a FAILURES+=1
) else (
    echo [SUCCESS] C99 Microcontroller Simulator executed cleanly.
)
echo.

:: ── SUMMARY & USER INSTRUCTIONS ───────────────────────────────────────────
:summary
echo =======================================================================
if !FAILURES! equ 0 goto passed
goto failed

:passed
echo   [ALL PASSED] END-TO-END HARDWARE AND SOFTWARE VALIDATION SUCCESSFUL!
echo =======================================================================
echo.
echo  To run the Software Web Services manually, open two terminal windows:
echo.
echo    Terminal 1 (Physics Simulator - Port 8000):
echo      python software/simulator/app.py
echo.
echo    Terminal 2 (Visualiser Dashboard - Port 5000):
echo      python software/visualiser/app.py
echo.
echo  Access Visualiser Dashboard UI at: http://localhost:5000
echo =======================================================================
goto finish

:failed
echo   [FAILED] VALIDATION COMPLETED WITH !FAILURES! ERROR(S).
echo =======================================================================

:finish
echo.
if not defined NON_INTERACTIVE pause
if !FAILURES! neq 0 exit /b 1

