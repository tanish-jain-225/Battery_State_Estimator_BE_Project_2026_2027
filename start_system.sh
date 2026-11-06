#!/usr/bin/env bash
# =======================================================================
# Battery State Estimator - POSIX Live System Launcher
# =======================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

exec "$PYTHON_BIN" "$DIR/start_system.py" "$@"

