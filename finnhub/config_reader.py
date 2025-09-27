"""
Configuration reader for Finnhub API credentials
"""
import os
from configparser import ConfigParser


def get_finnhub_credentials():
    """
    Read Finnhub API credentials from finnhub-config.ini file
    
    Returns:
        str: API key for Finnhub
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        KeyError: If API_KEY is not found in [finnhub] section
    """
    # Get the project root directory (parent of current directory)
    config_path = '../../config/finnhub-config.ini'
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    config = ConfigParser()
    config.read(config_path)
    
    if 'finnhub' not in config:
        raise KeyError("Section [finnhub] not found in config file")
    
    if 'API_KEY' not in config['finnhub']:
        raise KeyError("API_KEY not found in [finnhub] section")
    
    return config['finnhub']['API_KEY']
