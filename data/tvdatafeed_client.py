from tvDatafeed import TvDatafeed, Interval
import logging
from typing import Optional
import configparser
import os
from pathlib import Path
import sys

def get_config_path() -> Path:
    """
    Gets the path to the tradingview config file.
    
    Returns:
        Path: Path to the config file
    """
    # Get the parent directory of the current file
    current_dir = Path(__file__).parent
    # Get the project root (parent of scripts directory)
    project_root = current_dir.parent.parent
    # Create config directory path
    config_dir = project_root / 'config'
    # Return path to config file
    return config_dir / 'tradingview-config.ini'

def read_tradingview_credentials() -> tuple[Optional[str], Optional[str]]:
    """
    Reads TradingView credentials from environment variables or config file.
    Environment variables take precedence for CI/CD environments.
    
    Returns:
        tuple[Optional[str], Optional[str]]: Username and password from environment or config file
    """
    # Check for environment variables first (for CI/CD)
    env_username = os.getenv('TRADINGVIEW_USERNAME')
    env_password = os.getenv('TRADINGVIEW_PASSWORD')
    
    if env_username and env_password:
        logging.info("Using credentials from environment variables")
        return env_username, env_password
    
    # Fall back to config file for local development
    config_path = get_config_path()
    
    # Create config file with template if it doesn't exist
    if not config_path.exists():
        config = configparser.ConfigParser()
        config['login'] = {
            'username': '',
            'password': ''
        }
        with open(config_path, 'w') as f:
            config.write(f)
        logging.info(f"Created config file template at {config_path}")
        return None, None
    
    # Read existing config
    config = configparser.ConfigParser()
    config.read(config_path)
    
    try:
        username = config.get('login', 'username')
        password = config.get('login', 'password')
        return username if username else None, password if password else None
    except (configparser.NoSectionError, configparser.NoOptionError):
        logging.warning("Login section or credentials not found in config file")
        return None, None

def setup_tvdatafeed_client(username: Optional[str] = None, password: Optional[str] = None) -> TvDatafeed:
    """
    Sets up and returns a TvDatafeed client instance.
    If credentials are not provided, attempts to read them from config file.
    
    Args:
        username (str, optional): TradingView username. If not provided, will try to read from config.
        password (str, optional): TradingView password. If not provided, will try to read from config.
        
    Returns:
        TvDatafeed: Initialized TvDatafeed client instance
        
    Raises:
        SystemExit: If login fails
    """
    # If credentials not provided, try to read from config
    if username is None or password is None:
        config_username, config_password = read_tradingview_credentials()
        username = username or config_username
        password = password or config_password
    
    try:
        # Initialize the client
        tv = TvDatafeed(username=username, password=password)
        
        
        # Test the connection by getting some basic data
        # This will raise an exception if the login failed
        tv.get_hist(
            symbol='AAPL',
            exchange='NASDAQ',
            interval=Interval.in_daily,
            n_bars=1
        )
        
        logging.info("Successfully connected to TradingView")
        return tv
        
    except Exception as e:
        # Temporary debugging - remove in production
        logging.error("Failed to setup TvDatafeed client")
        sys.exit(1)

def get_tvdatafeed_client(username: Optional[str] = None, password: Optional[str] = None) -> TvDatafeed:
    """
    Gets or creates a TvDatafeed client instance.
    This is a wrapper around setup_tvdatafeed_client that can be used to get a singleton instance.
    
    Args:
        username (str, optional): TradingView username. If not provided, will try to read from config.
        password (str, optional): TradingView password. If not provided, will try to read from config.
        
    Returns:
        TvDatafeed: Initialized TvDatafeed client instance
    """
    if not hasattr(get_tvdatafeed_client, '_instance'):
        get_tvdatafeed_client._instance = setup_tvdatafeed_client(username, password)
    return get_tvdatafeed_client._instance

