class MoneyManagerMethod(object):
    def __init__(self, method, MoneyManager):
        
        methodList=['FixedFraction', 'ConsecutiveWins']
        
        if method not in methodList:
            raise Exception( 'Invalid MoneyManagerMethod '+str(method) )
            
        self.method = method
        self.MoneyManager = MoneyManager
        
    def __str__(self):
        return self.name
    
    def getRiskTarget(self):
        if self.method == 'FixedFraction':
            return self.MoneyManager.base_risk_pct
        
        else:
            raise Exception(str(self.method)+' MoneyManagerMethod.getRiskTarget()' + \
                            ' not implemented')