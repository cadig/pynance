import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging
from typing import Dict, List, Tuple

# Configuration for which modules to run
MODULE_CONFIG = {
    'mmth_cross_exit': {
        'enabled': False,
        'threshold': 70,  # Exit when crossing below this threshold
        'period': 200  # 200-day moving average
    },
    'mmfi_cross_exit': {
        'enabled': False,
        'threshold': 70,  # Exit when crossing below this threshold
        'period': 50  # 50-day moving average
    },
    'mmtw_cross_exit': {
        'enabled': False,
        'threshold': 70,  # Exit when crossing below this threshold
        'period': 20  # 20-day moving average
    },
    'mmth_gap_exit': {
        'enabled': False,
        'gap_threshold': 0.05,  # Exit when gap down is at least 5%
        'period': 200  # 200-day moving average
    },
    'mmfi_gap_exit': {
        'enabled': False,
        'gap_threshold': 0.10,  # Exit when gap down is at least 5%
        'period': 50  # 50-day moving average
    },
    'mmtw_gap_exit': {
        'enabled': False,
        'gap_threshold': 0.10,  # Exit when gap down is at least 5%
        'period': 20  # 20-day moving average
    },
    'vix_bollinger_exit': {
        'enabled': True,
        'lookback_period': 20,  # Number of days for Bollinger Band calculation
        'std_dev': 2.0,  # Number of standard deviations for bands
        'percent_b_threshold': 0  # Exit when %B goes below this threshold
    }
}

class ExitResearch:
    def __init__(self):
        self.data_dir = Path(__file__).parent / 'data'
        self.spx_data = None
        self.additional_data = {}
        self.combined_data = None
        
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

    def apply_mmth_exit_module(self) -> pd.Series:
        """
        Apply the MMTH exit module.
        Returns a boolean series indicating exit points when crossing below threshold
        after having crossed above it.
        """
        if 'MMTH-200-day_close' not in self.combined_data.columns:
            raise ValueError("MMTH data not loaded")
            
        # Get configuration parameters
        threshold = MODULE_CONFIG['mmth_cross_exit']['threshold']
        
        # Get MMTH data
        mmth_data = self.combined_data['MMTH-200-day_close']
        
        # Initialize exit signal series
        exit_signal = pd.Series(False, index=mmth_data.index)
        
        # Track if we're in an active signal (crossed above threshold)
        in_signal = False
        
        # Iterate through the data to find exit points
        for i in range(1, len(mmth_data)):
            if not in_signal and mmth_data.iloc[i-1] < threshold and mmth_data.iloc[i] >= threshold:
                # Crossed above threshold
                in_signal = True
            elif in_signal and mmth_data.iloc[i-1] >= threshold and mmth_data.iloc[i] < threshold:
                # Crossed below threshold - exit point
                exit_signal.iloc[i] = True
                in_signal = False
        
        return exit_signal

    def apply_mmfi_exit_module(self) -> pd.Series:
        """
        Apply the MMFI exit module.
        Returns a boolean series indicating exit points when crossing below threshold
        after having crossed above it.
        """
        if 'MMFI-50-day_close' not in self.combined_data.columns:
            raise ValueError("MMFI data not loaded")
            
        # Get configuration parameters
        threshold = MODULE_CONFIG['mmfi_cross_exit']['threshold']
        
        # Get MMFI data
        mmfi_data = self.combined_data['MMFI-50-day_close']
        
        # Initialize exit signal series
        exit_signal = pd.Series(False, index=mmfi_data.index)
        
        # Track if we're in an active signal (crossed above threshold)
        in_signal = False
        
        # Iterate through the data to find exit points
        for i in range(1, len(mmfi_data)):
            if not in_signal and mmfi_data.iloc[i-1] < threshold and mmfi_data.iloc[i] >= threshold:
                # Crossed above threshold
                in_signal = True
            elif in_signal and mmfi_data.iloc[i-1] >= threshold and mmfi_data.iloc[i] < threshold:
                # Crossed below threshold - exit point
                exit_signal.iloc[i] = True
                in_signal = False
        
        return exit_signal

    def apply_mmtw_exit_module(self) -> pd.Series:
        """
        Apply the MMTW exit module.
        Returns a boolean series indicating exit points when crossing below threshold
        after having crossed above it.
        """
        if 'MMTW-20-day_close' not in self.combined_data.columns:
            raise ValueError("MMTW data not loaded")
            
        # Get configuration parameters
        threshold = MODULE_CONFIG['mmtw_cross_exit']['threshold']
        
        # Get MMTW data
        mmtw_data = self.combined_data['MMTW-20-day_close']
        
        # Initialize exit signal series
        exit_signal = pd.Series(False, index=mmtw_data.index)
        
        # Track if we're in an active signal (crossed above threshold)
        in_signal = False
        
        # Iterate through the data to find exit points
        for i in range(1, len(mmtw_data)):
            if not in_signal and mmtw_data.iloc[i-1] < threshold and mmtw_data.iloc[i] >= threshold:
                # Crossed above threshold
                in_signal = True
            elif in_signal and mmtw_data.iloc[i-1] >= threshold and mmtw_data.iloc[i] < threshold:
                # Crossed below threshold - exit point
                exit_signal.iloc[i] = True
                in_signal = False
        
        return exit_signal

    def apply_mmth_gap_exit_module(self) -> pd.Series:
        """
        Apply the MMTH gap down exit module.
        Returns a boolean series indicating exit signals when there is a gap down of at least 5%.
        """
        if 'MMTH-200-day_close' not in self.combined_data.columns:
            raise ValueError("MMTH data not loaded")
            
        # Get configuration parameters
        gap_threshold = MODULE_CONFIG['mmth_gap_exit']['gap_threshold']
        
        # Get MMTH data
        mmth_data = self.combined_data['MMTH-200-day_close']
        
        # Calculate gap down
        gap_down = (mmth_data.shift(1) - mmth_data) / mmth_data.shift(1)
        
        # Create exit signal - True when gap down is at least threshold
        exit_signal = gap_down >= gap_threshold
        
        return exit_signal

    def apply_mmfi_gap_exit_module(self) -> pd.Series:
        """
        Apply the MMFI gap down exit module.
        Returns a boolean series indicating exit signals when there is a gap down of at least 5%.
        """
        if 'MMFI-50-day_close' not in self.combined_data.columns:
            raise ValueError("MMFI data not loaded")
            
        # Get configuration parameters
        gap_threshold = MODULE_CONFIG['mmfi_gap_exit']['gap_threshold']
        
        # Get MMFI data
        mmfi_data = self.combined_data['MMFI-50-day_close']
        
        # Calculate gap down
        gap_down = (mmfi_data.shift(1) - mmfi_data) / mmfi_data.shift(1)
        
        # Create exit signal - True when gap down is at least threshold
        exit_signal = gap_down >= gap_threshold
        
        return exit_signal

    def apply_mmtw_gap_exit_module(self) -> pd.Series:
        """
        Apply the MMTW gap down exit module.
        Returns a boolean series indicating exit signals when there is a gap down of at least 5%.
        """
        if 'MMTW-20-day_close' not in self.combined_data.columns:
            raise ValueError("MMTW data not loaded")
            
        # Get configuration parameters
        gap_threshold = MODULE_CONFIG['mmtw_gap_exit']['gap_threshold']
        
        # Get MMTW data
        mmtw_data = self.combined_data['MMTW-20-day_close']
        
        # Calculate gap down
        gap_down = (mmtw_data.shift(1) - mmtw_data) / mmtw_data.shift(1)
        
        # Create exit signal - True when gap down is at least threshold
        exit_signal = gap_down >= gap_threshold
        
        return exit_signal

    def apply_vix_bollinger_exit_module(self) -> pd.Series:
        """
        Apply the VIX Bollinger Band exit module using %B indicator.
        Returns a boolean series indicating exit signals.
        Generates exit signal when %B goes below 0.
        """
        if 'VIX_close' not in self.combined_data.columns:
            raise ValueError("VIX data not loaded")
            
        # Get configuration parameters
        lookback = MODULE_CONFIG['vix_bollinger_exit']['lookback_period']
        std_dev = MODULE_CONFIG['vix_bollinger_exit']['std_dev']
        threshold = MODULE_CONFIG['vix_bollinger_exit']['percent_b_threshold']
        
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
        
        # Create exit signal - True when %B is below threshold
        exit_signal = percent_b < threshold
        
        return exit_signal

    def plot_mmth_exit_signals(self, exit_signal: pd.Series) -> None:
        """
        Plot SPX data with MMTH exit signals.
        
        Args:
            exit_signal (pd.Series): Boolean series indicating exit points
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Plot exit signals as red triangles
        exit_dates = self.combined_data.index[exit_signal]
        exit_prices = self.combined_data['spx_close'][exit_signal]
        arrow_y_positions = exit_prices * 1.01  # 1% above the price
        
        ax1.scatter(exit_dates, arrow_y_positions,
                   marker='v',  # Downward pointing triangle
                   color='red',
                   alpha=0.5,
                   s=50,  # Size of the arrows
                   label='Exit Signal')
        
        ax1.set_title('SPX with MMTH Exit Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot MMTH data
        threshold = MODULE_CONFIG['mmth_cross_exit']['threshold']
        mmth_data = self.combined_data['MMTH-200-day_close']
        
        ax2.plot(mmth_data.index, mmth_data, label='MMTH', color='blue')
        ax2.axhline(y=threshold, color='red', linestyle='--', 
                   label=f'Threshold ({threshold}%)')
        
        ax2.set_ylabel('Percentage of Stocks Above MA')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def plot_mmfi_exit_signals(self, exit_signal: pd.Series) -> None:
        """
        Plot SPX data with MMFI exit signals.
        
        Args:
            exit_signal (pd.Series): Boolean series indicating exit points
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Plot exit signals as red triangles
        exit_dates = self.combined_data.index[exit_signal]
        exit_prices = self.combined_data['spx_close'][exit_signal]
        arrow_y_positions = exit_prices * 1.01  # 1% above the price
        
        ax1.scatter(exit_dates, arrow_y_positions,
                   marker='v',  # Downward pointing triangle
                   color='red',
                   alpha=0.5,
                   s=50,  # Size of the arrows
                   label='Exit Signal')
        
        ax1.set_title('SPX with MMFI Exit Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot MMFI data
        threshold = MODULE_CONFIG['mmfi_cross_exit']['threshold']
        mmfi_data = self.combined_data['MMFI-50-day_close']
        
        ax2.plot(mmfi_data.index, mmfi_data, label='MMFI', color='blue')
        ax2.axhline(y=threshold, color='red', linestyle='--', 
                   label=f'Threshold ({threshold}%)')
        
        ax2.set_ylabel('Percentage of Stocks Above MA')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def plot_mmtw_exit_signals(self, exit_signal: pd.Series) -> None:
        """
        Plot SPX data with MMTW exit signals.
        
        Args:
            exit_signal (pd.Series): Boolean series indicating exit points
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Plot exit signals as red triangles
        exit_dates = self.combined_data.index[exit_signal]
        exit_prices = self.combined_data['spx_close'][exit_signal]
        arrow_y_positions = exit_prices * 1.01  # 1% above the price
        
        ax1.scatter(exit_dates, arrow_y_positions,
                   marker='v',  # Downward pointing triangle
                   color='red',
                   alpha=0.5,
                   s=50,  # Size of the arrows
                   label='Exit Signal')
        
        ax1.set_title('SPX with MMTW Exit Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot MMTW data
        threshold = MODULE_CONFIG['mmtw_cross_exit']['threshold']
        mmtw_data = self.combined_data['MMTW-20-day_close']
        
        ax2.plot(mmtw_data.index, mmtw_data, label='MMTW', color='blue')
        ax2.axhline(y=threshold, color='red', linestyle='--', 
                   label=f'Threshold ({threshold}%)')
        
        ax2.set_ylabel('Percentage of Stocks Above MA')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def plot_mmth_gap_exit_signals(self, exit_signal: pd.Series) -> None:
        """
        Plot SPX data with MMTH gap down exit signals.
        
        Args:
            exit_signal (pd.Series): Boolean series indicating exit signals
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Plot red arrows pointing down at exit signals
        exit_dates = self.combined_data.index[exit_signal]
        exit_prices = self.combined_data['spx_close'][exit_signal]
        
        # Plot arrows slightly above the price points
        arrow_y_positions = exit_prices * 1.01  # 1% above the price
        
        ax1.scatter(exit_dates, arrow_y_positions,
                   marker='v',  # Downward pointing triangle
                   color='red',
                   alpha=0.5,
                   s=50,  # Size of the arrows
                   label='MMTH Gap Down Exit')
        
        ax1.set_title('SPX with MMTH Gap Down Exit Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot MMTH data
        gap_threshold = MODULE_CONFIG['mmth_gap_exit']['gap_threshold']
        mmth_data = self.combined_data['MMTH-200-day_close']
        
        # Calculate gap down
        gap_down = (mmth_data.shift(1) - mmth_data) / mmth_data.shift(1)
        
        ax2.plot(mmth_data.index, mmth_data, label='MMTH', color='blue')
        ax2.axhline(y=gap_threshold * 100, color='red', linestyle='--', 
                   label=f'Gap Threshold ({gap_threshold*100:.0f}%)')
        
        ax2.set_ylabel('Percentage of Stocks Above MA')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def plot_mmfi_gap_exit_signals(self, exit_signal: pd.Series) -> None:
        """
        Plot SPX data with MMFI gap down exit signals.
        
        Args:
            exit_signal (pd.Series): Boolean series indicating exit signals
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Plot red arrows pointing down at exit signals
        exit_dates = self.combined_data.index[exit_signal]
        exit_prices = self.combined_data['spx_close'][exit_signal]
        
        # Plot arrows slightly above the price points
        arrow_y_positions = exit_prices * 1.01  # 1% above the price
        
        ax1.scatter(exit_dates, arrow_y_positions,
                   marker='v',  # Downward pointing triangle
                   color='red',
                   alpha=0.5,
                   s=50,  # Size of the arrows
                   label='MMFI Gap Down Exit')
        
        ax1.set_title('SPX with MMFI Gap Down Exit Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot MMFI data
        gap_threshold = MODULE_CONFIG['mmfi_gap_exit']['gap_threshold']
        mmfi_data = self.combined_data['MMFI-50-day_close']
        
        # Calculate gap down
        gap_down = (mmfi_data.shift(1) - mmfi_data) / mmfi_data.shift(1)
        
        ax2.plot(mmfi_data.index, mmfi_data, label='MMFI', color='blue')
        ax2.axhline(y=gap_threshold * 100, color='red', linestyle='--', 
                   label=f'Gap Threshold ({gap_threshold*100:.0f}%)')
        
        ax2.set_ylabel('Percentage of Stocks Above MA')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def plot_mmtw_gap_exit_signals(self, exit_signal: pd.Series) -> None:
        """
        Plot SPX data with MMTW gap down exit signals.
        
        Args:
            exit_signal (pd.Series): Boolean series indicating exit signals
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Plot red arrows pointing down at exit signals
        exit_dates = self.combined_data.index[exit_signal]
        exit_prices = self.combined_data['spx_close'][exit_signal]
        
        # Plot arrows slightly above the price points
        arrow_y_positions = exit_prices * 1.01  # 1% above the price
        
        ax1.scatter(exit_dates, arrow_y_positions,
                   marker='v',  # Downward pointing triangle
                   color='red',
                   alpha=0.5,
                   s=50,  # Size of the arrows
                   label='MMTW Gap Down Exit')
        
        ax1.set_title('SPX with MMTW Gap Down Exit Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot MMTW data
        gap_threshold = MODULE_CONFIG['mmtw_gap_exit']['gap_threshold']
        mmtw_data = self.combined_data['MMTW-20-day_close']
        
        # Calculate gap down
        gap_down = (mmtw_data.shift(1) - mmtw_data) / mmtw_data.shift(1)
        
        ax2.plot(mmtw_data.index, mmtw_data, label='MMTW', color='blue')
        ax2.axhline(y=gap_threshold * 100, color='red', linestyle='--', 
                   label=f'Gap Threshold ({gap_threshold*100:.0f}%)')
        
        ax2.set_ylabel('Percentage of Stocks Above MA')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def plot_vix_bollinger_exit_signals(self, exit_signal: pd.Series) -> None:
        """
        Plot SPX data with VIX Bollinger Band exit signals.
        Shows red down arrows when VIX %B goes below 0.
        
        Args:
            exit_signal (pd.Series): Boolean series indicating exit signals
        """
        # Create figure with two subplots instead of three
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Plot exit signals as red down arrows
        exit_dates = self.combined_data.index[exit_signal]
        exit_prices = self.combined_data['spx_close'][exit_signal]
        
        # Plot arrows slightly above the price points
        arrow_y_positions = exit_prices * 1.01  # 1% above the price
        
        ax1.scatter(exit_dates, arrow_y_positions,
                   marker='v',  # Downward pointing triangle
                   color='red',
                   alpha=0.5,
                   s=50,  # Size of the arrows
                   label='Exit Signal')
        
        ax1.set_title('SPX with VIX Bollinger Band Exit Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Calculate VIX Bollinger Bands and %B
        lookback = MODULE_CONFIG['vix_bollinger_exit']['lookback_period']
        std_dev = MODULE_CONFIG['vix_bollinger_exit']['std_dev']
        threshold = MODULE_CONFIG['vix_bollinger_exit']['percent_b_threshold']
        
        vix_data = self.combined_data['VIX_close']
        rolling_mean = vix_data.rolling(window=lookback).mean()
        rolling_std = vix_data.rolling(window=lookback).std()
        
        # Calculate bands
        upper_band = rolling_mean + (rolling_std * std_dev)
        lower_band = rolling_mean - (rolling_std * std_dev)
        
        # Calculate %B
        percent_b = (vix_data - lower_band) / (upper_band - lower_band)
        
        # Plot %B indicator
        ax2.plot(percent_b.index, percent_b, label='%B', color='purple')
        
        # Plot %B threshold and reference lines
        ax2.axhline(y=threshold, 
                   color='red', linestyle='--', 
                   label=f'Exit Threshold ({threshold})')
        ax2.axhline(y=0, color='black', linestyle=':', alpha=0.3, label='%B = 0')
        ax2.axhline(y=0.5, color='black', linestyle=':', alpha=0.3, label='%B = 0.5')
        ax2.axhline(y=1, color='black', linestyle=':', alpha=0.3, label='%B = 1')
        
        ax2.set_ylabel('%B')
        ax2.set_ylim(-0.5, 1.5)  # Set y-axis limits to show the full range of %B
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

def main():
    # Initialize research
    research = ExitResearch()
    
    # Determine which data files we need based on active modules
    required_files = ['SPX.csv']
    
    # Add VIX if enabled
    if MODULE_CONFIG['vix_bollinger_exit']['enabled']:
        required_files.append('VIX.csv')
    
    # Add percentage of stocks data if enabled
    if any(MODULE_CONFIG[module]['enabled'] for module in ['mmth_cross_exit', 'mmfi_cross_exit', 'mmtw_cross_exit',
                                                         'mmth_gap_exit', 'mmfi_gap_exit', 'mmtw_gap_exit']):
        required_files.extend(['MMTW-20-day.csv', 'MMFI-50-day.csv', 'MMTH-200-day.csv'])
    
    # Load all required data
    logging.info("Loading required data files: %s", required_files)
    research.load_data(required_files)
    
    # Run VIX Bollinger Band exit module
    if MODULE_CONFIG['vix_bollinger_exit']['enabled']:
        logging.info("Running VIX Bollinger Band exit module")
        exit_signal = research.apply_vix_bollinger_exit_module()
        research.plot_vix_bollinger_exit_signals(exit_signal)
    
    # Run MMTH cross exit module
    if MODULE_CONFIG['mmth_cross_exit']['enabled']:
        logging.info("Running MMTH cross exit module")
        exit_signal = research.apply_mmth_exit_module()
        research.plot_mmth_exit_signals(exit_signal)
    
    # Run MMFI cross exit module
    if MODULE_CONFIG['mmfi_cross_exit']['enabled']:
        logging.info("Running MMFI cross exit module")
        exit_signal = research.apply_mmfi_exit_module()
        research.plot_mmfi_exit_signals(exit_signal)
    
    # Run MMTW cross exit module
    if MODULE_CONFIG['mmtw_cross_exit']['enabled']:
        logging.info("Running MMTW cross exit module")
        exit_signal = research.apply_mmtw_exit_module()
        research.plot_mmtw_exit_signals(exit_signal)
    
    # Run MMTH gap exit module
    if MODULE_CONFIG['mmth_gap_exit']['enabled']:
        logging.info("Running MMTH gap exit module")
        exit_signal = research.apply_mmth_gap_exit_module()
        research.plot_mmth_gap_exit_signals(exit_signal)
    
    # Run MMFI gap exit module
    if MODULE_CONFIG['mmfi_gap_exit']['enabled']:
        logging.info("Running MMFI gap exit module")
        exit_signal = research.apply_mmfi_gap_exit_module()
        research.plot_mmfi_gap_exit_signals(exit_signal)
    
    # Run MMTW gap exit module
    if MODULE_CONFIG['mmtw_gap_exit']['enabled']:
        logging.info("Running MMTW gap exit module")
        exit_signal = research.apply_mmtw_gap_exit_module()
        research.plot_mmtw_gap_exit_signals(exit_signal)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    main()

