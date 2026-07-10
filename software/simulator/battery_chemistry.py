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
        
        # Precompute numpy arrays to prevent slow list comprehensions in high-frequency lookup_ocv
        self.socs = np.array([x[0] for x in ocv_table])
        self.ocvs = np.array([x[1] for x in ocv_table])

    def lookup_ocv(self, soc):
        return float(np.interp(np.clip(soc, 0.0, 1.0), self.socs, self.ocvs))

# NMC (Single Cell, 3.7V nominal)
NMC_OCV_TABLE = [
    (0.00, 3.00),
    (0.05, 3.25),
    (0.10, 3.45),
    (0.20, 3.60),
    (0.30, 3.68),
    (0.40, 3.73),
    (0.50, 3.77),
    (0.60, 3.82),
    (0.70, 3.90),
    (0.80, 3.99),
    (0.90, 4.08),
    (0.95, 4.15),
    (1.00, 4.20)
]
NMC_Chemistry = BatteryChemistry(
    name="NMC",
    nominal_capacity=2.5,
    R0_nom=0.025,
    R1_nom=0.015,
    C1_nom=1200,
    R2_nom=0.020,
    C2_nom=5000,
    thermal_capacitance=80.0,
    cooling_coefficient=0.25,
    ocv_table=NMC_OCV_TABLE,
    n_cells=1
)

# LFP (Single Cell, 3.2V nominal, very flat OCV)
LFP_OCV_TABLE = [
    (0.00, 2.50),
    (0.05, 3.00),
    (0.10, 3.12),
    (0.20, 3.20),
    (0.30, 3.24),
    (0.40, 3.25),
    (0.50, 3.26),
    (0.60, 3.27),
    (0.70, 3.28),
    (0.80, 3.29),
    (0.90, 3.30),
    (0.95, 3.40),
    (1.00, 3.60)
]
LFP_Chemistry = BatteryChemistry(
    name="LFP",
    nominal_capacity=3.0,
    R0_nom=0.018,
    R1_nom=0.010,
    C1_nom=1500,
    R2_nom=0.015,
    C2_nom=6000,
    thermal_capacitance=90.0,
    cooling_coefficient=0.30,
    ocv_table=LFP_OCV_TABLE,
    n_cells=1
)

# Lead-Acid (Single Cell, 2.0V nominal)
LeadAcid_OCV_TABLE = [
    (0.00, 1.75),
    (0.05, 1.85),
    (0.10, 1.90),
    (0.20, 1.95),
    (0.30, 1.98),
    (0.40, 2.00),
    (0.50, 2.02),
    (0.60, 2.04),
    (0.70, 2.06),
    (0.80, 2.08),
    (0.90, 2.11),
    (0.95, 2.13),
    (1.00, 2.15)
]
LeadAcid_Chemistry = BatteryChemistry(
    name="Lead Acid",
    nominal_capacity=7.0,
    R0_nom=0.008,
    R1_nom=0.005,
    C1_nom=2000,
    R2_nom=0.007,
    C2_nom=8000,
    thermal_capacitance=200.0,
    cooling_coefficient=0.15,
    ocv_table=LeadAcid_OCV_TABLE,
    n_cells=1
)

# Generic Li-ion (uses NMC profile)
LiIon_Chemistry = BatteryChemistry(
    name="Li-ion",
    nominal_capacity=2.5,
    R0_nom=0.025,
    R1_nom=0.015,
    C1_nom=1200,
    R2_nom=0.020,
    C2_nom=5000,
    thermal_capacitance=80.0,
    cooling_coefficient=0.25,
    ocv_table=NMC_OCV_TABLE,
    n_cells=1
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

def register_chemistry(name, nominal_capacity, R0_nom, R1_nom, C1_nom, R2_nom, C2_nom, thermal_capacitance, cooling_coefficient, ocv_table, n_cells):
    """
    Registers a new battery chemistry profile dynamically at runtime.
    """
    clean_name = str(name).lower().replace(" ", "_").replace("-", "_")
    
    # Validate and structure ocv_table as list of (soc, ocv) tuples
    formatted_ocv_table = []
    for pair in ocv_table:
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            formatted_ocv_table.append((float(pair[0]), float(pair[1])))
    
    # Sort OCV table by SOC to ensure monotonic lookup behavior
    formatted_ocv_table.sort(key=lambda x: x[0])
    
    chem = BatteryChemistry(
        name=name,
        nominal_capacity=float(nominal_capacity),
        R0_nom=float(R0_nom),
        R1_nom=float(R1_nom),
        C1_nom=float(C1_nom),
        R2_nom=float(R2_nom),
        C2_nom=float(C2_nom),
        thermal_capacitance=float(thermal_capacitance),
        cooling_coefficient=float(cooling_coefficient),
        ocv_table=formatted_ocv_table,
        n_cells=int(n_cells)
    )
    
    CHEMISTRIES[clean_name] = chem
    return chem
