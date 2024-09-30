class StocksMoneyManager(object):
    """A class object that implements a money management strategy based on initialization params"""

    def __init__(self, base_risk_pct):
        self.base_risk_pct = base_risk_pct
        
    def getStockPositionSizing(self, cash, stop_distance, symbol_price):
        """Return total units of risk per input parameters and boolean enoughCash
        in account. If first check does not have enough cash. Attempts to use half
        of the original intended position size (halves the risk)."""
        acc_dollar_risk = cash * self.base_risk_pct
        units = round( int(round(acc_dollar_risk / 
                                 stop_distance)), 2)
        position_cost = units * symbol_price
        position_cost_pct = position_cost / cash
        print('Sizing:')
        print('\tacc_dollar_risk: \t', acc_dollar_risk)
        print('\tstop_distance: \t\t', stop_distance)
        print('\tsymbol_price: \t\t', symbol_price)
        print('\ttarget units: \t\t',units)
        print('\tposition_cost: \t\t', position_cost)
        print('\tposition_cost_pct: \t{}%'.format(round(position_cost_pct*100, 4)) )
        if position_cost > cash:
            print('Not enough cash for total position.')
            
            if (units/2) * symbol_price > cash:
                print('Not enough cash for HALF target units.')
                return 0, False
            
            else:
                print(' - enough cash for HALF target units.')
                return units/2, True
            
        else:
            print(' - enough cash for total position.')
            return units, True