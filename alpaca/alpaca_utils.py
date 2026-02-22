"""
Alpaca API Utilities

Shared utility functions for Alpaca API operations across the trading system.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from configparser import ConfigParser
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.requests import StopOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus

from config import ATR_PERIOD, STOP_LOSS_ATR_MULT

# Per-execution bar cache: avoids redundant Alpaca Data API calls for the
# same symbol within a single script run.  Cleared automatically on exit;
# call clear_bar_cache() explicitly if you need a mid-run reset.
_bar_cache = {}

def clear_bar_cache():
    """Clear the in-memory bar cache"""
    _bar_cache.clear()

def get_alpaca_variables(whichAccount: str):
    """Get Alpaca API credentials from config file"""
    config = ConfigParser()
    config.read('../../config/alpaca-config.ini')
    return {
        'api_key': config.get(whichAccount, 'API_KEY'),
        'api_secret': config.get(whichAccount, 'API_SECRET'),
    }

def initialize_alpaca_api():
    """Initialize Alpaca trading and data clients"""
    alpaca_config = get_alpaca_variables('paper')
    trading_client = TradingClient(
        api_key=alpaca_config['api_key'], 
        secret_key=alpaca_config['api_secret'], 
    )
    data_client = StockHistoricalDataClient(
        api_key=alpaca_config['api_key'],
        secret_key=alpaca_config['api_secret'],
    )
    return trading_client, data_client

def fetch_bars(symbol, data_client, limit=100):
    """Fetch historical bars for a symbol (cached per execution)"""
    if symbol in _bar_cache:
        return _bar_cache[symbol].copy()

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=100)
    try:
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
        )
        bars = data_client.get_stock_bars(request_params)
        if bars and hasattr(bars, 'df'):
            _bar_cache[symbol] = bars.df
            return bars.df.copy()
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
    return pd.DataFrame()

def calculate_atr(df, period=ATR_PERIOD):
    """Calculate Average True Range (ATR) for a dataframe"""
    df['H-L'] = df['high'] - df['low']
    df['H-PC'] = np.abs(df['high'] - df['close'].shift(1))
    df['L-PC'] = np.abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(period).mean()
    return df
