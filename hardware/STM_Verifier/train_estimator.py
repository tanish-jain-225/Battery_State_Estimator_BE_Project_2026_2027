import os
import sys
import pandas as pd
import numpy as np
import pickle
import argparse

base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from train import EchoStateNetwork

def generate_full_range_dataset():
    """
    Generates a high-fidelity synthetic battery dataset covering the full range
    of SOC (0% to 100%) and SOH (80% to 100%) with continuous degradation profiles.
    """
    import sys
    import os
    from pathlib import Path
    root_dir = Path(__file__).resolve().parent.parent.parent
    shared_path = str(root_dir / 'software' / 'shared')
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)
    try:
        from software.shared.battery_simulator import BatterySimulator
    except ImportError:
        from battery_simulator import BatterySimulator
        
    import pandas as pd
    
    records = []
    soh_levels = [1.0, 0.95, 0.90, 0.85, 0.80]
    dt = 1.0
    global_time = 0.0
    
    for idx, soh_target in enumerate(soh_levels):
        next_soh = soh_levels[idx + 1] if idx + 1 < len(soh_levels) else soh_target - 0.05
        # 1. Discharging Cycle (Constant + Pulsed)
        sim = BatterySimulator()
        sim.reset("li_ion")
        sim.soh = soh_target
        sim.internal_resistance_growth = 1.0 + 1.5 * (1.0 - soh_target)
        sim.temperature = 25.0
        
        t = 0.0
        total_steps = 1500
        step_count = 0
        while sim.soc > 0.01 and step_count < total_steps:
            step_count += 1
            # Smoothly decay SOH over step progress to prevent artificial step shocks
            sim.soh = max(0.80, soh_target - (soh_target - next_soh) * (step_count / float(total_steps)))
            sim.internal_resistance_growth = 1.0 + 1.5 * (1.0 - sim.soh)
            I = 2.0
            if int(t) % 100 < 20:
                I = 4.5
            elif int(t) % 200 >= 180:
                I = -1.0
                
            out = sim.step(I, dt, accelerated_aging=False)
            records.append({
                'Time': global_time,
                'Voltage': 3.0 * out['voltage'],
                'Current': I,
                'Temperature': out['temperature'],
                'SOC': out['true_soc'],
                'SOH': sim.soh
            })
            t += dt
            global_time += dt
            
        # 2. Charging Cycle (CCCV Charge)
        sim = BatterySimulator()
        sim.reset("li_ion")
        sim.soh = soh_target
        sim.internal_resistance_growth = 1.0 + 1.5 * (1.0 - soh_target)
        sim.soc = 0.01
        sim.temperature = 25.0
        
        t = 0.0
        step_count = 0
        last_cell_v = 3.5
        while sim.soc < 0.99 and step_count < total_steps:
            step_count += 1
            sim.soh = max(0.80, soh_target - (soh_target - next_soh) * (step_count / float(total_steps)))
            sim.internal_resistance_growth = 1.0 + 1.5 * (1.0 - sim.soh)
            I_charge = 2.0
            if last_cell_v > 4.15:
                I_charge = max(0.1, 2.0 * (4.2 - last_cell_v) / 0.05)
                
            out = sim.step(-I_charge, dt, accelerated_aging=False)
            last_cell_v = out['voltage'] / float(sim.n_cells)
            records.append({
                'Time': global_time,
                'Voltage': 3.0 * out['voltage'],
                'Current': -I_charge,
                'Temperature': out['temperature'],
                'SOC': out['true_soc'],
                'SOH': sim.soh
            })
            t += dt
            global_time += dt
            
    return pd.DataFrame(records)

def train_and_export_estimator(csv_path=None, header_path=None, grid_search=False):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Resolve paths
    if csv_path is None:
        csv_path = os.path.join(base_dir, "training_ev_battery_dataset_multiclass.csv")
        if not os.path.exists(csv_path):
            csv_path = os.path.join(base_dir, "original_ev_battery_dataset_multiclass.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}. Please place the CSV in the hardware directory.")

    from config import Config as HWConfig
    if header_path is None:
        header_path = HWConfig.ESTIMATOR_WEIGHTS_HEADER

    # 2. Load dataset
    df = None
    if csv_path is not None and os.path.exists(csv_path):
        print(f"Loading local dataset from {csv_path}...")
        try:
            df = pd.read_csv(csv_path)
            print(f"Local CSV loaded successfully ({len(df)} rows).")
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            
    if df is None:
        print("Generating high-fidelity full-range fallback dataset from physical battery simulator...")
        try:
            df = generate_full_range_dataset()
            print(f"Fallback dataset generated successfully: {len(df)} rows.")
        except Exception as gen_err:
            print(f"Failed to generate fallback dataset: {gen_err}")
            raise gen_err

    if df is not None:
        # Recover if CSV was pasted into a single column
        if len(df.columns) == 1 and ',' in str(df.columns[0]):
            col_name = df.columns[0]
            new_cols = [c.strip() for c in col_name.split(',')]
            split_data = df[col_name].astype(str).str.split(',', expand=True)
            if split_data.shape[1] == len(new_cols):
                split_data.columns = new_cols
                df = split_data.apply(pd.to_numeric, errors='coerce')
                
        df.columns = [str(col).strip() for col in df.columns]
        rename_dict = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower == 'voltage':
                rename_dict[col] = 'Voltage'
            elif col_lower == 'current':
                rename_dict[col] = 'Current'
            elif col_lower == 'temperature':
                rename_dict[col] = 'Temperature'
            elif col_lower == 'soc':
                rename_dict[col] = 'SOC'
            elif col_lower == 'soh':
                rename_dict[col] = 'SOH'
            elif col_lower == 'time':
                rename_dict[col] = 'Time'
        df.rename(columns=rename_dict, inplace=True)

    # 3. Feature engineering
    print("Performing feature engineering...")
    df = df.copy()
    df['Voltage_grad'] = df['Voltage'].diff().fillna(0.0)
    df['Current_ma'] = df['Current'].rolling(window=5, min_periods=1).mean()
    df['Temp_ma'] = df['Temperature'].rolling(window=5, min_periods=1).mean()

    U = df[['Voltage', 'Current', 'Voltage_grad', 'Current_ma']].values
    Y_soc = df[['SOC']].values
    Y_soh = df[['SOH']].values

    # 4. Normalization
    input_means = U.mean(axis=0)
    input_stds = U.std(axis=0)
    input_stds[input_stds == 0.0] = 1.0
    U_scaled = (U - input_means) / input_stds

    print("Input features details:")
    print(f"  Voltage: mean={input_means[0]:.4f}, std={input_stds[0]:.4f}")
    print(f"  Current: mean={input_means[1]:.4f}, std={input_stds[1]:.4f}")
    print(f"  Voltage_grad: mean={input_means[2]:.4f}, std={input_stds[2]:.4f}")
    print(f"  Current_ma: mean={input_means[3]:.4f}, std={input_stds[3]:.4f}")

    # ── ESN Estimator Hyperparameters — read from hardware/STM_Verifier/config.py ──────────
    # These values MUST mirror software/visualiser/config.py → ESN_SOC_*/ESN_SOH_*.
    # Do NOT hardcode them here — change config.py to affect both hardware and software.
    from config import Config as HWConfig
    SOC_N_RESERVOIR     = HWConfig.ESN_SOC_RESERVOIR
    SOC_SPECTRAL_RADIUS = HWConfig.ESN_SOC_SPECTRAL_RADIUS
    SOC_LEAK_RATE       = HWConfig.ESN_SOC_LEAK_RATE
    SOC_INPUT_SCALING   = HWConfig.ESN_SOC_INPUT_SCALING
    SOC_RIDGE_PARAM     = HWConfig.ESN_SOC_RIDGE_PARAM
    SOC_SPARSITY        = HWConfig.ESN_SOC_SPARSITY
    SOC_WASHOUT         = HWConfig.ESN_SOC_WASHOUT

    SOH_N_RESERVOIR     = HWConfig.ESN_SOH_RESERVOIR
    SOH_SPECTRAL_RADIUS = HWConfig.ESN_SOH_SPECTRAL_RADIUS
    SOH_LEAK_RATE       = HWConfig.ESN_SOH_LEAK_RATE
    SOH_INPUT_SCALING   = HWConfig.ESN_SOH_INPUT_SCALING
    SOH_RIDGE_PARAM     = HWConfig.ESN_SOH_RIDGE_PARAM
    SOH_SPARSITY        = HWConfig.ESN_SOH_SPARSITY
    SOH_WASHOUT         = HWConfig.ESN_SOH_WASHOUT

    # 5. Train SOC ESN
    if grid_search:
        print("Starting SOC ESN hyperparameter grid search...")
        best_soc_rmse = float('inf')
        best_soc_params = {}
        for sr in [0.75, 0.85, 0.95]:
            for lr in [0.05, 0.15, 0.25]:
                for rp in [1e-6, 1e-5]:
                    esn_temp = EchoStateNetwork(
                        n_inputs=4,
                        n_reservoir=SOC_N_RESERVOIR,
                        n_outputs=1,
                        spectral_radius=sr,
                        leak_rate=lr,
                        input_scaling=SOC_INPUT_SCALING,
                        ridge_param=rp,
                        sparsity=SOC_SPARSITY
                    )
                    esn_temp.train(U_scaled, Y_soc, washout=SOC_WASHOUT)
                    preds = esn_temp.predict(U_scaled)
                    rmse = np.sqrt(np.mean((Y_soc[SOC_WASHOUT:] - preds[SOC_WASHOUT:]) ** 2))
                    if rmse < best_soc_rmse:
                        best_soc_rmse = rmse
                        best_soc_params = {'spectral_radius': sr, 'leak_rate': lr, 'ridge_param': rp}
                        esn_soc = esn_temp
        print(f"SOC Grid search complete. Best RMSE: {best_soc_rmse:.6f} with parameters: {best_soc_params}")
    else:
        print("Training SOC Echo State Network...")
        esn_soc = EchoStateNetwork(
            n_inputs=4,
            n_reservoir=SOC_N_RESERVOIR,
            n_outputs=1,
            spectral_radius=SOC_SPECTRAL_RADIUS,
            leak_rate=SOC_LEAK_RATE,
            input_scaling=SOC_INPUT_SCALING,
            ridge_param=SOC_RIDGE_PARAM,
            sparsity=SOC_SPARSITY
        )
        esn_soc.train(U_scaled, Y_soc, washout=SOC_WASHOUT)
    pred_soc = esn_soc.predict(U_scaled)
    soc_rmse = np.sqrt(np.mean((Y_soc[SOC_WASHOUT:] - pred_soc[SOC_WASHOUT:]) ** 2))
    print(f"SOC RMSE: {soc_rmse:.6f}")

    # 6. Train SOH ESN
    if grid_search:
        print("Starting SOH ESN hyperparameter grid search...")
        best_soh_rmse = float('inf')
        best_soh_params = {}
        for sr in [0.75, 0.85, 0.95]:
            for lr in [0.01, 0.02, 0.05]:
                for rp in [1e-6, 1e-5]:
                    esn_temp = EchoStateNetwork(
                        n_inputs=4,
                        n_reservoir=SOH_N_RESERVOIR,
                        n_outputs=1,
                        spectral_radius=sr,
                        leak_rate=lr,
                        input_scaling=SOH_INPUT_SCALING,
                        ridge_param=rp,
                        sparsity=SOH_SPARSITY
                    )
                    esn_temp.train(U_scaled, Y_soh, washout=SOH_WASHOUT)
                    preds = esn_temp.predict(U_scaled)
                    rmse = np.sqrt(np.mean((Y_soh[SOH_WASHOUT:] - preds[SOH_WASHOUT:]) ** 2))
                    if rmse < best_soh_rmse:
                        best_soh_rmse = rmse
                        best_soh_params = {'spectral_radius': sr, 'leak_rate': lr, 'ridge_param': rp}
                        esn_soh = esn_temp
        print(f"SOH Grid search complete. Best RMSE: {best_soh_rmse:.6f} with parameters: {best_soh_params}")
    else:
        print("Training SOH Echo State Network...")
        esn_soh = EchoStateNetwork(
            n_inputs=4,
            n_reservoir=SOH_N_RESERVOIR,
            n_outputs=1,
            spectral_radius=SOH_SPECTRAL_RADIUS,
            leak_rate=SOH_LEAK_RATE,
            input_scaling=SOH_INPUT_SCALING,
            ridge_param=SOH_RIDGE_PARAM,
            sparsity=SOH_SPARSITY
        )
        esn_soh.train(U_scaled, Y_soh, washout=SOH_WASHOUT)
    pred_soh = esn_soh.predict(U_scaled)
    soh_rmse = np.sqrt(np.mean((Y_soh[SOH_WASHOUT:] - pred_soh[SOH_WASHOUT:]) ** 2))
    print(f"SOH RMSE: {soh_rmse:.6f}")

    # 7. Generate header file
    print(f"Writing weights to {header_path}...")

    def to_csr(matrix):
        val = []
        col = []
        row_ptr = [0]
        for r in range(matrix.shape[0]):
            for c in range(matrix.shape[1]):
                v = matrix[r, c]
                if v != 0.0:
                    val.append(v)
                    col.append(c)
            row_ptr.append(len(val))
        return np.array(val), np.array(col), np.array(row_ptr)

    def write_array_1d(f, name, arr):
        f.write(f"const float {name}[{len(arr)}] = {{\n    ")
        for i, val in enumerate(arr):
            f.write(f"{val:.9f}f")
            if i < len(arr) - 1:
                f.write(", ")
            if (i + 1) % 6 == 0:
                f.write("\n    ")
        f.write("\n};\n\n")

    def write_array_1d_int(f, name, arr):
        f.write(f"const uint16_t {name}[{len(arr)}] = {{\n    ")
        for i, val in enumerate(arr):
            f.write(f"{val}")
            if i < len(arr) - 1:
                f.write(", ")
            if (i + 1) % 12 == 0:
                f.write("\n    ")
        f.write("\n};\n\n")

    def write_array_2d(f, name, arr):
        rows, cols = arr.shape
        f.write(f"const float {name}[{rows}][{cols}] = {{\n")
        for r in range(rows):
            f.write("    {")
            for c in range(cols):
                f.write(f"{arr[r, c]:.9f}f")
                if c < cols - 1:
                    f.write(", ")
            f.write("}")
            if r < rows - 1:
                f.write(",\n")
            else:
                f.write("\n")
        f.write("};\n\n")

    with open(header_path, "w") as f:
        f.write("#ifndef ESN_ESTIMATOR_WEIGHTS_H\n")
        f.write("#define ESN_ESTIMATOR_WEIGHTS_H\n\n")
        f.write("// Auto-generated weights file for STM32 ESN estimators\n\n")
        f.write("#include <stdint.h>\n\n")
        
        f.write(f"#define ESN_ESTIMATOR_N_INPUTS 4\n")
        f.write(f"#define ESN_SOC_N_RESERVOIR {SOC_N_RESERVOIR}\n")
        f.write(f"#define ESN_SOH_N_RESERVOIR {SOH_N_RESERVOIR}\n")
        f.write(f"#define ESN_SOC_LEAK_RATE {SOC_LEAK_RATE:.6f}f\n")
        f.write(f"#define ESN_SOH_LEAK_RATE {SOH_LEAK_RATE:.6f}f\n")
        f.write(f"#define ESN_SOC_WASHOUT_STEPS {SOC_WASHOUT}\n")
        f.write(f"#define ESN_SOH_WASHOUT_STEPS {SOH_WASHOUT}\n\n")
        
        write_array_1d(f, "esn_estimator_input_means", input_means)
        write_array_1d(f, "esn_estimator_input_stds", input_stds)
        
        f.write("// SOC Weights\n")
        write_array_2d(f, "esn_soc_W_in", esn_soc.W_in)
        write_array_2d(f, "esn_soc_W_out", esn_soc.W_out)
        soc_val, soc_col, soc_row_ptr = to_csr(esn_soc.W_res)
        f.write(f"#define ESN_SOC_W_RES_NNZ {len(soc_val)}\n\n")
        write_array_1d(f, "esn_soc_W_res_val", soc_val)
        write_array_1d_int(f, "esn_soc_W_res_col", soc_col)
        write_array_1d_int(f, "esn_soc_W_res_row_ptr", soc_row_ptr)
        
        f.write("// SOH Weights\n")
        write_array_2d(f, "esn_soh_W_in", esn_soh.W_in)
        write_array_2d(f, "esn_soh_W_out", esn_soh.W_out)
        soh_val, soh_col, soh_row_ptr = to_csr(esn_soh.W_res)
        f.write(f"#define ESN_SOH_W_RES_NNZ {len(soh_val)}\n\n")
        write_array_1d(f, "esn_soh_W_res_val", soh_val)
        write_array_1d_int(f, "esn_soh_W_res_col", soh_col)
        write_array_1d_int(f, "esn_soh_W_res_row_ptr", soh_row_ptr)
        
        # Write 500-sample test data subset: Voltage, Current, Temperature, SOC, SOH
        n_test_samples = min(500, len(df))
        f.write(f"#define ESTIMATOR_TEST_N {n_test_samples}\n")
        f.write(f"#if STATIC_VERIFICATION_MODE\n")
        f.write(f"const float estimator_test_data[{n_test_samples}][5] = {{\n")
        for i in range(n_test_samples):
            v_val = df['Voltage'].iloc[i]
            i_val = df['Current'].iloc[i]
            t_val = df['Temperature'].iloc[i]
            soc_val = df['SOC'].iloc[i]
            soh_val = df['SOH'].iloc[i]
            f.write(f"    {{{v_val:.4f}f, {i_val:.4f}f, {t_val:.4f}f, {soc_val:.4f}f, {soh_val:.4f}f}}")
            if i < n_test_samples - 1:
                f.write(",\n")
            else:
                f.write("\n")
        f.write("};\n")
        f.write(f"#endif // STATIC_VERIFICATION_MODE\n\n")

        f.write("#endif // ESN_ESTIMATOR_WEIGHTS_H\n")

    print(f"Successfully generated {header_path}!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--grid-search', action='store_true', help='Enable hyperparameter grid search')
    args = parser.parse_args()
    train_and_export_estimator(grid_search=args.grid_search)
