"""
Volatility Hedge sleeve analyzer.

Event-driven tactical overlay that deploys capital only when volatility is
rising. Unlike other sleeves, the default state is "inactive" — no position.

Entry/exit is controlled by VIX Bollinger Band %B:
- Entry: VIX %B > 0.8 AND VIX > 20 (vol rising through upper range)
- Exit:  VIX %B < 0.5 OR VIX < 18 (vol mean-reverting)

Instrument priority (not momentum-ranked like other sleeves):
- UVXY: pure VIX spike trade, only when %B > 1.0 (VIX above upper Bollinger)
- TAIL: structural put-spread hedge, less decay, preferred for sustained vol
- CAOS: alternative tail risk ETF, backup to TAIL

The regime allocation determines *how much* (0-15%); the VIX signal determines
*whether* to deploy at all.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Optional
from ..utils import load_csv_data


# Bollinger Band parameters for VIX
BB_WINDOW = 20       # 20-day SMA
BB_STD_MULT = 2.0    # 2 standard deviations

# Entry/exit thresholds
VIX_ENTRY_LEVEL = 20       # Minimum VIX level to consider entry
VIX_EXIT_LEVEL = 18        # VIX below this = exit
BB_ENTRY_THRESHOLD = 0.8   # %B above this = entry signal
BB_EXIT_THRESHOLD = 0.5    # %B below this = exit signal
BB_SPIKE_THRESHOLD = 1.0   # %B above this = active spike (UVXY territory)

# Default ETF universe
DEFAULT_SYMBOLS = ['UVXY', 'TAIL', 'CAOS']


def load_vix_data(data_dir: Path) -> Optional[pd.DataFrame]:
    """
    Load VIX data from the TradingView CSV.

    Returns DataFrame with datetime index and OHLCV columns, or None on failure.
    """
    try:
        df = load_csv_data('VIX.csv', data_dir)
        if not df.index.is_monotonic_increasing:
            df = df.sort_index()
        return df
    except Exception as e:
        logging.error(f"Failed to load VIX data: {e}")
        return None


def compute_bollinger_pctb(series: pd.Series, window: int = BB_WINDOW,
                           num_std: float = BB_STD_MULT) -> Optional[float]:
    """
    Compute Bollinger Band %B for the most recent value.

    %B = (value - lower_band) / (upper_band - lower_band)
    %B > 1 means above upper band, %B < 0 means below lower band.
    """
    if series is None or len(series) < window:
        return None

    sma = series.rolling(window=window, min_periods=window).mean()
    std = series.rolling(window=window, min_periods=window).std()

    upper = sma + num_std * std
    lower = sma - num_std * std

    latest_upper = upper.iloc[-1]
    latest_lower = lower.iloc[-1]
    latest_value = series.iloc[-1]

    if pd.isna(latest_upper) or pd.isna(latest_lower):
        return None

    band_width = latest_upper - latest_lower
    if band_width == 0:
        return None

    return float((latest_value - latest_lower) / band_width)


def compute_vix_momentum(series: pd.Series, lookback: int = 5) -> Optional[float]:
    """
    Compute VIX momentum: percentage change over lookback days.
    Positive = VIX rising, negative = VIX falling.
    """
    if series is None or len(series) < lookback + 1:
        return None

    current = series.iloc[-1]
    past = series.iloc[-(lookback + 1)]

    if pd.isna(current) or pd.isna(past) or past == 0:
        return None

    return float((current / past) - 1.0)


def evaluate_vix_signal(data_dir: Path) -> Dict:
    """
    Evaluate VIX conditions to determine vol hedge entry/exit.

    Returns:
        dict with:
          - active: bool (should hedge be deployed?)
          - spike: bool (is VIX in active spike territory — UVXY appropriate?)
          - vix_close: float
          - vix_pctb: float (Bollinger %B)
          - vix_momentum_5d: float (5-day VIX change)
          - signal: str ('inactive', 'entry', 'spike', 'exit')
    """
    vix_df = load_vix_data(data_dir)

    if vix_df is None or vix_df.empty or 'close' not in vix_df.columns:
        logging.warning("VIX data unavailable — vol hedge inactive")
        return {
            'active': False, 'spike': False,
            'vix_close': None, 'vix_pctb': None,
            'vix_momentum_5d': None, 'signal': 'no_data'
        }

    vix_close = float(vix_df['close'].iloc[-1])
    vix_pctb = compute_bollinger_pctb(vix_df['close'])
    vix_momentum = compute_vix_momentum(vix_df['close'])

    # Determine signal
    if vix_pctb is None:
        signal = 'no_data'
        active = False
        spike = False
    elif vix_close >= VIX_ENTRY_LEVEL and vix_pctb >= BB_SPIKE_THRESHOLD:
        signal = 'spike'
        active = True
        spike = True
    elif vix_close >= VIX_ENTRY_LEVEL and vix_pctb >= BB_ENTRY_THRESHOLD:
        signal = 'entry'
        active = True
        spike = False
    elif vix_close < VIX_EXIT_LEVEL or vix_pctb < BB_EXIT_THRESHOLD:
        signal = 'exit'
        active = False
        spike = False
    else:
        # VIX between exit and entry thresholds — maintain current state
        # Since we don't persist state, treat as inactive (conservative)
        signal = 'neutral'
        active = False
        spike = False

    return {
        'active': active,
        'spike': spike,
        'vix_close': round(vix_close, 2),
        'vix_pctb': round(vix_pctb, 4) if vix_pctb is not None else None,
        'vix_momentum_5d': round(vix_momentum, 4) if vix_momentum is not None else None,
        'signal': signal,
    }


def select_instruments(vix_signal: Dict, symbols: List[str]) -> List[Dict]:
    """
    Select which vol hedge instruments to use based on VIX conditions.

    Priority:
    - Spike (%B > 1.0): UVXY first (pure VIX leverage), then TAIL
    - Entry (%B 0.8-1.0): TAIL first (less decay), then CAOS
    - Inactive: empty list

    Returns list of dicts with rank, symbol, and rationale.
    """
    if not vix_signal.get('active', False):
        return []

    available = set(symbols)
    selected = []

    if vix_signal.get('spike', False):
        # Active spike — UVXY for the VIX pop, TAIL for duration
        priority = ['UVXY', 'TAIL', 'CAOS']
    else:
        # Rising vol but not spiking — structural hedges only, no UVXY (too much decay)
        priority = ['TAIL', 'CAOS']

    for rank, sym in enumerate(priority, start=1):
        if sym in available:
            rationale = _instrument_rationale(sym, vix_signal)
            selected.append({
                'rank': rank,
                'symbol': sym,
                'rationale': rationale,
            })

    return selected


def _instrument_rationale(symbol: str, vix_signal: Dict) -> str:
    """Generate a brief explanation for why this instrument is selected."""
    pctb = vix_signal.get('vix_pctb')
    vix = vix_signal.get('vix_close')
    pctb_str = f"{pctb:.2f}" if pctb is not None else "N/A"

    if symbol == 'UVXY':
        return f"VIX spike trade — VIX={vix}, %B={pctb_str} (above upper Bollinger)"
    elif symbol == 'TAIL':
        return f"Structural put hedge — VIX={vix}, %B={pctb_str}"
    elif symbol == 'CAOS':
        return f"Tail risk hedge — VIX={vix}, %B={pctb_str}"
    return f"Vol hedge — VIX={vix}, %B={pctb_str}"


def analyze_vol_hedges(data_dir: Path, allocation_percentage: float,
                       symbols: Optional[List[str]] = None,
                       regime_key: str = 'moderate_risk') -> Dict:
    """
    Analyze Volatility Hedge opportunities.

    This sleeve is event-driven: it only deploys capital when VIX signals
    indicate rising volatility. When inactive, it returns 0% allocation
    regardless of what the regime rules say.

    Args:
        data_dir: Path to data directory containing CSV files
        allocation_percentage: Target allocation percentage for vol hedges sleeve
        symbols: Optional list of specific symbols to analyze
        regime_key: Current regime key (passed through for output context)

    Returns:
        dict: Analysis results with hedge status, selected instruments, and weights
    """
    logging.info(f"Analyzing Vol Hedges with {allocation_percentage:.2%} allocation")

    if symbols is None:
        from ..config import SLEEVE_CONFIG
        symbols = SLEEVE_CONFIG['vol_hedges'].get('symbols', DEFAULT_SYMBOLS)

    # Evaluate VIX conditions
    vix_signal = evaluate_vix_signal(data_dir)

    # Select instruments based on VIX signal
    selected = select_instruments(vix_signal, symbols)

    if not selected:
        logging.info(f"Vol hedge INACTIVE — VIX signal: {vix_signal['signal']}")
        effective_allocation = 0.0
    else:
        effective_allocation = allocation_percentage
        assets = [s['symbol'] for s in selected]
        logging.info(f"Vol hedge ACTIVE — signal: {vix_signal['signal']}, "
                     f"instruments: {assets}")

    # Priority-based weights: first instrument gets 60%, second 40%
    # (or 100% if only one)
    weights = {}
    if len(selected) == 1:
        weights[selected[0]['symbol']] = 1.0
    elif len(selected) == 2:
        weights[selected[0]['symbol']] = 0.6
        weights[selected[1]['symbol']] = 0.4
    elif len(selected) >= 3:
        weights[selected[0]['symbol']] = 0.5
        weights[selected[1]['symbol']] = 0.3
        weights[selected[2]['symbol']] = 0.2

    return {
        'sleeve': 'vol_hedges',
        'allocation_percentage': allocation_percentage,
        'regime_key': regime_key,
        'vix_signal': vix_signal,
        'selected_etfs': selected,
        'weights': weights,
        'total_allocation': effective_allocation,
    }
