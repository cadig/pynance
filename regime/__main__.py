"""Entry point for regime detection: python regime/__main__.py"""

import logging

from .config import REGIME_CONFIG
from .engine import RegimeEngine
from .plotting import plot_regime_signals


def main():
    engine = RegimeEngine()

    # Determine which data files we need based on active modules
    required_files = ['SPX.csv']

    if REGIME_CONFIG['vix_bollinger_exit']['enabled']:
        required_files.append('VIX.csv')

    if REGIME_CONFIG['nyse_cumulative_ad_zscore']['enabled']:
        required_files.append('ADRN.csv')

    if REGIME_CONFIG['combined_mm_signals']['enabled']:
        for name, config in REGIME_CONFIG['combined_mm_signals']['indicators'].items():
            if config['enabled']:
                required_files.append(f'{name}-{config["period"]}-day.csv')

    logging.info("Loading required data files: %s", required_files)
    engine.load_data(required_files)

    # Plot combined signals
    plot_regime_signals(engine)

    # Save JSON results
    engine.save_json_results()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    main()
