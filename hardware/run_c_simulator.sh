#!/bin/bash

# Move to the script's directory
cd "$(dirname "$0")"

echo "=============================================="
echo "  STM32 ESN Classifier C Simulator Build"
echo "=============================================="

# Check for gcc
if command -v gcc &> /dev/null; then
    echo "[FOUND] GCC compiler. Compiling main.c..."
    gcc -O2 -Wall -std=c99 main.c -lm -o esn_simulator
    if [ $? -eq 0 ]; then
        echo "[SUCCESS] Compilation complete. Running simulator..."
        echo "----------------------------------------------"
        ./esn_simulator
        rm esn_simulator
    else
        echo "[ERROR] Compilation failed."
    fi
# Check for clang
elif command -v clang &> /dev/null; then
    echo "[FOUND] Clang compiler. Compiling main.c..."
    clang -O2 -Wall -std=c99 main.c -lm -o esn_simulator
    if [ $? -eq 0 ]; then
        echo "[SUCCESS] Compilation complete. Running simulator..."
        echo "----------------------------------------------"
        ./esn_simulator
        rm esn_simulator
    else
        echo "[ERROR] Compilation failed."
    fi
else
    echo "[ERROR] No compatible C compiler (gcc or clang) was found in your PATH."
    echo "Please install a C compiler and try again."
fi
