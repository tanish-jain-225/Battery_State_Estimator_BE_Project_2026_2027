"""
software/shared
───────────────
Canonical shared battery physics, chemistry, and drive-cycle package
for the Battery State Estimator cyber-physical system.
"""

from .battery_chemistry import CHEMISTRIES, BatteryChemistry, get_chemistry, register_chemistry
from .battery_simulator import BatterySimulator, DriveCycles

__all__ = [
    'BatteryChemistry',
    'get_chemistry',
    'register_chemistry',
    'CHEMISTRIES',
    'BatterySimulator',
    'DriveCycles'
]
