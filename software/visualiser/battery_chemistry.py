"""
software/visualiser/battery_chemistry.py
─────────────────────────────────────────
Wrapper forwarding imports to canonical package software.shared.battery_chemistry.
"""
import sys
import os

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from software.shared.battery_chemistry import (
    BatteryChemistry,
    get_chemistry,
    register_chemistry,
    CHEMISTRIES,
    NMC_Chemistry,
    LFP_Chemistry,
    LeadAcid_Chemistry,
    LiIon_Chemistry
)

__all__ = [
    'BatteryChemistry',
    'get_chemistry',
    'register_chemistry',
    'CHEMISTRIES',
    'NMC_Chemistry',
    'LFP_Chemistry',
    'LeadAcid_Chemistry',
    'LiIon_Chemistry'
]
