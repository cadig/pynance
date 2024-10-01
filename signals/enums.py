from enum import Flag, unique

@unique
class EntryMethod(Flag):
    HOURLY_CORNFLOWER = 'HOURLY_CORNFLOWER'
    DONCHIAN_CHANNEL_BREAKOUT = 'DONCHIAN_CHANNEL_BREAKOUT'
    WEEKLY_TREND_TRADER = 'WEEKLY_TREND_TRADER'
    KELTNER_CHANNEL_BREAKOUT = 'KELTNER_CHANNEL_BREAKOUT'
    RSI_PULLBACK = 'RSI_PULLBACK'
    SMA_PRICE_CROSS = 'SMA_PRICE_CROSS'
    
@unique
class ExitMethod(Flag):
    ATR = 'ATR'
    DONCHIAN_CHANNEL_BREAKOUT = 'DONCHIAN_CHANNEL_BREAKOUT'
    SMA_PRICE_CROSS = 'SMA_PRICE_CROSS'
    EMA_PRICE_CROSS = 'EMA_PRICE_CROSS'
    KELTNER_CHANNEL_BREAKOUT = 'KELTNER_CHANNEL_BREAKOUT'
    RSI_THRESHOLD = 'RSI_THRESHOLD'

@unique
class FilterType(Flag):
    EMA = 'EMA'
    SMA = 'SMA'
    
@unique
class MarketSentiment(Flag):
    BULLISH = 'BULLISH'
    BEARISH = 'BEARISH'
    NONE = 'NONE'

@unique
class TradeDirection(Flag):
    LONG = 'LONG'
    SHORT = 'SHORT'
    NONE = 'NONE'

@unique
class TrendDirection(Flag):
    UP = 'UP'
    DOWN = 'DOWN'
    NONE = 'NONE'
    