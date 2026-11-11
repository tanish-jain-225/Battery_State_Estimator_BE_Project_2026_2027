import math
import random

import numpy as np

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
        n_cells = self.n_cells

        # Sync external state overrides
        if n_cells == 1:
            if abs(self.soc - self.cell_soc[0]) > 1e-4:
                self.cell_soc[0] = self.soc
            if abs(self.soh - self.cell_soh[0]) > 1e-4:
                self.cell_soh[0] = self.soh
            if abs(self.temperature - self.cell_temperature[0]) > 1e-4:
                self.cell_temperature[0] = self.temperature
        else:
            if abs(self.soc - (sum(self.cell_soc) / n_cells)) > 1e-4:
                self.cell_soc = [self.soc] * n_cells
            if abs(self.soh - min(self.cell_soh)) > 1e-4:
                self.cell_soh = [self.soh] * n_cells
            if abs(self.temperature - max(self.cell_temperature)) > 1e-4:
                self.cell_temperature = [self.temperature] * n_cells

        cell_voltages = []
        cell_ocvs = []
        temp_ref_inv = 1.0 / (25.0 + 273.15)
        cell_therm_cap = self.thermal_capacitance / n_cells
        inv_3600 = 1.0 / 3600.0
        lookup_ocv = self.chemistry.lookup_ocv

        # Update each cell in series using pure scalar math to avoid NumPy array churn
        for i in range(n_cells):
            I_bleed = 0.05 if self.balancing_active[i] else 0.0
            I_leak = 2.0 if (fault_short and i == n_cells - 1) else 0.0
            current_internal = current - I_bleed - I_leak

            temp_kelvin = self.cell_temperature[i] + 273.15
            temp_effect = math.exp(1500.0 * (1.0 / temp_kelvin - temp_ref_inv))

            R0 = self.cell_r0s[i] * self.cell_r_growth[i] * temp_effect
            R1 = self.cell_r1s[i] * temp_effect
            C1 = self.cell_c1s[i] / temp_effect
            R2 = self.cell_r2s[i] * temp_effect
            C2 = self.cell_c2s[i] / temp_effect

            active_cap = self.cell_caps[i] * self.cell_soh[i]

            # SOC update (Current > 0 means discharge, Current < 0 means charge in physics conventions)
            dSOC = (current_internal * dt) * inv_3600 / active_cap
            new_soc = self.cell_soc[i] - dSOC
            if new_soc < 0.0:
                new_soc = 0.0
            elif new_soc > 1.0:
                new_soc = 1.0
            self.cell_soc[i] = new_soc

            # Polarization voltages
            v1_i = self.cell_V1[i] + ((current_internal - self.cell_V1[i] / R1) / C1) * dt
            v2_i = self.cell_V2[i] + ((current_internal - self.cell_V2[i] / R2) / C2) * dt
            self.cell_V1[i] = v1_i
            self.cell_V2[i] = v2_i

            # OCV lookup per cell
            cell_ocv = lookup_ocv(new_soc)
            cell_ocvs.append(cell_ocv)

            cell_v = cell_ocv - (current_internal * R0) - v1_i - v2_i
            cell_voltages.append(cell_v)

            # Heat generation
            heat_gen = (current_internal * current_internal * R0) + abs(current_internal * v1_i) + abs(current_internal * v2_i)
            if fault_short and i == n_cells - 1:
                heat_gen += 15.0  # 15W internal short heating

            cooling = self.cooling_coefficient * (self.cell_temperature[i] - self.T_ambient) / n_cells
            dT = ((heat_gen - cooling) / cell_therm_cap) * dt

            if fault_thermal and i == n_cells - 1:
                dT += 0.5 * math.exp(0.08 * (self.cell_temperature[i] - 25.0)) * dt

            new_temp = self.cell_temperature[i] + dT
            if new_temp < self.T_ambient:
                new_temp = self.T_ambient
            elif new_temp > 1000.0:
                new_temp = 1000.0
            self.cell_temperature[i] = float(new_temp)

            # SOH degradation
            aging_mult = 1500.0 if accelerated_aging else 1.0
            temp_aging_fac = math.exp(0.06 * (new_temp - 25.0))
            current_aging_fac = abs(current_internal) ** 1.3
            cap_fade = -1.2e-7 * current_aging_fac * temp_aging_fac * aging_mult * dt

            new_soh = self.cell_soh[i] + cap_fade
            if new_soh < 0.2:
                new_soh = 0.2
            self.cell_soh[i] = float(new_soh)
            self.cell_r_growth[i] = 1.0 + (1.0 - new_soh) * 1.5

        # Determine cell balancing decisions (compare single cell voltage vs 4.10V top balancing)
        min_v_cell = min(cell_voltages)
        for i in range(n_cells):
            self.balancing_active[i] = (
                cell_voltages[i] > 4.10 and (cell_voltages[i] - min_v_cell) > 0.010 and current < -0.05
            )

        # Pack aggregation
        if n_cells == 1:
            self.soc = float(self.cell_soc[0])
            self.soh = float(self.cell_soh[0])
            self.V1 = float(self.cell_V1[0])
            self.V2 = float(self.cell_V2[0])
            self.temperature = float(self.cell_temperature[0])
            self.internal_resistance_growth = float(self.cell_r_growth[0])
            pack_voltage = cell_voltages[0]
            ocv_mean = float(cell_ocvs[0])
        else:
            inv_n = 1.0 / n_cells
            self.soc = float(sum(self.cell_soc) * inv_n)
            self.soh = float(min(self.cell_soh))
            self.V1 = float(sum(self.cell_V1) * inv_n)
            self.V2 = float(sum(self.cell_V2) * inv_n)
            self.temperature = float(max(self.cell_temperature))
            self.internal_resistance_growth = float(sum(self.cell_r_growth) * inv_n)
            pack_voltage = sum(cell_voltages)
            ocv_mean = float(sum(cell_ocvs) * inv_n)

        min_v = 1.5 * n_cells
        max_v = 4.5 * n_cells
        if pack_voltage < min_v:
            pack_voltage = min_v
        elif pack_voltage > max_v:
            pack_voltage = max_v
        pack_voltage = float(pack_voltage)

        # Fault dropout introduces sensor dropout noise
        V_meas = pack_voltage
        I_meas = current
        T_meas = self.temperature

        if fault_dropout and random.random() < 0.2:
            V_meas = 0.0
            I_meas = 0.0

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

