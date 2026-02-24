"""
Alpaca Trading System — Centralized Configuration

All risk parameters, trading constants, and system settings in one place.
Mirrors the pattern used in allocation/config.py.
"""

# ---------------------------------------------------------------------------
# Execution mode
# ---------------------------------------------------------------------------
DRY_RUN = True  # Set to False to submit actual orders

# ---------------------------------------------------------------------------
# Risk per position (flat % of account value risked per trade)
# ---------------------------------------------------------------------------
RISK_PER_TRADE = 0.4  # 0.4% of account risked per trade, regardless of regime

# Legacy risk percentages — kept for RiskManager backward compatibility
RISK_PERCENTAGES = {
    'red':    0.0,
    'orange': RISK_PER_TRADE,
    'yellow': RISK_PER_TRADE,
    'green':  RISK_PER_TRADE,
}

# ---------------------------------------------------------------------------
# Regime-based entry pace (how many new entries per day by regime color)
# ---------------------------------------------------------------------------
MAX_ENTRIES_BY_REGIME = {
    'red':    0,   # No entries
    'orange': 1,   # Cautious — 1 entry per day
    'yellow': 3,   # Moderate — 3 entries per day
    'green':  4,   # Full pace — 4 entries per day
}

# ---------------------------------------------------------------------------
# Pyramiding (adding to winners)
# ---------------------------------------------------------------------------
PYRAMID_R_THRESHOLD = 3.0      # Add to position after 3R profit
PYRAMID_SIZE_FRACTION = 0.5    # Add 50% of original qty
PYRAMID_MAX_ADDS = 1           # Maximum pyramid adds per position

# ---------------------------------------------------------------------------
# ATR & stop loss
# ---------------------------------------------------------------------------
ATR_PERIOD = 20
STOP_LOSS_ATR_MULT = 4.0
RED_REGIME_STOP_ATR_MULT = 2.0   # Tighter stop multiplier when regime is red
TRAILING_STOP_MIN_MOVE = 0.5     # Minimum ATR move required to update trailing stop

# ---------------------------------------------------------------------------
# Position sizing & limits
# ---------------------------------------------------------------------------
MAX_POSITIONS = 40
MAX_POSITIONS_PER_DAY = 4        # Maximum new positions to enter per day

# ---------------------------------------------------------------------------
# Moving averages & trend
# ---------------------------------------------------------------------------
LONG_MA_PERIOD = 50
SHORT_MA_PERIOD = 10

# ---------------------------------------------------------------------------
# Entry & exit filters
# ---------------------------------------------------------------------------
EXTENSION_MULT = 2.5             # Max extension from 50MA (in ATRs) allowed at entry
EXTENDED_ATR_EXIT_MULT = 14      # ATR multiple above 50MA for overextension exit
LIMIT_PRICE_ATR_MULT = 0.3      # ATR multiplier for limit price in stop-limit orders
MA_BREAK_STOP_BUFFER_ATR = 0.5  # ATR buffer below candle low when tightening stop on 50MA break
MA_EXIT_COOLDOWN_DAYS = 3       # Trading days to wait before re-entering a stock after 50MA exit
VIX_ENTRY_THRESHOLD = 25         # VIX above this blocks new entries

# ---------------------------------------------------------------------------
# Earnings
# ---------------------------------------------------------------------------
EARNINGS_MIN_DAYS_AWAY = 8                  # Minimum days until earnings to allow entry
EARNINGS_PROFIT_THRESHOLD_ATR = 8.0         # ATR profit needed to hold through earnings

# ---------------------------------------------------------------------------
# Universe filtering
# ---------------------------------------------------------------------------
EXCLUDE_TICKERS = ['RUM', 'EXAS', 'AAUC']        # Tickers excluded from universe scan
UNIVERSE_BREADTH_THRESHOLD = 0.40  # Min % of universe above 50MA to allow new entries

# ---------------------------------------------------------------------------
# Regime data source
# ---------------------------------------------------------------------------
REGIME_URL = "https://cadig.github.io/pynance/spx-regime-results.json"
