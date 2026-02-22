# Alpaca Trend Trader — System Improvement TODO

Prioritized list of remaining improvements. Completed items are collapsed at the bottom.

---

## 1. Exit Scaling (was 6C)

Exits are all-or-nothing. No partial profit-taking at intermediate levels. Most of the open P&L can evaporate on the way back down before the 50MA exit triggers.

**TODO:** Scale out at milestones (e.g., sell 1/3 at 5 ATR profit, trail the rest).

---

## 2. Overextension Exit Caps Convexity (was 6B)

14 ATR above the 50MA is enormous — this only triggers in parabolic blow-offs. But trend systems win by letting extreme outliers run. This rule suppresses exactly the right tail you want.

**TODO:** Backtest with and without this rule. If it reduces long-term CAGR (likely), consider removing it or replacing with partial profit-taking (sell half, trail the rest).

---

## 3. Performance Kill-Switch (was 8C)

The system doesn't monitor its own rolling drawdown, win rate, or expectancy. Pure mechanical execution is the design, but there's no circuit breaker if the strategy enters a prolonged losing period.

**TODO:** Track rolling 30/60/90 day returns. If drawdown exceeds a threshold (e.g., -15%), reduce position count or pause entries independently of regime.

---

## 4. Add Breadth Filter to Market Gate (was 2A)

SPY 50MA, VIX > 25, and regime color all measure the same thing — broad market stress. In real drawdowns they flip together and flip back together. You re-enter late and crowded, and you're not gaining orthogonal information from three correlated signals.

**TODO:** Add one true breadth metric as an independent filter:
- % of S&P 500 stocks above their 50MA
- % of universe making 20-day highs
- Advance/decline line slope

Trend systems fail most in narrow breadth environments where the index holds up but individual stocks break down.

---

## 5. Smoother Regime Transitions

The current regime model maps to discrete colors (green/yellow/orange/red) with hard cutoffs. A stock universe that's fine at green flips to restricted at yellow with no gradient. This causes whiplash — the system goes from full aggression to near-standby in one step, and back again the next day if the signal oscillates near a boundary.

**TODO:**
- Replace hard color buckets with a continuous regime score (e.g., 0–100) that blends the underlying breadth, VIX, and trend signals
- Map risk-per-trade and stop multipliers to the score via smooth curves rather than lookup tables
- Add hysteresis / confirmation period before regime transitions take effect (e.g., require 2 consecutive days at a new level before adjusting risk)
- Preserve the hard block at extreme levels (equivalent of current red) as a safety floor

---

## 6. Position Add-On Sizing After Regime Improvement

Positions entered during weaker regimes (orange/yellow) get smaller initial sizes because risk-per-trade is lower. If the position is working and the regime later improves to green, the system never scales back up — the strongest trends end up undersized for the best part of the move.

**TODO:**
- On each run in green regime, review existing positions that were originally sized at orange/yellow risk levels
- If the position is profitable and still meets entry criteria (above 50MA, not extended, trend intact), add to the position to bring total risk closer to the green-regime size
- Cap add-ons: only add once per position, and only if the new average entry still allows a reasonable stop distance
- Track the original regime at entry in `position_tracker.json` so the system knows which positions are candidates for add-ons

---

## Completed

<details>
<summary>Previously resolved items</summary>

### Trailing Stop Dead Path
De-indented the `if should_update:` block so it runs for both the `current_stop is None` and the minimum-move branches. Fixed in commit `8b3b28d`.

### Exit-Level Regime Response (partial)
When regime is red, trailing stops now tighten to 2 ATR (via `RED_REGIME_STOP_ATR_MULT`). Also removed early returns that were preventing position management from running when entries were blocked.

### Stop-Limit Breakout Orders
Widened `LIMIT_PRICE_ATR_MULT` from 0.1 to 0.3 ATR to capture stronger breakout fills.

### Earnings Blindspot on Held Positions
Added `check_earnings_proximity()` to `RiskManager.py`. Closes positions before imminent earnings unless they have >= 8 ATR open profit.

### RiskManager Partial Fill Risk
Added `reconcile_position_qty()` to `risk_utils.py`. Both scripts now re-fetch live position quantity from Alpaca before placing stop orders.

</details>
