import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging
from typing import Dict, List, Tuple
import json
from datetime import datetime

# Configuration for the entry signal modules
ENTRY_CONFIG = {
    'mmth_25_cross': {
        'enabled': True,
        'threshold': 25,  # Entry signal when crossing back above this threshold
        'confirmation_days': 0  # Number of days the indicator must stay above threshold
    },
    'mmfi_25_cross': {
        'enabled': True,
        'threshold': 15,  # Entry signal when crossing back above this threshold
        'confirmation_days': 0  # Number of days the indicator must stay above threshold
    },
    'mmtw_25_cross': {
        'enabled': True,
        'threshold': 10,  # Entry signal when crossing back above this threshold
        'confirmation_days': 0  # Number of days the indicator must stay above threshold
    },
    'r3tw_25_cross': {
        'enabled': True,
        'threshold': 10,  # Entry signal when crossing back above this threshold
        'confirmation_days': 0  # Number of days the indicator must stay above threshold
    },
    'r3tw_mmtw_cross': {
        'enabled': False,
        'r3tw_threshold': 20,  # R3TW must cross below this threshold first
        'confirmation_days': 0  # Number of days the crossover must be maintained
    }
}

# Configuration for which modules to run
MODULE_CONFIG = {
    'mmth_25_cross': {
        'enabled': False,
        'threshold': 25,  # Entry when crossing above this threshold
        'period': 200  # 200-day moving average
    },
    'mmtw_25_cross': {
        'enabled': False,
        'threshold': 25,  # Entry when crossing above this threshold
        'period': 20  # 20-day moving average
    },
    'mmfi_25_cross': {
        'enabled': False,
        'threshold': 25,  # Entry when crossing above this threshold
        'period': 50  # 50-day moving average
    },
    'r3tw_25_cross': {
        'enabled': False,
        'threshold': 25,  # Entry when crossing above this threshold
        'period': 20  # 20-day moving average
    },
    'r3tw_mmtw_cross': {
        'enabled': False,
        'threshold': 0,  # Entry when R3TW crosses above MMTW
        'period': 20  # 20-day moving average
    },
    'vix_bollinger_entry': {
        'enabled': True,
        'lookback_period': 20,  # Number of days for Bollinger Band calculation
        'std_dev': 2.0,  # Number of standard deviations for bands
        'percent_b_threshold': 1.0  # Entry when %B goes above this threshold
    }
}

class EntryResearch:
    def __init__(self):
        self.data_dir = Path(__file__).parent / 'data'
        self.spx_data = None
        self.additional_data = {}
        self.combined_data = None
        self.returns = None
        self.entry_signals = None
        
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

    def apply_mmth_25_cross_module(self) -> pd.Series:
        """
        Apply the MMTH 25% cross module.
        Generates entry signals when MMTH crosses back above 25% after being below it.
        Returns a boolean series indicating entry signals.
        """
        if 'MMTH-200-day_close' not in self.combined_data.columns:
            raise ValueError("MMTH data not loaded")
            
        # Get configuration parameters
        threshold = ENTRY_CONFIG['mmth_25_cross']['threshold']
        confirmation_days = ENTRY_CONFIG['mmth_25_cross']['confirmation_days']
        
        # Get MMTH data
        mmth_data = self.combined_data['MMTH-200-day_close']
        
        # Create initial signal - True when crossing above threshold
        initial_signal = pd.Series(False, index=mmth_data.index)
        
        # Track when we're below threshold
        below_threshold = mmth_data < threshold
        
        # Find crossovers
        for i in range(1, len(mmth_data)):
            if below_threshold.iloc[i-1] and not below_threshold.iloc[i]:
                initial_signal.iloc[i] = True
        
        # Apply confirmation period if specified
        if confirmation_days > 0:
            final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        else:
            final_signal = initial_signal
        
        return final_signal

    def _apply_confirmation_period(self, initial_signal: pd.Series, confirmation_days: int) -> pd.Series:
        """
        Helper method to apply confirmation period to a signal.
        
        Args:
            initial_signal (pd.Series): Initial boolean signal series
            confirmation_days (int): Number of days required for confirmation
            
        Returns:
            pd.Series: Confirmed signal series
        """
        confirmed_signal = pd.Series(False, index=initial_signal.index)
        days_in_state = 0
        
        for i in range(len(initial_signal)):
            if initial_signal.iloc[i]:
                days_in_state += 1
                if days_in_state >= confirmation_days:
                    confirmed_signal.iloc[i] = True
            else:
                days_in_state = 0
        
        return confirmed_signal

    def plot_entry_signals(self, signal: pd.Series, title: str) -> None:
        """
        Plot SPX data with entry signals shown as green arrows.
        
        Args:
            signal (pd.Series): Boolean series indicating entry signals
            title (str): Title for the plot
        """
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), height_ratios=[2, 1])
        
        # Plot SPX data
        spx_data = self.combined_data['spx_close']
        ax1.plot(spx_data.index, spx_data, label='SPX', color='black')
        
        # Plot entry signals as green arrows
        entry_dates = spx_data.index[signal]
        entry_prices = spx_data[signal]
        
        # Calculate arrow positions (slightly below the price)
        arrow_y = entry_prices * 0.99  # 1% below the price
        
        # Plot arrows
        for date, price, arrow_pos in zip(entry_dates, entry_prices, arrow_y):
            ax1.annotate('', xy=(date, price), xytext=(date, arrow_pos),
                        arrowprops=dict(facecolor='green', shrink=0.05, width=2, headwidth=8))
        
        ax1.set_title(f'SPX with {title} Entry Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot MMTH data
        mmth_data = self.combined_data['MMTH-200-day_close']
        threshold = ENTRY_CONFIG['mmth_25_cross']['threshold']
        
        ax2.plot(mmth_data.index, mmth_data, label='MMTH %', color='blue')
        ax2.axhline(y=threshold, color='red', linestyle='--', 
                   label=f'Threshold ({threshold}%)')
        
        # Shade periods below threshold
        ax2.fill_between(mmth_data.index, 
                        mmth_data.min(),
                        mmth_data.max(),
                        where=mmth_data < threshold,
                        color='red', alpha=0.2, label='Below Threshold')
        
        ax2.set_ylabel('Percentage of Stocks Above 200-day MA')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def apply_mmtw_25_cross_module(self) -> pd.Series:
        """
        Apply the MMTW 25% cross module.
        Generates entry signals when MMTW crosses back above 25% after being below it.
        Returns a boolean series indicating entry signals.
        """
        if 'MMTW-20-day_close' not in self.combined_data.columns:
            raise ValueError("MMTW data not loaded")
            
        # Get configuration parameters
        threshold = ENTRY_CONFIG['mmtw_25_cross']['threshold']
        confirmation_days = ENTRY_CONFIG['mmtw_25_cross']['confirmation_days']
        
        # Get MMTW data
        mmtw_data = self.combined_data['MMTW-20-day_close']
        
        # Create initial signal - True when crossing above threshold
        initial_signal = pd.Series(False, index=mmtw_data.index)
        
        # Track when we're below threshold
        below_threshold = mmtw_data < threshold
        
        # Find crossovers
        for i in range(1, len(mmtw_data)):
            if below_threshold.iloc[i-1] and not below_threshold.iloc[i]:
                initial_signal.iloc[i] = True
        
        # Apply confirmation period if specified
        if confirmation_days > 0:
            final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        else:
            final_signal = initial_signal
        
        return final_signal

    def apply_mmfi_25_cross_module(self) -> pd.Series:
        """
        Apply the MMFI 25% cross module.
        Generates entry signals when MMFI crosses back above 25% after being below it.
        Returns a boolean series indicating entry signals.
        """
        if 'MMFI-50-day_close' not in self.combined_data.columns:
            raise ValueError("MMFI data not loaded")
            
        # Get configuration parameters
        threshold = ENTRY_CONFIG['mmfi_25_cross']['threshold']
        confirmation_days = ENTRY_CONFIG['mmfi_25_cross']['confirmation_days']
        
        # Get MMFI data
        mmfi_data = self.combined_data['MMFI-50-day_close']
        
        # Create initial signal - True when crossing above threshold
        initial_signal = pd.Series(False, index=mmfi_data.index)
        
        # Track when we're below threshold
        below_threshold = mmfi_data < threshold
        
        # Find crossovers
        for i in range(1, len(mmfi_data)):
            if below_threshold.iloc[i-1] and not below_threshold.iloc[i]:
                initial_signal.iloc[i] = True
        
        # Apply confirmation period if specified
        if confirmation_days > 0:
            final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        else:
            final_signal = initial_signal
        
        return final_signal

    def apply_r3tw_25_cross_module(self) -> pd.Series:
        """
        Apply the R3TW 25% cross module.
        Generates entry signals when R3TW crosses back above 25% after being below it.
        Returns a boolean series indicating entry signals.
        """
        if 'R3TW-20-day_close' not in self.combined_data.columns:
            raise ValueError("R3TW data not loaded")
            
        # Get configuration parameters
        threshold = ENTRY_CONFIG['r3tw_25_cross']['threshold']
        confirmation_days = ENTRY_CONFIG['r3tw_25_cross']['confirmation_days']
        
        # Get R3TW data
        r3tw_data = self.combined_data['R3TW-20-day_close']
        
        # Create initial signal - True when crossing above threshold
        initial_signal = pd.Series(False, index=r3tw_data.index)
        
        # Track when we're below threshold
        below_threshold = r3tw_data < threshold
        
        # Find crossovers
        for i in range(1, len(r3tw_data)):
            if below_threshold.iloc[i-1] and not below_threshold.iloc[i]:
                initial_signal.iloc[i] = True
        
        # Apply confirmation period if specified
        if confirmation_days > 0:
            final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        else:
            final_signal = initial_signal
        
        return final_signal

    def apply_r3tw_mmtw_cross_module(self) -> pd.Series:
        """
        Apply the R3TW/MMTW crossover module.
        Generates entry signals when:
        1. R3TW crosses below threshold (20%)
        2. After that, R3TW crosses back above MMTW
        
        Returns a boolean series indicating entry signals.
        """
        if 'R3TW-20-day_close' not in self.combined_data.columns or 'MMTW-20-day_close' not in self.combined_data.columns:
            raise ValueError("R3TW and MMTW data not loaded")
            
        # Get configuration parameters
        r3tw_threshold = ENTRY_CONFIG['r3tw_mmtw_cross']['r3tw_threshold']
        confirmation_days = ENTRY_CONFIG['r3tw_mmtw_cross']['confirmation_days']
        
        # Get data
        r3tw_data = self.combined_data['R3TW-20-day_close']
        mmtw_data = self.combined_data['MMTW-20-day_close']
        
        # Initialize signal series
        signal = pd.Series(False, index=r3tw_data.index)
        
        # Track when we're below threshold
        below_threshold = r3tw_data < r3tw_threshold
        
        # Track when R3TW is above MMTW
        r3tw_above_mmtw = r3tw_data > mmtw_data
        
        # Find entry signals
        for i in range(1, len(r3tw_data)):
            # Check if we've been below threshold and now R3TW crosses above MMTW
            if below_threshold.iloc[i-1] and r3tw_above_mmtw.iloc[i] and not r3tw_above_mmtw.iloc[i-1]:
                signal.iloc[i] = True
        
        # Apply confirmation period if specified
        if confirmation_days > 0:
            signal = self._apply_confirmation_period(signal, confirmation_days)
        
        return signal

    def plot_mmtw_25_signals(self, signal: pd.Series) -> None:
        """
        Plot SPX data with MMTW 25% cross entry signals shown as green arrows.
        
        Args:
            signal (pd.Series): Boolean series indicating entry signals
        """
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), height_ratios=[2, 1])
        
        # Plot SPX data
        spx_data = self.combined_data['spx_close']
        ax1.plot(spx_data.index, spx_data, label='SPX', color='black')
        
        # Plot entry signals as green arrows
        entry_dates = spx_data.index[signal]
        entry_prices = spx_data[signal]
        
        # Calculate arrow positions (slightly below the price)
        arrow_y = entry_prices * 0.99  # 1% below the price
        
        # Plot arrows
        for date, price, arrow_pos in zip(entry_dates, entry_prices, arrow_y):
            ax1.annotate('', xy=(date, price), xytext=(date, arrow_pos),
                        arrowprops=dict(facecolor='green', shrink=0.05, width=2, headwidth=8))
        
        ax1.set_title('SPX with MMTW 25% Cross Entry Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot MMTW data
        mmtw_data = self.combined_data['MMTW-20-day_close']
        threshold = ENTRY_CONFIG['mmtw_25_cross']['threshold']
        
        ax2.plot(mmtw_data.index, mmtw_data, label='MMTW %', color='blue')
        ax2.axhline(y=threshold, color='red', linestyle='--', 
                   label=f'Threshold ({threshold}%)')
        
        # Shade periods below threshold
        ax2.fill_between(mmtw_data.index, 
                        mmtw_data.min(),
                        mmtw_data.max(),
                        where=mmtw_data < threshold,
                        color='red', alpha=0.2, label='Below Threshold')
        
        ax2.set_ylabel('Percentage of Stocks Above 20-day MA')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def plot_mmfi_25_signals(self, signal: pd.Series) -> None:
        """
        Plot SPX data with MMFI 25% cross entry signals shown as green arrows.
        
        Args:
            signal (pd.Series): Boolean series indicating entry signals
        """
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), height_ratios=[2, 1])
        
        # Plot SPX data
        spx_data = self.combined_data['spx_close']
        ax1.plot(spx_data.index, spx_data, label='SPX', color='black')
        
        # Plot entry signals as green arrows
        entry_dates = spx_data.index[signal]
        entry_prices = spx_data[signal]
        
        # Calculate arrow positions (slightly below the price)
        arrow_y = entry_prices * 0.99  # 1% below the price
        
        # Plot arrows
        for date, price, arrow_pos in zip(entry_dates, entry_prices, arrow_y):
            ax1.annotate('', xy=(date, price), xytext=(date, arrow_pos),
                        arrowprops=dict(facecolor='green', shrink=0.05, width=2, headwidth=8))
        
        ax1.set_title('SPX with MMFI 25% Cross Entry Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot MMFI data
        mmfi_data = self.combined_data['MMFI-50-day_close']
        threshold = ENTRY_CONFIG['mmfi_25_cross']['threshold']
        
        ax2.plot(mmfi_data.index, mmfi_data, label='MMFI %', color='blue')
        ax2.axhline(y=threshold, color='red', linestyle='--', 
                   label=f'Threshold ({threshold}%)')
        
        # Shade periods below threshold
        ax2.fill_between(mmfi_data.index, 
                        mmfi_data.min(),
                        mmfi_data.max(),
                        where=mmfi_data < threshold,
                        color='red', alpha=0.2, label='Below Threshold')
        
        ax2.set_ylabel('Percentage of Stocks Above 50-day MA')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def plot_r3tw_25_signals(self, signal: pd.Series) -> None:
        """
        Plot SPX data with R3TW 25% cross entry signals shown as green arrows.
        
        Args:
            signal (pd.Series): Boolean series indicating entry signals
        """
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), height_ratios=[2, 1])
        
        # Plot SPX data
        spx_data = self.combined_data['spx_close']
        ax1.plot(spx_data.index, spx_data, label='SPX', color='black')
        
        # Plot entry signals as green arrows
        entry_dates = spx_data.index[signal]
        entry_prices = spx_data[signal]
        
        # Calculate arrow positions (slightly below the price)
        arrow_y = entry_prices * 0.99  # 1% below the price
        
        # Plot arrows
        for date, price, arrow_pos in zip(entry_dates, entry_prices, arrow_y):
            ax1.annotate('', xy=(date, price), xytext=(date, arrow_pos),
                        arrowprops=dict(facecolor='green', shrink=0.05, width=2, headwidth=8))
        
        ax1.set_title('SPX with R3TW 25% Cross Entry Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot R3TW data
        r3tw_data = self.combined_data['R3TW-20-day_close']
        threshold = ENTRY_CONFIG['r3tw_25_cross']['threshold']
        
        ax2.plot(r3tw_data.index, r3tw_data, label='R3TW %', color='blue')
        ax2.axhline(y=threshold, color='red', linestyle='--', 
                   label=f'Threshold ({threshold}%)')
        
        # Shade periods below threshold
        ax2.fill_between(r3tw_data.index, 
                        r3tw_data.min(),
                        r3tw_data.max(),
                        where=r3tw_data < threshold,
                        color='red', alpha=0.2, label='Below Threshold')
        
        ax2.set_ylabel('Percentage of Stocks Above 20-day MA')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def plot_r3tw_mmtw_signals(self, signal: pd.Series) -> None:
        """
        Plot SPX data with R3TW/MMTW crossover entry signals shown as green arrows.
        
        Args:
            signal (pd.Series): Boolean series indicating entry signals
        """
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), height_ratios=[2, 1])
        
        # Plot SPX data
        spx_data = self.combined_data['spx_close']
        ax1.plot(spx_data.index, spx_data, label='SPX', color='black')
        
        # Plot entry signals as green arrows
        entry_dates = spx_data.index[signal]
        entry_prices = spx_data[signal]
        
        # Calculate arrow positions (slightly below the price)
        arrow_y = entry_prices * 0.99  # 1% below the price
        
        # Plot arrows
        for date, price, arrow_pos in zip(entry_dates, entry_prices, arrow_y):
            ax1.annotate('', xy=(date, price), xytext=(date, arrow_pos),
                        arrowprops=dict(facecolor='green', shrink=0.05, width=2, headwidth=8))
        
        ax1.set_title('SPX with R3TW/MMTW Crossover Entry Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot R3TW and MMTW data
        r3tw_data = self.combined_data['R3TW-20-day_close']
        mmtw_data = self.combined_data['MMTW-20-day_close']
        threshold = ENTRY_CONFIG['r3tw_mmtw_cross']['r3tw_threshold']
        
        ax2.plot(r3tw_data.index, r3tw_data, label='R3TW %', color='blue')
        ax2.plot(mmtw_data.index, mmtw_data, label='MMTW %', color='red')
        ax2.axhline(y=threshold, color='black', linestyle='--', 
                   label=f'R3TW Threshold ({threshold}%)')
        
        # Shade periods below threshold
        ax2.fill_between(r3tw_data.index, 
                        r3tw_data.min(),
                        r3tw_data.max(),
                        where=r3tw_data < threshold,
                        color='red', alpha=0.2, label='Below Threshold')
        
        ax2.set_ylabel('Percentage of Stocks Above 20-day MA')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def apply_vix_bollinger_entry_module(self) -> pd.Series:
        """
        Apply the VIX Bollinger Band entry module.
        Returns a boolean series indicating entry signals.
        Generates entry signals when VIX %B goes above 1.
        
        %B = (Price - Lower Band)/(Upper Band - Lower Band)
        %B > 1: Price is above the upper band
        %B = 1: Price is at the upper band
        %B between 0.5 and 1: Price is between middle and upper band
        %B = 0.5: Price is at the middle band
        %B between 0 and 0.5: Price is between lower and middle band
        %B = 0: Price is at the lower band
        %B < 0: Price is below the lower band
        """
        if 'VIX_close' not in self.combined_data.columns:
            raise ValueError("VIX data not loaded")
            
        # Get configuration parameters
        lookback = MODULE_CONFIG['vix_bollinger_entry']['lookback_period']
        std_dev = MODULE_CONFIG['vix_bollinger_entry']['std_dev']
        threshold = MODULE_CONFIG['vix_bollinger_entry']['percent_b_threshold']
        
        # Get VIX data
        vix_data = self.combined_data['VIX_close']
        
        # Calculate Bollinger Bands
        rolling_mean = vix_data.rolling(window=lookback).mean()
        rolling_std = vix_data.rolling(window=lookback).std()
        
        # Calculate bands
        upper_band = rolling_mean + (rolling_std * std_dev)
        lower_band = rolling_mean - (rolling_std * std_dev)
        
        # Calculate %B
        percent_b = (vix_data - lower_band) / (upper_band - lower_band)
        
        # Generate entry signals when %B goes above threshold
        entry_signal = percent_b > threshold
        
        return entry_signal

    def plot_vix_bollinger_entry_signals(self, entry_signal: pd.Series) -> None:
        """
        Plot SPX data with VIX Bollinger Band entry signals.
        Shows green up arrows when VIX %B goes above 1.
        
        Args:
            entry_signal (pd.Series): Boolean series indicating entry signals
        """
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 10), height_ratios=[2, 1, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Plot entry signals as green up arrows
        entry_dates = self.combined_data.index[entry_signal]
        entry_prices = self.combined_data['spx_close'][entry_signal]
        
        # Plot arrows slightly below the price points
        arrow_y_positions = entry_prices * 0.99  # 1% below the price
        
        ax1.scatter(entry_dates, arrow_y_positions,
                   marker='^',  # Upward pointing triangle
                   color='green',
                   alpha=0.5,
                   s=50,  # Size of the arrows
                   label='Entry Signal')
        
        ax1.set_title('SPX with VIX Bollinger Band Entry Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Calculate VIX Bollinger Bands and %B
        lookback = MODULE_CONFIG['vix_bollinger_entry']['lookback_period']
        std_dev = MODULE_CONFIG['vix_bollinger_entry']['std_dev']
        threshold = MODULE_CONFIG['vix_bollinger_entry']['percent_b_threshold']
        
        vix_data = self.combined_data['VIX_close']
        rolling_mean = vix_data.rolling(window=lookback).mean()
        rolling_std = vix_data.rolling(window=lookback).std()
        
        # Calculate bands
        upper_band = rolling_mean + (rolling_std * std_dev)
        lower_band = rolling_mean - (rolling_std * std_dev)
        
        # Calculate %B
        percent_b = (vix_data - lower_band) / (upper_band - lower_band)
        
        # Plot VIX data and bands
        ax2.plot(vix_data.index, vix_data, label='VIX', color='blue')
        ax2.plot(rolling_mean.index, rolling_mean, 
                label=f'{lookback}-day MA', color='red', linestyle='--')
        ax2.plot(upper_band.index, upper_band, 
                label=f'+{std_dev}σ Band', color='green', linestyle=':')
        ax2.plot(lower_band.index, lower_band, 
                label=f'-{std_dev}σ Band', color='green', linestyle=':')
        
        ax2.set_ylabel('VIX')
        ax2.legend()
        ax2.grid(True)
        
        # Plot %B indicator
        ax3.plot(percent_b.index, percent_b, label='%B', color='purple')
        
        # Plot %B threshold and reference lines
        ax3.axhline(y=threshold, 
                   color='red', linestyle='--', 
                   label=f'Entry Threshold ({threshold})')
        ax3.axhline(y=0, color='black', linestyle=':', alpha=0.3, label='%B = 0')
        ax3.axhline(y=0.5, color='black', linestyle=':', alpha=0.3, label='%B = 0.5')
        ax3.axhline(y=1, color='black', linestyle=':', alpha=0.3, label='%B = 1')
        
        ax3.set_ylabel('%B')
        ax3.set_ylim(-0.5, 1.5)  # Set y-axis limits to show the full range of %B
        ax3.legend()
        ax3.grid(True)
        
        plt.tight_layout()
        plt.show()

def main():
    # Initialize research
    research = EntryResearch()
    
    # Determine which data files we need based on active modules
    required_files = ['SPX.csv']
    
    # Add VIX if enabled
    if MODULE_CONFIG['vix_bollinger_entry']['enabled']:
        required_files.append('VIX.csv')
    
    # Add percentage of stocks data if enabled
    if any(MODULE_CONFIG[module]['enabled'] for module in ['mmth_25_cross', 'mmtw_25_cross', 'mmfi_25_cross', 'r3tw_25_cross', 'r3tw_mmtw_cross']):
        required_files.extend(['MMTW-20-day.csv', 'MMFI-50-day.csv', 'MMTH-200-day.csv', 'R3TW-20-day.csv'])
    
    # Load all required data
    logging.info("Loading required data files: %s", required_files)
    research.load_data(required_files)
    
    # Run VIX Bollinger Band entry module
    if MODULE_CONFIG['vix_bollinger_entry']['enabled']:
        logging.info("Running VIX Bollinger Band entry module")
        entry_signal = research.apply_vix_bollinger_entry_module()
        research.plot_vix_bollinger_entry_signals(entry_signal)
    
    # Run MMTH 25% cross module
    if ENTRY_CONFIG['mmth_25_cross']['enabled']:
        logging.info("Running MMTH 25% cross module")
        signal = research.apply_mmth_25_cross_module()
        research.plot_entry_signals(signal, "MMTH 25% Cross")
    
    # Run MMTW 25% cross module
    if ENTRY_CONFIG['mmtw_25_cross']['enabled']:
        logging.info("Running MMTW 25% cross module")
        signal = research.apply_mmtw_25_cross_module()
        research.plot_mmtw_25_signals(signal)
    
    # Run MMFI 25% cross module
    if ENTRY_CONFIG['mmfi_25_cross']['enabled']:
        logging.info("Running MMFI 25% cross module")
        signal = research.apply_mmfi_25_cross_module()
        research.plot_mmfi_25_signals(signal)
    
    # Run R3TW 25% cross module
    if ENTRY_CONFIG['r3tw_25_cross']['enabled']:
        logging.info("Running R3TW 25% cross module")
        signal = research.apply_r3tw_25_cross_module()
        research.plot_r3tw_25_signals(signal)
    
    # Run R3TW/MMTW crossover module
    if ENTRY_CONFIG['r3tw_mmtw_cross']['enabled']:
        logging.info("Running R3TW/MMTW crossover module")
        signal = research.apply_r3tw_mmtw_cross_module()
        research.plot_r3tw_mmtw_signals(signal)
    
    if not any(config['enabled'] for config in ENTRY_CONFIG.values()):
        logging.warning("No modules are enabled. Please enable at least one module in ENTRY_CONFIG.")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    main()
