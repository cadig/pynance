import backtrader as bt
import pandas as pd
from pathlib import Path
import datetime

class MMStrategy(bt.Strategy):
    params = (
        ('mmth_period', 200),
        ('mmtw_period', 20),
        ('mmfi_period', 50),
        ('threshold', 50),
    )

    def __init__(self):
        # Store the MM indicators
        self.mmth = self.data1.close
        self.mmtw = self.data2.close
        self.mmfi = self.data3.close
        
        # Track the number of indicators above threshold
        self.indicators_above_threshold = 0
        
        # Set initial position size to 0
        self.position_size = 0

    def next(self):
        # Count how many indicators are above threshold
        self.indicators_above_threshold = sum([
            self.mmth[0] > self.p.threshold,
            self.mmtw[0] > self.p.threshold,
            self.mmfi[0] > self.p.threshold
        ])
        
        # Calculate target position size based on number of indicators above threshold
        if self.indicators_above_threshold == 3:
            target_size = 1.0  # 100% exposure
        elif self.indicators_above_threshold == 2:
            target_size = 0.67  # 67% exposure
        elif self.indicators_above_threshold == 1:
            target_size = 0.33  # 33% exposure
        else:
            target_size = 0.0  # Flat
            
        # Calculate the actual position size in terms of units
        target_units = int(self.broker.getvalue() * target_size / self.data0.close[0])
        
        # Adjust position if needed
        if target_units != self.position.size:
            self.order_target_size(target=target_units)

def run_backtest():
    # Create a cerebro entity
    cerebro = bt.Cerebro()
    
    # Add the strategy
    cerebro.addstrategy(MMStrategy)
    
    # Get the data directory path
    data_dir = Path(__file__).parent.parent / 'data'
    
    # Set start date
    start_date = pd.Timestamp('2001-01-01')
    
    # Load SPX data
    spx_data = pd.read_csv(data_dir / 'SPX.csv', index_col=0, parse_dates=True)
    # Drop the 'symbol' column as it's not needed for backtesting
    spx_data = spx_data.drop('symbol', axis=1)
    # Filter data from 2001 onwards
    spx_data = spx_data[spx_data.index >= start_date]
    
    # Load MM indicator data
    mmth_data = pd.read_csv(data_dir / 'MMTH-200-day.csv', index_col=0, parse_dates=True)
    mmtw_data = pd.read_csv(data_dir / 'MMTW-20-day.csv', index_col=0, parse_dates=True)
    mmfi_data = pd.read_csv(data_dir / 'MMFI-50-day.csv', index_col=0, parse_dates=True)
    
    # Filter indicator data from 2001 onwards
    mmth_data = mmth_data[mmth_data.index >= start_date]
    mmtw_data = mmtw_data[mmtw_data.index >= start_date]
    mmfi_data = mmfi_data[mmfi_data.index >= start_date]
    
    # Create data feeds
    spx_feed = bt.feeds.PandasData(
        dataname=spx_data,
        name='SPX'
    )
    
    mmth_feed = bt.feeds.PandasData(
        dataname=mmth_data,
        name='MMTH'
    )
    
    mmtw_feed = bt.feeds.PandasData(
        dataname=mmtw_data,
        name='MMTW'
    )
    
    mmfi_feed = bt.feeds.PandasData(
        dataname=mmfi_data,
        name='MMFI'
    )
    
    # Add the data feeds
    cerebro.adddata(spx_feed)
    cerebro.adddata(mmth_feed)
    cerebro.adddata(mmtw_feed)
    cerebro.adddata(mmfi_feed)
    
    # Set our desired cash start
    cerebro.broker.setcash(100000.0)
    
    # Set the commission - 0.1% ... divide by 100 to remove the %
    cerebro.broker.setcommission(commission=0.001)
    
    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    print('Backtest Start Date:', spx_data.index[0].strftime('%Y-%m-%d'))
    print('Backtest End Date:', spx_data.index[-1].strftime('%Y-%m-%d'))
    
    # Run over everything
    cerebro.run()
    
    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    
    # Plot the result
    cerebro.plot()

if __name__ == '__main__':
    run_backtest()
