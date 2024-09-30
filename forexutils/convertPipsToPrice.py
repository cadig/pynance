def convertPipsToPrice(instrument, pips):
    """Convert number of pips to price (distance)"""
    if 'JPY' not in instrument and 'HUF' not in instrument:
        return pips/10000
    elif 'JPY' in instrument or 'HUF' in instrument:
        return pips/100