#!/usr/bin/env python3
"""
Battery State Estimator — Unified 1-Click System Launcher
=========================================================
Starts both the 2-RC Physics Simulator (Port 8000) and Web Visualiser Dashboard (Port 5000)
concurrently, verifies service health, automatically opens the dashboard in your default browser,
and manages graceful cross-platform shutdown on Ctrl+C.
"""

import os
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from typing import Optional

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a given network port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def wait_for_port(port: int, timeout: float = 15.0, host: str = "127.0.0.1") -> bool:
    """Wait until a local port opens and accepts TCP connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_in_use(port, host):
            return True
        time.sleep(0.3)
    return False

def check_dependencies() -> bool:
    """Verify that core runtime dependencies are installed."""
    missing = []
    for pkg in ("flask", "numpy", "scipy"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("\n[ERROR] Missing required Python packages:")
        for m in missing:
            print(f"  - {m}")
        print("\nPlease run the following command to install dependencies:")
        print(f"  {sys.executable} -m pip install -r requirements.txt\n")
        return False
    return True

def print_banner():
    banner = r"""
=======================================================================
   BATTERY STATE ESTIMATOR: AN ESN-BASED ALTERNATIVE TO EKF & CC
                  Unified 1-Click System Launcher
=======================================================================
    """
    print(banner.strip())
    print()

def main():
    print_banner()

    if not check_dependencies():
        sys.exit(1)

    sim_port = 8000
    vis_port = 5000

    if is_port_in_use(sim_port):
        print(f"[WARNING] Port {sim_port} is already in use. A simulator instance may already be running.")
    if is_port_in_use(vis_port):
        print(f"[WARNING] Port {vis_port} is already in use. A visualiser instance may already be running.")

    sim_script = os.path.join(ROOT_DIR, "software", "simulator", "app.py")
    vis_script = os.path.join(ROOT_DIR, "software", "visualiser", "app.py")

    if not os.path.isfile(sim_script):
        print(f"[ERROR] Cannot locate simulator script at: {sim_script}")
        sys.exit(1)
    if not os.path.isfile(vis_script):
        print(f"[ERROR] Cannot locate visualiser script at: {vis_script}")
        sys.exit(1)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    sim_proc: Optional[subprocess.Popen] = None
    vis_proc: Optional[subprocess.Popen] = None

    def shutdown_services(signum=None, frame=None):
        print("\n\nShutting down services gracefully...")
        for name, proc in [("Visualiser Dashboard", vis_proc), ("Physics Simulator", sim_proc)]:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=3.0)
                    print(f"  [OK] {name} terminated.")
                except Exception:
                    try:
                        proc.kill()
                        print(f"  [FORCED] {name} killed.")
                    except Exception:
                        pass
        print("All processes stopped cleanly. Goodbye!\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_services)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown_services)

    try:
        # 1. Start Physics Simulator
        print(f"[1/2] Launching 2-RC Battery Physics Simulator on port {sim_port}...")
        sim_proc = subprocess.Popen(
            [sys.executable, sim_script],
            cwd=os.path.join(ROOT_DIR, "software", "simulator"),
            env=env
        )

        if not wait_for_port(sim_port, timeout=12.0):
            print(f"[WARN] Simulator did not respond on port {sim_port} within timeout (continuing)...")
        else:
            print(f"      [OK] Physics Simulator active at: http://localhost:{sim_port}")

        # 2. Start Web Visualiser
        print(f"[2/2] Launching Web Visualiser & Estimator Pipeline on port {vis_port}...")
        vis_proc = subprocess.Popen(
            [sys.executable, vis_script],
            cwd=os.path.join(ROOT_DIR, "software", "visualiser"),
            env=env
        )

        if not wait_for_port(vis_port, timeout=12.0):
            print(f"[WARN] Visualiser did not respond on port {vis_port} within timeout (continuing)...")
        else:
            print(f"      [OK] Web Visualiser active at: http://localhost:{vis_port}")

        print("\n" + "=" * 71)
        print("  LIVE BMS OBSERVER SYSTEM IS RUNNING!")
        print("=" * 71)
        print(f"  • Visualiser UI:     http://localhost:{vis_port}")
        print(f"  • Physics Simulator: http://localhost:{sim_port}")
        print("  • Architecture:      Decoupled Real-Time Pub/Sub")
        print("=" * 71)
        print("Press Ctrl+C at any time to stop all services.\n")

        # Automatically open browser
        dashboard_url = f"http://localhost:{vis_port}"
        try:
            time.sleep(1.0)
            webbrowser.open(dashboard_url)
        except Exception:
            pass

        # Monitor processes
        while True:
            time.sleep(1.0)
            if sim_proc.poll() is not None:
                print(f"\n[ALERT] Physics Simulator exited with code {sim_proc.returncode}.")
                break
            if vis_proc.poll() is not None:
                print(f"\n[ALERT] Web Visualiser exited with code {vis_proc.returncode}.")
                break

    except KeyboardInterrupt:
        pass
    finally:
        shutdown_services()

if __name__ == "__main__":
    main()
