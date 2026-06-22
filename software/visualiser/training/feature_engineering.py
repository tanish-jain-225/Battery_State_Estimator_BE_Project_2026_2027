import sys
import os
import numpy as np
import pandas as pd

# Allow importing Config whether run from project root or from training/ subdirectory
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base_dir not in sys.path:
    sys.path.insert(0, _base_dir)

from config import Config

def extract_features_df(df, rolling_window=None):
    """
    Offline feature engineering on a pandas DataFrame.
    :param df: DataFrame with columns Voltage, Current, Temperature, SOC, SOH
    :param rolling_window: Window size for moving averages. Defaults to Config.FEATURE_ROLLING_WINDOW.
    Returns: U_engineered (numpy array of shape (N, n_features))
    """
    if rolling_window is None:
        rolling_window = Config.FEATURE_ROLLING_WINDOW

    # Make a copy to avoid modifications
    df = df.copy()

    # Voltage gradient: dV between consecutive rows (units: V/row = V/DATASET_TIME_STEP)
    df['Voltage_grad'] = df['Voltage'].diff().fillna(0.0)

    # Rolling moving averages of Current and Temperature
    df['Current_ma'] = df['Current'].rolling(window=rolling_window, min_periods=1).mean()
    df['Temp_ma'] = df['Temperature'].rolling(window=rolling_window, min_periods=1).mean()

    feature_cols = ['Voltage', 'Current', 'Temperature', 'Voltage_grad', 'Current_ma', 'Temp_ma']
    return df[feature_cols].values

def extract_features_step(V_current, I_current, T_current, history, rolling_window=None):
    """
    Online feature engineering step-by-step at runtime.
    :param V_current: Current voltage reading
    :param I_current: Current current reading
    :param T_current: Current temperature reading
    :param history: List of dicts of past readings, e.g. [{'voltage': v, 'current': i, 'temperature': t}, ...]
    :param rolling_window: Window size for moving averages. Defaults to Config.FEATURE_ROLLING_WINDOW.
    :returns: numpy array of shape (6,) = [Voltage, Current, Temperature, Voltage_grad, Current_ma, Temp_ma]
    """
    if rolling_window is None:
        rolling_window = Config.FEATURE_ROLLING_WINDOW

    # Number of past samples to pull from history for rolling window (window - 1 past + 1 current)
    lookback = rolling_window - 1

    if len(history) == 0:
        V_prev = V_current
        V_history = [V_current]
        I_history = [I_current]
        T_history = [T_current]
    else:
        V_prev = history[-1]['voltage']
        V_history = [r['voltage'] for r in history[-lookback:]] + [V_current]
        I_history = [r['current'] for r in history[-lookback:]] + [I_current]
        T_history = [r['temperature'] for r in history[-lookback:]] + [T_current]

    V_grad = V_current - V_prev
    I_ma = np.mean(I_history)
    T_ma = np.mean(T_history)

    return np.array([V_current, I_current, T_current, V_grad, I_ma, T_ma])
