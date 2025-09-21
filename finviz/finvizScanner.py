# This python script provides a flexible interface to the finvizfinance package.
# It allows custom filter and sort parameters to be passed in for screening stocks.

from finvizfinance.screener.performance import Performance
import subprocess

banned_tickers = ['HEES', 'ITCI', 'SWI', 'PYCR', 'PTVE', 'PDCO']

def open_incognito(url):
    """Open a URL in Chrome incognito mode (macOS only)"""
    apple_script = f'''
    tell application "Google Chrome"
        activate
        set incognitoWindow to make new window with properties {{mode:"incognito"}}
        tell incognitoWindow to make new tab with properties {{URL:"{url}"}}
    end tell
    '''
    subprocess.run(["osascript", "-e", apple_script])

def get_top_stocks(sort, filters, limit=50):
    """
    Get top stocks based on specific filter and sort criteria
    
    Args:
        sort (str): Sort criteria (e.g., 'Performance (Quarter)', 'Performance (Month)')
        filters (dict): Dictionary of filter criteria
        limit (int): Maximum number of stocks to return (default: 50)
    
    Returns:
        list: List of ticker symbols
    """
    screener = Performance()
    screener.set_filter(filters_dict=filters)
    df = screener.screener_view(order=sort, limit=limit, select_page=None, verbose=1, ascend=False, columns=None, sleep_sec=1)

    # Extract the ticker symbols
    tickers = [f'{ticker}' for ticker in df['Ticker'].values]
    return tickers

def scan_stocks(filters_dict: dict, sort_criteria: str, limit: int = 50, remove_banned: bool = True) -> list:
    """
    Scan stocks using custom filters and sort criteria
    
    Args:
        filters_dict (dict): Dictionary of filter criteria for screening
        sort_criteria (str): Sort criteria for ranking results
        limit (int): Maximum number of stocks to return (default: 50)
        remove_banned (bool): Whether to remove banned tickers (default: True)
    
    Returns:
        list: List of unique ticker symbols
    """
    # Get stocks based on the provided criteria
    tickers = get_top_stocks(sort_criteria, filters_dict, limit)
    
    # Remove banned tickers if requested
    if remove_banned:
        tickers = [ticker for ticker in tickers if ticker not in banned_tickers]
    
    return tickers

def scan_multiple_criteria(filters_dict: dict, sort_criteria_list: list, limit: int = 50, remove_banned: bool = True) -> list:
    """
    Scan stocks using multiple sort criteria and combine results
    
    Args:
        filters_dict (dict): Dictionary of filter criteria for screening
        sort_criteria_list (list): List of sort criteria to use
        limit (int): Maximum number of stocks to return per criteria (default: 50)
        remove_banned (bool): Whether to remove banned tickers (default: True)
    
    Returns:
        list: List of unique ticker symbols from all criteria
    """
    all_tickers = []
    
    for sort_criteria in sort_criteria_list:
        tickers = get_top_stocks(sort_criteria, filters_dict, limit)
        all_tickers.extend(tickers)
    
    # Remove duplicates while preserving order, then remove banned tickers
    unique_tickers = list(dict.fromkeys(all_tickers))
    
    if remove_banned:
        unique_tickers = [ticker for ticker in unique_tickers if ticker not in banned_tickers]
    
    return unique_tickers

def main():
    """Example usage of the finvizScanner module"""
    # Example filters
    filters = {
        'Average Volume': 'Over 100K',
        'Current Volume': 'Over 100K',
        '200-Day Simple Moving Average': 'Price above SMA200',
        'Market Cap.': '+Mid (over $2bln)',
        'Performance': 'Quarter Up'
    }
    
    # Example sort criteria
    sort_criteria = 'Performance (Quarter)'
    
    # Get stocks using single criteria
    tickers = scan_stocks(filters, sort_criteria)
    
    print(f"Found {len(tickers)} tickers using single criteria")
    print("Tickers:", ', '.join(tickers))
    
    # Example with multiple criteria
    sort_criteria_list = [
        'Performance (Quarter)',
        'Performance (Half Year)',
        'Performance (Year)'
    ]
    
    unique_tickers = scan_multiple_criteria(filters, sort_criteria_list)
    
    print(f"\nFound {len(unique_tickers)} unique tickers using multiple criteria")
    print("Tickers:", ', '.join(unique_tickers))

if __name__ == "__main__":
    main()
