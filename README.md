# pynance - v2

... Slowly migrating and cleaning up functionality from my old repositories to be more cleanly imported as standalone python packages


### forexutils - forex specific utilities

### moneymanagement - algorithms & functions used for calculating position sizes
- martingale & reverse martingale - inspired by [this book](https://www.amazon.com/Forex-Trading-Money-Management-System/dp/1542621895). Includes parameterization for flat_lining, stay_at_max, cycle_target, etc. described by the book for handling dynamic position sizing based on winning/losing streaks.
- Also has basic fixed fractional sizing, kelly sizing, and more ...

### oanda - interface for the oanda forex broker oandapyv20 API
