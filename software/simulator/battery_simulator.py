import numpy as np
import random

try:
    from battery_chemistry import get_chemistry
    from config import Config
except ImportError:
    from simulator.battery_chemistry import get_chemistry
    from simulator.config import Config

class BatterySimulator:
    def __init__(self, chemistry_name="li_ion"):
        self.chemistry_name = chemistry_name
        self.chemistry = get_chemistry(chemistry_name)
        self.reset(chemistry_name)

    def change_chemistry(self, chemistry_name):
        self.chemistry_name = chemistry_name
        self.chemistry = get_chemistry(chemistry_name)

        # Hydrate parameters from chemistry without resetting active states
        self.nominal_capacity = self.chemistry.nominal_capacity  # Ah
        self.R0_nom = self.chemistry.R0_nom                      # Ohms
        self.R1_nom = self.chemistry.R1_nom                      # Ohms
        self.C1_nom = self.chemistry.C1_nom                      # Farads
        self.R2_nom = self.chemistry.R2_nom                      # Ohms
        self.C2_nom = self.chemistry.C2_nom                      # Farads
        self.thermal_capacitance = self.chemistry.thermal_capacitance  # J/K
        self.cooling_coefficient = self.chemistry.cooling_coefficient  # W/K
        self.n_cells = self.chemistry.n_cells

    def reset(self, chemistry_name=None):
        if chemistry_name is not None:
            self.chemistry_name = chemistry_name
            self.chemistry = get_chemistry(chemistry_name)

        # Hydrate parameters from chemistry
        self.nominal_capacity = self.chemistry.nominal_capacity  # Ah
        self.R0_nom = self.chemistry.R0_nom                      # Ohms
        self.R1_nom = self.chemistry.R1_nom                      # Ohms
        self.C1_nom = self.chemistry.C1_nom                      # Farads
        self.R2_nom = self.chemistry.R2_nom                      # Ohms
        self.C2_nom = self.chemistry.C2_nom                      # Farads
        self.thermal_capacitance = self.chemistry.thermal_capacitance  # J/K
        self.cooling_coefficient = self.chemistry.cooling_coefficient  # W/K
        self.n_cells = self.chemistry.n_cells

        # Define cell-to-cell variations for n_cells
        np.random.seed(42)  # for reproducibility
        self.cell_caps = []
        self.cell_r0s = []
        self.cell_r1s = []
        self.cell_c1s = []
        self.cell_r2s = []
        self.cell_c2s = []
        
        for i in range(self.n_cells):
            # Introduce cell unbalance: Cell 1 is nominal, Cell 2 is 98%, Cell 3 is 96%
            cap_factor = 1.0 - 0.02 * i
            res_factor = 1.0 + 0.05 * i
            
            self.cell_caps.append(self.nominal_capacity * cap_factor)
            self.cell_r0s.append((self.R0_nom / self.n_cells) * res_factor)
            self.cell_r1s.append((self.R1_nom / self.n_cells) * res_factor)
            self.cell_c1s.append((self.C1_nom * self.n_cells) / res_factor)
            self.cell_r2s.append((self.R2_nom / self.n_cells) * res_factor)
            self.cell_c2s.append((self.C2_nom * self.n_cells) / res_factor)
            
        # States for each cell
        self.cell_soc = [1.0] * self.n_cells
        self.cell_soh = [1.0] * self.n_cells
        self.cell_V1 = [0.0] * self.n_cells
        self.cell_V2 = [0.0] * self.n_cells
        # Introduce thermal gradients: cell 3 starts slightly hotter
        self.cell_temperature = [25.0 + 1.0 * i for i in range(self.n_cells)]
        self.cell_r_growth = [1.0] * self.n_cells
        
        self.balancing_active = [False] * self.n_cells

        # Legacy states for backward compatibility and test validation
        self.soc = 1.0                   # State of Charge (0.0 to 1.0)
        self.soh = 1.0                   # State of Health (0.0 to 1.0)
        self.V1 = 0.0                    # polarization voltage 1 (V)
        self.V2 = 0.0                    # polarization voltage 2 (V)
        self.temperature = 25.0          # Cell temperature (°C)
        self.time = 0.0                  # Simulation time (s)
        self.internal_resistance_growth = 1.0  # Multiplier for R0 based on aging
        self.T_ambient = 25.0            # Ambient temp (°C)

    def step(self, current, dt, accelerated_aging=False, fault_thermal=False, fault_dropout=False, fault_short=False):
        """
        Update the battery physics by one time step dt.
        """
        self.time += dt

        # Sync external state overrides (for backwards compatibility with direct test-suite writes)
        if abs(self.soc - np.mean(self.cell_soc)) > 1e-4:
            self.cell_soc = [self.soc] * self.n_cells
        if abs(self.soh - np.min(self.cell_soh)) > 1e-4:
            self.cell_soh = [self.soh] * self.n_cells
        if abs(self.temperature - np.max(self.cell_temperature)) > 1e-4:
            self.cell_temperature = [self.temperature] * self.n_cells

        cell_voltages = []
        cell_ocvs = []

        # Update each cell in series
        for i in range(self.n_cells):
            # Apply balance bleed current if active
            I_bleed = 0.05 if self.balancing_active[i] else 0.0
            
            # Apply short-circuit leakage to Cell 3 (last cell) specifically
            I_leak = 0.0
            if fault_short and i == self.n_cells - 1:
                I_leak = Config.FAULT_SHORT_LEAKAGE_CURRENT
                
            # Current through cell i (Positive = Charge, Negative = Discharge)
            current_internal = current - I_bleed - I_leak
                
            # Temperature and degradation effects
            temp_kelvin = self.cell_temperature[i] + 273.15
            temp_ref_kelvin = 25.0 + 273.15
            temp_effect = np.exp(1500 * (1 / temp_kelvin - 1 / temp_ref_kelvin))
            
            R0 = self.cell_r0s[i] * self.cell_r_growth[i] * temp_effect
            R1 = self.cell_r1s[i] * temp_effect
            C1 = self.cell_c1s[i] / temp_effect
            R2 = self.cell_r2s[i] * temp_effect
            C2 = self.cell_c2s[i] / temp_effect
            
            active_cap = self.cell_caps[i] * self.cell_soh[i]
            
            # SOC update
            dSOC = (current_internal * dt) / (active_cap * 3600.0)
            self.cell_soc[i] = float(np.clip(self.cell_soc[i] + dSOC, 0.0, 1.0))
            
            # Polarization voltages
            dV1 = ((current_internal - self.cell_V1[i] / R1) / C1) * dt
            dV2 = ((current_internal - self.cell_V2[i] / R2) / C2) * dt
            self.cell_V1[i] += dV1
            self.cell_V2[i] += dV2
            
            # OCV lookup (scaled per cell)
            cell_ocv = self.chemistry.lookup_ocv(self.cell_soc[i]) / self.n_cells
            cell_ocvs.append(cell_ocv)
            
            cell_v = cell_ocv + (current_internal * R0) + self.cell_V1[i] + self.cell_V2[i]
            cell_voltages.append(cell_v)
            
            # Heat generation
            heat_gen = (current_internal * current_internal * R0) + abs(current_internal * self.cell_V1[i]) + abs(current_internal * self.cell_V2[i])
            if fault_short and i == self.n_cells - 1:
                heat_gen += Config.FAULT_SHORT_HEATING_RATE
                
            cooling = self.cooling_coefficient * (self.cell_temperature[i] - self.T_ambient) / self.n_cells
            dT = ((heat_gen - cooling) / (self.thermal_capacitance / self.n_cells)) * dt
            
            # Apply thermal runaway to Cell 3 specifically
            if fault_thermal and i == self.n_cells - 1:
                dT_runaway = Config.FAULT_THERMAL_RUNAWAY_MULT * np.exp(
                    Config.FAULT_THERMAL_RUNAWAY_EXP * (self.cell_temperature[i] - 25.0)
                )
                dT += dT_runaway * dt
                
            self.cell_temperature[i] = float(max(self.T_ambient, min(1000.0, self.cell_temperature[i] + dT)))
            
            # SOH degradation
            aging_mult = 1500.0 if accelerated_aging else 1.0
            temp_aging_fac = np.exp(0.06 * (self.cell_temperature[i] - 25.0))
            current_aging_fac = np.power(abs(current_internal), 1.3)
            cap_fade = -1.2e-7 * current_aging_fac * temp_aging_fac * aging_mult * dt
            
            self.cell_soh[i] = float(max(0.2, self.cell_soh[i] + cap_fade))
            self.cell_r_growth[i] = 1.0 + (1.0 - self.cell_soh[i]) * 1.5
            
        # Determine cell balancing decisions for the next step (active charging > 0.05A)
        min_v_cell = min(cell_voltages)
        for i in range(self.n_cells):
            if cell_voltages[i] > (4.10 / 3.0 * self.n_cells) and (cell_voltages[i] - min_v_cell) > 0.010 and current > 0.05:
                self.balancing_active[i] = True
            else:
                self.balancing_active[i] = False
                
        # Pack aggregation for single-cell backwards compatibility
        self.soc = float(np.mean(self.cell_soc))
        self.soh = float(np.min(self.cell_soh)) # capacity is bottlenecked by the weakest cell
        self.V1 = float(np.mean(self.cell_V1))
        self.V2 = float(np.mean(self.cell_V2))
        self.temperature = float(np.max(self.cell_temperature)) # Report peak cell temp
        self.internal_resistance_growth = float(np.mean(self.cell_r_growth))
        
        pack_voltage = float(np.sum(cell_voltages))
        
        # Clip pack voltage
        min_v = 1.5 * self.n_cells
        max_v = 4.5 * self.n_cells
        pack_voltage = float(np.clip(pack_voltage, min_v, max_v))
        
        return {
            'time': self.time,
            'true_soc': self.soc,
            'true_soh': self.soh,
            'ocv': float(np.sum(cell_ocvs)),
            'v1': self.V1,
            'v2': self.V2,
            'voltage': pack_voltage,
            'current': current,
            'temperature': self.temperature,
            'R0': float(np.sum(self.cell_r0s) * self.internal_resistance_growth),
            
            # Multi-cell telemetry outputs
            'cell_voltages': [float(v) for v in cell_voltages],
            'cell_socs': [float(s) for s in self.cell_soc],
            'cell_temperatures': [float(t) for t in self.cell_temperature],
            'balancing_active': self.balancing_active.copy()
        }

    def add_sensor_noise(self, state, v_noise=0.005, i_noise=0.05, t_noise=0.2, fault_dropout=False):
        """
        Add measurement noise to simulate real-world physical sensors, or simulate sensor dropout.
        """
        if fault_dropout:
            return {
                'time': state['time'],
                'voltage': 0.0,
                'current': 0.0,
                'temperature': 25.0, # Pulled to ambient temperature
                'true_soc': state['true_soc'],
                'true_soh': state['true_soh'],
                'cell_voltages': [0.0] * self.n_cells,
                'cell_socs': [0.0] * self.n_cells,
                'cell_temperatures': [25.0] * self.n_cells,
                'balancing_active': [False] * self.n_cells
            }
            
        noisy_rec = {
            'time': state['time'],
            'voltage': max(0.0, state['voltage'] + random.normalvariate(0, v_noise)),
            'current': state['current'] + random.normalvariate(0, i_noise),
            'temperature': state['temperature'] + random.normalvariate(0, t_noise),
            'true_soc': state['true_soc'],
            'true_soh': state['true_soh']
        }
        
        # Inject noise into cell-level arrays if present
        if 'cell_voltages' in state:
            noisy_rec['cell_voltages'] = [max(0.0, v + random.normalvariate(0, v_noise / np.sqrt(self.n_cells))) for v in state['cell_voltages']]
            noisy_rec['cell_socs'] = state['cell_socs'].copy()
            noisy_rec['cell_temperatures'] = [t + random.normalvariate(0, t_noise) for t in state['cell_temperatures']]
            noisy_rec['balancing_active'] = state['balancing_active'].copy()
            
        return noisy_rec

# Drive cycle current profiles (Amps) based on time t (seconds)
class DriveCycles:
    @staticmethod
    def udds(t):
        current = -1.5
        current += 2.5 * np.sin(2 * np.pi * 0.01 * t)
        current += 1.5 * np.sin(2 * np.pi * 0.035 * t)
        current += 0.8 * np.sin(2 * np.pi * 0.07 * t)
        
        if (t % 120 > 30) and (t % 120 < 45):
            current -= 3.5
        if (t % 80 > 65) and (t % 80 < 75):
            current += 4.0
            
        return float(np.clip(current, -8.0, 4.0))

    @staticmethod
    def hwfet(t):
        current = -2.8
        current += 0.8 * np.sin(2 * np.pi * 0.005 * t)
        current += 0.4 * np.sin(2 * np.pi * 0.02 * t)
        
        if (t % 150 > 90) and (t % 150 < 105):
            current -= 1.5
        if (t % 200 > 180) and (t % 200 < 190):
            current += 1.5
            
        return float(np.clip(current, -6.0, 1.0))

    @staticmethod
    def us06(t):
        current = -2.0
        current += 4.5 * np.sin(2 * np.pi * 0.025 * t)
        current += 2.5 * np.sin(2 * np.pi * 0.06 * t)
        current += 1.2 * np.sin(2 * np.pi * 0.15 * t)

        if (t % 90 > 15) and (t % 90 < 30):
            current -= 5.0
        if (t % 140 > 70) and (t % 140 < 85):
            current -= 6.0
        if (t % 100 > 45) and (t % 100 < 55):
            current += 6.5
            
        return float(np.clip(current, -12.0, 8.0))

    @staticmethod
    def constant_discharge(t):
        return -2.5

    @staticmethod
    def cccv_charge(t, current_soc):
        if current_soc < 0.80:
            return 2.5
        else:
            return float(max(0.1, 2.5 * (1.0 - current_soc) / 0.20))
