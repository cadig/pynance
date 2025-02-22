import logging
from random import randint
from ib_insync import util, ContFuture, Stock
from math import floor

from .enums import IB_AssetClass
from . import formatIbDataframe

class IbkrTrader(object):
    def __init__(self, ib, logFilepath, verbose=False):
        self.ib = ib
        self.logger = logging.getLogger(logFilepath)
        self.verbose = verbose
        self.clientId = randint(0,9999)
        
    def connectClient(self, port=4001):
        if not self.ib.isConnected():
            self.ib.connect('127.0.0.1', port, clientId=self.clientId)
            self.logger.info('ib client id '+str(self.clientId)+' connected')
            
        return
    
    def disconnectClient(self):
        self.ib.disconnect()
        
        if self.ib.isConnected():
            self.logger.error('ib disconnect failed, client is still connected')
        else:
            self.logger.info('ib client disconnected')
        return
    
    def getQualifiedContract(self, instrument, assetClass):
        if assetClass == IB_AssetClass.ContFuture.name or assetClass == IB_AssetClass.ContFuture.value:
            contract = ContFuture(instrument)
            
        elif assetClass == IB_AssetClass.STK.name or assetClass == IB_AssetClass.STK.value:
            contract = Stock(instrument, exchange='SMART', currency='USD')
            
        else:
            raise Exception(assetClass+' not yet supported')
            
        self.ib.qualifyContracts(contract)
        
        return contract
        
        
    def placeBracketOrder(self, instrument, buyOrSell, quantity, 
                          limitPrice=None, takeProfitPrice=None, 
                          stopLossPrice=None):
        contract = ContFuture(instrument)
        bracket_order = self.ib.bracketOrder(
            contract,
            buyOrSell, # 'BUY' or 'SELL'
            quantity,
            limitPrice=limitPrice,
            takeProfitPrice=takeProfitPrice,
            stopLossPrice=stopLossPrice
        )
        
        # multiple orders contained in bracket order, so loop to execute
        for order in bracket_order:
            self.ib.placeOrder(contract, order)
            
        return
    
    def getContFutureData(self, instrument, ibGranularity, durationStr, whatToShow):
        contract = ContFuture(instrument)
        bars = self.ib.reqHistoricalData(
            contract, endDateTime='', durationStr=durationStr,
            barSizeSetting=ibGranularity, whatToShow=whatToShow, 
            keepUpToDate=False, useRTH=True, timeout=2)
        return util.df(bars)
    
    def getStockData(self, instrument: str, primaryExchange: str, ibGranularity: str, 
                     durationStr: str, whatToShow: str, endDateTime: str = ''):
        # TODO - better systemetize these rules instead of hardcoding
        # primaryExchange=None
        if instrument == 'BRK.B':
            instrument='BRK B'
            primaryExchange='NYSE'
        elif instrument == 'BF.B':
            instrument='BF B'
        elif instrument=='CAT':
            primaryExchange='NYSE'
        elif instrument=='CSCO':
            primaryExchange='NASDAQ'
        elif instrument=='FANG':
            primaryExchange='NASDAQ'
        elif instrument=='KEYS':
            primaryExchange='NYSE'
        elif instrument=='WELL':
            primaryExchange='NYSE'
        elif instrument=='LGF-A':
            instrument = 'LGF A'
        elif instrument=='LGF-B':
            instrument = 'LGF B'
            
        if primaryExchange is None:
            contract = Stock(instrument, exchange='SMART', currency='USD')
            # TODO: can use qualifyContracts here?
        else:
            contract = Stock(instrument, exchange='SMART', currency='USD', 
                             primaryExchange=primaryExchange)

        bars = self.ib.reqHistoricalData(
            contract, endDateTime=endDateTime, durationStr=durationStr,
            barSizeSetting=ibGranularity, whatToShow=whatToShow, 
            keepUpToDate=False, useRTH=True, timeout=2)
        
        return util.df(bars)
    
    def checkSymbolPositions(self, symbol, accList):
        symbolPositions = []
        for acc in accList:
            accId = acc['account_identifier']
            positions = self.ib.positions(accId)
            # append another array because otherwise a memory location is returned, 
            # ex: <generator object IbTrader.checkSymbolPositions.<locals>.<genexpr> at 0x7f8c98e63f50>
            symbolPositions.append(
                [i for i in positions if i.contract.symbol == symbol]
            )
        return symbolPositions
    
    def getIbAccountNetLiquidation(self, ibAccId):
        accountSummary = self.ib.accountSummary(ibAccId)
        
        print('\naccountSummary for '+ibAccId)
        print(accountSummary)
        
        return [i.value for i in accountSummary if i.tag == 'NetLiquidation'][0]
    
    def getAllAccountPositions(self, account):
        symbolPositions = []
        accId = account['account_identifier']
        symbolPositions.append(i for i in self.ib.positions(accId))
        return self.ib.positions(accId) # symbolPositions[0]
    
    def getTargetDollarRisk(self, accountList, targetRiskPercentage):
        accountValues = []
        for acc in accountList:
            accId = acc['account_identifier']
            pctAllocation = float( acc['pct_allocation'] )
            #
            # TODO - maybe should not always assume only one netLiquidation value?
            #   perhaps remove [0] and check if len > 1 first?
            netLiquidation = self.getIbAccountNetLiquidation(accId)
            
            allocatedValue = pctAllocation * float( netLiquidation ) 
            #
            # TODO may need to also check AvailableFunds, BuyingPower ?
            #   calculate/check margin needed & available for the trade
            maxDollarRisk = round( allocatedValue * targetRiskPercentage, 2)
            accountValues.append(
                {
                    'account': accId,
                    'dollarRisk': maxDollarRisk
                } 
            )
            
            if self.verbose:
                print('\nib_utils.getTargetDollarRisk(): '
                      +'\n\taccId:          '+str(accId)
                      +'\n\tpctAllocation:  '+str(pctAllocation)
                      +'\n\tnetLiquidation: '+str(netLiquidation)
                      +'\n\tallocatedValue: '+str(allocatedValue)
                      +'\n\ttargetRisk:     '+str(targetRiskPercentage)
                      +'\n\tmaxDollarRisk:  '+str(maxDollarRisk)
                )
        #
        # TODO: above - maybe JSON value needs to be cast to string bc
        #   it does not capture float values? throws off rounding?
        #
        return accountValues

    def getContFuturePositionUnits(self, accountList,
            stopDistance, targetRiskPercentage, tickIncrement, tickSize):
        #
        # 1. CONTRACT SIZE
        # round up to next multiple of tickIncremnt
        stopDistRounded = stopDistance if stopDistance % tickIncrement == 0 \
            else stopDistance + tickIncrement - stopDistance % tickIncrement
            
        contractDollarRisk = stopDistRounded * tickSize
        #
        #
        # 2. NUMBER OF CONTRACTS PER MANAGED ACCOUNT
        accountValues = self.getTargetDollarRisk(
            accountList, targetRiskPercentage)
        
        for acc in accountValues:
            numContracts = floor( acc['dollarRisk'] / contractDollarRisk )
            
            reportString = '\nib_utils.getContFuturePositionUnits(): ' \
                      +'\n\tstopDistance:         '+str(stopDistance) \
                      +'\n\ttargetRiskPercentage: '+str(targetRiskPercentage*100) \
                      +'\n\ttickIncrement:        '+str(tickIncrement) \
                      +'\n\ttickSize:             '+str(tickSize) \
                      +'\n\taccountValues: '+str(accountValues) \
                      +'\n\tstopDistRounded:    '+str(stopDistRounded) \
                      +'\n\tcontractDollarRisk: '+str(contractDollarRisk) \
                      +'\n\tnumContracts:       '+str(numContracts)
            
            self.logger.debug(reportString)
            if self.verbose:
                print(reportString)
                
            if numContracts < 1:
                minOverrideBool = [a for a in accountList if a['account_identifier'] \
                           == acc['account'] ][0]['min_contract_override']
                
                if minOverrideBool:
                    numContracts = 1
                    
                else:
                    notEnoughString = 'Account '+str(acc['account']) \
                                    +' does not have enough capital or risk to trade 1 contract'
                    if self.verbose:
                        print('\n'+notEnoughString)
                    raise Exception(notEnoughString)
                    continue
            
            acc['numContracts'] = numContracts
            
        return accountValues
    
    def getInstrumentData(self, instrumentInfo, formattedGranularity):
        """
        Parameters
        ----------
        instrumentInfo : TYPE
            DESCRIPTION.
        formattedGranularity : TYPE
            DESCRIPTION.

        Raises
        ------
        Exception
            DESCRIPTION.
        ex
            DESCRIPTION.

        Returns
        -------
        df : TYPE
            DESCRIPTION.

        """
        instrument = instrumentInfo['instrument']
        assetClass = instrumentInfo['asset_class']
        
        if assetClass == 'ContFuture':
            # TODO seems like futures that expire soon cause ContFuture to fail,
            # -- on 2/22/23, MBT 2/24/23 contract data is not getting returned
            df = self.getContFutureData(
                instrument, formattedGranularity, '6 M', 'MIDPOINT'
            )
                
        elif assetClass == 'STK':
            df = self.getStockData(
                instrument, None, formattedGranularity, '1 Y', 'MIDPOINT'
            )
        else:
            raise Exception(
                assetClass+' asset class not yet supported, could not retrieve data'
            )
                
        if df is None:
            raise Exception(str(instrument)+' failed to retrieve market data, returned None')
             
        try:
            df = formatIbDataframe(df, formattedGranularity)
        except Exception as ex:
            self.logger.error('error formatting data')
            raise ex
                
        return df