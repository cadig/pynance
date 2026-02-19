"""
Main allocation engine that orchestrates the asset allocation process.

This is the entry point for the allocation strategy system.
"""

import argparse
import logging
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List

# Handle both direct execution and module import
if __name__ == "__main__":
    # Add parent directory to path for direct execution
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from allocation.regime_allocator import get_allocation_summary
    from allocation.config import SLEEVE_CONFIG, OUTPUT_CONFIG
    from allocation.utils import get_data_dir, get_docs_dir, save_results, archive_results, load_spx_regime_data
    from allocation.rebalance import run_rebalance_check
    from allocation.llm_regime import run_llm_regime_analysis
    from allocation.sleeves import equity
    from allocation.sleeves import commodities
    from allocation.sleeves import crypto
    from allocation.sleeves import managed_futures
    from allocation.sleeves import vol_hedges
    from allocation.sleeves import fixed_income
    from allocation.portfolio_analytics import compute_portfolio_analytics
else:
    # Relative imports for module execution
    from .regime_allocator import get_allocation_summary
    from .config import SLEEVE_CONFIG, OUTPUT_CONFIG
    from .utils import get_data_dir, get_docs_dir, save_results, archive_results, load_spx_regime_data
    from .rebalance import run_rebalance_check
    from .llm_regime import run_llm_regime_analysis
    from .sleeves import equity
    from .sleeves import commodities
    from .sleeves import crypto
    from .sleeves import managed_futures
    from .sleeves import vol_hedges
    from .sleeves import fixed_income
    from .portfolio_analytics import compute_portfolio_analytics


SKIP_LLM = False


def validate_data_quality(regime_data: Dict, data_dir: Path) -> tuple:
    """
    Check input data quality and return (warnings, regime_data_age_hours, stale_regime_data).

    Checks:
    - Regime JSON has a datetime and it's from today (or at most 1 day old on weekends)
    - Key regime fields are present
    """
    warnings = []
    regime_data_age_hours = None
    stale_regime_data = False

    # Check regime data freshness
    regime_dt_str = regime_data.get('datetime')
    if not regime_dt_str:
        warnings.append("Regime data has no datetime — cannot verify freshness")
    else:
        try:
            regime_dt = datetime.fromisoformat(regime_dt_str)
            age = datetime.now() - regime_dt
            regime_data_age_hours = round(age.total_seconds() / 3600, 1)
            days_old = age.days
            if days_old > 3:
                warnings.append(f"Regime data is {days_old} days old (from {regime_dt_str})")
            # Flag stale on weekdays (Mon=0..Fri=4) if >3 days old
            if days_old > 3 and datetime.now().weekday() < 5:
                stale_regime_data = True
        except (ValueError, TypeError):
            warnings.append(f"Regime data has unparseable datetime: {regime_dt_str}")

    # Check required regime fields
    for field in ('background_color', 'above_200ma', 'VIX_close'):
        if field not in regime_data or regime_data[field] is None:
            warnings.append(f"Regime data missing field: {field}")

    # Check VIX data file exists
    vix_path = data_dir / 'VIX.csv'
    if not vix_path.exists():
        warnings.append("VIX.csv not found in data directory")

    return warnings, regime_data_age_hours, stale_regime_data


def run_allocation_analysis() -> Dict:
    """
    Run the complete allocation analysis process.
    
    Returns:
        dict: Complete allocation results including regime info, allocations, and sleeve analyses
    """
    logging.info("Starting allocation analysis")
    
    # Load SPX regime data
    regime_data = load_spx_regime_data()
    
    # Get allocation summary (regime info + allocation percentages)
    allocation_summary = get_allocation_summary(regime_data)
    allocation_percentages = allocation_summary['allocation']
    regime_key = allocation_summary.get('regime_key', 'moderate_risk')
    
    logging.info(f"Determined allocation percentages: {allocation_percentages}")
    
    # Get data directory
    data_dir = get_data_dir()

    # Validate input data quality
    warnings, regime_data_age_hours, stale_regime_data = validate_data_quality(regime_data, data_dir)
    for w in warnings:
        logging.warning(f"Data quality: {w}")
    if stale_regime_data:
        logging.warning("Regime data is stale — output will be flagged")

    # Initialize results structure
    results = {
        'datetime': datetime.now().isoformat(),
        'regime': allocation_summary['regime'],
        'allocation_percentages': allocation_percentages,
        'warnings': warnings,
        'sleeve_analyses': {}
    }
    
    # Run analysis for each enabled sleeve
    if SLEEVE_CONFIG['equity']['enabled']:
        equity_allocation = allocation_percentages.get('equity', 0.0)
        equity_results = equity.analyze_equity_sleeve(
            data_dir=data_dir,
            allocation_percentage=equity_allocation,
            enabled_sub_modules=SLEEVE_CONFIG['equity'].get('sub_modules')
        )
        results['sleeve_analyses']['equity'] = equity_results
    
    if SLEEVE_CONFIG['commodities']['enabled']:
        commodities_allocation = allocation_percentages.get('commodities', 0.0)
        commodities_results = commodities.analyze_commodities(
            data_dir=data_dir,
            allocation_percentage=commodities_allocation
        )
        results['sleeve_analyses']['commodities'] = commodities_results
    
    if SLEEVE_CONFIG['crypto']['enabled']:
        crypto_allocation = allocation_percentages.get('crypto', 0.0)
        crypto_results = crypto.analyze_crypto(
            data_dir=data_dir,
            allocation_percentage=crypto_allocation
        )
        results['sleeve_analyses']['crypto'] = crypto_results
    
    if SLEEVE_CONFIG['managed_futures']['enabled']:
        managed_futures_allocation = allocation_percentages.get('managed_futures', 0.0)
        managed_futures_results = managed_futures.analyze_managed_futures(
            data_dir=data_dir,
            allocation_percentage=managed_futures_allocation
        )
        results['sleeve_analyses']['managed_futures'] = managed_futures_results
    
    if SLEEVE_CONFIG['vol_hedges']['enabled']:
        vol_hedges_allocation = allocation_percentages.get('vol_hedges', 0.0)
        vol_hedges_results = vol_hedges.analyze_vol_hedges(
            data_dir=data_dir,
            allocation_percentage=vol_hedges_allocation,
            regime_key=regime_key
        )
        results['sleeve_analyses']['vol_hedges'] = vol_hedges_results
    
    if SLEEVE_CONFIG['fixed_income']['enabled']:
        fixed_income_allocation = allocation_percentages.get('fixed_income', 0.0)
        fixed_income_results = fixed_income.analyze_fixed_income(
            data_dir=data_dir,
            allocation_percentage=fixed_income_allocation,
            regime_key=regime_key
        )
        results['sleeve_analyses']['fixed_income'] = fixed_income_results
    
    # Check sleeve output quality
    for sleeve_name, sleeve_result in results['sleeve_analyses'].items():
        selected = sleeve_result.get('selected_etfs', [])
        if isinstance(selected, list) and len(selected) == 0:
            alloc = sleeve_result.get('allocation_percentage', 0)
            if alloc > 0:
                warnings.append(f"{sleeve_name}: 0 ETFs selected despite {alloc:.0%} allocation")

    # Portfolio-level analytics (correlation, stress correlation, drawdowns)
    try:
        analytics = compute_portfolio_analytics(
            results['sleeve_analyses'],
            allocation_percentages,
            data_dir
        )
        if analytics:
            results['portfolio_analytics'] = analytics
    except Exception as e:
        logging.warning(f"Portfolio analytics failed: {e}")

    # LLM regime analysis (runs after all sleeves so it can see full picture)
    if not SKIP_LLM:
        try:
            llm_result = run_llm_regime_analysis(data_dir, regime_data, results)
            results['llm_analysis'] = llm_result
        except Exception as e:
            logging.warning(f"LLM regime analysis failed: {e}")
            results['llm_analysis'] = {'skipped': True, 'reason': str(e)}
    else:
        results['llm_analysis'] = {'skipped': True, 'reason': '--no-llm flag'}

    # Staleness flag for dashboard rendering
    if stale_regime_data:
        results['_stale_regime'] = {
            'stale': True,
            'age_hours': regime_data_age_hours
        }

    logging.info("Allocation analysis completed successfully")

    return results


def save_allocation_results(results: Dict) -> None:
    """
    Save allocation results to output files.

    Args:
        results: Allocation results dictionary
    """
    docs_dir = get_docs_dir()

    # Run rebalance check (reads previous entry from JSONL before we append today's)
    summary, changes = run_rebalance_check(results, docs_dir)
    results['daily_summary'] = summary
    results['changes'] = changes

    if summary:
        logging.info(f"Daily summary:\n{summary}")

    if OUTPUT_CONFIG['save_json']:
        filename = OUTPUT_CONFIG['json_filename']
        save_results(results, filename)

    # Append to rolling history log (JSONL) — must happen AFTER rebalance check
    archive_results(results)


def main():
    """
    Main entry point for the allocation engine.
    """
    try:
        # Run allocation analysis
        results = run_allocation_analysis()
        
        # Save results
        save_allocation_results(results)
        
        logging.info("Allocation engine completed successfully")
        
    except Exception as e:
        logging.error(f"Allocation engine failed: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run allocation engine")
    parser.add_argument('--force-refresh', action='store_true',
                        help="Bypass yfinance CSV cache and re-fetch all ETF data")
    parser.add_argument('--no-llm', action='store_true',
                        help="Skip LLM regime analysis")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    if args.force_refresh:
        from allocation.utils import FORCE_REFRESH
        import allocation.utils
        allocation.utils.FORCE_REFRESH = True
        logging.info("Force refresh enabled — bypassing yfinance cache")

    if args.no_llm:
        SKIP_LLM = True
        logging.info("LLM regime analysis disabled via --no-llm")

    main()
