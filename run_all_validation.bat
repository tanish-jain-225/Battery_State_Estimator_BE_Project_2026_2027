@echo off
set VALIDATION_PIPELINE=1
echo ===================================================
echo   End-to-End Battery Estimator Validation Pipeline
echo ===================================================
echo.
echo [STEP 1/5] Training Software Reservoir Computer...
python software/visualiser/training/train_rc.py
if %errorlevel% neq 0 (
    echo [ERROR] Software training failed.
    exit /b %errorlevel%
)
echo.
echo [STEP 2/5] Training Hardware ESN Estimator...
python hardware/train_estimator.py
if %errorlevel% neq 0 (
    echo [ERROR] Hardware estimator training failed.
    exit /b %errorlevel%
)
echo.
echo [STEP 3/5] Training Hardware ESN Classifier...
python hardware/train_classifier.py
if %errorlevel% neq 0 (
    echo [ERROR] Hardware classifier training failed.
    exit /b %errorlevel%
)
echo.
echo [STEP 4/5] Running Software Unit Tests...
python -m unittest discover -s software/tests
if %errorlevel% neq 0 (
    echo [ERROR] Unit tests failed.
    exit /b %errorlevel%
)
echo.
echo [STEP 5/5] Compiling and Running C Simulator...
call hardware/run_c_simulator.bat
echo ===================================================
echo   Pipeline Completed Successfully!
echo ===================================================
