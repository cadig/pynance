from ib_insync import Order

def bracketLimitOrderWithStopLoss(
        accountId: str, parentOrderId:int, tif: str, action:str, quantity:int, 
        limitPrice:float, stopLossPrice:float
    ):

     parent = Order()
     parent.account = accountId
     parent.orderId = parentOrderId
     parent.tif = tif
     parent.action = action
     parent.orderType = "LMT"
     parent.totalQuantity = quantity
     parent.lmtPrice = limitPrice
     #The parent and children orders will need this attribute set to False to prevent accidental executions.
     #The LAST CHILD will have it set to True, 
     parent.transmit = False

    #  takeProfit = Order()
    #  takeProfit.account = accountId
    #  takeProfit.orderId = parent.orderId + 1
    #  takeProfit.action = "SELL" if action == "BUY" else "BUY"
    #  takeProfit.orderType = "LMT"
    #  takeProfit.totalQuantity = quantity
    #  takeProfit.lmtPrice = takeProfitLimitPrice
    #  takeProfit.parentId = parentOrderId
    #  takeProfit.transmit = False

     stopLoss = Order()
     stopLoss.account = accountId
     stopLoss.orderId = parent.orderId + 1
     stopLoss.action = "SELL" if action == "BUY" else "BUY"
     stopLoss.orderType = "STP"
     #Stop trigger price
     stopLoss.auxPrice = stopLossPrice
     stopLoss.totalQuantity = quantity
     stopLoss.parentId = parentOrderId
     #In this case, the low side order will be the last child being sent. Therefore, it needs to set this attribute to True 
     #to activate all its predecessors
     stopLoss.transmit = True

     bracketOrder = [parent, stopLoss]
     return bracketOrder