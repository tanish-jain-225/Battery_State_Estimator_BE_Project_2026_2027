import pandas as pd
import numpy as np
import os
import argparse
from train import EchoStateNetwork
from config import Config

# Load the multiclass dataset from configuration path
csv_path = Config.CSV_PATH
if not os.path.exists(csv_path):
    raise FileNotFoundError(f"Dataset not found at {csv_path}")

def clean_df_columns(df_in):
    if df_in is not None:
        if len(df_in.columns) == 1 and ',' in str(df_in.columns[0]):
            col_name = df_in.columns[0]
            new_cols = [c.strip() for c in col_name.split(',')]
            split_data = df_in[col_name].astype(str).str.split(',', expand=True)
            if split_data.shape[1] == len(new_cols):
                split_data.columns = new_cols
                df_in = split_data.apply(pd.to_numeric, errors='coerce')
                
        df_in.columns = [str(col).strip() for col in df_in.columns]
        rename_dict = {}
        for col in df_in.columns:
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
        df_in.rename(columns=rename_dict, inplace=True)
    return df_in

print(f"Loading dataset from {csv_path}...")
df = pd.read_csv(csv_path)
df = clean_df_columns(df)

def get_labels(df_in):
    T_in = df_in['Temperature'].values
    labels_in = np.zeros(len(T_in), dtype=int)
    for idx in range(len(T_in)):
        if T_in[idx] < Config.TEMP_NORMAL_MAX:
            labels_in[idx] = 0  # Normal
        elif T_in[idx] < Config.TEMP_WARNING_MAX:
            labels_in[idx] = 1  # Warning
        else:
            labels_in[idx] = 2  # Critical
    return labels_in

labels = get_labels(df)
if len(np.unique(labels)) < 3:
    print(f"WARNING: The dataset {csv_path} has only {len(np.unique(labels))} classes represented. The ESN classifier requires all 3 classes (Normal, Warning, Critical) to train correctly.")
    fallback_path = os.path.join(os.path.dirname(csv_path), "original_ev_battery_dataset_multiclass.csv")
    if os.path.exists(fallback_path):
        print(f"Attempting to use fallback multiclass dataset containing all three classes: {fallback_path}...")
        df = pd.read_csv(fallback_path)
        df = clean_df_columns(df)
        labels = get_labels(df)
    else:
        print(f"ERROR: Fallback file {fallback_path} not found.")

# Extract features: Voltage, Current, Temperature
U = df[['Voltage', 'Current', 'Temperature']].values

# One-hot encode the target states (3 classes)
n_classes = Config.ESN_N_OUTPUTS
Y = np.zeros((len(labels), n_classes))
for i in range(len(labels)):
    Y[i, labels[i]] = 1.0

print("Class distribution in dataset:")
for c in range(n_classes):
    print(f"  Class {c}: {np.sum(labels == c)} samples")

# Normalize inputs
input_means = U.mean(axis=0)
input_stds = U.std(axis=0)
input_stds[input_stds == 0.0] = 1.0
U_scaled = (U - input_means) / input_stds

print("Input features details:")
print(f"  Voltage: mean={input_means[0]:.4f}, std={input_stds[0]:.4f}")
print(f"  Current: mean={input_means[1]:.4f}, std={input_stds[1]:.4f}")
print(f"  Temperature: mean={input_means[2]:.4f}, std={input_stds[2]:.4f}")

# Parse CLI arguments
parser = argparse.ArgumentParser()
parser.add_argument('--grid-search', action='store_true', help='Enable hyperparameter grid search')
args = parser.parse_args()

n_inputs = Config.ESN_N_INPUTS
n_reservoir = Config.ESN_N_RESERVOIR
n_outputs = Config.ESN_N_OUTPUTS
washout = Config.ESN_WASHOUT

best_acc = 0.0
best_params = {}
best_esn = None

if args.grid_search:
    print("Starting ESN Classifier hyperparameter grid search...")
    # Swapping parameters
    for sr in [0.6, 0.8, 1.0, 1.2]:
        for lr in [0.2, 0.3, 0.4]:
            for sp in [0.8, 0.85, 0.9]:
                for rp in [1e-4, 1e-3, 1e-2]:
                    esn_temp = EchoStateNetwork(
                        n_inputs=n_inputs,
                        n_reservoir=n_reservoir,
                        n_outputs=n_outputs,
                        spectral_radius=sr,
                        leak_rate=lr,
                        input_scaling=Config.ESN_INPUT_SCALING,
                        ridge_param=rp,
                        sparsity=sp
                    )
                    esn_temp.train(U_scaled, Y, washout=washout)
                    preds = esn_temp.predict(U_scaled)
                    pred_lbls = np.argmax(preds, axis=1)
                    curr_acc = np.mean(pred_lbls[washout:] == labels[washout:])
                    if curr_acc > best_acc:
                        best_acc = curr_acc
                        best_params = {'spectral_radius': sr, 'leak_rate': lr, 'sparsity': sp, 'ridge_param': rp}
                        best_esn = esn_temp
    print(f"Grid search complete. Best Accuracy: {best_acc*100.0:.2f}% with parameters: {best_params}")
    esn = best_esn
else:
    print(f"Training ESN Classifier (n_reservoir={n_reservoir}, washout={washout})...")
    esn = EchoStateNetwork(
        n_inputs=n_inputs,
        n_reservoir=n_reservoir,
        n_outputs=n_outputs,
        spectral_radius=Config.ESN_SPECTRAL_RADIUS,
        leak_rate=Config.ESN_LEAK_RATE,
        input_scaling=Config.ESN_INPUT_SCALING,
        ridge_param=Config.ESN_RIDGE_PARAM,
        sparsity=Config.ESN_SPARSITY
    )
    esn.train(U_scaled, Y, washout=washout)

# Predict and verify accuracy
predictions = esn.predict(U_scaled)
pred_labels = np.argmax(predictions, axis=1)

# Accuracy post-washout
acc = np.mean(pred_labels[washout:] == labels[washout:])
print(f"Training Accuracy (post-washout): {acc*100.0:.2f}%")

# Generate the C header file containing weights
header_path = Config.WEIGHTS_HEADER
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
    f.write("#ifndef ESN_CLASSIFIER_WEIGHTS_H\n")
    f.write("#define ESN_CLASSIFIER_WEIGHTS_H\n\n")
    f.write("// Auto-generated weights file for STM32 ESN classifier\n\n")
    f.write("#include <stdint.h>\n\n")
    
    f.write(f"#define ESN_N_INPUTS {n_inputs}\n")
    f.write(f"#define ESN_N_RESERVOIR {n_reservoir}\n")
    f.write(f"#define ESN_N_OUTPUTS {n_outputs}\n")
    f.write(f"#define ESN_LEAK_RATE {Config.ESN_LEAK_RATE:.6f}f\n")
    f.write(f"#define ESN_SPECTRAL_RADIUS {Config.ESN_SPECTRAL_RADIUS:.6f}f\n")
    f.write(f"#define ESN_WASHOUT_STEPS {washout}\n\n")
    
    write_array_1d(f, "esn_input_means", input_means)
    write_array_1d(f, "esn_input_stds", input_stds)
    
    f.write("// ESN Input & Readout Weights (Dense)\n")
    write_array_2d(f, "esn_W_in", esn.W_in)
    write_array_2d(f, "esn_W_out", esn.W_out)
    
    f.write("// ESN Reservoir Weights (Compressed Sparse Row CSR Optimization)\n")
    val, col, row_ptr = to_csr(esn.W_res)
    f.write(f"#define ESN_W_RES_NNZ {len(val)}\n\n")
    write_array_1d(f, "esn_W_res_val", val)
    write_array_1d_int(f, "esn_W_res_col", col)
    write_array_1d_int(f, "esn_W_res_row_ptr", row_ptr)
    
    f.write("#endif // ESN_CLASSIFIER_WEIGHTS_H\n")

print(f"Successfully generated {header_path}!")
