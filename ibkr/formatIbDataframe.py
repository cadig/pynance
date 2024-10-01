from pandas import to_datetime

def formatIbDataframe(df, granularity=None):
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['open'] = df['open'].astype(float)
    df['volume'] = df['volume'].astype(float)
    if granularity=='1 week' or granularity=='1 day':
        df['time'] = to_datetime(df['date'], utc=True, format='%Y-%m-%d')
    else:
        df['time'] = to_datetime(df['date'], utc=True, format='%Y-%m-%dT%H:%M:%S.%f000Z')
    df.set_index( df['time'], drop=True, inplace=True )
    return df