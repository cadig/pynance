"""
Portfolio-level analytics: correlation matrices, stress correlation, and drawdown metrics.

Computes cross-sleeve correlation and drawdown data for the allocation dashboard.
All heavy computation happens here (backend) so the frontend only renders pre-computed JSON.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# Handle both direct execution and module import
import sys
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from allocation.utils import load_etf_data
else:
    try:
        from .utils import load_etf_data
    except ImportError:
        from allocation.utils import load_etf_data


def _collect_selected_symbols(sleeve_analyses: Dict) -> Dict[str, str]:
    """
    Extract a map of symbol -> sleeve_name from all sleeve analyses.

    Returns:
        Dict mapping symbol to its sleeve name (e.g. {'SCHD': 'equity', 'KMLM': 'managed_futures'})
    """
    symbol_sleeve = {}
    for sleeve_name, sleeve_data in sleeve_analyses.items():
        if not sleeve_data:
            continue
        # equity uses final_assets; other sleeves use selected_etfs[].symbol
        symbols = []
        if sleeve_data.get('final_assets'):
            symbols = sleeve_data['final_assets']
        elif sleeve_data.get('selected_etfs'):
            symbols = [e['symbol'] for e in sleeve_data['selected_etfs'] if isinstance(e, dict)]
        for sym in symbols:
            if sym not in symbol_sleeve:
                symbol_sleeve[sym] = sleeve_name


    return symbol_sleeve


# Canonical sleeve display order for grouping
_SLEEVE_ORDER = ['equity', 'managed_futures', 'commodities', 'fixed_income', 'crypto', 'vol_hedges']


def _symbols_grouped_by_sleeve(symbol_sleeve: Dict[str, str]) -> List[str]:
    """
    Return symbols ordered by sleeve group (using _SLEEVE_ORDER), then
    alphabetically within each sleeve. This ensures the heatmap and tables
    show same-sleeve tickers adjacent to each other.
    """
    sleeve_rank = {s: i for i, s in enumerate(_SLEEVE_ORDER)}
    return sorted(
        symbol_sleeve.keys(),
        key=lambda sym: (sleeve_rank.get(symbol_sleeve[sym], 999), sym)
    )


def _load_returns_matrix(symbols: List[str], data_dir: Path, lookback: int) -> Optional[pd.DataFrame]:
    """
    Load daily returns for a list of symbols over the given lookback period.

    Returns:
        DataFrame with columns=symbols, index=dates, values=daily returns.
        None if insufficient data.
    """
    close_data = {}
    for sym in symbols:
        try:
            df = load_etf_data(sym, data_dir)
            if df is not None and 'close' in df.columns and len(df) > lookback:
                close_data[sym] = df['close'].iloc[-(lookback + 1):]
        except Exception as e:
            logging.warning(f"portfolio_analytics: could not load {sym}: {e}")

    if len(close_data) < 2:
        return None

    prices = pd.DataFrame(close_data)
    prices = prices.dropna(how='all')

    if len(prices) < lookback // 2:
        return None

    returns = prices.pct_change().iloc[1:]
    returns = returns.dropna(how='all')
    return returns


def compute_correlation_matrix(
    sleeve_analyses: Dict,
    data_dir: Path,
    lookback: int = 63
) -> Optional[Dict]:
    """
    Compute a standard Pearson correlation matrix across all selected ETFs.

    Args:
        sleeve_analyses: The sleeve_analyses dict from allocation results
        data_dir: Path to data directory for loading ETF prices
        lookback: Number of trading days for correlation window (default 63 ~ 3 months)

    Returns:
        Dict with keys: lookback_days, symbols, matrix, sleeve_labels
        None if insufficient data
    """
    symbol_sleeve = _collect_selected_symbols(sleeve_analyses)
    if len(symbol_sleeve) < 2:
        return None

    symbols = _symbols_grouped_by_sleeve(symbol_sleeve)
    returns = _load_returns_matrix(symbols, data_dir, lookback)
    if returns is None:
        return None

    # Only keep symbols that had enough data
    available = [s for s in symbols if s in returns.columns]
    if len(available) < 2:
        return None

    returns = returns[available]
    corr = returns.corr().values

    # Replace any NaN with 0 for JSON serialization
    corr = np.nan_to_num(corr, nan=0.0)

    return {
        'lookback_days': lookback,
        'symbols': available,
        'matrix': corr.tolist(),
        'sleeve_labels': [symbol_sleeve[s] for s in available]
    }


def compute_stress_correlation(
    sleeve_analyses: Dict,
    allocation_percentages: Dict,
    data_dir: Path,
    lookback: int = 126,
    n_worst: int = 20
) -> Optional[Dict]:
    """
    Compute conditional correlation using only the worst portfolio return days.

    This reveals which assets cluster together during selloffs — the correlation
    that matters most for risk management.

    Args:
        sleeve_analyses: The sleeve_analyses dict from allocation results
        allocation_percentages: Regime allocation percentages per sleeve
        data_dir: Path to data directory
        lookback: Number of trading days to consider (default 126 ~ 6 months)
        n_worst: Number of worst days to use for stress correlation

    Returns:
        Dict with keys: lookback_days, n_worst_days, threshold_return, symbols,
                        matrix, worst_days
        None if insufficient data
    """
    symbol_sleeve = _collect_selected_symbols(sleeve_analyses)
    if len(symbol_sleeve) < 2:
        return None

    symbols = _symbols_grouped_by_sleeve(symbol_sleeve)
    returns = _load_returns_matrix(symbols, data_dir, lookback)
    if returns is None:
        return None

    available = [s for s in symbols if s in returns.columns]
    if len(available) < 2:
        return None

    returns = returns[available]

    # Compute equal-weighted portfolio return for ranking days
    portfolio_returns = returns.mean(axis=1)

    # Select the n_worst days by portfolio return
    n_worst_actual = min(n_worst, len(portfolio_returns))
    if n_worst_actual < 5:
        return None

    worst_indices = portfolio_returns.nsmallest(n_worst_actual).index
    threshold_return = float(portfolio_returns.loc[worst_indices].max())

    # Stress correlation: correlation computed only on worst days
    stress_returns = returns.loc[worst_indices]
    if len(stress_returns) < 5:
        return None

    stress_corr = stress_returns.corr().values
    stress_corr = np.nan_to_num(stress_corr, nan=0.0)

    # Build worst-day decomposition
    worst_days = []
    for dt in sorted(worst_indices):
        day_returns = {}
        for sym in available:
            val = returns.loc[dt, sym]
            day_returns[sym] = round(float(val), 6) if not pd.isna(val) else None
        worst_days.append({
            'date': dt.strftime('%Y-%m-%d') if hasattr(dt, 'strftime') else str(dt),
            'portfolio_return': round(float(portfolio_returns.loc[dt]), 6),
            'returns': day_returns
        })

    return {
        'lookback_days': lookback,
        'n_worst_days': n_worst_actual,
        'threshold_return': round(threshold_return, 6),
        'symbols': available,
        'matrix': stress_corr.tolist(),
        'worst_days': worst_days
    }


def _compute_drawdown_series(returns_series: pd.Series) -> Dict:
    """
    Compute drawdown metrics from a daily returns series.

    Returns:
        Dict with max_drawdown_6mo, max_drawdown_1yr, drawdown_start, drawdown_trough,
        current_drawdown, recovery_days
    """
    if returns_series is None or len(returns_series) < 10:
        return None

    # Build cumulative wealth index
    wealth = (1 + returns_series).cumprod()
    running_max = wealth.cummax()
    drawdown = (wealth / running_max) - 1

    result = {}

    # Max drawdown over different lookbacks
    for label, days in [('max_drawdown_6mo', 126), ('max_drawdown_1yr', 252)]:
        if len(drawdown) >= days:
            dd_slice = drawdown.iloc[-days:]
        else:
            dd_slice = drawdown
        result[label] = round(float(dd_slice.min()), 6)

    # Current drawdown
    result['current_drawdown'] = round(float(drawdown.iloc[-1]), 6)

    # Find the worst drawdown period (over the full series)
    trough_idx = drawdown.idxmin()
    trough_pos = drawdown.index.get_loc(trough_idx)

    # Find the peak before the trough
    peak_idx = running_max.iloc[:trough_pos + 1].idxmax()

    result['drawdown_start'] = peak_idx.strftime('%Y-%m-%d') if hasattr(peak_idx, 'strftime') else str(peak_idx)
    result['drawdown_trough'] = trough_idx.strftime('%Y-%m-%d') if hasattr(trough_idx, 'strftime') else str(trough_idx)

    # Recovery: find first day after trough where wealth >= peak wealth
    peak_wealth = running_max.loc[trough_idx]
    post_trough = wealth.iloc[trough_pos:]
    recovered = post_trough[post_trough >= peak_wealth]
    if len(recovered) > 0 and recovered.index[0] != trough_idx:
        recovery_date = recovered.index[0]
        recovery_days = len(wealth.loc[trough_idx:recovery_date]) - 1
        result['recovery_days'] = int(recovery_days)
    else:
        result['recovery_days'] = None

    return result


def compute_sleeve_drawdowns(
    sleeve_analyses: Dict,
    allocation_percentages: Dict,
    data_dir: Path,
    lookback: int = 252
) -> Optional[Dict]:
    """
    Compute per-sleeve and portfolio-level max drawdown metrics.

    Each sleeve's drawdown is computed using equal-weighted returns of its selected ETFs.
    The portfolio drawdown uses allocation-weighted sleeve returns.

    Args:
        sleeve_analyses: The sleeve_analyses dict from allocation results
        allocation_percentages: Regime allocation percentages per sleeve
        data_dir: Path to data directory
        lookback: Maximum lookback in trading days (default 252 ~ 1 year)

    Returns:
        Dict with keys: by_sleeve (dict of sleeve -> drawdown metrics),
                        portfolio (drawdown metrics)
        None if insufficient data
    """
    symbol_sleeve = _collect_selected_symbols(sleeve_analyses)
    if not symbol_sleeve:
        return None

    symbols = _symbols_grouped_by_sleeve(symbol_sleeve)
    returns = _load_returns_matrix(symbols, data_dir, lookback)
    if returns is None:
        return None

    available = [s for s in symbols if s in returns.columns]
    if not available:
        return None

    returns = returns[available]

    # Group symbols by sleeve
    sleeve_symbols = {}
    for sym in available:
        sleeve = symbol_sleeve[sym]
        sleeve_symbols.setdefault(sleeve, []).append(sym)

    # Compute per-sleeve drawdowns
    by_sleeve = {}
    sleeve_return_series = {}
    for sleeve_name, syms in sleeve_symbols.items():
        sleeve_returns = returns[syms].mean(axis=1)
        dd = _compute_drawdown_series(sleeve_returns)
        if dd:
            by_sleeve[sleeve_name] = dd
            sleeve_return_series[sleeve_name] = sleeve_returns

    if not by_sleeve:
        return None

    # Compute portfolio-level drawdown using allocation weights
    portfolio_returns = None
    total_weight = 0
    for sleeve_name, sleeve_ret in sleeve_return_series.items():
        weight = allocation_percentages.get(sleeve_name, 0)
        if weight > 0:
            weighted = sleeve_ret * weight
            if portfolio_returns is None:
                portfolio_returns = weighted
            else:
                portfolio_returns = portfolio_returns.add(weighted, fill_value=0)
            total_weight += weight

    portfolio_dd = None
    if portfolio_returns is not None and total_weight > 0:
        # Normalize by total weight (in case not all sleeves have data)
        portfolio_returns = portfolio_returns / total_weight
        portfolio_dd = _compute_drawdown_series(portfolio_returns)

    return {
        'by_sleeve': by_sleeve,
        'portfolio': portfolio_dd
    }


def compute_portfolio_analytics(
    sleeve_analyses: Dict,
    allocation_percentages: Dict,
    data_dir: Path
) -> Optional[Dict]:
    """
    Main entry point: compute all portfolio analytics.

    Returns a dict suitable for inclusion as results['portfolio_analytics'].
    Returns None if there aren't enough selected ETFs for meaningful analysis.
    """
    symbol_sleeve = _collect_selected_symbols(sleeve_analyses)
    if len(symbol_sleeve) < 2:
        logging.info("portfolio_analytics: fewer than 2 ETFs selected, skipping analytics")
        return None

    logging.info(f"portfolio_analytics: computing analytics for {len(symbol_sleeve)} ETFs: {_symbols_grouped_by_sleeve(symbol_sleeve)}")

    result = {}

    try:
        corr = compute_correlation_matrix(sleeve_analyses, data_dir, lookback=63)
        if corr:
            result['correlation'] = corr
    except Exception as e:
        logging.warning(f"portfolio_analytics: correlation failed: {e}")

    try:
        stress = compute_stress_correlation(sleeve_analyses, allocation_percentages, data_dir, lookback=126, n_worst=20)
        if stress:
            result['stress_correlation'] = stress
    except Exception as e:
        logging.warning(f"portfolio_analytics: stress correlation failed: {e}")

    try:
        drawdowns = compute_sleeve_drawdowns(sleeve_analyses, allocation_percentages, data_dir, lookback=252)
        if drawdowns:
            result['drawdowns'] = drawdowns
    except Exception as e:
        logging.warning(f"portfolio_analytics: drawdowns failed: {e}")

    return result if result else None
