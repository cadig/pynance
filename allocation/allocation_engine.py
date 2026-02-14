"""
Main allocation engine that orchestrates the asset allocation process.

This is the entry point for the allocation strategy system.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

# Handle both direct execution and module import
if __name__ == "__main__":
    # Add parent directory to path for direct execution
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from allocation.regime_allocator import get_allocation_summary
    from allocation.config import SLEEVE_CONFIG, OUTPUT_CONFIG
    from allocation.utils import get_data_dir, get_docs_dir, save_results, archive_results, load_spx_regime_data
    from allocation.sleeves import equity
    from allocation.sleeves import commodities
    from allocation.sleeves import crypto
    from allocation.sleeves import managed_futures
    from allocation.sleeves import alternatives
    from allocation.sleeves import fixed_income
else:
    # Relative imports for module execution
    from .regime_allocator import get_allocation_summary
    from .config import SLEEVE_CONFIG, OUTPUT_CONFIG
    from .utils import get_data_dir, get_docs_dir, save_results, archive_results, load_spx_regime_data
    from .sleeves import equity
    from .sleeves import commodities
    from .sleeves import crypto
    from .sleeves import managed_futures
    from .sleeves import alternatives
    from .sleeves import fixed_income


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
    
    # Initialize results structure
    results = {
        'datetime': datetime.now().isoformat(),
        'regime': allocation_summary['regime'],
        'allocation_percentages': allocation_percentages,
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
    
    if SLEEVE_CONFIG['alternatives']['enabled']:
        alternatives_allocation = allocation_percentages.get('alternatives', 0.0)
        alternatives_results = alternatives.analyze_alternatives(
            data_dir=data_dir,
            allocation_percentage=alternatives_allocation,
            regime_key=regime_key
        )
        results['sleeve_analyses']['alternatives'] = alternatives_results
    
    if SLEEVE_CONFIG['fixed_income']['enabled']:
        fixed_income_allocation = allocation_percentages.get('fixed_income', 0.0)
        fixed_income_results = fixed_income.analyze_fixed_income(
            data_dir=data_dir,
            allocation_percentage=fixed_income_allocation,
            regime_key=regime_key
        )
        results['sleeve_analyses']['fixed_income'] = fixed_income_results
    
    logging.info("Allocation analysis completed successfully")
    
    return results


def save_allocation_results(results: Dict) -> None:
    """
    Save allocation results to output files.

    Args:
        results: Allocation results dictionary
    """
    if OUTPUT_CONFIG['save_json']:
        filename = OUTPUT_CONFIG['json_filename']
        save_results(results, filename)

    # Append to rolling history log (JSONL)
    archive_results(results)
    
    # TODO: Implement PNG and HTML output if enabled
    if OUTPUT_CONFIG.get('save_png', False):
        logging.info("PNG output not yet implemented")
    
    if OUTPUT_CONFIG.get('save_html', False):
        logging.info("HTML output not yet implemented")


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

    main()
