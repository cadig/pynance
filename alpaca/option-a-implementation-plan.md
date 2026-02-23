# Option A Implementation Plan: Flat Entry Size + Regime Controls Entry Pace + R-Multiple Pyramiding

## Summary

Replace regime-variable position sizing (0.1%/0.3%/0.5%) with a flat risk-per-trade and use regime to control how many new entries per day. Add R-multiple pyramiding to scale into winners.

**Current behavior:** Regime color sets risk% per trade (0.1–0.5%). All entries get up to 4/day.
**New behavior:** Every entry gets the same risk% (0.3%). Regime color sets how many entries per day (1–4). At 3R profit, add 50% more shares to winners (once per position).

---

## Part 1: Flat Entry Sizing + Regime-Based Entry Pace

### Config Changes (`config.py`)

Replace `RISK_PERCENTAGES` dict with two new structures:

```python
# Old (remove):
RISK_PERCENTAGES = {
    'red':    0.0,
    'orange': 0.1,
    'yellow': 0.3,
    'green':  0.5,
}

# New:
RISK_PER_TRADE = 0.3  # Fixed 0.3% of account risked per trade, all regimes

MAX_ENTRIES_PER_DAY = {
    'red':    0,   # No entries (gates already block, this is defense-in-depth)
    'orange': 1,   # Cautious — 1 entry per day
    'yellow': 3,   # Moderate — 3 entries per day
    'green':  4,   # Full pace — 4 entries per day
}
```

Keep `MAX_POSITIONS_PER_DAY = 4` as an absolute ceiling (renamed or used as fallback if regime data is unavailable).

### RiskManager.py Changes

1. `get_risk_percentage()` — always returns `RISK_PER_TRADE` regardless of color (or simplify to remove the color parameter entirely). Keep the method signature for backward compatibility but make it constant.

2. `can_enter_positions()` — still returns `False` for red (no change needed, `MAX_ENTRIES_PER_DAY['red'] = 0` handles this too).

3. Add new method:
```python
def get_max_entries_per_day(self, background_color: str) -> int:
    """Return daily entry limit based on regime color."""
    return MAX_ENTRIES_PER_DAY.get(background_color.lower(), 1)  # Default to cautious
```

### trendTrader.py Changes

**Position sizing block (lines 760-762):**
```python
# Old:
risk_per_position = account_value * (percent_risk / 100)

# New:
risk_per_position = account_value * (RISK_PER_TRADE / 100)
```

`percent_risk` variable from `get_regime_based_risk()` is no longer used for sizing. Can keep it for logging/display purposes.

**Daily entry limit (lines 755-756):**
```python
# Old:
available_slots = MAX_POSITIONS - len(held_symbols)
daily_entry_limit = min(available_slots, MAX_POSITIONS_PER_DAY)

# New:
available_slots = MAX_POSITIONS - len(held_symbols)
regime_entry_limit = risk_manager.get_max_entries_per_day(background_color) if background_color else 1
daily_entry_limit = min(available_slots, regime_entry_limit)
```

**Logging in `get_regime_based_risk()` (lines 44-49):** Update to print the entry pace instead of risk% being meaningful for sizing. Something like:
```
Background Color: yellow
Risk Per Trade: 0.3% (flat)
Max Entries Today: 3
Can Enter Positions: True
```

### Files touched
- `config.py` — replace `RISK_PERCENTAGES`, add `RISK_PER_TRADE` and `MAX_ENTRIES_PER_DAY`
- `RiskManager.py` — add `get_max_entries_per_day()`, simplify `get_risk_percentage()` to return constant
- `trendTrader.py` — use `RISK_PER_TRADE` for sizing, use `get_max_entries_per_day()` for daily limit
- `README.md` — update Position Sizing and Market Gatekeeping sections

---

## Part 2: R-Multiple Pyramiding (Add to Winners)

### New Config Values (`config.py`)

```python
# Pyramiding
PYRAMID_R_THRESHOLD = 3.0      # Add to position after 3R profit
PYRAMID_SIZE_FRACTION = 0.5    # Add 50% of original qty
PYRAMID_MAX_ADDS = 1           # Maximum pyramid adds per position
```

### Position Tracker Schema Changes

Add three new fields per position in `position_tracker.json`:

```json
{
  "AAPL": {
    "entry_price": 200.00,
    "highest_price": 220.00,
    "current_stop": 185.00,
    "initial_r_multiple": 15.00,
    "entry_date": "2025-09-22T12:56:52",
    "qty": 50.0,
    "entry_regime": "yellow",
    "original_qty": 50,
    "pyramid_count": 0
  }
}
```

New fields:
- `entry_regime` — regime color at time of initial entry (informational/logging)
- `original_qty` — the qty at initial entry (doesn't change when pyramiding)
- `pyramid_count` — how many times we've added (capped at `PYRAMID_MAX_ADDS`)

### New Function: `check_pyramid_candidates()`

Add to `trendTrader.py`, called from `main()` between the exit logic and new-entry logic.

```python
def check_pyramid_candidates(live_data, position_tracker, account_value):
    """
    Scan held positions for R-multiple pyramid opportunities.

    A position qualifies if:
    1. pyramid_count < PYRAMID_MAX_ADDS
    2. initial_r_multiple is set (not None)
    3. Current profit >= PYRAMID_R_THRESHOLD * initial_r_multiple
    4. Stock still passes trend filter (above 50MA, 10MA > 50MA)
    5. Stock is not overextended (< EXTENSION_MULT ATRs above 50MA)

    For qualifying positions:
    - Add PYRAMID_SIZE_FRACTION * original_qty shares
    - Place via market order (position already confirmed, no need for stop-limit)
    - Update stop loss to cover full new quantity at current trailing stop level
    - Increment pyramid_count
    """
```

**Logic flow:**
1. Loop through `position_tracker` entries
2. Skip if `pyramid_count >= PYRAMID_MAX_ADDS`
3. Skip if `initial_r_multiple` is None or <= 0
4. Fetch bars, calculate ATR
5. Calculate current R profit: `(current_price - entry_price) / initial_r_multiple`
6. If R profit >= `PYRAMID_R_THRESHOLD`:
   - Verify stock still passes trend filters via `should_enter()` (reuse existing function — confirms price above 50MA, 10MA above 50MA, not overextended)
   - Calculate add qty: `int(original_qty * PYRAMID_SIZE_FRACTION)`
   - Submit market buy order for add qty
   - Cancel existing stop order, resubmit for total qty (original + add) at current trailing stop price
   - Update tracker: increment `pyramid_count`, update `qty`
7. Log all pyramid actions

### Pyramid Order Type

Use a **market order** (not stop-limit) for pyramids. Reasoning: the stock has already proven itself with 3R of profit. There's no need to wait for a breakout confirmation — we're adding to a confirmed winner. The stop-limit entry logic is for *unproven* new positions.

```python
# Pyramid add uses market order
order_data = MarketOrderRequest(
    symbol=symbol,
    qty=add_qty,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY,
    position_intent=PositionIntent.BUY_TO_OPEN
)
```

### Stop Loss Handling for Pyramided Positions

After adding shares, the existing stop order covers only the original quantity. Must:
1. Cancel the existing stop order (covers original qty)
2. Place a new stop order covering the **full position** (original + pyramid qty) at the current trailing stop price

This is already handled by the trailing stop logic in `update_trailing_stops_with_live_data()` — it reads live position qty from Alpaca. But to avoid a gap between the pyramid fill and the next trailing stop update, the pyramid function should immediately place a new stop for the full qty.

### Where It Runs in main()

Insert between exit logic and entry logic:

```python
# === Exit Logic === (existing, lines 606-635)
...

# === Update Trailing Stops === (existing, lines 638-693)
...

# === NEW: Pyramid Check ===
print("\n=== Checking Pyramid Opportunities ===")
pyramid_count = check_pyramid_candidates(live_data, position_tracker, account_value)
if pyramid_count > 0:
    # Re-fetch held_symbols since we may have increased position sizes
    # (not new symbols, but important for risk summary accuracy)
    print(f"Pyramided {pyramid_count} position(s)")

# === Entry Logic === (existing, lines 697+)
...
```

### Backfilling `initial_r_multiple` for Existing Positions

Many current positions have `initial_r_multiple: null`. For pyramiding to work, this field must be populated. Two approaches:

**Option A (recommended):** On first run after deployment, backfill using current ATR:
```python
# In sync or load logic:
if tracker[symbol]['initial_r_multiple'] is None:
    bars = fetch_bars(symbol, data_client)
    bars = calculate_atr(bars)
    atr_value = bars['ATR'].iloc[-1]
    tracker[symbol]['initial_r_multiple'] = round(STOP_LOSS_ATR_MULT * atr_value, 2)
```
This isn't perfect (ATR may have changed since entry) but is a reasonable approximation and only applies to legacy positions.

**Option B:** Skip pyramiding for positions with null `initial_r_multiple`. They'll naturally exit over time and new positions will have it set correctly.

Recommend Option A — it lets existing winners (like ALAB which has run from $92 to $236) qualify for pyramiding immediately.

### Files touched
- `config.py` — add `PYRAMID_R_THRESHOLD`, `PYRAMID_SIZE_FRACTION`, `PYRAMID_MAX_ADDS`
- `trendTrader.py` — add `check_pyramid_candidates()`, call from `main()`, add new tracker fields to `submit_order_with_stop_loss()`
- `position_tracker.json` — schema evolves (new fields added, old positions backfilled)
- `README.md` — add Pyramiding section

---

## Part 3: Migrate Existing Positions

On first run after deployment, handle the transition:

1. **Backfill `original_qty`** — set to current `qty` for all existing positions
2. **Backfill `pyramid_count`** — set to 0 for all existing positions
3. **Backfill `entry_regime`** — set to `"unknown"` for existing positions (informational only)
4. **Backfill `initial_r_multiple`** — use current ATR × STOP_LOSS_ATR_MULT as approximation

Add a migration helper to `load_position_tracker()`:

```python
def load_position_tracker():
    try:
        with open('position_tracker.json', 'r') as f:
            data = json.load(f)
        # Migrate legacy entries
        for symbol, info in data.items():
            if 'original_qty' not in info:
                info['original_qty'] = info['qty']
            if 'pyramid_count' not in info:
                info['pyramid_count'] = 0
            if 'entry_regime' not in info:
                info['entry_regime'] = 'unknown'
        return data
    except FileNotFoundError:
        return {}
```

This is safe — it only adds missing fields with sensible defaults, doesn't modify existing data.

---

## Implementation Order

### Step 1: Config + flat sizing (low risk, behavior change is minimal)
1. Add `RISK_PER_TRADE` and `MAX_ENTRIES_PER_DAY` to `config.py`
2. Add `get_max_entries_per_day()` to `RiskManager.py`
3. Update `trendTrader.py` to use flat risk and regime-based entry pace
4. Keep old `RISK_PERCENTAGES` temporarily (RiskManager still references it for logging)
5. Test with `DRY_RUN = True`

### Step 2: Position tracker migration (no behavior change)
1. Add migration logic to `load_position_tracker()`
2. Add new fields to `submit_order_with_stop_loss()` tracker writes
3. Run once to verify tracker migration works cleanly
4. Backfill `initial_r_multiple` for existing positions

### Step 3: Pyramid logic (new behavior)
1. Add pyramid config values
2. Implement `check_pyramid_candidates()`
3. Wire into `main()` between exits and entries
4. Test with `DRY_RUN = True` — verify logging shows correct R-multiple calculations and pyramid candidates
5. Verify stop loss replacement logic works correctly for increased qty

### Step 4: Cleanup + docs
1. Remove `RISK_PERCENTAGES` from config if no longer used
2. Update `README.md` with new position sizing, entry pace, and pyramid docs
3. Remove `percent_risk` flow from `get_regime_based_risk()` if fully replaced

---

## Risk Considerations

**What could go wrong:**

1. **Pyramid into a reversal** — Stock hits 3R, we add shares, then it reverses. Mitigated by: requiring `should_enter()` to still pass (confirms trend intact), and the trailing stop covering the full position.

2. **Stop order gap during pyramid** — Between the market buy fill and new stop placement, there's a brief window with no stop on the new shares. Mitigated by: immediately placing the new stop in the same function, and the position being profitable (3R up from entry) so a sudden gap would need to be catastrophic to cause real damage.

3. **Position concentration** — A pyramided position is 1.5x normal size. With 40 positions, worst case one position is ~2.25% of total heat (0.3% × 1.5) vs normal 0.3%. This is acceptable.

4. **Partial fills on pyramid** — Market order should fill immediately for liquid large-caps, but if it doesn't, the stop logic already handles qty reconciliation via `reconcile_position_qty()`.

5. **Regime data unavailable** — If regime fetch fails, default to `regime_entry_limit = 1` (most conservative non-zero pace). Current fallback already sets `can_enter = False`, which would block all entries — consider whether that's too aggressive with flat sizing.

---

## What This Looks Like in Practice

**Scenario: Mixed regime over 3 weeks**

| Day | Regime | Entries (old) | Entries (new) | Size (old) | Size (new) |
|-----|--------|--------------|--------------|-----------|-----------|
| 1   | Orange | 4 × 0.1%    | 1 × 0.3%    | Tiny      | Full      |
| 2   | Orange | 4 × 0.1%    | 1 × 0.3%    | Tiny      | Full      |
| 3   | Yellow | 4 × 0.3%    | 3 × 0.3%    | Medium    | Full      |
| 5   | Green  | 4 × 0.5%    | 4 × 0.3%    | Large     | Full      |
| 10  | Green  | 4 × 0.5%    | 4 × 0.3%    | Large     | Full      |
| 15  | —      | —            | Day-1 stock hits 3R → pyramid 50% | — | 1.5x full |

**Old system after 2 weeks:** 8 tiny positions, 8 medium, 8 large. Portfolio looks random.
**New system after 2 weeks:** 5 positions from cautious days, 14 from moderate/full days. All same size. Best performers get pyramided to 1.5x.

The new system deploys capital more slowly in uncertain environments (fewer entries) but every trade it takes has full conviction behind it. Winners get rewarded with more capital based on *proven performance*, not entry-day luck.
