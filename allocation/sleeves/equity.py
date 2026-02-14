"""
Equity sleeve analyzer.

Contains analysis functions for all equity sub-modules:
- Ex-US equity
- US Large Cap
- Small Caps
- Total Market
- Sector ETFs
- Custom ETFs
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from ..utils import load_etf_data, compute_position_weights


# Configuration for return period weights
RETURN_PERIOD_WEIGHTS = {
    1: 0.50,   # 1 month weight
    3: 0.25,   # 3 month weight
    6: 0.15,   # 6 month weight
    12: 0.10  # 12 month weight
}

# Trading days per month (approximate)
TRADING_DAYS_PER_MONTH = 21


def is_above_200dma(df: pd.DataFrame) -> bool:
    """
    Return True if the most recent close is above the 200-day moving average.

    Assumes daily bars. If insufficient history or missing 'close', returns False.
    """
    if df is None or df.empty:
        return False
    if 'close' not in df.columns:
        return False
    if len(df) < 200:
        return False

    close = df['close'].iloc[-1]
    sma_200 = df['close'].rolling(window=200, min_periods=200).mean().iloc[-1]
    if pd.isna(close) or pd.isna(sma_200):
        return False
    return bool(close > sma_200)


def calculate_period_return(df: pd.DataFrame, months: int) -> float:
    """
    Calculate percentage return for a given period in months.
    
    Args:
        df: DataFrame with 'close' column and datetime index
        months: Number of months for the return period
        
    Returns:
        float: Percentage return (e.g., 0.05 for 5% return)
    """
    if len(df) < months * TRADING_DAYS_PER_MONTH:
        logging.warning(f"Insufficient data for {months}-month return calculation")
        return np.nan
    
    trading_days = months * TRADING_DAYS_PER_MONTH
    current_price = df['close'].iloc[-1]
    past_price = df['close'].iloc[-trading_days]
    
    if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
        return np.nan
    
    return (current_price / past_price) - 1.0


def calculate_returns_for_symbol(symbol: str, data_dir: Path) -> Dict[str, float]:
    """
    Calculate 1, 3, 6, and 12 month returns for a symbol.
    Uses hybrid approach: tries CSV first, falls back to yfinance.
    
    Args:
        symbol: ETF ticker symbol
        data_dir: Path to data directory containing CSV files
        
    Returns:
        dict: Dictionary with return periods as keys and returns as values
    """
    try:
        # Use hybrid load function that tries CSV first, then yfinance
        df = load_etf_data(symbol, data_dir)
        
        returns = {}
        for months in [1, 3, 6, 12]:
            returns[months] = calculate_period_return(df, months)
        
        return returns
    except Exception as e:
        logging.error(f"Error calculating returns for {symbol}: {e}")
        return {1: np.nan, 3: np.nan, 6: np.nan, 12: np.nan}


def rank_etfs_by_composite_score(symbols: List[str], data_dir: Path) -> List[Tuple[str, float, Dict]]:
    """
    Rank ETFs by composite score based on weighted return rankings.
    
    Args:
        symbols: List of ETF ticker symbols to rank
        data_dir: Path to data directory containing CSV files
        
    Returns:
        list: List of tuples (symbol, composite_score, returns_dict) sorted by composite score (descending, best first)
    """
    # Calculate returns for all symbols (skip any ETF not above its 200DMA)
    symbol_returns: Dict[str, Dict[int, float]] = {}
    for symbol in symbols:
        try:
            df = load_etf_data(symbol, data_dir)
            if not df.index.is_monotonic_increasing:
                df = df.sort_index()

            # Log the most recent bar so we can verify the data used
            try:
                tail_rows = df.tail(3)
                logging.info(f"\n=== {symbol} most recent bars (tail) ===\n{tail_rows}\n")
                last_ts = df.index[-1] if len(df) else None
                last_row = df.iloc[-1] if len(df) else None
                ohlc_cols = [c for c in ['open', 'high', 'low', 'close'] if c in df.columns]
                last_ohlc = last_row[ohlc_cols].to_dict() if (last_row is not None and ohlc_cols) else {}
                logging.info(f"{symbol} last bar: {last_ts} OHLC={last_ohlc}")
            except Exception as log_err:
                logging.warning(f"{symbol}: failed to log tail/last bar: {log_err}")

            if not is_above_200dma(df):
                close = df['close'].iloc[-1] if ('close' in df.columns and len(df)) else None
                sma_200 = (
                    df['close'].rolling(window=200, min_periods=200).mean().iloc[-1]
                    if ('close' in df.columns and len(df) >= 200)
                    else None
                )
                logging.info(
                    f"{symbol}: excluded (not above 200DMA). close={close} sma200={sma_200}"
                )
                continue

            returns: Dict[int, float] = {}
            for months in [1, 3, 6, 12]:
                returns[months] = calculate_period_return(df, months)
            symbol_returns[symbol] = returns
        except Exception as e:
            logging.error(f"Error loading/calculating returns for {symbol}: {e}")
            continue

    if not symbol_returns:
        logging.warning("No ETFs passed the 200DMA filter; nothing to rank.")
        return []

    # Create DataFrame with returns
    returns_df = pd.DataFrame.from_dict(symbol_returns, orient='index')
    returns_df = returns_df.reindex(columns=[1, 3, 6, 12])  # Column names are months
    
    # Rank returns for each period (1 = best return, higher number = worse return)
    # Using method='min' so ties get the same rank, and ascending=False so higher returns get lower ranks
    ranks_df = returns_df.rank(method='min', ascending=False, na_option='keep')
    
    # Calculate composite score for each symbol
    # Invert ranks so higher composite_score = better performance
    num_symbols = len(returns_df.index)
    results = []
    for symbol in returns_df.index:
        composite_score = 0.0
        returns_dict = symbol_returns[symbol]
        
        for months, weight in RETURN_PERIOD_WEIGHTS.items():
            rank = ranks_df.loc[symbol, months]
            if pd.notna(rank):
                # Invert rank: rank 1 (best) becomes num_symbols (highest score)
                # rank N (worst) becomes 1 (lowest score)
                inverted_rank = num_symbols + 1 - rank
                composite_score += inverted_rank * weight
            else:
                # If data is missing, assign worst score (0)
                composite_score += 0.0
        
        results.append((symbol, composite_score, returns_dict))
    
    # Sort by composite score (descending - higher is better)
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results


def analyze_equity_sub_sleeve(symbols: List[str], data_dir: Path, 
                               sub_module_name: str) -> Dict:
    """
    Analyze an equity sub-sleeve by ranking ETFs using composite score.
    
    Args:
        symbols: List of ETF ticker symbols for this sub-sleeve
        data_dir: Path to data directory containing CSV files
        sub_module_name: Name of the sub-module (e.g., 'ex_us', 'us_large_cap')
        
    Returns:
        dict: Analysis results with ranked assets and their scores
    """
    if not symbols:
        logging.warning(f"No symbols provided for {sub_module_name}")
        return {
            'sleeve': 'equity',
            'sub_module': sub_module_name,
            'assets': [],
            'weights': {},
            'allocation': 0.0,
            'rankings': []
        }
    
    logging.info(f"Ranking {len(symbols)} ETFs for {sub_module_name}")
    
    # Rank ETFs by composite score
    ranked_etfs = rank_etfs_by_composite_score(symbols, data_dir)
    
    # Extract rankings and scores
    rankings = []
    for rank, (symbol, composite_score, returns_dict) in enumerate(ranked_etfs, start=1):
        rankings.append({
            'rank': rank,
            'symbol': symbol,
            'composite_score': round(composite_score, 4),
            'returns': {
                '1_month': round(returns_dict[1] * 100, 2) if pd.notna(returns_dict[1]) else None,
                '3_month': round(returns_dict[3] * 100, 2) if pd.notna(returns_dict[3]) else None,
                '6_month': round(returns_dict[6] * 100, 2) if pd.notna(returns_dict[6]) else None,
                '12_month': round(returns_dict[12] * 100, 2) if pd.notna(returns_dict[12]) else None
            }
        })
    
    # For now, return all ranked ETFs (weights can be assigned later based on ranking)
    # Top ranked ETFs could get higher weights
    assets = [item['symbol'] for item in rankings]
    weights = {}  # Will be populated based on allocation strategy
    
    return {
        'sleeve': 'equity',
        'sub_module': sub_module_name,
        'assets': assets,
        'weights': weights,
        'allocation': 0.0,
        'rankings': rankings
    }


def analyze_ex_us(data_dir: Path, symbols: Optional[List[str]] = None) -> Dict:
    """
    Analyze Ex-US equity opportunities.
    
    Args:
        data_dir: Path to data directory containing CSV files
        symbols: List of ETF ticker symbols for Ex-US equity (e.g., ['VEA', 'VXUS', 'IEFA'])
        
    Returns:
        dict: Analysis results with recommended assets and weights
    """
    logging.info("Analyzing Ex-US equity opportunities")
    
    if symbols is None:
        # Read symbols from config
        from ..config import SLEEVE_CONFIG
        symbols = SLEEVE_CONFIG['equity']['sub_modules'].get('ex_us', {}).get('symbols', [])
        if not symbols:
            logging.warning("No symbols provided for Ex-US equity analysis")
    
    return analyze_equity_sub_sleeve(symbols, data_dir, 'ex_us')


def analyze_us_large_cap(data_dir: Path, symbols: Optional[List[str]] = None) -> Dict:
    """
    Analyze US Large Cap equity opportunities.
    
    Args:
        data_dir: Path to data directory containing CSV files
        symbols: List of ETF ticker symbols for US Large Cap (e.g., ['SPY', 'VOO', 'IVV'])
        
    Returns:
        dict: Analysis results with recommended assets and weights
    """
    logging.info("Analyzing US Large Cap equity opportunities")
    
    if symbols is None:
        # Read symbols from config
        from ..config import SLEEVE_CONFIG
        symbols = SLEEVE_CONFIG['equity']['sub_modules'].get('us_large_cap', {}).get('symbols', [])
        if not symbols:
            logging.warning("No symbols provided for US Large Cap analysis")
    
    return analyze_equity_sub_sleeve(symbols, data_dir, 'us_large_cap')


def analyze_small_caps(data_dir: Path, symbols: Optional[List[str]] = None) -> Dict:
    """
    Analyze Small Caps equity opportunities.
    
    Args:
        data_dir: Path to data directory containing CSV files
        symbols: List of ETF ticker symbols for Small Caps (e.g., ['IWM', 'VB', 'SCHA'])
        
    Returns:
        dict: Analysis results with recommended assets and weights
    """
    logging.info("Analyzing Small Caps equity opportunities")
    
    if symbols is None:
        # Read symbols from config
        from ..config import SLEEVE_CONFIG
        symbols = SLEEVE_CONFIG['equity']['sub_modules'].get('small_caps', {}).get('symbols', [])
        if not symbols:
            logging.warning("No symbols provided for Small Caps analysis")
    
    return analyze_equity_sub_sleeve(symbols, data_dir, 'small_caps')


def analyze_total_market(data_dir: Path, symbols: Optional[List[str]] = None) -> Dict:
    """
    Analyze Total Market equity opportunities.
    
    Args:
        data_dir: Path to data directory containing CSV files
        symbols: List of ETF ticker symbols for Total Market (e.g., ['VTI', 'ITOT', 'SWTSX'])
        
    Returns:
        dict: Analysis results with recommended assets and weights
    """
    logging.info("Analyzing Total Market equity opportunities")
    
    if symbols is None:
        # Read symbols from config
        from ..config import SLEEVE_CONFIG
        symbols = SLEEVE_CONFIG['equity']['sub_modules'].get('total_market', {}).get('symbols', [])
        if not symbols:
            logging.warning("No symbols provided for Total Market analysis")
    
    return analyze_equity_sub_sleeve(symbols, data_dir, 'total_market')


def analyze_sector_etfs(data_dir: Path, symbols: Optional[List[str]] = None) -> Dict:
    """
    Analyze Sector ETFs opportunities.
    
    Args:
        data_dir: Path to data directory containing CSV files
        symbols: List of ETF ticker symbols for Sector ETFs (e.g., ['XLK', 'XLF', 'XLE', ...])
        
    Returns:
        dict: Analysis results with recommended assets and weights
    """
    logging.info("Analyzing Sector ETFs opportunities")
    
    if symbols is None:
        # Read symbols from config
        from ..config import SLEEVE_CONFIG
        symbols = SLEEVE_CONFIG['equity']['sub_modules'].get('sector_etfs', {}).get('symbols', [])
        if not symbols:
            logging.warning("No symbols provided for Sector ETFs analysis")
    
    return analyze_equity_sub_sleeve(symbols, data_dir, 'sector_etfs')


def analyze_custom_etfs(data_dir: Path, symbols: Optional[List[str]] = None) -> Dict:
    """
    Analyze Custom ETFs opportunities.
    
    Args:
        data_dir: Path to data directory containing CSV files
        symbols: List of ETF ticker symbols for Custom ETFs
        
    Returns:
        dict: Analysis results with recommended assets and weights
    """
    logging.info("Analyzing Custom ETFs opportunities")
    
    if symbols is None:
        # Read symbols from config
        from ..config import SLEEVE_CONFIG
        symbols = SLEEVE_CONFIG['equity']['sub_modules'].get('custom_etfs', {}).get('symbols', [])
        if not symbols:
            logging.warning("No symbols provided for Custom ETFs analysis")
    
    return analyze_equity_sub_sleeve(symbols, data_dir, 'custom_etfs')


def analyze_equity_sleeve(data_dir: Path, allocation_percentage: float, 
                          enabled_sub_modules: Optional[Dict] = None) -> Dict:
    """
    Analyze the entire equity sleeve, running all enabled sub-modules.
    
    Args:
        data_dir: Path to data directory containing CSV files
        allocation_percentage: Target allocation percentage for equity sleeve
        enabled_sub_modules: Optional dict of enabled sub-modules. If None, all are enabled.
        
    Returns:
        dict: Combined equity analysis results
    """
    logging.info(f"Analyzing equity sleeve with {allocation_percentage:.2%} allocation")
    
    # Default to all sub-modules enabled if not specified
    if enabled_sub_modules is None:
        from ..config import SLEEVE_CONFIG
        enabled_sub_modules = SLEEVE_CONFIG['equity'].get('sub_modules', {})
    
    sub_module_results = []
    
    # Run each enabled sub-module
    if enabled_sub_modules.get('ex_us', {}).get('enabled', False):
        symbols = enabled_sub_modules.get('ex_us', {}).get('symbols', None)
        sub_module_results.append(analyze_ex_us(data_dir, symbols=symbols))
    
    if enabled_sub_modules.get('us_large_cap', {}).get('enabled', False):
        symbols = enabled_sub_modules.get('us_large_cap', {}).get('symbols', None)
        sub_module_results.append(analyze_us_large_cap(data_dir, symbols=symbols))
    
    if enabled_sub_modules.get('small_caps', {}).get('enabled', False):
        symbols = enabled_sub_modules.get('small_caps', {}).get('symbols', None)
        sub_module_results.append(analyze_small_caps(data_dir, symbols=symbols))
    
    if enabled_sub_modules.get('total_market', {}).get('enabled', False):
        symbols = enabled_sub_modules.get('total_market', {}).get('symbols', None)
        sub_module_results.append(analyze_total_market(data_dir, symbols=symbols))
    
    if enabled_sub_modules.get('sector_etfs', {}).get('enabled', False):
        symbols = enabled_sub_modules.get('sector_etfs', {}).get('symbols', None)
        sub_module_results.append(analyze_sector_etfs(data_dir, symbols=symbols))
    
    if enabled_sub_modules.get('custom_etfs', {}).get('enabled', False):
        symbols = enabled_sub_modules.get('custom_etfs', {}).get('symbols', None)
        sub_module_results.append(analyze_custom_etfs(data_dir, symbols=symbols))
    
    # Collect all rankings from all sub-modules with their sub_module names
    all_rankings = []
    for result in sub_module_results:
        sub_module_name = result.get('sub_module', 'unknown')
        rankings = result.get('rankings', [])
        for ranking in rankings:
            # Add sub_module info to each ranking
            ranking_with_module = ranking.copy()
            ranking_with_module['sub_module'] = sub_module_name
            all_rankings.append(ranking_with_module)
    
    # Sort all rankings by composite_score (descending - higher is better)
    all_rankings.sort(key=lambda x: x.get('composite_score', float('-inf')), reverse=True)
    
    # Select top 4 ETFs, ensuring no more than 2 from any sub-module
    selected_etfs = []
    sub_module_counts = {}  # Track how many ETFs selected from each sub-module
    
    for ranking in all_rankings:
        if len(selected_etfs) >= 4:
            break
        
        sub_module = ranking['sub_module']
        current_count = sub_module_counts.get(sub_module, 0)
        
        # Only add if we haven't exceeded 2 per sub-module
        if current_count < 2:
            selected_etfs.append(ranking)
            sub_module_counts[sub_module] = current_count + 1
    
    logging.info(f"Selected {len(selected_etfs)} ETFs from equity sleeve: {[etf['symbol'] for etf in selected_etfs]}")
    
    # Create final assets and weights dictionaries
    final_assets = [etf['symbol'] for etf in selected_etfs]
    final_weights = compute_position_weights(selected_etfs)
    
    # Aggregate all assets (for backward compatibility)
    all_assets = {}
    for result in sub_module_results:
        for asset, weight in result.get('weights', {}).items():
            if asset in all_assets:
                all_assets[asset] += weight
            else:
                all_assets[asset] = weight
    
    return {
        'sleeve': 'equity',
        'allocation_percentage': allocation_percentage,
        'sub_modules': sub_module_results,
        'selected_etfs': selected_etfs,  # Top 4 selected ETFs with rankings
        'aggregated_assets': all_assets,
        'final_assets': final_assets,  # Final selected ETF symbols
        'final_weights': final_weights,  # Final weights (to be populated)
        'total_allocation': sum(all_assets.values()) if all_assets else 0.0
    }
