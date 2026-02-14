# Portfolio Research Findings

*Generated from available CSV data in `data/` directory*
*Run date: 2026-02-14 13:13*

---

### D.1: Breadth Divergence as Vol Predictor

**Divergence events found:** 423

| Window | Hit Rate (VIX > 20) | Sample Size |
|--------|--------------------|---------|
| 5 days | 25.5% | 423 |
| 10 days | 32.4% | 423 |
| 20 days | 44.9% | 423 |

*Divergence = SPX at 20-day high while MMTW or MMFI below 60%*


### D.4: ADRN Distribution

No distribution phases found (ADRN 20d avg < 0.9 for 5+ days).


### D.5: VIX Mean Reversion Speed

**VIX spikes above 25:** 161
**Spike types:** 73 sudden (1-5d), 88 sustained (>5d)

**Days to VIX < 20:** avg=85, median=53 (n=161)
**Days to VIX < 15:** avg=854, median=826 (n=159)



### F.3: VIX Context-Aware Thresholds

**Analysis period:** 1990-12-31 to 2025-12-05 (9761 days)

| Threshold | Risk-Off Days | % of Total |
|-----------|--------------|----------|
| VIX > 30 (static) | 770 | 7.9% |
| VIX z-score > 2.0 | 644 | 6.6% |
| VIX percentile > 95th | 725 | 7.4% |

**Overlap:** 292 days both fire, 352 z-score only, 478 static only

*z-score only = dynamic catches risk earlier in low-vol environments; static only = dynamic misses in high-vol environments*


### G.2: Conditional Correlation

SKIPPED — insufficient overlapping data.


### G.5: Intraday Gap vs Overnight Risk

**Worst 1% of SPY daily returns** (threshold: -2.70%, n=6)

| Component | Average Return | % of Total Loss |
|-----------|---------------|-----------------|
| Total | -3.96% | 100% |
| Overnight gap | -2.13% | 54% |
| Intraday move | -1.86% | 47% |

*If most loss is overnight: need pre-positioned hedges. If intraday: faster regime checks help.*


### F.4: Leverage Decay

SKIPPED — insufficient overlapping data.


### G.1: Worst-Day Portfolio Decomposition

**Worst 1% portfolio days:** 6 (threshold: -2.24%)
**Avg sleeves negative:** 3.7 out of 4
**All sleeves negative:** 4 of 6 worst days

| Sleeve | Avg Return on Worst Days |
|--------|-------------------------|
| equity | -3.27% |
| mf | -1.34% |
| commodities | -2.45% |
| crypto | -5.77% |

*If avg negative sleeves is close to 4, diversification is mostly illusory on worst days*


### D.2: VIX Term Structure as Entry Signal

**Data range:** 2007-12-05 to 2025-06-20 (4377 days)
**Backwardation frequency:** 10.6% of days
**Backwardation entry signals:** 120
**Bollinger %B > 0.8 signals:** 274

**Avg VIX change 5d after backwardation:** -1.8
**Avg VIX change 10d after backwardation:** -2.6

