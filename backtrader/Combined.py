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

class CombinedStrategy(bt.Strategy):
    params = (
        ('debug', False),    # Debug flag for logging
        ('spx_alloc', 0.60), # SPX allocation
        ('gold_alloc', 0.20), # GOLD allocation
        ('btc_alloc', 0.10), # BTC allocation
        ('rebalance_threshold', 0.10),  # Rebalance when allocation deviates by 5%
        ('rebalance_days', 90),  # Minimum days between rebalances
    )

    def __init__(self):
        # Track position targets
        self.position_targets = {
            'spx': 0,
            'gold': 0,
            'btc': 0
        }
        
        # Track last rebalance date
        self.last_rebalance = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if self.p.debug:  # Only log if debug is enabled
                if order.isbuy():
                    self.log(f'BUY EXECUTED, Asset: {order.data._name}, Price: ${order.executed.price:,.2f}, Cost: ${order.executed.value:,.2f}, Comm: ${order.executed.comm:,.2f}')
                else:
                    self.log(f'SELL EXECUTED, Asset: {order.data._name}, Price: ${order.executed.price:,.2f}, Cost: ${order.executed.value:,.2f}, Comm: ${order.executed.comm:,.2f}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.p.debug:  # Only log if debug is enabled
                self.log(f'Order Canceled/Margin/Rejected for {order.data._name}')

    def log(self, txt, dt=None):
        if self.p.debug:  # Only log if debug is enabled
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def should_rebalance(self):
        # Check if enough days have passed since last rebalance
        if self.last_rebalance is None:
            return True
            
        days_since_rebalance = (self.data0.datetime.date(0) - self.last_rebalance).days
        if days_since_rebalance < self.p.rebalance_days:
            return False
            
        # Check if any allocation has deviated beyond threshold
        portfolio_value = self.broker.getvalue()
        
        # Calculate current allocations
        spx_value = self.position_targets['spx'] * self.data0.close[0]
        gold_value = self.position_targets['gold'] * self.data1.close[0]
        btc_value = self.position_targets['btc'] * self.data2.close[0]
        
        spx_alloc = spx_value / portfolio_value
        gold_alloc = gold_value / portfolio_value
        btc_alloc = btc_value / portfolio_value
        
        # Check if any allocation has deviated beyond threshold
        if (abs(spx_alloc - self.p.spx_alloc) > self.p.rebalance_threshold or
            abs(gold_alloc - self.p.gold_alloc) > self.p.rebalance_threshold or
            abs(btc_alloc - self.p.btc_alloc) > self.p.rebalance_threshold):
            return True
            
        return False

    def next(self):
        # Skip if we have any NaN values
        if any(np.isnan([self.data0.close[0], self.data1.close[0], self.data2.close[0]])):
            return
            
        # Check if we should rebalance
        if not self.should_rebalance():
            return
            
        # Calculate target positions for each asset
        portfolio_value = self.broker.getvalue()
        
        # SPX position (60%)
        spx_target = portfolio_value * self.p.spx_alloc
        spx_units = int(spx_target / self.data0.close[0])
        if spx_units != self.position_targets['spx']:
            self.order_target_size(data=self.data0, target=spx_units)
            self.position_targets['spx'] = spx_units
        
        # GOLD position (20%)
        gold_target = portfolio_value * self.p.gold_alloc
        gold_units = int(gold_target / self.data1.close[0])
        if gold_units != self.position_targets['gold']:
            self.order_target_size(data=self.data1, target=gold_units)
            self.position_targets['gold'] = gold_units
        
        # BTC position (10%)
        btc_target = portfolio_value * self.p.btc_alloc
        btc_units = int(btc_target / self.data2.close[0])
        if btc_units != self.position_targets['btc']:
            self.order_target_size(data=self.data2, target=btc_units)
            self.position_targets['btc'] = btc_units
            
        # Update last rebalance date
        self.last_rebalance = self.data0.datetime.date(0)

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
    
    # Add a strategy
    cerebro.addstrategy(CombinedStrategy)
    
    # Load data
    spx_data = pd.read_csv(Path(__file__).parent.parent / 'data' / 'SPX.csv', index_col=0, parse_dates=True)
    gold_data = pd.read_csv(Path(__file__).parent.parent / 'data' / 'GOLD.csv', index_col=0, parse_dates=True)
    btc_data = pd.read_csv(Path(__file__).parent.parent / 'data' / 'BTCUSD.csv', index_col=0, parse_dates=True)
    
    # Drop the 'symbol' column if it exists
    for data in [spx_data, gold_data, btc_data]:
        if 'symbol' in data.columns:
            data.drop('symbol', axis=1, inplace=True)
    
    # Filter data from 2010 onwards (to include BTC)
    start_date = pd.Timestamp('2010-01-01')
    spx_data = spx_data[spx_data.index >= start_date]
    gold_data = gold_data[gold_data.index >= start_date]
    btc_data = btc_data[btc_data.index >= start_date]
    
    # Drop any rows with NaN values
    spx_data = spx_data.dropna()
    gold_data = gold_data.dropna()
    btc_data = btc_data.dropna()
    
    # Create data feeds
    spx_feed = bt.feeds.PandasData(dataname=spx_data, name='SPX')
    gold_feed = bt.feeds.PandasData(dataname=gold_data, name='GOLD')
    btc_feed = bt.feeds.PandasData(dataname=btc_data, name='BTC')
    
    # Add the data feeds
    cerebro.adddata(spx_feed)
    cerebro.adddata(gold_feed)
    cerebro.adddata(btc_feed)
    
    # Set our desired cash start
    cerebro.broker.setcash(100000.0)
    
    # Set the commission - 0.1% ... divide by 100 to remove the %
    cerebro.broker.setcommission(commission=0.001)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(WinRateAnalyzer, _name='winrate')
    
    # Print out the starting conditions
    print('Starting Portfolio Value: ${:,.2f}'.format(cerebro.broker.getvalue()))
    print('Backtest Start Date:', spx_data.index[0].strftime('%Y-%m-%d'))
    print('Backtest End Date:', spx_data.index[-1].strftime('%Y-%m-%d'))
    
    # Run over everything
    results = cerebro.run()
    strat = results[0]
    
    # Print out the final result
    print('\nFinal Portfolio Value: ${:,.2f}'.format(cerebro.broker.getvalue()))

    # Calculate buy and hold returns
    start_price_spx = spx_data['close'].iloc[0]
    end_price_spx = spx_data['close'].iloc[-1]
    spx_return = (end_price_spx / start_price_spx - 1) * 100

    start_price_gold = gold_data['close'].iloc[0]
    end_price_gold = gold_data['close'].iloc[-1]
    gold_return = (end_price_gold / start_price_gold - 1) * 100

    start_price_btc = btc_data['close'].iloc[0]
    end_price_btc = btc_data['close'].iloc[-1]
    btc_return = (end_price_btc / start_price_btc - 1) * 100

    # Calculate weighted buy and hold return
    buy_hold_return = (spx_return * 0.60 + gold_return * 0.20 + btc_return * 0.10)
    buy_hold_value = 100000.0 * (1 + buy_hold_return/100)

    print('\nBuy and Hold Value: ${:,.2f}'.format(buy_hold_value))

    # Calculate buy and hold drawdown
    def calculate_drawdown(returns):
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative / running_max - 1) * 100
        return drawdown

    # Calculate daily returns for each asset
    spx_returns = spx_data['close'].pct_change()
    gold_returns = gold_data['close'].pct_change()
    btc_returns = btc_data['close'].pct_change()

    # Calculate weighted portfolio returns
    portfolio_returns = (spx_returns * 0.60 + gold_returns * 0.20 + btc_returns * 0.10)
    portfolio_returns = portfolio_returns.fillna(0)

    # Calculate drawdown
    drawdown = calculate_drawdown(portfolio_returns)
    max_drawdown = drawdown.min()
    
    # Calculate max drawdown length
    drawdown_periods = (drawdown < 0).astype(int)
    drawdown_lengths = []
    current_length = 0
    
    for is_drawdown in drawdown_periods:
        if is_drawdown:
            current_length += 1
        else:
            if current_length > 0:
                drawdown_lengths.append(current_length)
            current_length = 0
    
    if current_length > 0:
        drawdown_lengths.append(current_length)
    
    max_drawdown_length = max(drawdown_lengths) if drawdown_lengths else 0

    # Get the analyzers
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    returns = strat.analyzers.returns.get_analysis()
    trades = strat.analyzers.trades.get_analysis()

    print('\nDrawdown Analysis:')
    print('Strategy Max Drawdown: {:.2f}%'.format(drawdown['max']['drawdown']))
    print('Strategy Max Drawdown Length: {} days'.format(drawdown['max']['len']))
    print('Buy and Hold Max Drawdown: {:.2f}%'.format(abs(max_drawdown)))
    print('Buy and Hold Max Drawdown Length: {} days'.format(max_drawdown_length))

    print('\nReturns Analysis:')
    print('Strategy Total Return: {:.2f}%'.format(returns['rtot'] * 100))
    print('Strategy Annual Return: {:.2f}%'.format(returns['rnorm'] * 100))
    print('Buy and Hold Return: {:.2f}%'.format(buy_hold_return))
    print('Buy and Hold Annual Return: {:.2f}%'.format(buy_hold_return / (len(spx_data) / 252)))

    print('\nIndividual Asset Buy and Hold Returns:')
    print('SPX (60%): {:.2f}%'.format(spx_return))
    print('GOLD (20%): {:.2f}%'.format(gold_return))
    print('BTC (10%): {:.2f}%'.format(btc_return))

    print('\nTrade Analysis:')
    print('Total Trades:', trades.get('total', {}).get('total', 0))
    
    # Safely access trade statistics with error handling
    won_trades = trades.get('won', {})
    lost_trades = trades.get('lost', {})
    
    if won_trades:
        print('Winning Trades:', won_trades.get('total', 0))
        print('Win Rate: {:.2f}%'.format(won_trades.get('total', 0) / trades.get('total', {}).get('total', 1) * 100))
        print('Average Win: ${:,.2f}'.format(won_trades.get('pnl', {}).get('average', 0)))
    else:
        print('No winning trades recorded')
        
    if lost_trades:
        print('Losing Trades:', lost_trades.get('total', 0))
        print('Average Loss: ${:,.2f}'.format(lost_trades.get('pnl', {}).get('average', 0)))
    else:
        print('No losing trades recorded')

    # Plot win rate over time
    winrate_analysis = strat.analyzers.winrate.get_analysis()
    if winrate_analysis['win_rates']:
        plot_win_rate(winrate_analysis['win_rates'], winrate_analysis['dates'])
    
    # Plot the result
    cerebro.plot(style='candlestick')

if __name__ == '__main__':
    run_backtest()
