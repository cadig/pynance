"""
Shared utilities for the allocation system.

Provides common functions for data loading, file I/O, and data processing.
"""

import pandas as pd
import json
from pathlib import Path
import logging
from typing import Dict, List, Optional


def get_data_dir() -> Path:
    """
    Get the path to the data directory.
    
    Returns:
        Path: Path to the data directory
    """
    return Path(__file__).parent.parent.parent / 'data'


def get_docs_dir() -> Path:
    """
    Get the path to the docs directory.
    
    Returns:
        Path: Path to the docs directory
    """
    return Path(__file__).parent.parent.parent / 'docs'


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
            json.dump(results, f, indent=2)
        logging.info(f"Results saved to: {output_path}")
    except Exception as e:
        logging.error(f"Failed to save results to {output_path}: {e}")
        raise
