# this script is going to receive the path to the nasdaq.csv as an input arg string
# it will read that file and retrieve the list of tickers from the "Ticker" column.
# it will iterate through the list of tickers and for each iteration it will
# - request historical data from the ib client that we set up,
# - then calculate a column of change from the previous day close to the current day open as a percentage,
# - then we will filter the days that the percent gap up is greater than 8%
# - then we will write the ticker and list of days (as mm/dd/yyy format) into a map structure like gapUpDays = { "ticker": [date] }
# - then we will do the same thing by filtering on the column for down days less than -8% and capture in a separate map structure named gapDownDays
# Finally, at the end of the iteration of all of the tickers, we will write to two separate new csv files, with columns Ticker,Date , named gapUpDays.csv and gapDownDays.csv
from ib_insync import IB
import pandas as pd
import time
import sys
sys.path.append('../..')
from ibkr.IbkrTrader import IbkrTrader as IbkrClient

def get_stock_data_with_retry(ibt, ticker, retries=3, delay=5):
    for attempt in range(retries):
        try:
            data = ibt.getStockData(ticker, None, '1 day', '10 Y', 'TRADES')
            if not data.empty:
                return data
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {ticker}: {e}")
        
        time.sleep(delay)
    print(f"Failed to retrieve data for {ticker} after {retries} attempts.")
    return pd.DataFrame()

def main():
    args = sys.argv[1:]
    pathToFile = args[0]
    
    # Read CSV file and extract first 25 tickers since those were most likely in the nasdaq for past 10 years
    # TODO: get the date added to the nasdaq for the others, and only use history from that date forward
    df = pd.read_csv(pathToFile)
    tickers = df['Ticker'][0:24].tolist()
    
    gapUpDays = {}
    gapDownDays = {}
    
    ib = IB()
    ibt = IbkrClient(ib, logFilepath='System', verbose=True)
    try:
        ibt.connectClient(port=7496)
    
        for ticker in tickers: # ['NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOG', 'META', 'TSLA']:
            if ticker == 'GOOGL': continue
            
            data = get_stock_data_with_retry(ibt, ticker)
            
            # Calculate ADR (average daily range) over the past 20 days
            # data['adr'] = (data['high'] - data['low']).rolling(window=20).mean()
            # data['threshold'] = data['adr'].shift(1) * 20  # Use previous day's ADR
                
            if data.empty:
                continue
            
            data['date'] = pd.to_datetime(data['date'])
            
            # Calculate percentage change
            data['gap_change'] = ((data['open'] - data['close'].shift(1)) / data['close'].shift(1)) * 100
            
            # Filter gap up (> 8%) and gap down (< -8%)
            gap_up = data[data['gap_change'] > 10]
            gap_down = data[data['gap_change'] < -10]
            
            # Filter gap up and gap down based on the dynamic threshold
            # gap_up = data[data['gap_change'] > data['threshold']]
            # gap_down = data[data['gap_change'] < -data['threshold']]
            
            if not gap_up.empty:
                gapUpDays[ticker] = gap_up['date'].dt.strftime('%m/%d/%Y').tolist()
            
            if not gap_down.empty:
                gapDownDays[ticker] = gap_down['date'].dt.strftime('%m/%d/%Y').tolist()
        
    finally:
        ibt.disconnectClient()
        
    # Save results to CSV
    pd.DataFrame([(k, v) for k, dates in gapUpDays.items() for v in dates], columns=['Ticker', 'Date']).to_csv('gapUpDays.csv', index=False)
    pd.DataFrame([(k, v) for k, dates in gapDownDays.items() for v in dates], columns=['Ticker', 'Date']).to_csv('gapDownDays.csv', index=False)
    
    return

if __name__ == "__main__":
    main()