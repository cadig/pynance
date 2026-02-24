"""Signal modules for regime detection.

Each function takes a combined DataFrame and its config section,
returning a boolean or numeric pd.Series aligned to the DataFrame index.
"""

import numpy as np
import pandas as pd
import logging


def _apply_confirmation_period(initial_signal: pd.Series, confirmation_days: int) -> pd.Series:
    """Apply confirmation period to a boolean signal series."""
    confirmed_signal = pd.Series(True, index=initial_signal.index)
    current_state = True
    days_in_state = 0

    for i in range(len(initial_signal)):
        if current_state:  # Currently risk-on
            if not initial_signal.iloc[i]:  # Below threshold
                days_in_state += 1
                if days_in_state >= confirmation_days:
                    current_state = False
                    days_in_state = 0
            else:
                days_in_state = 0
        else:  # Currently risk-off
            if initial_signal.iloc[i]:  # Above threshold
                current_state = True
                days_in_state = 0
            else:
                days_in_state = 0

        confirmed_signal.iloc[i] = current_state

    return confirmed_signal


def apply_nyse_cumulative_ad_zscore(combined_data: pd.DataFrame, config: dict) -> pd.Series:
    """NYSE cumulative AD z-score regime signal. True = risk-on, False = risk-off."""
    lookback = config['lookback_period']
    smoothing_period = config['smoothing_period']
    threshold = config['threshold']
    confirmation_days = config['confirmation_days']

    adrn_data = combined_data['ADRN_close']
    normalized_data = np.tanh(np.log(adrn_data))

    cumulative_ad = normalized_data.cumsum()
    smoothed_ad = cumulative_ad.rolling(window=smoothing_period).mean()

    rolling_mean = smoothed_ad.rolling(window=lookback).mean()
    rolling_std = smoothed_ad.rolling(window=lookback).std()
    zscore = (smoothed_ad - rolling_mean) / rolling_std

    initial_signal = zscore >= threshold

    if confirmation_days > 0:
        signal = _apply_confirmation_period(initial_signal, confirmation_days)
    else:
        signal = initial_signal

    return signal


def _apply_cross_module(combined_data: pd.DataFrame, column: str,
                        threshold: int, confirmation_days: int) -> pd.Series:
    """Generic cross-above-threshold entry signal detector."""
    if column not in combined_data.columns:
        raise ValueError(f"{column} not loaded")

    data = combined_data[column].copy()
    initial_signal = data >= threshold
    final_signal = _apply_confirmation_period(initial_signal, confirmation_days)

    # Only keep the first True value in each sequence of True values
    entry_signals = pd.Series(False, index=final_signal.index)
    for i in range(1, len(final_signal)):
        if final_signal.iloc[i] and not final_signal.iloc[i - 1]:
            entry_signals.iloc[i] = True

    return entry_signals


def apply_mmth_cross(combined_data: pd.DataFrame, config: dict) -> pd.Series:
    """MMTH cross entry signal."""
    return _apply_cross_module(
        combined_data, 'MMTH-200-day_close',
        config['threshold'], config['confirmation_days']
    )


def apply_mmtw_cross(combined_data: pd.DataFrame, config: dict) -> pd.Series:
    """MMTW cross entry signal."""
    return _apply_cross_module(
        combined_data, 'MMTW-20-day_close',
        config['threshold'], config['confirmation_days']
    )


def apply_mmfi_cross(combined_data: pd.DataFrame, config: dict) -> pd.Series:
    """MMFI cross entry signal."""
    return _apply_cross_module(
        combined_data, 'MMFI-50-day_close',
        config['threshold'], config['confirmation_days']
    )


def apply_vix_bollinger_exit(combined_data: pd.DataFrame, config: dict) -> pd.Series:
    """VIX Bollinger %B exit signal. True = exit triggered."""
    if 'VIX_close' not in combined_data.columns:
        raise ValueError("VIX data not loaded")

    lookback = config['lookback_period']
    std_dev = config['std_dev']
    threshold = config['percent_b_threshold']

    vix_data = combined_data['VIX_close']
    rolling_mean = vix_data.rolling(window=lookback).mean()
    rolling_std = vix_data.rolling(window=lookback).std()

    upper_band = rolling_mean + (rolling_std * std_dev)
    lower_band = rolling_mean - (rolling_std * std_dev)

    percent_b = (vix_data - lower_band) / (upper_band - lower_band)
    return percent_b < threshold


def apply_combined_mm_signals(combined_data: pd.DataFrame, config: dict) -> pd.Series:
    """Count of MM indicators below threshold."""
    signal_count = pd.Series(0, index=combined_data.index)

    for name, indicator_config in config['indicators'].items():
        if indicator_config['enabled']:
            column_name = f'{name}-{indicator_config["period"]}-day_close'
            if column_name not in combined_data.columns:
                logging.error(f"Column {column_name} not found in data. "
                              f"Available columns: {combined_data.columns.tolist()}")
                continue
            indicator_data = combined_data[column_name]
            signal_count += (indicator_data < config['threshold']).astype(int)

    return signal_count
