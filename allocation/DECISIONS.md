# Implementation Decisions Log

Records design choices made during autonomous implementation. Review and override as needed.

---

## Sprint 5 — Alternatives / Volatility Hedge Sleeve

### Decision 1: VIX Data Source
**Options:**
1. Use VIX data from TradingView CSV (`data/VIX.csv`) — already fetched daily via Stage 1
2. Fetch VIX via yfinance like other ETFs — uses `^VIX` ticker
3. Use regime JSON `VIX_close` field only — simplest but only a single point-in-time value

**Selected:** Option 1 — Use TradingView VIX CSV. It has full OHLC history going back to 1990, is already fetched daily by the pipeline, and provides enough data for Bollinger Bands and rolling calculations. The regime JSON only has the latest close — not enough for term structure or Bollinger analysis.

### Decision 2: VIX Term Structure
**Options:**
1. Use VIX vs VIX3M from existing CSVs (both exist in `data/` but `shouldFetch: false` for VIX3M) — data may be stale
2. Skip term structure for now, use only VIX level + Bollinger %B for entry/exit signals
3. Enable VIX3M in `symbols_to_fetch.json` by setting `shouldFetch: true`

**Selected:** Option 2 — Skip term structure for initial implementation. The VIX3M/VIX9D CSVs exist but may be stale (shouldFetch is false). Per the plan, enabling new TradingView symbols requires user validation. VIX level + Bollinger %B already provides meaningful entry/exit signals. Can add term structure later when the user enables those data sources.

### Decision 3: Alternatives Allocation Budget (Where Do Percentages Come From?)
**Options:**
1. Add alternatives allocation ON TOP of existing 100% (over-allocate, requires scaling down all sleeves)
2. Reduce equity and crypto to make room for alternatives in elevated/risk-off/crisis regimes
3. Reduce managed futures slightly to make room

**Selected:** Option 2 — Take allocation from equity (primary) and crypto (secondary) since alternatives serve as a hedge when equities are weak. Specifically:
- Risk-on: 0% alternatives (unchanged — decay instruments, don't hold)
- Moderate: 2% alternatives (from equity: 40% → 38%)
- Elevated: 5% alternatives (from equity: 40% → 35%)
- Risk-off: 5% alternatives (from equity: 15% → 10%)
- Crisis: 5% alternatives (from equity: 5% → 0%, but equity shouldn't be 0 — take from MF instead: 55% → 50%)

### Decision 4: Entry/Exit Signal Design
**Options:**
1. Complex multi-signal system (VIX level + VIX %B + term structure + VIX momentum)
2. Simple VIX Bollinger %B threshold system (entry when VIX %B > 0.8, exit when %B < 0.5)
3. Regime-only (active when regime is elevated/risk-off/crisis, inactive otherwise)

**Selected:** Option 2 — VIX Bollinger %B threshold. This is consistent with the existing regime detection system (which already uses VIX Bollinger). Entry signal: VIX %B > 0.8 AND VIX > 20. Exit signal: VIX %B < 0.5 OR VIX < 18. This catches rising vol before it spikes and exits when vol is mean-reverting. The regime allocation already handles the "should we be hedged at all" question — the VIX signal handles "is vol actually rising."

### Decision 5: Per-Instrument Logic
**Options:**
1. Rank all three instruments by momentum like other sleeves
2. Tiered approach: UVXY for spikes only, TAIL/CAOS as longer-term structural hedges
3. Simple priority: if VIX is spiking (VIX %B > 1.0), use UVXY; otherwise prefer TAIL

**Selected:** Option 3 — Priority-based selection. UVXY is a pure spike trade (1.5x VIX futures, massive decay). It should only be held when VIX is actively spiking (%B > 1.0). TAIL and CAOS are put-option based hedges with less decay — suitable for sustained elevated vol periods. TAIL gets priority over CAOS as the more established vehicle. This is fundamentally different from other sleeves and matches the plan's guidance that "this is the only sleeve where not being in it is the default state."

---

## B.1 — Allocation Rules Refinement

### Decision 6: Updated Allocation Percentages
See Decision 3 above. Full updated table:
```
risk_on:       equity 50%, MF 20%, commodities 20%, FI 5%, crypto 5%, alt 0%  (unchanged)
moderate:      equity 38%, MF 30%, commodities 20%, FI 5%, crypto 5%, alt 2%  (equity -2)
elevated:      equity 35%, MF 30%, commodities 20%, FI 5%, crypto 5%, alt 5%  (equity -5)
risk_off:      equity 10%, MF 45%, commodities 25%, FI 10%, crypto 1%, alt 9% (equity -5, FI -4, alt +9)
crisis:        equity 0%, MF 50%, commodities 20%, FI 15%, crypto 0%, alt 15% (equity -5, MF -5, FI -5, alt +15)
```

**Rationale:** In risk-off/crisis, alternatives (vol hedges) should have the highest allocation since that's when they pay off. In crisis, equity goes to 0% because UVXY/TAIL should be the better risk-reward at that point. All rows sum to 100%.

---

## B+.1 — Result Archiving

### Decision 7: Archive Format
**Options:**
1. Timestamped files: `docs/history/2026-02-14-allocation.json`
2. Rolling JSONL: `docs/history/allocation-log.jsonl` (one JSON per line per day)
3. Both

**Selected:** Option 2 — JSONL. Single file, easy to query with `jq`, easy to diff, doesn't create hundreds of files over time. One line per day with the full allocation result.

---

## B+.4 — Pipeline Failure Handling

### Decision 8: Stale Data Behavior
**Options:**
1. Fail hard if data is stale (>1 day old) — prevents publishing garbage
2. Warn and annotate output as "stale" but still publish
3. Use stale data silently (current behavior)

**Selected:** Option 2 — Warn and annotate. Hard failure would mean a single TradingView outage breaks the entire pipeline. Instead, add a `data_quality` field to the output that flags which tickers used stale data, and a top-level `warnings` array. The dashboard can display these warnings.

---

## B+.5 — Smoke Tests

### Decision 9: Test Framework
**Options:**
1. pytest with fixture data
2. Simple Python script with assert statements (no dependency)
3. pytest with live data (integration test)

**Selected:** Option 1 — pytest with fixture data. pytest is standard, produces clear output, integrates with CI. Fixture data means tests are deterministic and don't require network access.

---

## B+.6 — Local Development Experience

### Decision 10: Local Run Script
**Options:**
1. Shell script (`scripts/run_local.sh`)
2. Makefile targets
3. Python script with argparse

**Selected:** Option 1 — Shell script. Simplest, no additional dependencies, works on Mac/Linux. Can be extended later.

---

## B.4 + B+.2 — Rebalance Signal + Actionable Output

### Decision 11: Change Detection Approach
**Options:**
1. Diff current vs previous JSONL entry
2. Separate "previous state" JSON file
3. Git diff of allocation-results.json

**Selected:** Option 1 — Diff against last JSONL entry. This depends on B+.1 (result archiving) being in place. Compare today's selected ETFs and allocations against yesterday's. Flag changes in: regime shift, ETF entering/leaving a sleeve, allocation percentage changes > 2%.

---

## B.3 — Dashboard Improvements

### Decision 12: Portfolio Summary Design
**Options:**
1. Pie chart showing sleeve allocations + selected ETFs
2. Table view with sleeve → ETFs → weights
3. Both

**Selected:** Option 2 — Table view. The dashboard already uses accordion UI for sleeves. A summary table at the top showing "if you followed all recommendations, here's your portfolio" is the most actionable format. Pie charts are pretty but less useful for action.
