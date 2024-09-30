from enum import Enum

majorCurrencyPairs = [
    'AUD_USD', 'AUD_CAD', 'AUD_CHF', 'GBP_AUD', 'AUD_JPY', 'AUD_NZD', 'EUR_AUD', 'USD_CAD', 'CAD_CHF', 'CAD_JPY', 'GBP_CAD',
    'EUR_CAD', 'NZD_CAD', 'USD_CHF', 'EUR_CHF', 'GBP_CHF', 'CHF_JPY', 'NZD_CHF', 'EUR_GBP', 'EUR_USD', 'EUR_JPY', 'EUR_NZD',
    'GBP_JPY', 'GBP_NZD', 'GBP_USD', 'USD_JPY', 'NZD_JPY', 'NZD_USD'
]

class MajorCurrencyDictionary(Enum):
    AUD = {'list':['AUD_USD','AUD_CAD','AUD_CHF','GBP_AUD','AUD_JPY','AUD_NZD','EUR_AUD']}
    CAD = {'list':['AUD_CAD','USD_CAD','CAD_CHF','CAD_JPY','GBP_CAD','EUR_CAD','NZD_CAD']}
    CHF = {'list':['AUD_CHF','CAD_CHF','USD_CHF','EUR_CHF','GBP_CHF','CHF_JPY','NZD_CHF']}
    EUR = {'list':['EUR_AUD','EUR_CAD','EUR_CHF','EUR_GBP','EUR_USD','EUR_JPY','EUR_NZD']}
    GBP = {'list':['GBP_AUD','GBP_CAD','GBP_CHF','EUR_GBP','GBP_JPY','GBP_NZD','GBP_USD']}
    JPY = {'list':['AUD_JPY','CAD_JPY','CHF_JPY','EUR_JPY','GBP_JPY','USD_JPY','NZD_JPY']}
    NZD = {'list':['AUD_NZD','NZD_CAD','NZD_CHF','EUR_NZD','GBP_NZD','NZD_JPY','NZD_USD']}
    USD = {'list':['AUD_USD','USD_CAD','USD_CHF','EUR_USD','GBP_USD','USD_JPY','NZD_USD']}