from enum import Flag, unique

@unique
class MoneyManagerMethodList(Flag):
    FIXED_FRACTION = 'FixedFraction'
    CONSECUTIVE_WINS = 'ConsecutiveWins'