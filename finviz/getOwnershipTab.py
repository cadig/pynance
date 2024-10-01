from finvizfinance.screener.ownership import Ownership

def getOwnershipTab(filters_dict):
    finvizScreenerTab = Ownership()
    
    finvizScreenerTab.set_filter(filters_dict=filters_dict)
    
    df = finvizScreenerTab.screener_view()
    
    return df