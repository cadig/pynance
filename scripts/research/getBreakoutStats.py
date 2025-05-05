#
# This script will receive a ticker, and day
# It will retrieve the first 1 minute, 2 minute, 5 minute, and 15 minute bars on that day
# It will also retrieve the close price on the previous day, and the 20 day avg volume on the previous day
# Then we can calculate the gapUp pct, pct range up, and pct volume up
#
from ib_insync import IB
from datetime import datetime, timedelta
from typing import Tuple
import sys
sys.path.append('../..')
from ibkr.IbkrTrader import IbkrTrader as IbkrClient

VERBOSE = False

def convert_date_for_ib(date_str: str) -> str:
    """
    Converts a date from 'dd/mm/yyyy' format to 'yyyyMMdd HH:mm:ss' format
    for use with ib_insync's reqHistoricalData endDateTime parameter.
    
    Args:
        date_str (str): Date in 'mm/dd/yyyy' format.
    
    Returns:
        str: Date in 'yyyyMMdd HH:mm:ss' format.
    """
    try:
        date_obj = datetime.strptime(date_str, "%m/%d/%Y")
        return date_obj.strftime("%Y%m%d %H:%M:%S")
    except ValueError:
        raise ValueError("Invalid date format. Use 'dd/mm/yyyy'.")
    
def get_endDateTime_minuteTarget(date_str: str, minutes: int) -> str:
    """
    Adds one day and a specified number of minutes to a date string in 'yyyyMMdd HH:mm:ss' format.
    
    Args:
        date_str (str): Date in 'yyyyMMdd HH:mm:ss' format.
        minutes (int): Number of minutes to add.
    
    Returns:
        str: New date string in 'yyyyMMdd HH:mm:ss' format.
    """
    date_obj = datetime.strptime(date_str, "%Y%m%d %H:%M:%S")
    new_date_obj = date_obj + timedelta(days=1)
    return new_date_obj.strftime("%Y%m%d %H:%M:%S")

def get_day_before(ibt: IbkrClient, ticker: str, endDateTime: str) -> (float, float, float):
    df = ibt.getStockData(ticker, None, '1 day', '20 D', 'TRADES', endDateTime)
    if VERBOSE: print(df)
    return round(df['close'].iloc[-1], 2), round(df['volume'].mean(), 2), round((df['high'] - df['low']).mean(), 2)

def get_breakout_stats(ticker: str, targetDate: str) -> str:
    endDateTime = convert_date_for_ib(targetDate)
    
    ib = IB()
    ibt = IbkrClient(ib, logFilepath='System', verbose=True)
    csvPrintLine=ticker+','+targetDate+','
    try:
        ibt.connectClient(port=7496)
        
        prevClose, prev20DayAvgVol, prev20DayRange = get_day_before(ibt, ticker, endDateTime)
        
        print('prevClose: ', prevClose)
        print('prev20DayAvgVol: ', prev20DayAvgVol)
        # print('prev20DayRange: ', prev20DayRange)
        
        for minuteToGet in ['1 min', '2 mins', '5 mins', '15 mins']:
            endDateTimeForMinuteToGet = get_endDateTime_minuteTarget(endDateTime, int(minuteToGet.split(' ')[0]))
            df = ibt.getStockData(ticker, None, minuteToGet, '1 D', 'TRADES', endDateTimeForMinuteToGet)
            if VERBOSE:
                print('df: ', df)
                print('row: ', df.iloc[0])
            
            barHigh = round(df['high'].iloc[0], 2)
            barLow = round(df['low'].iloc[0], 2)
            barOpen = round(df['open'].iloc[0], 2)
            
            pctRangeUp = round(((barHigh - barLow) / barLow) * 100, 2)
            pctVolumeUp = round((df['volume'].iloc[0] / prev20DayAvgVol) * 100, 2)
            
            print(f'{minuteToGet}:\n\tpctRangeUp: {pctRangeUp}%\n\tpctVolumeUp: {pctVolumeUp}%')
            
            if minuteToGet == '1 min':
                lowestLow = df['low'].min()
                lowestLowIdx = df['low'].idxmin()
                highestHigh = df['high'].max()
                highestHighIdx = df['high'].idxmax()
                
                pctBelowOpen = round(((barOpen - lowestLow) / barOpen) * 100, 2)
                pctAboveOpen = round(((highestHigh - barOpen) / barOpen) * 100, 2)
                gapUpPct = round(((barOpen - prevClose) / prevClose) * 100, 2)
                
                csvPrintLine += f'{gapUpPct/100},{lowestLowIdx},{pctBelowOpen/100},{highestHighIdx},{pctAboveOpen/100},{pctRangeUp/100},{pctVolumeUp/100}'
                
            else:
                csvPrintLine += f',{pctRangeUp/100},{pctVolumeUp/100}'
        
    finally:
        ibt.disconnectClient()
        
    print(csvPrintLine)
        
    return csvPrintLine

def main():
    args = sys.argv[1:]
    ticker = args[0]
    targetDate = args[1]
    get_breakout_stats(ticker, targetDate)
    return
    

if __name__ == "__main__":
    main()