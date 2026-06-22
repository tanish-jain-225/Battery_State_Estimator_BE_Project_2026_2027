import numpy as np

class BatteryChemistry:
    def __init__(self, name, nominal_capacity, R0_nom, R1_nom, C1_nom, R2_nom, C2_nom, thermal_capacitance, cooling_coefficient, ocv_table, n_cells):
        self.name = name
        self.nominal_capacity = nominal_capacity  # Ah
        self.R0_nom = R0_nom                      # Ohms
        self.R1_nom = R1_nom                      # Ohms
        self.C1_nom = C1_nom                      # Farads
        self.R2_nom = R2_nom                      # Ohms
        self.C2_nom = C2_nom                      # Farads
        self.thermal_capacitance = thermal_capacitance  # J/K
        self.cooling_coefficient = cooling_coefficient  # W/K
        self.ocv_table = ocv_table                      # List of (SOC, OCV)
        self.n_cells = n_cells

    def lookup_ocv(self, soc):
        s = np.clip(soc, 0.0, 1.0)
        socs = [x[0] for x in self.ocv_table]
        ocvs = [x[1] for x in self.ocv_table]
        return float(np.interp(s, socs, ocvs))

# NMC 3S (3 Cells in Series, 11.1V nominal)
NMC_OCV_TABLE = [
    (0.00, 3.00 * 3),
    (0.05, 3.25 * 3),
    (0.10, 3.45 * 3),
    (0.20, 3.60 * 3),
    (0.30, 3.68 * 3),
    (0.40, 3.73 * 3),
    (0.50, 3.77 * 3),
    (0.60, 3.82 * 3),
    (0.70, 3.90 * 3),
    (0.80, 3.99 * 3),
    (0.90, 4.08 * 3),
    (0.95, 4.15 * 3),
    (1.00, 4.20 * 3)
]
NMC_Chemistry = BatteryChemistry(
    name="NMC",
    nominal_capacity=2.5,
    R0_nom=0.025 * 3,
    R1_nom=0.015 * 3,
    C1_nom=1200 / 3,
    R2_nom=0.020 * 3,
    C2_nom=5000 / 3,
    thermal_capacitance=80.0,
    cooling_coefficient=0.25,
    ocv_table=NMC_OCV_TABLE,
    n_cells=3
)

# LFP 3S (3 Cells in Series, 9.6V nominal, very flat OCV)
LFP_OCV_TABLE = [
    (0.00, 2.50 * 3),
    (0.05, 3.00 * 3),
    (0.10, 3.12 * 3),
    (0.20, 3.20 * 3),
    (0.30, 3.24 * 3),
    (0.40, 3.25 * 3),
    (0.50, 3.26 * 3),
    (0.60, 3.27 * 3),
    (0.70, 3.28 * 3),
    (0.80, 3.29 * 3),
    (0.90, 3.30 * 3),
    (0.95, 3.40 * 3),
    (1.00, 3.60 * 3)
]
LFP_Chemistry = BatteryChemistry(
    name="LFP",
    nominal_capacity=3.0,
    R0_nom=0.018 * 3,
    R1_nom=0.010 * 3,
    C1_nom=1500 / 3,
    R2_nom=0.015 * 3,
    C2_nom=6000 / 3,
    thermal_capacitance=90.0,
    cooling_coefficient=0.30,
    ocv_table=LFP_OCV_TABLE,
    n_cells=3
)

# Lead-Acid 6S (6 Cells in Series, 12.0V nominal)
LeadAcid_OCV_TABLE = [
    (0.00, 1.75 * 6),
    (0.05, 1.85 * 6),
    (0.10, 1.90 * 6),
    (0.20, 1.95 * 6),
    (0.30, 1.98 * 6),
    (0.40, 2.00 * 6),
    (0.50, 2.02 * 6),
    (0.60, 2.04 * 6),
    (0.70, 2.06 * 6),
    (0.80, 2.08 * 6),
    (0.90, 2.11 * 6),
    (0.95, 2.13 * 6),
    (1.00, 2.15 * 6)
]
LeadAcid_Chemistry = BatteryChemistry(
    name="Lead Acid",
    nominal_capacity=7.0,
    R0_nom=0.008 * 6,
    R1_nom=0.005 * 6,
    C1_nom=2000 / 6,
    R2_nom=0.007 * 6,
    C2_nom=8000 / 6,
    thermal_capacitance=200.0,
    cooling_coefficient=0.15,
    ocv_table=LeadAcid_OCV_TABLE,
    n_cells=6
)

# Generic Li-ion 3S (uses NMC profile)
LiIon_Chemistry = BatteryChemistry(
    name="Li-ion",
    nominal_capacity=2.5,
    R0_nom=0.025 * 3,
    R1_nom=0.015 * 3,
    C1_nom=1200 / 3,
    R2_nom=0.020 * 3,
    C2_nom=5000 / 3,
    thermal_capacitance=80.0,
    cooling_coefficient=0.25,
    ocv_table=NMC_OCV_TABLE,
    n_cells=3
)

CHEMISTRIES = {
    "nmc": NMC_Chemistry,
    "lfp": LFP_Chemistry,
    "lead_acid": LeadAcid_Chemistry,
    "li_ion": LiIon_Chemistry
}

def get_chemistry(name):
    clean_name = str(name).lower().replace(" ", "_").replace("-", "_")
    return CHEMISTRIES.get(clean_name, LiIon_Chemistry)
