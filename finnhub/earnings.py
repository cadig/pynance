"""
Earnings data retrieval using Finnhub API with local caching
"""
import requests
import json
import os
import pandas as pd
from datetime import datetime, timedelta
from .config_reader import get_finnhub_credentials


def _get_cache_file_path():
    """Get the path to the earnings cache CSV file"""
    cache_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(cache_dir, 'finnhub_earnings_calendar.csv')


def _load_earnings_cache():
    """Load earnings data from cache CSV file"""
    cache_file = _get_cache_file_path()
    
    if not os.path.exists(cache_file):
        return pd.DataFrame(columns=['Ticker', 'Next_Earnings_Date', 'Last_Updated'])
    
    try:
        df = pd.read_csv(cache_file)
        # Convert date column to datetime
        if 'Next_Earnings_Date' in df.columns:
            df['Next_Earnings_Date'] = pd.to_datetime(df['Next_Earnings_Date'], errors='coerce')
        return df
    except Exception as e:
        print(f"Warning: Could not load earnings cache: {e}")
        return pd.DataFrame(columns=['Ticker', 'Next_Earnings_Date', 'Last_Updated'])


def _save_earnings_cache(df):
    """Save earnings data to cache CSV file"""
    cache_file = _get_cache_file_path()
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        
        # Convert datetime to string for CSV storage
        df_to_save = df.copy()
        if 'Next_Earnings_Date' in df_to_save.columns:
            df_to_save['Next_Earnings_Date'] = df_to_save['Next_Earnings_Date'].dt.strftime('%Y-%m-%d')
        
        df_to_save.to_csv(cache_file, index=False)
        return True
    except Exception as e:
        print(f"Warning: Could not save earnings cache: {e}")
        return False


def _clean_expired_cache_entries(df):
    """Remove cache entries where the earnings date has passed"""
    today = datetime.now().date()
    
    # Ensure Next_Earnings_Date column is datetime
    if 'Next_Earnings_Date' in df.columns:
        df['Next_Earnings_Date'] = pd.to_datetime(df['Next_Earnings_Date'], errors='coerce')
    
    # Filter out entries where earnings date is in the past
    valid_entries = df[
        (df['Next_Earnings_Date'].isna()) | 
        (df['Next_Earnings_Date'].dt.date >= today)
    ].copy()
    
    removed_count = len(df) - len(valid_entries)
    if removed_count > 0:
        print(f"Cleaned {removed_count} expired earnings cache entries")
    
    return valid_entries


def _get_earnings_from_api(symbol):
    """Get earnings date from Finnhub API"""
    try:
        # Get API credentials
        api_key = get_finnhub_credentials()
        
        # Set date range: from today to 3 months in advance
        today = datetime.now()
        from_date = today.strftime('%Y-%m-%d')
        to_date = (today + timedelta(days=90)).strftime('%Y-%m-%d')
        
        # Build API URL
        base_url = "https://finnhub.io/api/v1/calendar/earnings"
        params = {
            'from': from_date,
            'to': to_date,
            'symbol': symbol.upper(),
            'token': api_key
        }
        
        # Make API request
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        
        # Check if earnings data exists
        if 'earningsCalendar' not in data or not data['earningsCalendar']:
            return None
        
        # Find the next earnings date
        earnings_list = data['earningsCalendar']
        
        # Sort by date to get the earliest upcoming earnings
        earnings_list.sort(key=lambda x: x.get('date', ''))
        
        # Get the first (earliest) earnings date
        if earnings_list:
            next_earnings_date_str = earnings_list[0].get('date')
            if next_earnings_date_str:
                # Parse the date string (format: YYYY-MM-DD)
                next_earnings_date = datetime.strptime(next_earnings_date_str, '%Y-%m-%d')
                return next_earnings_date
        
        return None
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse API response: {str(e)}")
    except Exception as e:
        raise Exception(f"Error retrieving earnings data: {str(e)}")


def get_next_earnings_date(symbol):
    """
    Retrieve the next upcoming earnings date for a given ticker symbol with caching
    
    Args:
        symbol (str): Stock ticker symbol (e.g., 'AAPL')
        
    Returns:
        datetime or None: Next earnings date if found, None if no earnings found
        
    Raises:
        Exception: If API request fails or credentials are invalid
    """
    symbol_upper = symbol.upper()
    
    try:
        # Load cache and clean expired entries
        cache_df = _load_earnings_cache()
        cache_df = _clean_expired_cache_entries(cache_df)
        
        # Check if ticker exists in cache
        ticker_row = cache_df[cache_df['Ticker'] == symbol_upper]
        
        if not ticker_row.empty:
            # Found in cache, check if earnings date is still valid (not in the past)
            cached_date = ticker_row.iloc[0]['Next_Earnings_Date']
            today = datetime.now().date()
            
            if pd.isna(cached_date) or cached_date.date() >= today:
                # Cache is valid, return the cached date
                return cached_date if not pd.isna(cached_date) else None
            else:
                # Cached date is in the past, remove from cache
                cache_df = cache_df[cache_df['Ticker'] != symbol_upper]
                print(f"Removed expired cache entry for {symbol_upper}")
        
        # Not in cache or expired, fetch from API
        print(f"Fetching earnings data from API for {symbol_upper}")
        next_earnings_date = _get_earnings_from_api(symbol_upper)
        
        # Update cache with new data
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if next_earnings_date:
            new_row = pd.DataFrame({
                'Ticker': [symbol_upper],
                'Next_Earnings_Date': [next_earnings_date],
                'Last_Updated': [current_time]
            })
        else:
            # Store None as NaN for no earnings found
            new_row = pd.DataFrame({
                'Ticker': [symbol_upper],
                'Next_Earnings_Date': [pd.NaT],
                'Last_Updated': [current_time]
            })
        
        # Add or update the row in cache
        if not ticker_row.empty:
            # Update existing row
            cache_df.loc[cache_df['Ticker'] == symbol_upper, 'Next_Earnings_Date'] = next_earnings_date
            cache_df.loc[cache_df['Ticker'] == symbol_upper, 'Last_Updated'] = current_time
        else:
            # Add new row
            cache_df = pd.concat([cache_df, new_row], ignore_index=True)
        
        # Save updated cache
        _save_earnings_cache(cache_df)
        
        return next_earnings_date
        
    except Exception as e:
        raise Exception(f"Error retrieving earnings data: {str(e)}")


def is_earnings_at_least_days_away(symbol, min_days=8):
    """
    Check if the next earnings date is at least the specified number of days away
    
    Args:
        symbol (str): Stock ticker symbol
        min_days (int): Minimum number of days required (default: 8)
        
    Returns:
        bool: True if earnings are at least min_days away, False otherwise
        
    Raises:
        Exception: If unable to retrieve earnings data
    """
    try:
        next_earnings = get_next_earnings_date(symbol)
        
        # If no earnings found, consider it safe
        if next_earnings is None:
            return True
        
        # Calculate days until earnings
        today = datetime.now()
        days_until_earnings = (next_earnings - today).days
        
        return days_until_earnings >= min_days
        
    except Exception as e:
        # If we can't get earnings data, log the error but don't block the trade
        print(f"Warning: Could not verify earnings date for {symbol}: {str(e)}")
        return True  # Allow the trade to proceed if we can't verify earnings
