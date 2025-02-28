import pandas as pd
from ib_insync import IB
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

def get_best_etfs() -> dict[str, str]:
    ib = IB()
    ibt = IbkrClient(ib, logFilepath='System', verbose=True)
    try:
        ibt.connectClient(port=7496)
        
        file_path = "../universe/YieldMax_ETFs.csv"
        df = pd.read_csv(file_path)

        best_etfs = {"A": "None", "B": "None", "C": "None", "D": "None"}

        best_yield = {"A": float('-inf'), "B": float('-inf'), "C": float('-inf'), "D": float('-inf')}

        for _, row in df.iterrows():
            underlying_ticker = row["Underlying"]
            current_etf = row["ETF"]
            group = row["Group"]
            yield_value = row["Yield"]
            
            data = get_stock_data_with_retry(ibt, underlying_ticker, retries=5, delay=5)
            
            if data.empty:
                print(f"Failed to retrieve data for {underlying_ticker}")
                continue
            
            # Price must be above the 50 day moving average and the 21 day must be above the 50 day
            current_price = data["close"].iloc[-1]
            sma_21 = data["close"].rolling(window=21).mean().iloc[-1]
            sma_50 = data["close"].rolling(window=50).mean().iloc[-1]
            
            if current_price > sma_50 and sma_21 > sma_50:
                if yield_value > best_yield[group]:
                    print(f'\nAdding {current_etf} to {group} because it has the highest yield of {yield_value}\n')
                    best_yield[group] = yield_value
                    best_etfs[group] = current_etf

        print("\nResults:")
        for group, etf in best_etfs.items():
            print(f"Group {group}: {etf}")
            
    finally:
        ibt.disconnectClient()
        
    return best_etfs

def main():
    return get_best_etfs()

if __name__ == "__main__":
    main()