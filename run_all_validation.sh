#!/usr/bin/env bash
# ===================================================
#   End-to-End Battery Estimator Validation Pipeline
# ===================================================
set -e

export VALIDATION_PIPELINE=1

echo "==================================================="
echo "  End-to-End Battery Estimator Validation Pipeline"
echo "==================================================="
echo ""

echo "[STEP 1/5] Training Software Reservoir Computer..."
python software/visualiser/training/train_rc.py
echo ""

echo "[STEP 2/5] Training Hardware ESN Estimator..."
python hardware/train_estimator.py
echo ""

echo "[STEP 3/5] Training Hardware ESN Classifier..."
python hardware/train_classifier.py
echo ""

echo "[STEP 4/5] Running Software Unit Tests..."
python -m unittest discover -s software/tests -t .
echo ""

echo "[STEP 5/5] Compiling and Running C Simulator..."
chmod +x hardware/run_c_simulator.sh
hardware/run_c_simulator.sh

echo "==================================================="
echo "  Pipeline Completed Successfully!"
echo "==================================================="
