import pytest
from software.shared.battery_chemistry import get_chemistry, register_chemistry, CHEMISTRIES

def test_get_chemistry():
    chem = get_chemistry("nmc")
    assert chem.name == "NMC"
    assert chem.nominal_capacity == 2.5
    
    # Test fallback
    fallback = get_chemistry("non_existent_chemistry")
    assert fallback.name == "Li-ion"

def test_ocv_lookup():
    chem = get_chemistry("nmc")
    ocv_full = chem.lookup_ocv(1.0)
    ocv_empty = chem.lookup_ocv(0.0)
    
    assert ocv_full == 4.20
    assert ocv_empty == 3.00
    assert ocv_full > ocv_empty

def test_register_chemistry():
    custom_ocv = [(0.0, 3.0), (0.5, 3.7), (1.0, 4.2)]
    chem = register_chemistry(
        name="CustomChem",
        nominal_capacity=5.0,
        R0_nom=0.01,
        R1_nom=0.01,
        C1_nom=1000,
        R2_nom=0.01,
        C2_nom=2000,
        thermal_capacitance=100.0,
        cooling_coefficient=0.5,
        ocv_table=custom_ocv,
        n_cells=1
    )
    assert chem.name == "CustomChem"
    assert get_chemistry("customchem").nominal_capacity == 5.0
