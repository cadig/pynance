# Allocation Engine — How Each Sleeve Works

This document explains the logic behind each asset sleeve in plain english. For code-level details, see the source files in `sleeves/`.

## How the system decides what to buy

The allocation engine runs daily in three steps:

1. **Determine the regime** — Read the SPX regime results (generated upstream by `combined-research.py`) to figure out the current market environment: risk-on, moderate, elevated, risk-off, or crisis.

2. **Set the allocation split** — Based on the regime, decide what percentage of the portfolio goes to each sleeve. In risk-on, equities get 50% and managed futures get 20%. In a crisis, that flips: equities drop to 5% and managed futures jump to 55%.

3. **Pick the best ETFs within each sleeve** — Each sleeve runs its own analysis to rank and select ETFs from its universe. The ranking methods differ by sleeve because the asset classes behave differently.

---

## Equity Sleeve

**Goal:** Own the strongest-trending equity ETFs across geography and style, while avoiding anything in a downtrend.

**Universe:** ~17 ETFs across 5 sub-modules (US Large Cap, Ex-US, Small Caps, Total Market, Custom). Sector ETFs are configured but currently disabled.

**How it picks:**

1. **Load price data** for every ETF in each enabled sub-module.

2. **Filter by 200-day moving average.** If an ETF's current price is below its 200-day simple moving average, it's excluded entirely. This is a hard gate — no exceptions. The idea is to avoid catching falling knives. If QQQ is in a sustained downtrend, it doesn't matter how good its short-term momentum looks.

3. **Calculate momentum returns** over four periods: 1 month, 3 months, 6 months, and 12 months.

4. **Rank all surviving ETFs** across each period. The ETF with the best 1-month return gets rank 1 for that period, the second-best gets rank 2, and so on.

5. **Compute a composite score** by weighting the ranks:
   - 1-month return: **50%** weight (recent momentum matters most)
   - 3-month return: **25%** weight
   - 6-month return: **15%** weight
   - 12-month return: **10%** weight (long-term trend is a tiebreaker)

   Ranks are inverted so that higher scores = better performance.

6. **Select the top 4 ETFs** from the combined rankings, with a cap of 2 per sub-module. This prevents the portfolio from, say, picking 4 US Large Cap funds and ignoring international exposure entirely.

**What it doesn't do (yet):** Assign within-sleeve weights. The selected ETFs are identified and ranked, but the exact dollar allocation between them is not yet computed.

---

## Managed Futures Sleeve

**Goal:** Own the trend-following funds that are currently capturing trends, while giving volatile funds a fair shake and not penalizing them for dividend distributions.

**Universe:** 5 ETFs — KMLM, DBMF, CTA, WTMF, FMF. These are all managed futures / trend-following funds that trade across equities, bonds, commodities, and currencies.

**How it picks:**

1. **Load dividend-adjusted price data** for each ETF. yfinance returns adjusted prices by default, so distribution drops (which can be 8-10% annually for these funds) don't look like momentum losses.

2. **Evaluate trend strength** using 4 signals, each worth 1 point (0-4 scale):
   - Is the price above its 50-day moving average (with ATR buffer)?
   - Is the price above its 200-day moving average (with ATR buffer)?
   - Is the 50-day MA slope rising over the last 10 days?
   - Is the 200-day MA slope rising over the last 10 days?

3. **Apply ATR buffer to the MA comparisons.** Instead of checking "price > 50DMA" exactly, the sleeve checks "price > (50DMA minus 1x ATR)". ATR (Average True Range, 14-day) measures how much the fund typically moves in a day. A volatile fund like KMLM might have an ATR of $0.40, giving it that much cushion before it's considered "below" the moving average. A low-volatility fund like WTMF has a smaller ATR and therefore a smaller buffer. This prevents volatile funds from constantly whipsawing in and out of the trend filter on normal daily noise.

4. **Exclude any ETF with a trend score of 0.** If all four signals are negative — price below both MAs (even with the buffer) and both MAs falling — the fund isn't capturing any trend and shouldn't be held.

5. **Calculate momentum returns** over three periods: 1 month, 3 months, and 6 months. No 12-month lookback because managed futures trends cycle faster than equities.

6. **Risk-adjust the returns.** Each period's return is divided by the fund's 63-day (3-month) annualized realized volatility. This means a fund returning 5% with 8% vol (ratio: 0.625) ranks higher than a fund returning 8% with 20% vol (ratio: 0.4). Without this adjustment, the most volatile fund would tend to rank first simply because it swings more in either direction.

7. **Rank by weighted composite score** of the risk-adjusted returns:
   - 1-month: **50%** weight (what's working right now)
   - 3-month: **30%** weight
   - 6-month: **20%** weight

8. **Add a trend bonus.** The trend score (0-4) is scaled by 0.25 and added on top of the composite score. This acts as a tiebreaker: between two funds with similar risk-adjusted momentum, the one with stronger trend signals ranks higher.

9. **Output all passing ETFs** ranked by final score. The universe is only 5 funds, so there's no need to cap at a top N — typically 3-5 pass the trend filter.

**What it doesn't do (yet):** Assign within-sleeve weights.

---

## Commodities / Metals Sleeve

**Goal:** Own the strongest-trending commodity exposures across metals, miners, energy, and agriculture, while avoiding anything in a downtrend. Prevent over-concentration in a single commodity by enforcing mutual exclusion between correlated ETFs.

**Universe:** 9 ETFs across 4 categories:
- Broad commodities: DBC
- Precious metals: GLD, SLV
- Miners/materials: GDX (gold miners), SIL (silver miners), COPX (copper miners), URNM (uranium miners)
- Energy: USO
- Agriculture: DBA

**How it picks:**

1. **Load price data** for every ETF in the universe.

2. **Filter by 200-day moving average.** Same hard gate as equity — if the ETF's price is below its 200-day SMA, it's excluded. Commodities can have extended drawdowns, and you don't want to hold broad commodity ETFs in a deflationary bust. No exceptions, no ATR buffer (unlike managed futures, these aren't structurally leveraged products with high daily noise).

3. **Calculate momentum returns** over three periods: 1 month, 3 months, and 6 months. No 12-month lookback — commodities are cyclical and a 12-month return can span an entire boom-bust cycle, making it less useful for current positioning.

4. **Risk-adjust the returns.** Each period's return is divided by the ETF's 63-day annualized realized volatility. This is important here because the universe mixes very different asset types: a broad commodity basket like DBC might have 12% annual vol, while a uranium miner ETF like URNM could have 40%+. Without risk-adjustment, the most volatile miner would dominate the rankings whenever it swings up, even if the risk-adjusted return is mediocre.

5. **Rank by weighted composite score** of the risk-adjusted returns:
   - 1-month: **50%** weight
   - 3-month: **30%** weight
   - 6-month: **20%** weight

6. **Enforce mutual exclusion pairs.** Two pairs are configured:
   - **GLD vs GDX:** Gold the metal vs gold miners. Both track the gold trade — keeping the higher-ranked one and dropping the other prevents doubling up on gold exposure.
   - **SLV vs SIL:** Silver the metal vs silver miners. Same logic.

   The higher-ranked member of each pair (by composite score) survives. If GLD ranks #2 and GDX ranks #5, GDX is removed. If neither passes the 200DMA filter, neither appears.

7. **Output all surviving ETFs** ranked by final score.

**What it doesn't do (yet):** Assign within-sleeve weights.

---

## Crypto Sleeve

**Goal:** Get exposure to the best-performing crypto vehicle when the trend is up, and stay out entirely when it's down. This is a small allocation (0-5%) where the trend filter matters more than the ranking.

**Universe:** 4 ETFs — IBIT (BTC spot), ETHA (ETH spot), BITO (BTC futures), NODE (crypto industry equities)

**How it picks:**

1. **Load price data** for each ETF.

2. **Filter by 200-day moving average.** Same hard gate as equity and commodities. Crypto is high-vol and high-beta — when BTC is below its 200DMA, you don't want exposure at all. This single filter avoids the worst of bear markets.

   **Exception for young ETFs:** Some crypto ETFs have less than 200 days of trading history (they launched recently). If there isn't enough data to compute the 200DMA, the ETF bypasses the filter with a warning and is included anyway. This prevents new but legitimately trending ETFs from being silently dropped.

3. **Calculate momentum returns** over two periods only: 1 month and 3 months. No 6-month or 12-month lookback — crypto moves too fast for those to be useful. A 3-month crypto return can span an entire rally or crash.

4. **Rank by weighted composite score** of raw returns (not risk-adjusted):
   - 1-month: **60%** weight (dominant signal)
   - 3-month: **40%** weight

   Raw returns are used because all crypto ETFs have similarly high volatility (50%+ annualized). Risk-adjusting doesn't add meaningful signal when everything is volatile — it just adds noise.

5. **Output all passing ETFs** ranked by score. The regime allocation already caps crypto at 0-5% (and 0-1% in risk-off), so no additional cap is needed within the sleeve.

**What it doesn't do (yet):** Assign within-sleeve weights.

---

## Fixed Income Sleeve

**Goal:** Own the best-performing bond ETFs appropriate for the current market regime. In risk-on environments, keep duration short and avoid long-term treasuries. In risk-off or crisis, let long-duration bonds into the universe so flight-to-quality rallies can be captured.

**Universe:** 4 ETFs — TLT (long-term treasuries), SGOV (short-term / cash-like), TIP (inflation-protected), AGG (core aggregate bonds).

**How it picks:**

1. **Filter by regime eligibility.** Unlike other sleeves that use a 200DMA gate, fixed income uses the market regime to determine which ETFs are even candidates. The mapping:
   - **Risk-on / moderate:** SGOV, AGG, TIP only. TLT is excluded because long-duration treasuries tend to lose value when the economy is strong and rates may rise.
   - **Elevated risk:** All four eligible — TLT is allowed as a hedge option since the market may be about to deteriorate.
   - **Risk-off / crisis:** All four eligible — long-duration treasuries rally hardest in flight-to-quality environments. TLT will naturally rank highest by momentum when bonds are rallying.

2. **Calculate momentum returns** over three periods: 1 month, 3 months, and 6 months.

3. **Rank by weighted composite score** of raw returns (not risk-adjusted):
   - 1-month: **50%** weight
   - 3-month: **30%** weight
   - 6-month: **20%** weight

   Raw returns are used (not risk-adjusted) because the four ETFs are intentionally different in duration and risk profile. You *want* to pick the best-performing type of bond, not normalize away the differences between a 1-month T-bill and a 20-year treasury.

4. **Output all eligible ETFs** ranked by score. The universe is only 3-4 depending on regime, so no additional cap is needed.

**What it doesn't do (yet):** Assign within-sleeve weights.

---

## Vol Hedges Sleeve

**Goal:** Deploy capital into vol hedge instruments only when volatility is actively rising, and stay completely out otherwise. This is the only sleeve where "not being in it" is the default state.

**Universe:** 3 ETFs — UVXY (1.5x VIX short-term futures), TAIL (put-spread tail risk hedge), CAOS (tail risk via options)

**How it picks:**

This sleeve is fundamentally different from the others. It doesn't rank ETFs by momentum. Instead, it uses VIX conditions to decide whether to deploy at all, and then selects instruments by priority.

1. **Evaluate VIX signal** using the VIX Bollinger Band %B:
   - **Entry signal:** VIX > 20 AND %B > 0.8 (VIX is elevated and rising toward the upper Bollinger Band)
   - **Spike signal:** VIX > 20 AND %B > 1.0 (VIX has broken above the upper Bollinger Band — active spike)
   - **Exit signal:** VIX < 18 OR %B < 0.5 (VIX is low or mean-reverting back to normal)
   - **Neutral:** VIX between thresholds — treated as inactive (conservative, since we don't persist state between runs)

2. **If inactive (no signal or exit):** Return 0% allocation regardless of what the regime rules say. These instruments decay — holding them in calm markets destroys capital.

3. **If active, select instruments by priority:**
   - **During a spike (%B > 1.0):** UVXY first (pure VIX leverage, captures the spike), then TAIL for duration
   - **During entry (%B 0.8–1.0):** TAIL first (structural put hedge, less decay than UVXY), then CAOS as backup
   - UVXY is excluded from non-spike signals because its daily decay is too severe for sustained holding

4. **Output the selected instruments** with rationale explaining the VIX conditions.

**Allocation by regime:**
- Risk-on: 0% (decay instruments, don't hold)
- Moderate: 2% (small hedge if VIX triggers)
- Elevated: 5% (meaningful hedge)
- Risk-off: 9% (active hedge, reallocated from equities)
- Crisis: 15% (maximum hedge, vol instruments pay off here)

**What it doesn't do:** Track days held (no state persistence between runs), use VIX term structure (VIX9D/VIX3M data sources not yet enabled), assign within-sleeve weights.

---

## Key Design Decisions

**Why weighted momentum ranks instead of raw returns?** Ranking normalizes across different return magnitudes. An ETF returning 15% vs 14% shouldn't score dramatically different from one returning 5% vs 4% — both are a one-rank difference. The weighting then controls how much we care about recency vs. persistence.

**Why does equity use 4 return periods but managed futures only uses 3?** Equity trends tend to persist over longer horizons (12+ months), so a 12-month lookback helps identify sustained winners. Managed futures funds rotate their positions more frequently, so a 12-month return says less about what the fund is doing *now*.

**Why is the MF trend filter more lenient than the equity filter?** Equity uses a hard 200DMA gate with no buffer. Managed futures uses an ATR buffer because MF funds are structurally more volatile (they use leverage and trade volatile asset classes), so crossing below a moving average on normal noise doesn't carry the same signal.

**Why risk-adjust MF and commodity returns but not equity returns?** The equity universe spans different asset classes (US large cap, international, small cap) where volatility differences are partly intentional — you might *want* more volatile small caps if they're trending. The MF universe is 5 funds all doing roughly the same thing (trend following), so volatility is pure noise/cost and should be normalized out. Commodities are similar — the universe mixes a 12%-vol broad basket (DBC) with 40%+ vol uranium miners (URNM), so without risk-adjustment the most volatile miner dominates the rankings whenever it happens to swing up.

**Why mutual exclusion pairs in commodities?** GLD and GDX both track the gold trade (metal vs miners). If both pass the trend filter, holding both doubles your gold concentration. Same for SLV/SIL with silver. The system keeps whichever has the better risk-adjusted momentum and drops the other. This is configured in `config.py` so pairs can be added/removed without changing sleeve code.

**Why does fixed income use regime eligibility instead of a 200DMA filter?** Bond prices are driven by interest rate cycles, not equity-style momentum trends. A 200DMA gate would frequently exclude long-duration treasuries during normal environments, then allow them in too late after a crisis rally is already underway. Regime-based filtering is more forward-looking: it uses the market regime (which reflects equity conditions via breadth, VIX, and SPX trend) to decide what *type* of bond exposure is appropriate *now*. In risk-on, short duration is correct; in crisis, long duration is correct. The momentum ranking then picks the best performer within the eligible set.

**Why raw returns for fixed income but risk-adjusted for commodities/MF?** The FI universe (TLT, SGOV, TIP, AGG) is intentionally diverse in duration and risk. You want to pick the best-performing *type* of bond, not the one with the best Sharpe ratio. If TLT is up 8% in a risk-off rally, that's the signal — normalizing by its higher vol would dilute that signal. In contrast, the MF and commodity universes contain funds doing similar things at different vol levels, where normalizing removes noise.

**Why are all prices dividend-adjusted?** yfinance returns adjusted prices by default. This matters most for managed futures funds (KMLM, DBMF, etc.) that pay large distributions — without adjustment, each ex-dividend date would look like a momentum loss and trigger false "below MA" signals.
