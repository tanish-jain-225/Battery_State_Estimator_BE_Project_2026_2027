import os
import pandas as pd
import numpy as np
import pickle
from train import EchoStateNetwork

def train_and_export_estimator(csv_path=None, header_path=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Resolve paths
    if csv_path is None:
        csv_path = os.path.join(base_dir, "training_ev_battery_dataset_multiclass.csv")
        if not os.path.exists(csv_path):
            csv_path = os.path.join(base_dir, "original_ev_battery_dataset_multiclass.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}. Please place the CSV in the hardware directory.")

    if header_path is None:
        header_path = os.path.join(base_dir, "esn_estimator_weights.h")

    # 2. Load dataset
    print(f"Loading dataset from {csv_path}...")
    df = pd.read_csv(csv_path)

    # 3. Feature engineering
    print("Performing feature engineering...")
    df = df.copy()
    df['Voltage_grad'] = df['Voltage'].diff().fillna(0.0)
    df['Current_ma'] = df['Current'].rolling(window=5, min_periods=1).mean()
    df['Temp_ma'] = df['Temperature'].rolling(window=5, min_periods=1).mean()

    U = df[['Voltage', 'Current', 'Temperature', 'Voltage_grad', 'Current_ma', 'Temp_ma']].values
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
    print(f"  Temperature: mean={input_means[2]:.4f}, std={input_stds[2]:.4f}")
    print(f"  Voltage_grad: mean={input_means[3]:.4f}, std={input_stds[3]:.4f}")
    print(f"  Current_ma: mean={input_means[4]:.4f}, std={input_stds[4]:.4f}")
    print(f"  Temp_ma: mean={input_means[5]:.4f}, std={input_stds[5]:.4f}")

    # ── ESN Estimator Hyperparameters (Aligned with Software Config) ────────────
    SOC_N_RESERVOIR = 500
    SOC_SPECTRAL_RADIUS = 0.95
    SOC_LEAK_RATE = 0.15
    SOC_INPUT_SCALING = 0.8
    SOC_RIDGE_PARAM = 1e-5
    SOC_SPARSITY = 0.85
    SOC_WASHOUT = 50

    SOH_N_RESERVOIR = 400
    SOH_SPECTRAL_RADIUS = 0.85
    SOH_LEAK_RATE = 0.02
    SOH_INPUT_SCALING = 0.4
    SOH_RIDGE_PARAM = 1e-5
    SOH_SPARSITY = 0.85
    SOH_WASHOUT = 50

    # 5. Train SOC ESN
    print("Training SOC Echo State Network...")
    esn_soc = EchoStateNetwork(
        n_inputs=6,
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
    print("Training SOH Echo State Network...")
    esn_soh = EchoStateNetwork(
        n_inputs=6,
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

    def write_array_1d(f, name, arr):
        f.write(f"const float {name}[{len(arr)}] = {{\n    ")
        for i, val in enumerate(arr):
            f.write(f"{val:.9f}f")
            if i < len(arr) - 1:
                f.write(", ")
            if (i + 1) % 6 == 0:
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
        
        f.write(f"#define ESN_N_INPUTS 6\n")
        f.write(f"#define ESN_SOC_N_RESERVOIR {SOC_N_RESERVOIR}\n")
        f.write(f"#define ESN_SOH_N_RESERVOIR {SOH_N_RESERVOIR}\n\n")
        
        write_array_1d(f, "esn_input_means", input_means)
        write_array_1d(f, "esn_input_stds", input_stds)
        
        f.write("// SOC Weights\n")
        write_array_2d(f, "esn_soc_W_in", esn_soc.W_in)
        write_array_2d(f, "esn_soc_W_res", esn_soc.W_res)
        write_array_2d(f, "esn_soc_W_out", esn_soc.W_out)
        
        f.write("// SOH Weights\n")
        write_array_2d(f, "esn_soh_W_in", esn_soh.W_in)
        write_array_2d(f, "esn_soh_W_res", esn_soh.W_res)
        write_array_2d(f, "esn_soh_W_out", esn_soh.W_out)
        
        f.write("#endif // ESN_ESTIMATOR_WEIGHTS_H\n")

    print(f"Successfully generated {header_path}!")

if __name__ == "__main__":
    train_and_export_estimator()
