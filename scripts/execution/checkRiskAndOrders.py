from configparser import ConfigParser
from ib_insync import IB
import sys
sys.path.append('../..')
from ibkr.IbkrTrader import IbkrTrader as IbkrClient

def get_ibkr_account_id(whichAccount: str) -> str:
    config = ConfigParser()
    config.read('../../../config/ibkr-config.ini')
    return config.get(whichAccount, 'accountId')

def check_position_risk(ib: IB, ibt: IbkrClient, account_id: str):
    """Check risk for each position in the account."""
    # Get account net liquidation value
    net_liq = float(ibt.getIbAccountNetLiquidation(account_id))
    print(f"\nAccount Net Liquidation: ${net_liq:,.2f}")
    
    # Get all positions
    positions = ibt.getAllAccountPositions({'account_identifier': account_id})
    
    if not positions:
        print("No open positions found")
        return
    
    print("\nPosition Risk Analysis:")
    print("-" * 80)
    
    # Request all open orders first
    ib.reqAllOpenOrders()
    open_trades = ib.openTrades()
    
    # Filter trades for this specific account
    account_trades = [t for t in open_trades if t.order.account == account_id]
    
    # Track total risk
    total_dollar_risk = 0.0
    
    for position in positions:
        contract = position.contract
        quantity = position.position
        avg_cost = position.avgCost
        
        # Get current market price
        ticker = ib.reqMktData(contract)
        ib.sleep(1)  # Give time for market data to arrive
        current_price = ticker.last if ticker.last else ticker.close
        
        if not current_price:
            print(f"Warning: Could not get current price for {contract.symbol}")
            continue
            
        # Get open trades for this contract
        trades = [t for t in account_trades if t.contract == contract]
        stop_orders = [t for t in trades if t.order.orderType == 'STP']
        
        if not stop_orders:
            print(f"Warning: No stop loss orders found for {contract.symbol}")
            continue
            
        # Calculate risk to stop loss
        stop_price = stop_orders[0].order.auxPrice  # Access auxPrice through the order object
        price_to_stop = abs(current_price - stop_price)
        dollar_risk = price_to_stop * abs(quantity)
        risk_percentage = (dollar_risk / net_liq) * 100
        
        # Add to total risk
        total_dollar_risk += dollar_risk
        
        print(f"\nPosition: {contract.symbol}")
        print(f"Quantity: {quantity}")
        print(f"Current Price: ${current_price:.2f}")
        print(f"Stop Price: ${stop_price:.2f}")
        print(f"Dollar Risk: ${dollar_risk:.2f}")
        print(f"Risk as % of Account: {risk_percentage:.2f}%")
    
    # Print total risk summary
    total_risk_percentage = (total_dollar_risk / net_liq) * 100
    print("\nTotal Risk Summary:")
    print("-" * 80)
    print(f"Total Dollar Risk: ${total_dollar_risk:.2f}")
    print(f"Total Risk as % of Account: {total_risk_percentage:.2f}%")

def check_open_orders(ib: IB, ibt: IbkrClient, account_id: str):
    """Check open orders and verify stop losses match positions."""
    # Get all positions
    positions = ibt.getAllAccountPositions({'account_identifier': account_id})
    position_dict = {p.contract: p for p in positions}
    
    # Get all open trades
    ib.reqAllOpenOrders()
    open_trades = ib.openTrades()
    
    # Filter trades for this specific account
    account_trades = [t for t in open_trades if t.order.account == account_id]
    
    print("\nOrder Analysis:")
    print("-" * 80)
    
    # Check for stop loss orders
    stop_trades = [t for t in account_trades if t.order.orderType == 'STP']
    other_trades = [t for t in account_trades if t.order.orderType != 'STP']
    
    # Group stop trades by contract
    stop_trades_by_contract = {}
    for trade in stop_trades:
        contract = trade.contract
        if contract not in stop_trades_by_contract:
            stop_trades_by_contract[contract] = []
        stop_trades_by_contract[contract].append(trade)
    
    # Analyze stop loss orders
    for contract, trades in stop_trades_by_contract.items():
        if contract not in position_dict:
            print(f"Warning: Stop loss order for {contract.symbol} without matching position")
            continue
            
        position = position_dict[contract]
        total_stop_quantity = sum(abs(t.order.totalQuantity) for t in trades)
        
        if total_stop_quantity != abs(position.position):
            print(f"Warning: Total stop loss quantity ({total_stop_quantity}) doesn't match position size ({position.position}) for {contract.symbol}")
            print(f"Individual stop orders: {[t.order.totalQuantity for t in trades]}")
    
    # Check for other open orders
    if other_trades:
        print("\nOther Open Orders:")
        for trade in other_trades:
            print(f"Warning: Open order found: {trade.order.orderType} for {trade.contract.symbol}")

def main():
    ibAccId = get_ibkr_account_id('margin')
    
    ib = IB()
    ibt = IbkrClient(ib, logFilepath='System', verbose=True)
    
    try:
        ibt.connectClient(port=7496)
        
        # Check position risk
        check_position_risk(ib, ibt, ibAccId)
        
        # Check open orders
        check_open_orders(ib, ibt, ibAccId)
        
    finally:
        ibt.disconnectClient()

if __name__ == "__main__":
    main()
