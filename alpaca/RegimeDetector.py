
"""
Regime Detection Module for SPX Market Regime Analysis

This module fetches and validates SPX regime data from the pynance GitHub Pages
and provides market regime information for trading decisions.
"""

import requests
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

REGIME_URL = "https://cadig.github.io/pynance/spx-regime-results.json"

class RegimeDetector:
    """Handles fetching and validation of SPX regime data"""
    
    def __init__(self, url: str = REGIME_URL):
        self.url = url
        self.regime_data: Optional[Dict[str, Any]] = None
    
    def fetch_regime_data(self) -> Dict[str, Any]:
        """
        Fetch regime data from the specified URL
        
        Returns:
            Dict containing regime data
            
        Raises:
            requests.RequestException: If unable to fetch data
            json.JSONDecodeError: If response is not valid JSON
        """
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            self.regime_data = response.json()
            return self.regime_data
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch regime data: {e}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON response: {e}")
    
    def validate_datetime(self, regime_data: Dict[str, Any]) -> bool:
        """
        Validate that the regime data datetime is from today or yesterday
        
        Args:
            regime_data: Dictionary containing regime data with 'datetime' key
            
        Returns:
            True if datetime is valid (today or yesterday), False otherwise
            
        Raises:
            ValueError: If datetime format is invalid or too old
        """
        if 'datetime' not in regime_data:
            raise ValueError("Regime data missing 'datetime' field")
        
        try:
            # Parse the datetime string - handle both with and without timezone info
            datetime_str = regime_data['datetime']
            
            # If the string ends with 'Z', replace with '+00:00' for timezone awareness
            if datetime_str.endswith('Z'):
                datetime_str = datetime_str.replace('Z', '+00:00')
            
            # Parse the datetime string
            regime_datetime = datetime.fromisoformat(datetime_str)
            
            # Ensure regime_datetime is timezone-aware
            if regime_datetime.tzinfo is None:
                # If no timezone info, assume UTC
                regime_datetime = regime_datetime.replace(tzinfo=timezone.utc)
            
            # Get current time in UTC
            now = datetime.now(timezone.utc)
            
            # Calculate time difference
            time_diff = now - regime_datetime
            
            # Check if datetime is from today or yesterday (within 48 hours)
            if time_diff > timedelta(hours=96):
                raise ValueError(f"Regime data is too old: {regime_datetime} (current time: {now})")
            
            return True
            
        except ValueError as e:
            if "too old" in str(e):
                raise e
            else:
                raise ValueError(f"Invalid datetime format in regime data: {e}")
    
    def get_regime_info(self) -> Dict[str, Any]:
        """
        Fetch and validate regime data, returning the complete regime information
        
        Returns:
            Dict containing validated regime data
            
        Raises:
            requests.RequestException: If unable to fetch data
            json.JSONDecodeError: If response is not valid JSON
            ValueError: If datetime validation fails
        """
        regime_data = self.fetch_regime_data()
        self.validate_datetime(regime_data)
        return regime_data
    
    def get_background_color(self) -> str:
        """
        Get the background color from the regime data
        
        Returns:
            Background color string ('red', 'orange', 'yellow', or 'green')
            
        Raises:
            ValueError: If regime data is not available or background_color is invalid
        """
        if not self.regime_data:
            raise ValueError("No regime data available. Call get_regime_info() first.")
        
        if 'background_color' not in self.regime_data:
            raise ValueError("Regime data missing 'background_color' field")
        
        color = self.regime_data['background_color']
        valid_colors = ['red', 'orange', 'yellow', 'green']
        
        if color not in valid_colors:
            raise ValueError(f"Invalid background color: {color}. Must be one of {valid_colors}")
        
        return color
    
    def is_above_200ma(self) -> bool:
        """
        Check if SPX is above 200-day moving average
        
        Returns:
            True if above 200MA, False otherwise
        """
        if not self.regime_data:
            raise ValueError("No regime data available. Call get_regime_info() first.")
        
        return self.regime_data.get('above_200ma', False)
    
    def get_combined_mm_signals(self) -> int:
        """
        Get the combined money flow signals count
        
        Returns:
            Number of combined money flow signals
        """
        if not self.regime_data:
            raise ValueError("No regime data available. Call get_regime_info() first.")
        
        return self.regime_data.get('combined_mm_signals', 0)
    
    def get_vix_close(self) -> Optional[float]:
        """
        Get the VIX close price from the regime data
        
        Returns:
            VIX close price as float, or None if not available
        """
        if not self.regime_data:
            raise ValueError("No regime data available. Call get_regime_info() first.")
        
        return self.regime_data.get('VIX_close')

def get_current_regime() -> Dict[str, Any]:
    """
    Convenience function to get current regime data
    
    Returns:
        Dict containing current regime data
        
    Raises:
        requests.RequestException: If unable to fetch data
        json.JSONDecodeError: If response is not valid JSON
        ValueError: If datetime validation fails
    """
    detector = RegimeDetector()
    return detector.get_regime_info()

if __name__ == "__main__":
    # Example usage
    try:
        detector = RegimeDetector()
        regime_data = detector.get_regime_info()
        
        print("=== SPX Regime Data ===")
        print(f"Datetime: {regime_data['datetime']}")
        print(f"Background Color: {regime_data['background_color']}")
        print(f"Above 200MA: {regime_data['above_200ma']}")
        print(f"NYSE Cumulative AD Z-Score: {regime_data['nyse_cumulative_ad_zscore']}")
        print(f"Combined MM Signals: {regime_data['combined_mm_signals']}")
        
        # Test individual methods
        print(f"\nBackground Color: {detector.get_background_color()}")
        print(f"Above 200MA: {detector.is_above_200ma()}")
        print(f"Combined MM Signals: {detector.get_combined_mm_signals()}")
        
    except Exception as e:
        print(f"Error: {e}")
