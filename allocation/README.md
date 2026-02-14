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

## Stubs (Not Yet Implemented)

The following sleeves exist in the config and are dispatched by the engine, but return empty results:

- **Commodities** — Will cover metals, energy, and agricultural commodity ETFs.
- **Fixed Income** — Will cover treasury, corporate bond, and TIPS ETFs.
- **Crypto** — Will cover Bitcoin and Ethereum ETFs.
- **Alternatives** — Placeholder; currently allocated 0% in all regimes.

---

## Key Design Decisions

**Why weighted momentum ranks instead of raw returns?** Ranking normalizes across different return magnitudes. An ETF returning 15% vs 14% shouldn't score dramatically different from one returning 5% vs 4% — both are a one-rank difference. The weighting then controls how much we care about recency vs. persistence.

**Why does equity use 4 return periods but managed futures only uses 3?** Equity trends tend to persist over longer horizons (12+ months), so a 12-month lookback helps identify sustained winners. Managed futures funds rotate their positions more frequently, so a 12-month return says less about what the fund is doing *now*.

**Why is the MF trend filter more lenient than the equity filter?** Equity uses a hard 200DMA gate with no buffer. Managed futures uses an ATR buffer because MF funds are structurally more volatile (they use leverage and trade volatile asset classes), so crossing below a moving average on normal noise doesn't carry the same signal.

**Why risk-adjust MF returns but not equity returns?** The equity universe spans different asset classes (US large cap, international, small cap) where volatility differences are partly intentional — you might *want* more volatile small caps if they're trending. The MF universe is 5 funds all doing roughly the same thing (trend following), so volatility is pure noise/cost and should be normalized out.

**Why are all prices dividend-adjusted?** yfinance returns adjusted prices by default. This matters most for managed futures funds (KMLM, DBMF, etc.) that pay large distributions — without adjustment, each ex-dividend date would look like a momentum loss and trigger false "below MA" signals.
