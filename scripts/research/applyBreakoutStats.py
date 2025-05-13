import pandas as pd
import time
import random  # Simulating API behavior
from getBreakoutStats import get_breakout_stats

def get_breakout_stats_with_retry(ticker, date, retries=3, delay=10):
    """
    Retries the get_breakout_stats function in case of failure.
    """
    for attempt in range(retries):
        try:
            result = get_breakout_stats(ticker, date)
            return result
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {ticker} on {date}: {e}")
            time.sleep(delay)
    return None

def main():
    # Read the gapUpDays.csv file
    df = pd.read_csv("gapUpDays.csv")
    df.columns = ["Ticker", "Date"]  # Ensure proper column names
    
    all_data = []
    
    for _, row in df.iterrows():
        ticker, date = row["Ticker"], row["Date"]
        
        breakout_stats = get_breakout_stats_with_retry(ticker, date)
        
        if breakout_stats:
            # Convert CSV string to list and append
            all_data.append(breakout_stats.split(','))
    
    # Create DataFrame with appropriate column names
    columns = [
        "Ticker", "Date", "GapUp", "LowestLowIdxTime", "LowestLowPctBelowOpen", "HighestHighIdxTime", "HighestHighPctAboveOpen",
        "1min (1/12) BarUp", "1min (1/12) VolUp", "2min (1/10) BarUp", "2min (1/10) VolUp", 
        "5min (1/8) BarUp", "5min (1/8) VolUp", "15min (1/7) BarUp", "15min (1/7) VolUp", 
    ]
    result_df = pd.DataFrame(all_data, columns=columns)
    
    # Save to CSV
    result_df.to_csv("gapUpWithBreakoutStats.csv", index=False)
    print("Saved gapUpWithBreakoutStats.csv")

if __name__ == "__main__":
    main()
