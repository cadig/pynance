"""Regime detection engine — data loading, signal orchestration, JSON output."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd

from .config import REGIME_CONFIG
from . import signals


class RegimeEngine:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.spx_data = None
        self.additional_data = {}
        self.combined_data = None
        self.returns = None

    def load_data(self, required_symbols: List[str]) -> None:
        """Load and combine data from multiple CSV files."""
        # Load SPX data first
        spx_path = self.data_dir / 'SPX.csv'
        self.spx_data = pd.read_csv(spx_path, index_col=0, parse_dates=True)
        self.spx_data.columns = ['spx_' + col for col in self.spx_data.columns]

        # Load additional data
        for symbol in required_symbols:
            if symbol == 'SPX.csv':
                continue
            file_path = self.data_dir / symbol
            if file_path.exists():
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                prefix = symbol.replace('.csv', '')
                df.columns = [f'{prefix}_{col}' for col in df.columns]
                self.additional_data[symbol] = df
            else:
                logging.warning(f"File not found: {file_path}")

        # Combine all data
        dfs = [self.spx_data] + list(self.additional_data.values())

        # Find the common date range
        start_dates = [df.index.min() for df in dfs]
        end_dates = [df.index.max() for df in dfs]
        common_start = max(start_dates)
        common_end = min(end_dates)

        # Trim all dataframes to the common date range
        dfs = [df[common_start:common_end] for df in dfs]

        # Combine the trimmed dataframes
        self.combined_data = pd.concat(dfs, axis=1)
        self.combined_data = self.combined_data.ffill()

        self.calculate_returns()

    def calculate_returns(self) -> None:
        """Calculate daily returns for SPX."""
        self.returns = self.combined_data['spx_close'].pct_change()
        self.returns = self.returns.fillna(0)

    def generate_json_results(self) -> dict:
        """Generate JSON results with datetime, background color, and signal statuses."""
        if self.combined_data is None:
            logging.error("No data loaded. Call load_data() first.")
            return {}

        current_datetime = datetime.now().isoformat()
        latest_data = self.combined_data.iloc[-1]

        # Calculate 200-day MA and check if SPX is above it
        spx_200ma = self.combined_data['spx_close'].rolling(window=200).mean().iloc[-1]
        above_200ma = latest_data['spx_close'] > spx_200ma

        # Determine final background color based on active modules
        background_color = "green"

        # Check NYSE cumulative AD z-score for risk-off regime
        if REGIME_CONFIG['nyse_cumulative_ad_zscore']['enabled']:
            regime_signal = signals.apply_nyse_cumulative_ad_zscore(
                self.combined_data, REGIME_CONFIG['nyse_cumulative_ad_zscore'])
            if not regime_signal.iloc[-1]:
                background_color = "red"

        # Check combined MM signals if enabled and no red background from NYSE AD
        if (REGIME_CONFIG['combined_mm_signals']['enabled'] and
                background_color != "red"):
            mm_signal_count = signals.apply_combined_mm_signals(
                self.combined_data, REGIME_CONFIG['combined_mm_signals'])
            latest_mm_count = mm_signal_count.iloc[-1]

            if latest_mm_count == 3:
                background_color = "red"
            elif latest_mm_count == 2:
                background_color = "orange"
            elif latest_mm_count == 1:
                background_color = "yellow"
            else:
                background_color = "green"

        # Build results dictionary
        results = {
            "datetime": current_datetime,
            "background_color": background_color,
            "above_200ma": bool(above_200ma)
        }

        # Add VIX close price if VIX data is available
        if 'VIX_close' in self.combined_data.columns:
            results["VIX_close"] = float(latest_data['VIX_close'])

        # Add signal statuses for enabled modules
        if REGIME_CONFIG['nyse_cumulative_ad_zscore']['enabled']:
            regime_signal = signals.apply_nyse_cumulative_ad_zscore(
                self.combined_data, REGIME_CONFIG['nyse_cumulative_ad_zscore'])
            results["nyse_cumulative_ad_zscore"] = bool(regime_signal.iloc[-1])

        if REGIME_CONFIG['mmth_cross']['enabled']:
            mmth_signal = signals.apply_mmth_cross(
                self.combined_data, REGIME_CONFIG['mmth_cross'])
            results["mmth_cross"] = bool(mmth_signal.iloc[-1])

        if REGIME_CONFIG['mmtw_cross']['enabled']:
            mmtw_signal = signals.apply_mmtw_cross(
                self.combined_data, REGIME_CONFIG['mmtw_cross'])
            results["mmtw_cross"] = bool(mmtw_signal.iloc[-1])

        if REGIME_CONFIG['mmfi_cross']['enabled']:
            mmfi_signal = signals.apply_mmfi_cross(
                self.combined_data, REGIME_CONFIG['mmfi_cross'])
            results["mmfi_cross"] = bool(mmfi_signal.iloc[-1])

        if REGIME_CONFIG['vix_bollinger_exit']['enabled']:
            vix_signal = signals.apply_vix_bollinger_exit(
                self.combined_data, REGIME_CONFIG['vix_bollinger_exit'])
            results["vix_bollinger_exit"] = bool(vix_signal.iloc[-1])

        if REGIME_CONFIG['combined_mm_signals']['enabled']:
            mm_signal_count = signals.apply_combined_mm_signals(
                self.combined_data, REGIME_CONFIG['combined_mm_signals'])
            results["combined_mm_signals"] = int(mm_signal_count.iloc[-1])

        return results

    def save_json_results(self) -> None:
        """Save JSON results to the docs directory."""
        if not REGIME_CONFIG['output_json_results']:
            return

        try:
            results = self.generate_json_results()
            if not results:
                logging.warning("No results to save")
                return

            docs_dir = Path(__file__).parent.parent / 'docs'
            docs_dir.mkdir(exist_ok=True)

            json_filename = "spx-regime-results.json"
            json_path = docs_dir / json_filename

            with open(json_path, 'w') as f:
                json.dump(results, f, indent=2)

            logging.info(f"JSON results saved to: {json_path}")

        except Exception as e:
            logging.error(f"Failed to save JSON results: {e}")
