import pandas as pd
import numpy as np
import json
import os
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.requests import MarketOrderRequest, StopOrderRequest, GetOrdersRequest, StopLimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus, PositionIntent
from datetime import datetime, timedelta, timezone
from configparser import ConfigParser
import sys

sys.path.append('..')
from finviz.finvizScanner import scan_multiple_criteria
from RegimeDetector import RegimeDetector
from RiskManager import RiskManager
from alpaca_utils import get_alpaca_variables, initialize_alpaca_api, fetch_bars, calculate_atr, ATR_PERIOD
from risk_utils import calculate_risk_metrics, check_missing_stop_loss_orders, add_stop_loss_order, STOP_LOSS_ATR_MULT
from finnhub.earnings import is_earnings_at_least_days_away

# === CONFIG ===
MAX_POSITIONS = 40
MAX_POSITIONS_PER_DAY = 4  # Maximum new positions to enter per day
LONG_MA_PERIOD = 50
SHORT_MA_PERIOD = 10
EXTENDED_ATR_EXIT_MULT = 14
EXTENSION_MULT = 2.5
LIMIT_PRICE_ATR_MULT = 0.1  # ATR multiplier for limit price in stop-limit orders
TRAILING_STOP_MIN_MOVE = 0.5  # Minimum ATR move required to update trailing stop
EXCLUDE_TICKERS = ['RUM']  # List of tickers to exclude from universe
DRY_RUN = True  # Set to False to submit actual orders


def get_regime_based_risk():
    """
    Get risk percentage based on current market regime background color
    
    Returns:
        float: Risk percentage as decimal (e.g., 0.2 for 0.2%)
        
    Raises:
        Exception: If unable to fetch or validate regime data
    """
    try:
        # Fetch regime data
        regime_detector = RegimeDetector()
        regime_data = regime_detector.get_regime_info()
        background_color = regime_detector.get_background_color()
        
        # Get risk percentage based on background color
        risk_manager = RiskManager()
        risk_percentage = risk_manager.get_risk_percentage(background_color)
        
        print(f"=== Market Regime Analysis ===")
        print(f"Background Color: {background_color}")
        print(f"Risk Percentage: {risk_percentage:.1f}%")
        print(f"Can Enter Positions: {risk_manager.can_enter_positions(background_color)}")
        print(f"Above 200MA: {regime_detector.is_above_200ma()}")
        print(f"Combined MM Signals: {regime_detector.get_combined_mm_signals()}")
        
        return risk_percentage
        
    except Exception as e:
        print(f"Error fetching regime data: {e}")
        print("Falling back to default risk percentage: 0.2%")
        return 0.2  # Fallback to 0.2% if regime data unavailable


def load_universe_tickers():
    """Load tickers using the finviz screener and exclude specified tickers"""

    tickers = scan_multiple_criteria({
        'Average Volume': 'Over 100K',
        'Current Volume': 'Over 100K',
        '200-Day Simple Moving Average': 'Price above SMA200',
        'Market Cap.': '+Mid (over $2bln)',
        'Performance': 'Quarter Up',
        'EPS growthqtr over qtr': 'High (>25%)',
    }, ['Performance (Half Year)'], limit=50, remove_banned=True)
    
    # Filter out excluded tickers
    filtered_tickers = [ticker for ticker in tickers if ticker not in EXCLUDE_TICKERS]
    
    if EXCLUDE_TICKERS:
        excluded_count = len(tickers) - len(filtered_tickers)
        if excluded_count > 0:
            print(f"Excluded {excluded_count} ticker(s): {', '.join(EXCLUDE_TICKERS)}")
    
    return filtered_tickers

# === Helper Functions ===

def should_enter(df):
    if len(df) < max(ATR_PERIOD, LONG_MA_PERIOD) + 1:
        return False

    latest = df.iloc[-1]
    sma_long = df['close'].rolling(LONG_MA_PERIOD).mean().iloc[-1]
    sma_short = df['close'].rolling(SHORT_MA_PERIOD).mean().iloc[-1]

    if latest['close'] <= sma_long or sma_short <= sma_long:
        return False

    extension = latest['close'] - sma_long
    if extension > EXTENSION_MULT * latest['ATR']:
        return False

    return True

def should_exit(df):
    """Check if position should be exited based on 50-day SMA"""
    if len(df) < LONG_MA_PERIOD:
        return False
    
    latest_close = df['close'].iloc[-1]
    sma_long = df['close'].rolling(LONG_MA_PERIOD).mean().iloc[-1]
    
    return latest_close < sma_long

def should_exit_extended(df):
    """Check if position should be exited based on 50-day SMA + 10 ATRs"""
    if len(df) < LONG_MA_PERIOD:
        return False
    
    latest_close = df['close'].iloc[-1]
    sma_long = df['close'].rolling(LONG_MA_PERIOD).mean().iloc[-1]
    atr_value = df['ATR'].iloc[-1]
    
    # Exit if price >= 50-day MA + EXTENDED_ATR_EXIT_MULT ATRs
    return latest_close >= (sma_long + (EXTENDED_ATR_EXIT_MULT * atr_value))

def spy_above_long_ma():
    try:
        spy = fetch_bars('SPY', data_client, 60)
        if len(spy) < LONG_MA_PERIOD:
            return False
        sma_long = spy['close'].rolling(LONG_MA_PERIOD).mean().iloc[-1]
        return spy['close'].iloc[-1] > sma_long
    except Exception as e:
        print(f"Error fetching SPY bars: {e}")
        return False

# === Position Tracking Functions ===
def load_position_tracker():
    """Load position tracking data from JSON file"""
    try:
        with open('position_tracker.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_position_tracker(data):
    """Save position tracking data to JSON file"""
    with open('position_tracker.json', 'w') as f:
        json.dump(data, f, indent=2)

def fetch_live_alpaca_data():
    """Fetch all live data from Alpaca in minimal API calls"""
    try:
        # Fetch all positions and orders in parallel
        positions = trading_client.get_all_positions()
        account = trading_client.get_account()
        
        # Get all open orders (including stop orders)
        request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
        orders = trading_client.get_orders(filter=request)
        
        # Organize data for efficient lookup
        positions_dict = {p.symbol: p for p in positions}
        
        # Organize stop orders by symbol
        stop_orders_by_symbol = {}
        for order in orders:
            if order.side == OrderSide.SELL and order.order_type == 'stop':
                if order.symbol not in stop_orders_by_symbol:
                    stop_orders_by_symbol[order.symbol] = []
                stop_orders_by_symbol[order.symbol].append(order)
        
        return {
            'positions': positions_dict,
            'stop_orders': stop_orders_by_symbol,
            'account': account,
            'all_orders': orders
        }
        
    except Exception as e:
        print(f"Error fetching live Alpaca data: {e}")
        return None

def sync_with_alpaca_positions():
    """Sync tracking data with actual Alpaca positions (legacy function - now uses live data)"""
    try:
        alpaca_positions = trading_client.get_all_positions()
        tracking_data = load_position_tracker()
        
        # Remove positions that no longer exist
        alpaca_symbols = {p.symbol for p in alpaca_positions}
        tracking_data = {k: v for k, v in tracking_data.items() if k in alpaca_symbols}
        
        # Add new positions
        for position in alpaca_positions:
            if position.symbol not in tracking_data:
                tracking_data[position.symbol] = {
                    'entry_price': float(position.avg_entry_price),
                    'highest_price': float(position.avg_entry_price),
                    'current_stop': None,
                    'initial_r_multiple': None,  # Will be calculated when stop is set
                    'entry_date': datetime.now().isoformat(),
                    'qty': float(position.qty)
                }
                print(f"Added new position to tracker: {position.symbol}")
        
        save_position_tracker(tracking_data)
        return tracking_data
        
    except Exception as e:
        print(f"Error syncing with Alpaca positions: {e}")
        return load_position_tracker()

def get_current_stop_from_live_data(symbol, live_data, position_tracker):
    """Get current stop price from live Alpaca data, with position tracker as fallback"""
    # First, try to get from live stop orders
    if symbol in live_data['stop_orders'] and live_data['stop_orders'][symbol]:
        # Get the most recent stop order (highest stop price)
        stop_orders = live_data['stop_orders'][symbol]
        current_stop = max(float(order.stop_price) for order in stop_orders)
        return current_stop, 'live_order'
    
    # Fallback to position tracker
    if symbol in position_tracker and position_tracker[symbol]['current_stop'] is not None:
        return position_tracker[symbol]['current_stop'], 'tracker'
    
    return None, 'none'

def update_trailing_stops_with_live_data(live_data, position_tracker):
    """Update trailing stops using live Alpaca data with position tracker fallback"""
    updated_count = 0
    sync_issues = []
    
    # Get all position symbols from live data
    position_symbols = list(live_data['positions'].keys())
    
    for symbol in position_symbols:
        try:
            # Get current price and ATR
            bars = fetch_bars(symbol, data_client)
            if bars.empty:
                continue
                
            bars = calculate_atr(bars)
            current_price = bars['close'].iloc[-1]
            atr_value = bars['ATR'].iloc[-1]
            
            # Get current stop from live data or tracker
            current_stop, source = get_current_stop_from_live_data(symbol, live_data, position_tracker)
            
            # Always calculate new trailing stop based on current price and ATR
            new_stop = round(current_price - (STOP_LOSS_ATR_MULT * atr_value), 2)
            
            # Only update if new stop is higher and meets minimum move requirement
            should_update = False
            if current_stop is None:
                should_update = True
            elif new_stop > current_stop + (TRAILING_STOP_MIN_MOVE * atr_value):
                should_update = True
                
                if should_update:
                    # Check for sync issues
                    if source == 'tracker' and current_stop is not None:
                        sync_issues.append(f"{symbol}: Tracker has stop {current_stop:.2f} but no live order found")
                    
                    if DRY_RUN:
                        current_stop_str = f"{current_stop:.2f}" if current_stop is not None else "None"
                        print(f"[DRY RUN] Would update trailing stop for {symbol}: {current_stop_str} -> {new_stop:.2f} (source: {source})")
                    else:
                        # Cancel existing stop loss orders for this symbol
                        if symbol in live_data['stop_orders']:
                            for order in live_data['stop_orders'][symbol]:
                                try:
                                    trading_client.cancel_order_by_id(order.id)
                                    print(f"Cancelled stop order {order.id} for {symbol}")
                                except Exception as e:
                                    print(f"Failed to cancel stop order {order.id} for {symbol}: {e}")
                        
                        # Add new stop loss order
                        qty = int(live_data['positions'][symbol].qty)
                        add_stop_loss_order(symbol, qty, new_stop, current_price, None, trading_client, DRY_RUN)
                        
                        current_stop_str = f"{current_stop:.2f}" if current_stop is not None else "None"
                        print(f"Updated trailing stop for {symbol}: {current_stop_str} -> {new_stop:.2f} (source: {source})")
                    
                    # Update position tracker
                    if symbol not in position_tracker:
                        position_tracker[symbol] = {
                            'entry_price': float(live_data['positions'][symbol].avg_entry_price),
                            'highest_price': current_price,  # Track current price as highest
                            'current_stop': new_stop,
                            'initial_r_multiple': None,
                            'entry_date': datetime.now().isoformat(),
                            'qty': float(live_data['positions'][symbol].qty)
                        }
                    else:
                        # Update highest price to current price if it's higher
                        position_tracker[symbol]['highest_price'] = max(position_tracker[symbol]['highest_price'], current_price)
                        position_tracker[symbol]['current_stop'] = new_stop
                    
                    updated_count += 1
                    
        except Exception as e:
            print(f"Error updating trailing stop for {symbol}: {e}")
    
    # Report sync issues
    if sync_issues:
        print(f"\n=== Sync Issues Detected ===")
        for issue in sync_issues:
            print(f"WARNING: {issue}")
    
    if updated_count > 0:
        save_position_tracker(position_tracker)
        print(f"Updated {updated_count} trailing stops")
    
    return updated_count

def update_trailing_stops(position_tracker):
    """Update trailing stops for all positions (legacy function)"""
    updated_count = 0
    
    for symbol, data in position_tracker.items():
        try:
            # Get current price and ATR
            bars = fetch_bars(symbol, data_client)
            if bars.empty:
                continue
                
            bars = calculate_atr(bars)
            current_price = bars['close'].iloc[-1]
            atr_value = bars['ATR'].iloc[-1]
            
            # Update highest price
            if current_price > data['highest_price']:
                data['highest_price'] = current_price
                
                # Calculate new trailing stop
                new_stop = round(current_price - (STOP_LOSS_ATR_MULT * atr_value), 2)
                
                # Only update if new stop is higher and meets minimum move requirement
                if (data['current_stop'] is None or 
                    new_stop > data['current_stop'] + (TRAILING_STOP_MIN_MOVE * atr_value)):
                    
                    if DRY_RUN:
                        current_stop_str = f"{data['current_stop']:.2f}" if data['current_stop'] is not None else "None"
                        print(f"[DRY RUN] Would update trailing stop for {symbol}: {current_stop_str} -> {new_stop:.2f}")
                    else:
                        # Cancel existing stop loss order
                        cancel_stop_orders_for_symbol(symbol)
                        
                        # Add new stop loss order
                        qty = int(data['qty'])
                        add_stop_loss_order(symbol, qty, new_stop, current_price, None, trading_client, DRY_RUN)
                        
                        current_stop_str = f"{data['current_stop']:.2f}" if data['current_stop'] is not None else "None"
                        print(f"Updated trailing stop for {symbol}: {current_stop_str} -> {new_stop:.2f}")
                    
                    data['current_stop'] = new_stop
                    updated_count += 1
                    
        except Exception as e:
            print(f"Error updating trailing stop for {symbol}: {e}")
    
    if updated_count > 0:
        save_position_tracker(position_tracker)
        print(f"Updated {updated_count} trailing stops")
    
    return updated_count

def submit_order_with_stop_loss(symbol, qty, entry_price, atr_value, current_high, stop_loss_price, counter=None, account_value=None):
    """Submit stop-limit order with stop loss order"""
    # Use current day's high as stop price (trigger for limit order)
    buy_stop_price = round(current_high, 2)
    # Calculate limit price (entry_price + ATR * LIMIT_PRICE_ATR_MULT)
    buy_limit_price = round(buy_stop_price + (LIMIT_PRICE_ATR_MULT * atr_value), 2)
            
    if DRY_RUN:
        # Calculate risk metrics using shared function
        risk_metrics = calculate_risk_metrics(entry_price, stop_loss_price, qty, account_value)
        
        counter_text = f"[#{counter}] " if counter is not None else ""
        print(f"[DRY RUN] {counter_text}Would submit STOP-LIMIT order for {symbol}: qty={qty}, limit_price={buy_limit_price:.2f}, stop_price={buy_stop_price:.2f}, stop_loss={stop_loss_price:.2f}, risk=${risk_metrics['dollar_risk']:.2f} ({risk_metrics['percent_risk']:.2f}%), cost=${risk_metrics['position_cost']:.2f}, stop%={risk_metrics['percent_to_stop']:.2f}%")
        return True
    else:
        try:
            # Submit stop-limit order with stop loss
            order_data = StopLimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
                limit_price=buy_limit_price,
                stop_price=buy_stop_price,
                position_intent=PositionIntent.BUY_TO_OPEN
            )
            order = trading_client.submit_order(order_data)
            
            # Debug: Check if the order was created and what type it is
            print(f"Order submitted for {symbol}: ID={order.id}, Status={order.status}, Type={order.order_type}")
            
            # Calculate risk metrics using shared function
            risk_metrics = calculate_risk_metrics(entry_price, stop_loss_price, qty, account_value)
            print(f"Submitted STOP-LIMIT for {symbol}: qty={qty}, limit_price={buy_limit_price:.2f}, stop_price={buy_stop_price:.2f}, stop_loss={stop_loss_price:.2f}, risk=${risk_metrics['dollar_risk']:.2f} ({risk_metrics['percent_risk']:.2f}%), cost=${risk_metrics['position_cost']:.2f}, stop%={risk_metrics['percent_to_stop']:.2f}%")
            
            # Add position to tracker
            tracking_data = load_position_tracker()
            initial_r_multiple = round(entry_price - stop_loss_price, 2)
            tracking_data[symbol] = {
                'entry_price': entry_price,
                'highest_price': entry_price,
                'current_stop': stop_loss_price,
                'initial_r_multiple': initial_r_multiple,
                'entry_date': datetime.now().isoformat(),
                'qty': qty
            }
            save_position_tracker(tracking_data)
            print(f"Added {symbol} to position tracker with initial R multiple: {initial_r_multiple:.2f}")
            
            return True
        except Exception as e:
            print(f"Order failed for {symbol}: {e}")
            return False

def cancel_stop_orders_for_symbol(symbol):
    """Cancel all stop loss orders for a specific symbol"""
    try:
        # Get all open orders
        request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
        orders = trading_client.get_orders(filter=request)
        
        # Find and cancel stop loss orders for this symbol
        cancelled_count = 0
        for order in orders:
            if (order.symbol == symbol and 
                order.side == OrderSide.SELL and 
                order.order_type == 'stop'):
                try:
                    trading_client.cancel_order_by_id(order.id)
                    print(f"Cancelled stop order {order.id} for {symbol} (qty: {order.qty}, stop: ${order.stop_price})")
                    cancelled_count += 1
                except Exception as e:
                    print(f"Failed to cancel stop order {order.id} for {symbol}: {e}")
        
        if cancelled_count > 0:
            print(f"Cancelled {cancelled_count} stop order(s) for {symbol}")
        else:
            print(f"No stop orders found for {symbol}")
        
        return True
        
    except Exception as e:
        print(f"Error checking/canceling stop orders for {symbol}: {e}")
        return False

def close_position(symbol, qty, counter=None):
    """Close a position with a market sell order"""
    if DRY_RUN:
        counter_text = f"[#{counter}] " if counter is not None else ""
        print(f"[DRY RUN] {counter_text}Would close position for {symbol}: qty={qty}")
        return True
    else:
        try:
            # Check and cancel any stop orders for this symbol first
            print(f"Checking for stop orders before closing {symbol}...")
            cancel_stop_orders_for_symbol(symbol)
            
            # Submit market sell order to close position
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
                position_intent=PositionIntent.SELL_TO_CLOSE
            )
            order = trading_client.submit_order(order_data)
            print(f"Closed position for {symbol}, qty: {qty}")
            return True
        except Exception as e:
            print(f"Failed to close position for {symbol}: {e}")
            return False


def has_stop_loss_order(symbol):
    """Check if a position has an active stop loss order (deprecated - use check_missing_stop_loss_orders instead)"""
    try:
        request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
        orders = trading_client.get_orders(filter=request)
        
        for order in orders:
            if order.symbol == symbol and order.side == OrderSide.SELL and order.order_type == 'stop':
                return True
        return False
    except Exception as e:
        print(f"Error checking stop loss orders for {symbol}: {e}")
        return False


def main():
    # === Print execution timestamp ===
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"\n=== AlpacaTrend.py Execution Started ===")
    print(f"Timestamp: {current_time}")
    print(f"Dry Run Mode: {DRY_RUN}")
    
    # === Initialize API and Load Data ===
    global trading_client, data_client
    trading_client, data_client = initialize_alpaca_api()
    tickers = load_universe_tickers()
    
    # === Print initial ticker list ===
    print(f"\n=== Initial Ticker List ({len(tickers)} tickers) ===")
    print(','.join(tickers))
    print(f"Finviz URL: https://finviz.com/screener.ashx?v=310&f=cap_midover,fa_epsqoq_high,sh_avgvol_o100,sh_curvol_o100,ta_perf_13wup,ta_sma200_pa&ft=4&o=-perf26w&t={','.join(tickers)}")
    
    # === Get Dynamic Risk Percentage Based on Market Regime ===
    percent_risk = get_regime_based_risk()
    
    # === Check if positions can be entered based on regime ===
    can_enter = False  # Default to conservative approach
    try:
        regime_detector = RegimeDetector()
        regime_data = regime_detector.get_regime_info()
        background_color = regime_detector.get_background_color()
        
        risk_manager = RiskManager()
        can_enter = risk_manager.can_enter_positions(background_color)
        
        if not can_enter:
            print(f"Market regime is {background_color.upper()} - no new positions allowed.")
            return
            
    except Exception as e:
        print(f"Error checking regime for position entry: {e}")
        print("Proceeding with caution...")
        can_enter = False  # Default to conservative approach
    
    # === Check SPY Trend for Entry Eligibility ===
    spy_above_ma = spy_above_long_ma()
    if not spy_above_ma:
        print("SPY is below long MA – no new entries allowed.")
    else:
        print("SPY is above long MA – new entries allowed.")

    # Fetch all live data from Alpaca in minimal API calls
    print("\n=== Fetching Live Alpaca Data ===")
    live_data = fetch_live_alpaca_data()
    if live_data is None:
        print("Failed to fetch live data, falling back to legacy approach")
        positions = trading_client.get_all_positions()
        account = trading_client.get_account()
        account_value = float(account.portfolio_value)
        held_symbols = set([p.symbol for p in positions])
        position_tracker = sync_with_alpaca_positions()
    else:
        positions = list(live_data['positions'].values())
        account = live_data['account']
        account_value = float(account.portfolio_value)
        held_symbols = set(live_data['positions'].keys())
        
        # Load position tracker for fallback data
        position_tracker = load_position_tracker()
        
        print(f"Fetched {len(positions)} positions and {len(live_data['all_orders'])} orders")
        print(f"Found {len(live_data['stop_orders'])} symbols with stop orders")

    # === Exit Logic - Check existing positions ===
    print("Checking existing positions for exits...")
    exit_counter = 0
    missing_stops = []
    position_symbols = []
    closed_positions = []  # Track positions that were successfully closed
    
    for position in positions:
        symbol = position.symbol
        qty = float(position.qty)
        
        if qty <= 0:  # Skip short positions
            continue
            
        exit_counter += 1
        position_symbols.append(symbol)
        bars = fetch_bars(symbol, data_client)
        if bars.empty:
            continue
            
        bars = calculate_atr(bars)
        
        if should_exit(bars):
            print(f"Exit signal for {symbol}: price below long MA {LONG_MA_PERIOD}")
            if close_position(symbol, qty, exit_counter):
                closed_positions.append(symbol)
        elif should_exit_extended(bars):
            print(f"Exit signal for {symbol}: EXTENDED: price >= 50-day MA + 10 ATRs")
            if close_position(symbol, qty, exit_counter):
                closed_positions.append(symbol)
    
    # === Update Trailing Stops ===
    print("\n=== Updating Trailing Stops ===")
    if live_data is not None:
        trailing_updates = update_trailing_stops_with_live_data(live_data, position_tracker)
    else:
        trailing_updates = update_trailing_stops(position_tracker)
    
    # Check for missing stop loss orders in batch
    if position_symbols:
        if live_data is not None:
            # Use live data to find missing stops
            symbols_needing_stops = [symbol for symbol in position_symbols 
                                   if symbol not in live_data['stop_orders'] or not live_data['stop_orders'][symbol]]
        else:
            symbols_needing_stops = check_missing_stop_loss_orders(position_symbols, trading_client)
        
        # Filter out symbols that were just closed
        symbols_needing_stops = [symbol for symbol in symbols_needing_stops if symbol not in closed_positions]
        
        if closed_positions:
            print(f"Excluding {len(closed_positions)} closed position(s) from stop loss creation: {', '.join(closed_positions)}")
        
        # Calculate stop prices for symbols needing stops
        for symbol in symbols_needing_stops:
            bars = fetch_bars(symbol, data_client)
            if not bars.empty:
                bars = calculate_atr(bars)
                current_price = bars['close'].iloc[-1]
                atr_value = bars['ATR'].iloc[-1]
                stop_price = round(current_price - (STOP_LOSS_ATR_MULT * atr_value), 2)
                
                # Find the position quantity for this symbol
                for position in positions:
                    if position.symbol == symbol:
                        qty = float(position.qty)
                        missing_stops.append((symbol, qty, stop_price, current_price))
                        break
    
    # Add missing stop loss orders
    if missing_stops:
        print(f"\n=== Adding Missing Stop Loss Orders ({len(missing_stops)} positions) ===")
        for symbol, qty, stop_price, current_price in missing_stops:
            add_stop_loss_order(symbol, qty, stop_price, current_price, account_value, trading_client, DRY_RUN)
            
            # Update position tracker with initial R multiple
            if symbol in position_tracker:
                entry_price = position_tracker[symbol]['entry_price']
                initial_r_multiple = round(entry_price - stop_price, 2)
                position_tracker[symbol]['initial_r_multiple'] = initial_r_multiple
                position_tracker[symbol]['current_stop'] = stop_price
                print(f"Updated {symbol} initial R multiple: {initial_r_multiple:.2f}")
        
        save_position_tracker(position_tracker)
    else:
        print("\n=== All positions have stop loss orders ===")

    # === Entry Logic - Find new positions ===
    entry_candidates = []
    entry_counter = 0

    # Only look for new entries if both market regime and SPY conditions allow it
    can_enter_new_positions = can_enter and spy_above_ma
    
    if can_enter_new_positions:
        print("Both market regime and SPY trend allow new entries - scanning for candidates...")
        
        for ticker in tickers:
            if ticker in held_symbols:
                continue

            entry_counter += 1
            bars = fetch_bars(ticker, data_client)
            if bars.empty:
                continue

            bars = calculate_atr(bars)

            if should_enter(bars):
                # Check if earnings are at least 8 days away
                if is_earnings_at_least_days_away(ticker, min_days=8):
                    latest = bars.iloc[-1]
                    entry_candidates.append((ticker, latest['close'], latest['ATR'], latest['high']))
                else:
                    print(f"Skipping {ticker} - earnings within 8 days")
    else:
        if not can_enter:
            print("Market regime blocks new entries.")
        if not spy_above_ma:
            print("SPY trend blocks new entries.")
        print("Skipping entry candidate scanning.")

    available_slots = MAX_POSITIONS - len(held_symbols)
    daily_entry_limit = min(available_slots, MAX_POSITIONS_PER_DAY)

    if daily_entry_limit > 0 and can_enter_new_positions:
        to_enter = entry_candidates[:daily_entry_limit]
        # Calculate risk per position as percentage of account value
        risk_per_position = account_value * (percent_risk / 100)

        order_counter = 0
        for symbol, price, atr_value, current_high in to_enter:
            order_counter += 1
            # Calculate risk per share (entry price - stop loss price)
            stop_loss_price = round(price - (STOP_LOSS_ATR_MULT * atr_value), 2)
            risk_per_share = price - stop_loss_price
            
            # Calculate quantity based on risk per position
            if risk_per_share > 0:
                qty = int(risk_per_position // risk_per_share)
                if qty > 0:
                    submit_order_with_stop_loss(symbol, qty, price, atr_value, current_high, stop_loss_price, order_counter, account_value)
    else:
        if not can_enter_new_positions:
            print("Entry conditions not met - no new trades placed.")
        elif available_slots <= 0:
            print("Max positions reached. No new trades placed.")
        else:
            print(f"Daily entry limit reached ({MAX_POSITIONS_PER_DAY} positions). No new trades placed.")

    # === Print CSV of tickers for entries ===
    if daily_entry_limit > 0 and can_enter_new_positions and to_enter:
        print("\n=== Tickers for Entry ===")
        print("Symbol,Price,ATR,Stop_Price,Quantity")
        
        for symbol, price, atr_value, current_high in to_enter:
            # Calculate risk per share (entry price - stop loss price)
            stop_price = round(price - (STOP_LOSS_ATR_MULT * atr_value), 2)
            risk_per_share = price - stop_price
            
            # Calculate quantity based on risk per position
            if risk_per_share > 0:
                qty = int(risk_per_position // risk_per_share)
                if qty > 0:
                    stop_price_rounded = round(stop_price, 2)
                    print(f"{symbol},{price:.2f},{atr_value:.2f},{stop_price_rounded:.2f},{qty}")
        
        # Print single line CSV format
        entry_symbols = [symbol for symbol, _, _, _ in to_enter]
        print(f"\n=== Entry Candidates ({len(entry_symbols)} tickers) ===")
        print(','.join(entry_symbols))
    else:
        print("\n=== No tickers for entry ===")

    # === Calculate and Print Total Risk Summary ===
    print("\n=== Risk Summary ===")
    total_dollar_risk = 0
    total_position_value = 0
    
    # Calculate risk for existing positions
    for position in positions:
        symbol = position.symbol
        qty = float(position.qty)
        
        if qty <= 0:  # Skip short positions
            continue
            
        bars = fetch_bars(symbol, data_client)
        if not bars.empty:
            bars = calculate_atr(bars)
            current_price = bars['close'].iloc[-1]
            atr_value = bars['ATR'].iloc[-1]
            stop_price = round(current_price - (STOP_LOSS_ATR_MULT * atr_value), 2)
            # Calculate risk metrics using shared function
            risk_metrics = calculate_risk_metrics(current_price, stop_price, qty, account_value)
            total_dollar_risk += risk_metrics['dollar_risk']
            total_position_value += risk_metrics['position_cost']
    
    # Calculate risk for new entries
    if daily_entry_limit > 0 and can_enter_new_positions and to_enter:
        risk_per_position = account_value * (percent_risk / 100)
        for symbol, price, atr_value, current_high in to_enter:
            # Calculate risk per share (entry price - stop loss price)
            stop_price = round(price - (STOP_LOSS_ATR_MULT * atr_value), 2)
            risk_per_share = price - stop_price
            
            # Calculate quantity based on risk per position
            if risk_per_share > 0:
                qty = int(risk_per_position // risk_per_share)
                if qty > 0:
                    stop_price_rounded = round(stop_price, 2)
                    # Calculate risk metrics using shared function
                    risk_metrics = calculate_risk_metrics(price, stop_price_rounded, qty, account_value)
                    total_dollar_risk += risk_metrics['dollar_risk']
                    total_position_value += risk_metrics['position_cost']
    
    total_percent_risk = (total_dollar_risk / account_value * 100) if account_value > 0 else 0
    print(f"Total Dollar Risk: ${total_dollar_risk:.2f}")
    print(f"Total Account Risk: {total_percent_risk:.2f}%")
    print(f"Total Position Value: ${total_position_value:.2f}")
    print(f"Account Value: ${account_value:.2f}")

    # === Write execution timestamp to JSON file for UI monitoring ===
    try:
        # Create timestamp data
        timestamp_data = {
            "last_execution": datetime.now().isoformat(),
            "execution_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"),
            "dry_run_mode": DRY_RUN
        }
        
        # Write to JSON file in ui directory
        ui_json_path = os.path.join('..', 'ui', 'trend-trader-status.json')
        with open(ui_json_path, 'w') as f:
            json.dump(timestamp_data, f, indent=2)
        
        print(f"\n=== Execution Status Written ===")
        print(f"Status file: {ui_json_path}")
        print(f"Last execution: {timestamp_data['execution_timestamp']}")
        
    except Exception as e:
        print(f"Error writing execution status: {e}")

if __name__ == "__main__":
    main()