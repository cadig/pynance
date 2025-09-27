# Alpaca Trading Dashboard

A simple web-based UI for viewing your Alpaca trading positions, historical trades, and price charts with order overlays.

## Setup

1. **Generate configuration file:**
   ```bash
   cd ui
   python load_config.py
   ```
   This will read your existing `config/alpaca-config.ini` file and generate a `config.js` file with your Alpaca credentials.

2. **Open the dashboard:**
   ```bash
   # Option 1: Open directly in browser
   open index.html
   
   # Option 2: Serve with a simple HTTP server (recommended)
   python -m http.server 8000
   # Then open http://localhost:8000
   ```

## Features

- **Current Positions**: View all your current Alpaca positions with P&L
- **Historical Trades**: Browse through your trading history by symbol
- **Interactive Charts**: Click on any ticker to view its price chart
- **Order Overlay**: See entry points, stop losses, and exits on the chart (coming soon)

## API Endpoints Used

The dashboard uses these Alpaca API endpoints:

1. **GET /v2/positions** - Current portfolio positions
2. **GET /v2/orders?status=all** - All historical orders
3. **GET /v2/orders?symbols={symbol}&status=all** - Orders for specific symbol
4. **GET /v2/stocks/{symbol}/bars** - Historical price data

## Configuration

The dashboard uses your existing Alpaca configuration from `config/alpaca-config.ini`. It reads the `paper` account credentials by default.

To switch to live trading, modify the `baseUrl` in the generated `config.js` file:
```javascript
baseUrl: 'https://api.alpaca.markets' // Live trading
```

## Security Note

This is designed for local use only. The `config.js` file contains your API credentials and should never be committed to version control or hosted publicly.
