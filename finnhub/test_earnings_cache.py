#!/usr/bin/env python3
"""
Test script for earnings cache functionality
"""
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import the earnings module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finnhub.earnings import get_next_earnings_date, is_earnings_at_least_days_away, _get_cache_file_path, _load_earnings_cache

def test_earnings_cache():
    """Test the earnings caching functionality"""
    print("=== Testing Earnings Cache Functionality ===\n")
    
    # Test symbols
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
    
    print("1. Testing cache file creation and first API calls...")
    for symbol in test_symbols:
        try:
            print(f"   Fetching earnings for {symbol}...")
            earnings_date = get_next_earnings_date(symbol)
            if earnings_date:
                print(f"   {symbol}: Next earnings on {earnings_date.strftime('%Y-%m-%d')}")
            else:
                print(f"   {symbol}: No earnings found")
        except Exception as e:
            print(f"   {symbol}: Error - {e}")
    
    print(f"\n2. Checking cache file...")
    cache_file = _get_cache_file_path()
    print(f"   Cache file location: {cache_file}")
    print(f"   Cache file exists: {os.path.exists(cache_file)}")
    
    if os.path.exists(cache_file):
        cache_df = _load_earnings_cache()
        print(f"   Cache contains {len(cache_df)} entries:")
        for _, row in cache_df.iterrows():
            date_str = row['Next_Earnings_Date'].strftime('%Y-%m-%d') if pd.notna(row['Next_Earnings_Date']) else 'None'
            print(f"     {row['Ticker']}: {date_str} (updated: {row['Last_Updated']})")
    
    print(f"\n3. Testing cache retrieval (should use cache, not API)...")
    for symbol in test_symbols:
        try:
            print(f"   Fetching earnings for {symbol} (should use cache)...")
            earnings_date = get_next_earnings_date(symbol)
            if earnings_date:
                print(f"   {symbol}: Next earnings on {earnings_date.strftime('%Y-%m-%d')} (from cache)")
            else:
                print(f"   {symbol}: No earnings found (from cache)")
        except Exception as e:
            print(f"   {symbol}: Error - {e}")
    
    print(f"\n4. Testing is_earnings_at_least_days_away function...")
    for symbol in test_symbols:
        try:
            is_safe = is_earnings_at_least_days_away(symbol, min_days=8)
            print(f"   {symbol}: Safe to trade (8+ days from earnings): {is_safe}")
        except Exception as e:
            print(f"   {symbol}: Error - {e}")
    
    print(f"\n=== Test Complete ===")

if __name__ == "__main__":
    test_earnings_cache()
