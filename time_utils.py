from datetime import datetime, timedelta
from typing import Tuple
import pytz

def isDaylightSavings() -> bool:
    """
    Check if current date is in daylight savings time for the US.
    """
    tz = pytz.timezone('America/New_York')
    now = datetime.now(tz)
    return now.dst() != timedelta(0)

def getMarketHours() -> Tuple[datetime, datetime]:
    """
    Based on daylight savings time, return the market open and close times in local time.
    TODO: handle timezone support
    """
    
    if isDaylightSavings():
        marketOpen = datetime.now().replace(hour=6, minute=30, second=0, microsecond=0)
        marketClose = datetime.now().replace(hour=13, minute=0, second=0, microsecond=0)
        
    else:
        marketOpen = datetime.now().replace(hour=7, minute=30, second=0, microsecond=0)
        marketClose = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
        
    return [marketOpen, marketClose]