"""
Shared utilities for the allocation system.

Provides common functions for data loading, file I/O, and data processing.
"""

import pandas as pd
import numpy as np
import json
from datetime import date, datetime
from pathlib import Path
import logging
import time
from typing import Dict, List, Optional


class _NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# Try to import yfinance, but don't fail if it's not available
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.warning("yfinance not available. CSV fallback will be used.")


def get_data_dir() -> Path:
    """
    Get the path to the data directory.

    Respects PYNANCE_DATA_DIR env var for local development with fixtures.

    Returns:
        Path: Path to the data directory
    """
    import os
    override = os.environ.get('PYNANCE_DATA_DIR')
    if override:
        return Path(override)
    return Path(__file__).parent.parent / 'data'


def get_docs_dir() -> Path:
    """
    Get the path to the docs directory.
    
    Returns:
        Path: Path to the docs directory
    """
    return Path(__file__).parent.parent / 'docs'


def load_spx_regime_data() -> Dict:
    """
    Load SPX regime data from JSON file.
    
    Returns:
        dict: SPX regime data containing background_color, above_200ma, VIX_close, etc.
    
    Raises:
        FileNotFoundError: If the regime results file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    docs_dir = get_docs_dir()
    regime_file = docs_dir / 'spx-regime-results.json'
    
    if not regime_file.exists():
        raise FileNotFoundError(f"SPX regime results file not found: {regime_file}")
    
    try:
        with open(regime_file, 'r') as f:
            regime_data = json.load(f)
        logging.info(f"Loaded SPX regime data from: {regime_file}")
        return regime_data
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse SPX regime data: {e}")
        raise


def fetch_data_via_yfinance(symbol: str, retries: int = 3, delay: int = 2) -> pd.DataFrame:
    """
    Fetch data for a symbol using yfinance API.
    
    Args:
        symbol: Ticker symbol (e.g., 'VEA', 'SPY')
        retries: Number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        pd.DataFrame: DataFrame with datetime index and OHLCV columns
        
    Raises:
        ImportError: If yfinance is not available
        Exception: If data fetch fails after all retries
    """
    if not YFINANCE_AVAILABLE:
        raise ImportError("yfinance is not available. Install it with: pip install yfinance")
    
    for attempt in range(retries):
        try:
            logging.info(f"Fetching data for {symbol} via yfinance (attempt {attempt + 1}/{retries})...")
            ticker_obj = yf.Ticker(symbol)
            # Fetch up to 2 years of daily data to ensure we have enough for 12-month returns
            data = ticker_obj.history(period='2y', interval='1d')
            
            if data.empty:
                logging.warning(f"Empty data returned for {symbol}")
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
                raise ValueError(f"Empty data returned for {symbol} after {retries} attempts")
            
            # Ensure column names are lowercase to match CSV format
            data.columns = [col.lower() for col in data.columns]
            
            # Rename 'date' index if it exists, or ensure index is datetime
            if not isinstance(data.index, pd.DatetimeIndex):
                data.index = pd.to_datetime(data.index)
            
            logging.info(f"Successfully fetched {len(data)} rows for {symbol} via yfinance")
            return data
            
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logging.error(f"Failed to retrieve data for {symbol} after {retries} attempts")
                raise
    
    raise Exception(f"Failed to fetch data for {symbol} after {retries} attempts")


def load_csv_data(filename: str, data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load CSV data from the data directory.
    
    Args:
        filename: Name of the CSV file (e.g., 'SPX.csv')
        data_dir: Optional path to data directory. If None, uses default data directory.
        
    Returns:
        pd.DataFrame: DataFrame with datetime index
        
    Raises:
        FileNotFoundError: If the CSV file doesn't exist
    """
    if data_dir is None:
        data_dir = get_data_dir()
    
    filepath = data_dir / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    try:
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        logging.info(f"Loaded data from: {filepath}")
        return df
    except Exception as e:
        logging.error(f"Failed to load data from {filepath}: {e}")
        raise


def _is_csv_fresh(filepath: Path) -> bool:
    """Check if a CSV file was modified today."""
    if not filepath.exists():
        return False
    mtime = date.fromtimestamp(filepath.stat().st_mtime)
    return mtime == date.today()


# Module-level flag toggled by --force-refresh CLI arg
FORCE_REFRESH = False


def load_etf_data(symbol: str, data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load ETF data using hybrid approach: try fresh CSV first, fallback to yfinance.

    Write-through cache: after a successful yfinance fetch, saves to data/{SYMBOL}.csv
    so subsequent calls (or local re-runs) use the cached file. A CSV is considered
    fresh if it was modified today.

    Args:
        symbol: ETF ticker symbol (e.g., 'VEA', 'SPY')
        data_dir: Optional path to data directory. If None, uses default data directory.

    Returns:
        pd.DataFrame: DataFrame with datetime index and OHLCV columns

    Raises:
        Exception: If both CSV and yfinance fail
    """
    if data_dir is None:
        data_dir = get_data_dir()

    filename = f"{symbol}.csv"
    filepath = data_dir / filename

    # Try CSV first (must be from today, unless force-refresh bypasses cache entirely)
    if not FORCE_REFRESH:
        try:
            if _is_csv_fresh(filepath):
                df = load_csv_data(filename, data_dir)
                logging.info(f"Loaded {symbol} from fresh CSV cache")
                return df
            elif filepath.exists():
                logging.info(f"CSV for {symbol} is stale, refreshing via yfinance...")
            else:
                logging.info(f"No CSV for {symbol}, fetching via yfinance...")
        except Exception as e:
            logging.warning(f"Failed to load CSV for {symbol}: {e}, trying yfinance...")
    else:
        logging.info(f"Force refresh enabled, bypassing cache for {symbol}")

    # Fetch from yfinance and write-through to CSV
    if YFINANCE_AVAILABLE:
        try:
            df = fetch_data_via_yfinance(symbol)
            # Write-through: save to CSV for future calls
            try:
                df.to_csv(filepath)
                logging.info(f"Cached {symbol} to {filepath}")
            except Exception as e:
                logging.warning(f"Failed to cache {symbol} to CSV: {e}")
            return df
        except Exception as e:
            # If yfinance fails but a stale CSV exists, use it as fallback
            if filepath.exists():
                logging.warning(f"yfinance failed for {symbol}, falling back to stale CSV")
                return load_csv_data(filename, data_dir)
            logging.error(f"Failed to fetch {symbol} via yfinance: {e}")
            raise Exception(f"Failed to load data for {symbol} from both CSV and yfinance")
    else:
        if filepath.exists():
            logging.warning(f"yfinance not available, using existing CSV for {symbol}")
            return load_csv_data(filename, data_dir)
        raise ImportError(f"CSV file not found for {symbol} and yfinance is not available")


# ---------------------------------------------------------------------------
# Shared constants & analytics used by multiple sleeves
# ---------------------------------------------------------------------------

TRADING_DAYS_PER_MONTH = 21

# Realized vol lookback (63 trading days ≈ 3 months)
VOL_LOOKBACK_DAYS = 63


def calculate_period_return(df: pd.DataFrame, months: int) -> float:
    """
    Calculate percentage return for a given period in months.

    Args:
        df: DataFrame with 'close' column and datetime index
        months: Number of months for the return period

    Returns:
        float: Percentage return (e.g., 0.05 for 5% return)
    """
    trading_days = months * TRADING_DAYS_PER_MONTH
    if len(df) < trading_days:
        return np.nan

    current_price = df['close'].iloc[-1]
    past_price = df['close'].iloc[-trading_days]

    if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
        return np.nan

    return (current_price / past_price) - 1.0


def is_above_200dma(df: pd.DataFrame) -> bool:
    """
    Return True if the most recent close is above the 200-day moving average.

    Assumes daily bars. If insufficient history or missing 'close', returns False.
    """
    if df is None or df.empty or 'close' not in df.columns or len(df) < 200:
        return False

    close = df['close'].iloc[-1]
    sma_200 = df['close'].rolling(window=200, min_periods=200).mean().iloc[-1]
    if pd.isna(close) or pd.isna(sma_200):
        return False
    return bool(close > sma_200)


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


def compute_composite_scores(returns_df: pd.DataFrame,
                              period_weights: Dict[int, float]) -> List[Dict]:
    """
    Rank ETFs by weighted composite score from a returns DataFrame.

    Handles the rank-invert-weight pattern shared across all momentum sleeves.
    Each column in returns_df is a return period (e.g. 1, 3, 6 months) and each
    row is a symbol. Returns are ranked per-period (higher return = better rank),
    then ranks are inverted and combined via weighted sum.

    Args:
        returns_df: DataFrame with symbols as index, period months as columns.
                    Values are returns (raw or risk-adjusted).
        period_weights: Dict mapping period (months) to weight, e.g. {1: 0.5, 3: 0.3, 6: 0.2}

    Returns:
        List of dicts with 'symbol' and 'composite_score', sorted descending by score.
    """
    returns_df = returns_df.reindex(columns=list(period_weights.keys()))
    ranks_df = returns_df.rank(method='min', ascending=False, na_option='keep')
    num_symbols = len(returns_df)

    results = []
    for symbol in returns_df.index:
        composite_score = 0.0
        for months, weight in period_weights.items():
            rank = ranks_df.loc[symbol, months]
            if pd.notna(rank):
                inverted_rank = num_symbols + 1 - rank
                composite_score += inverted_rank * weight
        results.append({
            'symbol': symbol,
            'composite_score': round(composite_score, 4),
        })

    results.sort(key=lambda x: x['composite_score'], reverse=True)
    return results


def compute_position_weights(selected_etfs: List[Dict], score_key: str = 'composite_score',
                              min_weight: float = 0.10) -> Dict[str, float]:
    """
    Compute within-sleeve position weights from ranked ETF scores.

    Uses score-proportional weighting with a minimum floor to prevent
    near-zero allocations. Weights sum to 1.0.

    Args:
        selected_etfs: List of ETF dicts, each containing a score field and 'symbol'
        score_key: Key to use for score-based weighting
        min_weight: Minimum weight per position (prevents dust allocations)

    Returns:
        Dict mapping symbol to weight (summing to 1.0)
    """
    if not selected_etfs:
        return {}

    n = len(selected_etfs)
    if n == 1:
        return {selected_etfs[0]['symbol']: 1.0}

    # Extract scores; fall back to equal weight if scores are missing or all zero
    scores = []
    for etf in selected_etfs:
        s = etf.get(score_key, 0)
        scores.append(max(s, 0) if s is not None else 0)

    total_score = sum(scores)
    if total_score == 0:
        equal = round(1.0 / n, 4)
        return {etf['symbol']: equal for etf in selected_etfs}

    # Score-proportional weights
    raw_weights = [s / total_score for s in scores]

    # Enforce minimum weight floor
    weights = [max(w, min_weight) for w in raw_weights]
    total = sum(weights)
    weights = [round(w / total, 4) for w in weights]

    # Fix rounding so weights sum exactly to 1.0
    diff = round(1.0 - sum(weights), 4)
    if diff != 0 and weights:
        weights[0] = round(weights[0] + diff, 4)

    return {etf['symbol']: w for etf, w in zip(selected_etfs, weights)}


def load_multiple_csv_files(filenames: List[str], data_dir: Optional[Path] = None) -> Dict[str, pd.DataFrame]:
    """
    Load multiple CSV files from the data directory.
    
    Args:
        filenames: List of CSV filenames to load
        data_dir: Optional path to data directory. If None, uses default data directory.
        
    Returns:
        dict: Dictionary mapping filename (without .csv) to DataFrame
    """
    if data_dir is None:
        data_dir = get_data_dir()
    
    data_dict = {}
    
    for filename in filenames:
        try:
            df = load_csv_data(filename, data_dir)
            # Use filename without extension as key
            key = filename.replace('.csv', '')
            data_dict[key] = df
        except FileNotFoundError:
            logging.warning(f"Skipping missing file: {filename}")
            continue
        except Exception as e:
            logging.error(f"Failed to load {filename}: {e}")
            continue
    
    return data_dict


def archive_results(results: Dict, docs_dir: Optional[Path] = None) -> None:
    """
    Append today's results as a single JSON line to the rolling history log.

    File: docs/history/allocation-log.jsonl (one JSON object per line per day).
    This enables change detection, performance tracking, and historical analysis.
    """
    if docs_dir is None:
        docs_dir = get_docs_dir()

    history_dir = docs_dir / 'history'
    history_dir.mkdir(parents=True, exist_ok=True)
    log_path = history_dir / 'allocation-log.jsonl'

    try:
        line = json.dumps(results, cls=_NumpyEncoder, separators=(',', ':'))
        with open(log_path, 'a') as f:
            f.write(line + '\n')
        logging.info(f"Archived results to: {log_path}")
    except Exception as e:
        logging.warning(f"Failed to archive results: {e}")


def save_chart_data(results: Dict, data_dir: Path, docs_dir: Optional[Path] = None) -> None:
    """
    Pre-compute OHLC chart data for all selected ETFs and save as static JSON.

    Builds daily (last 250 rows) and weekly (last 250 weeks, resampled) OHLC arrays
    so the dashboard can render charts without hitting Yahoo Finance (CORS-blocked).

    Args:
        results: Allocation results dict containing sleeve_analyses
        data_dir: Path to data directory for loading CSVs
        docs_dir: Optional path to docs directory for output
    """
    if docs_dir is None:
        docs_dir = get_docs_dir()

    # Collect all unique symbols from sleeve results
    symbols = set()
    for sleeve_data in results.get('sleeve_analyses', {}).values():
        if sleeve_data.get('final_assets'):
            for sym in sleeve_data['final_assets']:
                symbols.add(sym)
        if sleeve_data.get('selected_etfs'):
            for etf in sleeve_data['selected_etfs']:
                if isinstance(etf, dict) and 'symbol' in etf:
                    symbols.add(etf['symbol'])

    if not symbols:
        logging.warning("No ETF symbols found in results — skipping chart data generation")
        return

    logging.info(f"Generating chart data for {len(symbols)} symbols: {sorted(symbols)}")

    daily_data = {}
    weekly_data = {}

    for symbol in sorted(symbols):
        try:
            df = load_etf_data(symbol, data_dir)
            if df.empty:
                continue

            # Ensure we have the required columns
            required = ['open', 'high', 'low', 'close']
            missing = [c for c in required if c not in df.columns]
            if missing:
                logging.warning(f"Skipping {symbol}: missing columns {missing}")
                continue

            # Ensure index is DatetimeIndex (CSV dates may not auto-parse)
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index, utc=True)
            if hasattr(df.index, 'tz') and df.index.tz is not None:
                df.index = df.index.tz_localize(None)

            # Daily: last 250 rows
            daily_df = df[required].tail(250).dropna()
            daily_bars = []
            for idx, row in daily_df.iterrows():
                daily_bars.append({
                    'time': idx.strftime('%Y-%m-%d'),
                    'open': round(float(row['open']), 2),
                    'high': round(float(row['high']), 2),
                    'low': round(float(row['low']), 2),
                    'close': round(float(row['close']), 2),
                })
            daily_data[symbol] = daily_bars

            # Weekly: resample to weekly OHLC, last 250 weeks
            weekly_df = df[required].resample('W').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
            }).dropna().tail(250)
            weekly_bars = []
            for idx, row in weekly_df.iterrows():
                weekly_bars.append({
                    'time': idx.strftime('%Y-%m-%d'),
                    'open': round(float(row['open']), 2),
                    'high': round(float(row['high']), 2),
                    'low': round(float(row['low']), 2),
                    'close': round(float(row['close']), 2),
                })
            weekly_data[symbol] = weekly_bars

            logging.info(f"Chart data for {symbol}: {len(daily_bars)} daily, {len(weekly_bars)} weekly bars")

        except Exception as e:
            logging.warning(f"Failed to generate chart data for {symbol}: {e}")

    chart_payload = {
        'generated': datetime.now().isoformat(),
        'daily': daily_data,
        'weekly': weekly_data,
    }

    save_results(chart_payload, 'chart-data.json', docs_dir)
    logging.info(f"Chart data saved with {len(daily_data)} symbols")


def save_results(results: Dict, filename: str, docs_dir: Optional[Path] = None) -> None:
    """
    Save results dictionary to JSON file in docs directory.
    
    Args:
        results: Dictionary containing results to save
        filename: Name of the output file (e.g., 'allocation-results.json')
        docs_dir: Optional path to docs directory. If None, uses default docs directory.
    """
    if docs_dir is None:
        docs_dir = get_docs_dir()
    
    docs_dir.mkdir(exist_ok=True)
    output_path = docs_dir / filename
    
    try:
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, cls=_NumpyEncoder)
        logging.info(f"Results saved to: {output_path}")
    except Exception as e:
        logging.error(f"Failed to save results to {output_path}: {e}")
        raise
