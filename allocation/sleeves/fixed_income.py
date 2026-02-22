"""
Fixed Income sleeve analyzer.

Ranks bond ETFs using short/medium-term momentum with regime-based
eligibility filtering instead of a 200DMA gate.

The regime determines which bond ETFs are appropriate:
- Risk-on / moderate: short duration and core (SGOV, AGG, TIP) — no long
  duration TLT because rates may rise in a strong economy.
- Elevated: all four eligible — TLT allowed as a hedge option.
- Risk-off / crisis: all eligible — long duration treasuries rally hardest
  in flight-to-quality environments.

Uses raw returns (not risk-adjusted) because the four ETFs are intentionally
different in duration and risk profile. The investor wants to pick the
best-performing *type* of bond, not normalize away the differences.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Optional
from ..utils import (load_etf_data, compute_position_weights,
                     calculate_period_return, compute_composite_scores)

RETURN_PERIOD_WEIGHTS = {
    1: 0.50,   # 1 month — most important
    3: 0.30,   # 3 month
    6: 0.20,   # 6 month
}


def get_eligible_symbols(regime_key: str, all_symbols: List[str]) -> List[str]:
    """
    Return the subset of symbols eligible for the current regime.

    Falls back to all_symbols if no mapping is configured.
    """
    from ..config import SLEEVE_CONFIG
    regime_map = SLEEVE_CONFIG['fixed_income'].get('regime_eligible', {})
    eligible = regime_map.get(regime_key)
    if eligible is None:
        logging.warning(f"No regime_eligible mapping for '{regime_key}', using all symbols")
        return all_symbols
    # Only include symbols that are in both the eligible list and the master list
    return [s for s in eligible if s in all_symbols]


def rank_fixed_income(symbols: List[str], data_dir: Path) -> List[Dict]:
    """
    Rank fixed income ETFs by raw composite momentum.

    Process:
    1. Load data for each symbol
    2. Compute 1/3/6 month returns (raw, not risk-adjusted)
    3. Rank by weighted composite score

    No 200DMA filter — the regime-based eligibility replaces it.

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
        logging.warning("No fixed income ETF data loaded; nothing to rank.")
        return []

    # Compute returns for each symbol
    candidates = {}
    for symbol, df in etf_data.items():
        returns = {}
        for months in RETURN_PERIOD_WEIGHTS:
            returns[months] = calculate_period_return(df, months)
        candidates[symbol] = {'returns': returns}

    if not candidates:
        return []

    # Build returns DataFrame and rank via shared utility
    returns_df = pd.DataFrame(
        {sym: data['returns'] for sym, data in candidates.items()}
    ).T
    scored = compute_composite_scores(returns_df, RETURN_PERIOD_WEIGHTS)

    # Enrich with raw returns
    results = []
    for i, item in enumerate(scored, start=1):
        symbol = item['symbol']
        returns_raw = candidates[symbol]['returns']
        results.append({
            'rank': i,
            'symbol': symbol,
            'composite_score': item['composite_score'],
            'returns': {
                '1_month': round(returns_raw[1] * 100, 2) if pd.notna(returns_raw.get(1)) else None,
                '3_month': round(returns_raw[3] * 100, 2) if pd.notna(returns_raw.get(3)) else None,
                '6_month': round(returns_raw[6] * 100, 2) if pd.notna(returns_raw.get(6)) else None,
            },
        })

    return results


def analyze_fixed_income(data_dir: Path, allocation_percentage: float,
                         regime_key: str = 'moderate_risk',
                         symbols: Optional[List[str]] = None) -> Dict:
    """
    Analyze Fixed Income opportunities.

    Args:
        data_dir: Path to data directory containing CSV files
        allocation_percentage: Target allocation percentage for fixed income sleeve
        regime_key: Current regime key (e.g. 'risk_on', 'crisis') — controls
                    which ETFs are eligible
        symbols: Optional override list of symbols (bypasses regime filtering)

    Returns:
        dict: Analysis results with recommended assets and weights
    """
    logging.info(f"Analyzing Fixed Income with {allocation_percentage:.2%} allocation (regime={regime_key})")

    if symbols is None:
        from ..config import SLEEVE_CONFIG
        all_symbols = SLEEVE_CONFIG['fixed_income'].get('symbols', [])
        symbols = get_eligible_symbols(regime_key, all_symbols)
        logging.info(f"Regime '{regime_key}' eligible FI symbols: {symbols}")

    if not symbols:
        logging.warning("No symbols eligible for fixed income sleeve")
        return {
            'sleeve': 'fixed_income',
            'allocation_percentage': allocation_percentage,
            'regime_key': regime_key,
            'eligible_symbols': [],
            'selected_etfs': [],
            'weights': {},
            'total_allocation': 0.0
        }

    ranked = rank_fixed_income(symbols, data_dir)

    assets = [etf['symbol'] for etf in ranked]
    logging.info(f"Selected {len(ranked)} fixed income ETFs: {assets}")

    weights = compute_position_weights(ranked)

    return {
        'sleeve': 'fixed_income',
        'allocation_percentage': allocation_percentage,
        'regime_key': regime_key,
        'eligible_symbols': symbols,
        'selected_etfs': ranked,
        'weights': weights,
        'total_allocation': allocation_percentage if ranked else 0.0
    }
