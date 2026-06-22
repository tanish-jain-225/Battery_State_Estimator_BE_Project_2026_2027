import pandas as pd
import numpy as np
import os
from train import EchoStateNetwork

# Load the original multiclass dataset
base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, "original_ev_battery_dataset_multiclass.csv")
if not os.path.exists(csv_path):
    raise FileNotFoundError(f"Dataset not found at {csv_path}")

print(f"Loading dataset from {csv_path}...")
df = pd.read_csv(csv_path)

# Extract features: Voltage, Current, Temperature
U = df[['Voltage', 'Current', 'Temperature']].values

# Programmatically generate State label based on data_set.m thresholds
T = df['Temperature'].values
labels = np.zeros(len(T), dtype=int)
for i in range(len(T)):
    if T[i] < 35:
        labels[i] = 0  # Normal
    elif T[i] < 45:
        labels[i] = 1  # Warning
    else:
        labels[i] = 2  # Critical

# One-hot encode the target states (3 classes)
n_classes = 3
Y = np.zeros((len(labels), n_classes))
for i in range(len(labels)):
    Y[i, labels[i]] = 1.0

# Normalize inputs
input_means = U.mean(axis=0)
input_stds = U.std(axis=0)
input_stds[input_stds == 0.0] = 1.0
U_scaled = (U - input_means) / input_stds

print("Input features details:")
print(f"  Voltage: mean={input_means[0]:.4f}, std={input_stds[0]:.4f}")
print(f"  Current: mean={input_means[1]:.4f}, std={input_stds[1]:.4f}")
print(f"  Temperature: mean={input_means[2]:.4f}, std={input_stds[2]:.4f}")

# Train the ESN Classifier
n_inputs = 3
n_reservoir = 50
n_outputs = 3
washout = 50

print(f"Training ESN Classifier (n_reservoir={n_reservoir}, washout={washout})...")
esn = EchoStateNetwork(
    n_inputs=n_inputs,
    n_reservoir=n_reservoir,
    n_outputs=n_outputs,
    spectral_radius=0.95,
    leak_rate=0.3,
    input_scaling=1.0,
    ridge_param=1e-4,
    sparsity=0.85
)

esn.train(U_scaled, Y, washout=washout)

# Predict and verify accuracy
predictions = esn.predict(U_scaled)
pred_labels = np.argmax(predictions, axis=1)

# Accuracy post-washout
acc = np.mean(pred_labels[washout:] == labels[washout:])
print(f"Training Accuracy (post-washout): {acc*100.0:.2f}%")

# Generate the esn_classifier_weights.h header file
header_path = os.path.join(base_dir, "esn_classifier_weights.h")
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
    f.write(f"#define ESN_LEAK_RATE 0.3f\n\n")
    
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

