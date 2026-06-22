@echo off
setlocal enabledelayedexpansion

echo ==============================================
echo   STM32 ESN Classifier C Simulator Build
echo ==============================================

cd /d "%~dp0"

:: Check for gcc
where gcc >nul 2>nul
if !errorlevel! equ 0 (
    echo [FOUND] GCC compiler. Compiling main.c...
    gcc -O2 -Wall -std=c99 main.c -lm -o esn_simulator.exe
    if !errorlevel! equ 0 (
        echo [SUCCESS] Compilation complete. Running simulator...
        echo ----------------------------------------------
        esn_simulator.exe
        del esn_simulator.exe
    ) else (
        echo [ERROR] Compilation failed.
    )
    goto end
)

:: Check for clang
where clang >nul 2>nul
if !errorlevel! equ 0 (
    echo [FOUND] Clang compiler. Compiling main.c...
    clang -O2 -Wall -std=c99 main.c -lm -o esn_simulator.exe
    if !errorlevel! equ 0 (
        echo [SUCCESS] Compilation complete. Running simulator...
        echo ----------------------------------------------
        esn_simulator.exe
        del esn_simulator.exe
    ) else (
        echo [ERROR] Compilation failed.
    )
    goto end
)

:: Check for cl (MSVC)
where cl >nul 2>nul
if !errorlevel! equ 0 (
    echo [FOUND] MSVC compiler (cl). Compiling main.c...
    cl /O2 /W3 /D_CRT_SECURE_NO_WARNINGS main.c /Fe:esn_simulator.exe
    if !errorlevel! equ 0 (
        echo [SUCCESS] Compilation complete. Running simulator...
        echo ----------------------------------------------
        esn_simulator.exe
        del esn_simulator.exe
        del main.obj
    ) else (
        echo [ERROR] Compilation failed.
    )
    goto end
)

echo [ERROR] No compatible C compiler (gcc, clang, or cl) was found in your PATH.
echo Please install GCC (MinGW), Clang, or MSVC and try again.

:end
pause
