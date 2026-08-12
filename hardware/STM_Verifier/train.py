import os
import sys
import numpy as np

# Try importing the canonical EchoStateNetwork class from software module for single-source-of-truth logic
try:
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    train_rc_dir = os.path.join(root_dir, "software", "visualiser", "training")
    if train_rc_dir not in sys.path:
        sys.path.insert(0, train_rc_dir)
    from train_rc import EchoStateNetwork as CanonicalEchoStateNetwork
    _CANONICAL_ESN_AVAILABLE = True
except Exception:
    _CANONICAL_ESN_AVAILABLE = False

if _CANONICAL_ESN_AVAILABLE:
    class EchoStateNetwork(CanonicalEchoStateNetwork):
        """
        Hardware verifier ESN class wrapping canonical software implementation for 100% logic alignment.
        """
        def _clip_output(self, y_pred):
            return np.clip(y_pred, 0.0, 1.0)
else:
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
            u_biased = np.vstack(([1.0], np.array(u).reshape(-1, 1)))
            arg = np.dot(self.W_in, u_biased) + np.dot(self.W_res, self.x)
            self.x = (1.0 - self.leak_rate) * self.x + self.leak_rate * np.tanh(arg)
            return self.x

        def train(self, U, Y, washout=50, timeout_check=None):
            n_samples = U.shape[0]
            self.reset_state()
            
            U_biased = np.hstack((np.ones((n_samples, 1)), U))
            W_in_U = np.dot(U_biased, self.W_in.T)
            
            x_vec = self.x.ravel().copy()
            W_res = self.W_res
            leak = self.leak_rate
            one_minus_leak = 1.0 - leak
            
            n_effective = max(0, n_samples - washout)
            state_dim = 1 + self.n_inputs + self.n_reservoir
            X = np.empty((n_effective, state_dim))
            
            for t in range(n_samples):
                if t % 2000 == 0 and timeout_check is not None:
                    timeout_check()
                x_vec = one_minus_leak * x_vec + leak * np.tanh(W_in_U[t] + W_res.dot(x_vec))
                if t >= washout:
                    idx = t - washout
                    X[idx, 0] = 1.0
                    X[idx, 1:1+self.n_inputs] = U[t]
                    X[idx, 1+self.n_inputs:] = x_vec
                    
            self.x = x_vec.reshape(-1, 1)
            if timeout_check is not None:
                timeout_check()

            X_T = X.T
            Y_target = Y[washout:].reshape(-1, self.n_outputs).T
            X_XT = np.dot(X_T, X)
            reg_matrix = self.ridge_param * np.eye(state_dim)
            self.W_out = np.dot(np.dot(Y_target, X), np.linalg.inv(X_XT + reg_matrix))
            
            return np.clip(np.dot(X, self.W_out.T), 0.0, 1.0)
        
    def adapt_online(self, u, y_target, learning_rate=0.01, mode='rls'):
        """
        Adapt the readout weights W_out online based on target feedback.
        :param u: normalized input features vector u_scaled
        :param y_target: target ground truth value (scalar)
        :param learning_rate: adaptation rate (for NLMS mode)
        :param mode: 'rls' (Recursive Least Squares) or 'nlms' (Normalized LMS)
        """
        if self.W_out is None:
            return
        
        u_t = np.array(u).reshape(-1, 1)
        state_vec = np.vstack(([1.0], u_t, self.x)) # shape (1 + n_inputs + n_reservoir, 1)
        
        y_pred = np.dot(self.W_out, state_vec).item()
        error = y_target - y_pred
        
        if mode == 'nlms':
            # Normalized LMS update:
            vec_norm_sq = np.sum(state_vec ** 2)
            denom = vec_norm_sq + 1e-4
            update = learning_rate * (error / denom) * state_vec.T
            self.W_out += update
        elif mode == 'rls':
            # Recursive Least Squares online update:
            if not hasattr(self, 'P_adapt') or self.P_adapt is None:
                self.P_adapt = np.eye(state_vec.shape[0]) * 10.0
            
            lmbda = 0.9995  # Forgetting factor
            
            P_s = np.dot(self.P_adapt, state_vec)
            denom = lmbda + np.dot(state_vec.T, P_s).item()
            K = P_s / max(denom, 1e-6)
            
            self.W_out += error * K.T
            self.P_adapt = (self.P_adapt - np.dot(K, np.dot(state_vec.T, self.P_adapt))) / lmbda
            
            if np.any(np.isnan(self.P_adapt)) or np.any(np.isinf(self.P_adapt)):
                self.P_adapt = np.eye(state_vec.shape[0]) * 10.0

    def _clip_output(self, y_pred):
        return np.clip(y_pred, 0.0, 1.0)

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

            # Quantize input, weights and states
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
            return self._clip_output(y_pred).flatten()
        else:
            x_t = self._update(u_t)
            state_vec = np.vstack(([1.0], u_t, x_t))
            y_pred = np.dot(self.W_out, state_vec)
            return self._clip_output(y_pred).flatten()

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


if __name__ == '__main__':
    import subprocess, sys, os

    print("=" * 52)
    print("  Battery State Estimator — Hardware ESN Trainer")
    print("=" * 52)
    here = os.path.dirname(os.path.abspath(__file__))

    scripts = [
        ("ESN Estimator  (SOC + SOH → esn_estimator_weights.h)", "train_estimator.py"),
        ("ESN Classifier (fault detection → esn_classifier_weights.h)", "train_classifier.py"),
    ]

    for label, script in scripts:
        print(f"\n[STEP] Training {label}...")
        result = subprocess.run(
            [sys.executable, os.path.join(here, script)],
            capture_output=False
        )
        if result.returncode != 0:
            print(f"[ERROR] {script} exited with code {result.returncode}.")
            sys.exit(result.returncode)

    print("\n" + "=" * 52)
    print("  All hardware ESN weights generated successfully!")
    print("  → esn_estimator_weights.h")
    print("  → esn_classifier_weights.h")
    print("  Run: .\\run_c_simulator.bat  to test in C")
    print("=" * 52)
