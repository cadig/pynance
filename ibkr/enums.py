from enum import Flag, unique

@unique
class IB_AssetClass(Flag):
    STK = 'STK'
    ContFuture = 'ContFuture'