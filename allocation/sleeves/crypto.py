"""
Crypto sleeve analyzer.

Ranks crypto ETFs using short-term momentum with a 200DMA trend gate.
Crypto is high-vol and high-beta — the trend filter does most of the work.
When BTC is below its 200DMA, you don't want exposure. When above, simple
momentum ranking picks the best vehicle.

Uses raw returns (not risk-adjusted) because all crypto ETFs have similarly
high volatility — normalizing by vol adds noise, not signal.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Optional
from ..utils import load_etf_data

# Shorter lookback than other sleeves — crypto moves fast
RETURN_PERIOD_WEIGHTS = {
    1: 0.60,   # 1 month — dominant signal
    3: 0.40,   # 3 month
}

TRADING_DAYS_PER_MONTH = 21


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


def is_above_200dma(df: pd.DataFrame) -> bool:
    """Return True if the most recent close is above the 200-day SMA."""
    if df is None or df.empty or 'close' not in df.columns or len(df) < 200:
        return False
    close = df['close'].iloc[-1]
    sma_200 = df['close'].rolling(window=200, min_periods=200).mean().iloc[-1]
    if pd.isna(close) or pd.isna(sma_200):
        return False
    return bool(close > sma_200)


def _detect_structural_downtrend(etf_data: Dict[str, pd.DataFrame]) -> bool:
    """
    Detect crypto structural downtrend: all three major crypto ETFs
    (IBIT, ETHA, BITO) are below their 200DMA.

    When the entire crypto market is in a structural bear, crypto-adjacent
    assets like NODE should not be included via the young-ETF bypass.
    """
    major_symbols = ['IBIT', 'ETHA', 'BITO']
    for sym in major_symbols:
        if sym not in etf_data:
            continue
        df = etf_data[sym]
        if len(df) >= 200 and is_above_200dma(df):
            return False
    return True


def rank_crypto(symbols: List[str], data_dir: Path) -> tuple:
    """
    Rank crypto ETFs by raw composite momentum.

    Process:
    1. Load data for each symbol
    2. Detect structural downtrend (all majors below 200DMA)
    3. Filter by 200-day MA (hard gate)
    4. Compute 1/3 month returns (raw, not risk-adjusted)
    5. Rank by weighted composite score

    Returns (ranked_list, structural_downtrend_bool).
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
        logging.warning("No crypto ETF data loaded; nothing to rank.")
        return [], False

    # Check if crypto is in a structural downtrend
    structural_downtrend = _detect_structural_downtrend(etf_data)
    if structural_downtrend:
        logging.info("Crypto structural downtrend detected (IBIT/ETHA/BITO all below 200DMA)")

    # Filter by 200DMA and compute returns
    candidates = {}
    for symbol, df in etf_data.items():
        # Some crypto ETFs are young (<200 days of history). If insufficient
        # data for the 200DMA, skip the filter and let them through with a warning —
        # UNLESS we're in a structural downtrend, in which case exclude them too.
        if len(df) >= 200:
            if not is_above_200dma(df):
                close = df['close'].iloc[-1] if 'close' in df.columns else None
                sma_200 = df['close'].rolling(window=200, min_periods=200).mean().iloc[-1]
                logging.info(f"{symbol}: excluded (below 200DMA). close={close} sma200={sma_200}")
                continue
        else:
            if structural_downtrend:
                logging.info(f"{symbol}: excluded (young ETF bypass blocked — crypto structural downtrend)")
                continue
            logging.warning(f"{symbol}: insufficient history for 200DMA ({len(df)} bars), including anyway")

        returns = {}
        for months in RETURN_PERIOD_WEIGHTS:
            returns[months] = calculate_period_return(df, months)

        candidates[symbol] = {'returns': returns}

    if not candidates:
        logging.warning("No crypto ETFs passed 200DMA filter; nothing to rank.")
        return [], structural_downtrend

    # Build returns DataFrame for ranking (raw returns, no risk adjustment)
    returns_df = pd.DataFrame(
        {sym: data['returns'] for sym, data in candidates.items()}
    ).T
    returns_df = returns_df.reindex(columns=list(RETURN_PERIOD_WEIGHTS.keys()))

    ranks_df = returns_df.rank(method='min', ascending=False, na_option='keep')

    num_symbols = len(returns_df)
    results = []
    for symbol in returns_df.index:
        composite_score = 0.0
        for months, weight in RETURN_PERIOD_WEIGHTS.items():
            rank = ranks_df.loc[symbol, months]
            if pd.notna(rank):
                inverted_rank = num_symbols + 1 - rank
                composite_score += inverted_rank * weight

        returns_raw = candidates[symbol]['returns']
        results.append({
            'rank': 0,
            'symbol': symbol,
            'composite_score': round(composite_score, 4),
            'returns': {
                '1_month': round(returns_raw[1] * 100, 2) if pd.notna(returns_raw.get(1)) else None,
                '3_month': round(returns_raw[3] * 100, 2) if pd.notna(returns_raw.get(3)) else None,
            },
        })

    results.sort(key=lambda x: x['composite_score'], reverse=True)
    for i, r in enumerate(results, start=1):
        r['rank'] = i

    return results, structural_downtrend


def analyze_crypto(data_dir: Path, allocation_percentage: float,
                   symbols: Optional[List[str]] = None) -> Dict:
    """
    Analyze Crypto opportunities.

    Args:
        data_dir: Path to data directory containing CSV files
        allocation_percentage: Target allocation percentage for crypto sleeve
        symbols: Optional list of specific symbols to analyze

    Returns:
        dict: Analysis results with recommended assets and weights
    """
    logging.info(f"Analyzing Crypto with {allocation_percentage:.2%} allocation")

    if symbols is None:
        from ..config import SLEEVE_CONFIG
        symbols = SLEEVE_CONFIG['crypto'].get('symbols', [])

    if not symbols:
        logging.warning("No symbols configured for crypto sleeve")
        return {
            'sleeve': 'crypto',
            'allocation_percentage': allocation_percentage,
            'selected_etfs': [],
            'weights': {},
            'total_allocation': 0.0
        }

    ranked, structural_downtrend = rank_crypto(symbols, data_dir)

    assets = [etf['symbol'] for etf in ranked]
    logging.info(f"Selected {len(ranked)} crypto ETFs: {assets}")

    return {
        'sleeve': 'crypto',
        'allocation_percentage': allocation_percentage,
        'structural_downtrend': structural_downtrend,
        'selected_etfs': ranked,
        'weights': {},
        'total_allocation': allocation_percentage if ranked else 0.0
    }
