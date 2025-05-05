import pandas as pd
import yfinance as yf
import time
from typing import Dict, Optional
from curl_cffi import requests

def get_weekly_data_with_retry(ticker: str, retries: int = 3, delay: int = 5) -> Optional[pd.DataFrame]:
    """Fetch weekly data for a ticker with retry logic"""
    session = requests.Session(impersonate="chrome")
    for attempt in range(retries):
        try:
            data = yf.download(ticker, interval='1wk', period='1y', progress=False, session=session)
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

def get_weekly_signals() -> Dict[str, Dict[str, str]]:
    """Get trading signals for different groups of tickers"""
    ticker_groups = {
        "Managed Futures": ['DBMF', 'KMLM', 'CTA', 'FMF', 'WTMF', 'TFPN', 'MFUT'],
        "Commodities": ['GLD', 'USO', 'DBP', 'DBA', 'DBB', 'DBC', 'DBE', 'DBO'],
        "Mega Cap": ['DIVO','MAGS','TOPT','OEF','QTOP'],
        "Large Cap": ['SPY', 'SCHD', 'NTSX', 'DIVO', 'USMV', 'SSO', 'BRK-B'],
        "Small Cap": ['IWM', 'AVUV'],
        "Tech & Growth": ['QQQ', 'FFTY', 'ARKK', 'ARKQ'],
        "Equity Sectors": ['XLRE', 'XLB', 'XLE', 'XLK', 'XLV', 'XLF', 'XLG', 'XLU', 'XLV'],
        "Crypto": ['BTC-USD', 'ETH-USD'],
        "Real Estate": ['VNQ','MORT','REM','HAUS','SRET','MBB'],
        "Option Income": ['SPYI','QQQI','QYLD','RYLD','YMAX','SVOL'],
        "Bonds": ['TLT', 'IEF', 'SHY', 'AGG', 'MUB', 'HYG', 'LQD'],
        "Ex-US": ['EEM','DFIV','EWC','EWZ','KWEB','FXI','EWA','EWJ','EWG','EWU','EWH','EWS']
    }
    
    all_signals = {}
    long_signals_by_group = {}
    
    for group_name, tickers in ticker_groups.items():
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
        
        # Print summary for this group
        print(f"\n=== {group_name} ===")
        for detail in signal_details:
            print(detail)
            
        if long_signals:
            print(f"\n=== {group_name} LONG Signals ===")
            for ticker in long_signals:
                print(f"LONG: {ticker}")
        else:
            print(f"\nNo LONG signals detected for {group_name}")
        
        all_signals[group_name] = signals
        long_signals_by_group[group_name] = long_signals  # Store long signals for final summary
    
    # Print final summary of all LONG signals by group
    print("\n\n=== FINAL SUMMARY - ALL LONG SIGNALS ===")
    for group_name, long_signals in long_signals_by_group.items():
        if long_signals:
            print(f"\n{group_name}:")
            for ticker in long_signals:
                print(f"  • {ticker}")
    
    return all_signals

def main():
    return get_weekly_signals()

if __name__ == "__main__":
    main() 