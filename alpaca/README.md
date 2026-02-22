# Alpaca Trend Trading System

Automated long-only equity trend-following system that trades via the Alpaca API. Two scripts run on separate schedules: **trendTrader.py** (daily, finds entries and exits) and **RiskManager.py** (more frequently, ensures every position has a stop loss).

## How It Works

### Market Gatekeeping (3 checks before any new entry)

1. **Market regime** — Fetches the pynance regime signal (green/yellow/orange/red background color) from GitHub Pages. Red regime = no new entries. Other regimes set how much risk per trade (green 0.5%, yellow 0.3%, orange 0.1%).
2. **VIX check** — If VIX closes above 25, all new entries are blocked regardless of regime color.
3. **SPY trend** — SPY must be above its 50-day moving average for any new entries.

All three must pass. If any fail, the system only manages existing positions (trailing stops, exits) and places no new trades.

### Universe Selection (Finviz Screener)

The stock universe is built fresh each run using a Finviz screener with these filters:
- Mid-cap or larger (>$2B)
- Price above 200-day SMA
- Quarter performance positive
- EPS growth QoQ > 25%
- Average and current volume > 100K
- Sorted by 6-month performance, top 50

### Entry Rules

A stock passes the entry filter when:
1. Price is **above the 50-day SMA**
2. The **10-day SMA is above the 50-day SMA** (short-term trend confirmation)
3. Price is **not extended** — the gap between price and the 50-day SMA must be less than 2.5 ATRs
4. **Earnings are at least 8 days away** (avoids binary event risk)

Orders are placed as **stop-limit buys** — the stop (trigger) price is the current day's high, and the limit price is slightly above that (0.1 ATR). This means the stock must break above today's high to trigger a fill, confirming upward momentum.

Up to **4 new positions per day**, max **40 total positions**.

### Position Sizing

Each position is sized so that the dollar risk (entry price minus stop loss) equals a fixed percentage of the account value. That percentage comes from the regime color:
- Green: 0.5% risk per trade
- Yellow: 0.3%
- Orange: 0.1%
- Red: 0% (no entries)

### Stop Losses (ATR-Based Trailing Stops)

Every position gets a stop loss order at **entry price minus 4 ATRs** (20-day ATR).

Stops trail upward: when price makes a new high and the new calculated stop is meaningfully higher (at least 0.5 ATR above the current stop), the old stop order is cancelled and replaced with the higher one. Stops never move down.

### Exit Rules

Positions are sold via market order when either condition is met:
1. **Trend breakdown** — price closes below the 50-day SMA
2. **Overextension** — price reaches 50-day SMA + 14 ATRs (takes profit on parabolic moves)

Stop losses handle the downside exits independently via Alpaca's order system.

### RiskManager.py (Stop Loss Monitor)

Runs on a more frequent schedule than the main trader. Its only job: scan all open positions, find any that are missing a stop loss order (e.g., if a stop was triggered and partially filled, or an order was manually cancelled), and place new stop loss orders for them. This is a safety net.

## Files

| File | Role |
|------|------|
| `trendTrader.py` | Main script — universe scan, entries, exits, trailing stops |
| `RiskManager.py` | Risk percentage logic + standalone stop loss monitor |
| `RegimeDetector.py` | Fetches regime data from pynance GitHub Pages, validates freshness |
| `alpaca_utils.py` | Alpaca API init, bar fetching, ATR calculation |
| `risk_utils.py` | Risk metric calculations, stop loss order helpers |
| `position_tracker.json` | Local state — tracks entry price, highest price, current stop per position |

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `ATR_PERIOD` | 20 | Days for ATR calculation |
| `STOP_LOSS_ATR_MULT` | 4.0 | ATRs below price for stop loss |
| `LONG_MA_PERIOD` | 50 | Moving average for trend filter |
| `SHORT_MA_PERIOD` | 10 | Short MA for entry confirmation |
| `EXTENSION_MULT` | 2.5 | Max ATRs above 50-day SMA to enter |
| `EXTENDED_ATR_EXIT_MULT` | 14 | ATRs above 50-day SMA to exit (overextension) |
| `MAX_POSITIONS` | 40 | Portfolio capacity |
| `MAX_POSITIONS_PER_DAY` | 4 | Daily entry limit |
| `DRY_RUN` | True | Set to False to submit real orders |
