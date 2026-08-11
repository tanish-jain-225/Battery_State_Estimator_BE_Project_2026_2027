"""
software/simulator/battery_simulator.py
────────────────────────────────────────
Wrapper forwarding imports to canonical package software.shared.battery_simulator.
"""
import sys
import os

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from software.shared.battery_simulator import BatterySimulator, DriveCycles

__all__ = ['BatterySimulator', 'DriveCycles']
