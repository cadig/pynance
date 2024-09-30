import pandas as pd

class AccountRiskModulator(object):    
    def __init__(self, init_acc_val, scheme, verbose, isSimulation=False):
        self.init_acc_val = init_acc_val
        self.scheme = scheme
        self.verbose = bool( verbose )
        self.isSimulation = isSimulation
        
    def getSchemeRules(self):
        """Return dataframe representation of scheme rules"""
        if self.scheme=='progressive':
            rules = {
                "r-multiple":[-20,21,61,100],
                "percentRisk":[.0025,.005,.01,.02],
                "percentReturn":[-.075,.05,.25,.65]
            }
            df = pd.DataFrame(rules)
            return df
        else:
            print('ERROR AccountRiskModulator.getSchemeRules() invalid scheme')
            return None

    def getAccountReturn(self,currentNav):
        """Calculate account return since the initial account value setting"""
        return round((currentNav-self.init_acc_val)/self.init_acc_val,4)
    
    def getTargetRiskPercentage(self,currentNav):
        """Return target risk percentage per position, based on account return"""
        rdf = self.getSchemeRules()
        accountReturn = self.getAccountReturn(currentNav)
        
        targetRiskPercentage=None
        for idx in rdf.index:
            percentReturn = float(rdf.loc[idx,'percentReturn'])
            if accountReturn >= percentReturn:
                targetRiskPercentage = float(rdf.loc[idx,'percentRisk'])
                
        if self.verbose==True:
            print('\nAccountRiskModulator.getTargetRiskPercentage():')
            print('\tcurrentNav: \t\t\t',currentNav)
            print('\taccountReturn: \t\t',accountReturn)
            print('\ttargetRiskPercentage: ',targetRiskPercentage)
            
        return targetRiskPercentage
    
    def getSplitRiskByCurrency(self,oandaTrader,method,symbol,symbolList,simCurrentNav=0):
        """Divide target risk percentage by the number of currency units traded across the account"""
        
        if self.isSimulation==False:
            currentNav = float( oandaTrader.getOandaAccNAV() )
        else:
            currentNav = simCurrentNav
            
        trp = self.getTargetRiskPercentage(currentNav)
        if trp is None and self.isSimulation == False:
            print('AccountRiskModulator.getSplitRiskByCurrency(): target risk is None')
            return None
        
        if method=='fixed':
            return trp
        
        elif method=='equalCurrencyRisk':
            counter=symbol[4:]
            base=symbol[:-4]
            baseCount=1
            counterCount=1
            
            for sym in symbolList:
                if sym==symbol:
                    # symbol already counted
                    continue
                
                if base in sym:
                    baseCount = baseCount+1
                    
                if counter in sym:
                    counterCount = counterCount+1
                    
                    
            if self.verbose==True:
                print('AccountRiskModulator.getSplitRiskByCurrency():')
                print('\tbase: ',base)
                print('\tcounter: ',counter)
                print('\tsymbolList: ',symbolList)
                print('\tbaseCount: ',baseCount)
                print('\tcounterCount: ',counterCount)
                print('\ttrp: ',trp)
                print('\tfinal: ',round(trp/max(baseCount,counterCount),4))
                
            return round(trp/max(baseCount,counterCount),4)
        
        else:
            print('ERROR AccountRiskModulator.getSplitRiskByCurrency() invalid method')
            return None