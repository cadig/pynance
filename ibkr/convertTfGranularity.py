def convertTfGranularity(engine_granularity):
    # TODO- encode all:
    # 1 sec, 5 secs, 15 secs, 30 secs,
    # 1 min, 2 mins, 3 mins, 5 mins...
    if engine_granularity=='M15':
        granularity='15 mins'
    if engine_granularity=='M30':
        granularity='30 mins'
    if engine_granularity=='H1':
        granularity='1 hour'
    if engine_granularity=='D':
        granularity='1 day'
    if engine_granularity=='W':
        granularity='1 week'
    return granularity