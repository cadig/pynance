import oandapyV20
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.transactions as trans
import pandas as pd
import forexutils as fx

class OandaTrader(object):
    """A class object that interfaces with the Oanda V20 API for trading activities"""

    def __init__(self, accountID, access_token, environment, acc_denom, max_risk_pct):
        self.accountID = accountID
        self.access_token = access_token
        self.environment = environment
        self.client = oandapyV20.API(access_token=self.access_token, environment=self.environment)
        self.acc_denom = acc_denom
        self.max_risk_pct = max_risk_pct

    def getOandaData(self, bar_count, granularity, instrument):
        """Pulls specified data from Oanda api"""
        params = {
                  "count": bar_count,
                  "granularity": granularity
        }
        r = instruments.InstrumentsCandles(instrument=instrument,
                                          params=params)
        response = self.client.request(r)
        return response

    def getOandaTradesState(self):
        "Returns list of open trades in the account."
        r = trades.TradesList(accountID=self.accountID)
        response = self.client.request(r)
        opendf = pd.json_normalize(response['trades'])
        return opendf

    def getOandaAccNAV(self):
        """Returns account net asset value of account from Oanda API."""
        r = accounts.AccountDetails(self.accountID)
        response = self.client.request(r)
        return response['account']['NAV']

    def sendOandaMktStopOrder(self, instrument, stopprice, units):
        if units > 0:
            print('{0}: opening {2} units LONG at stop {1}'.format(instrument,stopprice,units))
        elif units < 0:
            print('{0}: opening {2} units SHORT at stop {1}'.format(instrument,stopprice,units))
        order = {
            "order": {
                    "stopLossOnFill": {
                        "timeInForce": "GTC",
                        "price": stopprice
                        },
                        "timeInForce": "FOK",
                        "instrument": instrument,
                        "units": units,
                        "type": "MARKET",
                        "positionFill": "DEFAULT"
                        }
                    }
        r = orders.OrderCreate(self.accountID, data=order)
        response = self.client.request(r)
        return response

    def findExchangePairPrice(self, target_pair, direction):
        '''Used for calculating position size. Finds the pair that exists between
        the acc_denom currency and the target_pair counter currency.'''
        idf = pd.read_csv('instruments.csv')
        acc_denom = self.acc_denom
        if self.acc_denom in target_pair:
            if (self.acc_denom + target_pair[-4:]) in idf['name'].values:
                # print('acc_denom is base in exchange currency')
                exchange_instrument = self.acc_denom + target_pair[-4:]
                if direction == 'LONG':
                    exchange_rate = self.getOandaAskPrice(exchange_instrument)
                elif direction == 'SHORT':
                    exchange_rate = self.getOandaBidPrice(exchange_instrument)
                else:
                    print('ERROR findExchangePairPrice: direction must be LONG or SHORT')
                return exchange_rate
            elif (target_pair[:4] + self.acc_denom) in idf['name'].values:
                # print('acc_denom is counter in exchange currency')
                exchange_instrument = target_pair[:4] + self.acc_denom
                if direction == 'LONG':
                    exchange_rate = self.getOandaAskPrice(exchange_instrument)
                elif direction == 'SHORT':
                    exchange_rate = self.getOandaBidPrice(exchange_instrument)
                else:
                    print('ERROR findExchangePairPrice: direction must be LONG or SHORT')
                return exchange_rate
        elif acc_denom not in target_pair:
            if acc_denom + target_pair[-4:] in idf.values:
                exchange_instrument = acc_denom + target_pair[-4:]
                if direction == 'LONG':
                    exchange_rate = self.getOandaAskPrice(exchange_instrument)
                elif direction == 'SHORT':
                    exchange_rate = self.getOandaBidPrice(exchange_instrument)
                else:
                    print('ERROR findExchangePairPrice: direction must be LONG or SHORT')
                return exchange_rate
            elif target_pair[-3:] + '_' + acc_denom in idf.values:
                exchange_instrument = target_pair[-3:] + '_' + acc_denom
                if direction == 'LONG':
                    exchange_rate = self.getOandaAskPrice(exchange_instrument)
                elif direction == 'SHORT':
                    exchange_rate = self.getOandaBidPrice(exchange_instrument)
                else:
                    print('ERROR findExchangePairPrice: direction must be LONG or SHORT')
                exchange_rate = 1 / exchange_rate
                return exchange_rate
        else:
            return 'Something went wrong in findExchangePairPrice finding the acc_denom / target_pair price.'

    def getOandaMidpointPrice(self, instrument):
        '''return the midpoint of current instrument ask and bid prices'''
        #accountID, access_token = exampleAuth()
        #client = oandapyV20.API(access_token=access_token)
        params = {
            "instruments": instrument
            }
        r = pricing.PricingInfo(self.accountID, params=params)
        response = self.client.request(r)
        data = pd.json_normalize(response['prices'])
        asks = float(data['asks'][0][0]['price'])
        bids = float(data['bids'][0][0]['price'])
        midpoint = (asks + bids) / 2
        return midpoint

    def getOandaBidPrice(self, instrument):
        """Return instantaneous ask price of instrument"""
        params = {
            "instruments": instrument
            }
        r = pricing.PricingInfo(self.accountID, params=params)
        response = self.client.request(r)
        data = pd.json_normalize(response['prices'])
        bid_price = float(data['bids'][0][0]['price'])
        return bid_price

    def getOandaAskPrice(self, instrument):
        """Return instantaneous bid price of instrument"""
        params = {
            "instruments": instrument
            }
        r = pricing.PricingInfo(self.accountID, params=params)
        response = self.client.request(r)
        data = pd.json_normalize(response['prices'])
        ask_price = float(data['asks'][0][0]['price'])
        return ask_price

    def getMaxPositionDollarRisk(self):
        acc_val = self.getOandaAccNAV()
        max_dollar_risk = float(acc_val) * self.max_risk_pct
        return max_dollar_risk

    def getPositionDollarRisk(self, target_risk_pct):
        acc_val = self.getOandaAccNAV()
        dollar_risk = float(acc_val) * target_risk_pct
        return dollar_risk

    def calc_units(self, instrument, pips, direction):
        """Calculates the number of units based on the given number of pips."""
        acc_val = self.getOandaAccNAV()
        max_dollar_risk = float(acc_val) * self.max_risk_pct
        current_price = self.getOandaMidpointPrice(instrument)
        multiplier = fx.getCrossPairMultiplier(instrument)

        # initialize pip_val
        distance = pips * multiplier
        pip_val = float(max_dollar_risk) / pips

        # check for acc_denom in the target fx pair & update pip val: counter, base, or not at all
        if self.acc_denom == instrument[-3:]:
            units = pip_val / multiplier
        elif self.acc_denom == instrument[:3]:
            pip_val = pip_val * current_price
            units = pip_val / multiplier
        elif self.acc_denom not in instrument:
            print(self.acc_denom, ' not in ', instrument)
            exchange_rate = self.findExchangePairPrice(self, instrument)
            pip_val = pip_val * exchange_rate
            units = pip_val / multiplier

        units = int(units)
        if direction == 'long':
            units = units
            pip_price = current_price - distance
        elif direction == 'short':
            pip_price = current_price + distance
            units = units * -1

        return units, pip_price

    def getMaxPositionUnits(self, instrument, direction, stop_distance):
        """Uses initialized max_dollar_risk of the class to calculate trade size.
        Used for systems with fixed positions sizing as a percentage of net account value."""
        multiplier = fx.getCrossPairMultiplier(instrument)
        pips_risk = round((stop_distance / multiplier), 1)
        max_dollar_risk = self.getMaxPositionDollarRisk()
        pip_val = float(max_dollar_risk) / pips_risk

        # check for acc_denom in the target fx pair: counter, base, or not at all
        if self.acc_denom == instrument[-3:]:
            units = pip_val / multiplier
        elif self.acc_denom == instrument[:3]:
            exchange_rate = self.findExchangePairPrice(instrument, direction)
            pip_val = pip_val * exchange_rate
            units = pip_val / multiplier
        elif self.acc_denom not in instrument:
            exchange_rate = self.findExchangePairPrice(instrument, direction)
            pip_val = pip_val * exchange_rate
            units = pip_val / multiplier
        return units

    def getPositionUnits(self, instrument, direction, stop_distance, target_risk_pct):
        """Uses target_risk_pct as input to calculate trade size & ignores the initialized max_dollar_risk of the class.
        Used for systems with variable positions sizing."""
        multiplier = fx.getCrossPairMultiplier(instrument)
        pips_risk = round((stop_distance / multiplier), 1)
        max_dollar_risk = self.getPositionDollarRisk(target_risk_pct)
        pip_val = float(max_dollar_risk) / pips_risk

        # check for acc_denom in the target fx pair: counter, base, or not at all
        if self.acc_denom == instrument[-3:]:
            units = pip_val / multiplier
        elif self.acc_denom == instrument[:3]:
            exchange_rate = self.findExchangePairPrice(instrument, direction)
            pip_val = pip_val * exchange_rate
            units = pip_val / multiplier
        elif self.acc_denom not in instrument:
            exchange_rate = self.findExchangePairPrice(instrument, direction)
            pip_val = pip_val * exchange_rate
            units = pip_val / multiplier
        return units
    
    def getCurrentTradePips(self, instrument, currentUnits, unrealizedPL):
        multiplier = fx.getCrossPairMultiplier(instrument)
        
        direction = 'LONG' if currentUnits > 0 else 'SHORT'
        #
        # TODO | may need to round off calculations below if it causes problems
        #
        # check for acc_denom in the target fx pair: counter, base, or not at all
        if self.acc_denom == instrument[-3:]:
             pip_val = multiplier * currentUnits
            
        elif self.acc_denom == instrument[:3]:
            exchange_rate = self.findExchangePairPrice(instrument, direction)
            pip_val = (currentUnits * multiplier) / exchange_rate
            
        elif self.acc_denom not in instrument:
            exchange_rate = self.findExchangePairPrice(instrument, direction)
            pip_val = (currentUnits * multiplier) / exchange_rate
            
        # ensure that pip_val is always positive before the final calculation
        pip_val = pip_val if pip_val > 0 else pip_val * -1
            
        return round(unrealizedPL / pip_val, 2)

    def sendOandaCloseLong(self, instrument):
        print('{0}: closing LONG position'.format(instrument))
        data = {
            "longUnits": "ALL"
        }

        r = positions.PositionClose(accountID=self.accountID,
                                    instrument=instrument,
                                    data=data)
        response = self.client.request(r)
        return response
    
    def sendOandaCloseShort(self, instrument):
        print('{0}: closing SHORT position'.format(instrument))
        data = {
            "shortUnits": "ALL"
        }
        r = positions.PositionClose(accountID=self.accountID,
                                    instrument=instrument,
                                    data=data)
        response = self.client.request(r)
        return response
      
    def sendOandaMktOrder(self, instrument, units):
        print('{0}: sending market order units {1}'.format(instrument, units))
        order = {
            "order": {
                    "instrument": instrument,
                    "units": units,
                    "type": "MARKET",
                    "positionFill": "DEFAULT"
                    }
            }
        r = orders.OrderCreate(self.accountID, data=order)
        response = self.client.request(r)
        return response

    def sendOandaMktTpSlOrder(self, instrument, takeprofitprice, stopprice, units):
        if units > 0:
            print('\n', instrument,'entering LONG',
              '\n   Units:        ', units,
              '\n   Stop loss:    ', stopprice,
              '\n   Take profit:  ', takeprofitprice)
        elif units < 0:
            print('\n', instrument,'entering SHORT',
              '\n   Units:        ', units,
              '\n   Stop loss:    ', stopprice,
              '\n   Take profit:  ', takeprofitprice)
        order = {
            "order": {
                "takeProfitOnFill": {
                    "timeInForce": "GTC",
                    "price": takeprofitprice
                },
                    "stopLossOnFill": {
                        "timeInForce": "GTC",
                        "price": stopprice
                        },
                        "timeInForce": "FOK",
                        "instrument": instrument,
                        "units": units,
                        "type": "MARKET",
                        "positionFill": "DEFAULT"
                        }
                    }
        r = orders.OrderCreate(self.accountID, data=order)
        response = self.client.request(r)
        return response

    def sendOandaTrailingStopTakeProfitOrder(self, instrument, distance, takeprofitprice, units):
        """Create a trailing stop loss order with distance param and take profit price param."""
        if units > 0:
            print('{0}: opening {2} units LONG with trailing stop {1} away'.format(instrument,distance,units))
        elif units < 0:
            print('{0}: opening {2} units SHORT with trailing stop {1} away'.format(instrument,distance,units))
        order = {
            "order": {
                "takeProfitOnFill": {
                    "timeInForce": "GTC",
                    "price": takeprofitprice
                },
                    "trailingStopLossOnFill": {
                        "timeInForce": "GTC",
                        "distance": distance
                        },
                        "timeInForce": "FOK",
                        "instrument": instrument,
                        "units": units,
                        "type": "MARKET",
                        "positionFill": "DEFAULT"
                        }
                    }
        r = orders.OrderCreate(self.accountID, data=order)
        response = self.client.request(r)
        return response

    def sendOandaTrailingStopTakeProfitStopLossOrder(self,instrument,distance,takeprofitprice,stopprice,units):
        """Create a trailling stop loss order with distrance param and take profit price param."""
        if units > 0:
            print('{0}: opening {2} units LONG with trailing stop {1} away'.format(instrument,distance,units))
        elif units < 0:
            print('{0}: opening {2} units SHORT with trailing stop {1} away'.format(instrument,distance,units))
        order = {
            "order": {
                "takeProfitOnFill": {
                    "timeInForce": "GTC",
                    "price": takeprofitprice
                },
                "stopLossOnFill": {
                    "timeInForce": "GTC",
                    "price": stopprice
                },
                "trailingStopLossOnFill": {
                    "timeInForce": "GTC",
                    "distance": distance
                },
                "timeInForce": "FOK",
                "instrument": instrument,
                "units": units,
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }
        r = orders.OrderCreate(self.accountID, data=order)
        response = self.client.request(r)
        return response

    def sendOandaTrailingStopOrder(self, instrument, distance, units):
        if units > 0:
            print('{0}: opening {2} units LONG with trailing stop {1} away'.format(instrument,distance,units))
        elif units < 0:
            print('{0}: opening {2} units SHORT with trailing stop {1} away'.format(instrument,distance,units))
        order = {
            "order": {
                    "trailingStopLossOnFill": {
                        "timeInForce": "GTC",
                        "distance": distance
                        },
                        "timeInForce": "FOK",
                        "instrument": instrument,
                        "units": units,
                        "type": "MARKET",
                        "positionFill": "DEFAULT"
                        }
                    }
        r = orders.OrderCreate(self.accountID, data=order)
        response = self.client.request(r)
        return response

    def checkOandaSpread(self, instrument, pip_threshold):
        '''If the difference between asks and bids for the input instrument, divided by the instrument multiplier factor, is less than the pip_threshold, return True.'''
        params = {"instruments": instrument}
        r = pricing.PricingInfo(self.accountID, params=params)
        res = self.client.request(r)
        asks = float(res['prices'][0]['asks'][0]['price'])
        bids = float(res['prices'][0]['bids'][0]['price'])
        val_spread = asks - bids
        mult = fx.getCrossPairMultiplier(instrument)
        pip_spread = val_spread / mult
        # print(instrument, 'pips spread ', pip_spread)
        if pip_spread > pip_threshold:
            print('oanda.checkOandaSpread pip_spread is greater than pip_threshold!',
                  '\n\tinstrument', instrument,
                  '\n\tpip_threshold', pip_threshold,
                  '\n\tpip_spread', pip_spread)
            return False, pip_spread
        elif pip_spread < pip_threshold:
            return True, pip_spread

    def getTransactionIDRange(self, to_id, from_id):
        '''Retrieve a list of oanda account transactions from_id, to_id range'''
        params = {
            "to":to_id,
            "from":from_id
        }
        r = trans.TransactionIDRange(self.accountID,params=params)
        res = self.client.request(r)
        return res

    def closeAllOpenPositions(self):
        pos = self.getOandaTradesState()
        for row in range(0,len(pos)):
            inst = pos.loc[row,'instrument']
            units = int(pos.loc[row,'currentUnits'])
            if units > 0:
                try:
                    self.sendOandaCloseLong(inst)
                except:
                    ValueError
            elif units < 0:
                try:
                    self.sendOandaCloseShort(inst)
                except:
                    ValueError
        return print('oandaTrader.closeAllOpenPositions() double check all positions closed.')

    def check_stopped_positions(self, sdf):
        """Dataframe input must have instrument and trade_phase columns."""
        open_trades = self.getOandaTradesState()
        if open_trades.size != 0:
            for row in range(0,len(sdf)):
                if sdf.loc[row,'instrument'] in open_trades['instrument'].values:
                    # print(sdf.loc[row,'instrument'], 'trade still on.')
                    continue
                else:
                    # print(sdf.loc[row,'instrument'], 'no trade on.')
                    sdf.loc[row,'trade_phase'] = 0
        else:
            sdf['trade_phase'] = 0
            print('Empty open_trades response.')
        return sdf

    def getOandaAsksPrice(self, instrument):
        params = {
            "instruments": instrument
            }
        r = pricing.PricingInfo(self.accountID, params=params)
        response = self.client.request(r)
        data = pd.json_normalize(response['prices'])
        asks = float(data['asks'][0][0]['price'])
        return asks

    def getOandaBidsPrice(self, instrument):
        params = {
            "instruments": instrument
            }
        r = pricing.PricingInfo(self.accountID, params=params)
        response = self.client.request(r)
        data = pd.json_normalize(response['prices'])
        bids = float(data['bids'][0][0]['price'])
        return bids

    def getOandaInstrumentOpenTrades(self,instrument):
        params ={
                  "instrument": instrument
                }
        r = trades.TradesList(accountID=self.accountID, params=params)
        res = self.client.request(r)
        tdf = pd.json_normalize(res['trades'])
        return tdf

    def replaceStopOrder(self,new_stop_price,tradeID,orderID):
        data = {
          "order": {
                        "timeInForce": "GTC",
                        "price": new_stop_price,
                        "type": "STOP_LOSS",
                        "tradeID": tradeID
                    }
        }
        r = orders.OrderReplace(accountID=self.accountID, orderID=orderID, data=data)
        res = self.client.request(r)
        return res

    def moveInstrumentStops(self,instrument,new_stop_price):
        tdf = self.getOandaInstrumentOpenTrades(instrument)
        if 'stopLossOrder.tradeID' in tdf.columns:
            new_stop = fx.getCrossPairPricePrecision(instrument,new_stop_price)
            for i in range(0,len(tdf)):
                try:
                    if int(tdf.loc[i,'stopLossOrder.tradeID']) > 0:
                        tradeID = tdf.loc[i,'stopLossOrder.tradeID']
                        orderID = tdf.loc[i,'stopLossOrder.id']
                        self.replaceStopOrder(new_stop,tradeID,orderID)
                    else:
                        i=+1
                except ValueError:
                    print('Skipping trailing stop, replacing stop loss orders only.')
        return