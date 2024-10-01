from enums import MoneyManagerMethodList

class MoneyManagerMethod(object):
    def __init__(self, method, MoneyManager):
        
        if method not in MoneyManagerMethodList._value2member_map_:
            raise Exception( 'Invalid MoneyManagerMethod '+str(method) )
            
        self.method = method
        self.MoneyManager = MoneyManager
        
    def __str__(self):
        return self.name
    
    def getRiskTarget(self):
        if self.method == MoneyManagerMethodList.FIXED_FRACTION:
            return self.MoneyManager.base_risk_pct
        
        else:
            raise Exception(str(self.method)+' MoneyManagerMethod.getRiskTarget()' + \
                            ' not implemented')