import os
import sys
import unittest
import pandas as pd
import numpy as np
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

LOCAL_DATASET_PATH = os.path.join(
    visualiser_dir,
    'datasets',
    'training_ev_battery_dataset_multiclass.csv',
)


def load_training_dataframe():
    """Load the checked-in training dataset and normalize column names."""
    if not os.path.exists(LOCAL_DATASET_PATH):
        raise FileNotFoundError(f"Local training dataset is missing: {LOCAL_DATASET_PATH}")

    df = pd.read_csv(LOCAL_DATASET_PATH)
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
    return df

class TestProductionTraining(unittest.TestCase):

    def test_local_dataset_fetch_and_parse(self):
        """Test loading and parsing the checked-in training dataset."""
        print(f"\n[STEP 1] Loading local dataset from: {LOCAL_DATASET_PATH}")
        df = load_training_dataframe()
        print(f"Loaded DataFrame successfully: {len(df)} rows found.")

        expected_cols = ['Time', 'Voltage', 'Current', 'Temperature', 'SOC', 'SOH']
        for col in expected_cols:
            self.assertIn(col, df.columns, f"Required column '{col}' is missing from the dataset.")

        self.assertGreater(len(df), 100, "Dataset contains too few records.")

    def test_end_to_end_training_pipeline(self):
        """Test complete feature extraction, scaling, ESN training and pickling logic."""
        print("\n[STEP 2] Loading local dataset for E2E training test...")
        df = load_training_dataframe()
        
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
