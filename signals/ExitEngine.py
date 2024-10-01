
from enums import TradeDirection, MarketSentiment, ExitMethod
from talib import ATR, EMA, RSI, SMA
import logging


class ExitEngine(object):
    def __init__(self, strategyName, df, exitVars, tradeDirection=None, verbose=False, simulation=False):
        self.logger = logging.getLogger(strategyName)
        self.df = df
        self.exitVars = exitVars
        self.tradeDirection = tradeDirection
        self.verbose = verbose
        self.simulation = simulation

        self.useProfitTarget = exitVars['profit_target']['use']
        self.profitTargetSignal = None

        self.isExit = self.exitVars['initial_stop']
        self.useInitialStop = self.isExit['use']
        self.initialStopSignal = None
        self.initialStopDistance = None
        self.initialStopPrice = None

        self.tsExit = self.exitVars['trailing_stop']
        self.useTrailingStop = self.tsExit['use']
        self.trailingStopSignal = None
        self.trailingStopDistance = None
        self.trailingStopPrice = None

        self.useTimeStop = exitVars['time_stop']['use']
        self.timeStopSignal = None

        self.useProfitableCloses = exitVars['profitable_closes']['use']
        self.profitableClosesSignal = None

        self.useTechnicalCondition = exitVars['technical_condition']['use']
        self.tcExits = exitVars['technical_condition']['conditions']
        self.technicalConditionSignal = None

        if self.useProfitTarget or self.useTimeStop or self.useProfitableCloses:
            raise Exception(
                'ExitEngine using exit type that is not yet supported!')

        if self.useProfitTarget and not self.useInitialStop:
            raise Exception('must useInitialStop to useProfitTarget')

        self.calculateRisk = 'trailingStop'
        if self.isExit['calculateRisk']:
            self.calculateRisk = 'initialStop'
        if self.tsExit['calculateRisk']:
            self.calculateRisk = 'trailingStop'

        self.brokerStopDistance = None

    def getSystemExits(self):
        """
        Check for exits that this system will manage & execute
        """
        if self.useTechnicalCondition:
            for condition in self.tcExits:
                print('\nchecking technical exit condition: ', condition)

                if condition['systemOrBroker'] == 'system':
                    if condition['type'] == ExitMethod.EMA_PRICE_CROSS.name or\
                        condition['type'] == ExitMethod.SMA_PRICE_CROSS.name:
                        print('checking MA Price Cross exit, ', condition['type'])
                        parameter = int(condition['parameter'])
                        
                        if condition['type'] == ExitMethod.EMA_PRICE_CROSS.name:
                            ma = EMA(self.df.close, timeperiod=parameter)[-1]
                            
                        elif condition['type'] == ExitMethod.SMA_PRICE_CROSS.name:
                            ma = SMA(self.df.close, timeperiod=parameter)[-1]
                            
                        else:
                            print('MA type not supported!')
                            
                        close = self.df.close[-1]
                        print('ma & close: ', ma, close)
                        
                        if self.tradeDirection == TradeDirection.SHORT.name and close > ma:
                            self.technicalConditionSignal = MarketSentiment.BULLISH.name

                        if self.tradeDirection == TradeDirection.LONG.name and close < ma:
                            self.technicalConditionSignal = MarketSentiment.BEARISH.name

                    if condition['type'] == ExitMethod.DONCHIAN_CHANNEL_BREAKOUT.name:
                        print('checking DONCHIAN_CHANNEL_BREAKOUT exit')
                        parameter = int(condition['parameter'])
                        close = self.df.close[-1]
                        highestClose = self.df.close[-parameter:].max()
                        lowestClose = self.df.close[-parameter:].min()
                        print('close, highestClose, lowestClose: ', close, highestClose, lowestClose)
                        
                        if self.tradeDirection == TradeDirection.SHORT.name and close >= highestClose:
                            self.technicalConditionSignal = MarketSentiment.BULLISH.name

                        if self.tradeDirection == TradeDirection.LONG.name and close <= lowestClose:
                            self.technicalConditionSignal = MarketSentiment.BEARISH.name
                            
                    if condition['type'] == ExitMethod.KELTNER_CHANNEL_BREAKOUT.name:
                        print('checking KELTNER_CHANNEL_BREAKOUT exit')
                        channelLength = int(condition['channelLength'])
                        atrParameter = int(condition['atrParameter'])
                        atrMultiplier = int(condition['atrMultiplier'])
                        close = self.df.close.values[-1]
                        atrSeries = ATR(self.df.high, self.df.low, self.df.close, timeperiod=atrParameter) * atrMultiplier
                        middleBand = EMA(self.df.close, timeperiod=channelLength)
                        upperBand = middleBand + atrSeries
                        upperBandValue = upperBand.values[-1]
                        lowerBand = middleBand - atrSeries
                        lowerBandValue = lowerBand.values[-1]
                        
                        print('close, lowerBandValue, upperBandValue: ', close, lowerBandValue, upperBandValue)
                        
                        if self.tradeDirection == TradeDirection.LONG.name and close <= lowerBandValue:
                            self.technicalConditionSignal = MarketSentiment.BEARISH.name
                        
                        if self.tradeDirection == TradeDirection.SHORT.name and close >= upperBandValue:
                            self.technicalConditionSignal = MarketSentiment.BULLISH.name
                            
                    if condition['type'] == ExitMethod.RSI_THRESHOLD.name:
                        print('checking RSI_THRESHOLD exit')
                        rsiLength = int(condition['parameter'])
                        rsiThreshold = int(condition['threshold'])
                        rsi = RSI(self.df.close, timeperiod=rsiLength).values[-1]
                        
                        if self.tradeDirection == TradeDirection.LONG.name and rsi >= rsiThreshold:
                            self.technicalConditionSignal = MarketSentiment.BEARISH.name
                            
                        if self.tradeDirection == TradeDirection.SHORT.name and rsi <= rsiThreshold:
                            self.technicalConditionSignal = MarketSentiment.BULLISH.name
                        

        if self.useTrailingStop and self.tsExit['systemOrBroker'] == 'system':
            print('chkpt useTrailingStop system exit entry')
            if self.tsExit['type'] == ExitMethod.ATR.name:
                parameter = int(self.tsExit['atr_parameter'])
                atr = ATR(self.df.high, self.df.low, self.df.close,
                          timeperiod=parameter)[-1]
                atrMult = float(self.tsExit['atr_multiple'])
                self.trailingStopDistance = round(atr * atrMult, 2)

                reportString = '\nuseTrailingStop ATR on broker' \
                    + '\n\tatr_parameter:  '+str(parameter) \
                    + '\n\tatr_multiple:   '+str(atrMult) \
                    + '\n\tATR:                    '+str(atr) \
                    + '\n\ttrailingStopDistance:   ' \
                    + str(self.trailingStopDistance)

                if self.verbose:
                    print(reportString)

                self.logger.debug(reportString)

        return

    def getBrokerExits(self):
        """
        Check for exits that can be sent to the broker upon trade initialization
        """
        if self.useProfitTarget:
            raise Exception('profit target not yet implemented!')
            self.profitTargetSignal = None
            # TODO finish profitTarget implementation here
            #rMultipleProfit = exitVars['profit_target']['profit_r_multiple']
            # if rMultipleProfit:
            #    profitDist = round( stopDist * float( rMultipleProfit ), 2)

        if self.useTrailingStop:
            if self.tsExit['type'] == ExitMethod.ATR.name:
                timeperiod = int(self.tsExit['atr_parameter'])
                atr = ATR(self.df.high, self.df.low, self.df.close,
                          timeperiod=timeperiod)[-1]
                atrMult = float(self.tsExit['atr_multiple'])
                self.trailingStopDistance = round(atr * atrMult, 2)
                
                if self.tradeDirection == TradeDirection.LONG.name:
                    self.trailingStopPrice = self.df.close.values[-1] - self.trailingStopDistance
                    
                if self.tradeDirection == TradeDirection.SHORT.name:
                    self.trailingStopPrice = self.df.close.values[-1] + self.trailingStopDistance

                reportString = '\nuseTrailingStop ATR' \
                    + '\n\tatr_parameter:  '+str(timeperiod) \
                    + '\n\tatr_multiple:   '+str(atrMult) \
                    + '\n\tATR:                  '+str(atr) \
                    + '\n\ttrailingStopDistance: ' \
                    + str(self.trailingStopDistance)\
                    + '\n\ttrailingStopPrice: '+str(self.trailingStopPrice)

                if self.verbose:
                    print(reportString)

                self.logger.debug(reportString)

        if self.useInitialStop:
            if self.isExit['type'] == ExitMethod.ATR.name:
                timeperiod = int(self.isExit['atr_parameter'])
                atr = ATR(self.df.high, self.df.low, self.df.close,
                          timeperiod=timeperiod)[-1]
                atrMult = float(self.isExit['atr_multiple'])
                self.initialStopDistance = round(atr * atrMult, 2)
                
                if self.tradeDirection == TradeDirection.LONG.name:
                    self.initialStopPrice = self.df.close.values[-1] - self.initialStopDistance
                    
                if self.tradeDirection == TradeDirection.SHORT.name:
                    self.initialStopPrice = self.df.close.values[-1] + self.initialStopDistance

                reportString = '\nuseInitialStop ATR' \
                    + '\n\tatr_parameter:  '+str(timeperiod) \
                    + '\n\tatr_multiple:   '+str(atrMult) \
                    + '\n\tATR:                 '+str(atr) \
                    + '\n\tinitialStopDistance: ' \
                    + str(self.initialStopDistance)\
                    + '\n\tinitialStopPrice: '+str(self.initialStopPrice)

                if self.verbose:
                    print(reportString)

                self.logger.debug(reportString)

        if self.isExit['systemOrBroker'] == 'broker':
            self.brokerStopDistance = self.initialStopDistance

        if self.tsExit['systemOrBroker'] == 'broker':
            self.brokerStopDistance = self.trailingStopDistance

        if self.brokerStopDistance == None:
            errorString = 'could not set broker stop distance'
            self.logger.error(errorString)
            raise Exception(errorString)

        return