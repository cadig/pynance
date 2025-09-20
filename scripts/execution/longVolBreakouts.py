import time
from datetime import datetime
from typing import TypedDict, Dict, Tuple
from ib_insync import IB

import sys
sys.path.append('../..')
from ibkr.IbkrTrader import IbkrTrader as IbkrClient

sys.path.append('..')
from time_utils import getMarketHours
from data.finvizConsolidateRecentGainers import gather_tickers as gather_recent_gainers


class AnchorData(TypedDict):
    yesterday_close: float
    avg_volume_20_days: float
    closed_above_upperBand: bool
    avg_range_20_days: float
    
AnchorDataDict = Dict[str, AnchorData]

class AlertData(TypedDict):
    pct_gap_up: str
    pct_current_bar_up: str
    pct_volume_up: str
    
AlertDataDict = Dict[str, AlertData]

def createAlertDataPrintLine(ticker: str, data: AlertData) -> str:
    return f"{ticker}: GAP {data['pct_gap_up']}, BAR {data['pct_current_bar_up']}, VOL {data['pct_volume_up']}"

def getFormattedPercent(numerator: float, denominator: float) -> str:
    return f"{(numerator / denominator) * 100:.2f}%"

def isUp(higherPrice: float, lowerPrice: float) -> Tuple[bool, str]:
    return higherPrice > lowerPrice, getFormattedPercent(higherPrice - lowerPrice, lowerPrice)

def isVolumeSpike(currentVolume: float, avg_volume_20_days: float, minuteToCheck: int) -> Tuple[bool, str]:
    if minuteToCheck == 1:
        return currentVolume > avg_volume_20_days / 12, getFormattedPercent(currentVolume, avg_volume_20_days)
    elif minuteToCheck == 2:
        return currentVolume > avg_volume_20_days / 10, getFormattedPercent(currentVolume, avg_volume_20_days)
    elif minuteToCheck == 5:
        return currentVolume > avg_volume_20_days / 8, getFormattedPercent(currentVolume, avg_volume_20_days)
    elif minuteToCheck == 15:
        return currentVolume > avg_volume_20_days / 7, getFormattedPercent(currentVolume, avg_volume_20_days)
    elif minuteToCheck == 30:
        return currentVolume > avg_volume_20_days / 7, getFormattedPercent(currentVolume, avg_volume_20_days)
    else:
        return False, 'N/A'

def fetch_and_check(ibt: IbkrClient, anchorData: AnchorDataDict, minuteToCheck: int) -> None:
    if minuteToCheck == 1: 
        ibFormatBar = '1 min'
    else:
        ibFormatBar = str(minuteToCheck) + ' mins'
    
    tickersToAlert: AlertDataDict = {}
    extendedTickers: AlertDataDict = {}
    for ticker, data in anchorData.items():
        try:
            yesterdayClose = data['yesterday_close']
            avg20dayVolume = data['avg_volume_20_days']
            isLikelyExtended = data['closed_above_upperBand']
            
            df = ibt.getStockData(ticker, None, ibFormatBar, '1 D', 'ADJUSTED_LAST')
            # use the second to last bar because otherwise the fetch will data for return the current bar that isn't closed yet
            currentVolume = df['volume'].iloc[-2]
            openPrice = df['open'].iloc[-2]
            closePrice = df['close'].iloc[-2]
            
            isGapUp, pctGapUp = isUp(openPrice, yesterdayClose)
            isCurrentBarUp, pctCurrentBarUp = isUp(closePrice, openPrice)
            isSuperVolume, pctVolumeUp = isVolumeSpike(currentVolume, avg20dayVolume, minuteToCheck)
            
            if VERBOSE: print('ticker: ', ticker, 'currentVolume: ', currentVolume, 'avg20dayVolume: ', avg20dayVolume,
                  'openPrice: ', openPrice, 'closePrice: ', closePrice, 'yesterdayClose: ', yesterdayClose,
                  'isGapUp: ', isGapUp, 'isCurrentBarUp: ', isCurrentBarUp, 'isSuperVolume: ', isSuperVolume)
            
            meetsBreakoutCriteria = isGapUp and isCurrentBarUp and isSuperVolume
            
            if meetsBreakoutCriteria:
                if not isLikelyExtended:
                    tickersToAlert[ticker] = {
                        'pct_gap_up': pctGapUp,
                        'pct_current_bar_up': pctCurrentBarUp,
                        'pct_volume_up': pctVolumeUp
                    }
                else:
                    extendedTickers[ticker] = {
                        'pct_gap_up': pctGapUp,
                        'pct_current_bar_up': pctCurrentBarUp,
                        'pct_volume_up': pctVolumeUp
                    }
            
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
    
    if len(extendedTickers) > 0:
        print(f"\nALERT: {minuteToCheck} minute bar, likely extended:\n\t", ",\n\t".join([createAlertDataPrintLine(ticker, data) for ticker, data in extendedTickers.items()]))
    else:
        print(f"\nNo extended alerts for {minuteToCheck} minute bar")
            
    if len(tickersToAlert) > 0:
        print(f"\nALERT: {minuteToCheck} minute bar:\n\t", ",\n\t".join([createAlertDataPrintLine(ticker, data) for ticker, data in tickersToAlert.items()]))
    else:
        print(f"\nNo alerts for {minuteToCheck} minute bar\n")
        
    return

def get_anchor_data(ibt: IbkrClient, tickers: [str]) -> AnchorDataDict:
    anchorData: AnchorDataDict = {}
    for ticker in tickers:
        try:
            df = ibt.getStockData(ticker, None, '1 day', '20 D', 'ADJUSTED_LAST')
            
            yesterday_close = df['close'].iloc[-1]
            volume_avg = df['volume'].mean()
            avg_range_20_days = (df['high'] - df['low']).mean()
            upperBandValue = (df['close'].rolling(window=20).mean() + 3 * avg_range_20_days).iloc[-1]
            closed_above_upperBand, _ = isUp(yesterday_close, upperBandValue)
            
            anchorData[ticker] = {
                'yesterday_close': yesterday_close,
                'avg_volume_20_days': volume_avg,
                'closed_above_upperBand': closed_above_upperBand,
                'avg_range_20_days': avg_range_20_days
            }
        except Exception as e:
            print(f"\nError fetching data for {ticker}: {e}")
    
    return anchorData

def main():
    [marketOpen, _] = getMarketHours()
    
    ib = IB()
    ibt = IbkrClient(ib, logFilepath='System', verbose=True)
    try:
        ibt.connectClient(port=7496)
        
        if not TEST_MODE:
            tickers = gather_recent_gainers()
        else:
            tickers = ['LMND', 'BROS', 'SOFI', 'AAPL', 'TSLA']
        
        anchorData = get_anchor_data(ibt, tickers)
        
        if VERBOSE: print('anchorData: \n', anchorData)
        
        isMinuteCheckedMap = {
            1: False,
            2: False,
            5: False,
            15: False,
            30: False
        }
        
        while True and not TEST_MODE:
            now = datetime.now()
            isHourOfMarketOpen = now.hour == marketOpen.hour
            
            if isHourOfMarketOpen:
                for minuteToCheck in [1, 2, 5, 15, 30]:
                    if now.minute == marketOpen.minute + minuteToCheck and not isMinuteCheckedMap[minuteToCheck]:
                        fetch_and_check(ibt, anchorData, minuteToCheck)
                        isMinuteCheckedMap[minuteToCheck] = True
                        continue
                
                if VERBOSE: print("\nwaiting for a minute: ", now)
                time.sleep(60)
                
            else:
                print("\nNot hour of market open, exiting: ", now)
                ibt.disconnectClient()
                break
            
        if TEST_MODE:
            fetch_and_check(ibt, anchorData, 15)
            
    finally:
        print("Disconnecting IB Client")
        ibt.disconnectClient()
    
    return

if __name__ == "__main__":
    VERBOSE = True
    TEST_MODE = False
    main()
    