import backtrader as bt
import pandas as pd
import numpy as np
from pathlib import Path
import datetime
import matplotlib.pyplot as plt

class HeikinAshi(bt.Indicator):
    lines = ('ha_open', 'ha_high', 'ha_low', 'ha_close',)
    params = ()

    def __init__(self):
        # For the first bar, use regular OHLC values
        self.lines.ha_close = (self.data.close + self.data.open + self.data.high + self.data.low) / 4
        self.lines.ha_open = bt.If(self.data.open(-1) is None, self.data.open, (self.data.open(-1) + self.data.close(-1)) / 2)
        self.lines.ha_high = bt.Max(self.data.high, self.lines.ha_open, self.lines.ha_close)
        self.lines.ha_low = bt.Min(self.data.low, self.lines.ha_open, self.lines.ha_close)

class WinRateAnalyzer(bt.Analyzer):
    def __init__(self):
        self.trades = []
        self.win_rates = []
        self.dates = []
        self.window_size = 20  # Number of trades to consider for rolling win rate

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades.append({
                'date': self.strategy.data.datetime.date(0),
                'pnl': trade.pnl,
                'won': trade.pnl > 0
            })
            
            # Calculate rolling win rate
            if len(self.trades) >= self.window_size:
                recent_trades = self.trades[-self.window_size:]
                win_rate = sum(1 for t in recent_trades if t['won']) / len(recent_trades)
                self.win_rates.append(win_rate)
                self.dates.append(self.strategy.data.datetime.date(0))

    def get_analysis(self):
        return {
            'win_rates': self.win_rates,
            'dates': self.dates
        }

class GOLDStrategy(bt.Strategy):
    params = (
        ('fast_ma', 50),     # 20-day MA
        ('slow_ma', 200),    # 100-day MA
        ('debug', False),    # Debug flag for logging
    )

    def __init__(self):
        # Calculate Heikin Ashi values
        self.ha = HeikinAshi(self.data0)
        
        # Calculate moving averages of Heikin Ashi close
        self.ha_fast_ma = bt.indicators.SimpleMovingAverage(
            self.ha.ha_close,
            period=self.p.fast_ma
        )
        
        self.ha_slow_ma = bt.indicators.SimpleMovingAverage(
            self.ha.ha_close,
            period=self.p.slow_ma
        )
        
        # Track our position
        self.position_size = 0

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if self.p.debug:  # Only log if debug is enabled
                if order.isbuy():
                    self.log(f'BUY EXECUTED, Price: ${order.executed.price:,.2f}, Cost: ${order.executed.value:,.2f}, Comm: ${order.executed.comm:,.2f}')
                else:
                    self.log(f'SELL EXECUTED, Price: ${order.executed.price:,.2f}, Cost: ${order.executed.value:,.2f}, Comm: ${order.executed.comm:,.2f}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.p.debug:  # Only log if debug is enabled
                self.log('Order Canceled/Margin/Rejected')

    def log(self, txt, dt=None):
        if self.p.debug:  # Only log if debug is enabled
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def next(self):
        # Skip if we don't have enough data for the MAs
        if len(self.ha_fast_ma) < self.p.slow_ma:
            return
            
        # Skip if we have any NaN values in our data
        if (np.isnan(self.data0.close[0]) or 
            np.isnan(self.ha.ha_close[0]) or 
            np.isnan(self.ha_fast_ma[0]) or 
            np.isnan(self.ha_slow_ma[0])):
            return
            
        # Initialize target size
        target_size = 0.0
        
        # Add 33.33% if Heikin Ashi close is above 20-day MA
        if self.ha.ha_close[0] > self.ha_fast_ma[0]:
            target_size += 0.3333
            
        # Add another 33.33% if Heikin Ashi close is above 100-day MA
        if self.ha.ha_close[0] > self.ha_slow_ma[0]:
            target_size += 0.3333
            
        # Add final 33.33% if 20-day MA is above 100-day MA
        if self.ha_fast_ma[0] > self.ha_slow_ma[0]:
            target_size += 0.3333
            
        # Calculate the actual position size in terms of units
        if self.data0.close[0] > 0:  # Ensure we don't divide by zero
            target_units = int(self.broker.getvalue() * target_size / self.data0.close[0])
            
            # Adjust position if needed
            if target_units != self.position.size:
                self.order_target_size(target=target_units)

def plot_win_rate(win_rates, dates):
    plt.figure(figsize=(12, 6))
    plt.plot(dates, win_rates, label='Rolling Win Rate (20 trades)')
    plt.axhline(y=0.5, color='r', linestyle='--', label='50% Win Rate')
    plt.title('Strategy Win Rate Over Time')
    plt.xlabel('Date')
    plt.ylabel('Win Rate')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def run_backtest():
    # Create a cerebro entity
    cerebro = bt.Cerebro()
    
    # Add the strategy
    cerebro.addstrategy(GOLDStrategy)
    
    # Get the data directory path
    data_dir = Path(__file__).parent.parent / 'data'
    
    # Load GOLD data
    gold_data = pd.read_csv(data_dir / 'GOLD.csv', index_col=0, parse_dates=True)
    # Drop the 'symbol' column if it exists
    if 'symbol' in gold_data.columns:
        gold_data = gold_data.drop('symbol', axis=1)
    
    # Filter data from 1960 onwards
    start_date = pd.Timestamp('1960-01-01')
    gold_data = gold_data[gold_data.index >= start_date]
    
    # Drop any rows with NaN values
    gold_data = gold_data.dropna()
    
    # Create data feed
    gold_feed = bt.feeds.PandasData(
        dataname=gold_data,
        name='GOLD'
    )
    
    # Add the data feed
    cerebro.adddata(gold_feed)
    
    # Set our desired cash start
    initial_cash = 100000.0
    cerebro.broker.setcash(initial_cash)
    
    # Set the commission - 0.1% ... divide by 100 to remove the %
    cerebro.broker.setcommission(commission=0.001)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='time_return')
    cerebro.addanalyzer(WinRateAnalyzer, _name='winrate')
    
    # Print out the starting conditions
    print('Starting Portfolio Value: ${:,.2f}'.format(cerebro.broker.getvalue()))
    print('Backtest Start Date:', gold_data.index[0].strftime('%Y-%m-%d'))
    print('Backtest End Date:', gold_data.index[-1].strftime('%Y-%m-%d'))
    
    # Run over everything
    results = cerebro.run()
    strat = results[0]
    
    # Calculate buy and hold returns
    start_price = gold_data['close'].iloc[0]
    end_price = gold_data['close'].iloc[-1]
    buy_hold_return = (end_price / start_price - 1) * 100
    buy_hold_value = initial_cash * (1 + buy_hold_return/100)
    
    # Print out the final result
    print('\nFinal Portfolio Value: ${:,.2f}'.format(cerebro.broker.getvalue()))
    print('Buy and Hold Value: ${:,.2f}'.format(buy_hold_value))
    
    # Print Drawdown Analysis
    drawdown = strat.analyzers.drawdown.get_analysis()
    print('\nDrawdown Analysis:')
    print('Max Drawdown: {:.2f}%'.format(drawdown['max']['drawdown']))
    print('Max Drawdown Length: {} days'.format(drawdown['max']['len']))
    
    # Print Returns Analysis
    returns = strat.analyzers.returns.get_analysis()
    print('\nReturns Analysis:')
    print('Strategy Total Return: {:.2f}%'.format(returns['rtot'] * 100))
    print('Strategy Annual Return: {:.2f}%'.format(returns['rnorm'] * 100))
    print('Buy and Hold Return: {:.2f}%'.format(buy_hold_return))
    
    # Calculate and print annualized buy and hold return
    years = (gold_data.index[-1] - gold_data.index[0]).days / 365.25
    buy_hold_annual = ((1 + buy_hold_return/100) ** (1/years) - 1) * 100
    print('Buy and Hold Annual Return: {:.2f}%'.format(buy_hold_annual))
    
    # Print Trade Analysis
    trades = strat.analyzers.trades.get_analysis()
    print('\nTrade Analysis:')
    print('Total Trades:', trades['total']['total'])
    if trades['total']['total'] > 0:
        print('Winning Trades:', trades['won']['total'])
        print('Losing Trades:', trades['lost']['total'])
        print('Win Rate: {:.2f}%'.format(trades['won']['total'] / trades['total']['total'] * 100))
        if 'pnl' in trades['won']:
            print('Average Winning Trade: ${:,.2f}'.format(trades['won']['pnl']['average']))
        if 'pnl' in trades['lost']:
            print('Average Losing Trade: ${:,.2f}'.format(trades['lost']['pnl']['average']))
    
    # Plot win rate over time
    winrate_analysis = strat.analyzers.winrate.get_analysis()
    if winrate_analysis['win_rates']:
        plot_win_rate(winrate_analysis['win_rates'], winrate_analysis['dates'])
    
    # Plot the result
    cerebro.plot()

if __name__ == '__main__':
    run_backtest()
