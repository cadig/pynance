"""
Risk Management Module for Dynamic Position Sizing

This module provides risk management functionality based on market regime
background colors, adjusting position risk percentages accordingly.

Additionally, this module can be run as a standalone script to monitor
and ensure all positions have stop loss orders.
"""

import pandas as pd
import numpy as np
import json
import os
import sys
from typing import Dict, Optional, List, Tuple
from enum import Enum
from datetime import datetime, timedelta, timezone
from configparser import ConfigParser
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, PositionIntent

# Add parent directory to path for imports
sys.path.append('..')

# Import shared utilities
from alpaca_utils import get_alpaca_variables, initialize_alpaca_api, fetch_bars, calculate_atr, ATR_PERIOD
from risk_utils import calculate_risk_metrics, check_missing_stop_loss_orders, add_stop_loss_order, cancel_stop_orders, reconcile_position_qty, STOP_LOSS_ATR_MULT
from finnhub.earnings import get_earnings_with_hour

class RiskLevel(Enum):
    """Risk level enumeration based on background colors"""
    RED = "red"
    ORANGE = "orange" 
    YELLOW = "yellow"
    GREEN = "green"

class RiskManager:
    """Manages position risk based on market regime background color"""
    
    # Risk percentage mapping based on background color
    RISK_PERCENTAGES = {
        RiskLevel.RED: 0.0,      # No new positions
        RiskLevel.ORANGE: 0.1,   # 0.1% risk per position
        RiskLevel.YELLOW: 0.3,   # 0.3% risk per position
        RiskLevel.GREEN: 0.5     # 0.5% risk per position
    }
    
    def __init__(self):
        self.current_risk_level: Optional[RiskLevel] = None
        self.current_risk_percentage: Optional[float] = None
    
    def set_risk_level(self, background_color: str) -> None:
        """
        Set the current risk level based on background color
        
        Args:
            background_color: Background color string ('red', 'orange', 'yellow', 'green')
            
        Raises:
            ValueError: If background_color is invalid
        """
        try:
            self.current_risk_level = RiskLevel(background_color.lower())
            self.current_risk_percentage = self.RISK_PERCENTAGES[self.current_risk_level]
        except ValueError:
            valid_colors = [level.value for level in RiskLevel]
            raise ValueError(f"Invalid background color: {background_color}. Must be one of {valid_colors}")
    
    def get_risk_percentage(self, background_color: str) -> float:
        """
        Get risk percentage for a given background color
        
        Args:
            background_color: Background color string
            
        Returns:
            Risk percentage as decimal (e.g., 0.2 for 0.2%)
            
        Raises:
            ValueError: If background_color is invalid
        """
        try:
            risk_level = RiskLevel(background_color.lower())
            return self.RISK_PERCENTAGES[risk_level]
        except ValueError:
            valid_colors = [level.value for level in RiskLevel]
            raise ValueError(f"Invalid background color: {background_color}. Must be one of {valid_colors}")
    
    def can_enter_positions(self, background_color: str) -> bool:
        """
        Check if new positions can be entered based on background color
        
        Args:
            background_color: Background color string
            
        Returns:
            True if positions can be entered, False otherwise
        """
        risk_percentage = self.get_risk_percentage(background_color)
        return risk_percentage > 0.0
    
    def get_current_risk_percentage(self) -> float:
        """
        Get the current risk percentage
        
        Returns:
            Current risk percentage as decimal
            
        Raises:
            ValueError: If no risk level has been set
        """
        if self.current_risk_percentage is None:
            raise ValueError("No risk level has been set. Call set_risk_level() first.")
        
        return self.current_risk_percentage
    
    def get_current_risk_level(self) -> RiskLevel:
        """
        Get the current risk level
        
        Returns:
            Current RiskLevel enum value
            
        Raises:
            ValueError: If no risk level has been set
        """
        if self.current_risk_level is None:
            raise ValueError("No risk level has been set. Call set_risk_level() first.")
        
        return self.current_risk_level
    
    def get_risk_info(self, background_color: str) -> Dict[str, any]:
        """
        Get comprehensive risk information for a background color
        
        Args:
            background_color: Background color string
            
        Returns:
            Dictionary containing risk information
        """
        risk_percentage = self.get_risk_percentage(background_color)
        can_enter = self.can_enter_positions(background_color)
        
        return {
            'background_color': background_color,
            'risk_percentage': risk_percentage,
            'risk_percentage_formatted': f"{risk_percentage:.1f}%",
            'can_enter_positions': can_enter,
            'risk_level': RiskLevel(background_color.lower()).name
        }

def get_risk_percentage_for_color(background_color: str) -> float:
    """
    Convenience function to get risk percentage for a background color
    
    Args:
        background_color: Background color string
        
    Returns:
        Risk percentage as decimal
    """
    risk_manager = RiskManager()
    return risk_manager.get_risk_percentage(background_color)

def can_enter_positions_for_color(background_color: str) -> bool:
    """
    Convenience function to check if positions can be entered for a background color
    
    Args:
        background_color: Background color string
        
    Returns:
        True if positions can be entered, False otherwise
    """
    risk_manager = RiskManager()
    return risk_manager.can_enter_positions(background_color)


# === Constants ===
DRY_RUN = True  # Set to False to submit actual orders
EARNINGS_PROFIT_THRESHOLD_ATR = 8.0  # ATR profit needed to hold through earnings

def check_earnings_proximity(positions, trading_client, data_client, dry_run=True):
    """
    Close positions reporting earnings imminently unless they have >= 8 ATR open profit.

    'Imminent' means:
    - Earnings after market close today (amc) and it's already past 2pm ET
    - Earnings before market open tomorrow (bmo) with date = tomorrow
    - Earnings today with unknown hour (treat conservatively)

    Positions with >= EARNINGS_PROFIT_THRESHOLD_ATR open profit are kept.
    """
    from pytz import timezone as pytz_tz
    et = pytz_tz('US/Eastern')
    now_et = datetime.now(et)
    today = now_et.date()
    tomorrow = today + timedelta(days=1)
    is_late_session = now_et.hour >= 14  # 2pm ET or later

    closed_symbols = []

    print(f"\n=== Earnings Proximity Check ===")
    print(f"Current time (ET): {now_et.strftime('%Y-%m-%d %H:%M ET')}")

    for position in positions:
        symbol = position.symbol
        qty = float(position.qty)
        if qty <= 0:
            continue

        try:
            earnings_info = get_earnings_with_hour(symbol)
            if earnings_info is None:
                continue

            earnings_date = earnings_info['date'].date()
            earnings_hour = earnings_info['hour']  # 'bmo', 'amc', or ''

            # Determine if earnings are imminent
            imminent = False
            reason = ""
            if earnings_date == today and earnings_hour == 'amc' and is_late_session:
                imminent = True
                reason = "reports after close today"
            elif earnings_date == tomorrow and earnings_hour == 'bmo':
                imminent = True
                reason = "reports before open tomorrow"
            elif earnings_date == today and earnings_hour == '' and is_late_session:
                # Unknown hour, today, late in session — treat conservatively
                imminent = True
                reason = "reports today (unknown hour)"
            elif earnings_date == tomorrow and earnings_hour == '':
                imminent = True
                reason = "reports tomorrow (unknown hour)"

            if not imminent:
                continue

            # Check open profit in ATR terms
            bars = fetch_bars(symbol, data_client)
            if bars.empty:
                print(f"  {symbol}: {reason} but no price data — skipping")
                continue

            bars = calculate_atr(bars)
            current_price = bars['close'].iloc[-1]
            atr_value = bars['ATR'].iloc[-1]
            entry_price = float(position.avg_entry_price)
            profit_atr = (current_price - entry_price) / atr_value if atr_value > 0 else 0

            if profit_atr >= EARNINGS_PROFIT_THRESHOLD_ATR:
                print(f"  {symbol}: {reason}, but {profit_atr:.1f} ATR profit >= {EARNINGS_PROFIT_THRESHOLD_ATR} — holding through earnings")
                continue

            # Close the position
            print(f"  {symbol}: {reason}, only {profit_atr:.1f} ATR profit — closing position")

            if dry_run:
                print(f"  [DRY RUN] Would close {symbol}: qty={int(qty)}")
                print(f"  [DRY RUN] Would cancel stop orders for {symbol}")
            else:
                # Cancel stop orders first
                cancel_stop_orders(symbol, trading_client, dry_run=False)
                # Close position
                try:
                    order_data = MarketOrderRequest(
                        symbol=symbol,
                        qty=int(qty),
                        side=OrderSide.SELL,
                        time_in_force=TimeInForce.DAY,
                        position_intent=PositionIntent.SELL_TO_CLOSE
                    )
                    trading_client.submit_order(order_data)
                    print(f"  Closed {symbol}: qty={int(qty)}")
                except Exception as e:
                    print(f"  Failed to close {symbol}: {e}")
                    continue

            closed_symbols.append(symbol)

        except Exception as e:
            print(f"  Error checking earnings for {symbol}: {e}")

    if not closed_symbols:
        print("  No positions with imminent earnings to close")
    else:
        print(f"  Closed {len(closed_symbols)} position(s) before earnings: {', '.join(closed_symbols)}")

    return closed_symbols


def ensure_all_positions_have_stop_losses():
    """
    Main function to ensure all positions have stop loss orders.
    This replicates the exact logic from trendTrader.py
    """
    print(f"\n=== RiskManager Stop Loss Monitor ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Dry Run Mode: {DRY_RUN}")
    
    # Initialize API
    trading_client, data_client = initialize_alpaca_api()
    
    # Get all positions
    try:
        positions = trading_client.get_all_positions()
        account = trading_client.get_account()
        account_value = float(account.portfolio_value)
        
        print(f"Found {len(positions)} positions")
        print(f"Account Value: ${account_value:,.2f}")
        
        if not positions:
            print("No positions found - nothing to monitor")
            return
        
        # Get position symbols
        long_positions = [p for p in positions if float(p.qty) > 0]

        if not long_positions:
            print("No long positions found - nothing to monitor")
            return

        # Check earnings proximity — close positions reporting imminently without enough profit
        closed_for_earnings = check_earnings_proximity(long_positions, trading_client, data_client, DRY_RUN)

        # Exclude positions closed for earnings from stop loss check
        position_symbols = [p.symbol for p in long_positions if p.symbol not in closed_for_earnings]

        if not position_symbols:
            print("No remaining positions to check for stop losses")
            return

        # Check for missing stop loss orders
        symbols_needing_stops = check_missing_stop_loss_orders(position_symbols, trading_client)
        
        if not symbols_needing_stops:
            print("✅ All positions have stop loss orders")
            return
        
        print(f"\n=== Adding Missing Stop Loss Orders ({len(symbols_needing_stops)} positions) ===")
        
        # Add missing stop loss orders
        for symbol in symbols_needing_stops:
            # Find the position for this symbol
            position = None
            for p in positions:
                if p.symbol == symbol and float(p.qty) > 0:
                    position = p
                    break
            
            if not position:
                print(f"⚠️  Position not found for {symbol}")
                continue
            
            # Get current price and ATR
            bars = fetch_bars(symbol, data_client)
            if bars.empty:
                print(f"⚠️  No price data for {symbol}")
                continue
            
            bars = calculate_atr(bars)
            current_price = bars['close'].iloc[-1]
            atr_value = bars['ATR'].iloc[-1]
            
            if pd.isna(atr_value):
                print(f"⚠️  No ATR data for {symbol}")
                continue
            
            # Calculate stop price
            stop_price = round(current_price - (STOP_LOSS_ATR_MULT * atr_value), 2)

            # Reconcile live quantity before placing stop (handles partial fills)
            qty = reconcile_position_qty(symbol, float(position.qty), trading_client)
            if qty <= 0:
                continue

            # Add stop loss order
            success = add_stop_loss_order(
                symbol, qty, stop_price, current_price, account_value, trading_client, DRY_RUN
            )
            
            if success:
                print(f"✅ Stop loss order processed for {symbol}")
            else:
                print(f"❌ Failed to add stop loss order for {symbol}")
        
        print(f"\n=== Stop Loss Monitoring Complete ===")
        
        # === Write execution timestamp to JSON file for UI monitoring ===
        try:
            # Create timestamp data
            timestamp_data = {
                "last_execution": datetime.now().isoformat(),
                "execution_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"),
                "dry_run_mode": DRY_RUN,
                "account_value": account_value,
                "total_positions": len(positions),
                "positions_with_stops": len(positions) - len(symbols_needing_stops) if 'symbols_needing_stops' in locals() else len(positions),
                "positions_needing_stops": len(symbols_needing_stops) if 'symbols_needing_stops' in locals() else 0
            }
            
            # Write to JSON file in ui directory
            ui_json_path = os.path.join('..', 'ui', 'risk-manager-status.json')
            with open(ui_json_path, 'w') as f:
                json.dump(timestamp_data, f, indent=2)
            
            print(f"\n=== Execution Status Written ===")
            print(f"Status file: {ui_json_path}")
            print(f"Last execution: {timestamp_data['execution_timestamp']}")
            print(f"Positions with stops: {timestamp_data['positions_with_stops']}")
            print(f"Positions needing stops: {timestamp_data['positions_needing_stops']}")
            
        except Exception as json_error:
            print(f"Error writing execution status: {json_error}")
        
    except Exception as e:
        print(f"❌ Error during stop loss monitoring: {e}")
        return

if __name__ == "__main__":
    # Run stop loss monitoring as the main functionality
    print("=== RiskManager.py - Stop Loss Monitor ===")
    print("This script ensures all positions have stop loss orders")
    print("Run this more frequently than trendTrader.py via cron job")
    print()
    
    # Execute the stop loss monitoring
    ensure_all_positions_have_stop_losses()
    
    # Also demonstrate risk management functionality
    print(f"\n=== Risk Management by Background Color (Demo) ===")
    risk_manager = RiskManager()
    
    colors = ['red', 'orange', 'yellow', 'green']
    for color in colors:
        try:
            risk_info = risk_manager.get_risk_info(color)
            print(f"{color.upper()}: {risk_info['risk_percentage_formatted']} risk, Can Enter: {risk_info['can_enter_positions']}")
        except ValueError as e:
            print(f"Error for {color}: {e}")
