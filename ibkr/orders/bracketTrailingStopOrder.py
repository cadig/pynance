from ib_insync import Order

def bracketTrailingStopOrder(
        accountId, parentOrderId, childOrderId, action, quantity, limitPrice, trailingPercent):
    """
    https://groups.io/g/insync/topic/10785315?p=Created,,,20,2,0,0

    Parameters
    ----------
    accountId : TYPE
        DESCRIPTION.
    parentOrderId : TYPE
        DESCRIPTION.
    childOrderId : TYPE
        DESCRIPTION.
    action : TYPE
        DESCRIPTION.
    quantity : TYPE
        DESCRIPTION.
    limitPrice : TYPE
        DESCRIPTION.
    trailingPercent : TYPE
        DESCRIPTION.

    Returns
    -------
    bracketOrder : TYPE
        DESCRIPTION.

    """

    #This will be our main or "parent" order
    parent = Order()
    parent.account = accountId
    parent.orderId = parentOrderId
    parent.action = action
    parent.orderType = "LMT"
    parent.totalQuantity = quantity
    parent.lmtPrice = limitPrice
    parent.transmit = False

    stopLoss = Order()
    stopLoss.orderId = childOrderId
    stopLoss.action = "SELL" if action == "BUY" else "BUY"
    stopLoss.orderType = "TRAIL"
    stopLoss.trailingPercent = trailingPercent
    stopLoss.totalQuantity = quantity
    stopLoss.parentId = parentOrderId
    stopLoss.account = accountId
    stopLoss.transmit = True

    bracketOrder = [parent, stopLoss]
    return bracketOrder