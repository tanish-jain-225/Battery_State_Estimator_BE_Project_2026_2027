import sys
import os
import pandas as pd
import numpy as np
import pickle

# Add base directory to path to support config imports
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from config import Config

try:
    from feature_engineering import extract_features_df
except ImportError:
    from training.feature_engineering import extract_features_df

class EchoStateNetwork:
    def __init__(self, n_inputs, n_reservoir, n_outputs, spectral_radius=0.95, leak_rate=0.3, input_scaling=1.0, ridge_param=1e-4, sparsity=0.85):
        self.n_inputs = n_inputs
        self.n_reservoir = n_reservoir
        self.n_outputs = n_outputs
        self.spectral_radius = spectral_radius
        self.leak_rate = leak_rate
        self.input_scaling = input_scaling
        self.ridge_param = ridge_param
        self.sparsity = sparsity
        
        # Initialize input weights
        np.random.seed(42)  # For reproducible weights
        self.W_in = (np.random.rand(n_reservoir, 1 + n_inputs) - 0.5) * 2.0 * input_scaling
        
        # Initialize reservoir weights
        W = np.random.randn(n_reservoir, n_reservoir)
        
        # Apply sparsity (zero out random elements)
        if sparsity > 0.0:
            mask = np.random.rand(*W.shape) < sparsity
            W[mask] = 0.0
            
        # Scale reservoir weights to have desired spectral radius
        eigenvalues = np.linalg.eigvals(W)
        max_eigenval = np.max(np.abs(eigenvalues))
        if max_eigenval > 0:
            self.W_res = W * (spectral_radius / max_eigenval)
        else:
            self.W_res = W
            
        # Readout weights
        self.W_out = None
        
        # Reservoir state vector
        self.x = np.zeros((n_reservoir, 1))

    def reset_state(self, state_vector=None):
        if state_vector is not None:
            self.x = np.array(state_vector).reshape(self.n_reservoir, 1)
        else:
            self.x = np.zeros((self.n_reservoir, 1))

    def get_state(self):
        return self.x.flatten().tolist()

    def _update(self, u):
        # u is shape (n_inputs, 1)
        u_biased = np.vstack(([1.0], u))
        # Reservoir state update:
        # x(t) = (1 - alpha)*x(t-1) + alpha * tanh(W_in * u_biased + W_res * x(t-1))
        arg = np.dot(self.W_in, u_biased) + np.dot(self.W_res, self.x)
        self.x = (1.0 - self.leak_rate) * self.x + self.leak_rate * np.tanh(arg)
        return self.x

    def train(self, U, Y, washout=50):
        """
        Train the readout weights W_out using Ridge Regression.
        :param U: input sequence, shape (n_samples, n_inputs)
        :param Y: target sequence, shape (n_samples, n_outputs)
        :param washout: number of initial steps to discard so reservoir settles before learning.
                        This prevents cold-start reservoir states (all zeros) from biasing the
                        output weights. Typically 50-100 steps.
        """
        n_samples = U.shape[0]
        self.reset_state()
        
        states = []
        for t in range(n_samples):
            u_t = U[t].reshape(-1, 1)
            x_t = self._update(u_t)
            # Skip the washout phase — reservoir states are unreliable when starting from zero
            if t >= washout:
                state_vec = np.vstack(([1.0], u_t, x_t))
                states.append(state_vec.flatten())
            
        # Design matrix X: (1 + n_inputs + n_reservoir, n_samples - washout)
        X = np.array(states).T
        
        # Target matrix Y_target: (n_outputs, n_samples - washout)
        Y_target = Y[washout:].reshape(-1, self.n_outputs).T
        
        # Ridge Regression: W_out = Y_target * X^T * (X * X^T + lambda * I)^-1
        X_XT = np.dot(X, X.T)
        reg_matrix = self.ridge_param * np.eye(X.shape[0])
        self.W_out = np.dot(np.dot(Y_target, X.T), np.linalg.inv(X_XT + reg_matrix))
        
    def predict_step(self, u, quantize_mode='float32'):
        """
        Advance ESN state by one step and make prediction, optionally simulating quantization.
        :param u: input vector of shape (n_inputs,)
        :param quantize_mode: 'float32', 'int16', or 'int8'
        """
        u_t = np.array(u).reshape(-1, 1)
        
        if quantize_mode in ('int8', 'int16'):
            bits = 8 if quantize_mode == 'int8' else 16
            
            # Helper function to quantize arrays to simulate fixed-point precision
            def simulate_quantization(val, bits_limit):
                if val is None:
                    return None
                v_max = max(1e-4, np.max(np.abs(val)))
                scale = (2**(bits_limit - 1) - 1) / v_max
                val_q = np.round(val * scale)
                val_q = np.clip(val_q, -(2**(bits_limit - 1)), 2**(bits_limit - 1) - 1)
                return val_q / scale

            # Quantize input, weights, and states
            u_t_q = simulate_quantization(u_t, bits)
            W_in_q = simulate_quantization(self.W_in, bits)
            W_res_q = simulate_quantization(self.W_res, bits)
            x_q = simulate_quantization(self.x, bits)
            
            u_biased = np.vstack(([1.0], u_t_q))
            arg = np.dot(W_in_q, u_biased) + np.dot(W_res_q, x_q)
            arg_q = simulate_quantization(arg, bits)
            
            # Perform state update in quantized space
            self.x = (1.0 - self.leak_rate) * x_q + self.leak_rate * np.tanh(arg_q)
            self.x = simulate_quantization(self.x, bits)
            
            # Compute output in quantized space
            W_out_q = simulate_quantization(self.W_out, bits)
            state_vec = np.vstack(([1.0], u_t_q, self.x))
            state_vec_q = simulate_quantization(state_vec, bits)
            
            y_pred = np.dot(W_out_q, state_vec_q)
            return y_pred.flatten()
        else:
            x_t = self._update(u_t)
            state_vec = np.vstack(([1.0], u_t, x_t))
            y_pred = np.dot(self.W_out, state_vec)
            return y_pred.flatten()

    def predict(self, U):
        """
        Predict output sequence for a series of inputs U.
        :param U: shape (n_samples, n_inputs)
        """
        n_samples = U.shape[0]
        self.reset_state()
        predictions = []
        for t in range(n_samples):
            y_pred = self.predict_step(U[t])
            predictions.append(y_pred)
        return np.array(predictions)

def main():
    csv_path = Config.CSV_PATH
    csv_url = getattr(Config, 'CSV_URL', '').strip()
    model_save_path = Config.MODEL_PATH

    df = None
    if os.path.exists(csv_path):
        print(f"Loading local dataset from {csv_path}...")
        df = pd.read_csv(csv_path)
    elif csv_url:
        print(f"Local dataset not found. Fetching remote dataset from URL: {csv_url}...")
        try:
            df = pd.read_csv(csv_url)
            print(f"Remote dataset loaded ({len(df)} rows).")
        except Exception as e:
            print(f"Error loading remote CSV from CSV_URL: {e}")
            return
    else:
        print(f"Error: No training dataset source available.")
        print(f"  • Local path '{csv_path}' does not exist.")
        print(f"  • CSV_URL is not configured.")
        return

    # 1. Feature Engineering
    print("Performing feature engineering...")
    U_raw = extract_features_df(df)
    n_features = U_raw.shape[1]
    print(f"Engineered {n_features} features: Voltage, Current, Temperature, Voltage_grad, Current_ma, Temp_ma")
    
    # Target values
    Y_soc = df[['SOC']].values
    Y_soh = df[['SOH']].values

    # 2. Select robust features — indices defined in Config to stay consistent with runtime inference
    selected_indices = Config.ESN_SELECTED_FEATURE_INDICES  # e.g. [0,1,3,4] = Voltage, Current, Voltage_grad, Current_ma
    U_raw = U_raw[:, selected_indices]
    n_features = len(selected_indices)
    
    print("Normalizing input features...")
    input_means = U_raw.mean(axis=0)
    input_stds = U_raw.std(axis=0)
    input_stds[input_stds == 0.0] = 1.0
    
    all_names = ['Voltage', 'Current', 'Temperature', 'Voltage_grad', 'Current_ma', 'Temp_ma']
    feature_names = [all_names[i] for i in selected_indices]
    for idx, name in enumerate(feature_names):
        print(f"  Feature '{name}': mean={input_means[idx]:.4f}, std={input_stds[idx]:.4f}")
        
    U_scaled = (U_raw - input_means) / input_stds

    # 3. Instantiate and Train SOC ESN
    print("Initializing and training SOC Echo State Network...")
    esn_soc = EchoStateNetwork(
        n_inputs=n_features,
        n_reservoir=Config.ESN_SOC_RESERVOIR,
        n_outputs=1,
        spectral_radius=Config.ESN_SOC_SPECTRAL_RADIUS,
        leak_rate=Config.ESN_SOC_LEAK_RATE,
        input_scaling=Config.ESN_SOC_INPUT_SCALING,
        ridge_param=Config.ESN_SOC_RIDGE_PARAM,
        sparsity=Config.ESN_SOC_SPARSITY
    )
    esn_soc.train(U_scaled, Y_soc, washout=Config.ESN_WASHOUT_STEPS)
    
    # Evaluate SOC ESN
    pred_soc = esn_soc.predict(U_scaled)
    soc_rmse = np.sqrt(np.mean((Y_soc[Config.ESN_WASHOUT_STEPS:] - pred_soc[Config.ESN_WASHOUT_STEPS:]) ** 2))
    print(f"Training SOC RMSE (post-washout): {soc_rmse:.6f}")
    print(f"  Target SOC Range: min={Y_soc.min():.4f}, max={Y_soc.max():.4f}, mean={Y_soc.mean():.4f}")
    print(f"  Pred   SOC Range: min={pred_soc.min():.4f}, max={pred_soc.max():.4f}, mean={pred_soc.mean():.4f}")

    # 4. Instantiate and Train SOH ESN
    print("Initializing and training SOH Echo State Network...")
    esn_soh = EchoStateNetwork(
        n_inputs=n_features,
        n_reservoir=Config.ESN_SOH_RESERVOIR,
        n_outputs=1,
        spectral_radius=Config.ESN_SOH_SPECTRAL_RADIUS,
        leak_rate=Config.ESN_SOH_LEAK_RATE,
        input_scaling=Config.ESN_SOH_INPUT_SCALING,
        ridge_param=Config.ESN_SOH_RIDGE_PARAM,
        sparsity=Config.ESN_SOH_SPARSITY
    )
    esn_soh.train(U_scaled, Y_soh, washout=Config.ESN_WASHOUT_STEPS)
    
    # Evaluate SOH ESN
    pred_soh = esn_soh.predict(U_scaled)
    soh_rmse = np.sqrt(np.mean((Y_soh[Config.ESN_WASHOUT_STEPS:] - pred_soh[Config.ESN_WASHOUT_STEPS:]) ** 2))
    print(f"Training SOH RMSE (post-washout): {soh_rmse:.6f}")
    print(f"  Target SOH Range: min={Y_soh.min():.4f}, max={Y_soh.max():.4f}, mean={Y_soh.mean():.4f}")
    print(f"  Pred   SOH Range: min={pred_soh.min():.4f}, max={pred_soh.max():.4f}, mean={pred_soh.mean():.4f}")

    # 5. Save model package locally
    model_package = {
        'esn_soc': esn_soc,
        'esn_soh': esn_soh,
        'input_means': input_means,
        'input_stds': input_stds,
        'soc_rmse': float(soc_rmse),
        'soh_rmse': float(soh_rmse)
    }
    
    print(f"Saving trained ESN models locally to {model_save_path}...")
    try:
        with open(model_save_path, 'wb') as f:
            pickle.dump(model_package, f)
        print("Model package saved locally successfully!")
    except Exception as local_err:
        print(f"Failed to save local file (read-only filesystem or path error): {local_err}")

    # 6. Upload package to MongoDB model registry (if connection is configured)
    try:
        from pymongo import MongoClient
        from datetime import datetime
        print("Checking MongoDB Model Registry connection...")
        client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=2000)
        client.server_info()  # trigger connection check
        db = client[Config.MONGODB_DB_NAME]
        
        print("Uploading package to MongoDB registry cluster...")
        db['model_weights'].replace_one(
            {'_id': 'esn_package'},
            {
                '_id': 'esn_package',
                'pickle_data': pickle.dumps(model_package),
                'soc_rmse': float(soc_rmse),
                'soh_rmse': float(soh_rmse),
                'updated_at': datetime.utcnow().isoformat()
            },
            upsert=True
        )
        print("Model saved to MongoDB Model Registry successfully!")
    except Exception as mongo_err:
        print(f"MongoDB Model Registry upload skipped or failed: {mongo_err}")

if __name__ == "__main__":
    main()
