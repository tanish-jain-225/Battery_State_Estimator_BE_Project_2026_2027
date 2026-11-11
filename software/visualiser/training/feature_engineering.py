import os
import sys

import numpy as np
import pandas as pd

# Allow importing Config whether run from project root or from training/ subdirectory
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base_dir not in sys.path:
    sys.path.insert(0, _base_dir)

try:
    from software.visualiser.config import Config
except ImportError:
    from config import Config

_COLUMN_ALIAS_MAP = {
    'voltage': 'Voltage',
    'current': 'Current',
    'temperature': 'Temperature',
    'soc': 'SOC',
    'soh': 'SOH',
    'time': 'Time',
}


def normalize_battery_dataframe(df, require_soc=True, default_soh=1.0):
    """Recover single-column CSVs, canonicalize column names, coerce numeric types, and normalize percentages."""
    if df is None:
        return None

    # Recover if CSV was pasted into a single comma-delimited column
    if len(df.columns) == 1 and ',' in str(df.columns[0]):
        col_name = df.columns[0]
        new_cols = [c.strip() for c in col_name.split(',')]
        split_data = df[col_name].astype(str).str.split(',', expand=True)
        if split_data.shape[1] == len(new_cols):
            split_data.columns = new_cols
            df = split_data.apply(pd.to_numeric, errors='coerce')

    df.columns = [str(col).strip() for col in df.columns]
    rename_dict = {
        col: _COLUMN_ALIAS_MAP[col.lower()]
        for col in df.columns
        if col.lower() in _COLUMN_ALIAS_MAP and col != _COLUMN_ALIAS_MAP[col.lower()]
    }
    if rename_dict:
        df = df.rename(columns=rename_dict)

    req_cols = ['Voltage', 'Current', 'Temperature'] + (['SOC'] if require_soc else [])
    for col in req_cols + (['SOH'] if 'SOH' in df.columns else []):
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = pd.to_numeric(df[col], errors='coerce')

    subset_cols = [c for c in req_cols if c in df.columns]
    if subset_cols:
        df = df.dropna(subset=subset_cols)

    if default_soh is not None and 'SOH' not in df.columns:
        df['SOH'] = default_soh

    if 'SOC' in df.columns and not df.empty and df['SOC'].max() > 1.5:
        df['SOC'] = df['SOC'] / 100.0
    if 'SOH' in df.columns and not df.empty and df['SOH'].max() > 1.5:
        df['SOH'] = df['SOH'] / 100.0

    return df.reset_index(drop=True)


def extract_features_df(df, rolling_window=None):
    """
    Offline feature engineering on a pandas DataFrame.
    :param df: DataFrame with columns Voltage, Current, Temperature, SOC, SOH
    :param rolling_window: Window size for moving averages. Defaults to Config.FEATURE_ROLLING_WINDOW.
    Returns: U_engineered (numpy array of shape (N, n_features))
    """
    if rolling_window is None:
        rolling_window = Config.FEATURE_ROLLING_WINDOW

    v_arr = df['Voltage'].to_numpy(dtype=np.float64, copy=False)
    i_ser = df['Current']
    t_ser = df['Temperature']

    # Voltage gradient: dV between consecutive rows (units: V/row = V/DATASET_TIME_STEP)
    v_grad = np.empty_like(v_arr)
    if len(v_arr) > 0:
        v_grad[0] = 0.0
        if len(v_arr) > 1:
            v_grad[1:] = v_arr[1:] - v_arr[:-1]

    # Rolling moving averages of Current and Temperature
    i_ma = i_ser.rolling(window=rolling_window, min_periods=1).mean().to_numpy(dtype=np.float64, copy=False)
    t_ma = t_ser.rolling(window=rolling_window, min_periods=1).mean().to_numpy(dtype=np.float64, copy=False)

    return np.column_stack((
        v_arr,
        i_ser.to_numpy(dtype=np.float64, copy=False),
        t_ser.to_numpy(dtype=np.float64, copy=False),
        v_grad,
        i_ma,
        t_ma,
    ))


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

    n_hist = len(history)
    if n_hist == 0 or rolling_window <= 1:
        V_prev = history[-1]['voltage'] if n_hist else V_current
        I_ma = float(I_current)
        T_ma = float(T_current)
    else:
        lookback = rolling_window - 1
        tail = history[-lookback:]
        V_prev = tail[-1]['voltage']
        i_sum = float(I_current)
        t_sum = float(T_current)
        for rec in tail:
            i_sum += rec['current']
            t_sum += rec['temperature']
        inv_cnt = 1.0 / (len(tail) + 1)
        I_ma = i_sum * inv_cnt
        T_ma = t_sum * inv_cnt

    V_grad = V_current - V_prev
    return np.array([V_current, I_current, T_current, V_grad, I_ma, T_ma], dtype=np.float64)
