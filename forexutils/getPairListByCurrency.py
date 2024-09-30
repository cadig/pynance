def getPairListByCurrency(currency):
    if currency == 'AUD':
        currency_list = ['AUD_JPY', 'AUD_CAD', 'AUD_CHF', 'EUR_AUD', 'GBP_AUD', 'AUD_NZD', 'AUD_USD']
    elif currency == 'CAD':
        currency_list = ['AUD_CAD', 'CAD_JPY', 'CAD_CHF', 'EUR_CAD', 'GBP_CAD', 'NZD_CAD', 'USD_CAD']
    elif currency == 'CHF':
        currency_list = ['AUD_CHF', 'CHF_JPY', 'CAD_CHF', 'EUR_CHF', 'GBP_CHF', 'NZD_CHF', 'USD_CHF']
    elif currency == 'EUR':
        currency_list = ['EUR_AUD', 'EUR_CAD', 'EUR_CHF', 'EUR_GBP', 'EUR_NZD', 'EUR_JPY', 'EUR_USD']
    elif currency == 'GBP':
        currency_list = ['GBP_AUD', 'GBP_CAD', 'GBP_CHF', 'EUR_GBP', 'GBP_NZD', 'GBP_JPY', 'GBP_USD']
    elif currency == 'JPY':
        currency_list = ['AUD_JPY', 'CAD_JPY', 'CHF_JPY', 'EUR_JPY', 'GBP_JPY', 'NZD_JPY', 'USD_JPY']
    elif currency == 'NZD':
        currency_list = ['AUD_NZD', 'NZD_JPY', 'NZD_CHF', 'EUR_NZD', 'GBP_NZD', 'NZD_CAD', 'NZD_USD']
    elif currency == 'USD':
        currency_list = ['AUD_USD', 'USD_JPY', 'USD_CHF', 'EUR_USD', 'GBP_USD', 'NZD_USD', 'USD_CAD']
    else:
        print('forex_utils.getCurrencyList ERROR: unsupported currency input.')
    return currency_list