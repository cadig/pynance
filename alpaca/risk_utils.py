"""
Risk Management Utilities

Shared risk calculation and stop loss management functions.
"""

import pandas as pd
from alpaca.trading.requests import StopOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus

# === Constants ===
STOP_LOSS_ATR_MULT = 4.0

def calculate_risk_metrics(entry_price, stop_price, qty, account_value=None):
    """
    Calculate all risk-related metrics for a position
    
    Args:
        entry_price (float): Entry price per share
        stop_price (float): Stop loss price per share
        qty (int): Number of shares
        account_value (float, optional): Total account value for percentage calculations
    
    Returns:
        dict: {
            'dollar_risk': float,
            'percent_risk': float, 
            'position_cost': float,
            'percent_to_stop': float
        }
    """
    dollar_risk = (entry_price - stop_price) * qty
    percent_risk = (dollar_risk / account_value * 100) if account_value else 0
    position_cost = entry_price * qty
    percent_to_stop = ((entry_price - stop_price) / entry_price * 100)
    
    return {
        'dollar_risk': dollar_risk,
        'percent_risk': percent_risk,
        'position_cost': position_cost,
        'percent_to_stop': percent_to_stop
    }

def check_missing_stop_loss_orders(symbols, trading_client):
    """Check which symbols are missing stop loss orders"""
    try:
        # Get all open orders
        request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
        orders = trading_client.get_orders(filter=request)
        
        # Find stop loss orders by symbol
        symbols_with_stops = set()
        for order in orders:
            if order.side == OrderSide.SELL and order.order_type == 'stop':
                symbols_with_stops.add(order.symbol)
        
        # Return symbols that don't have stop loss orders
        return [symbol for symbol in symbols if symbol not in symbols_with_stops]
        
    except Exception as e:
        print(f"Error checking stop loss orders: {e}")
        return symbols  # Assume all symbols need stops if error occurs

def cancel_stop_orders(symbol, trading_client, dry_run=True):
    """Cancel all stop loss orders for a symbol. Returns count of cancelled orders."""
    try:
        request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
        orders = trading_client.get_orders(filter=request)
        cancelled = 0
        for order in orders:
            if order.symbol == symbol and order.side == OrderSide.SELL and order.order_type == 'stop':
                if dry_run:
                    print(f"[DRY RUN] Would cancel stop order {order.id} for {symbol} (stop: ${order.stop_price})")
                    cancelled += 1
                else:
                    try:
                        trading_client.cancel_order_by_id(order.id)
                        print(f"Cancelled stop order {order.id} for {symbol} (stop: ${order.stop_price})")
                        cancelled += 1
                    except Exception as e:
                        print(f"Failed to cancel stop order {order.id} for {symbol}: {e}")
        return cancelled
    except Exception as e:
        print(f"Error cancelling stop orders for {symbol}: {e}")
        return 0


def reconcile_position_qty(symbol, expected_qty, trading_client):
    """
    Re-fetch live position quantity from Alpaca and reconcile against expected.
    Returns the actual quantity, or 0 if position no longer exists.
    Logs a warning if actual differs from expected (partial fill scenario).
    """
    try:
        position = trading_client.get_open_position(symbol)
        actual_qty = int(float(position.qty))
        if actual_qty != int(expected_qty):
            print(f"WARNING: {symbol} quantity mismatch — expected {int(expected_qty)}, actual {actual_qty} (partial fill?)")
        return actual_qty
    except Exception:
        # Position no longer exists (fully closed)
        print(f"WARNING: {symbol} position no longer exists — skipping stop order")
        return 0


def add_stop_loss_order(symbol, qty, stop_price, current_price=None, account_value=None, trading_client=None, dry_run=True):
    """Add a stop loss order for an existing position"""
    if dry_run:
        # Calculate risk metrics using shared function (handle None current_price)
        if current_price:
            risk_metrics = calculate_risk_metrics(current_price, stop_price, qty, account_value)
            print(f"[DRY RUN] Would add STOP order for {symbol}: qty={qty}, stop_price={stop_price:.2f}, risk=${risk_metrics['dollar_risk']:.2f} ({risk_metrics['percent_risk']:.2f}%), cost=${risk_metrics['position_cost']:.2f}, stop%={risk_metrics['percent_to_stop']:.2f}%")
        else:
            print(f"[DRY RUN] Would add STOP order for {symbol}: qty={qty}, stop_price={stop_price:.2f}")
        return True
    else:
        try:
            stop_order_data = StopOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                stop_price=stop_price,
                time_in_force=TimeInForce.GTC
            )
            stop_order = trading_client.submit_order(stop_order_data)
            
            # Calculate risk metrics using shared function (handle None current_price)
            if current_price:
                risk_metrics = calculate_risk_metrics(current_price, stop_price, qty, account_value)
                print(f"Added STOP order for {symbol}: qty={qty}, stop_price={stop_price:.2f}, risk=${risk_metrics['dollar_risk']:.2f} ({risk_metrics['percent_risk']:.2f}%), cost=${risk_metrics['position_cost']:.2f}, stop%={risk_metrics['percent_to_stop']:.2f}%")
            else:
                print(f"Added STOP order for {symbol}: qty={qty}, stop_price={stop_price:.2f}")
            return True
        except Exception as e:
            print(f"Failed to add stop loss order for {symbol}: {e}")
            return False
