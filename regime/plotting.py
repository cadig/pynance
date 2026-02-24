"""Regime signal plotting — generates docs/spx-regime.png."""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import REGIME_CONFIG
from . import signals


def plot_regime_signals(engine) -> None:
    """
    Plot SPX data with combined regime and entry signals.
    - Red background indicates risk-off regime (from either NYSE AD z-score or all MM signals below 50%)
    - Dark green triangles indicate strong entry signals (MMTH)
    - Light green triangles indicate light entry signals (MMFI)
    - Light red down arrows indicate VIX Bollinger exit signals
    """
    combined_data = engine.combined_data
    cfg = REGIME_CONFIG

    # Get signals independently
    regime_signal = signals.apply_nyse_cumulative_ad_zscore(
        combined_data, cfg['nyse_cumulative_ad_zscore'])
    mmth_entry_signal = signals.apply_mmth_cross(
        combined_data, cfg['mmth_cross'])
    mmfi_entry_signal = signals.apply_mmfi_cross(
        combined_data, cfg['mmfi_cross'])

    # Get combined MM signals if enabled
    mm_signal_count = None
    if cfg['combined_mm_signals']['enabled']:
        mm_signal_count = signals.apply_combined_mm_signals(
            combined_data, cfg['combined_mm_signals'])

    # Calculate VIX Bollinger exit signals
    if 'VIX_close' in combined_data.columns and cfg['vix_bollinger_exit']['enabled']:
        vix_cfg = cfg['vix_bollinger_exit']
        vix_data = combined_data['VIX_close']
        rolling_mean = vix_data.rolling(window=vix_cfg['lookback_period']).mean()
        rolling_std = vix_data.rolling(window=vix_cfg['lookback_period']).std()

        upper_band = rolling_mean + (rolling_std * vix_cfg['std_dev'])
        lower_band = rolling_mean - (rolling_std * vix_cfg['std_dev'])
        percent_b = (vix_data - lower_band) / (upper_band - lower_band)
        vix_exit_signal = percent_b < vix_cfg['percent_b_threshold']
    else:
        vix_exit_signal = pd.Series(False, index=combined_data.index)
        percent_b = None

    # Count how many subplots we need
    num_subplots = 1
    if cfg['nyse_cumulative_ad_zscore']['show_subplot']:
        num_subplots += 1
    if cfg['mmth_cross']['show_subplot']:
        num_subplots += 1
    if cfg['mmfi_cross']['show_subplot']:
        num_subplots += 1
    if cfg['vix_bollinger_exit']['show_subplot']:
        num_subplots += 1

    # Create figure with appropriate number of subplots
    if num_subplots == 1:
        fig, ax1 = plt.subplots(figsize=(15, 8))
        axes = [ax1]
    else:
        fig, axes = plt.subplots(num_subplots, 1, figsize=(15, 4 * num_subplots))
        ax1 = axes[0]

    # Determine the date range for plotting
    if cfg['plot_zoom']['enabled']:
        end_date = combined_data.index[-1]
        start_date = end_date - pd.Timedelta(days=cfg['plot_zoom']['days'])
        plot_data = combined_data[start_date:end_date]
    else:
        plot_data = combined_data

    # Plot SPX data and 200-day MA
    ax1.plot(plot_data.index, plot_data['spx_close'],
             label='SPX', color='black')
    spx_200ma = plot_data['spx_close'].rolling(window=200).mean()
    ax1.plot(spx_200ma.index, spx_200ma, label='200-day MA', color='gray', linestyle='--')

    # Determine red background conditions
    red_background = pd.Series(False, index=plot_data.index)
    red_background |= ~regime_signal[plot_data.index]

    # Apply red background where needed (from NYSE AD z-score)
    if red_background.any():
        ax1.fill_between(
            plot_data.index,
            plot_data['spx_close'].min(),
            plot_data['spx_close'].max(),
            where=red_background,
            color='red',
            alpha=0.2,
            label='Risk-Off Period (NYSE AD)'
        )

    # Show MM signal colors where there's no red background from NYSE AD
    if mm_signal_count is not None:
        mm_colors = {
            3: ('red', 'Three Signals Below 50%'),
            2: ('orange', 'Two Signals Below 50%'),
            1: ('yellow', 'One Signal Below 50%'),
            0: ('green', 'All Signals Above 50%')
        }
        for count, (color, label) in mm_colors.items():
            mask = (mm_signal_count[plot_data.index] == count) & ~red_background
            if mask.any():
                ax1.fill_between(
                    plot_data.index,
                    plot_data['spx_close'].min(),
                    plot_data['spx_close'].max(),
                    where=mask,
                    color=color,
                    alpha=0.2,
                    label=label
                )

    # Plot MMTH entry signals (strong)
    mmth_entry_dates = plot_data.index[mmth_entry_signal[plot_data.index]]
    mmth_entry_prices = plot_data.loc[mmth_entry_dates, 'spx_close']
    ax1.scatter(mmth_entry_dates, mmth_entry_prices,
                marker='^', color='green', s=100,
                label='Strong Entry Signal (MMTH)')

    # Plot MMFI entry signals (light)
    mmfi_entry_dates = plot_data.index[mmfi_entry_signal[plot_data.index]]
    mmfi_entry_prices = plot_data.loc[mmfi_entry_dates, 'spx_close']
    ax1.scatter(mmfi_entry_dates, mmfi_entry_prices,
                marker='^', color='lightgreen', s=100,
                label='Light Entry Signal (MMFI)')

    # Plot VIX Bollinger exit signals if enabled
    if cfg['vix_bollinger_exit']['enabled']:
        vix_exit_dates = plot_data.index[vix_exit_signal[plot_data.index]]
        vix_exit_prices = plot_data.loc[vix_exit_dates, 'spx_close']
        arrow_y_positions = vix_exit_prices * 1.01

        ax1.scatter(vix_exit_dates, arrow_y_positions,
                    marker='v',
                    color='red',
                    alpha=0.3,
                    s=50,
                    label='Light Exit Signal (VIX %B)')

    # Add zoom status to title
    zoom_status = "Zoomed View" if cfg['plot_zoom']['enabled'] else "Full View"
    ax1.set_title(f'SPX with Combined Regime, Entry, and Exit Signals ({zoom_status})')
    ax1.set_ylabel('SPX Price')
    ax1.legend()
    ax1.grid(True)

    # Plot subplots if enabled
    current_ax = 1
    if cfg['nyse_cumulative_ad_zscore']['show_subplot']:
        ad_cfg = cfg['nyse_cumulative_ad_zscore']
        adrn_data = plot_data['ADRN_close']
        normalized_data = np.tanh(np.log(adrn_data))
        cumulative_ad = normalized_data.cumsum()
        smoothed_ad = cumulative_ad.rolling(window=ad_cfg['smoothing_period']).mean()

        rolling_mean = smoothed_ad.rolling(window=ad_cfg['lookback_period']).mean()
        rolling_std = smoothed_ad.rolling(window=ad_cfg['lookback_period']).std()
        zscore = (smoothed_ad - rolling_mean) / rolling_std

        axes[current_ax].plot(zscore.index, zscore, label='Z-Score', color='blue')
        axes[current_ax].axhline(y=ad_cfg['threshold'], color='red', linestyle='--',
                                 label=f'Threshold ({ad_cfg["threshold"]})')
        axes[current_ax].axhline(y=0, color='black', linestyle='--', alpha=0.3)
        axes[current_ax].set_ylabel('Z-Score')
        axes[current_ax].legend()
        axes[current_ax].grid(True)
        current_ax += 1

    if cfg['mmth_cross']['show_subplot']:
        mmth_data = plot_data['MMTH-200-day_close']
        mmth_threshold = cfg['mmth_cross']['threshold']
        axes[current_ax].plot(mmth_data.index, mmth_data, label='MMTH', color='blue')
        axes[current_ax].axhline(y=mmth_threshold, color='red', linestyle='--',
                                 label=f'{mmth_threshold}%')
        axes[current_ax].set_ylabel('MMTH')
        axes[current_ax].legend()
        axes[current_ax].grid(True)
        current_ax += 1

    if cfg['mmfi_cross']['show_subplot']:
        mmfi_data = plot_data['MMFI-50-day_close']
        mmfi_threshold = cfg['mmfi_cross']['threshold']
        axes[current_ax].plot(mmfi_data.index, mmfi_data, label='MMFI', color='blue')
        axes[current_ax].axhline(y=mmfi_threshold, color='red', linestyle='--',
                                 label=f'{mmfi_threshold}%')
        axes[current_ax].set_ylabel('MMFI')
        axes[current_ax].legend()
        axes[current_ax].grid(True)
        current_ax += 1

    if cfg['vix_bollinger_exit']['show_subplot'] and percent_b is not None:
        threshold = cfg['vix_bollinger_exit']['percent_b_threshold']
        axes[current_ax].plot(percent_b[plot_data.index], label='VIX %B', color='purple')
        axes[current_ax].axhline(y=threshold, color='red', linestyle='--',
                                 label=f'Threshold ({threshold})')
        axes[current_ax].set_ylabel('VIX %B')
        axes[current_ax].legend()
        axes[current_ax].grid(True)

    plt.tight_layout()

    # Save the plot to file if outputFile is enabled
    if cfg['outputFile']:
        pages_dir = Path(__file__).parent.parent / 'docs'
        pages_dir.mkdir(exist_ok=True)
        output_path = pages_dir / 'spx-regime.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logging.info(f"Plot saved to: {output_path}")

    if cfg['showPlot']:
        plt.show()
    else:
        plt.close()
