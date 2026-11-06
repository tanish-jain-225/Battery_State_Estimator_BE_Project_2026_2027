@echo off
setlocal
title Battery State Estimator - Live System Launcher

echo Starting Battery State Estimator Services...
python "%~dp0start_system.py" %*

if %errorlevel% neq 0 (
    echo.
    echo System startup ended with an error code: %errorlevel%
    pause
)

