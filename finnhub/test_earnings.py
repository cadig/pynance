"""
Test script for earnings functionality
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finnhub.earnings import get_next_earnings_date, is_earnings_at_least_days_away


def test_earnings_functions():
    """Test the earnings functions with AAPL"""
    try:
        print("Testing earnings functions...")
        
        # Test getting next earnings date
        print("\n1. Testing get_next_earnings_date('AAPL')...")
        next_earnings = get_next_earnings_date('AAPL')
        if next_earnings:
            print(f"Next earnings date for AAPL: {next_earnings.strftime('%Y-%m-%d')}")
        else:
            print("No earnings date found for AAPL")
        
        # Test earnings validation
        print("\n2. Testing is_earnings_at_least_days_away('AAPL', 8)...")
        is_safe = is_earnings_at_least_days_away('AAPL', min_days=8)
        print(f"AAPL earnings are at least 8 days away: {is_safe}")
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        print("Make sure you have a valid finnhub-config.ini file with API_KEY")


if __name__ == "__main__":
    test_earnings_functions()
