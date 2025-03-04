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

def get_best_etfs() -> dict[str, list[tuple[str, float]]]:
    ib = IB()
    ibt = IbkrClient(ib, logFilepath='System', verbose=True)
    try:
        ibt.connectClient(port=7496)
        
        file_path = "../universe/YieldMax_ETFs.csv"
        df = pd.read_csv(file_path)

        # Initialize dictionaries to store all qualifying ETFs and their yields
        qualified_etfs = {"A": [], "B": [], "C": [], "D": []}

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
                print(f'\nAdding {current_etf} to {group} with yield {yield_value}\n')
                qualified_etfs[group].append((current_etf, yield_value))

        # Sort each group's ETFs by yield in descending order
        for group in qualified_etfs:
            qualified_etfs[group].sort(key=lambda x: x[1], reverse=True)

        print("\nResults:")
        for group, etfs in qualified_etfs.items():
            etf_list = [f"{etf[0]} ({etf[1]:.2f}%)" for etf in etfs]
            print(f"Group {group}: {', '.join(etf_list) if etf_list else 'None'}")
            
    finally:
        ibt.disconnectClient()
        
    return qualified_etfs

def main():
    return get_best_etfs()

if __name__ == "__main__":
    main()