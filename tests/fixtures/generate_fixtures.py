"""
Generate fixture CSV files for smoke tests.

Run this script once to create static test data. The generated files
are deterministic (fixed random seed) so tests are reproducible.
"""

import pandas as pd
import numpy as np
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent

# Fixed seed for reproducibility
RNG = np.random.default_rng(42)

# 300 trading days of data (enough for 200DMA + 6mo returns)
N_DAYS = 300


def generate_ohlcv(symbol: str, base_price: float = 100.0,
                   drift: float = 0.0003, vol: float = 0.015,
                   above_200dma: bool = True) -> pd.DataFrame:
    """Generate synthetic OHLCV data for a ticker."""
    dates = pd.bdate_range(end='2026-02-14', periods=N_DAYS)

    # Random walk with drift
    if above_200dma:
        # Ensure price ends above 200DMA by using positive drift
        drift = abs(drift) + 0.0002
    else:
        # Ensure price ends below 200DMA
        drift = -abs(drift) - 0.0001

    log_returns = RNG.normal(drift, vol, N_DAYS)
    prices = base_price * np.exp(np.cumsum(log_returns))

    high = prices * (1 + RNG.uniform(0.001, 0.02, N_DAYS))
    low = prices * (1 - RNG.uniform(0.001, 0.02, N_DAYS))
    open_prices = prices * (1 + RNG.normal(0, 0.005, N_DAYS))
    volume = RNG.integers(100000, 10000000, N_DAYS)

    df = pd.DataFrame({
        'open': open_prices,
        'high': high,
        'low': low,
        'close': prices,
        'volume': volume,
    }, index=dates)
    df.index.name = 'datetime'

    return df


def generate_vix_data() -> pd.DataFrame:
    """Generate synthetic VIX data — mean-reverting around 18."""
    dates = pd.bdate_range(end='2026-02-14', periods=N_DAYS)

    vix = np.zeros(N_DAYS)
    vix[0] = 18.0
    for i in range(1, N_DAYS):
        # Mean reversion to 18
        vix[i] = vix[i-1] + 0.1 * (18 - vix[i-1]) + RNG.normal(0, 0.8)
        vix[i] = max(vix[i], 9)  # VIX floor

    df = pd.DataFrame({
        'symbol': 'CBOE:VIX',
        'open': vix,
        'high': vix * 1.02,
        'low': vix * 0.98,
        'close': vix,
        'volume': 0,
    }, index=dates)
    df.index.name = 'datetime'

    return df


def main():
    # Equity ETFs (above 200DMA)
    for sym in ['SPY', 'QQQ', 'VTI', 'IWM', 'CWI']:
        df = generate_ohlcv(sym, base_price=RNG.uniform(80, 500), above_200dma=True)
        df.to_csv(FIXTURE_DIR / f'{sym}.csv')

    # One equity below 200DMA (should be filtered out)
    df = generate_ohlcv('EEM', base_price=40, above_200dma=False)
    df.to_csv(FIXTURE_DIR / 'EEM.csv')

    # Managed futures
    for sym in ['KMLM', 'DBMF', 'CTA', 'WTMF', 'FMF']:
        df = generate_ohlcv(sym, base_price=RNG.uniform(20, 40), above_200dma=True)
        df.to_csv(FIXTURE_DIR / f'{sym}.csv')

    # Commodities
    for sym in ['DBC', 'GLD', 'SLV', 'GDX', 'SIL', 'COPX', 'URNM', 'USO', 'DBA']:
        df = generate_ohlcv(sym, base_price=RNG.uniform(15, 200), above_200dma=True)
        df.to_csv(FIXTURE_DIR / f'{sym}.csv')

    # Crypto
    for sym in ['IBIT', 'ETHA', 'BITO', 'NODE']:
        df = generate_ohlcv(sym, base_price=RNG.uniform(20, 60), above_200dma=True)
        df.to_csv(FIXTURE_DIR / f'{sym}.csv')

    # Fixed income
    for sym in ['TLT', 'SGOV', 'TIP', 'AGG']:
        df = generate_ohlcv(sym, base_price=RNG.uniform(80, 120), vol=0.005, above_200dma=True)
        df.to_csv(FIXTURE_DIR / f'{sym}.csv')

    # Alternatives (vol hedge)
    for sym in ['UVXY', 'TAIL', 'CAOS']:
        df = generate_ohlcv(sym, base_price=RNG.uniform(10, 30), vol=0.03, above_200dma=False)
        df.to_csv(FIXTURE_DIR / f'{sym}.csv')

    # VIX
    vix_df = generate_vix_data()
    vix_df.to_csv(FIXTURE_DIR / 'VIX.csv')

    # Regime JSON
    import json
    regime = {
        "datetime": "2026-02-14T10:00:00",
        "background_color": "green",
        "above_200ma": True,
        "VIX_close": 15.5
    }
    with open(FIXTURE_DIR / 'spx-regime-results.json', 'w') as f:
        json.dump(regime, f, indent=2)

    print(f"Generated fixtures in {FIXTURE_DIR}")


if __name__ == '__main__':
    main()
