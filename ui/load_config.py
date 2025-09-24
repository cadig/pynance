#!/usr/bin/env python3
"""
Simple script to load Alpaca credentials from your existing config file
and generate a JavaScript configuration file for the frontend.
"""

import sys
import os
from configparser import ConfigParser

def load_alpaca_config():
    """Load Alpaca configuration from your existing config file"""
    try:
        # Navigate to the config directory (same as alpacaTrend.py)
        config_path = '../../config/alpaca-config.ini'
        config = ConfigParser()
        config.read(config_path)
        
        # Get paper trading credentials (same as alpacaTrend.py)
        api_key = config.get('paper', 'API_KEY')
        api_secret = config.get('paper', 'API_SECRET')
        
        return api_key, api_secret
        
    except Exception as e:
        print(f"Error loading config: {e}")
        print("Make sure your config file exists at: ../../config/alpaca-config.ini")
        return None, None

def generate_js_config():
    """Generate JavaScript configuration file with credentials"""
    api_key, api_secret = load_alpaca_config()
    
    if not api_key or not api_secret:
        print("Failed to load credentials")
        return False
    
    js_config = f"""
// Auto-generated configuration file
// DO NOT commit this file to version control

const ALPACA_CONFIG = {{
    apiKey: '{api_key}',
    secretKey: '{api_secret}',
    baseUrl: 'https://paper-api.alpaca.markets' // Paper trading
}};
"""
    
    with open('config.js', 'w') as f:
        f.write(js_config)
    
    print("Generated config.js with your Alpaca credentials")
    print("You can now open index.html in your browser")
    return True

if __name__ == "__main__":
    generate_js_config()
