import pytest
import numpy as np
from software.shared.battery_simulator import BatterySimulator, DriveCycles

def test_simulator_initialization():
    sim = BatterySimulator("li_ion")
    assert sim.soc == 1.0
    assert sim.soh == 1.0
    assert sim.temperature == 25.0
    assert sim.time == 0.0

def test_simulator_step_discharge():
    sim = BatterySimulator("li_ion")
    initial_soc = sim.soc
    out = sim.step(current=2.0, dt=1.0)
    
    assert out['time'] == 1.0
    assert out['voltage'] > 0.0
    assert out['true_soc'] < initial_soc
    assert 'cell_voltages' in out
    assert 'cell_temperatures' in out
    assert 'v1' in out
    assert 'v2' in out
    assert 'r0' in out
    assert 'ocv' in out

def test_simulator_chemistry_change():
    sim = BatterySimulator("li_ion")
    sim.change_chemistry("lfp")
    assert sim.chemistry_name == "lfp"
    assert sim.nominal_capacity == 3.0

def test_drive_cycles():
    cycles = ['udds', 'hwfet', 'us06', 'constant_discharge', 'constant_charge', 'pulse']
    for c in cycles:
        current = DriveCycles.get_current(c, t=10.0)
        assert isinstance(current, float)
        
    assert isinstance(DriveCycles.udds(10.0), float)
    assert isinstance(DriveCycles.hwfet(10.0), float)
    assert isinstance(DriveCycles.us06(10.0), float)
    assert isinstance(DriveCycles.constant_discharge(10.0), float)
    assert isinstance(DriveCycles.constant_charge(10.0), float)
    assert isinstance(DriveCycles.pulse(10.0), float)

def test_sensor_noise():
    sim = BatterySimulator("li_ion")
    out = sim.step(current=2.0, dt=1.0)
    noisy = sim.add_sensor_noise(out, noise_level=0.05)
    assert 'voltage' in noisy
    assert 'current' in noisy
    assert 'temperature' in noisy

def test_fault_modes():
    sim = BatterySimulator("li_ion")
    out_short = sim.step(current=2.0, dt=1.0, fault_short=True)
    assert out_short['voltage'] > 0.0
    
    out_thermal = sim.step(current=2.0, dt=1.0, fault_thermal=True)
    assert out_thermal['temperature'] >= 25.0

def test_multi_cell_voltage():
    sim = BatterySimulator("li_ion")
    out = sim.step(current=0.0, dt=1.0)
    # Single cell NMC OCV at 100% SOC is 4.2V
    assert abs(out['voltage'] - 4.2) < 0.2
