def getPairSpreadThreshold(instrument):
    """Return the maximum spread_threshold for the given instrument."""
    if (instrument == 'EUR_USD' or
        instrument == 'USD_JPY' or
        instrument == 'AUD_USD'):
            spread_threshold = 6 #2.3 #1.5
    elif (instrument == 'AUD_JPY' or 
          instrument == 'EUR_GBP' or
          instrument == 'GBP_USD' or
          instrument == 'USD_CAD' or
          instrument == 'EUR_CHF' or
          instrument == 'USD_CHF' or
          instrument == 'EUR_JPY' or
          instrument == 'NZD_USD' or
          instrument == 'CAD_JPY'):
        spread_threshold = 7 #2.8 #2
    elif (instrument == 'AUD_CAD' or 
          instrument == 'CAD_CHF' or
          instrument == 'EUR_CAD' or
          instrument == 'CHF_JPY' or
          instrument == 'NZD_JPY'):
        spread_threshold = 9 #3.3 #2.5
    elif (instrument == 'AUD_CHF' or 
          instrument == 'EUR_AUD' or
          instrument == 'AUD_NZD' or
          instrument == 'GBP_CHF' or
          instrument == 'GBP_JPY' or
          instrument == 'NZD_CAD' or
          instrument == 'NZD_CHF'):
        spread_threshold = 6 #3.8 # 3
    elif (instrument == 'EUR_NZD'):
        spread_threshold = 11 #4.4 # 3.6
    elif (instrument == 'GBP_CAD'):
        spread_threshold = 9 #5.2 # 4.4
    elif (instrument == 'GBP_AUD'):
        spread_threshold = 14 #5.8 # 5
    elif (instrument == 'GBP_NZD'):
        spread_threshold = 14 #7.0 # 6.2
    else:
        print('forex_utils.getPairSpreadThreshold: did not find instrument ', instrument)
        print('returning default - 100 pips')
        spread_threshold = 100
        
    return spread_threshold