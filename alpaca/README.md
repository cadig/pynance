# Alpaca Trend Trading System

Automated long-only equity trend-following system that trades via the Alpaca API. Two scripts run on separate schedules: **trendTrader.py** (daily, finds entries and exits) and **RiskManager.py** (more frequently, ensures every position has a stop loss).

## How It Works

### Market Gatekeeping (4 checks before any new entry)

1. **Market regime** — Fetches the pynance regime signal (green/yellow/orange/red background color) from GitHub Pages. Red regime = no new entries. Other regimes control how many new entries per day (green 4, yellow 3, orange 1).
2. **VIX check** — If VIX closes above 25, all new entries are blocked regardless of regime color.
3. **SPY trend** — SPY must be above its 50-day moving average for any new entries.
4. **Universe breadth** — After scanning the universe, the system counts what percentage of scanned stocks are above their 50-day SMA. If this falls below 40%, new entries are blocked. This catches environments where the index holds up but individual growth stocks are breaking down — a leading signal that the system's edge is thinning.

The first three must pass before the universe is scanned. Then the breadth check determines whether the scan results in actual entries. If any gate fails, the system only manages existing positions (trailing stops, exits) and places no new trades.

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

Orders are placed as **stop-limit buys** — the stop (trigger) price is the current day's high, and the limit price is slightly above that (0.3 ATR). This means the stock must break above today's high to trigger a fill, confirming upward momentum.

The number of new entries per day is controlled by the market regime: **green 4, yellow 3, orange 1, red 0**. Max **40 total positions**.

### Position Sizing

Every position is sized identically: the dollar risk (entry price minus stop loss) equals **0.4% of account value**. Regime color does not affect position size — it controls entry pace (how many new positions per day) instead. This ensures every trade gets a full-sized allocation regardless of when it was entered.

### Stop Losses (ATR-Based Trailing Stops)

Every position gets a stop loss order at **entry price minus 4 ATRs** (20-day ATR).

Stops trail upward: when price makes a new high and the new calculated stop is meaningfully higher (at least 0.5 ATR above the current stop), the old stop order is cancelled and replaced with the higher one. Stops never move down.

### Exit Rules

Positions are sold via market order when any of these conditions are met:
1. **Trend breakdown** — price closes below the 50-day SMA
2. **Overextension** — price reaches 50-day SMA + 14 ATRs (takes profit on parabolic moves)
3. **Earnings proximity** — if a stock reports earnings after today's close (AMC) or before tomorrow's open (BMO), the position is closed unless it has >= 8 ATR open profit. Positions with large open profits are held through earnings. This check runs in RiskManager.py on its more frequent schedule.

Stop losses handle the downside exits independently via Alpaca's order system.

In a **red regime**, trailing stops tighten from 4 ATR to 2 ATR to reduce exposure while conditions deteriorate.

### RiskManager.py (Stop Loss Monitor + Earnings Guard)

Runs on a more frequent schedule than the main trader. Two jobs:
1. **Earnings proximity check** — for each held position, fetches the next earnings date and reporting hour from Finnhub. If earnings are imminent (AMC today after 2pm ET, or BMO tomorrow), closes the position and cancels its stop orders — unless the position has >= 8 ATR open profit, in which case it's held through earnings.
2. **Stop loss safety net** — scans all open positions, finds any missing a stop loss order (e.g., if a stop was triggered and partially filled, or an order was manually cancelled), and places new stop loss orders.

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
| `STOP_LOSS_ATR_MULT` | 4.0 | ATRs below price for stop loss (2.0 in red regime) |
| `LONG_MA_PERIOD` | 50 | Moving average for trend filter |
| `SHORT_MA_PERIOD` | 10 | Short MA for entry confirmation |
| `EXTENSION_MULT` | 2.5 | Max ATRs above 50-day SMA to enter |
| `EXTENDED_ATR_EXIT_MULT` | 14 | ATRs above 50-day SMA to exit (overextension) |
| `RISK_PER_TRADE` | 0.4 | Fixed % of account risked per trade (all regimes) |
| `MAX_POSITIONS` | 40 | Portfolio capacity |
| `MAX_ENTRIES_BY_REGIME` | green:4, yellow:3, orange:1, red:0 | Daily entry limit by regime |
| `EARNINGS_PROFIT_THRESHOLD_ATR` | 8.0 | ATR profit needed to hold through earnings |
| `RED_REGIME_STOP_ATR_MULT` | 2.0 | Tighter stop multiplier in red regime |
| `UNIVERSE_BREADTH_THRESHOLD` | 0.40 | Min % of universe above 50MA to allow entries |
| `DRY_RUN` | True | Set to False to submit real orders |
