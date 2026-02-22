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
# Risk per position (% of account value risked per trade, by regime)
# ---------------------------------------------------------------------------
RISK_PERCENTAGES = {
    'red':    0.0,   # No new positions
    'orange': 0.1,   # 0.1% risk per position
    'yellow': 0.3,   # 0.3% risk per position
    'green':  0.5,   # 0.5% risk per position
}

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
VIX_ENTRY_THRESHOLD = 25         # VIX above this blocks new entries

# ---------------------------------------------------------------------------
# Earnings
# ---------------------------------------------------------------------------
EARNINGS_MIN_DAYS_AWAY = 8                  # Minimum days until earnings to allow entry
EARNINGS_PROFIT_THRESHOLD_ATR = 8.0         # ATR profit needed to hold through earnings

# ---------------------------------------------------------------------------
# Universe filtering
# ---------------------------------------------------------------------------
EXCLUDE_TICKERS = ['RUM']        # Tickers excluded from universe scan

# ---------------------------------------------------------------------------
# Regime data source
# ---------------------------------------------------------------------------
REGIME_URL = "https://cadig.github.io/pynance/spx-regime-results.json"
