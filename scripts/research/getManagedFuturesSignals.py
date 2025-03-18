import pandas as pd
import yfinance as yf
import time
from typing import Dict, Optional

def get_weekly_data_with_retry(ticker: str, retries: int = 3, delay: int = 5) -> Optional[pd.DataFrame]:
    """Fetch weekly data for a ticker with retry logic"""
    for attempt in range(retries):
        try:
            data = yf.download(ticker, interval='1wk', period='1y')
            if not data.empty:
                return data
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {ticker}: {e}")
        
        time.sleep(delay)
    print(f"Failed to retrieve data for {ticker} after {retries} attempts.")
    return None

def calculate_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate Heikin Ashi candles from OHLC data"""
    ha = pd.DataFrame(index=df.index)
    
    # Calculate HA Close
    ha['Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # Calculate HA Open
    ha['Open'] = df['Open'].copy()  # Initialize with regular open
    for i in range(1, len(df)):
        ha.loc[ha.index[i], 'Open'] = (ha['Open'].iloc[i-1] + ha['Close'].iloc[i-1]) / 2
    
    # Calculate HA High and Low
    ha['High'] = df[['High', 'Open', 'Close']].max(axis=1)
    ha['Low'] = df[['Low', 'Open', 'Close']].min(axis=1)
    
    return ha

def get_managed_futures_signals() -> Dict[str, str]:
    """Get trading signals for managed futures ETFs"""
    tickers = ['DBMF', 'KMLM', 'CTA', 'FMF', 'WTMF']
    signals = {}
    long_signals = []
    signal_details = []
    
    for ticker in tickers:
        data = get_weekly_data_with_retry(ticker)
        if data is None:
            signals[ticker] = 'NONE'
            signal_details.append(f"{ticker}: NONE - Data retrieval failed")
            continue
            
        # Calculate 8-week EMA
        data['EMA8'] = data['Close'].ewm(span=8, adjust=False).mean()
        
        # Calculate Heikin Ashi candles
        ha_data = calculate_heikin_ashi(data)
        
        # Get latest values
        current_close = ha_data['Close'].iloc[-1]
        current_open = ha_data['Open'].iloc[-1]
        current_ema = data['EMA8'].iloc[-1]
        
        # Check if current bar is green and close is above EMA
        if current_close > current_open and current_close > current_ema:
            signals[ticker] = 'LONG'
            signal_details.append(f"{ticker}: LONG - Close: {current_close:.2f}, EMA8: {current_ema:.2f}")
            long_signals.append(ticker)
        else:
            signals[ticker] = 'NONE'
            signal_details.append(f"{ticker}: NONE - Close: {current_close:.2f}, EMA8: {current_ema:.2f}")
    
    # Print summary
    print("\n=== Signal Summary ===")
    for detail in signal_details:
        print(detail)
        
    if long_signals:
        print("\n=== LONG Signals ===")
        for ticker in long_signals:
            print(f"LONG: {ticker}")
    else:
        print("\nNo LONG signals detected")
    
    return signals

def main():
    return get_managed_futures_signals()

if __name__ == "__main__":
    main()
