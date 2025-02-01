# This python script will use the finvizfinance package.
# It will use the following filters:
# - Average Volume: Over 100K
# - 200-Day Simple Moving Average: Price Above 200SMA
# First, it will request the top 100 stocks on the Performance tab, sorted by descending order on the Perf Month and store them in an array.
# Second, it will request the top 100 stocks on the Performance tab, sorted by descending order on the Perf Quarter and store them in an array.
# Third, it will request the top 100 stocks on the Performance tab, sorted by descending order on the Perf Half and store them in an array.
# Finally, it will dedupe the list of tickers in all three arrays, and create a final list of unique tickers. 
# Lastly, it will print in a friendly format the number of total unique tickers, and create a URL that includes all of the tickers to use in finviz 

from finvizfinance.screener.performance import Performance
import subprocess

def open_incognito(url):
    apple_script = f'''
    tell application "Google Chrome"
        activate
        set incognitoWindow to make new window with properties {{mode:"incognito"}}
        tell incognitoWindow to make new tab with properties {{URL:"{url}"}}
    end tell
    '''
    subprocess.run(["osascript", "-e", apple_script])

# Define a function to get top 100 stocks based on specific filter
def get_top_stocks(sort, filters):
    screener = Performance()
    screener.set_filter(filters_dict=filters)
    # screener.set_sort(sort)
    # screener.set_order('asc')
    # screener.set_limit(100)
    df = screener.screener_view(order=sort, limit=50, select_page=None, verbose=1, ascend=False, columns=None, sleep_sec=1)

    # Extract the ticker symbols
    # tickers = [stock['Ticker'] for stock in df]
    # tickers = df['Ticker'].values
    # tickers_csv = ','.join(tickers)
    # return tickers_csv

    tickers = [f'{ticker}' for ticker in df['Ticker'].values]
    return tickers

def main():
    filters = {
        'Average Volume': 'Over 200K',
        'Current Volume': 'Over 100K',
        '200-Day Simple Moving Average': 'Price above SMA200',
        'Market Cap.': '+Mid (over $2bln)',
        'Performance': 'Quarter Up'
    }

    # Fetch stocks sorted by different performance metrics
    top_perf_month = get_top_stocks('Performance (Month)', filters)
    top_perf_quarter = get_top_stocks('Performance (Quarter)', filters)
    top_perf_half = get_top_stocks('Performance (Half Year)', filters)

    # Combine and deduplicate tickers
    unique_tickers = set(top_perf_month + top_perf_quarter + top_perf_half)

    # Print results
    print("\n================ Results ================")
    print(f"Total Unique Tickers: {len(unique_tickers)}")
    print("Tickers:", ', '.join(unique_tickers))

    # Generate Finviz URL
    tickers_list = ','.join(unique_tickers)
    finviz_url = f"https://finviz.com/screener.ashx?v=311&t={tickers_list}&o=-perf13w"
    print("\nFinviz URL:\n", finviz_url)
    
    open_incognito(finviz_url)

if __name__ == "__main__":
    main()
