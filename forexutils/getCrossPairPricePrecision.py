import json
from decimal import Decimal as D

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, D):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

def getCrossPairPricePrecision(instrument,price):
    if "JPY" not in instrument and "HUF" not in instrument:
        prec = 5
    else:
        prec = 3
    if price == 'na':
        return price
    else:
        prec_price = float(price)
        prec_price = DecimalEncoder().encode(round((prec_price),prec))
        return prec_price