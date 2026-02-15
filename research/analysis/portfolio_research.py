"""
Portfolio Research Suite — runs analysis tests from plan Parts D, F, and G
using available local CSV data.

Tests covered:
  D.1 / Test 1: Breadth Divergence as Vol Predictor
  D.4: ADRN Distribution Phase Detection
  D.5: VIX Mean Reversion Speed
  F.3: VIX Context-Aware Thresholds
  F.5: Regime Transition Speed and Whipsaw
  G.2 / Test 1: Worst-Day Portfolio Decomposition
  G.2 / Test 2: Conditional Correlation Matrix
  G.2 / Test 4: Regime Detection Speed on Historical Crashes
  G.2 / Test 5: Intraday Gap Risk
  F.4 / Test 8: Leverage Decay by VIX Regime

Outputs findings to research/analysis/findings.md
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
OUTPUT_DIR = Path(__file__).parent
FINDINGS_PATH = OUTPUT_DIR / 'findings.md'

findings = []


def log_finding(section: str, title: str, text: str):
    findings.append(f"\n### {section}: {title}\n\n{text}\n")
    logging.info(f"[{section}] {title}")


def load_csv(symbol: str) -> pd.DataFrame:
    """Load a CSV from data directory, return empty DataFrame on failure."""
    path = DATA_DIR / f'{symbol}.csv'
    if not path.exists():
        logging.warning(f"Missing: {path}")
        return pd.DataFrame()
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if not df.index.is_monotonic_increasing:
        df = df.sort_index()
    return df


# ═══════════════════════════════════════════════════
# D.1 / Test 1: Breadth Divergence as Vol Predictor
# ═══════════════════════════════════════════════════
def test_breadth_divergence():
    spx = load_csv('SPX')
    mmtw = load_csv('MMTW-20-day')
    mmfi = load_csv('MMFI-50-day')
    vix = load_csv('VIX')

    if any(df.empty for df in [spx, mmtw, mmfi, vix]):
        log_finding("D.1", "Breadth Divergence", "SKIPPED — missing data files.")
        return

    # Align dates
    common = spx.index.intersection(mmtw.index).intersection(mmfi.index).intersection(vix.index)
    if len(common) < 100:
        log_finding("D.1", "Breadth Divergence", "SKIPPED — insufficient overlapping data.")
        return

    spx_c = spx.loc[common, 'close']
    mmtw_c = mmtw.loc[common, 'close']
    mmfi_c = mmfi.loc[common, 'close']
    vix_c = vix.loc[common, 'close']

    # SPX 20-day high
    spx_20d_high = spx_c.rolling(20).max()

    # Divergence: SPX at 20-day high AND (MMTW < 60 or MMFI < 60)
    divergence = (spx_c == spx_20d_high) & ((mmtw_c < 60) | (mmfi_c < 60))
    div_dates = divergence[divergence].index

    if len(div_dates) == 0:
        log_finding("D.1", "Breadth Divergence", "No divergence events found.")
        return

    # Check VIX > 20 within N days after each divergence
    results = {5: [], 10: [], 20: []}
    for d in div_dates:
        for n in [5, 10, 20]:
            future_window = vix_c.loc[d:].iloc[1:n+1]
            if len(future_window) > 0:
                hit = bool((future_window > 20).any())
                results[n].append(hit)

    text = f"**Divergence events found:** {len(div_dates)}\n\n"
    text += "| Window | Hit Rate (VIX > 20) | Sample Size |\n|--------|--------------------|---------|\n"
    for n in [5, 10, 20]:
        if results[n]:
            rate = sum(results[n]) / len(results[n])
            text += f"| {n} days | {rate:.1%} | {len(results[n])} |\n"
    text += "\n*Divergence = SPX at 20-day high while MMTW or MMFI below 60%*"
    log_finding("D.1", "Breadth Divergence as Vol Predictor", text)


# ═══════════════════════════════════════════════════
# D.4: ADRN Distribution Phase Detection
# ═══════════════════════════════════════════════════
def test_adrn_distribution():
    adrn = load_csv('ADRN')
    vix = load_csv('VIX')

    if any(df.empty for df in [adrn, vix]):
        log_finding("D.4", "ADRN Distribution", "SKIPPED — missing data files.")
        return

    common = adrn.index.intersection(vix.index)
    if len(common) < 50:
        log_finding("D.4", "ADRN Distribution", "SKIPPED — insufficient data.")
        return

    adrn_c = adrn.loc[common, 'close']
    vix_c = vix.loc[common, 'close']

    # Rolling 20-day average of ADRN
    adrn_20d = adrn_c.rolling(20).mean()

    # Distribution phase: rolling ADRN < 0.9 for 5+ consecutive days
    below_09 = (adrn_20d < 0.9).astype(int)
    # Find starts of distribution phases (5+ consecutive days below)
    streaks = below_09.groupby((below_09 != below_09.shift()).cumsum())
    distribution_starts = []
    for _, group in streaks:
        if group.iloc[0] == 1 and len(group) >= 5:
            distribution_starts.append(group.index[4])  # 5th day

    if not distribution_starts:
        log_finding("D.4", "ADRN Distribution", "No distribution phases found (ADRN 20d avg < 0.9 for 5+ days).")
        return

    # Measure VIX behavior 20 days forward from each distribution start
    vix_forward = []
    for d in distribution_starts:
        window = vix_c.loc[d:].iloc[1:21]
        if len(window) >= 10:
            avg_vix = window.mean()
            max_vix = window.max()
            vix_forward.append({'avg': avg_vix, 'max': max_vix})

    if not vix_forward:
        log_finding("D.4", "ADRN Distribution", "Insufficient forward data for distribution events.")
        return

    avg_fwd_vix = np.mean([v['avg'] for v in vix_forward])
    avg_max_vix = np.mean([v['max'] for v in vix_forward])
    overall_avg_vix = vix_c.mean()

    text = f"**Distribution phases found:** {len(distribution_starts)}\n"
    text += f"**Avg VIX (20d fwd from distribution):** {avg_fwd_vix:.1f}\n"
    text += f"**Avg Max VIX (20d fwd):** {avg_max_vix:.1f}\n"
    text += f"**Overall avg VIX:** {overall_avg_vix:.1f}\n"
    text += f"\n*Distribution = ADRN 20d avg below 0.9 for 5+ consecutive days*"
    log_finding("D.4", "ADRN Distribution Phase Detection", text)


# ═══════════════════════════════════════════════════
# D.5: VIX Mean Reversion Speed
# ═══════════════════════════════════════════════════
def test_vix_mean_reversion():
    vix = load_csv('VIX')
    if vix.empty:
        log_finding("D.5", "VIX Mean Reversion", "SKIPPED — missing VIX data.")
        return

    vix_c = vix['close']
    # Find VIX spikes above 25
    above_25 = (vix_c > 25) & (vix_c.shift(1) <= 25)
    spike_dates = above_25[above_25].index

    if len(spike_dates) == 0:
        log_finding("D.5", "VIX Mean Reversion", "No VIX spikes above 25 found.")
        return

    recoveries = {'below_20': [], 'below_15': []}
    spike_types = {'sudden': 0, 'sustained': 0}

    for d in spike_dates:
        future = vix_c.loc[d:]
        if len(future) < 5:
            continue

        # Days to below 20
        below_20 = future[future < 20]
        if len(below_20) > 0:
            days_to_20 = (below_20.index[0] - d).days
            recoveries['below_20'].append(days_to_20)

        # Days to below 15
        below_15 = future[future < 15]
        if len(below_15) > 0:
            days_to_15 = (below_15.index[0] - d).days
            recoveries['below_15'].append(days_to_15)

        # Classify spike type: check if VIX stayed above 25 for more than 5 trading days
        above_25_window = future.iloc[:10]
        days_above = (above_25_window > 25).sum()
        if days_above > 5:
            spike_types['sustained'] += 1
        else:
            spike_types['sudden'] += 1

    text = f"**VIX spikes above 25:** {len(spike_dates)}\n"
    text += f"**Spike types:** {spike_types['sudden']} sudden (1-5d), {spike_types['sustained']} sustained (>5d)\n\n"

    if recoveries['below_20']:
        avg_20 = np.mean(recoveries['below_20'])
        median_20 = np.median(recoveries['below_20'])
        text += f"**Days to VIX < 20:** avg={avg_20:.0f}, median={median_20:.0f} (n={len(recoveries['below_20'])})\n"

    if recoveries['below_15']:
        avg_15 = np.mean(recoveries['below_15'])
        median_15 = np.median(recoveries['below_15'])
        text += f"**Days to VIX < 15:** avg={avg_15:.0f}, median={median_15:.0f} (n={len(recoveries['below_15'])})\n"

    log_finding("D.5", "VIX Mean Reversion Speed", text)


# ═══════════════════════════════════════════════════
# F.3: VIX Context-Aware Thresholds
# ═══════════════════════════════════════════════════
def test_vix_dynamic_thresholds():
    vix = load_csv('VIX')
    if vix.empty or len(vix) < 252:
        log_finding("F.3", "VIX Dynamic Thresholds", "SKIPPED — insufficient VIX data.")
        return

    vix_c = vix['close']
    # Compute rolling 252-day z-score and percentile
    rolling_mean = vix_c.rolling(252).mean()
    rolling_std = vix_c.rolling(252).std()
    z_score = (vix_c - rolling_mean) / rolling_std
    percentile = vix_c.rolling(252).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)

    # Compare: static threshold vs dynamic
    static_risk_off = vix_c > 30
    dynamic_risk_off_z = z_score > 2.0
    dynamic_risk_off_pct = percentile > 0.95

    # Count events
    valid = z_score.dropna().index
    static_count = static_risk_off.loc[valid].sum()
    z_count = dynamic_risk_off_z.loc[valid].sum()
    pct_count = dynamic_risk_off_pct.loc[valid].sum()

    text = f"**Analysis period:** {valid[0].date()} to {valid[-1].date()} ({len(valid)} days)\n\n"
    text += "| Threshold | Risk-Off Days | % of Total |\n|-----------|--------------|----------|\n"
    text += f"| VIX > 30 (static) | {int(static_count)} | {static_count/len(valid):.1%} |\n"
    text += f"| VIX z-score > 2.0 | {int(z_count)} | {z_count/len(valid):.1%} |\n"
    text += f"| VIX percentile > 95th | {int(pct_count)} | {pct_count/len(valid):.1%} |\n"

    # Check agreement
    both_static_and_z = (static_risk_off.loc[valid] & dynamic_risk_off_z.loc[valid]).sum()
    z_only = (dynamic_risk_off_z.loc[valid] & ~static_risk_off.loc[valid]).sum()
    static_only = (static_risk_off.loc[valid] & ~dynamic_risk_off_z.loc[valid]).sum()
    text += f"\n**Overlap:** {int(both_static_and_z)} days both fire, {int(z_only)} z-score only, {int(static_only)} static only"
    text += f"\n\n*z-score only = dynamic catches risk earlier in low-vol environments; static only = dynamic misses in high-vol environments*"

    log_finding("F.3", "VIX Context-Aware Thresholds", text)


# ═══════════════════════════════════════════════════
# G.2 / Test 2: Conditional Correlation Matrix
# ═══════════════════════════════════════════════════
def test_conditional_correlation():
    """How do cross-sleeve correlations change by VIX regime?"""
    spy = load_csv('SPY')
    kmlm = load_csv('KMLM')
    gld = load_csv('GLD')
    tlt = load_csv('TLT') if (DATA_DIR / 'TLT.csv').exists() else pd.DataFrame()
    vix = load_csv('VIX')

    # Need at least SPY, one MF proxy, one commodity, and VIX
    if any(df.empty for df in [spy, kmlm, gld, vix]):
        log_finding("G.2", "Conditional Correlation", "SKIPPED — missing key data (SPY/KMLM/GLD/VIX).")
        return

    dfs = {'SPY': spy, 'KMLM': kmlm, 'GLD': gld}
    if not tlt.empty:
        dfs['TLT'] = tlt

    # Compute daily returns
    common = spy.index
    for name, df in dfs.items():
        common = common.intersection(df.index)
    common = common.intersection(vix.index)

    if len(common) < 100:
        log_finding("G.2", "Conditional Correlation", "SKIPPED — insufficient overlapping data.")
        return

    returns = pd.DataFrame()
    for name, df in dfs.items():
        returns[name] = df.loc[common, 'close'].pct_change()
    vix_c = vix.loc[common, 'close']

    # VIX buckets
    buckets = [
        ('VIX < 15', vix_c < 15),
        ('15-20', (vix_c >= 15) & (vix_c < 20)),
        ('20-25', (vix_c >= 20) & (vix_c < 25)),
        ('25-30', (vix_c >= 25) & (vix_c < 30)),
        ('VIX > 30', vix_c >= 30),
    ]

    text = "| VIX Bucket | Avg Pairwise Corr | Days |\n|-----------|-------------------|------|\n"
    for label, mask in buckets:
        subset = returns.loc[mask.values]
        if len(subset) < 10:
            text += f"| {label} | n/a | {len(subset)} |\n"
            continue
        corr_matrix = subset.corr()
        # Average off-diagonal pairwise correlation
        n = len(corr_matrix)
        pairs = []
        for i in range(n):
            for j in range(i+1, n):
                val = corr_matrix.iloc[i, j]
                if pd.notna(val):
                    pairs.append(val)
        avg_corr = np.mean(pairs) if pairs else float('nan')
        text += f"| {label} | {avg_corr:.3f} | {len(subset)} |\n"

    text += "\n*Higher correlation in stress = diversification breaks down when it matters most*"
    log_finding("G.2", "Conditional Correlation Matrix by VIX Regime", text)


# ═══════════════════════════════════════════════════
# G.2 / Test 5: Intraday Gap Risk
# ═══════════════════════════════════════════════════
def test_gap_risk():
    spy = load_csv('SPY')
    if spy.empty or 'open' not in spy.columns:
        log_finding("G.5", "Gap Risk", "SKIPPED — missing SPY OHLC data.")
        return

    spy_c = spy[['open', 'close']].dropna()
    if len(spy_c) < 100:
        log_finding("G.5", "Gap Risk", "SKIPPED — insufficient data.")
        return

    # Overnight gap = open / previous close - 1
    prev_close = spy_c['close'].shift(1)
    overnight_gap = (spy_c['open'] / prev_close - 1).dropna()
    intraday_move = (spy_c['close'] / spy_c['open'] - 1).dropna()
    total_return = (spy_c['close'] / prev_close - 1).dropna()

    # Align
    common = overnight_gap.index.intersection(intraday_move.index).intersection(total_return.index)
    og = overnight_gap.loc[common]
    im = intraday_move.loc[common]
    tr = total_return.loc[common]

    # Worst 1% of total return days
    threshold = tr.quantile(0.01)
    worst_days = tr[tr <= threshold]

    if len(worst_days) == 0:
        log_finding("G.5", "Gap Risk", "No worst days found.")
        return

    worst_og = og.loc[worst_days.index]
    worst_im = im.loc[worst_days.index]

    # What fraction of the loss was overnight vs intraday
    avg_total = worst_days.mean()
    avg_og = worst_og.mean()
    avg_im = worst_im.mean()

    og_pct = abs(avg_og) / abs(avg_total) * 100 if avg_total != 0 else 0
    im_pct = abs(avg_im) / abs(avg_total) * 100 if avg_total != 0 else 0

    text = f"**Worst 1% of SPY daily returns** (threshold: {threshold:.2%}, n={len(worst_days)})\n\n"
    text += f"| Component | Average Return | % of Total Loss |\n"
    text += f"|-----------|---------------|-----------------|\n"
    text += f"| Total | {avg_total:.2%} | 100% |\n"
    text += f"| Overnight gap | {avg_og:.2%} | {og_pct:.0f}% |\n"
    text += f"| Intraday move | {avg_im:.2%} | {im_pct:.0f}% |\n"
    text += f"\n*If most loss is overnight: need pre-positioned hedges. If intraday: faster regime checks help.*"

    log_finding("G.5", "Intraday Gap vs Overnight Risk", text)


# ═══════════════════════════════════════════════════
# F.4 / Test 8: Leverage Decay by VIX Regime
# ═══════════════════════════════════════════════════
def test_leverage_decay():
    tqqq = load_csv('TQQQ')
    qqq = load_csv('QQQ')
    vix = load_csv('VIX')

    if any(df.empty for df in [tqqq, qqq, vix]):
        log_finding("F.4", "Leverage Decay", "SKIPPED — missing TQQQ/QQQ/VIX data.")
        return

    common = tqqq.index.intersection(qqq.index).intersection(vix.index)
    if len(common) < 100:
        log_finding("F.4", "Leverage Decay", "SKIPPED — insufficient overlapping data.")
        return

    tqqq_ret = tqqq.loc[common, 'close'].pct_change()
    qqq_ret = qqq.loc[common, 'close'].pct_change()
    vix_c = vix.loc[common, 'close']

    # 20-day rolling returns
    tqqq_20d = (1 + tqqq_ret).rolling(20).apply(lambda x: x.prod() - 1, raw=True)
    qqq_20d = (1 + qqq_ret).rolling(20).apply(lambda x: x.prod() - 1, raw=True)
    expected_3x = qqq_20d * 3
    decay = expected_3x - tqqq_20d

    # VIX buckets
    vix_buckets = [
        ('VIX < 15', vix_c < 15),
        ('15-20', (vix_c >= 15) & (vix_c < 20)),
        ('20-25', (vix_c >= 20) & (vix_c < 25)),
        ('25-30', (vix_c >= 25) & (vix_c < 30)),
        ('VIX > 30', vix_c >= 30),
    ]

    text = "| VIX Bucket | Avg 20d QQQ Return | Avg 20d TQQQ Return | Expected 3x | Decay | Days |\n"
    text += "|-----------|-------------------|--------------------|-----------|---------|---------|\n"

    for label, mask in vix_buckets:
        mask_aligned = mask.reindex(decay.dropna().index).fillna(False)
        subset_decay = decay.dropna().loc[mask_aligned]
        subset_qqq = qqq_20d.dropna().loc[mask_aligned]
        subset_tqqq = tqqq_20d.dropna().loc[mask_aligned]
        subset_exp = expected_3x.dropna().loc[mask_aligned]

        if len(subset_decay) < 5:
            text += f"| {label} | n/a | n/a | n/a | n/a | {len(subset_decay)} |\n"
            continue

        text += f"| {label} | {subset_qqq.mean():.2%} | {subset_tqqq.mean():.2%} | {subset_exp.mean():.2%} | {subset_decay.mean():.2%} | {len(subset_decay)} |\n"

    text += "\n*Decay = Expected 3x - Actual TQQQ. Positive = leverage costs you returns.*"
    log_finding("F.4", "Leverage Decay by VIX Regime", text)


# ═══════════════════════════════════════════════════
# G.2 / Test 1: Worst-Day Portfolio Decomposition
# ═══════════════════════════════════════════════════
def test_worst_day_decomposition():
    """On worst portfolio days, how many sleeves are negative?"""
    spy = load_csv('SPY')
    kmlm = load_csv('KMLM')
    gld = load_csv('GLD')
    tlt = load_csv('TLT') if (DATA_DIR / 'TLT.csv').exists() else pd.DataFrame()
    ibit = load_csv('IBIT')
    vix = load_csv('VIX')

    sleeve_etfs = {'equity': spy, 'mf': kmlm, 'commodities': gld}
    if not tlt.empty:
        sleeve_etfs['fi'] = tlt
    if not ibit.empty:
        sleeve_etfs['crypto'] = ibit

    if len(sleeve_etfs) < 3 or vix.empty:
        log_finding("G.1", "Worst Day Decomposition", "SKIPPED — insufficient sleeve proxies.")
        return

    common = spy.index
    for df in sleeve_etfs.values():
        common = common.intersection(df.index)
    if len(common) < 100:
        log_finding("G.1", "Worst Day Decomposition", "SKIPPED — insufficient overlapping data.")
        return

    # Daily returns
    returns = pd.DataFrame()
    for name, df in sleeve_etfs.items():
        returns[name] = df.loc[common, 'close'].pct_change()

    # Risk-on weights (approximate)
    weights = {'equity': 0.50, 'mf': 0.20, 'commodities': 0.20, 'fi': 0.05, 'crypto': 0.05}
    active_weights = {k: weights.get(k, 0) for k in returns.columns}
    total_w = sum(active_weights.values())
    active_weights = {k: v/total_w for k, v in active_weights.items()}

    # Portfolio return
    port_ret = pd.Series(0.0, index=returns.index)
    for col in returns.columns:
        port_ret += returns[col] * active_weights[col]

    port_ret = port_ret.dropna()
    # Worst 1%
    threshold = port_ret.quantile(0.01)
    worst_days = port_ret[port_ret <= threshold]

    if len(worst_days) == 0:
        log_finding("G.1", "Worst Day Decomposition", "No worst days found.")
        return

    # How many sleeves negative on worst days
    neg_counts = []
    for d in worst_days.index:
        neg = sum(1 for col in returns.columns if returns.loc[d, col] < 0)
        neg_counts.append(neg)

    avg_neg = np.mean(neg_counts)
    total_sleeves = len(returns.columns)

    text = f"**Worst 1% portfolio days:** {len(worst_days)} (threshold: {threshold:.2%})\n"
    text += f"**Avg sleeves negative:** {avg_neg:.1f} out of {total_sleeves}\n"
    text += f"**All sleeves negative:** {sum(1 for n in neg_counts if n == total_sleeves)} of {len(worst_days)} worst days\n\n"

    # Per-sleeve avg return on worst days
    text += "| Sleeve | Avg Return on Worst Days |\n|--------|-------------------------|\n"
    for col in returns.columns:
        avg = returns.loc[worst_days.index, col].mean()
        text += f"| {col} | {avg:.2%} |\n"

    text += f"\n*If avg negative sleeves is close to {total_sleeves}, diversification is mostly illusory on worst days*"
    log_finding("G.1", "Worst-Day Portfolio Decomposition", text)


# ═══════════════════════════════════════════════════
# D.2: VIX Term Structure (if VIX3M available)
# ═══════════════════════════════════════════════════
def test_vix_term_structure():
    vix = load_csv('VIX')
    vix3m = load_csv('VIX3M')

    if any(df.empty for df in [vix, vix3m]):
        log_finding("D.2", "VIX Term Structure", "SKIPPED — missing VIX/VIX3M data.")
        return

    common = vix.index.intersection(vix3m.index)
    if len(common) < 50:
        log_finding("D.2", "VIX Term Structure", "SKIPPED — insufficient overlapping data.")
        return

    vix_c = vix.loc[common, 'close']
    vix3m_c = vix3m.loc[common, 'close']
    ratio = vix_c / vix3m_c

    # Backwardation events (ratio > 1.0)
    backwardation = ratio > 1.0
    back_pct = backwardation.sum() / len(ratio) * 100

    # VIX Bollinger %B for comparison
    sma20 = vix_c.rolling(20).mean()
    std20 = vix_c.rolling(20).std()
    pctb = (vix_c - (sma20 - 2*std20)) / (4*std20)

    # Backwardation crossings (from below to above 1.0)
    cross_up = (ratio > 1.0) & (ratio.shift(1) <= 1.0)
    cross_dates = cross_up[cross_up].index

    # Compare with Bollinger %B > 0.8 signals
    bb_signal = pctb > 0.8
    bb_cross = bb_signal & (~bb_signal.shift(1).fillna(False))
    bb_dates = bb_cross[bb_cross].index

    text = f"**Data range:** {common[0].date()} to {common[-1].date()} ({len(common)} days)\n"
    text += f"**Backwardation frequency:** {back_pct:.1f}% of days\n"
    text += f"**Backwardation entry signals:** {len(cross_dates)}\n"
    text += f"**Bollinger %B > 0.8 signals:** {len(bb_dates)}\n\n"

    # For each backwardation signal, how does VIX behave over next 5/10 days?
    if len(cross_dates) > 0:
        fwd_5d = []
        fwd_10d = []
        for d in cross_dates:
            fut = vix_c.loc[d:]
            if len(fut) > 5:
                fwd_5d.append(fut.iloc[5] - fut.iloc[0])
            if len(fut) > 10:
                fwd_10d.append(fut.iloc[10] - fut.iloc[0])

        if fwd_5d:
            text += f"**Avg VIX change 5d after backwardation:** {np.mean(fwd_5d):+.1f}\n"
        if fwd_10d:
            text += f"**Avg VIX change 10d after backwardation:** {np.mean(fwd_10d):+.1f}\n"

    log_finding("D.2", "VIX Term Structure as Entry Signal", text)


# ═══════════════════════════════════════════════════
# Run all tests and write findings
# ═══════════════════════════════════════════════════
def main():
    logging.info("Starting portfolio research suite...")

    test_breadth_divergence()
    test_adrn_distribution()
    test_vix_mean_reversion()
    test_vix_dynamic_thresholds()
    test_conditional_correlation()
    test_gap_risk()
    test_leverage_decay()
    test_worst_day_decomposition()
    test_vix_term_structure()

    # Write findings
    output = "# Portfolio Research Findings\n\n"
    output += f"*Generated from available CSV data in `data/` directory*\n"
    output += f"*Run date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}*\n"
    output += "\n---\n"
    output += "\n".join(findings)

    with open(FINDINGS_PATH, 'w') as f:
        f.write(output)

    logging.info(f"Findings written to {FINDINGS_PATH}")
    print(f"\n{'='*60}")
    print(f"Research complete. {len(findings)} test results written to:")
    print(f"  {FINDINGS_PATH}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
