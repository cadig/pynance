# Pynance v2.0

A comprehensive Python trading system framework that provides building blocks for algorithmic trading, market analysis, and portfolio management. This project attempts to consolidate and refactor functionality from some of my old repositories into something more reusable and modular, while still serving as my main trading/investing repository for ongoing research, tooling, and execution.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/pynance.git
cd pynance

# Set up conda environment
conda env create -f envs/pynance-v2.0.yml
conda activate pynance-v2.0

# Run the trading dashboard
python dashboard.py
```

## 📁 Project Structure

```
pynance/
├── 📊 data/                    # Market data and data processing utilities
├── 🔬 research/                # Market research and analysis tools
├── 📈 ibkr/                    # Interactive Brokers integration
├── 💱 oanda/                   # OANDA forex broker integration
├── 📊 alpaca/                  # Alpaca trading platform integration
├── 🔧 finviz/                  # Finviz data scraping utilities
├── 💹 forexutils/              # Forex-specific utility functions
├── 📊 yfinance/                # Yahoo Finance data utilities
├── 📈 indicators/              # Custom technical indicators
├── 💰 moneymanagement/         # Position sizing and risk management
├── 🎯 signals/                 # Entry and exit signal generation
├── 📊 backtrader/              # Backtesting strategies
├── 📋 dashboard.py             # Main trading dashboard GUI
└── ⏰ time_utils.py            # Time and market hours utilities
```

## 🎯 Core Features

### 📊 **Trading Dashboard**
A comprehensive GUI application (`dashboard.py`) that provides:
- **Order Entry**: Place trades with risk management
- **Market Scanner**: Real-time volume breakout detection
- **Risk Management**: Portfolio risk monitoring
- **Research Tools**: Market analysis and signal generation
- **Data Collection**: Automated market data fetching

### 🔬 **Research & Analysis**
Advanced market research capabilities in the `research/` directory:
- **Regime Detection**: NYSE cumulative AD z-score analysis
- **Breakout Statistics**: Historical gap and breakout analysis
- **Signal Generation**: Multi-timeframe momentum signals
- **Market Visualization**: Interactive charts and plots
- **Backtesting**: Strategy performance evaluation

### 📈 **Broker Integrations**

#### Interactive Brokers (`ibkr/`)
- **IbkrTrader**: Core trading interface with order management
- **Order Types**: Bracket orders, trailing stops, limit orders
- **Data Retrieval**: Historical and real-time market data
- **Position Management**: Portfolio tracking and risk calculation
- **Account Management**: Multi-account support with allocation

#### OANDA (`oanda/`)
- **OandaTrader**: Live forex trading execution
- **OandaClerk**: Market data and account information
- **Order Management**: Market, limit, and stop orders
- **Position Tracking**: Real-time P&L monitoring

#### Alpaca (`alpaca/`)
- **Position Tracking**: Portfolio position management
- **Paper Trading**: Risk-free strategy testing

### 💰 **Money Management**
Sophisticated position sizing algorithms in `moneymanagement/`:
- **Martingale Systems**: Traditional and reverse martingale
- **Kelly Criterion**: Optimal position sizing
- **Fixed Fractional**: Percentage-based risk management
- **Account Risk Modulator**: Dynamic risk adjustment
- **Streak Management**: Win/loss streak handling

### 🎯 **Signal Generation**
Advanced signal processing in `signals/`:
- **EntryEngine**: Multi-timeframe entry signal detection
- **ExitEngine**: Risk management and profit-taking signals
- **Signal Types**: Momentum, mean reversion, breakout signals
- **Confirmation Logic**: Multi-factor signal validation

### 📊 **Technical Indicators**
Custom indicators in `indicators/`:
- **KAMA**: Kaufman Adaptive Moving Average
- **Custom Implementations**: Specialized technical analysis tools

### 💹 **Forex Utilities**
Specialized forex tools in `forexutils/`:
- **Pip Calculations**: Price to pip conversion utilities
- **Cross Pair Analysis**: Multi-currency pair calculations
- **Spread Management**: Dynamic spread threshold monitoring
- **Market Hours**: Forex market session detection
- **Currency Dictionaries**: Major currency pair mappings

### 📊 **Data Management**
Comprehensive data handling in `data/`:
- **Market Data**: SPX, VIX, bonds, commodities
- **Data Fetching**: Automated data collection scripts
- **Data Processing**: Cleaning and formatting utilities
- **Symbol Management**: Dynamic symbol list generation

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Conda or Miniconda
- Interactive Brokers TWS/Gateway (for IBKR features)
- OANDA account (for forex features)

### Environment Setup
```bash
# Create conda environment
conda env create -f envs/pynance-v2.0.yml
conda activate pynance-v2.0

# Install additional dependencies
pip install -r requirements.txt
```

### Configuration
1. Copy `config/dashboard-config.ini.example` to `config/dashboard-config.ini`
2. Update configuration with your broker credentials and paths
3. Ensure data directory contains required CSV files

## 🚀 Usage Examples

### Running the Dashboard
```bash
python dashboard.py
```

### Manual Data Collection
```bash
# Fetch latest market data
python data/fetch_data.py

# Get recent gainers from Finviz
python data/finvizConsolidateRecentGainers.py
```

### Research Analysis
```bash
# Generate SPX regime analysis
python research/combined-research.py

# Run breakout statistics
python research/getBreakoutStats.py SPY 2024-01-15
```

### Trading Operations
```bash
# Check risk and orders
python ibkr/checkRiskAndOrders.py

# Run volume breakout scanner
python ibkr/longVolBreakouts.py
```

## 🔧 Configuration

### Dashboard Configuration
Edit `config/dashboard-config.ini`:
```ini
[paths]
repo_root = /path/to/pynance

[environment]
conda_env = pynance-v2.0
```

### Broker Configuration
- **IBKR**: Configure TWS/Gateway connection settings
- **OANDA**: Set API credentials in environment variables
- **Alpaca**: Configure API keys in environment variables

## 📈 Key Features

### 🎯 **Multi-Asset Support**
- **Equities**: US stocks and ETFs
- **Forex**: Major and minor currency pairs
- **Futures**: Commodity and index futures
- **Options**: Options trading support

### 🔄 **Real-Time Processing**
- **Live Data**: Real-time market data feeds
- **Signal Generation**: Continuous signal monitoring
- **Risk Management**: Real-time portfolio risk assessment
- **Order Management**: Automated order execution

### 📊 **Advanced Analytics**
- **Regime Detection**: Market regime identification
- **Signal Confirmation**: Multi-factor signal validation
- **Performance Tracking**: Strategy performance monitoring
- **Risk Metrics**: Comprehensive risk analysis

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Trading involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Always consult with a qualified financial advisor before making investment decisions.

## 📞 Support

For questions, issues, or contributions:
- Create an issue on GitHub
- Check the documentation in the `docs/` directory
- Review the configuration examples

---

**Happy Trading! 📈**