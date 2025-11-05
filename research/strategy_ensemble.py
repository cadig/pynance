import pandas as pd
import numpy as np
from pathlib import Path
import logging
import json
from datetime import datetime

def load_spx_regime_data() -> dict:
    """
    Load SPX regime data from JSON file.
    
    Returns:
        dict: SPX regime data
    """
    docs_dir = Path(__file__).parent.parent / 'docs'
    regime_file = docs_dir / 'spx-regime-results.json'
    
    try:
        with open(regime_file, 'r') as f:
            regime_data = json.load(f)
        logging.info(f"Loaded SPX regime data from: {regime_file}")
        return regime_data
    except Exception as e:
        logging.error(f"Failed to load SPX regime data: {e}")
        raise

def load_tqqq_data() -> pd.DataFrame:
    """
    Load TQQQ data from CSV file.
    
    Returns:
        pd.DataFrame: TQQQ data with datetime index
    """
    data_dir = Path(__file__).parent.parent / 'data'
    tqqq_file = data_dir / 'TQQQ.csv'
    
    try:
        df = pd.read_csv(tqqq_file, index_col=0, parse_dates=True)
        logging.info(f"Loaded TQQQ data from: {tqqq_file}")
        return df
    except Exception as e:
        logging.error(f"Failed to load TQQQ data: {e}")
        raise

def load_gold_data() -> pd.DataFrame:
    """
    Load GOLD data from CSV file.
    
    Returns:
        pd.DataFrame: GOLD data with datetime index
    """
    data_dir = Path(__file__).parent.parent / 'data'
    gold_file = data_dir / 'GOLD.csv'
    
    try:
        df = pd.read_csv(gold_file, index_col=0, parse_dates=True)
        logging.info(f"Loaded GOLD data from: {gold_file}")
        return df
    except Exception as e:
        logging.error(f"Failed to load GOLD data: {e}")
        raise

def load_bitcoin_data() -> pd.DataFrame:
    """
    Load BTCUSD data from CSV file.
    
    Returns:
        pd.DataFrame: BTCUSD data with datetime index
    """
    data_dir = Path(__file__).parent.parent / 'data'
    btc_file = data_dir / 'BTCUSD.csv'
    
    try:
        df = pd.read_csv(btc_file, index_col=0, parse_dates=True)
        logging.info(f"Loaded BTCUSD data from: {btc_file}")
        return df
    except Exception as e:
        logging.error(f"Failed to load BTCUSD data: {e}")
        raise

def calculate_macd_signal(df: pd.DataFrame) -> bool:
    """
    Calculate MACD signal.
    Returns True if MACD line is above signal line (bullish), False otherwise.
    
    Args:
        df: DataFrame with 'close' column
        
    Returns:
        bool: True if MACD > Signal, False otherwise
    """
    # Calculate MACD (12-day EMA - 26-day EMA)
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    
    # Calculate Signal line (9-day EMA of MACD)
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    
    # Get latest values
    latest_macd = macd_line.iloc[-1]
    latest_signal = signal_line.iloc[-1]
    
    # Signal is bullish when MACD > Signal
    return latest_macd > latest_signal

def calculate_tqqq_strategies(tqqq_df: pd.DataFrame) -> dict:
    """
    Calculate TQQQ strategy signals.
    
    Args:
        tqqq_df: DataFrame with TQQQ data
        
    Returns:
        dict: Strategy signals and allocation
    """
    # Get latest close price
    latest_close = tqqq_df['close'].iloc[-1]
    
    # Calculate 10-day SMA
    sma10 = tqqq_df['close'].rolling(window=10).mean().iloc[-1]
    priceVs10sma = 1 if latest_close > sma10 else 0
    
    # Calculate 20-day SMA
    sma20 = tqqq_df['close'].rolling(window=20).mean().iloc[-1]
    priceVs20sma = 1 if latest_close > sma20 else 0
    
    # Calculate MACD signal
    macdSignal = 1 if calculate_macd_signal(tqqq_df) else 0
    
    # Calculate weighted allocation
    allocation = (priceVs10sma * 0.5) + (priceVs20sma * 0.3) + (macdSignal * 0.2)
    
    return {
        'priceVs10sma': priceVs10sma,
        'priceVs20sma': priceVs20sma,
        'macdSignal': macdSignal,
        'allocation': round(allocation, 4)
    }

def calculate_gold_strategies(gold_df: pd.DataFrame) -> dict:
    """
    Calculate Gold strategy signals.
    All strategies have equal weighting (0.333 each).
    
    Args:
        gold_df: DataFrame with GOLD data
        
    Returns:
        dict: Strategy signals and allocation
    """
    # Get latest close price
    latest_close = gold_df['close'].iloc[-1]
    
    # Calculate SMAs
    sma10 = gold_df['close'].rolling(window=10).mean().iloc[-1]
    sma50 = gold_df['close'].rolling(window=50).mean().iloc[-1]
    sma200 = gold_df['close'].rolling(window=200).mean().iloc[-1]
    
    # Strategy 1: priceVs10smaWith200sma
    # Check if close > 10 SMA AND average (close) > 200 SMA
    above_10sma = latest_close > sma10
    above_200sma = latest_close > sma200
    priceVs10smaWith200sma = 1 if (above_10sma and above_200sma) else 0
    
    # Strategy 2: priceVs50smaWith200sma
    # Check if close > 50 SMA AND average (close) > 200 SMA
    above_50sma = latest_close > sma50
    priceVs50smaWith200sma = 1 if (above_50sma and above_200sma) else 0
    
    # Strategy 3: macdSignal (no 200 SMA filter)
    macdSignal = 1 if calculate_macd_signal(gold_df) else 0
    
    # Calculate weighted allocation (equal weighting: 0.333 each)
    allocation = (priceVs10smaWith200sma * (1/3)) + (priceVs50smaWith200sma * (1/3)) + (macdSignal * (1/3))
    
    return {
        'priceVs10smaWith200sma': priceVs10smaWith200sma,
        'priceVs50smaWith200sma': priceVs50smaWith200sma,
        'macdSignal': macdSignal,
        'allocation': round(allocation, 4)
    }

def calculate_bitcoin_strategies(btc_df: pd.DataFrame) -> dict:
    """
    Calculate Bitcoin strategy signals.
    Both strategies have equal weighting (0.5 each).
    
    Args:
        btc_df: DataFrame with BTCUSD data
        
    Returns:
        dict: Strategy signals and allocation
    """
    # Get latest close price
    latest_close = btc_df['close'].iloc[-1]
    
    # Calculate SMAs
    sma50 = btc_df['close'].rolling(window=50).mean().iloc[-1]
    sma200 = btc_df['close'].rolling(window=200).mean().iloc[-1]
    
    # Strategy 1: priceVs50smaWith200sma
    # Check if close > 50 SMA AND average (close) > 200 SMA
    above_50sma = latest_close > sma50
    above_200sma = latest_close > sma200
    priceVs50smaWith200sma = 1 if (above_50sma and above_200sma) else 0
    
    # Strategy 2: macdWith200sma
    # MACD signal AND average (close) > 200 SMA
    macd_signal = calculate_macd_signal(btc_df)
    macdWith200sma = 1 if (macd_signal and above_200sma) else 0
    
    # Calculate weighted allocation (equal weighting: 0.5 each)
    allocation = (priceVs50smaWith200sma * 0.5) + (macdWith200sma * 0.5)
    
    return {
        'priceVs50smaWith200sma': priceVs50smaWith200sma,
        'macdWith200sma': macdWith200sma,
        'allocation': round(allocation, 4)
    }

def check_regime_filters(regime_data: dict) -> bool:
    """
    Check if regime filters allow trading.
    Returns False if any of these conditions are met:
    - background_color is "red"
    - VIX_close > 30
    - above_200ma is False
    
    Args:
        regime_data: SPX regime data dictionary
        
    Returns:
        bool: True if trading is allowed, False otherwise
    """
    # Check background color
    if regime_data.get('background_color') == 'red':
        logging.info("Regime filter: background_color is red")
        return False
    
    # Check VIX
    if 'VIX_close' in regime_data:
        vix_value = regime_data['VIX_close']
        if vix_value > 30:
            logging.info(f"Regime filter: VIX ({vix_value}) > 30")
            return False
    
    # Check above 200 MA
    if not regime_data.get('above_200ma', False):
        logging.info("Regime filter: above_200ma is False")
        return False
    
    return True

def generate_strategy_ensemble() -> dict:
    """
    Generate strategy ensemble results.
    
    Returns:
        dict: Strategy ensemble results
    """
    # Load SPX regime data
    regime_data = load_spx_regime_data()
    
    # Check regime filters
    trading_allowed = check_regime_filters(regime_data)
    
    # Initialize results
    results = {
        "datetime": datetime.now().isoformat(),
        "tqqq-long-ensemble": {}
    }
    
    if not trading_allowed:
        # All strategies should be 0 if filters fail
        results["tqqq-long-ensemble"] = {
            "priceVs10sma": 0,
            "priceVs20sma": 0,
            "macdSignal": 0,
            "allocation": 0.0
        }
        logging.info("Regime filters failed - all TQQQ strategies set to 0")
    else:
        # Load TQQQ data and calculate strategies
        tqqq_df = load_tqqq_data()
        tqqq_results = calculate_tqqq_strategies(tqqq_df)
        results["tqqq-long-ensemble"] = tqqq_results
        logging.info(f"TQQQ strategies calculated: {tqqq_results}")
    
    # Calculate Gold strategies (independent of regime filters)
    try:
        gold_df = load_gold_data()
        gold_results = calculate_gold_strategies(gold_df)
        results["gold-long-ensemble"] = gold_results
        logging.info(f"Gold strategies calculated: {gold_results}")
    except Exception as e:
        logging.error(f"Failed to calculate Gold strategies: {e}")
        # Set default values if calculation fails
        results["gold-long-ensemble"] = {
            "priceVs10smaWith200sma": 0,
            "priceVs50smaWith200sma": 0,
            "macdSignal": 0,
            "allocation": 0.0
        }
    
    # Calculate Bitcoin strategies (independent of regime filters)
    try:
        btc_df = load_bitcoin_data()
        btc_results = calculate_bitcoin_strategies(btc_df)
        results["bitcoin-long-ensemble"] = btc_results
        logging.info(f"Bitcoin strategies calculated: {btc_results}")
    except Exception as e:
        logging.error(f"Failed to calculate Bitcoin strategies: {e}")
        # Set default values if calculation fails
        results["bitcoin-long-ensemble"] = {
            "priceVs50smaWith200sma": 0,
            "macdWith200sma": 0,
            "allocation": 0.0
        }
    
    return results

def save_strategy_ensemble(results: dict) -> None:
    """
    Save strategy ensemble results to JSON file.
    
    Args:
        results: Strategy ensemble results dictionary
    """
    docs_dir = Path(__file__).parent.parent / 'docs'
    docs_dir.mkdir(exist_ok=True)
    
    output_file = docs_dir / 'strategy_ensemble.json'
    
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logging.info(f"Strategy ensemble results saved to: {output_file}")
    except Exception as e:
        logging.error(f"Failed to save strategy ensemble results: {e}")
        raise

def main():
    """
    Main function to generate and save strategy ensemble results.
    """
    try:
        # Generate strategy ensemble
        results = generate_strategy_ensemble()
        
        # Save results
        save_strategy_ensemble(results)
        
        logging.info("Strategy ensemble generation completed successfully")
        
    except Exception as e:
        logging.error(f"Failed to generate strategy ensemble: {e}")
        raise

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    main()

