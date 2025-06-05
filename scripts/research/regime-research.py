import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging
from typing import Dict, List, Tuple
import json

# Configuration for which modules to run
MODULE_CONFIG = {
    'adrt': {
        'enabled': False,
        'lookback_period': 50,  # Number of days to smooth ADRT data
        'threshold': 1.2,  # Threshold for risk-off signal (ratio < 1.0 means more declining than advancing)
        'days_crossed_threshold': 3  # Number of days the indicator must stay on one side of threshold to change signal
    },
    'adrt_zscore': {
        'enabled': False,
        'lookback_period': 252 * 3,  # Number of days to use for z-score calculation (1 year)
        'threshold': 1.6,  # Z-score threshold for risk-off signal (goes risk-off when above this)
        'days_crossed_threshold': 0,  # Number of days the z-score must stay above threshold
        'smoothing_period': 50  # Number of days to smooth the ADRT data before z-score calculation
    },
    'spx_ma_crossover': {
        'enabled': False,
        'ma_periods': [80],  # Moving average periods to use
        'signals': {
            'price_under_ma': {
                'enabled': True,
                'ma_period': 80,  # MA period to check price against
                'confirmation_days': 4
            },
            'ma_below_ma': {
                'enabled': False,
                'fast_ma_period': 10,  # Faster MA period
                'slow_ma_period': 50,  # Slower MA period
                'confirmation_days': 3
            }
        }
    },
    'pct_stocks_vs_ma': {
        'enabled': False,
        'threshold': 35,  # Risk-off when all enabled indicators are below this threshold
        'added_together': False,  # If True, average the enabled indicators; if False, require all to be below threshold
        'confirmation_days': 2,  # Number of days the indicator must stay below threshold to trigger risk-off
        'indicators': {
            'MMTW': {
                'enabled': False,
                'period': 20
            },
            'MMFI': {
                'enabled': False,
                'period': 50
            },
            'MMTH': {
                'enabled': True,
                'period': 200
            }
        }
    },
    'nasdaq_52w_netnew_high_low': {
        'enabled': False,
        'lookback_period': 252,  # Number of days to use for z-score calculation
        'confirmation_days': 0  # Number of days the indicator must stay below threshold
    },
    'nyse_cumulative_ad': {
        'enabled': False,
        'smoothing_period': 70,  # Number of days to smooth the AD line
        'ma_period': 252,  # 50-week MA (252 trading days)
        'confirmation_days': 0  # Number of days the indicator must stay below MA to trigger risk-off
    },
    # Note, this one is currently the primary regime signal used in combined-research.py
    'nyse_cumulative_ad_zscore': {
        'enabled': False,
        'lookback_period': 252,  # Number of days to use for z-score calculation
        'smoothing_period': 50,  # Number of days to smooth the cumulative AD line
        'threshold': -1.0,  # Risk-off when z-score goes below this threshold
        'confirmation_days': 0  # Number of days the z-score must stay below threshold
    },
    'nasdaq_cumulative_ad_zscore': {
        'enabled': False,
        'lookback_period': 252,  # Number of days to use for z-score calculation
        'smoothing_period': 10,  # Number of days to smooth the cumulative AD line
        'threshold': -1.0,  # Risk-off when z-score goes below this threshold
        'confirmation_days': 0  # Number of days the z-score must stay below threshold
    },
    # The S&P 500 tends to peak 7.3 months  (average) or 2.6 months (median) after a 2s10s yield curve inversion: bofa 
    'two_ten_inversion': {
        'enabled': False,
        'confirmation_days': 0  # Number of days the spread must stay below 0 to trigger risk-off
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
        }
    },
    'all_mm_signals_below_50': {
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
        }
    },
    'spx_mmfi_regime': {
        'enabled': False,
        'spx_ma_period': 50,  # 50-day moving average for SPX
        'mmfi_threshold': 50,  # Threshold for MMFI
        'confirmation_days': 0  # Number of days indicators must stay below threshold
    }
}

class SPXResearch:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.spx_data = None
        self.additional_data = {}
        self.combined_data = None
        self.signals = None
        
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
        
        # Calculate moving averages
        self.calculate_moving_averages()

    def calculate_moving_averages(self) -> None:
        """Calculate and store moving averages for all indicators."""
        # ADRT smoothed series
        if 'ADRT_close' in self.combined_data.columns:
            lookback = MODULE_CONFIG['adrt']['lookback_period']
            self.combined_data['ADRT_smoothed'] = self.combined_data['ADRT_close'].rolling(window=lookback).mean()

    def apply_adrt_module(self) -> pd.Series:
        """
        Apply the ADRT-based risk-off signal module using smoothed ratio.
        Returns a boolean series indicating risk-off periods.
        The signal only changes if the indicator stays on one side of the threshold
        for the specified number of days.
        """
        if 'ADRT_close' not in self.combined_data.columns:
            raise ValueError("ADRT data not loaded")
            
        # Get combined data with full time series
        combined_data = self.combined_data
        adrt_smoothed = combined_data['ADRT_smoothed']
        threshold = MODULE_CONFIG['adrt']['threshold']
        days_required = MODULE_CONFIG['adrt']['days_crossed_threshold']
        
        # Create initial signal based on threshold
        initial_signal = adrt_smoothed < threshold
        
        # Initialize the final signal series
        final_signal = pd.Series(index=adrt_smoothed.index, dtype=bool)
        
        # Start with the initial signal state
        current_signal = initial_signal.iloc[0]
        days_in_current_state = 0
        
        # Iterate through the data to implement confirmation period
        for i in range(len(adrt_smoothed)):
            if initial_signal.iloc[i] != current_signal:
                days_in_current_state += 1
                if days_in_current_state >= days_required:
                    current_signal = initial_signal.iloc[i]
                    days_in_current_state = 0
            else:
                days_in_current_state = 0
            
            final_signal.iloc[i] = current_signal
        
        return final_signal

    def plot_signals(self, signal: pd.Series, title: str, data_column: str, threshold: float = None, ma_column: str = None) -> None:
        """
        Plot SPX data with risk-off signals and additional data.
        
        Args:
            signal (pd.Series): Boolean series indicating risk-off periods
            title (str): Title for the plot
            data_column (str): Column name for the indicator data
            threshold (float): Threshold value for the indicator (if using fixed threshold)
            ma_column (str): Column name for the moving average (if using MA crossover)
        """
        # Get combined data with full time series
        combined_data = self.combined_data
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(combined_data.index, combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Shade risk-off periods
        risk_off_periods = combined_data.index[signal]
        ax1.fill_between(combined_data.index, 
                        combined_data['spx_close'].min(),
                        combined_data['spx_close'].max(),
                        where=signal,
                        color='red', alpha=0.2, label='Risk-Off Period')
        
        ax1.set_title(f'SPX with {title}')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot indicator data
        ax2.plot(combined_data.index, 
                combined_data[data_column],
                label=title.split()[0], color='blue')
        
        if threshold is not None:
            ax2.axhline(y=threshold, color='red', linestyle='--', 
                       label=f'{threshold}% Threshold')
        elif ma_column is not None:
            ax2.plot(combined_data.index,
                    combined_data[ma_column],
                    label=f'{title.split()[0]} MA', color='red', linestyle='--')
            
        ax2.set_ylabel('Percentage')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def apply_spx_ma_crossover_module(self) -> pd.Series:
        """
        Apply the SPX moving average crossover module.
        Returns a boolean series indicating risk-on periods based on configured MA signals.
        Each signal requires a confirmation period before becoming active.
        
        The module supports two types of signals:
        1. Price under MA: Risk-off when price is below specified MA
        2. MA below MA: Risk-off when faster MA is below slower MA
        """
        if 'spx_close' not in self.combined_data.columns:
            raise ValueError("SPX data not loaded")
            
        # Calculate moving averages for all configured periods
        ma_periods = MODULE_CONFIG['spx_ma_crossover']['ma_periods']
        ma_signals = {}
        
        # Calculate all MAs
        price = self.combined_data['spx_close']
        for period in ma_periods:
            ma_signals[f'ma{period}'] = price.rolling(window=period).mean()
        
        # Initialize final signal series
        final_signal = pd.Series(True, index=price.index)
        
        # Apply each active signal with confirmation period
        signals = MODULE_CONFIG['spx_ma_crossover']['signals']
        
        # Process price under MA signal
        if signals['price_under_ma']['enabled']:
            ma_period = signals['price_under_ma']['ma_period']
            confirmation_days = signals['price_under_ma']['confirmation_days']
            
            # Get the MA
            ma = ma_signals[f'ma{ma_period}']
            
            # Create signal - risk-off when price is below MA
            raw_signal = price >= ma
            
            # Apply confirmation period
            confirmed_signal = self._apply_confirmation_period(raw_signal, confirmation_days)
            
            # Combine with final signal
            final_signal = final_signal & confirmed_signal
        
        # Process MA below MA signal
        if signals['ma_below_ma']['enabled']:
            fast_period = signals['ma_below_ma']['fast_ma_period']
            slow_period = signals['ma_below_ma']['slow_ma_period']
            confirmation_days = signals['ma_below_ma']['confirmation_days']
            
            # Get the MAs
            fast_ma = ma_signals[f'ma{fast_period}']
            slow_ma = ma_signals[f'ma{slow_period}']
            
            # Create signal - risk-off when fast MA is below slow MA
            raw_signal = fast_ma >= slow_ma
            
            # Apply confirmation period
            confirmed_signal = self._apply_confirmation_period(raw_signal, confirmation_days)
            
            # Combine with final signal
            final_signal = final_signal & confirmed_signal
        
        return final_signal

    def plot_spx_ma_signals(self, signal: pd.Series) -> None:
        """
        Plot SPX data with moving averages and risk-on/off signals.
        
        Args:
            signal (pd.Series): Boolean series indicating risk-on periods
        """
        fig, ax = plt.subplots(figsize=(15, 8))
        
        # Plot SPX data and moving averages
        price = self.combined_data['spx_close']
        ax.plot(price.index, price, label='SPX', color='black')
        
        # Plot moving averages
        ma_periods = MODULE_CONFIG['spx_ma_crossover']['ma_periods']
        colors = ['blue', 'green', 'red']
        for period, color in zip(ma_periods, colors):
            ma = price.rolling(window=period).mean()
            ax.plot(ma.index, ma, label=f'{period}-day MA', color=color, linestyle='--')
        
        # Shade risk-off periods
        risk_off_periods = price.index[~signal]
        ax.fill_between(price.index, 
                        price.min(),
                        price.max(),
                        where=~signal,
                        color='red', alpha=0.2, label='Risk-Off Period')
        
        ax.set_title('SPX with Moving Averages')
        ax.set_ylabel('SPX Price')
        ax.legend()
        ax.grid(True)
        
        plt.tight_layout()
        plt.show()

    def apply_adrt_zscore_module(self) -> pd.Series:
        """
        Apply the ADRT z-score module.
        Returns a boolean series indicating risk-on periods based on ADRT z-scores.
        Goes risk-off when z-score crosses above positive threshold OR below negative threshold
        and stays there for the required days.
        ADRT data is first transformed using log ratio to get a natural [-1, 1] scale.
        """
        if 'ADRT_close' not in self.combined_data.columns:
            raise ValueError("ADRT data not loaded")
            
        # Get configuration parameters
        lookback = MODULE_CONFIG['adrt_zscore']['lookback_period']
        threshold = MODULE_CONFIG['adrt_zscore']['threshold']
        days_required = MODULE_CONFIG['adrt_zscore']['days_crossed_threshold']
        smoothing = MODULE_CONFIG['adrt_zscore']['smoothing_period']
        
        # Get raw ADRT data
        adrt_data = self.combined_data['ADRT_close']
        
        # Transform ADRT ratio to natural [-1, 1] scale using log ratio
        # log(ratio) gives us a symmetric scale around 0
        # We use tanh to bound the values between -1 and 1
        normalized_data = np.tanh(np.log(adrt_data))
        
        # Calculate smoothed normalized ADRT
        adrt_smoothed = normalized_data.rolling(window=smoothing).mean()
        
        # Calculate rolling mean and std for z-score
        rolling_mean = adrt_smoothed.rolling(window=lookback).mean()
        rolling_std = adrt_smoothed.rolling(window=lookback).std()
        
        # Calculate z-score
        zscore = (adrt_smoothed - rolling_mean) / rolling_std
        
        # Initialize signal series
        final_signal = pd.Series(True, index=zscore.index)  # Start with risk-on
        current_state = True
        days_in_state = 0
        
        # Iterate through the data to implement confirmation period
        for i in range(len(zscore)):
            if current_state:  # Currently risk-on
                if abs(zscore.iloc[i]) > threshold:  # Check if z-score exceeds threshold in either direction
                    days_in_state += 1
                    if days_in_state >= days_required:
                        current_state = False
                        days_in_state = 0
                else:
                    days_in_state = 0
            else:  # Currently risk-off
                if abs(zscore.iloc[i]) <= threshold:  # Return to risk-on when z-score is within threshold
                    current_state = True
                    days_in_state = 0
                else:
                    days_in_state = 0
            
            final_signal.iloc[i] = current_state
        
        return final_signal

    def plot_adrt_zscore_signals(self, signal: pd.Series) -> None:
        """
        Plot ADRT data with z-scores and risk-on/off signals.
        
        Args:
            signal (pd.Series): Boolean series indicating risk-on periods
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Shade risk-off periods
        risk_off_periods = self.combined_data.index[~signal]
        ax1.fill_between(self.combined_data.index, 
                        self.combined_data['spx_close'].min(),
                        self.combined_data['spx_close'].max(),
                        where=~signal,
                        color='red', alpha=0.2, label='Risk-Off Period')
        
        ax1.set_title('SPX with ADRT Z-Score Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Calculate and plot z-score
        lookback = MODULE_CONFIG['adrt_zscore']['lookback_period']
        smoothing = MODULE_CONFIG['adrt_zscore']['smoothing_period']
        threshold = MODULE_CONFIG['adrt_zscore']['threshold']
        
        adrt_data = self.combined_data['ADRT_close']
        normalized_data = np.tanh(np.log(adrt_data))
        adrt_smoothed = normalized_data.rolling(window=smoothing).mean()
        rolling_mean = adrt_smoothed.rolling(window=lookback).mean()
        rolling_std = adrt_smoothed.rolling(window=lookback).std()
        zscore = (adrt_smoothed - rolling_mean) / rolling_std
        
        # Plot smoothed z-score
        ax2.plot(zscore.index, zscore, label='ADRT Z-Score', color='blue')
        ax2.axhline(y=threshold, color='red', linestyle='--', 
                   label=f'Threshold ({threshold})')
        ax2.axhline(y=-threshold, color='red', linestyle='--', 
                   label=f'Threshold (-{threshold})')
        ax2.axhline(y=0, color='black', linestyle='--', alpha=0.3)
        
        ax2.set_ylabel('ADRT Z-Score')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def apply_pct_stocks_vs_ma_module(self) -> pd.Series:
        """
        Apply the percentage of stocks vs MA module.
        Returns a boolean series indicating risk-on periods.
        If added_together is True:
            - Averages the enabled indicators
            - Compares result against threshold
        If added_together is False:
            - Goes risk-off when all enabled indicators are below the threshold
        Requires confirmation_days of threshold breach before changing signal state.
        """
        # Get configuration parameters
        threshold = MODULE_CONFIG['pct_stocks_vs_ma']['threshold']
        indicators = MODULE_CONFIG['pct_stocks_vs_ma']['indicators']
        added_together = MODULE_CONFIG['pct_stocks_vs_ma']['added_together']
        confirmation_days = MODULE_CONFIG['pct_stocks_vs_ma']['confirmation_days']
        
        # Initialize list to store enabled data series
        enabled_data = []
        
        # Process each indicator if enabled
        for name, config in indicators.items():
            if config['enabled']:
                if f'{name}-{config["period"]}-day.csv' not in self.additional_data:
                    raise ValueError(f"Required data file for {name} not loaded")
                
                # Get the raw percentage data
                data = self.combined_data[f'{name}-{config["period"]}-day_close']
                enabled_data.append(data)
        
        if not enabled_data:
            raise ValueError("No indicators enabled in pct_stocks_vs_ma module")
        
        # Calculate the signal series based on added_together mode
        if added_together:
            # Calculate average of enabled indicators
            avg_data = pd.concat(enabled_data, axis=1).mean(axis=1)
            # Create initial signal based on average
            initial_signal = avg_data >= threshold
        else:
            # Initialize signal series
            initial_signal = pd.Series(True, index=self.combined_data.index)
            # Create individual signals and combine
            for data in enabled_data:
                signal = data >= threshold
                initial_signal = initial_signal & signal
        
        # Apply confirmation period
        final_signal = pd.Series(True, index=initial_signal.index)  # Start with risk-on
        current_state = True
        days_in_state = 0
        
        # Iterate through the data to implement confirmation period
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
            
            final_signal.iloc[i] = current_state
        
        return final_signal

    def plot_pct_stocks_vs_ma_signals(self, signal: pd.Series) -> None:
        """
        Plot SPX data with percentage of stocks vs MA signals.
        
        Args:
            signal (pd.Series): Boolean series indicating risk-on periods
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Shade risk-off periods
        risk_off_periods = self.combined_data.index[~signal]
        ax1.fill_between(self.combined_data.index, 
                        self.combined_data['spx_close'].min(),
                        self.combined_data['spx_close'].max(),
                        where=~signal,
                        color='red', alpha=0.2, label='Risk-Off Period')
        
        ax1.set_title('SPX with Percentage of Stocks vs MA Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot percentage data for enabled indicators
        threshold = MODULE_CONFIG['pct_stocks_vs_ma']['threshold']
        indicators = MODULE_CONFIG['pct_stocks_vs_ma']['indicators']
        added_together = MODULE_CONFIG['pct_stocks_vs_ma']['added_together']
        colors = {'MMTW': 'blue', 'MMFI': 'green', 'MMTH': 'red'}
        
        if added_together:
            # Calculate average of enabled indicators
            enabled_data = []
            for name, config in indicators.items():
                if config['enabled']:
                    data = self.combined_data[f'{name}-{config["period"]}-day_close']
                    enabled_data.append(data)
            avg_data = pd.concat(enabled_data, axis=1).mean(axis=1)
            
            # Plot average line
            ax2.plot(avg_data.index, avg_data,
                    label='Average of Enabled Indicators',
                    color='black',
                    linewidth=2)
        else:
            # Plot individual indicators
            for name, config in indicators.items():
                if config['enabled']:
                    data = self.combined_data[f'{name}-{config["period"]}-day_close']
                    ax2.plot(data.index, data, 
                            label=f'{name} ({config["period"]}-day)', 
                            color=colors[name], 
                            alpha=0.7)
        
        ax2.axhline(y=threshold, color='black', linestyle='--', 
                   label=f'Threshold ({threshold})')
        
        ax2.set_ylabel('Percentage of Stocks Above MA')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def apply_combined_signals(self) -> pd.Series:
        """
        Apply both ADRT z-score and SPX MA crossover modules to generate combined risk-off signals.
        Returns a boolean series indicating risk-on periods.
        Goes risk-off if either:
        1. ADRT z-score exceeds threshold in either direction
        2. SPX MA crossover signals indicate risk-off
        """
        # Get ADRT z-score signal
        adrt_signal = self.apply_adrt_zscore_module()
        
        # Get SPX MA crossover signal
        spx_ma_signal = self.apply_spx_ma_crossover_module()
        
        # Combine signals - risk-off if either signal indicates risk-off
        combined_signal = adrt_signal & spx_ma_signal
        
        return combined_signal

    def plot_combined_signals(self, signal: pd.Series) -> None:
        """
        Plot SPX data with combined risk-off signals from ADRT z-score and SPX MA crossover.
        
        Args:
            signal (pd.Series): Boolean series indicating risk-on periods
        """
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 10), height_ratios=[2, 1, 1])
        
        # Plot SPX data with combined signals
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Shade risk-off periods from combined signal
        risk_off_periods = self.combined_data.index[~signal]
        ax1.fill_between(self.combined_data.index, 
                        self.combined_data['spx_close'].min(),
                        self.combined_data['spx_close'].max(),
                        where=~signal,
                        color='red', alpha=0.2, label='Combined Risk-Off Period')
        
        ax1.set_title('SPX with Combined Risk-Off Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Calculate and plot ADRT z-score
        lookback = MODULE_CONFIG['adrt_zscore']['lookback_period']
        smoothing = MODULE_CONFIG['adrt_zscore']['smoothing_period']
        threshold = MODULE_CONFIG['adrt_zscore']['threshold']
        
        adrt_data = self.combined_data['ADRT_close']
        normalized_data = np.tanh(np.log(adrt_data))
        adrt_smoothed = normalized_data.rolling(window=smoothing).mean()
        rolling_mean = adrt_smoothed.rolling(window=lookback).mean()
        rolling_std = adrt_smoothed.rolling(window=lookback).std()
        zscore = (adrt_smoothed - rolling_mean) / rolling_std
        
        # Plot ADRT z-score
        ax2.plot(zscore.index, zscore, label='ADRT Z-Score', color='blue')
        ax2.axhline(y=threshold, color='red', linestyle='--', 
                   label=f'Threshold ({threshold})')
        ax2.axhline(y=-threshold, color='red', linestyle='--', 
                   label=f'Threshold (-{threshold})')
        ax2.axhline(y=0, color='black', linestyle='--', alpha=0.3)
        
        ax2.set_ylabel('ADRT Z-Score')
        ax2.legend()
        ax2.grid(True)
        
        # Plot SPX data with MA crossover signals and enabled MAs
        ax3.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Get and plot MA crossover signal
        ma_signal = self.apply_spx_ma_crossover_module()
        ax3.fill_between(self.combined_data.index, 
                        self.combined_data['spx_close'].min(),
                        self.combined_data['spx_close'].max(),
                        where=~ma_signal,
                        color='red', alpha=0.2, label='MA Crossover Risk-Off Period')
        
        # Plot enabled moving averages
        price = self.combined_data['spx_close']
        ma_periods = MODULE_CONFIG['spx_ma_crossover']['ma_periods']
        colors = ['blue', 'green', 'red']
        
        for period, color in zip(ma_periods, colors):
            ma = price.rolling(window=period).mean()
            ax3.plot(ma.index, ma, label=f'{period}-day MA', color=color, linestyle='--', alpha=0.7)
        
        ax3.set_ylabel('SPX Price')
        ax3.legend()
        ax3.grid(True)
        
        plt.tight_layout()
        plt.show()

    def plot_combined_pct_adrt_signals(self, pct_signal: pd.Series, adrt_signal: pd.Series) -> None:
        """
        Plot SPX data with combined risk-off signals from percentage of stocks vs MA and ADRT z-score.
        - Orange shading: Only one module signals risk-off
        - Red shading: Both modules signal risk-off
        
        Args:
            pct_signal (pd.Series): Boolean series indicating risk-on periods from pct_stocks_vs_ma
            adrt_signal (pd.Series): Boolean series indicating risk-on periods from adrt_zscore
        """
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 10), height_ratios=[2, 1, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Calculate combined signals
        both_risk_off = ~pct_signal & ~adrt_signal  # Both modules signal risk-off
        one_risk_off = (~pct_signal | ~adrt_signal) & ~both_risk_off  # Only one module signals risk-off
        
        # Shade risk-off periods
        ax1.fill_between(self.combined_data.index, 
                        self.combined_data['spx_close'].min(),
                        self.combined_data['spx_close'].max(),
                        where=both_risk_off,
                        color='red', alpha=0.2, label='Both Risk-Off')
        
        ax1.fill_between(self.combined_data.index, 
                        self.combined_data['spx_close'].min(),
                        self.combined_data['spx_close'].max(),
                        where=one_risk_off,
                        color='orange', alpha=0.2, label='One Risk-Off')
        
        ax1.set_title('SPX with Combined Risk-Off Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot percentage of stocks vs MA data
        threshold = MODULE_CONFIG['pct_stocks_vs_ma']['threshold']
        indicators = MODULE_CONFIG['pct_stocks_vs_ma']['indicators']
        added_together = MODULE_CONFIG['pct_stocks_vs_ma']['added_together']
        colors = {'MMTW': 'blue', 'MMFI': 'green', 'MMTH': 'red'}
        
        if added_together:
            # Calculate average of enabled indicators
            enabled_data = []
            for name, config in indicators.items():
                if config['enabled']:
                    data = self.combined_data[f'{name}-{config["period"]}-day_close']
                    enabled_data.append(data)
            avg_data = pd.concat(enabled_data, axis=1).mean(axis=1)
            
            # Plot average line
            ax2.plot(avg_data.index, avg_data,
                    label='Average of Enabled Indicators',
                    color='black',
                    linewidth=2)
        else:
            # Plot individual indicators
            for name, config in indicators.items():
                if config['enabled']:
                    data = self.combined_data[f'{name}-{config["period"]}-day_close']
                    ax2.plot(data.index, data, 
                            label=f'{name} ({config["period"]}-day)', 
                            color=colors[name], 
                            alpha=0.7)
        
        ax2.axhline(y=threshold, color='black', linestyle='--', 
                   label=f'Threshold ({threshold})')
        
        ax2.set_ylabel('Percentage of Stocks Above MA')
        ax2.legend()
        ax2.grid(True)
        
        # Calculate and plot ADRT z-score
        lookback = MODULE_CONFIG['adrt_zscore']['lookback_period']
        smoothing = MODULE_CONFIG['adrt_zscore']['smoothing_period']
        threshold = MODULE_CONFIG['adrt_zscore']['threshold']
        
        adrt_data = self.combined_data['ADRT_close']
        normalized_data = np.tanh(np.log(adrt_data))
        adrt_smoothed = normalized_data.rolling(window=smoothing).mean()
        rolling_mean = adrt_smoothed.rolling(window=lookback).mean()
        rolling_std = adrt_smoothed.rolling(window=lookback).std()
        zscore = (adrt_smoothed - rolling_mean) / rolling_std
        
        # Plot ADRT z-score
        ax3.plot(zscore.index, zscore, label='ADRT Z-Score', color='blue')
        ax3.axhline(y=threshold, color='red', linestyle='--', 
                   label=f'Threshold ({threshold})')
        ax3.axhline(y=-threshold, color='red', linestyle='--', 
                   label=f'Threshold (-{threshold})')
        ax3.axhline(y=0, color='black', linestyle='--', alpha=0.3)
        
        ax3.set_ylabel('ADRT Z-Score')
        ax3.legend()
        ax3.grid(True)
        
        plt.tight_layout()
        plt.show()

    def apply_nyse_cumulative_ad_module(self) -> pd.Series:
        """
        Apply the NYSE cumulative Advance-Decline line module.
        Returns a boolean series indicating risk-on periods.
        
        The module:
        1. Calculates daily net advances from NYSE ADRN data
        2. Normalizes the data using log transformation to bound values between -1 and 1
        3. Applies smoothing to the normalized data
        4. Calculates MA of the smoothed data
        5. Generates risk-off signal when smoothed line crosses below MA
        """
        if 'ADRN_close' not in self.combined_data.columns:
            raise ValueError("ADRN data not loaded")
            
        # Get configuration parameters
        smoothing_period = MODULE_CONFIG['nyse_cumulative_ad']['smoothing_period']
        ma_period = MODULE_CONFIG['nyse_cumulative_ad']['ma_period']
        confirmation_days = MODULE_CONFIG['nyse_cumulative_ad']['confirmation_days']
        
        # Get ADRN data and calculate daily net advances
        adrn_data = self.combined_data['ADRN_close']
        
        # Normalize the data using log transformation
        # log(ratio) gives us a symmetric scale around 0
        # We use tanh to bound the values between -1 and 1
        normalized_data = np.tanh(np.log(adrn_data))
        
        # Calculate cumulative sum of normalized data
        cumulative_ad = normalized_data.cumsum()
        
        # Apply smoothing
        smoothed_ad = cumulative_ad.rolling(window=smoothing_period).mean()
        
        # Calculate MA
        ad_ma = smoothed_ad.rolling(window=ma_period).mean()
        
        # Create initial signal - risk-off when smoothed AD line is below MA
        initial_signal = smoothed_ad >= ad_ma
        
        # Apply confirmation period
        final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        
        return final_signal

    def plot_nyse_cumulative_ad_signals(self, signal: pd.Series) -> None:
        """
        Plot SPX data with NYSE cumulative AD line signals.
        
        Args:
            signal (pd.Series): Boolean series indicating risk-on periods
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Shade risk-off periods
        risk_off_periods = self.combined_data.index[~signal]
        ax1.fill_between(self.combined_data.index, 
                        self.combined_data['spx_close'].min(),
                        self.combined_data['spx_close'].max(),
                        where=~signal,
                        color='red', alpha=0.2, label='Risk-Off Period')
        
        ax1.set_title('SPX with NYSE Cumulative AD Line Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Calculate and plot cumulative AD line
        smoothing_period = MODULE_CONFIG['nyse_cumulative_ad']['smoothing_period']
        ma_period = MODULE_CONFIG['nyse_cumulative_ad']['ma_period']
        
        adrn_data = self.combined_data['ADRN_close']
        normalized_data = np.tanh(np.log(adrn_data))
        cumulative_ad = normalized_data.cumsum()
        smoothed_ad = cumulative_ad.rolling(window=smoothing_period).mean()
        ad_ma = smoothed_ad.rolling(window=ma_period).mean()
        
        # Plot smoothed AD line and its MA
        ax2.plot(smoothed_ad.index, smoothed_ad,
                label=f'Smoothed NYSE AD Line ({smoothing_period}-day)', color='blue')
        ax2.plot(ad_ma.index, ad_ma,
                label=f'{ma_period}-day MA', color='red', linestyle='--')
        
        ax2.set_ylabel('Cumulative Normalized AD')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def apply_nasdaq_52w_netnew_high_low_module(self) -> pd.Series:
        """
        Apply the Nasdaq 52-week Cumulative New Highs-New Lows Line module.
        Returns a boolean series indicating risk-on periods.
        
        The module:
        1. Calculates net new highs (HIGQ - LOWQ)
        2. Creates a cumulative sum of net new highs
        3. Calculates z-score using 252-day lookback
        4. Generates risk-off signal when z-score goes below 0
        """
        if 'HIGQ_close' not in self.combined_data.columns or 'LOWQ_close' not in self.combined_data.columns:
            raise ValueError("HIGQ and LOWQ data not loaded")
            
        # Get configuration parameters
        lookback = MODULE_CONFIG['nasdaq_52w_netnew_high_low']['lookback_period']
        confirmation_days = MODULE_CONFIG['nasdaq_52w_netnew_high_low']['confirmation_days']
        
        # Get data
        highs = self.combined_data['HIGQ_close']
        lows = self.combined_data['LOWQ_close']
        
        # Calculate net new highs
        net_highs = highs - lows
        
        # Calculate cumulative sum
        cumulative_net_highs = net_highs.cumsum()
        
        # Calculate z-score
        rolling_mean = cumulative_net_highs.rolling(window=lookback).mean()
        rolling_std = cumulative_net_highs.rolling(window=lookback).std()
        zscore = (cumulative_net_highs - rolling_mean) / rolling_std
        
        # Create initial signal - risk-off when z-score is below 0
        initial_signal = zscore >= 0
        
        # Apply confirmation period
        final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        
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

    def plot_nasdaq_52w_netnew_high_low_signals(self, signal: pd.Series) -> None:
        """
        Plot SPX data with Nasdaq 52-week Cumulative New Highs-New Lows Line signals.
        
        Args:
            signal (pd.Series): Boolean series indicating risk-on periods
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Shade risk-off periods
        risk_off_periods = self.combined_data.index[~signal]
        ax1.fill_between(self.combined_data.index, 
                        self.combined_data['spx_close'].min(),
                        self.combined_data['spx_close'].max(),
                        where=~signal,
                        color='red', alpha=0.2, label='Risk-Off Period')
        
        ax1.set_title('SPX with Nasdaq 52-week Cumulative New Highs-New Lows Line Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Calculate and plot z-score
        lookback = MODULE_CONFIG['nasdaq_52w_netnew_high_low']['lookback_period']
        
        highs = self.combined_data['HIGQ_close']
        lows = self.combined_data['LOWQ_close']
        net_highs = highs - lows
        cumulative_net_highs = net_highs.cumsum()
        
        rolling_mean = cumulative_net_highs.rolling(window=lookback).mean()
        rolling_std = cumulative_net_highs.rolling(window=lookback).std()
        zscore = (cumulative_net_highs - rolling_mean) / rolling_std
        
        # Plot z-score
        ax2.plot(zscore.index, zscore, label='Z-Score', color='blue')
        ax2.axhline(y=0, color='red', linestyle='--', label='Threshold (0)')
        
        ax2.set_ylabel('Z-Score')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def apply_two_ten_inversion_module(self) -> pd.Series:
        """
        Apply the 10Y-2Y Treasury yield spread inversion module.
        Returns a boolean series indicating risk-on periods.
        
        The module:
        1. Calculates the spread between 10Y and 2Y Treasury yields
        2. Generates risk-off signal when spread goes below 0 (inversion)
        """
        if 'US10Y_close' not in self.combined_data.columns or 'US02Y_close' not in self.combined_data.columns:
            raise ValueError("US10Y and US02Y data not loaded")
            
        # Get configuration parameters
        confirmation_days = MODULE_CONFIG['two_ten_inversion']['confirmation_days']
        
        # Get data
        ten_year = self.combined_data['US10Y_close']
        two_year = self.combined_data['US02Y_close']
        
        # Calculate spread
        spread = ten_year - two_year
        
        # Create initial signal - risk-off when spread is below 0
        initial_signal = spread >= 0
        
        # Apply confirmation period
        final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        
        return final_signal

    def plot_two_ten_inversion_signals(self, signal: pd.Series) -> None:
        """
        Plot SPX data with 10Y-2Y Treasury yield spread inversion signals.
        
        Args:
            signal (pd.Series): Boolean series indicating risk-on periods
        """
        # Calculate spread first to ensure we have data
        ten_year = self.combined_data['US10Y_close']
        two_year = self.combined_data['US02Y_close']
        spread = ten_year - two_year
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        spx_data = self.combined_data['spx_close']
        ax1.plot(spx_data.index, spx_data, label='SPX', color='black')
        
        # Shade risk-off periods
        risk_off_periods = spx_data.index[~signal]
        ax1.fill_between(spx_data.index, 
                        spx_data.min(),
                        spx_data.max(),
                        where=~signal,
                        color='red', alpha=0.2, label='Risk-Off Period')
        
        ax1.set_title('SPX with 10Y-2Y Treasury Yield Spread Inversion Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot spread
        ax2.plot(spread.index, spread, label='10Y-2Y Spread', color='blue')
        ax2.axhline(y=0, color='red', linestyle='--', label='Inversion Threshold (0)')
        
        ax2.set_ylabel('Yield Spread (%)')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def apply_nyse_cumulative_ad_zscore_module(self) -> pd.Series:
        """
        Apply the NYSE cumulative AD line z-score module.
        Returns a boolean series indicating risk-on periods.
        
        The module:
        1. Calculates daily net advances from NYSE ADRN data
        2. Normalizes the data using log transformation to bound values between -1 and 1
        3. Calculates cumulative sum of normalized data
        4. Applies smoothing to the cumulative data
        5. Calculates z-score using lookback period
        6. Generates risk-off signal when z-score goes below threshold
        """
        if 'ADRN_close' not in self.combined_data.columns:
            raise ValueError("ADRN data not loaded")
            
        # Get configuration parameters
        lookback = MODULE_CONFIG['nyse_cumulative_ad_zscore']['lookback_period']
        smoothing_period = MODULE_CONFIG['nyse_cumulative_ad_zscore']['smoothing_period']
        threshold = MODULE_CONFIG['nyse_cumulative_ad_zscore']['threshold']
        confirmation_days = MODULE_CONFIG['nyse_cumulative_ad_zscore']['confirmation_days']
        
        # Get ADRN data and calculate daily net advances
        adrn_data = self.combined_data['ADRN_close']
        
        # Normalize the data using log transformation
        normalized_data = np.tanh(np.log(adrn_data))
        
        # Calculate cumulative sum of normalized data
        cumulative_ad = normalized_data.cumsum()
        
        # Apply smoothing
        smoothed_ad = cumulative_ad.rolling(window=smoothing_period).mean()
        
        # Calculate z-score
        rolling_mean = smoothed_ad.rolling(window=lookback).mean()
        rolling_std = smoothed_ad.rolling(window=lookback).std()
        zscore = (smoothed_ad - rolling_mean) / rolling_std
        
        # Create initial signal - risk-off when z-score is below threshold
        initial_signal = zscore >= threshold
        
        # Apply confirmation period
        final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        
        return final_signal

    def plot_nyse_cumulative_ad_zscore_signals(self, signal: pd.Series) -> None:
        """
        Plot SPX data with NYSE cumulative AD line z-score signals.
        
        Args:
            signal (pd.Series): Boolean series indicating risk-on periods
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Shade risk-off periods
        risk_off_periods = self.combined_data.index[~signal]
        ax1.fill_between(self.combined_data.index, 
                        self.combined_data['spx_close'].min(),
                        self.combined_data['spx_close'].max(),
                        where=~signal,
                        color='red', alpha=0.2, label='Risk-Off Period')
        
        ax1.set_title('SPX with NYSE Cumulative AD Line Z-Score Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Calculate and plot z-score
        lookback = MODULE_CONFIG['nyse_cumulative_ad_zscore']['lookback_period']
        smoothing_period = MODULE_CONFIG['nyse_cumulative_ad_zscore']['smoothing_period']
        threshold = MODULE_CONFIG['nyse_cumulative_ad_zscore']['threshold']
        
        adrn_data = self.combined_data['ADRN_close']
        normalized_data = np.tanh(np.log(adrn_data))
        cumulative_ad = normalized_data.cumsum()
        smoothed_ad = cumulative_ad.rolling(window=smoothing_period).mean()
        
        rolling_mean = smoothed_ad.rolling(window=lookback).mean()
        rolling_std = smoothed_ad.rolling(window=lookback).std()
        zscore = (smoothed_ad - rolling_mean) / rolling_std
        
        # Plot z-score
        ax2.plot(zscore.index, zscore, label='Z-Score', color='blue')
        ax2.axhline(y=threshold, color='red', linestyle='--', 
                   label=f'Threshold ({threshold})')
        ax2.axhline(y=0, color='black', linestyle='--', alpha=0.3)
        
        ax2.set_ylabel('Z-Score')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def apply_nasdaq_cumulative_ad_zscore_module(self) -> pd.Series:
        """
        Apply the NASDAQ cumulative AD line z-score module.
        Returns a boolean series indicating risk-on periods.
        
        The module:
        1. Calculates daily net advances from NASDAQ ADRQ data
        2. Normalizes the data using log transformation to bound values between -1 and 1
        3. Calculates cumulative sum of normalized data
        4. Applies smoothing to the cumulative data
        5. Calculates z-score using lookback period
        6. Generates risk-off signal when z-score goes below threshold
        """
        if 'ADRQ_close' not in self.combined_data.columns:
            raise ValueError("ADRQ data not loaded")
            
        # Get configuration parameters
        lookback = MODULE_CONFIG['nasdaq_cumulative_ad_zscore']['lookback_period']
        smoothing_period = MODULE_CONFIG['nasdaq_cumulative_ad_zscore']['smoothing_period']
        threshold = MODULE_CONFIG['nasdaq_cumulative_ad_zscore']['threshold']
        confirmation_days = MODULE_CONFIG['nasdaq_cumulative_ad_zscore']['confirmation_days']
        
        # Get ADRQ data and calculate daily net advances
        adrq_data = self.combined_data['ADRQ_close']
        
        # Normalize the data using log transformation
        normalized_data = np.tanh(np.log(adrq_data))
        
        # Calculate cumulative sum of normalized data
        cumulative_ad = normalized_data.cumsum()
        
        # Apply smoothing
        smoothed_ad = cumulative_ad.rolling(window=smoothing_period).mean()
        
        # Calculate z-score
        rolling_mean = smoothed_ad.rolling(window=lookback).mean()
        rolling_std = smoothed_ad.rolling(window=lookback).std()
        zscore = (smoothed_ad - rolling_mean) / rolling_std
        
        # Create initial signal - risk-off when z-score is below threshold
        initial_signal = zscore >= threshold
        
        # Apply confirmation period
        final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        
        return final_signal

    def plot_nasdaq_cumulative_ad_zscore_signals(self, signal: pd.Series) -> None:
        """
        Plot SPX data with NASDAQ cumulative AD line z-score signals.
        
        Args:
            signal (pd.Series): Boolean series indicating risk-on periods
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Shade risk-off periods
        risk_off_periods = self.combined_data.index[~signal]
        ax1.fill_between(self.combined_data.index, 
                        self.combined_data['spx_close'].min(),
                        self.combined_data['spx_close'].max(),
                        where=~signal,
                        color='red', alpha=0.2, label='Risk-Off Period')
        
        ax1.set_title('SPX with NASDAQ Cumulative AD Line Z-Score Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Calculate and plot z-score
        lookback = MODULE_CONFIG['nasdaq_cumulative_ad_zscore']['lookback_period']
        smoothing_period = MODULE_CONFIG['nasdaq_cumulative_ad_zscore']['smoothing_period']
        threshold = MODULE_CONFIG['nasdaq_cumulative_ad_zscore']['threshold']
        
        adrq_data = self.combined_data['ADRQ_close']
        normalized_data = np.tanh(np.log(adrq_data))
        cumulative_ad = normalized_data.cumsum()
        smoothed_ad = cumulative_ad.rolling(window=smoothing_period).mean()
        
        rolling_mean = smoothed_ad.rolling(window=lookback).mean()
        rolling_std = smoothed_ad.rolling(window=lookback).std()
        zscore = (smoothed_ad - rolling_mean) / rolling_std
        
        # Plot z-score
        ax2.plot(zscore.index, zscore, label='Z-Score', color='blue')
        ax2.axhline(y=threshold, color='red', linestyle='--', 
                   label=f'Threshold ({threshold})')
        ax2.axhline(y=0, color='black', linestyle='--', alpha=0.3)
        
        ax2.set_ylabel('Z-Score')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def apply_combined_mm_signals_module(self) -> pd.Series:
        """
        Apply the combined MM signals module.
        Returns a series with values:
        0: No signals (red)
        1: One signal (orange)
        2: Two signals (yellow)
        3: Three signals (green)
        """
        if not all(f'{name}-{config["period"]}-day.csv' in self.additional_data 
                  for name, config in MODULE_CONFIG['combined_mm_signals']['indicators'].items() 
                  if config['enabled']):
            raise ValueError("Required data files not loaded")
            
        # Get configuration parameters
        threshold = MODULE_CONFIG['combined_mm_signals']['threshold']
        indicators = MODULE_CONFIG['combined_mm_signals']['indicators']
        
        # Initialize signal count series
        signal_count = pd.Series(0, index=self.combined_data.index)
        
        # Process each enabled indicator
        for name, config in indicators.items():
            if config['enabled']:
                # Get the percentage data
                data = self.combined_data[f'{name}-{config["period"]}-day_close']
                # Add 1 to signal count when above threshold
                signal_count += (data >= threshold).astype(int)
        
        return signal_count

    def plot_combined_mm_signals(self, signal_count: pd.Series) -> None:
        """
        Plot SPX data with combined MM signals background.
        - Red: No signals
        - Orange: One signal
        - Yellow: Two signals
        - Green: Three signals
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Create background shading based on signal count
        colors = ['red', 'orange', 'yellow', 'green']
        for i in range(4):
            mask = signal_count == i
            if mask.any():
                ax1.fill_between(self.combined_data.index, 
                               self.combined_data['spx_close'].min(),
                               self.combined_data['spx_close'].max(),
                               where=mask,
                               color=colors[i], alpha=0.2, 
                               label=f'{i} Signal{"s" if i != 1 else ""}')
        
        ax1.set_title('SPX with Combined MM Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot individual indicators
        threshold = MODULE_CONFIG['combined_mm_signals']['threshold']
        indicators = MODULE_CONFIG['combined_mm_signals']['indicators']
        colors = {'MMTW': 'blue', 'MMFI': 'green', 'MMTH': 'red'}
        
        for name, config in indicators.items():
            if config['enabled']:
                data = self.combined_data[f'{name}-{config["period"]}-day_close']
                ax2.plot(data.index, data, 
                        label=f'{name} ({config["period"]}-day)', 
                        color=colors[name], 
                        alpha=0.7)
        
        ax2.axhline(y=threshold, color='black', linestyle='--', 
                   label=f'Threshold ({threshold}%)')
        
        ax2.set_ylabel('Percentage of Stocks Above MA')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

    def apply_all_mm_signals_below_50_module(self) -> pd.Series:
        """
        Apply the all MM signals below 50 module.
        Returns a series with values:
        0: No signals (red background)
        1: One signal (no background)
        2: Two signals (no background)
        3: Three signals (no background)
        """
        if not all(f'{name}-{config["period"]}-day.csv' in self.additional_data 
                  for name, config in MODULE_CONFIG['all_mm_signals_below_50']['indicators'].items() 
                  if config['enabled']):
            raise ValueError("Required data files not loaded")
            
        # Get configuration parameters
        threshold = MODULE_CONFIG['all_mm_signals_below_50']['threshold']
        indicators = MODULE_CONFIG['all_mm_signals_below_50']['indicators']
        
        # Initialize signal count series
        signal_count = pd.Series(0, index=self.combined_data.index)
        
        # Process each enabled indicator
        for name, config in indicators.items():
            if config['enabled']:
                # Get the percentage data
                data = self.combined_data[f'{name}-{config["period"]}-day_close']
                # Add 1 to signal count when above threshold
                signal_count += (data >= threshold).astype(int)
        
        return signal_count

    def plot_all_mm_signals_below_50(self, signal_count: pd.Series) -> None:
        """
        Plot SPX price with red background shading when all MM signals are below 50%.
        
        Args:
            signal_count (pd.Series): Series containing the count of signals below 50%
        """
        if self.combined_data is None:
            logging.error("No data loaded. Call load_data() first.")
            return
            
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(15, 8))
        
        # Plot SPX price
        ax.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black', linewidth=1.5)
        
        # Shade background red when all signals are below 50%
        all_signals_below_50 = signal_count == len(MODULE_CONFIG['all_mm_signals_below_50']['indicators'])
        if all_signals_below_50.any():
            ax.fill_between(
                self.combined_data.index,
                self.combined_data['spx_close'].min(),
                self.combined_data['spx_close'].max(),
                where=all_signals_below_50,
                color='red',
                alpha=0.2,
                label='All Signals Below 50%'
            )
        
        # Set labels and title
        ax.set_xlabel('Date')
        ax.set_ylabel('SPX Price')
        ax.set_title('SPX with All MM Signals Below 50%')
        
        # Add legend
        ax.legend(loc='upper left')
        
        # Rotate x-axis labels
        plt.xticks(rotation=45)
        
        # Adjust layout
        plt.tight_layout()
        
        # Show plot
        plt.show()

    def apply_spx_mmfi_regime_module(self) -> pd.Series:
        """
        Apply the combined SPX 50-day MA and MMFI regime module.
        Returns a boolean series indicating risk-on periods.
        Goes risk-off when either:
        1. SPX is below its 50-day moving average
        2. MMFI is below 50
        """
        if 'spx_close' not in self.combined_data.columns or 'MMFI-50-day_close' not in self.combined_data.columns:
            raise ValueError("Required data not loaded")
            
        # Get configuration parameters
        spx_ma_period = MODULE_CONFIG['spx_mmfi_regime']['spx_ma_period']
        mmfi_threshold = MODULE_CONFIG['spx_mmfi_regime']['mmfi_threshold']
        confirmation_days = MODULE_CONFIG['spx_mmfi_regime']['confirmation_days']
        
        # Calculate SPX 50-day MA
        spx_price = self.combined_data['spx_close']
        spx_ma = spx_price.rolling(window=spx_ma_period).mean()
        
        # Get MMFI data
        mmfi_data = self.combined_data['MMFI-50-day_close']
        
        # Create initial signals
        spx_signal = spx_price >= spx_ma
        mmfi_signal = mmfi_data >= mmfi_threshold
        
        # Combine signals - risk-off if either signal indicates risk-off
        initial_signal = spx_signal & mmfi_signal
        
        # Apply confirmation period if specified
        if confirmation_days > 0:
            final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        else:
            final_signal = initial_signal
        
        return final_signal

    def plot_spx_mmfi_regime_signals(self, signal: pd.Series) -> None:
        """
        Plot SPX data with combined SPX 50-day MA and MMFI regime signals.
        
        Args:
            signal (pd.Series): Boolean series indicating risk-on periods
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), height_ratios=[2, 1])
        
        # Plot SPX data
        ax1.plot(self.combined_data.index, self.combined_data['spx_close'], 
                label='SPX', color='black')
        
        # Plot SPX 50-day MA
        spx_ma_period = MODULE_CONFIG['spx_mmfi_regime']['spx_ma_period']
        spx_price = self.combined_data['spx_close']
        spx_ma = spx_price.rolling(window=spx_ma_period).mean()
        ax1.plot(spx_ma.index, spx_ma, 
                label=f'{spx_ma_period}-day MA', color='red', linestyle='--')
        
        # Shade risk-off periods
        risk_off_periods = self.combined_data.index[~signal]
        ax1.fill_between(self.combined_data.index, 
                        self.combined_data['spx_close'].min(),
                        self.combined_data['spx_close'].max(),
                        where=~signal,
                        color='red', alpha=0.2, label='Risk-Off Period')
        
        ax1.set_title('SPX with Combined SPX 50-day MA and MMFI Regime Signals')
        ax1.set_ylabel('SPX Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot MMFI data
        mmfi_threshold = MODULE_CONFIG['spx_mmfi_regime']['mmfi_threshold']
        mmfi_data = self.combined_data['MMFI-50-day_close']
        ax2.plot(mmfi_data.index, mmfi_data, 
                label='MMFI', color='blue')
        ax2.axhline(y=mmfi_threshold, color='red', linestyle='--', 
                   label=f'Threshold ({mmfi_threshold})')
        
        ax2.set_ylabel('MMFI')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

def main():
    # Initialize research
    research = SPXResearch()
    
    # Determine which data files we need based on active modules
    required_files = ['SPX.csv']
    
    # Add ADRT if enabled
    if MODULE_CONFIG['adrt']['enabled'] or MODULE_CONFIG['adrt_zscore']['enabled']:
        required_files.append('ADRT.csv')
    
    # Add ADRN if enabled
    if MODULE_CONFIG['nyse_cumulative_ad']['enabled'] or MODULE_CONFIG['nyse_cumulative_ad_zscore']['enabled']:
        required_files.append('ADRN.csv')
    
    # Add ADRQ if enabled
    if MODULE_CONFIG['nasdaq_cumulative_ad_zscore']['enabled']:
        required_files.append('ADRQ.csv')
    
    # Add HIGQ and LOWQ if enabled
    if MODULE_CONFIG['nasdaq_52w_netnew_high_low']['enabled']:
        required_files.extend(['HIGQ.csv', 'LOWQ.csv'])
    
    # Add US10Y and US02Y if enabled
    if MODULE_CONFIG['two_ten_inversion']['enabled']:
        required_files.extend(['US10Y.csv', 'US02Y.csv'])
    
    # Add percentage of stocks data if enabled
    if (MODULE_CONFIG['pct_stocks_vs_ma']['enabled'] or 
        MODULE_CONFIG['combined_mm_signals']['enabled'] or 
        MODULE_CONFIG['all_mm_signals_below_50']['enabled'] or
        MODULE_CONFIG['spx_mmfi_regime']['enabled']):
        # Get all unique indicators from all MM signal modules
        all_indicators = set()
        for module in ['pct_stocks_vs_ma', 'combined_mm_signals', 'all_mm_signals_below_50']:
            if MODULE_CONFIG[module]['enabled']:
                for name, config in MODULE_CONFIG[module]['indicators'].items():
                    if config['enabled']:
                        all_indicators.add(f'{name}-{config["period"]}-day.csv')
        required_files.extend(list(all_indicators))
    
    # Load all required data
    logging.info("Loading required data files: %s", required_files)
    research.load_data(required_files)
    
    # Run NYSE cumulative AD z-score module
    if MODULE_CONFIG['nyse_cumulative_ad_zscore']['enabled']:
        logging.info("Running NYSE cumulative AD z-score module")
        regime_signal = research.apply_nyse_cumulative_ad_zscore_module()
        research.plot_nyse_cumulative_ad_zscore_signals(regime_signal)
    
    # Run two-ten inversion module
    if MODULE_CONFIG['two_ten_inversion']['enabled']:
        logging.info("Running two-ten inversion module")
        regime_signal = research.apply_two_ten_inversion_module()
        research.plot_two_ten_inversion_signals(regime_signal)
    
    # Run SPX MMFI regime module
    if MODULE_CONFIG['spx_mmfi_regime']['enabled']:
        logging.info("Running SPX MMFI regime module")
        regime_signal = research.apply_spx_mmfi_regime_module()
        research.plot_spx_mmfi_regime_signals(regime_signal)
    
    # Run all MM signals below 50 module
    if MODULE_CONFIG['all_mm_signals_below_50']['enabled']:
        logging.info("Running all MM signals below 50 module")
        signal_count = research.apply_all_mm_signals_below_50_module()
        research.plot_all_mm_signals_below_50(signal_count)
    
    # Run combined MM signals module
    if MODULE_CONFIG['combined_mm_signals']['enabled']:
        logging.info("Running combined MM signals module")
        signal_count = research.apply_combined_mm_signals_module()
        research.plot_combined_mm_signals(signal_count)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    main()
