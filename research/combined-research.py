import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging
from typing import List
import json
from datetime import datetime

# Configuration for the combined research modules
COMBINED_CONFIG = {
    'show_subplots': False,  # Whether to show MMTH and MMFI subplots
    'outputFile': True,  # Whether to save the plot to a file
    'showPlot': False,  # Whether to display the plot
    'plot_zoom': {
        'enabled': True,  # Whether to show zoomed-in view by default
        'days': 200  # Number of days to show in zoomed view
    },
    'nyse_cumulative_ad_zscore': {
        'enabled': True,
        'type': 'regime',  # 'regime', 'entry', or 'exit'
        'lookback_period': 252,  # Number of days to use for z-score calculation
        'smoothing_period': 50,  # Number of days to smooth the cumulative AD line
        'threshold': -1.0,  # Risk-off when z-score goes below this threshold
        'confirmation_days': 0,  # Number of days the z-score must stay below threshold
        'show_subplot': False  # Whether to show the z-score subplot
    },
    'mmth_cross': {
        'enabled': True,
        'type': 'entry-strong',  # 'entry-strong', 'entry-light', or 'exit'
        'threshold': 25,  # Entry signal when crossing back above this threshold
        'confirmation_days': 0,  # Number of days the indicator must stay above threshold
        'period': 200,  # 200-day moving average
        'show_subplot': False  # Whether to show the MMTH subplot
    },
    'mmtw_cross': {
        'enabled': True,
        'type': 'entry-light',  # 'entry-strong', 'entry-light', or 'exit'
        'threshold': 25,  # Entry signal when crossing back above this threshold
        'confirmation_days': 3,  # Number of days the indicator must stay above threshold
        'period': 50,  # 50-day moving average
        'show_subplot': False  # Whether to show the MMTW subplot
    },
    'mmfi_cross': {
        'enabled': True,
        'type': 'entry-light',  # 'entry-strong', 'entry-light', or 'exit'
        'threshold': 25,  # Entry signal when crossing back above this threshold
        'confirmation_days': 3,  # Number of days the indicator must stay above threshold
        'period': 50,  # 50-day moving average
        'show_subplot': False  # Whether to show the MMFI subplot
    },
    'vix_bollinger_exit': {
        'enabled': True,
        'type': 'exit-light',  # 'entry-strong', 'entry-light', or 'exit'
        'lookback_period': 20,
        'std_dev': 2.0,
        'percent_b_threshold': 0,
        'show_subplot': False  # Whether to show the VIX %B subplot
    },
    'combined_mm_signals': {
        'enabled': True,
        'threshold': 50,  # Threshold for all MM signals
        'indicators': {
            'MMTW': {
                'enabled': True,
                'period': 20
            },
            'MMFI': {
                'enabled': True,
                'period': 50
            },
            'MMTH': {
                'enabled': True,
                'period': 200
            }
        },
        'show_subplot': False
    },
    'output_json_results': True
}

class CombinedResearch:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.spx_data = None
        self.additional_data = {}
        self.combined_data = None
        self.returns = None
        
    def load_data(self, required_symbols: List[str]) -> None:
        """
        Load and combine data from multiple CSV files.
        
        Args:
            required_symbols (List[str]): List of symbol filenames to load
        """
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
                # Prefix columns with symbol name (without .csv extension)
                prefix = symbol.replace('.csv', '')
                df.columns = [f'{prefix}_{col}' for col in df.columns]
                self.additional_data[symbol] = df
            else:
                logging.warning(f"File not found: {file_path}")
        
        # Combine all data
        dfs = [self.spx_data] + list(self.additional_data.values())
        
        # First, find the common date range
        start_dates = [df.index.min() for df in dfs]
        end_dates = [df.index.max() for df in dfs]
        common_start = max(start_dates)
        common_end = min(end_dates)
        
        # Trim all dataframes to the common date range
        dfs = [df[common_start:common_end] for df in dfs]
        
        # Now combine the trimmed dataframes
        self.combined_data = pd.concat(dfs, axis=1)
        
        # Forward fill any missing values
        self.combined_data = self.combined_data.fillna(method='ffill')
        
        # Calculate returns
        self.calculate_returns()

    def calculate_returns(self) -> None:
        """Calculate daily returns for SPX."""
        self.returns = self.combined_data['spx_close'].pct_change()
        self.returns = self.returns.fillna(0)

    def apply_nyse_cumulative_ad_zscore_module(self) -> pd.Series:
        """
        Apply NYSE cumulative AD z-score module to generate regime signals.
        Returns True for risk-on periods, False for risk-off periods.
        """
        # Get configuration parameters
        lookback = COMBINED_CONFIG['nyse_cumulative_ad_zscore']['lookback_period']
        smoothing_period = COMBINED_CONFIG['nyse_cumulative_ad_zscore']['smoothing_period']
        threshold = COMBINED_CONFIG['nyse_cumulative_ad_zscore']['threshold']
        confirmation_days = COMBINED_CONFIG['nyse_cumulative_ad_zscore']['confirmation_days']
        
        # Calculate normalized ADRN
        adrn_data = self.combined_data['ADRN_close']
        normalized_data = np.tanh(np.log(adrn_data))
        
        # Calculate cumulative sum
        cumulative_ad = normalized_data.cumsum()
        
        # Apply smoothing
        smoothed_ad = cumulative_ad.rolling(window=smoothing_period).mean()
        
        # Calculate z-score
        rolling_mean = smoothed_ad.rolling(window=lookback).mean()
        rolling_std = smoothed_ad.rolling(window=lookback).std()
        zscore = (smoothed_ad - rolling_mean) / rolling_std
        
        # Generate initial signal (True for risk-on, False for risk-off)
        initial_signal = zscore >= threshold
        
        # Apply confirmation period if specified
        if confirmation_days > 0:
            signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        else:
            signal = initial_signal
        
        return signal

    def apply_mmth_cross_module(self) -> pd.Series:
        """
        Apply the MMTH cross module.
        Returns a boolean series indicating entry signals.
        """
        if 'MMTH-200-day_close' not in self.combined_data.columns:
            raise ValueError("MMTH data not loaded")
            
        # Get configuration parameters
        threshold = COMBINED_CONFIG['mmth_cross']['threshold']
        confirmation_days = COMBINED_CONFIG['mmth_cross']['confirmation_days']
        
        # Get MMTH data
        mmth_data = self.combined_data['MMTH-200-day_close'].copy()
        
        # Create initial signal - entry when crossing back above threshold
        initial_signal = mmth_data >= threshold
        
        # Apply confirmation period
        final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        
        # Only keep the first True value in each sequence of True values
        entry_signals = pd.Series(False, index=final_signal.index)
        for i in range(1, len(final_signal)):
            if final_signal.iloc[i] and not final_signal.iloc[i-1]:
                entry_signals.iloc[i] = True
        
        return entry_signals

    def apply_mmtw_cross_module(self) -> pd.Series:
        """
        Apply the MMTW cross module.
        Returns a boolean series indicating entry signals.
        """
        if 'MMTW-20-day_close' not in self.combined_data.columns:
            raise ValueError("MMTW data not loaded")
            
        # Get configuration parameters
        threshold = COMBINED_CONFIG['mmtw_cross']['threshold']
        confirmation_days = COMBINED_CONFIG['mmtw_cross']['confirmation_days']
        
        # Get MMTW data
        mmtw_data = self.combined_data['MMTW-20-day_close'].copy()
        
        # Create initial signal - entry when crossing back above threshold
        initial_signal = mmtw_data >= threshold
        
        # Apply confirmation period
        final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        
        # Only keep the first True value in each sequence of True values
        entry_signals = pd.Series(False, index=final_signal.index)
        for i in range(1, len(final_signal)):
            if final_signal.iloc[i] and not final_signal.iloc[i-1]:
                entry_signals.iloc[i] = True
        
        return entry_signals

    def apply_mmfi_cross_module(self) -> pd.Series:
        """
        Apply the MMFI cross module.
        Returns a boolean series indicating entry signals.
        """
        if 'MMFI-50-day_close' not in self.combined_data.columns:
            raise ValueError("MMFI data not loaded")
            
        # Get configuration parameters
        threshold = COMBINED_CONFIG['mmfi_cross']['threshold']
        confirmation_days = COMBINED_CONFIG['mmfi_cross']['confirmation_days']
        
        # Get MMFI data
        mmfi_data = self.combined_data['MMFI-50-day_close'].copy()
        
        # Create initial signal - entry when crossing back above threshold
        initial_signal = mmfi_data >= threshold
        
        # Apply confirmation period
        final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        
        # Only keep the first True value in each sequence of True values
        entry_signals = pd.Series(False, index=final_signal.index)
        for i in range(1, len(final_signal)):
            if final_signal.iloc[i] and not final_signal.iloc[i-1]:
                entry_signals.iloc[i] = True
        
        return entry_signals

    def _apply_confirmation_period(self, initial_signal: pd.Series, confirmation_days: int) -> pd.Series:
        """
        Helper method to apply confirmation period to a signal.
        
        Args:
            initial_signal (pd.Series): Initial boolean signal series
            confirmation_days (int): Number of days required for confirmation
            
        Returns:
            pd.Series: Confirmed signal series
        """
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

    def apply_vix_bollinger_exit_module(self) -> pd.Series:
        """
        Apply VIX Bollinger exit module to generate exit signals.
        Returns True for exit signals, False for other signals.
        """
        if 'VIX_close' not in self.combined_data.columns:
            raise ValueError("VIX data not loaded")
            
        # Get configuration parameters
        lookback = COMBINED_CONFIG['vix_bollinger_exit']['lookback_period']
        std_dev = COMBINED_CONFIG['vix_bollinger_exit']['std_dev']
        threshold = COMBINED_CONFIG['vix_bollinger_exit']['percent_b_threshold']
        
        vix_data = self.combined_data['VIX_close']
        rolling_mean = vix_data.rolling(window=lookback).mean()
        rolling_std = vix_data.rolling(window=lookback).std()
        
        # Calculate bands
        upper_band = rolling_mean + (rolling_std * std_dev)
        lower_band = rolling_mean - (rolling_std * std_dev)
        
        # Calculate %B
        percent_b = (vix_data - lower_band) / (upper_band - lower_band)
        
        # Generate exit signals
        exit_signal = percent_b < threshold
        
        return exit_signal

    def apply_combined_mm_signals_module(self) -> pd.Series:
        """
        Apply the combined MM signals module to identify when signals are below threshold.
        
        Returns:
            pd.Series: Series containing the count of signals below threshold
        """
        if self.combined_data is None:
            logging.error("No data loaded. Call load_data() first.")
            return None
            
        # Initialize signal count series
        signal_count = pd.Series(0, index=self.combined_data.index)
        
        # Check each indicator
        for name, config in COMBINED_CONFIG['combined_mm_signals']['indicators'].items():
            if config['enabled']:
                # Get the indicator data using the correct column name format with _close suffix
                column_name = f'{name}-{config["period"]}-day_close'
                if column_name not in self.combined_data.columns:
                    logging.error(f"Column {column_name} not found in data. Available columns: {self.combined_data.columns.tolist()}")
                    continue
                    
                indicator_data = self.combined_data[column_name]
                
                # Count signals below threshold
                signal_count += (indicator_data < COMBINED_CONFIG['combined_mm_signals']['threshold']).astype(int)
        
        return signal_count

    def generate_json_results(self) -> dict:
        """
        Generate JSON results with current datetime, background color, and signal statuses.
        Only includes modules that are currently enabled and set to True.
        
        Returns:
            dict: JSON results containing datetime, background color, and signal booleans
        """
        if self.combined_data is None:
            logging.error("No data loaded. Call load_data() first.")
            return {}
        
        # Get current datetime
        current_datetime = datetime.now().isoformat()
        
        # Get the latest data point for analysis
        latest_data = self.combined_data.iloc[-1]
        
        # Calculate 200-day MA and check if SPX is above it
        spx_200ma = self.combined_data['spx_close'].rolling(window=200).mean().iloc[-1]
        above_200ma = latest_data['spx_close'] > spx_200ma
        
        # Determine final background color based on active modules
        background_color = "green"  # Default to green
        
        # Check NYSE cumulative AD z-score for risk-off regime
        if COMBINED_CONFIG['nyse_cumulative_ad_zscore']['enabled']:
            regime_signal = self.apply_nyse_cumulative_ad_zscore_module()
            if not regime_signal.iloc[-1]:  # Risk-off
                background_color = "red"
        
        # Check combined MM signals if enabled and no red background from NYSE AD
        if (COMBINED_CONFIG['combined_mm_signals']['enabled'] and 
            background_color != "red"):
            mm_signal_count = self.apply_combined_mm_signals_module()
            latest_mm_count = mm_signal_count.iloc[-1]
            
            if latest_mm_count == 3:
                background_color = "red"
            elif latest_mm_count == 2:
                background_color = "orange"
            elif latest_mm_count == 1:
                background_color = "yellow"
            else:  # latest_mm_count == 0
                background_color = "green"
        
        # Build results dictionary
        results = {
            "datetime": current_datetime,
            "background_color": background_color,
            "above_200ma": bool(above_200ma)
        }
        
        # Add signal statuses for enabled modules
        if COMBINED_CONFIG['nyse_cumulative_ad_zscore']['enabled']:
            regime_signal = self.apply_nyse_cumulative_ad_zscore_module()
            results["nyse_cumulative_ad_zscore"] = bool(regime_signal.iloc[-1])
        
        if COMBINED_CONFIG['mmth_cross']['enabled']:
            mmth_signal = self.apply_mmth_cross_module()
            results["mmth_cross"] = bool(mmth_signal.iloc[-1])
        
        if COMBINED_CONFIG['mmtw_cross']['enabled']:
            mmtw_signal = self.apply_mmtw_cross_module()
            results["mmtw_cross"] = bool(mmtw_signal.iloc[-1])
        
        if COMBINED_CONFIG['mmfi_cross']['enabled']:
            mmfi_signal = self.apply_mmfi_cross_module()
            results["mmfi_cross"] = bool(mmfi_signal.iloc[-1])
        
        if COMBINED_CONFIG['vix_bollinger_exit']['enabled']:
            vix_signal = self.apply_vix_bollinger_exit_module()
            results["vix_bollinger_exit"] = bool(vix_signal.iloc[-1])
        
        if COMBINED_CONFIG['combined_mm_signals']['enabled']:
            mm_signal_count = self.apply_combined_mm_signals_module()
            results["combined_mm_signals"] = int(mm_signal_count.iloc[-1])
        
        return results

    def save_json_results(self) -> None:
        """
        Save JSON results to the docs directory if output_json_results is enabled.
        """
        if not COMBINED_CONFIG['output_json_results']:
            return
        
        try:
            # Generate results
            results = self.generate_json_results()
            
            if not results:
                logging.warning("No results to save")
                return
            
            # Get the docs directory path
            docs_dir = Path(__file__).parent.parent / 'docs'
            docs_dir.mkdir(exist_ok=True)
            
            # Save JSON file with static filename (overwrites each run)
            json_filename = "spx-regime-results.json"
            json_path = docs_dir / json_filename
            
            with open(json_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            logging.info(f"JSON results saved to: {json_path}")
            
        except Exception as e:
            logging.error(f"Failed to save JSON results: {e}")

    def plot_combined_signals(self) -> None:
        """
        Plot SPX data with combined regime and entry signals.
        - Red background indicates risk-off regime (from either NYSE AD z-score or all MM signals below 50%)
        - Dark green triangles indicate strong entry signals (MMTH)
        - Light green triangles indicate light entry signals (MMFI)
        - Light red down arrows indicate VIX Bollinger exit signals
        """
        # Get signals independently
        regime_signal = self.apply_nyse_cumulative_ad_zscore_module()
        mmth_entry_signal = self.apply_mmth_cross_module()
        mmfi_entry_signal = self.apply_mmfi_cross_module()
        
        # Get combined MM signals if enabled
        mm_signal_count = None
        if COMBINED_CONFIG['combined_mm_signals']['enabled']:
            mm_signal_count = self.apply_combined_mm_signals_module()
        
        # Calculate VIX Bollinger exit signals
        if 'VIX_close' in self.combined_data.columns and COMBINED_CONFIG['vix_bollinger_exit']['enabled']:
            # Get configuration parameters
            lookback = COMBINED_CONFIG['vix_bollinger_exit']['lookback_period']
            std_dev = COMBINED_CONFIG['vix_bollinger_exit']['std_dev']
            threshold = COMBINED_CONFIG['vix_bollinger_exit']['percent_b_threshold']
            
            vix_data = self.combined_data['VIX_close']
            rolling_mean = vix_data.rolling(window=lookback).mean()
            rolling_std = vix_data.rolling(window=lookback).std()
            
            # Calculate bands
            upper_band = rolling_mean + (rolling_std * std_dev)
            lower_band = rolling_mean - (rolling_std * std_dev)
            
            # Calculate %B
            percent_b = (vix_data - lower_band) / (upper_band - lower_band)
            
            # Generate exit signals
            vix_exit_signal = percent_b < threshold
        else:
            vix_exit_signal = pd.Series(False, index=self.combined_data.index)
        
        # Count how many subplots we need
        num_subplots = 1  # Always have the main SPX plot
        if COMBINED_CONFIG['nyse_cumulative_ad_zscore']['show_subplot']:
            num_subplots += 1
        if COMBINED_CONFIG['mmth_cross']['show_subplot']:
            num_subplots += 1
        if COMBINED_CONFIG['mmfi_cross']['show_subplot']:
            num_subplots += 1
        if COMBINED_CONFIG['vix_bollinger_exit']['show_subplot']:
            num_subplots += 1
            
        # Create figure with appropriate number of subplots
        if num_subplots == 1:
            fig, ax1 = plt.subplots(figsize=(15, 8))
            axes = [ax1]
        else:
            fig, axes = plt.subplots(num_subplots, 1, figsize=(15, 4 * num_subplots))
            ax1 = axes[0]
        
        # Determine the date range for plotting
        if COMBINED_CONFIG['plot_zoom']['enabled']:
            end_date = self.combined_data.index[-1]
            start_date = end_date - pd.Timedelta(days=COMBINED_CONFIG['plot_zoom']['days'])
            plot_data = self.combined_data[start_date:end_date]
        else:
            plot_data = self.combined_data
        
        # Plot SPX data and 200-day MA
        ax1.plot(plot_data.index, plot_data['spx_close'], 
                label='SPX', color='black')
        spx_200ma = plot_data['spx_close'].rolling(window=200).mean()
        ax1.plot(spx_200ma.index, spx_200ma, label='200-day MA', color='gray', linestyle='--')
        
        # Determine red background conditions
        red_background = pd.Series(False, index=plot_data.index)
        
        # Check NYSE cumulative AD z-score for red background
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
                mask = (mm_signal_count[plot_data.index] == count) & ~red_background  # Only show where no red background
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
        if COMBINED_CONFIG['vix_bollinger_exit']['enabled']:
            vix_exit_dates = plot_data.index[vix_exit_signal[plot_data.index]]
            vix_exit_prices = plot_data.loc[vix_exit_dates, 'spx_close']
            arrow_y_positions = vix_exit_prices * 1.01  # 1% above the price
            
            ax1.scatter(vix_exit_dates, arrow_y_positions,
                       marker='v',  # Downward pointing triangle
                       color='red',
                       alpha=0.3,  # Lighter red for exit-light signal
                       s=50,  # Size of the arrows
                       label='Light Exit Signal (VIX %B)')
        
        # Add zoom status to title
        zoom_status = "Zoomed View" if COMBINED_CONFIG['plot_zoom']['enabled'] else "Full View"
        ax1.set_title(f'SPX with Combined Regime, Entry, and Exit Signals ({zoom_status})')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot subplots if enabled
        current_ax = 1
        if COMBINED_CONFIG['nyse_cumulative_ad_zscore']['show_subplot']:
            # Calculate and plot NYSE cumulative AD z-score
            lookback = COMBINED_CONFIG['nyse_cumulative_ad_zscore']['lookback_period']
            smoothing_period = COMBINED_CONFIG['nyse_cumulative_ad_zscore']['smoothing_period']
            threshold = COMBINED_CONFIG['nyse_cumulative_ad_zscore']['threshold']
            
            adrn_data = plot_data['ADRN_close']
            normalized_data = np.tanh(np.log(adrn_data))
            cumulative_ad = normalized_data.cumsum()
            smoothed_ad = cumulative_ad.rolling(window=smoothing_period).mean()
            
            rolling_mean = smoothed_ad.rolling(window=lookback).mean()
            rolling_std = smoothed_ad.rolling(window=lookback).std()
            zscore = (smoothed_ad - rolling_mean) / rolling_std
            
            # Plot z-score
            axes[current_ax].plot(zscore.index, zscore, label='Z-Score', color='blue')
            axes[current_ax].axhline(y=threshold, color='red', linestyle='--', 
                                   label=f'Threshold ({threshold})')
            axes[current_ax].axhline(y=0, color='black', linestyle='--', alpha=0.3)
            
            axes[current_ax].set_ylabel('Z-Score')
            axes[current_ax].legend()
            axes[current_ax].grid(True)
            current_ax += 1
            
        if COMBINED_CONFIG['mmth_cross']['show_subplot']:
            # Plot MMTH data
            mmth_data = plot_data['MMTH-200-day_close']
            mmth_threshold = COMBINED_CONFIG['mmth_cross']['threshold']
            axes[current_ax].plot(mmth_data.index, mmth_data, label='MMTH', color='blue')
            axes[current_ax].axhline(y=mmth_threshold, color='red', linestyle='--', 
                                   label=f'{mmth_threshold}%')
            axes[current_ax].set_ylabel('MMTH')
            axes[current_ax].legend()
            axes[current_ax].grid(True)
            current_ax += 1
            
        if COMBINED_CONFIG['mmfi_cross']['show_subplot']:
            # Plot MMFI data
            mmfi_data = plot_data['MMFI-50-day_close']
            mmfi_threshold = COMBINED_CONFIG['mmfi_cross']['threshold']
            axes[current_ax].plot(mmfi_data.index, mmfi_data, label='MMFI', color='blue')
            axes[current_ax].axhline(y=mmfi_threshold, color='red', linestyle='--', 
                                   label=f'{mmfi_threshold}%')
            axes[current_ax].set_ylabel('MMFI')
            axes[current_ax].legend()
            axes[current_ax].grid(True)
            current_ax += 1
            
        if COMBINED_CONFIG['vix_bollinger_exit']['show_subplot']:
            # Plot VIX %B
            axes[current_ax].plot(percent_b[plot_data.index], label='VIX %B', color='purple')
            axes[current_ax].axhline(y=threshold, color='red', linestyle='--', 
                                   label=f'Threshold ({threshold})')
            axes[current_ax].set_ylabel('VIX %B')
            axes[current_ax].legend()
            axes[current_ax].grid(True)
        
        plt.tight_layout()
        
        # Save the plot to file if outputFile is enabled
        if COMBINED_CONFIG['outputFile']:
            # Get the docs directory path (one level up from research)
            pages_dir = Path(__file__).parent.parent / 'docs'
            pages_dir.mkdir(exist_ok=True)  # Create the directory if it doesn't exist
            
            # Save the plot
            output_path = pages_dir / 'spx-regime.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            logging.info(f"Plot saved to: {output_path}")
        
        # Show the plot if showPlot is enabled
        if COMBINED_CONFIG['showPlot']:
            plt.show()
        else:
            plt.close()  # Close the figure to free memory

def main():
    # Initialize research
    research = CombinedResearch()
    
    # Determine which data files we need based on active modules
    required_files = ['SPX.csv']
    
    # Add VIX if VIX Bollinger exit module is enabled
    if COMBINED_CONFIG['vix_bollinger_exit']['enabled']:
        required_files.append('VIX.csv')
    
    # Add ADRN if NYSE cumulative AD z-score module is enabled
    if COMBINED_CONFIG['nyse_cumulative_ad_zscore']['enabled']:
        required_files.append('ADRN.csv')
    
    # Add percentage of stocks data if combined MM signals module is enabled
    if COMBINED_CONFIG['combined_mm_signals']['enabled']:
        for name, config in COMBINED_CONFIG['combined_mm_signals']['indicators'].items():
            if config['enabled']:
                required_files.append(f'{name}-{config["period"]}-day.csv')
    
    # Load all required data
    logging.info("Loading required data files: %s", required_files)
    research.load_data(required_files)
    
    # Plot combined signals (this will handle both NYSE AD z-score and combined MM signals)
    research.plot_combined_signals()
    
    # Save JSON results if enabled
    research.save_json_results()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    main()
