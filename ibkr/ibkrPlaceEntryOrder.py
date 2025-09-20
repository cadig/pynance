#
# This function will place an order to IBKR based on the input parameters
# args will be provided via command line, and will be passed to the function
# Args: ticker, minuteToUse
#
from configparser import ConfigParser
from ib_insync import IB, Stock
from math import floor
import sys
sys.path.append('../..')
from ibkr.IbkrTrader import IbkrTrader as IbkrClient
from ibkr.orders.bracketLimitOrderWithStopLoss import bracketLimitOrderWithStopLoss
# from moneymanagement.StocksMoneyManager import StocksMoneyManager as SMM

def get_ibkr_account_id(whichAccount: str) -> str:
    config = ConfigParser()
    config.read('../../../config/ibkr-config.ini')
    return config.get(whichAccount, 'accountId')

def get_number_of_shares(dollarsToRisk: float, buyLimitPrice: float, stopLossPrice: float) -> int:
    priceLossDistance = buyLimitPrice - stopLossPrice
    return floor( dollarsToRisk / priceLossDistance )

def main():
    args = sys.argv[1:]
    ticker = args[0]
    minuteToUse = int(args[1])
    dollarsToRisk = int(args[2])
    numStaggeredStops = int(args[3])
    
    ibAccId = get_ibkr_account_id('margin')
    
    # check that args are valid
    if minuteToUse not in [1, 2, 5, 15]:
        print('minuteToUse must be one of [1, 2, 5, 15]')
        return
    
    if dollarsToRisk < 1:
        print('dollarsToRisk must be greater than 0')
        return
    
    if numStaggeredStops == 0 or not numStaggeredStops: numStaggeredStops = 1
    
    # round dollarsToRisk to an integer
    dollarsToRisk = floor(dollarsToRisk)
    
    ibFormatBar = str(minuteToUse) + ' mins'
    if minuteToUse == 1: ibFormatBar = '1 min'
    
    ib = IB()
    ibt = IbkrClient(ib, logFilepath='System', verbose=True)
    try:
        ibt.connectClient(port=7496)
        
        # TODO: calc % of account instead of dollarsToRisk - accNetLiq = ibt.getIbAccountNetLiquidation(ibAccId)
        
        df = ibt.getStockData(ticker, None, ibFormatBar, '1 D', 'ADJUSTED_LAST')
        
        # Check if we have enough data
        if df.empty:
            print(f'Error: No data received for {ticker}')
            return
        
        if len(df) < 2:
            print(f'Error: Insufficient data for {ticker}. Need at least 2 rows, got {len(df)}')
            return
        
        print('row: ', df.iloc[-2])
        
        prevHigh = round(df['high'].iloc[-2], 2)
        prevLow = round(df['low'].iloc[-2], 2)
        
        buyLimitPrice = prevHigh + 0.10
        stopLossPrice = prevLow - 0.10
        
        numSharesToBuy = get_number_of_shares(dollarsToRisk, buyLimitPrice, stopLossPrice)
        
        numSharesPerOrder = floor(numSharesToBuy / numStaggeredStops)
        
        bracketOrderToPlace = bracketLimitOrderWithStopLoss(
            accountId=ibAccId,
            parentOrderId=ib.client.getReqId(),
            tif='DAY',
            action='BUY', 
            quantity=numSharesPerOrder,
            limitPrice=buyLimitPrice,
            stopLossPrice=stopLossPrice
        )
        
        contract = Stock(ticker,'SMART','USD')
        ib.qualifyContracts(contract)
        
        for subOrder in bracketOrderToPlace:
            print('Placing order: ', subOrder)
            ib.placeOrder(contract, subOrder)
    
        # smn = SMM(0.0001)
        # [numShares, hasEnoughCash] = smn.getStockPositionSizing(10_000, 10, 100)
        # print('numShares: ', numShares)
        # print('hasEnoughCash: ', hasEnoughCash)
        
        
    finally:
        ibt.disconnectClient()

    return

if __name__ == "__main__":
    main()
