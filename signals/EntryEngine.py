from enums import TradeDirection, TrendDirection, EntryMethod, FilterType
from indicators import KAMA
from talib import EMA, SMA, MAX, MIN, ROC, ATR, RSI
import logging

class EntryEngine(object):
    def __init__(self, strategyName, df, entryVars, verbose=False,
                 trendBias=None, tradableSpread=None, simulation=False):
        self.df = df
        self.logger = logging.getLogger(strategyName)
        self.entryMethod = entryVars['method']
        self.filterType = entryVars['filter_type']
        self.filterParameter = entryVars['filter_parameter']
        self.kwargs = entryVars['kwargs']
        self.verbose = verbose
        self.trendBias = trendBias
        self.tradableSpread = tradableSpread
        self.simulation = simulation
        self.trendDirection = None
        self.signal = None

    def run(self):

        try:
            print('getTrendDirection entry')
            self.getTrendDirection()
        except Exception as ex:
            raise Exception(
                'EntryEngine.getTrendDirection exception: \n'+str(ex)
                + '\ncurrent trendDirection set: '+str(self.trendDirection)
            )

        if self.entryMethod == EntryMethod.HOURLY_CORNFLOWER.name:
            self.hourlyCornflower()
        elif self.entryMethod == EntryMethod.WEEKLY_TREND_TRADER.name:
            self.weeklyTrendTrader()
        elif self.entryMethod == EntryMethod.DONCHIAN_CHANNEL_BREAKOUT.name:
            self.donchianChannelBreakout()
        elif self.entryMethod == EntryMethod.KELTNER_CHANNEL_BREAKOUT.name:
            self.keltnerChannelBreakout()
        elif self.entryMethod == EntryMethod.RSI_PULLBACK.name:
            self.rsiPullback()
        elif self.entryMethod == EntryMethod.SMA_PRICE_CROSS.name:
            self.smaPriceCross()
        else:
            raise Exception(str(self.entryMethod)+' entryMethod not supported')

        return
        

    def getTrendDirection(self):
        if self.filterType == FilterType.EMA.name:
            close = self.df.close[-1]
            ema = EMA(
                self.df.close, timeperiod=int(self.filterParameter)
            )[-1]

            if close > ema:
                self.trendDirection = TrendDirection.UP.name
            if ema > close:
                self.trendDirection = TrendDirection.DOWN.name
                
        if self.filterType == FilterType.SMA.name:
            close = self.df.close[-1]
            sma = SMA(
                self.df.close, timeperiod=int(self.filterParameter)
            )[-1]
            
            if close > sma:
                self.trendDirection = TrendDirection.UP.name
            if sma < close:
                self.trendDirection = TrendDirection.DOWN.name

        if self.verbose:
            print('EntryEngine.getTrendDirection returning '
                  + str(self.trendDirection)
                  )

        return

    def hourlyCornflower(self):
        if not self.simulation:
            H1Close = self.df.close[-1]
            H1EMA8 = EMA(self.df.close, timeperiod=8)[-1]
            H1EMA12 = EMA(self.df.close, timeperiod=12)[-1]
            H1EMA24 = EMA(self.df.close, timeperiod=24)[-1]
            H1EMA72 = EMA(self.df.close, timeperiod=72)[-1]
            LONGBO = (H1Close == self.df.close[-8:].max())
            SHORTBO = (H1Close == self.df.close[-8:].min())
        else:
            raise Exception(self.entryMethod, ' simulation not yet supported')
            return

        if self.trendBias != TradeDirection.SHORT.name and self.tradableSpread != False \
                and H1EMA8 > H1EMA12 and H1EMA12 > H1EMA24 and H1EMA24 > H1EMA72 \
                and H1Close > H1EMA24 and LONGBO == True:
            if self.verbose:
                print('LONG entry signal: ', H1Close, H1EMA8,
                      H1EMA12, H1EMA24, H1EMA72, LONGBO)

            self.signal = TradeDirection.LONG.name

        elif self.trendBias != TradeDirection.LONG.name and self.tradableSpread != False \
                and H1EMA8 < H1EMA12 and H1EMA12 < H1EMA24 and H1EMA24 < H1EMA72 \
                and H1Close < H1EMA24 and SHORTBO == True:
            if self.verbose:
                print('SHORT entry signal: ', H1Close, H1EMA8,
                      H1EMA12, H1EMA24, H1EMA72, SHORTBO)

            self.signal = TradeDirection.SHORT.name

        return

    def hourlyKamaCross(self, slowKama, fastKama):
        if not self.simulation:
            close = self.df.close[-1]
            # TODO does this return a series or a data point?
            slowMa = KAMA(self.df.close, 10, slowKama, 30)
            fastMa = KAMA(self.df.close, 10, fastKama, 30)
        else:
            raise Exception(self.entryMethod, ' simulation not yet supported')

        if self.trendBias != TradeDirection.SHORT.name and self.tradableSpread != False \
                and close > slowMa and slowMa > fastMa:
            if self.verbose:
                print('LONG entry signal: ', close, slowMa, fastMa)

            self.signal = TradeDirection.LONG.name

        elif self.trendBias != TradeDirection.LONG.name and self.tradableSpread != False \
                and close < slowMa and slowMa < fastMa:
            if self.verbose:
                print('SHORT entry signal: ', close, slowMa, fastMa)

            self.signal = TradeDirection.SHORT.name

        return

    def donchianChannelBreakout(self):
        """
        Highest or lowest close of the last `channelLength` bars.
        """

        # TODO add check that kwargs includes specifically channelLength parameters
        if len(self.kwargs) == 0:
            raise Exception(self.entryMethod+' must have channelLength kwarg')

        channelLength = self.kwargs[0]['channelLength']
        if not self.simulation:
            #high = self.df.high[-1]
            #highestHigh = MAX(self.df.high, timeperiod=channelLength)[-1]
            #low = self.df.low[-1]
            #lowestLow = MIN(self.df.low, timeperiod=channelLength)[-1]
            close = self.df.close[-1]
            highestClose = MAX(self.df.close, timeperiod=channelLength)[-1]
            lowestClose = MIN(self.df.close, timeperiod=channelLength)[-1]
            # TODO: middle band is average of upper & lower bands, if needed
        else:
            raise Exception(self.entryMethod+' simulation not yet supported')

        signalVerified = False
        if self.trendBias != TradeDirection.SHORT.name and self.tradableSpread != False \
                and close >= highestClose:
            signalVerified = True

            if self.filterType and self.trendDirection != TrendDirection.UP.name:
                signalVerified = False

            if signalVerified:
                if self.verbose:
                    print('LONG entry signal')

                self.signal = TradeDirection.LONG.name

        elif self.trendBias != TradeDirection.LONG.name and self.tradableSpread != False \
                and close <= lowestClose:
            signalVerified = True

            if self.filterType and self.trendDirection != TrendDirection.DOWN.name:
                signalVerified = False

            if signalVerified:
                if self.verbose:
                    print('SHORT entry signal')

                self.signal = TradeDirection.SHORT.name

        time = self.df.time[-1]
        reportString = '\n'+self.entryMethod+' channelLength: '+str(channelLength) \
            + '\n\ttime:         '+str(time) \
            + '\n\tclose:        '+str(close) \
            + '\n\thighestClose: '+str(highestClose) \
            + '\n\tlowestClose:  '+str(lowestClose) \
            + '\n\tfilterType:  '+str(self.filterType) \
            + '\n\ttrendDirection:  '+str(self.trendDirection) \
            + '\n\tSIGNAL:          '+str(self.signal) \
            #+ '\n\thigh:         '+str(high) \
            #+ '\n\thighestHigh:  '+str(highestHigh) \
            #+ '\n\tlow:          '+str(low) \
            #+ '\n\tlowestLow:    '+str(lowestLow) \
            #+ '\n\tincludeClose: '+str(includeClose) \

        if self.verbose:
            print(reportString)

        self.logger.debug(reportString)

        return
    
    def keltnerChannelBreakout(self):
        # TODO add check that kwargs includes specifically the required parameters
        if len(self.kwargs) == 0:
            raise Exception(self.entryMethod+' must have channelLength, atrParameter, and atrMultiplier kwargs')

        channelLength = self.kwargs[0]['channelLength']
        atrParameter = self.kwargs[0]['atrParameter']
        atrMultiplier = self.kwargs[0]['atrMultiplier']
        if not self.simulation:
            close = self.df.close.values[-1]
            atrSeries = ATR(self.df.high, self.df.low, self.df.close, timeperiod=atrParameter) * atrMultiplier
            middleBand = EMA(self.df.close, timeperiod=channelLength)
            upperBand = middleBand + atrSeries
            upperBandValue = upperBand.values[-1]
            lowerBand = middleBand - atrSeries
            lowerBandValue = lowerBand.values[-1]
        else:
            raise Exception(self.entryMethod+' simulation not yet supported')

        signalVerified = False
        if self.trendBias != TradeDirection.SHORT.name and self.tradableSpread != False \
                and close >= upperBandValue:
            signalVerified = True

            if self.filterType and self.trendDirection != TrendDirection.UP.name:
                signalVerified = False

            if signalVerified:
                if self.verbose:
                    print('LONG entry signal')

                self.signal = TradeDirection.LONG.name

        elif self.trendBias != TradeDirection.LONG.name and self.tradableSpread != False \
                and close <= lowerBandValue:
            signalVerified = True

            if self.filterType and self.trendDirection != TrendDirection.DOWN.name:
                signalVerified = False

            if signalVerified:
                if self.verbose:
                    print('SHORT entry signal')

                self.signal = TradeDirection.SHORT.name

        time = self.df.time[-1]
        reportString = '\n'+self.entryMethod+' channelLength: '+str(channelLength) \
            + '\n\ttime:         '+str(time) \
            + '\n\tclose:        '+str(close) \
            + '\n\tupperBandValue: '+str(upperBandValue) \
            + '\n\tlowerBandValue:  '+str(lowerBandValue) \
            + '\n\tfilterType:  '+str(self.filterType) \
            + '\n\ttrendDirection:  '+str(self.trendDirection) \
            + '\n\tSIGNAL:          '+str(self.signal) \

        if self.verbose:
            print(reportString)

        self.logger.debug(reportString)
        
        return
    
    def rsiPullback(self):
        if len(self.kwargs) == 0:
            raise Exception(self.entryMethod+' must have rsiLength and rsiThreshold kwargs')

        rsiLength = self.kwargs[0]['rsiLength']
        rsiThreshold = self.kwargs[0]['rsiThreshold']
        
        if not self.simulation:
            rsi = RSI(self.df.close, timeperiod=rsiLength).values[-1]
            
        else:
            raise Exception(self.entryMethod+' simulation not yet supported')

        signalVerified = False
        if self.trendBias != TradeDirection.SHORT.name and self.tradableSpread != False \
                and rsi <= rsiThreshold:
            signalVerified = True

            if self.filterType and self.trendDirection != TrendDirection.UP.name:
                signalVerified = False

            if signalVerified:
                if self.verbose:
                    print(self.entryMethod+' LONG entry signal')

                self.signal = TradeDirection.LONG.name

        elif self.trendBias != TradeDirection.LONG.name and self.tradableSpread != False \
                and rsi >= rsiThreshold:
            signalVerified = True

            if self.filterType and self.trendDirection != TrendDirection.DOWN.name:
                signalVerified = False

            if signalVerified:
                if self.verbose:
                    print(self.entryMethod+' SHORT entry signal')

                self.signal = TradeDirection.SHORT.name

        time = self.df.time[-1]
        reportString = '\n'+self.entryMethod \
            + '\n\ttime:         '+str(time) \
            + '\n\trsiLength: '+str(rsiLength) \
            + '\n\trsiThreshold:  '+str(rsiThreshold) \
            + '\n\trsi:  '+str(rsi) \
            + '\n\tfilterType:  '+str(self.filterType) \
            + '\n\ttrendDirection:  '+str(self.trendDirection) \
            + '\n\tSIGNAL:          '+str(self.signal) \

        if self.verbose:
            print(reportString)

        self.logger.debug(reportString)
        
        return
    
    def smaPriceCross(self):
        if len(self.kwargs) == 0:
            raise Exception(self.entryMethod+' must have channelLength kwarg')
            
        parameter = self.kwargs[0]['parameter']
        close = self.df.close.values[-1]
        
        if not self.simulation:
            sma = SMA(self.df.close, timeperiod=parameter).values[-1]
            
        else:
            raise Exception(self.entryMethod+' simulation not yet supported')

        signalVerified = False
        if self.trendBias != TradeDirection.SHORT.name and self.tradableSpread != False \
                and close >= sma:
            signalVerified = True

            if self.filterType and self.trendDirection != TrendDirection.UP.name:
                signalVerified = False

            if signalVerified:
                if self.verbose:
                    print(self.entryMethod+' LONG entry signal')

                self.signal = TradeDirection.LONG.name

        elif self.trendBias != TradeDirection.LONG.name and self.tradableSpread != False \
                and close <= sma:
            signalVerified = True

            if self.filterType and self.trendDirection != TrendDirection.DOWN.name:
                signalVerified = False

            if signalVerified:
                if self.verbose:
                    print(self.entryMethod+' SHORT entry signal')

                self.signal = TradeDirection.SHORT.name

        time = self.df.time[-1]
        reportString = '\n'+self.entryMethod \
            + '\n\ttime:         '+str(time) \
            + '\n\tclose: '+str(close) \
            + '\n\tsma:  '+str(sma) \
            + '\n\tfilterType:  '+str(self.filterType) \
            + '\n\ttrendDirection:  '+str(self.trendDirection) \
            + '\n\tSIGNAL:          '+str(self.signal) \

        if self.verbose:
            print(reportString)

        self.logger.debug(reportString)
            
        
        return

    def weeklyTrendTrader(self) -> None:

        # TODO add check that kwargs includes specifically
        #   channelLength and includeClose parameters
        if len(self.kwargs) == 0:
            raise Exception(
                self.entryMethod+' must have rocTimeperiod, rocThreshold, highestCloseBreakout kwargs')

        rocTimeperiod = self.kwargs[0]['rocTimeperiod']
        rocThreshold = self.kwargs[0]['rocThreshold']
        highestCloseBreakout = self.kwargs[0]['highestCloseBreakout']

        self.df['ROC'] = ROC(self.df.close, timeperiod=rocTimeperiod)
        self.df['HC'] = self.df['close'].rolling(highestCloseBreakout).max()
        close = self.df.close.values[-1]
        roc = self.df['ROC'].values[-1]
        breakout = (close == self.df.close[-highestCloseBreakout:].max())

        if (roc > rocThreshold) and (breakout == True):
            self.signal = TradeDirection.LONG.name

        return
