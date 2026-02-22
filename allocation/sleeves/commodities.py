"""
Commodities/Metals sleeve analyzer.

Ranks commodity ETFs across broad commodities, precious metals, miners,
energy, and agriculture using momentum + trend filtering. Uses risk-adjusted
returns to normalize across the very different volatility profiles of, say,
a broad commodity basket (DBC) vs. a uranium miner ETF (URNM).

Mutual exclusion: GLD/GDX and SLV/SIL pairs — only the higher-ranked of
each pair is selected, since they track the same underlying commodity and
holding both doubles concentration risk.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Optional
from ..utils import (load_etf_data, compute_position_weights,
                     calculate_period_return, is_above_200dma,
                     compute_realized_vol, compute_composite_scores)

# Momentum weighting — same periods as MF (no 12mo; commodities are cyclical)
RETURN_PERIOD_WEIGHTS = {
    1: 0.50,   # 1 month
    3: 0.30,   # 3 month
    6: 0.20,   # 6 month
}


def apply_exclusive_pairs(ranked: List[Dict], exclusive_pairs: List[List[str]]) -> List[Dict]:
    """
    Enforce mutual exclusion: for each pair (e.g. [GLD, GDX]), keep only the
    higher-ranked one (which appears first since the list is sorted by score).
    """
    if not exclusive_pairs:
        return ranked

    excluded = set()
    for pair in exclusive_pairs:
        pair_set = set(pair)
        # Walk the ranked list; the first member of the pair we encounter wins
        found = False
        for etf in ranked:
            sym = etf['symbol']
            if sym in pair_set:
                if found:
                    # Second member of the pair — mark for exclusion
                    excluded.add(sym)
                else:
                    found = True

    if excluded:
        logging.info(f"Mutual exclusion removed: {excluded}")

    return [etf for etf in ranked if etf['symbol'] not in excluded]


def rank_commodities(symbols: List[str], data_dir: Path) -> List[Dict]:
    """
    Rank commodity ETFs by risk-adjusted composite momentum.

    Process:
    1. Load data for each symbol
    2. Filter by 200-day MA (hard gate, same as equity)
    3. Compute 1/3/6 month returns
    4. Risk-adjust returns by dividing by 63-day realized vol
    5. Rank by weighted composite score

    Returns list of dicts sorted by composite_score descending.
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
        logging.warning("No commodity ETF data loaded; nothing to rank.")
        return []

    # Filter by 200DMA and compute returns + vol
    candidates = {}
    for symbol, df in etf_data.items():
        if not is_above_200dma(df):
            close = df['close'].iloc[-1] if ('close' in df.columns and len(df)) else None
            sma_200 = (
                df['close'].rolling(window=200, min_periods=200).mean().iloc[-1]
                if ('close' in df.columns and len(df) >= 200) else None
            )
            logging.info(f"{symbol}: excluded (below 200DMA). close={close} sma200={sma_200}")
            continue

        returns = {}
        for months in RETURN_PERIOD_WEIGHTS:
            returns[months] = calculate_period_return(df, months)

        vol = compute_realized_vol(df)
        if vol is not None:
            logging.info(f"{symbol}: annualized vol={vol:.1%}")
        else:
            logging.warning(f"{symbol}: could not compute realized vol, using raw returns")

        candidates[symbol] = {'returns': returns, 'vol': vol}

    if not candidates:
        logging.warning("No commodity ETFs passed 200DMA filter; nothing to rank.")
        return []

    # Build risk-adjusted returns DataFrame
    risk_adj_returns = {}
    for sym, data in candidates.items():
        vol = data['vol']
        raw = data['returns']
        adj = {}
        for months, ret in raw.items():
            if pd.notna(ret) and vol is not None and vol > 0:
                adj[months] = ret / vol
            else:
                adj[months] = ret
        risk_adj_returns[sym] = adj

    returns_df = pd.DataFrame(risk_adj_returns).T
    scored = compute_composite_scores(returns_df, RETURN_PERIOD_WEIGHTS)

    # Enrich with vol and raw returns
    results = []
    for i, item in enumerate(scored, start=1):
        symbol = item['symbol']
        returns_raw = candidates[symbol]['returns']
        vol = candidates[symbol]['vol']
        results.append({
            'rank': i,
            'symbol': symbol,
            'composite_score': item['composite_score'],
            'annualized_vol': round(vol * 100, 2) if vol is not None else None,
            'returns': {
                '1_month': round(returns_raw[1] * 100, 2) if pd.notna(returns_raw.get(1)) else None,
                '3_month': round(returns_raw[3] * 100, 2) if pd.notna(returns_raw.get(3)) else None,
                '6_month': round(returns_raw[6] * 100, 2) if pd.notna(returns_raw.get(6)) else None,
            },
        })

    return results


def analyze_commodities(data_dir: Path, allocation_percentage: float,
                        symbols: Optional[List[str]] = None) -> Dict:
    """
    Analyze Commodities/Metals opportunities.

    Args:
        data_dir: Path to data directory containing CSV files
        allocation_percentage: Target allocation percentage for commodities sleeve
        symbols: Optional list of specific symbols to analyze

    Returns:
        dict: Analysis results with recommended assets and weights
    """
    logging.info(f"Analyzing Commodities/Metals with {allocation_percentage:.2%} allocation")

    exclusive_pairs = []
    if symbols is None:
        from ..config import SLEEVE_CONFIG
        cfg = SLEEVE_CONFIG['commodities']
        symbols = cfg.get('symbols', [])
        exclusive_pairs = cfg.get('exclusive_pairs', [])

    if not symbols:
        logging.warning("No symbols configured for commodities sleeve")
        return {
            'sleeve': 'commodities',
            'allocation_percentage': allocation_percentage,
            'selected_etfs': [],
            'weights': {},
            'total_allocation': 0.0
        }

    ranked = rank_commodities(symbols, data_dir)

    # Enforce mutual exclusion pairs (GLD/GDX, SLV/SIL)
    selected = apply_exclusive_pairs(ranked, exclusive_pairs)

    # Cap to top 4 after exclusion
    selected = selected[:4]

    # Re-assign ranks after exclusion and capping
    for i, etf in enumerate(selected, start=1):
        etf['rank'] = i

    assets = [etf['symbol'] for etf in selected]

    logging.info(f"Selected {len(selected)} commodity ETFs: {assets}")

    weights = compute_position_weights(selected)

    return {
        'sleeve': 'commodities',
        'allocation_percentage': allocation_percentage,
        'selected_etfs': selected,
        'weights': weights,
        'total_allocation': allocation_percentage if selected else 0.0
    }
