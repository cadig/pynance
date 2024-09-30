def convertPriceToPips(instrument, price):
    """Convert a price to value in pips"""
    if 'JPY' not in instrument and 'HUF' not in instrument:
        return price*10000
    elif 'JPY' in instrument or 'HUF' in instrument:
        return price*100