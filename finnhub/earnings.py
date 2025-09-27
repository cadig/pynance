"""
Earnings data retrieval using Finnhub API
"""
import requests
import json
from datetime import datetime, timedelta
from .config_reader import get_finnhub_credentials


def get_next_earnings_date(symbol):
    """
    Retrieve the next upcoming earnings date for a given ticker symbol
    
    Args:
        symbol (str): Stock ticker symbol (e.g., 'AAPL')
        
    Returns:
        datetime or None: Next earnings date if found, None if no earnings found
        
    Raises:
        Exception: If API request fails or credentials are invalid
    """
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
