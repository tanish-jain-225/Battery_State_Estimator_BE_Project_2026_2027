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

        # States
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
        :param current: Applied current in Amperes (Positive = Charge, Negative = Discharge)
        :param dt: Time step in seconds
        :param accelerated_aging: If True, speeds up degradation rates
        :param fault_thermal: If True, inject thermal runaway self-heating
        :param fault_dropout: If True, indicates sensors are dropped out (handled in noise generation)
        :param fault_short: If True, injects an internal leakage micro-short circuit current
        """
        self.time += dt

        # Apply internal leakage current if micro-short fault is active
        # The leakage current drains the cells internally but is hidden from the external sensor
        I_leak = Config.FAULT_SHORT_LEAKAGE_CURRENT if fault_short else 0.0
        current_internal = current - I_leak

        # 1. Thermal and degradation effects on parameters
        temp_kelvin = self.temperature + 273.15
        temp_ref_kelvin = 25.0 + 273.15
        
        # Arrhenius temperature dependence
        temp_effect = np.exp(1500 * (1 / temp_kelvin - 1 / temp_ref_kelvin))

        R0 = self.R0_nom * self.internal_resistance_growth * temp_effect
        R1 = self.R1_nom * temp_effect
        C1 = self.C1_nom / temp_effect
        R2 = self.R2_nom * temp_effect
        C2 = self.C2_nom / temp_effect
        
        active_capacity = self.nominal_capacity * self.soh  # Ah

        # 2. State of Charge Update (Coulomb Counting)
        # current is in Amperes, capacity is in Ampere-hours. Convert to hours: dt / 3600
        dSOC = (current_internal * dt) / (active_capacity * 3600.0)
        self.soc = np.clip(self.soc + dSOC, 0.0, 1.0)

        # 3. Polarization Voltage Update (First-order differential equation for 2 RC branches)
        # dV1/dt = (current - V1/R1) / C1
        # dV2/dt = (current - V2/R2) / C2
        dV1 = ((current_internal - self.V1 / R1) / C1) * dt
        dV2 = ((current_internal - self.V2 / R2) / C2) * dt
        self.V1 += dV1
        self.V2 += dV2

        # 4. Thermal Model Update (Joule Heating + Convective Cooling + Runway)
        # Heat generated from external load and polarization losses
        heat_generated = (current_internal * current_internal * R0) + abs(current_internal * self.V1) + abs(current_internal * self.V2)
        
        if fault_short:
            # Direct short-circuit heating contribution
            heat_generated += Config.FAULT_SHORT_HEATING_RATE
            
        cooling = self.cooling_coefficient * (self.temperature - self.T_ambient)
        
        dT = ((heat_generated - cooling) / self.thermal_capacitance) * dt
        
        if fault_thermal:
            # Exponential thermal runaway heat spike
            dT_runaway = Config.FAULT_THERMAL_RUNAWAY_MULT * np.exp(
                Config.FAULT_THERMAL_RUNAWAY_EXP * (self.temperature - 25.0)
            )
            dT += dT_runaway * dt
            
        self.temperature = max(self.T_ambient, min(1000.0, self.temperature + dT))

        # 5. State of Health (SOH) Degradation Model
        # SOH capacity fade depends on current amplitude, temperature, and cumulative cycles
        aging_multiplier = 1500.0 if accelerated_aging else 1.0
        temp_aging_factor = np.exp(0.06 * (self.temperature - 25.0))
        current_aging_factor = np.power(abs(current_internal), 1.3)
        capacity_fade = -1.2e-7 * current_aging_factor * temp_aging_factor * aging_multiplier * dt
        
        self.soh = max(0.2, self.soh + capacity_fade)

        # Resistance growth matches capacity fade
        self.internal_resistance_growth = 1.0 + (1.0 - self.soh) * 1.5

        # 6. Calculate Terminal Voltage
        ocv = self.chemistry.lookup_ocv(self.soc)
        terminal_voltage = ocv + (current_internal * R0) + self.V1 + self.V2
        
        # Clip terminal voltage based on chemistry cell counts
        n_cells = self.chemistry.n_cells
        min_v = 1.5 * n_cells
        max_v = 4.5 * n_cells
        terminal_voltage = np.clip(terminal_voltage, min_v, max_v)

        return {
            'time': self.time,
            'true_soc': self.soc,
            'true_soh': self.soh,
            'ocv': ocv,
            'v1': self.V1,
            'v2': self.V2,
            'voltage': terminal_voltage,
            'current': current, # External current measured at terminal
            'temperature': self.temperature,
            'R0': R0
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
                'true_soh': state['true_soh']
            }
            
        return {
            'time': state['time'],
            'voltage': max(0.0, state['voltage'] + random.normalvariate(0, v_noise)),
            'current': state['current'] + random.normalvariate(0, i_noise),
            'temperature': state['temperature'] + random.normalvariate(0, t_noise),
            'true_soc': state['true_soc'],
            'true_soh': state['true_soh']
        }

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
