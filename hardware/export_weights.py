import pandas as pd
import numpy as np
import os
from train import EchoStateNetwork

# Load local dataset
base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, "original_ev_battery_dataset_multiclass.csv")
if not os.path.exists(csv_path):
    raise FileNotFoundError(f"Dataset not found at {csv_path}")

print(f"Loading dataset from {csv_path}...")
df = pd.read_csv(csv_path)

# Feature engineering
print("Performing feature engineering...")
df = df.copy()
df['Voltage_grad'] = df['Voltage'].diff().fillna(0.0)
df['Current_ma'] = df['Current'].rolling(window=5, min_periods=1).mean()

U = df[['Voltage', 'Current', 'Voltage_grad', 'Current_ma']].values
Y_soc = df[['SOC']].values
Y_soh = df[['SOH']].values

# Normalization
input_means = U.mean(axis=0)
input_stds = U.std(axis=0)
input_stds[input_stds == 0.0] = 1.0
U_scaled = (U - input_means) / input_stds

print("Input features details:")
print(f"  Voltage: mean={input_means[0]:.4f}, std={input_stds[0]:.4f}")
print(f"  Current: mean={input_means[1]:.4f}, std={input_stds[1]:.4f}")
print(f"  Voltage_grad: mean={input_means[2]:.4f}, std={input_stds[2]:.4f}")
print(f"  Current_ma: mean={input_means[3]:.4f}, std={input_stds[3]:.4f}")

# Train SOC ESN
print("Training SOC Echo State Network...")
esn_soc = EchoStateNetwork(
    n_inputs=4,
    n_reservoir=300,
    n_outputs=1,
    spectral_radius=0.90,
    leak_rate=0.3,
    input_scaling=0.8,
    ridge_param=1e-4,
    sparsity=0.85
)
esn_soc.train(U_scaled, Y_soc, washout=50)
pred_soc = esn_soc.predict(U_scaled)
soc_rmse = np.sqrt(np.mean((Y_soc[50:] - pred_soc[50:]) ** 2))
print(f"SOC RMSE: {soc_rmse:.6f}")

# Train SOH ESN
print("Training SOH Echo State Network...")
esn_soh = EchoStateNetwork(
    n_inputs=4,
    n_reservoir=200,
    n_outputs=1,
    spectral_radius=0.70,
    leak_rate=0.05,
    input_scaling=0.4,
    ridge_param=1e-3,
    sparsity=0.85
)
esn_soh.train(U_scaled, Y_soh, washout=50)
pred_soh = esn_soh.predict(U_scaled)
soh_rmse = np.sqrt(np.mean((Y_soh[50:] - pred_soh[50:]) ** 2))
print(f"SOH RMSE: {soh_rmse:.6f}")

# Generate header file
header_path = os.path.join(base_dir, "esn_estimator_weights.h")
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
    
    f.write(f"#define ESN_N_INPUTS 4\n")
    f.write(f"#define ESN_SOC_N_RESERVOIR 300\n")
    f.write(f"#define ESN_SOH_N_RESERVOIR 200\n\n")
    
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
