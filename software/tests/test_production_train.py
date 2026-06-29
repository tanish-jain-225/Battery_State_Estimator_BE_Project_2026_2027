import os
import sys
import unittest
import pandas as pd
import numpy as np
import io
import urllib.request
import socket
import pickle

# Add visualiser directory to path for imports
this_dir = os.path.dirname(os.path.abspath(__file__))
software_dir = os.path.dirname(this_dir)
visualiser_dir = os.path.join(software_dir, 'visualiser')
sys.path.insert(0, visualiser_dir)
sys.path.insert(0, os.path.join(visualiser_dir, 'training'))

# Prevent sys.modules caching collision with simulator config.py files during discover run
if 'config' in sys.modules:
    del sys.modules['config']
from config import Config
from train_rc import EchoStateNetwork
from feature_engineering import extract_features_df

class TestProductionTraining(unittest.TestCase):

    def setUp(self):
        # Use the actual published Google Sheets URL from the user
        self.csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRbY6uZX7_v-cvyxws5Xx1no7FRMp5tzjLynxBGPYutG5aC7dmgD6k7n8J_8G70D42R6kQNDi8oMYM-/pub?gid=432011183&single=true&output=csv"
        # Set socket timeout to 10s to prevent hangs
        socket.setdefaulttimeout(10.0)

    def test_remote_dataset_fetch_and_parse(self):
        """Test downloading and parsing the remote CSV dataset from Google Sheets."""
        print(f"\n[STEP 1] Fetching remote dataset from: {self.csv_url}")
        
        req = urllib.request.Request(
            self.csv_url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10.0) as response:
                csv_data = response.read().decode('utf-8')
            
            # Check for HTML redirect page error
            self.assertFalse(
                "<html" in csv_data.lower() or "<!doctype" in csv_data.lower(),
                "Error: Downloaded content is an HTML page, not raw CSV."
            )
            
            print(f"Downloaded {len(csv_data)} bytes of CSV data.")
            
            # Load into pandas
            df = pd.read_csv(io.StringIO(csv_data))
            print(f"Loaded DataFrame successfully: {len(df)} rows found.")
            
            # Validate columns
            expected_cols = ['Time', 'Voltage', 'Current', 'Temperature', 'SOC', 'SOH']
            for col in expected_cols:
                self.assertIn(col, df.columns, f"Required column '{col}' is missing from the dataset.")
            
            # Validate row count
            self.assertGreater(len(df), 100, "Dataset contains too few records.")
            
        except Exception as e:
            self.fail(f"Failed to fetch or parse remote CSV dataset: {e}")

    def test_end_to_end_training_pipeline(self):
        """Test complete feature extraction, scaling, ESN training, and pickling logic."""
        print("\n[STEP 2] Fetching remote dataset for E2E training test...")
        req = urllib.request.Request(
            self.csv_url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        
        with urllib.request.urlopen(req, timeout=10.0) as response:
            csv_data = response.read().decode('utf-8')
        
        df = pd.read_csv(io.StringIO(csv_data))
        
        print("Extracting features & scaling...")
        df = df.copy()
        df['Voltage_grad'] = df['Voltage'].diff().fillna(0.0)
        df['Current_ma'] = df['Current'].rolling(window=Config.FEATURE_ROLLING_WINDOW, min_periods=1).mean()
        df['Temp_ma'] = df['Temperature'].rolling(window=Config.FEATURE_ROLLING_WINDOW, min_periods=1).mean()

        U = df[['Voltage', 'Current', 'Temperature', 'Voltage_grad', 'Current_ma', 'Temp_ma']].values
        Y_soc = df[['SOC']].values
        Y_soh = df[['SOH']].values

        # Select indices configured in visualiser
        selected_indices = Config.ESN_SELECTED_FEATURE_INDICES
        U_raw = U[:, selected_indices]
        n_features = len(selected_indices)

        # Normalize
        input_means = U_raw.mean(axis=0)
        input_stds = U_raw.std(axis=0)
        input_stds[input_stds == 0.0] = 1.0
        U_scaled = (U_raw - input_means) / input_stds

        # Instantiate smaller ESN for rapid validation (50 nodes instead of 500)
        print("Initializing ESN for SOC...")
        esn_soc = EchoStateNetwork(
            n_inputs=n_features,
            n_reservoir=50,  # Fast test size
            n_outputs=1,
            spectral_radius=0.95,
            leak_rate=0.15,
            input_scaling=0.8,
            ridge_param=1e-5,
            sparsity=0.85
        )
        print("Fitting SOC ESN readouts...")
        esn_soc.train(U_scaled, Y_soc, washout=Config.ESN_WASHOUT_STEPS)
        pred_soc = esn_soc.predict(U_scaled)
        soc_rmse = np.sqrt(np.mean((Y_soc[Config.ESN_WASHOUT_STEPS:] - pred_soc[Config.ESN_WASHOUT_STEPS:]) ** 2))
        print(f"SOC RMSE: {soc_rmse:.6f}")
        self.assertLess(soc_rmse, 0.1, "SOC training error is too high.")

        print("Initializing ESN for SOH...")
        esn_soh = EchoStateNetwork(
            n_inputs=n_features,
            n_reservoir=50,  # Fast test size
            n_outputs=1,
            spectral_radius=0.85,
            leak_rate=0.02,
            input_scaling=0.4,
            ridge_param=1e-5,
            sparsity=0.85
        )
        print("Fitting SOH ESN readouts...")
        esn_soh.train(U_scaled, Y_soh, washout=Config.ESN_WASHOUT_STEPS)
        pred_soh = esn_soh.predict(U_scaled)
        soh_rmse = np.sqrt(np.mean((Y_soh[Config.ESN_WASHOUT_STEPS:] - pred_soh[Config.ESN_WASHOUT_STEPS:]) ** 2))
        print(f"SOH RMSE: {soh_rmse:.6f}")
        self.assertLess(soh_rmse, 0.1, "SOH training error is too high.")

        # Test model pickling roundtrip
        print("Serializing trained model package...")
        package = {
            'esn_soc': esn_soc,
            'esn_soh': esn_soh,
            'input_means': input_means,
            'input_stds': input_stds,
            'soc_rmse': soc_rmse,
            'soh_rmse': soh_rmse
        }
        
        pickle_data = pickle.dumps(package)
        self.assertIsNotNone(pickle_data, "Pickle serialization returned empty payload.")
        print(f"Model package serialized successfully ({len(pickle_data)} bytes).")

        # Restore from pickle and verify structure
        restored = pickle.loads(pickle_data)
        self.assertEqual(restored['esn_soc'].n_reservoir, 50)
        self.assertEqual(restored['esn_soh'].n_reservoir, 50)
        np.testing.assert_array_equal(restored['input_means'], input_means)
        print("Pickle deserialization roundtrip verified successfully.")

if __name__ == '__main__':
    unittest.main(verbosity=2)
