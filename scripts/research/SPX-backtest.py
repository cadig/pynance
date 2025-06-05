import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging
from typing import Dict, List, Tuple
import json
from datetime import datetime

# Configuration for the strategies
STRATEGY_CONFIG = {
    'nyse_cumulative_ad_zscore': {
        'enabled': False,
        'lookback_period': 252,  # Number of days to use for z-score calculation
        'smoothing_period': 50,  # Number of days to smooth the cumulative AD line
        'threshold': -1.0,  # Risk-off when z-score goes below this threshold
        'confirmation_days': 0  # Number of days the z-score must stay below threshold
    },
    'spx_50ma': {
        'enabled': False,
        'ma_period': 50,  # 50-day moving average
        'confirmation_days': 0  # Number of days price must stay below MA to trigger risk-off
    },
    'spx_200ma': {
        'enabled': False,
        'ma_period': 200,  # 200-day moving average
        'confirmation_days': 0  # Number of days price must stay below MA to trigger risk-off
    },
    'mmtw_50': {
        'enabled': False,
        'threshold': 50,  # Risk-off when percentage below this threshold
        'confirmation_days': 0  # Number of days the percentage must stay below threshold
    },
    'mmfi_50': {
        'enabled': True,
        'threshold': 50,  # Risk-off when percentage below this threshold
        'confirmation_days': 0  # Number of days the percentage must stay below threshold
    },
    # inverse created only as a test that the strategy absolutely falls apart when inverted
    'mmfi_50_inverse': {
        'enabled': False,
        'threshold': 50,  # Risk-on when percentage below this threshold
        'confirmation_days': 0  # Number of days the percentage must stay below threshold
    },
    'mmth_50': {
        'enabled': False,
        'threshold': 50,  # Risk-off when percentage below this threshold
        'confirmation_days': 0  # Number of days the percentage must stay below threshold
    },
    'mmtw_nyse_ad_combined': {
        'enabled': False,
        'mmtw_threshold': 50,  # Risk-off when MMTW percentage below this threshold
        'nyse_ad_threshold': -1.0,  # Risk-off when NYSE AD z-score below this threshold
        'nyse_ad_lookback': 252,  # Number of days to use for z-score calculation
        'nyse_ad_smoothing': 50,  # Number of days to smooth the cumulative AD line
        'confirmation_days': 0,  # Number of days indicators must stay below threshold
        'show_strategy_line': False  # Whether to show the strategy line on the plot
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
    }
}

class SPXBacktest:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.spx_data = None
        self.additional_data = {}
        self.combined_data = None
        self.signals = None
        self.returns = None
        self.strategy_returns = None
        
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

    def apply_nyse_cumulative_ad_zscore_strategy(self) -> pd.Series:
        """
        Apply the NYSE cumulative AD line z-score strategy.
        Returns a boolean series indicating risk-on periods.
        """
        if 'ADRN_close' not in self.combined_data.columns:
            raise ValueError("ADRN data not loaded")
            
        # Get configuration parameters
        lookback = STRATEGY_CONFIG['nyse_cumulative_ad_zscore']['lookback_period']
        smoothing_period = STRATEGY_CONFIG['nyse_cumulative_ad_zscore']['smoothing_period']
        threshold = STRATEGY_CONFIG['nyse_cumulative_ad_zscore']['threshold']
        confirmation_days = STRATEGY_CONFIG['nyse_cumulative_ad_zscore']['confirmation_days']
        
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

    def calculate_strategy_returns(self, signal: pd.Series) -> None:
        """
        Calculate strategy returns based on the signal.
        When signal is True (risk-on), returns are equal to SPX returns.
        When signal is False (risk-off), returns are 0 (cash).
        """
        self.strategy_returns = self.returns * signal

    def calculate_performance_metrics(self) -> Dict:
        """
        Calculate performance metrics for both SPX and strategy.
        
        Returns:
            Dict: Dictionary containing performance metrics
        """
        # Calculate cumulative returns
        spx_cumulative = (1 + self.returns).cumprod()
        strategy_cumulative = (1 + self.strategy_returns).cumprod()
        
        # Calculate annualized returns
        years = len(self.returns) / 252
        spx_annual_return = (spx_cumulative.iloc[-1] ** (1/years)) - 1
        strategy_annual_return = (strategy_cumulative.iloc[-1] ** (1/years)) - 1
        
        # Calculate annualized volatility
        spx_annual_vol = self.returns.std() * np.sqrt(252)
        strategy_annual_vol = self.strategy_returns.std() * np.sqrt(252)
        
        # Calculate Sharpe ratio (assuming risk-free rate of 0)
        spx_sharpe = spx_annual_return / spx_annual_vol
        strategy_sharpe = strategy_annual_return / strategy_annual_vol
        
        # Calculate maximum drawdown
        spx_drawdown = (spx_cumulative / spx_cumulative.cummax() - 1).min()
        strategy_drawdown = (strategy_cumulative / strategy_cumulative.cummax() - 1).min()
        
        # Calculate win rate
        spx_win_rate = (self.returns > 0).mean()
        strategy_win_rate = (self.strategy_returns > 0).mean()
        
        return {
            'SPX': {
                'Annual Return': f'{spx_annual_return:.2%}',
                'Annual Volatility': f'{spx_annual_vol:.2%}',
                'Sharpe Ratio': f'{spx_sharpe:.2f}',
                'Max Drawdown': f'{spx_drawdown:.2%}',
                'Win Rate': f'{spx_win_rate:.2%}'
            },
            'Strategy': {
                'Annual Return': f'{strategy_annual_return:.2%}',
                'Annual Volatility': f'{strategy_annual_vol:.2%}',
                'Sharpe Ratio': f'{strategy_sharpe:.2f}',
                'Max Drawdown': f'{strategy_drawdown:.2%}',
                'Win Rate': f'{strategy_win_rate:.2%}'
            }
        }

    def plot_strategy_results(self, strategy_name: str, signal: pd.Series) -> None:
        """
        Plot results for a single strategy.
        
        Args:
            strategy_name (str): Name of the strategy
            signal (pd.Series): Boolean series indicating risk-on periods
        """
        # Calculate cumulative returns
        spx_cumulative = (1 + self.returns).cumprod()
        strategy_returns = self.returns * signal
        strategy_cumulative = (1 + strategy_returns).cumprod()
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), height_ratios=[2, 1])
        
        # Plot SPX and strategy cumulative returns
        ax1.plot(spx_cumulative.index, spx_cumulative, 
                label='SPX', color='black')
        
        # Only plot strategy line if show_strategy_line is True for combined strategy
        if strategy_name != 'mmtw_nyse_ad_combined' or STRATEGY_CONFIG['mmtw_nyse_ad_combined']['show_strategy_line']:
            ax1.plot(strategy_cumulative.index, strategy_cumulative,
                    label=strategy_name.replace('_', ' ').title(), color='blue')
        
        # Shade risk-off periods
        ax1.fill_between(spx_cumulative.index, 
                        spx_cumulative.min(),
                        spx_cumulative.max(),
                        where=~signal,
                        color='red', alpha=0.2, label='Risk-Off Period')
        
        # Find and plot MAE points
        trade_returns = []
        trade_maes = []
        trade_dates = []
        current_trade = 0
        current_trade_start = None
        current_trade_high = None
        current_trade_high_date = None
        
        # Get strategy returns for MAE calculation
        strategy_returns = self.returns * signal
        strategy_cumulative = (1 + strategy_returns).cumprod()
        
        for i, ret in enumerate(strategy_returns):
            current_price = strategy_cumulative.iloc[i]
            current_date = strategy_cumulative.index[i]
            
            if ret != 0:  # If we're in a trade
                if current_trade == 0:  # Just started a new trade
                    current_trade_start = i
                    current_trade_high = current_price
                    current_trade_high_date = current_date
                current_trade += ret
                if current_price > current_trade_high:
                    current_trade_high = current_price
                    current_trade_high_date = current_date
            elif current_trade != 0:  # If we're exiting a trade
                # Calculate MAE for this trade
                if current_trade_start is not None:
                    trade_prices = strategy_cumulative.iloc[current_trade_start:i+1]
                    trade_high = trade_prices.max()
                    trade_low = trade_prices.min()
                    # Calculate MAE as the worst loss from the high
                    mae = (trade_low - trade_high) / trade_high
                    trade_maes.append(mae)
                    trade_dates.append(current_trade_high_date)
                
                trade_returns.append(current_trade)
                current_trade = 0
                current_trade_start = None
                current_trade_high = None
                current_trade_high_date = None
        
        # Add the last trade if it exists
        if current_trade != 0:
            trade_returns.append(current_trade)
            if current_trade_start is not None:
                trade_prices = strategy_cumulative.iloc[current_trade_start:]
                trade_high = trade_prices.max()
                trade_low = trade_prices.min()
                # Calculate MAE as the worst loss from the high
                mae = (trade_low - trade_high) / trade_high
                trade_maes.append(mae)
                trade_dates.append(current_trade_high_date)
        
        # Find the worst MAE point (most negative value)
        if trade_maes:
            max_mae_idx = np.argmin(trade_maes)  # Changed from argmax to argmin to find worst loss
            max_mae = trade_maes[max_mae_idx]
            max_mae_date = trade_dates[max_mae_idx]
            
            # Plot only the worst MAE arrow
            price = strategy_cumulative[max_mae_date]
            # Calculate arrow position (slightly above the price)
            arrow_y = price * 1.01  # 1% above the price
            ax1.annotate(f'MAE: {max_mae:.1%}', xy=(max_mae_date, price), xytext=(max_mae_date, arrow_y),
                        arrowprops=dict(facecolor='red', shrink=0.05, width=2, headwidth=8),
                        ha='center', va='bottom')
        
        ax1.set_title(f'SPX vs {strategy_name.replace("_", " ").title()} Strategy')
        ax1.set_ylabel('Cumulative Return')
        ax1.legend(loc='lower right')  # Always place legend in bottom right
        ax1.grid(True)
        
        # Plot strategy-specific indicator
        if strategy_name == 'nyse_cumulative_ad_zscore':
            # Calculate and plot z-score
            lookback = STRATEGY_CONFIG['nyse_cumulative_ad_zscore']['lookback_period']
            smoothing_period = STRATEGY_CONFIG['nyse_cumulative_ad_zscore']['smoothing_period']
            threshold = STRATEGY_CONFIG['nyse_cumulative_ad_zscore']['threshold']
            
            adrn_data = self.combined_data['ADRN_close']
            normalized_data = np.tanh(np.log(adrn_data))
            cumulative_ad = normalized_data.cumsum()
            smoothed_ad = cumulative_ad.rolling(window=smoothing_period).mean()
            
            rolling_mean = smoothed_ad.rolling(window=lookback).mean()
            rolling_std = smoothed_ad.rolling(window=lookback).std()
            zscore = (smoothed_ad - rolling_mean) / rolling_std
            
            ax2.plot(zscore.index, zscore, label='Z-Score', color='blue')
            ax2.axhline(y=threshold, color='red', linestyle='--', 
                       label=f'Threshold ({threshold})')
            ax2.axhline(y=0, color='black', linestyle='--', alpha=0.3)
            ax2.set_ylabel('Z-Score')
            ax2.legend(loc='lower right')  # Always place legend in bottom right
            
        elif strategy_name in ['spx_50ma', 'spx_200ma']:
            # Plot price and moving average
            price = self.combined_data['spx_close']
            ma_period = STRATEGY_CONFIG[strategy_name]['ma_period']
            ma = price.rolling(window=ma_period).mean()
            
            ax2.plot(price.index, price, label='SPX', color='black')
            ax2.plot(ma.index, ma, label=f'{ma_period}-day MA', color='red', linestyle='--')
            ax2.set_ylabel('SPX Price')
            ax2.legend(loc='lower right')  # Always place legend in bottom right
        
        elif strategy_name in ['mmtw_50', 'mmfi_50', 'mmth_50']:
            # Map strategy names to their corresponding data files
            data_mapping = {
                'mmtw_50': 'MMTW-20-day_close',
                'mmfi_50': 'MMFI-50-day_close',
                'mmth_50': 'MMTH-200-day_close'
            }
            
            # Plot percentage data
            percentage_data = self.combined_data[data_mapping[strategy_name]]
            threshold = STRATEGY_CONFIG[strategy_name]['threshold']
            
            ax2.plot(percentage_data.index, percentage_data, label='Percentage', color='blue')
            ax2.axhline(y=threshold, color='red', linestyle='--', 
                       label=f'Threshold ({threshold}%)')
            ax2.set_ylabel('Percentage of Stocks Above MA')
            ax2.legend(loc='lower right')  # Always place legend in bottom right
        
        elif strategy_name == 'mmtw_nyse_ad_combined':
            # Create two y-axes
            ax2_twin = ax2.twinx()
            
            # Plot MMTW percentage
            mmtw_data = self.combined_data['MMTW-20-day_close']
            mmtw_threshold = STRATEGY_CONFIG['mmtw_nyse_ad_combined']['mmtw_threshold']
            
            ax2.plot(mmtw_data.index, mmtw_data, label='MMTW %', color='blue')
            ax2.axhline(y=mmtw_threshold, color='blue', linestyle='--', 
                       label=f'MMTW Threshold ({mmtw_threshold}%)')
            ax2.set_ylabel('Percentage of Stocks Above MA', color='blue')
            
            # Plot NYSE AD Z-score
            lookback = STRATEGY_CONFIG['mmtw_nyse_ad_combined']['nyse_ad_lookback']
            smoothing_period = STRATEGY_CONFIG['mmtw_nyse_ad_combined']['nyse_ad_smoothing']
            nyse_ad_threshold = STRATEGY_CONFIG['mmtw_nyse_ad_combined']['nyse_ad_threshold']
            
            adrn_data = self.combined_data['ADRN_close']
            normalized_data = np.tanh(np.log(adrn_data))
            cumulative_ad = normalized_data.cumsum()
            smoothed_ad = cumulative_ad.rolling(window=smoothing_period).mean()
            
            rolling_mean = smoothed_ad.rolling(window=lookback).mean()
            rolling_std = smoothed_ad.rolling(window=lookback).std()
            zscore = (smoothed_ad - rolling_mean) / rolling_std
            
            ax2_twin.plot(zscore.index, zscore, label='NYSE AD Z-Score', color='red')
            ax2_twin.axhline(y=nyse_ad_threshold, color='red', linestyle='--', 
                           label=f'NYSE AD Threshold ({nyse_ad_threshold})')
            ax2_twin.axhline(y=0, color='black', linestyle='--', alpha=0.3)
            ax2_twin.set_ylabel('Z-Score', color='red')
            
            # Combine legends and place in bottom right
            lines1, labels1 = ax2.get_legend_handles_labels()
            lines2, labels2 = ax2_twin.get_legend_handles_labels()
            ax2.legend(lines1 + lines2, labels1 + labels2, loc='lower right')
        
        else:
            ax2.legend(loc='lower right')  # Always place legend in bottom right
            ax2.grid(True)
        
        # Calculate and add performance metrics
        metrics = {}
        metrics['SPX'] = self._calculate_strategy_metrics(self.returns)
        metrics[strategy_name] = self._calculate_strategy_metrics(strategy_returns)
        
        # Create table data
        table_data = [
            ['Metric', 'SPX', strategy_name.replace('_', ' ').title()],
            ['Annual Return', metrics['SPX']['Annual Return'], metrics[strategy_name]['Annual Return']],
            ['Annual Volatility', metrics['SPX']['Annual Volatility'], metrics[strategy_name]['Annual Volatility']],
            ['Sharpe Ratio', metrics['SPX']['Sharpe Ratio'], metrics[strategy_name]['Sharpe Ratio']],
            ['Max Drawdown', metrics['SPX']['Max Drawdown'], metrics[strategy_name]['Max Drawdown']],
            ['Win Rate', metrics['SPX']['Win Rate'], metrics[strategy_name]['Win Rate']],
            ['Worst Trade', metrics['SPX']['Worst Trade'], metrics[strategy_name]['Worst Trade']],
            ['Best Trade', metrics['SPX']['Best Trade'], metrics[strategy_name]['Best Trade']],
            ['Average Loss', metrics['SPX']['Average Loss'], metrics[strategy_name]['Average Loss']],
            ['Average Win', metrics['SPX']['Average Win'], metrics[strategy_name]['Average Win']],
            ['Number of Trades', metrics['SPX']['Number of Trades'], metrics[strategy_name]['Number of Trades']],
            ['Winning Trades', metrics['SPX']['Winning Trades'], metrics[strategy_name]['Winning Trades']],
            ['Losing Trades', metrics['SPX']['Losing Trades'], metrics[strategy_name]['Losing Trades']],
            ['Average MAE', metrics['SPX']['Average MAE'], metrics[strategy_name]['Average MAE']],
            ['Maximum MAE', metrics['SPX']['Maximum MAE'], metrics[strategy_name]['Maximum MAE']],
            ['Average MAE (Winning)', metrics['SPX']['Average MAE (Winning)'], metrics[strategy_name]['Average MAE (Winning)']],
            ['Average MAE (Losing)', metrics['SPX']['Average MAE (Losing)'], metrics[strategy_name]['Average MAE (Losing)']]
        ]
        
        # Add table to the figure - always in top left corner
        table = ax1.table(cellText=table_data,
                         loc='upper left',
                         cellLoc='center',
                         bbox=[0.02, 0.55, 0.3, 0.4])  # Adjusted position to accommodate more rows
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)
        
        plt.tight_layout()
        plt.show()

    def _calculate_strategy_metrics(self, returns: pd.Series) -> Dict:
        """
        Calculate performance metrics for a given return series.
        
        Args:
            returns (pd.Series): Daily returns series
            
        Returns:
            Dict: Dictionary containing performance metrics
        """
        cumulative = (1 + returns).cumprod()
        
        # Calculate annualized returns
        years = len(returns) / 252
        annual_return = (cumulative.iloc[-1] ** (1/years)) - 1
        
        # Calculate annualized volatility
        annual_vol = returns.std() * np.sqrt(252)
        
        # Calculate Sharpe ratio (assuming risk-free rate of 0)
        sharpe = annual_return / annual_vol
        
        # Calculate maximum drawdown
        drawdown = (cumulative / cumulative.cummax() - 1).min()
        
        # Calculate win rate
        win_rate = (returns > 0).mean()
        
        # Calculate trade statistics and MAE
        trade_returns = []
        trade_maes = []  # Store MAE for each trade
        current_trade = 0
        current_trade_start = None
        current_trade_high = None
        
        # Get price data for MAE calculation
        price_data = self.combined_data['spx_close']
        
        for i, ret in enumerate(returns):
            current_price = price_data.iloc[i]
            
            if ret != 0:  # If we're in a trade
                if current_trade == 0:  # Just started a new trade
                    current_trade_start = i
                    current_trade_high = current_price
                current_trade += ret
                current_trade_high = max(current_trade_high, current_price)
            elif current_trade != 0:  # If we're exiting a trade
                # Calculate MAE for this trade
                if current_trade_start is not None:
                    trade_prices = price_data.iloc[current_trade_start:i+1]
                    trade_high = trade_prices.max()
                    trade_low = trade_prices.min()
                    mae = (trade_low - trade_high) / trade_high
                    trade_maes.append(mae)
                
                trade_returns.append(current_trade)
                current_trade = 0
                current_trade_start = None
                current_trade_high = None
        
        # Add the last trade if it exists
        if current_trade != 0:
            trade_returns.append(current_trade)
            # Calculate MAE for the last trade
            if current_trade_start is not None:
                trade_prices = price_data.iloc[current_trade_start:]
                trade_high = trade_prices.max()
                trade_low = trade_prices.min()
                mae = (trade_low - trade_high) / trade_high
                trade_maes.append(mae)
        
        # Convert to numpy arrays for calculations
        trade_returns = np.array(trade_returns)
        trade_maes = np.array(trade_maes)
        
        # Calculate trade statistics
        if len(trade_returns) > 0:
            winning_trades = trade_returns[trade_returns > 0]
            losing_trades = trade_returns[trade_returns < 0]
            
            worst_loss = losing_trades.min() if len(losing_trades) > 0 else 0
            best_win = winning_trades.max() if len(winning_trades) > 0 else 0
            avg_loss = losing_trades.mean() if len(losing_trades) > 0 else 0
            avg_win = winning_trades.mean() if len(winning_trades) > 0 else 0
            num_trades = len(trade_returns)
            num_winning_trades = len(winning_trades)
            num_losing_trades = len(losing_trades)
            
            # Calculate MAE statistics
            avg_mae = trade_maes.mean() if len(trade_maes) > 0 else 0
            max_mae = trade_maes.max() if len(trade_maes) > 0 else 0
            winning_trade_maes = trade_maes[trade_returns > 0]
            losing_trade_maes = trade_maes[trade_returns < 0]
            avg_winning_mae = winning_trade_maes.mean() if len(winning_trade_maes) > 0 else 0
            avg_losing_mae = losing_trade_maes.mean() if len(losing_trade_maes) > 0 else 0
        else:
            worst_loss = 0
            best_win = 0
            avg_loss = 0
            avg_win = 0
            num_trades = 0
            num_winning_trades = 0
            num_losing_trades = 0
            avg_mae = 0
            max_mae = 0
            avg_winning_mae = 0
            avg_losing_mae = 0
        
        return {
            'Annual Return': f'{annual_return:.2%}',
            'Annual Volatility': f'{annual_vol:.2%}',
            'Sharpe Ratio': f'{sharpe:.2f}',
            'Max Drawdown': f'{drawdown:.2%}',
            'Win Rate': f'{win_rate:.2%}',
            'Worst Trade': f'{worst_loss:.2%}',
            'Best Trade': f'{best_win:.2%}',
            'Average Loss': f'{avg_loss:.2%}',
            'Average Win': f'{avg_win:.2%}',
            'Number of Trades': f'{num_trades}',
            'Winning Trades': f'{num_winning_trades}',
            'Losing Trades': f'{num_losing_trades}',
            'Average MAE': f'{avg_mae:.2%}',
            'Maximum MAE': f'{max_mae:.2%}',
            'Average MAE (Winning)': f'{avg_winning_mae:.2%}',
            'Average MAE (Losing)': f'{avg_losing_mae:.2%}'
        }

    def apply_spx_ma_strategy(self, ma_period: int, confirmation_days: int = 0) -> pd.Series:
        """
        Apply a simple moving average strategy to SPX.
        Returns a boolean series indicating risk-on periods.
        
        Args:
            ma_period (int): Period for the moving average
            confirmation_days (int): Number of days price must stay below MA to trigger risk-off
        """
        if 'spx_close' not in self.combined_data.columns:
            raise ValueError("SPX data not loaded")
            
        # Calculate moving average
        price = self.combined_data['spx_close']
        ma = price.rolling(window=ma_period).mean()
        
        # Create initial signal - risk-off when price is below MA
        initial_signal = price >= ma
        
        # Apply confirmation period if specified
        if confirmation_days > 0:
            final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        else:
            final_signal = initial_signal
        
        return final_signal

    def apply_mm_strategy(self, strategy_name: str) -> pd.Series:
        """
        Apply a strategy based on percentage of stocks above moving average.
        Returns a boolean series indicating risk-on periods.
        
        Args:
            strategy_name (str): Name of the strategy (mmtw_50, mmfi_50, or mmth_50)
        """
        # Map strategy names to their corresponding data files
        data_mapping = {
            'mmtw_50': 'MMTW-20-day_close',
            'mmfi_50': 'MMFI-50-day_close',
            'mmth_50': 'MMTH-200-day_close'
        }
        
        if strategy_name not in data_mapping:
            raise ValueError(f"Invalid strategy name: {strategy_name}")
            
        data_column = data_mapping[strategy_name]
        if data_column not in self.combined_data.columns:
            raise ValueError(f"Required data column {data_column} not found")
            
        # Get configuration parameters
        threshold = STRATEGY_CONFIG[strategy_name]['threshold']
        confirmation_days = STRATEGY_CONFIG[strategy_name]['confirmation_days']
        
        # Get percentage data
        percentage_data = self.combined_data[data_column]
        
        # Create initial signal - risk-off when percentage is below threshold
        initial_signal = percentage_data >= threshold
        
        # Apply confirmation period if specified
        if confirmation_days > 0:
            final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        else:
            final_signal = initial_signal
        
        return final_signal

    def apply_mmfi_50_inverse_strategy(self) -> pd.Series:
        """
        Apply an inverse strategy based on percentage of stocks above 50-day moving average.
        Returns a boolean series indicating risk-on periods.
        Goes risk-on when percentage is below threshold (opposite of mmfi_50).
        """
        if 'MMFI-50-day_close' not in self.combined_data.columns:
            raise ValueError("MMFI data not loaded")
            
        # Get configuration parameters
        threshold = STRATEGY_CONFIG['mmfi_50_inverse']['threshold']
        confirmation_days = STRATEGY_CONFIG['mmfi_50_inverse']['confirmation_days']
        
        # Get percentage data
        percentage_data = self.combined_data['MMFI-50-day_close']
        
        # Create initial signal - risk-on when percentage is below threshold (opposite of mmfi_50)
        initial_signal = percentage_data < threshold
        
        # Apply confirmation period if specified
        if confirmation_days > 0:
            final_signal = self._apply_confirmation_period(initial_signal, confirmation_days)
        else:
            final_signal = initial_signal
        
        return final_signal

    def apply_combined_mmtw_nyse_ad_strategy(self) -> pd.Series:
        """
        Apply a combined strategy using both MMTW-50 and NYSE AD Z-score.
        Returns a boolean series indicating risk-on periods.
        Goes risk-off if either indicator signals risk-off.
        """
        # Get MMTW signal
        mmtw_signal = self.apply_mm_strategy('mmtw_50')
        
        # Get NYSE AD Z-score signal
        nyse_ad_signal = self.apply_nyse_cumulative_ad_zscore_strategy()
        
        # Combine signals - risk-on only if both signals are risk-on
        combined_signal = mmtw_signal & nyse_ad_signal
        
        return combined_signal

    def apply_combined_mm_signals_strategy(self) -> pd.Series:
        """
        Apply the combined MM signals strategy with position sizing.
        Returns a series with values:
        0.0: No signals (red) - 0% position
        0.33: One signal (orange) - 33% position
        0.67: Two signals (yellow) - 67% position
        1.0: Three signals (green) - 100% position
        """
        if not all(f'{name}-{config["period"]}-day.csv' in self.additional_data 
                  for name, config in STRATEGY_CONFIG['combined_mm_signals']['indicators'].items() 
                  if config['enabled']):
            raise ValueError("Required data files not loaded")
            
        # Get configuration parameters
        threshold = STRATEGY_CONFIG['combined_mm_signals']['threshold']
        indicators = STRATEGY_CONFIG['combined_mm_signals']['indicators']
        
        # Initialize signal count series
        signal_count = pd.Series(0, index=self.combined_data.index)
        
        # Process each enabled indicator
        for name, config in indicators.items():
            if config['enabled']:
                # Get the percentage data
                data = self.combined_data[f'{name}-{config["period"]}-day_close']
                # Add 1 to signal count when above threshold
                signal_count += (data >= threshold).astype(int)
        
        # Convert signal count to position size
        position_size = signal_count.map({
            0: 0.0,    # No signals - 0% position
            1: 0.33,   # One signal - 33% position
            2: 0.67,   # Two signals - 67% position
            3: 1.0     # Three signals - 100% position
        })
        
        return position_size

    def plot_combined_mm_signals_strategy(self, position_size: pd.Series) -> None:
        """
        Plot results for the combined MM signals strategy.
        
        Args:
            position_size (pd.Series): Series indicating position size (0.0 to 1.0)
        """
        # Calculate strategy returns
        strategy_returns = self.returns * position_size
        strategy_cumulative = (1 + strategy_returns).cumprod()
        spx_cumulative = (1 + self.returns).cumprod()
        
        # Create figure with three subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12), height_ratios=[2, 1, 1])
        
        # Plot SPX and strategy cumulative returns
        ax1.plot(spx_cumulative.index, spx_cumulative, 
                label='SPX', color='black')
        ax1.plot(strategy_cumulative.index, strategy_cumulative,
                label='Combined MM Signals Strategy', color='blue')
        
        # Create background shading based on position size
        colors = ['red', 'orange', 'yellow', 'green']
        position_labels = ['0% Position', '33% Position', '67% Position', '100% Position']
        
        for i, (size, color, label) in enumerate(zip([0.0, 0.33, 0.67, 1.0], colors, position_labels)):
            mask = position_size == size
            if mask.any():
                ax1.fill_between(strategy_cumulative.index, 
                               strategy_cumulative.min(),
                               strategy_cumulative.max(),
                               where=mask,
                               color=color, alpha=0.2, 
                               label=label)
        
        ax1.set_title('SPX vs Combined MM Signals Strategy')
        ax1.set_ylabel('Cumulative Return')
        ax1.legend()
        ax1.grid(True)
        
        # Plot position size
        ax2.plot(position_size.index, position_size * 100, 
                label='Position Size', color='blue')
        ax2.set_ylabel('Position Size (%)')
        ax2.set_ylim(-5, 105)
        ax2.legend()
        ax2.grid(True)
        
        # Plot individual indicators
        threshold = STRATEGY_CONFIG['combined_mm_signals']['threshold']
        indicators = STRATEGY_CONFIG['combined_mm_signals']['indicators']
        colors = {'MMTW': 'blue', 'MMFI': 'green', 'MMTH': 'red'}
        
        for name, config in indicators.items():
            if config['enabled']:
                data = self.combined_data[f'{name}-{config["period"]}-day_close']
                ax3.plot(data.index, data, 
                        label=f'{name} ({config["period"]}-day)', 
                        color=colors[name], 
                        alpha=0.7)
        
        ax3.axhline(y=threshold, color='black', linestyle='--', 
                   label=f'Threshold ({threshold}%)')
        
        ax3.set_ylabel('Percentage of Stocks Above MA')
        ax3.legend()
        ax3.grid(True)
        
        # Calculate performance metrics by position size
        position_metrics = {}
        for size, color, label in zip([0.0, 0.33, 0.67, 1.0], colors, position_labels):
            # Get returns for this position size
            mask = position_size == size
            if mask.any():
                position_returns = strategy_returns[mask]
                
                # Calculate trade statistics
                trade_returns = []
                current_trade = 0
                
                for ret in position_returns:
                    if ret != 0:  # If we're in a trade
                        current_trade += ret
                    elif current_trade != 0:  # If we're exiting a trade
                        trade_returns.append(current_trade)
                        current_trade = 0
                
                # Add the last trade if it exists
                if current_trade != 0:
                    trade_returns.append(current_trade)
                
                # Convert to numpy array for calculations
                trade_returns = np.array(trade_returns)
                
                if len(trade_returns) > 0:
                    winning_trades = trade_returns[trade_returns > 0]
                    losing_trades = trade_returns[trade_returns < 0]
                    
                    position_metrics[label] = {
                        'Number of Trades': len(trade_returns),
                        'Winning Trades': len(winning_trades),
                        'Losing Trades': len(losing_trades),
                        'Win Rate': f"{(len(winning_trades) / len(trade_returns)):.1%}" if len(trade_returns) > 0 else "N/A",
                        'Average Win': f"{winning_trades.mean():.1%}" if len(winning_trades) > 0 else "N/A",
                        'Average Loss': f"{losing_trades.mean():.1%}" if len(losing_trades) > 0 else "N/A",
                        'Best Trade': f"{trade_returns.max():.1%}" if len(trade_returns) > 0 else "N/A",
                        'Worst Trade': f"{trade_returns.min():.1%}" if len(trade_returns) > 0 else "N/A",
                        'Total Return': f"{((1 + position_returns).prod() - 1):.1%}"
                    }
                else:
                    position_metrics[label] = {
                        'Number of Trades': 0,
                        'Winning Trades': 0,
                        'Losing Trades': 0,
                        'Win Rate': "N/A",
                        'Average Win': "N/A",
                        'Average Loss': "N/A",
                        'Best Trade': "N/A",
                        'Worst Trade': "N/A",
                        'Total Return': f"{((1 + position_returns).prod() - 1):.1%}"
                    }
        
        # Create table data
        metrics = ['Number of Trades', 'Winning Trades', 'Losing Trades', 'Win Rate', 
                  'Average Win', 'Average Loss', 'Best Trade', 'Worst Trade', 'Total Return']
        
        table_data = [['Metric'] + position_labels]
        for metric in metrics:
            row = [metric]
            for label in position_labels:
                if label in position_metrics:
                    row.append(position_metrics[label][metric])
                else:
                    row.append("N/A")
            table_data.append(row)
        
        # Add table to the figure
        table = ax1.table(cellText=table_data,
                         loc='upper left',
                         cellLoc='center',
                         bbox=[0.02, 0.55, 0.4, 0.4])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)
        
        plt.tight_layout()
        plt.show()

def main():
    # Initialize backtest
    backtest = SPXBacktest()
    
    # Determine which data files we need based on enabled strategies
    required_files = ['SPX.csv']
    
    # Add ADRN if NYSE AD Z-score strategy is enabled
    if STRATEGY_CONFIG['nyse_cumulative_ad_zscore']['enabled'] or STRATEGY_CONFIG['mmtw_nyse_ad_combined']['enabled']:
        required_files.append('ADRN.csv')
    
    # Add percentage of stocks data if enabled
    if any(STRATEGY_CONFIG[strategy]['enabled'] for strategy in ['mmtw_50', 'mmfi_50', 'mmfi_50_inverse', 'mmth_50', 'mmtw_nyse_ad_combined', 'combined_mm_signals']):
        required_files.extend(['MMTW-20-day.csv', 'MMFI-50-day.csv', 'MMTH-200-day.csv'])
    
    # Load required data
    logging.info("Loading required data files: %s", required_files)
    backtest.load_data(required_files)
    
    # Run and plot each enabled strategy separately
    if STRATEGY_CONFIG['nyse_cumulative_ad_zscore']['enabled']:
        logging.info("Running NYSE cumulative AD z-score strategy")
        signal = backtest.apply_nyse_cumulative_ad_zscore_strategy()
        backtest.plot_strategy_results('nyse_cumulative_ad_zscore', signal)
    
    if STRATEGY_CONFIG['spx_50ma']['enabled']:
        logging.info("Running SPX 50-day MA strategy")
        signal = backtest.apply_spx_ma_strategy(
            STRATEGY_CONFIG['spx_50ma']['ma_period'],
            STRATEGY_CONFIG['spx_50ma']['confirmation_days']
        )
        backtest.plot_strategy_results('spx_50ma', signal)
    
    if STRATEGY_CONFIG['spx_200ma']['enabled']:
        logging.info("Running SPX 200-day MA strategy")
        signal = backtest.apply_spx_ma_strategy(
            STRATEGY_CONFIG['spx_200ma']['ma_period'],
            STRATEGY_CONFIG['spx_200ma']['confirmation_days']
        )
        backtest.plot_strategy_results('spx_200ma', signal)
    
    # Run percentage of stocks strategies
    for strategy_name in ['mmtw_50', 'mmfi_50', 'mmth_50']:
        if STRATEGY_CONFIG[strategy_name]['enabled']:
            logging.info(f"Running {strategy_name} strategy")
            signal = backtest.apply_mm_strategy(strategy_name)
            backtest.plot_strategy_results(strategy_name, signal)
    
    # Run inverse MMFI strategy
    if STRATEGY_CONFIG['mmfi_50_inverse']['enabled']:
        logging.info("Running MMFI 50 inverse strategy")
        signal = backtest.apply_mmfi_50_inverse_strategy()
        backtest.plot_strategy_results('mmfi_50_inverse', signal)
    
    # Run combined MMTW and NYSE AD strategy
    if STRATEGY_CONFIG['mmtw_nyse_ad_combined']['enabled']:
        logging.info("Running combined MMTW and NYSE AD strategy")
        signal = backtest.apply_combined_mmtw_nyse_ad_strategy()
        backtest.plot_strategy_results('mmtw_nyse_ad_combined', signal)
    
    # Run combined MM signals strategy
    if STRATEGY_CONFIG['combined_mm_signals']['enabled']:
        logging.info("Running combined MM signals strategy")
        position_size = backtest.apply_combined_mm_signals_strategy()
        backtest.plot_combined_mm_signals_strategy(position_size)
    
    if not any(config['enabled'] for config in STRATEGY_CONFIG.values()):
        logging.warning("No strategies are enabled. Please enable at least one strategy in STRATEGY_CONFIG.")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    main()
