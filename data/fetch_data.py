import pandas as pd
from pathlib import Path
import logging
from datetime import datetime, date
import json
import argparse
from typing import Dict, List

import sys
sys.path.append('..')
from tvdatafeed_client import get_tvdatafeed_client, Interval

def load_config() -> List[Dict]:
    """
    Loads the symbols to fetch configuration from JSON file.

    Returns:
        List[Dict]: List of symbol configurations
    """
    config_path = Path(__file__).parent / 'symbols_to_fetch.json'
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config['symbols']
    except Exception as e:
        logging.error(f"Failed to load configuration: {str(e)}")
        raise

def get_data_dir() -> Path:
    """
    Gets the path to the data directory.

    Returns:
        Path: Path to the data directory
    """
    return Path(__file__).parent

def get_latest_date_from_csv(filepath: Path) -> datetime:
    """
    Gets the latest date from an existing CSV file.

    Args:
        filepath (Path): Path to the CSV file

    Returns:
        datetime: Latest date in the CSV file
    """
    try:
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        earliest_date = df.index.min()
        latest_date = df.index.max()
        logging.info(f"CSV data range: {earliest_date.date()} to {latest_date.date()}")
        return latest_date
    except Exception as e:
        logging.error(f"Failed to read CSV file {filepath}: {str(e)}")
        raise

def download_daily_data(symbol: str, exchange: str, n_bars: int = 1000) -> pd.DataFrame:
    """
    Downloads daily data for a given symbol.

    Args:
        symbol (str): The symbol to download data for
        exchange (str): The exchange to download from
        n_bars (int): Number of bars to download

    Returns:
        pd.DataFrame: DataFrame containing the market breadth data
    """
    try:
        client = get_tvdatafeed_client()
        data = client.get_hist(
            symbol=symbol,
            exchange=exchange,
            interval=Interval.in_daily,
            n_bars=n_bars
        )
        return data
    except Exception as e:
        logging.error(f"Failed to download data for {symbol} from {exchange}: {str(e)}")
        raise

def save_daily_data(filename: str, data: pd.DataFrame) -> None:
    """
    Saves daily data to a CSV file.

    Args:
        filename (str): The filename to save the data to
        data (pd.DataFrame): The data to save
    """
    data_dir = get_data_dir()
    filepath = data_dir / filename

    try:
        data.to_csv(filepath, index=True)
        file_size = filepath.stat().st_size
        file_size_mb = file_size / (1024 * 1024)  # Convert to MB
        logging.info(f"Successfully saved data to {filepath} (Size: {file_size_mb:.2f} MB)")
    except Exception as e:
        logging.error(f"Failed to save data to {filename}: {str(e)}")
        raise

def update_daily_data(symbol_config: Dict) -> None:
    """
    Updates daily data for a symbol configuration.
    Falls back to cached data if the API call fails.
    Right-sizes the fetch based on days since last data point.

    Args:
        symbol_config (Dict): Dictionary containing symbol configuration
    """
    symbol = symbol_config['symbol']
    exchange = symbol_config['exchange']
    filename = symbol_config['filename']
    description = symbol_config['description']

    data_dir = get_data_dir()
    filepath = data_dir / filename

    if filepath.exists():
        logging.info(f"Found existing data file for {symbol} ({description})")
        latest_date = get_latest_date_from_csv(filepath)
        today = pd.Timestamp.now().normalize()

        if latest_date.date() >= today.date():
            logging.info(f"{symbol} data is already up to date (latest: {latest_date.date()})")
            return

        days_diff = (today - latest_date).days
        # Right-size the fetch: only request what we need + padding
        n_bars = min(days_diff + 10, 1000)
        logging.info(f"Fetching ~{n_bars} bars of new data for {symbol} ({days_diff} days behind)")

        try:
            new_data = download_daily_data(symbol, exchange, n_bars=n_bars)

            # Read existing data
            existing_data = pd.read_csv(filepath, index_col=0, parse_dates=True)

            # Combine and remove duplicates
            combined_data = pd.concat([existing_data, new_data])
            combined_data = combined_data[~combined_data.index.duplicated(keep='last')]
            combined_data = combined_data.sort_index()

            save_daily_data(filename, combined_data)
            logging.info(f"Successfully updated {symbol} data from {latest_date.date()} to {today.date()}")
        except Exception as e:
            logging.warning(f"API fetch failed for {symbol}: {e}. Using cached data (latest: {latest_date.date()})")
            return

    else:
        logging.info(f"No existing data file found for {symbol} ({description}), downloading full history")
        data = download_daily_data(symbol, exchange, n_bars=30_000)
        earliest_date = data.index.min()
        latest_date = data.index.max()
        logging.info(f"Downloaded data range: {earliest_date.date()} to {latest_date.date()}")
        save_daily_data(filename, data)
        logging.info(f"Successfully created new data file for {symbol}")

def main():
    """
    Main function to download and save market breadth data for all configured symbols.
    """
    parser = argparse.ArgumentParser(description='Fetch market data from TradingView')
    parser.add_argument('--skip-fetch', action='store_true',
                        help='Skip TradingView API entirely, use only cached CSVs')
    args = parser.parse_args()

    if args.skip_fetch:
        logging.info("--skip-fetch: Skipping TradingView API. Using cached CSVs only.")
        return

    try:
        symbol_configs = load_config()
        for config in symbol_configs:
            try:
                if not config.get('shouldFetch', False):
                    logging.info(f"Skipping {config['symbol']} as shouldFetch is False")
                    continue

                update_daily_data(config)
            except Exception as e:
                logging.error(f"Failed to process {config['symbol']}: {str(e)}")
                continue
    except Exception as e:
        logging.error(f"Failed to load configuration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    main()
