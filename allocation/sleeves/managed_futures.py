"""
Managed Futures sleeve analyzer.

Ranks trend-following ETFs using momentum and trend strength filters.
MF ETFs perform well during sustained trends and poorly in choppy markets,
so scoring favors funds demonstrating strong recent performance with
shorter lookback periods than equities.

Volatility adjustments:
- MA crossover uses a 1x ATR buffer to reduce whipsaw in volatile funds
- Momentum ranking uses risk-adjusted returns (return / realized vol)
- yfinance already supplies dividend-adjusted prices (auto_adjust=True),
  so distribution drops don't penalize funds
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from ..utils import load_etf_data, compute_position_weights

# Shorter momentum weighting than equities — MF trends are faster
RETURN_PERIOD_WEIGHTS = {
    1: 0.50,   # 1 month — most important (capturing current trend)
    3: 0.30,   # 3 month
    6: 0.20,   # 6 month
}

TRADING_DAYS_PER_MONTH = 21

# ATR buffer multiplier for MA crossover filter
ATR_BUFFER_MULT = 1.0

# Lookback for realized volatility (63 trading days ≈ 3 months)
VOL_LOOKBACK_DAYS = 63


def compute_atr(df: pd.DataFrame, window: int = 14) -> Optional[float]:
    """Compute the most recent Average True Range value."""
    if df is None or len(df) < window + 1:
        return None
    for col in ('high', 'low', 'close'):
        if col not in df.columns:
            return None

    high = df['high']
    low = df['low']
    prev_close = df['close'].shift(1)

    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.rolling(window=window, min_periods=window).mean().iloc[-1]
    return None if pd.isna(atr) else float(atr)


def compute_realized_vol(df: pd.DataFrame, lookback: int = VOL_LOOKBACK_DAYS) -> Optional[float]:
    """
    Compute annualized realized volatility from daily log returns.
    Returns annualized vol (e.g. 0.15 = 15%).
    """
    if df is None or len(df) < lookback + 1 or 'close' not in df.columns:
        return None
    log_returns = np.log(df['close'] / df['close'].shift(1)).dropna().iloc[-lookback:]
    if len(log_returns) < lookback:
        return None
    daily_vol = log_returns.std()
    if pd.isna(daily_vol) or daily_vol == 0:
        return None
    return float(daily_vol * np.sqrt(252))


def calculate_period_return(df: pd.DataFrame, months: int) -> float:
    """Calculate percentage return for a given period in months."""
    trading_days = months * TRADING_DAYS_PER_MONTH
    if len(df) < trading_days:
        return np.nan

    current_price = df['close'].iloc[-1]
    past_price = df['close'].iloc[-trading_days]

    if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
        return np.nan

    return (current_price / past_price) - 1.0


def compute_ma(df: pd.DataFrame, window: int) -> Optional[float]:
    """Compute the most recent simple moving average value."""
    if df is None or len(df) < window or 'close' not in df.columns:
        return None
    val = df['close'].rolling(window=window, min_periods=window).mean().iloc[-1]
    return None if pd.isna(val) else float(val)


def compute_ma_slope(df: pd.DataFrame, window: int, slope_days: int = 10) -> Optional[float]:
    """
    Compute the slope direction of a moving average over the last N days.
    Returns the per-day change of the MA (positive = rising, negative = falling).
    """
    if df is None or len(df) < window + slope_days or 'close' not in df.columns:
        return None
    ma = df['close'].rolling(window=window, min_periods=window).mean()
    recent = ma.iloc[-1]
    past = ma.iloc[-(slope_days + 1)]
    if pd.isna(recent) or pd.isna(past):
        return None
    return float(recent - past) / slope_days


def evaluate_trend_strength(df: pd.DataFrame) -> Dict:
    """
    Evaluate trend strength for a single MF ETF.

    Uses a 1x ATR buffer on MA crossovers: price must be above (MA - ATR)
    to count as "above MA". This reduces whipsaw for volatile funds.

    Returns a dict with:
      - above_50dma: bool (with ATR buffer)
      - above_200dma: bool (with ATR buffer)
      - ma50_slope: float (positive = rising)
      - ma200_slope: float
      - atr: float (current 14-day ATR)
      - trend_score: 0-4 (count of positive signals)
    """
    if df is None or df.empty or 'close' not in df.columns:
        return {'above_50dma': False, 'above_200dma': False,
                'ma50_slope': None, 'ma200_slope': None,
                'atr': None, 'trend_score': 0}

    close = df['close'].iloc[-1]
    ma50 = compute_ma(df, 50)
    ma200 = compute_ma(df, 200)
    ma50_slope = compute_ma_slope(df, 50)
    ma200_slope = compute_ma_slope(df, 200)
    atr = compute_atr(df)

    # ATR-buffered MA comparison: price > (MA - 1*ATR) counts as "above"
    buffer = (atr * ATR_BUFFER_MULT) if atr is not None else 0.0
    above_50 = (ma50 is not None and close > (ma50 - buffer))
    above_200 = (ma200 is not None and close > (ma200 - buffer))
    slope_50_up = (ma50_slope is not None and ma50_slope > 0)
    slope_200_up = (ma200_slope is not None and ma200_slope > 0)

    trend_score = int(above_50 + above_200 + slope_50_up + slope_200_up)

    return {
        'above_50dma': above_50,
        'above_200dma': above_200,
        'ma50_slope': round(ma50_slope, 4) if ma50_slope is not None else None,
        'ma200_slope': round(ma200_slope, 4) if ma200_slope is not None else None,
        'atr': round(atr, 4) if atr is not None else None,
        'trend_score': trend_score,
    }


def rank_managed_futures(symbols: List[str], data_dir: Path) -> List[Dict]:
    """
    Rank MF ETFs by risk-adjusted composite momentum with trend strength overlay.

    Process:
    1. Load data for each symbol
    2. Compute trend strength (50/200 DMA with ATR buffer + slope)
    3. Exclude ETFs with trend_score == 0 (no positive trend signals at all)
    4. Compute momentum returns (1/3/6 month)
    5. Risk-adjust returns by dividing by 63-day realized volatility
    6. Rank by weighted composite score of risk-adjusted returns
    7. Apply trend_score as a tiebreaker bonus

    Returns list of dicts sorted by final_score descending.
    """
    etf_data = {}
    for symbol in symbols:
        try:
            df = load_etf_data(symbol, data_dir)
            if not df.index.is_monotonic_increasing:
                df = df.sort_index()
            etf_data[symbol] = df
        except Exception as e:
            logging.error(f"Failed to load data for {symbol}: {e}")

    if not etf_data:
        logging.warning("No MF ETF data loaded; nothing to rank.")
        return []

    # Evaluate trend strength, compute returns and vol
    candidates = {}
    for symbol, df in etf_data.items():
        trend = evaluate_trend_strength(df)

        # Exclude ETFs with zero trend signals (completely out of trend)
        if trend['trend_score'] == 0:
            logging.info(f"{symbol}: excluded (trend_score=0, no positive trend signals)")
            continue

        returns = {}
        for months in RETURN_PERIOD_WEIGHTS:
            returns[months] = calculate_period_return(df, months)

        vol = compute_realized_vol(df)
        if vol is not None:
            logging.info(f"{symbol}: annualized vol={vol:.1%}, ATR={trend['atr']}")
        else:
            logging.warning(f"{symbol}: could not compute realized vol, using raw returns")

        candidates[symbol] = {'trend': trend, 'returns': returns, 'vol': vol}

    if not candidates:
        logging.warning("No MF ETFs passed trend filter; nothing to rank.")
        return []

    # Build risk-adjusted returns DataFrame for ranking
    risk_adj_returns = {}
    for sym, data in candidates.items():
        vol = data['vol']
        raw = data['returns']
        adj = {}
        for months, ret in raw.items():
            if pd.notna(ret) and vol is not None and vol > 0:
                adj[months] = ret / vol
            else:
                adj[months] = ret  # fallback to raw if vol unavailable
        risk_adj_returns[sym] = adj

    returns_df = pd.DataFrame(risk_adj_returns).T
    returns_df = returns_df.reindex(columns=list(RETURN_PERIOD_WEIGHTS.keys()))

    # Rank: lower rank number = better risk-adjusted return
    ranks_df = returns_df.rank(method='min', ascending=False, na_option='keep')

    num_symbols = len(returns_df)
    results = []
    for symbol in returns_df.index:
        # Composite momentum score (same approach as equity sleeve)
        composite_score = 0.0
        for months, weight in RETURN_PERIOD_WEIGHTS.items():
            rank = ranks_df.loc[symbol, months]
            if pd.notna(rank):
                inverted_rank = num_symbols + 1 - rank
                composite_score += inverted_rank * weight

        # Trend bonus: add trend_score (0-4) scaled to ~10% of max composite
        trend_score = candidates[symbol]['trend']['trend_score']
        trend_bonus = trend_score * 0.25
        final_score = composite_score + trend_bonus

        returns_raw = candidates[symbol]['returns']
        vol = candidates[symbol]['vol']
        results.append({
            'rank': 0,  # assigned after sorting
            'symbol': symbol,
            'composite_score': round(composite_score, 4),
            'trend_score': trend_score,
            'final_score': round(final_score, 4),
            'annualized_vol': round(vol * 100, 2) if vol is not None else None,
            'returns': {
                '1_month': round(returns_raw[1] * 100, 2) if pd.notna(returns_raw.get(1)) else None,
                '3_month': round(returns_raw[3] * 100, 2) if pd.notna(returns_raw.get(3)) else None,
                '6_month': round(returns_raw[6] * 100, 2) if pd.notna(returns_raw.get(6)) else None,
            },
            'trend': candidates[symbol]['trend'],
        })

    # Sort by final_score descending
    results.sort(key=lambda x: x['final_score'], reverse=True)
    for i, r in enumerate(results, start=1):
        r['rank'] = i

    return results


def analyze_managed_futures(data_dir: Path, allocation_percentage: float,
                            symbols: Optional[List[str]] = None) -> Dict:
    """
    Analyze Managed Futures opportunities.

    Args:
        data_dir: Path to data directory containing CSV files
        allocation_percentage: Target allocation percentage for managed futures sleeve
        symbols: Optional list of specific symbols to analyze

    Returns:
        dict: Analysis results with recommended assets and weights
    """
    logging.info(f"Analyzing Managed Futures with {allocation_percentage:.2%} allocation")

    if symbols is None:
        from ..config import SLEEVE_CONFIG
        symbols = SLEEVE_CONFIG['managed_futures'].get('symbols', [])

    if not symbols:
        logging.warning("No symbols configured for managed futures sleeve")
        return {
            'sleeve': 'managed_futures',
            'allocation_percentage': allocation_percentage,
            'selected_etfs': [],
            'weights': {},
            'total_allocation': 0.0
        }

    ranked = rank_managed_futures(symbols, data_dir)

    # Select top 3 ETFs from those passing the trend filter
    selected = ranked[:3]

    assets = [etf['symbol'] for etf in selected]

    logging.info(f"Selected {len(selected)} MF ETFs: {assets}")

    weights = compute_position_weights(selected, score_key='final_score')

    return {
        'sleeve': 'managed_futures',
        'allocation_percentage': allocation_percentage,
        'selected_etfs': selected,
        'weights': weights,
        'total_allocation': allocation_percentage if selected else 0.0
    }
