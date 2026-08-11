import numpy as np
import random
import os
import sys

# Support relative or package import
try:
    from .battery_chemistry import get_chemistry
except ImportError:
    from battery_chemistry import get_chemistry

class DriveCycles:
    @staticmethod
    def get_current(cycle_type, t, dt=1.0):
        cycle = str(cycle_type).lower()
        if cycle == 'udds':
            # Urban Dynamometer Driving Schedule synthetic profile
            period = 1372.0
            t_rel = t % period
            val = 2.5 * np.sin(2 * np.pi * t_rel / 100.0) + \
                  4.0 * np.sin(2 * np.pi * t_rel / 300.0) + \
                  1.5 * np.cos(2 * np.pi * t_rel / 50.0)
            if (t_rel % 120) < 20:
                val = 0.0 # Idle stop
            elif (t_rel % 250) > 220:
                val = -3.5 # Regenerative braking charge
            return float(np.clip(val, -5.0, 10.0))
        elif cycle == 'hwfet':
            # Highway Fuel Economy Test profile (sustained discharge)
            period = 765.0
            t_rel = t % period
            val = 5.0 + 1.5 * np.sin(2 * np.pi * t_rel / 80.0) + 0.5 * np.sin(2 * np.pi * t_rel / 20.0)
            return float(np.clip(val, -2.0, 12.0))
        elif cycle == 'us06':
            # High acceleration aggressive drive cycle
            period = 600.0
            t_rel = t % period
            val = 6.0 * np.sin(2 * np.pi * t_rel / 40.0) + 3.0 * np.sin(2 * np.pi * t_rel / 15.0)
            if (t_rel % 90) > 75:
                val = -6.0 # Hard braking
            return float(np.clip(val, -8.0, 15.0))
        elif cycle == 'constant_discharge':
            return 2.5 # 2.5 A continuous
        elif cycle == 'constant_charge':
            return -2.5 # -2.5 A charging
        elif cycle == 'pulse':
            # Pulse discharge/charge profile
            t_rel = t % 100.0
            if t_rel < 30.0:
                return 4.0
            elif t_rel < 50.0:
                return 0.0
            elif t_rel < 80.0:
                return -2.0
            else:
                return 0.0
        else:
            return 1.5 # Default mild discharge

    @staticmethod
    def udds(t, dt=1.0):
        return DriveCycles.get_current('udds', t, dt)

    @staticmethod
    def hwfet(t, dt=1.0):
        return DriveCycles.get_current('hwfet', t, dt)

    @staticmethod
    def us06(t, dt=1.0):
        return DriveCycles.get_current('us06', t, dt)

    @staticmethod
    def constant_discharge(t, dt=1.0):
        return DriveCycles.get_current('constant_discharge', t, dt)

    @staticmethod
    def constant_charge(t, dt=1.0):
        return DriveCycles.get_current('constant_charge', t, dt)

    @staticmethod
    def pulse(t, dt=1.0):
        return DriveCycles.get_current('pulse', t, dt)

    @staticmethod
    def cccv_charge(t, soc=0.5, dt=1.0):
        if soc > 0.8:
            return -1.0
        return -3.0


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

    def add_sensor_noise(self, step_out, noise_level=0.01, v_noise=None, i_noise=None, t_noise=None, fault_dropout=False):
        """Adds Gaussian measurement noise to telemetry reading dict."""
        out = dict(step_out)
        v_std = v_noise if v_noise is not None else 0.05 * noise_level
        i_std = i_noise if i_noise is not None else 0.02 * noise_level
        t_std = t_noise if t_noise is not None else 0.1 * noise_level
        if v_std > 0 or i_std > 0 or t_std > 0:
            out['voltage'] += float(np.random.normal(0, v_std))
            out['current'] += float(np.random.normal(0, i_std))
            out['temperature'] += float(np.random.normal(0, t_std))
        return out

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

        # Sync external state overrides
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
            I_bleed = 0.05 if self.balancing_active[i] else 0.0
            
            I_leak = 0.0
            if fault_short and i == self.n_cells - 1:
                I_leak = 2.0 # 2A internal short leakage
                
            current_internal = current - I_bleed - I_leak
                
            temp_kelvin = self.cell_temperature[i] + 273.15
            temp_ref_kelvin = 25.0 + 273.15
            temp_effect = np.exp(1500 * (1 / temp_kelvin - 1 / temp_ref_kelvin))
            
            R0 = self.cell_r0s[i] * self.cell_r_growth[i] * temp_effect
            R1 = self.cell_r1s[i] * temp_effect
            C1 = self.cell_c1s[i] / temp_effect
            R2 = self.cell_r2s[i] * temp_effect
            C2 = self.cell_c2s[i] / temp_effect
            
            active_cap = self.cell_caps[i] * self.cell_soh[i]
            
            # SOC update (Current > 0 means discharge, Current < 0 means charge in physics conventions)
            dSOC = (current_internal * dt) / (active_cap * 3600.0)
            self.cell_soc[i] = float(np.clip(self.cell_soc[i] - dSOC, 0.0, 1.0))
            
            # Polarization voltages
            dV1 = ((current_internal - self.cell_V1[i] / R1) / C1) * dt
            dV2 = ((current_internal - self.cell_V2[i] / R2) / C2) * dt
            self.cell_V1[i] += dV1
            self.cell_V2[i] += dV2
            
            # OCV lookup per cell
            cell_ocv = self.chemistry.lookup_ocv(self.cell_soc[i])
            cell_ocvs.append(cell_ocv)
            
            cell_v = cell_ocv - (current_internal * R0) - self.cell_V1[i] - self.cell_V2[i]
            cell_voltages.append(cell_v)
            
            # Heat generation
            heat_gen = (current_internal * current_internal * R0) + abs(current_internal * self.cell_V1[i]) + abs(current_internal * self.cell_V2[i])
            if fault_short and i == self.n_cells - 1:
                heat_gen += 15.0 # 15W internal short heating
                
            cooling = self.cooling_coefficient * (self.cell_temperature[i] - self.T_ambient) / self.n_cells
            dT = ((heat_gen - cooling) / (self.thermal_capacitance / self.n_cells)) * dt
            
            if fault_thermal and i == self.n_cells - 1:
                dT_runaway = 0.5 * np.exp(0.08 * (self.cell_temperature[i] - 25.0))
                dT += dT_runaway * dt
                
            self.cell_temperature[i] = float(max(self.T_ambient, min(1000.0, self.cell_temperature[i] + dT)))
            
            # SOH degradation
            aging_mult = 1500.0 if accelerated_aging else 1.0
            temp_aging_fac = np.exp(0.06 * (self.cell_temperature[i] - 25.0))
            current_aging_fac = np.power(abs(current_internal), 1.3)
            cap_fade = -1.2e-7 * current_aging_fac * temp_aging_fac * aging_mult * dt
            
            self.cell_soh[i] = float(max(0.2, self.cell_soh[i] + cap_fade))
            self.cell_r_growth[i] = 1.0 + (1.0 - self.cell_soh[i]) * 1.5
            
        # Determine cell balancing decisions (compare single cell voltage vs 4.10V top balancing)
        min_v_cell = min(cell_voltages)
        for i in range(self.n_cells):
            if cell_voltages[i] > 4.10 and (cell_voltages[i] - min_v_cell) > 0.010 and current < -0.05:
                self.balancing_active[i] = True
            else:
                self.balancing_active[i] = False
                
        # Pack aggregation
        self.soc = float(np.mean(self.cell_soc))
        self.soh = float(np.min(self.cell_soh))
        self.V1 = float(np.mean(self.cell_V1))
        self.V2 = float(np.mean(self.cell_V2))
        self.temperature = float(np.max(self.cell_temperature))
        self.internal_resistance_growth = float(np.mean(self.cell_r_growth))
        
        pack_voltage = float(np.sum(cell_voltages))
        
        min_v = 1.5 * self.n_cells
        max_v = 4.5 * self.n_cells
        pack_voltage = float(np.clip(pack_voltage, min_v, max_v))
        
        # Fault dropout introduces sensor dropout noise
        V_meas = pack_voltage
        I_meas = current
        T_meas = self.temperature
        
        if fault_dropout and random.random() < 0.2:
            V_meas = 0.0
            I_meas = 0.0
            
        ocv_mean = float(np.mean(cell_ocvs))
        return {
            'time': self.time,
            'voltage': V_meas,
            'current': I_meas,
            'temperature': T_meas,
            'true_soc': self.soc,
            'true_soh': self.soh,
            'V1': self.V1,
            'V2': self.V2,
            'v1': self.V1,
            'v2': self.V2,
            'R0': self.chemistry.R0_nom * self.internal_resistance_growth,
            'r0': self.chemistry.R0_nom * self.internal_resistance_growth,
            'ocv': ocv_mean,
            'internal_resistance_growth': self.internal_resistance_growth,
            'balancing_active': any(self.balancing_active),
            'cell_voltages': cell_voltages,
            'cell_temperatures': self.cell_temperature
        }

