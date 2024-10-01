# pynance - v2

... In this project I am slowly migrating and cleaning up functionality from my old & messy repositories to be more cleanly imported as standalone python packages to provide better building blocks for additional trading system development.


### forexutils - forex specific utilities
- convertPipsToPrice and convertPriceToPips
- getCrossPairMultiplier, getCrossPairPricePrecision
- getPairListByCurrency (using "EUR" as an input, for example)
- getPairSpreadThreshold (hardcoded pip values that dictate when NOT to trade a certain pair, and can act as a filter)
- isForexMarketOpen
- MajorCurrencyDictionary

### ibkr - interactive brokers related utilities and interfacing

### indicators - indicator calculations that aren't provided by another package (namely talib)
- KAMA: Kaufman Adaptive Moving Average

### moneymanagement - algorithms & functions used for calculating position sizes
- martingale & reverse martingale - inspired by [this book](https://www.amazon.com/Forex-Trading-Money-Management-System/dp/1542621895). Includes parameterization for flat_lining, stay_at_max, cycle_target, etc. described by the book for handling dynamic position sizing based on winning/losing streaks.
- Also has basic fixed fractional sizing, kelly sizing, and more
- Account risk modulator to dynamically increase or decrease bet size based on the return of the account

### oanda - interface for the oanda forex broker oandapyv20 API
- OandaTrader: provides methods for placing various order types against the oanda API for live trading
- OandaClerk: provides methods for retrieving various data points from the oanda API

### signals - calculations on price and volume data to determine when to enter and exit trades
- EntryEngine - methods for entering trades
- ExitEngine - methods for exiting trades
