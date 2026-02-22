# Alpaca Trend Trader — System Review & Improvement Plan

Critical analysis of the trading system's logic, gaps, and areas for improvement. Organized by priority.

---

## 1. ~~Code Bug: Trailing Stop Dead Path~~ DONE

~~Indentation bug in trailing stop update caused the `if should_update:` block to be nested inside the `elif`, skipping positions with no existing stop.~~

**Resolution:** De-indented the `if should_update:` block so it runs for both the `current_stop is None` and the minimum-move branches. Fixed in commit `8b3b28d`.

---

## 2. Market Gate — Structural Weaknesses

### What's Working
- Multiple independent filters (regime color + VIX + SPY 50MA)
- Regime-linked risk scaling (green 0.5%, yellow 0.3%, orange 0.1%)
- Hard block in red regime

### A. All Gate Filters Are Correlated

SPY 50MA, VIX > 25, and regime color all measure the same thing — broad market stress. In real drawdowns they flip together and flip back together. You re-enter late and crowded, and you're not gaining orthogonal information from three correlated signals.

**Improvement:** Add one true breadth metric as an independent filter:
- % of S&P 500 stocks above their 50MA
- % of universe making 20-day highs
- Advance/decline line slope

Trend systems fail most in narrow breadth environments where the index holds up but individual stocks break down.

### B. ~~No Exit-Level Regime Response~~ DONE (partial)

~~Bad regimes block new entries — but existing positions keep full 4 ATR stops and full exposure.~~

**Resolution:** When regime is red, trailing stops now tighten to 2 ATR (via `RED_REGIME_STOP_ATR_MULT`). Also removed early returns that were preventing position management (exits, trailing stops) from running when entries were blocked. Remaining items (block stop widening in yellow/orange, force position reduction) are future work.

### C. 96-Hour Regime Staleness Window

`RegimeDetector.validate_datetime` accepts data up to 96 hours old. If the regime pipeline fails Friday, the system trades Monday-Tuesday on stale data.

**Improvement:** Tighten to 48 hours, or fail closed (no entries on stale data).

---

## 3. Universe Selection — Bias & Concentration Risk

### What's Working
- Liquidity floor (volume > 100K)
- Price > 200MA structural filter
- EPS growth quality filter
- Performance-based sort

### A. Concentration Risk (Critical)

The position tracker demonstrates the problem: KGC, PAAS, SSRM, TFPM, WPM are all precious metals — 5 of 18 positions in one correlated trade. The Finviz screener sorted by 6-month performance naturally clusters into whatever sector is hot. A sector reversal hits all positions simultaneously, and correlated stops gap down together.

**Improvement:** Add hard constraints:
- Sector cap (e.g., max 4-5 positions per GICS sector)
- Industry cap (e.g., max 2-3 per sub-industry)
- Consider beta caps or market cap stratification

### B. Redundant Momentum Filtering

Quarter-positive performance + 6-month sort is double-filtering momentum. This pushes into the same crowded high-beta / growth names repeatedly, amplifying factor concentration.

### C. No Volatility Filter for Universe

ATR is used for stops and sizing but not for selection. Consider:
- ATR/price ratio filter (exclude extremely low-vol grinders that won't move 4 ATR profitably)
- Minimum daily range threshold

### D. Survivorship Bias (If Backtesting)

Finviz screens are live snapshots of current survivors. If the system was backtested using current Finviz data, results are inflated. Forward-testing live is fine, but be aware historical analysis using scraped snapshots is unreliable.

---

## 4. Entry Logic — Execution Problems

### A. ~~Stop-Limit Breakout Orders Miss Strong Moves~~ DONE

~~Entry orders use stop = today's high, limit = high + 0.1 ATR. In fast moves, gap-ups, or momentum surges, you won't get filled.~~

**Resolution:** Widened `LIMIT_PRICE_ATR_MULT` from 0.1 to 0.3 ATR in `trendTrader.py`. This gives breakout entries more room to fill on strong moves without accepting unlimited slippage from stop-market orders.

### B. Extension Filter Loosens in Volatility

The 2.5 ATR "not extended" entry filter is sound, but ATR expands during volatility spikes. The rule becomes more permissive precisely when conditions are most unstable.

**Improvement:**
- Normalize by percent above 50MA instead of (or in addition to) ATR
- Combine ATR extension + percent threshold

### C. Entry Candidate Ranking Is Arbitrary

`entry_candidates[:daily_entry_limit]` takes the first 4 candidates in Finviz sort order. With a 4-per-day limit, there's no ranking by setup quality — ATR tightness, distance from 50MA, relative volume, or any edge metric.

**Improvement:** Score and rank candidates by setup quality before selecting the daily batch.

---

## 5. Position Sizing — Portfolio Heat Uncapped

### A. No Aggregate Risk Cap

Each position risks 0.1–0.5%, but 40 positions at 0.5% = 20% total portfolio heat. With correlated holdings, effective drawdown risk is much higher.

**Improvement:**
- Add a max total open risk cap (e.g., 8-12% of account value)
- Or make the cap dynamic based on regime (green 12%, yellow 8%, orange 5%)

### B. No Volatility Scaling at Portfolio Level

If VIX is rising but still under 25, full risk-per-trade is allocated. The system doesn't scale down as realized volatility increases.

**Improvement:** Scale risk allocation proportional to inverse of realized SPY volatility (e.g., reduce risk-per-trade when SPY 20-day realized vol is elevated).

---

## 6. Stop & Exit Logic — Edge Cases

### A. 50MA Exit vs Stop Redundancy

Two downside exits coexist: the 4 ATR trailing stop and the market-sell-on-close-below-50MA rule. In slow rollovers, the 50MA exit fires first. In violent crashes, the stop fires first. This is fine architecturally, but worth analyzing whether the 50MA exit actually improves expectancy or just double-exits the same weakness.

### B. 14 ATR Overextension Exit Caps Convexity

14 ATR above the 50MA is enormous — this only triggers in parabolic blow-offs. But trend systems win by letting extreme outliers run. This rule suppresses exactly the right tail you want.

**Improvement:** Backtest with and without this rule. If it reduces long-term CAGR (likely), consider removing it or replacing with partial profit-taking (sell half, trail the rest).

### C. No Exit Scaling

Exits are all-or-nothing. No partial profit-taking at intermediate levels. Most of the open P&L can evaporate on the way back down before the 50MA exit triggers.

**Improvement:** Scale out at milestones (e.g., sell 1/3 at 5 ATR profit, trail the rest).

### D. ~~Earnings Blindspot on Held Positions~~ DONE

~~Earnings are checked at entry (8+ days away), but positions are never exited before earnings.~~

**Resolution:** Added `check_earnings_proximity()` to `RiskManager.py` (runs more frequently than trendTrader). For each held position, fetches next earnings date + hour (bmo/amc) from Finnhub. If earnings are imminent (amc today after 2pm ET, or bmo tomorrow), positions are closed unless they have >= 8 ATR open profit. Also added `get_earnings_with_hour()` to `finnhub/earnings.py` and `cancel_stop_orders()` to `risk_utils.py`.

---

## 7. Operational Risk

### A. Entry-to-Stop Race Condition

Entry orders are `TimeInForce.DAY` stop-limit buys. If the buy fills near market close, the stop loss order might not be placed before system shutdown. The position is unprotected overnight until the next RiskManager run.

### B. ~~RiskManager Partial Fill Risk~~ DONE

~~If a stop triggers and partially fills, then RiskManager runs and re-adds a stop based on the original quantity before the position is fully closed, the stop size is wrong.~~

**Resolution:** Added `reconcile_position_qty()` to `risk_utils.py`. Before placing any stop order, both `RiskManager.py` and `trendTrader.py` now re-fetch the live position quantity from Alpaca. If quantity differs from expected (partial fill), a warning is logged and the actual quantity is used. If the position no longer exists (fully closed), the stop is skipped.

### C. Gap Risk (Acknowledged)

Stop orders don't protect against gap-downs. A 4 ATR stop can become an 8 ATR loss. This is inherent to stop orders and acceptable — but combined with concentration risk, a sector-wide gap hits multiple positions with bad fills simultaneously.

---

## 8. System-Level Missing Pieces

### A. No Cash Management

When regime blocks entries, idle capital earns nothing. Trend systems underperform badly if cash sits idle for extended periods.

**Improvement:** Sweep idle cash into money market, short-term treasuries, or T-bill ETF.

### B. No Position Rotation

With 40 positions and entries blocked, capital gets stuck in mediocre names that haven't broken down but aren't performing. When regime flips back to green and better setups appear, there's no mechanism to rotate out of weak holdings.

**Improvement:** Add a rotation rule — e.g., if a held position drops below the universe sort ranking threshold, replace it when a better candidate qualifies.

### C. No Performance Kill-Switch

The system doesn't monitor its own rolling drawdown, win rate, or expectancy. Pure mechanical execution is the design, but there's no circuit breaker if the strategy enters a prolonged losing period.

**Improvement:** Track rolling 30/60/90 day returns. If drawdown exceeds a threshold (e.g., -15%), reduce position count or pause entries independently of regime.
