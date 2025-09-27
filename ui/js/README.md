# JavaScript Modules

This directory contains the separated JavaScript modules for the Alpaca Trading Dashboard.

## File Structure

- **`api.js`** - Contains all API-related functions for communicating with the Alpaca API
  - `loadCredentials()` - Load Alpaca credentials from config
  - `loadPositions()` - Fetch current positions
  - `loadHistoricalTrades()` - Fetch historical trades/orders
  - `loadOrdersForSymbol(symbol)` - Load orders for a specific symbol
  - Getter functions for accessing stored data

- **`chart.js`** - Contains all chart-related functions using TradingView LightweightCharts
  - `initChart()` - Initialize the TradingView chart
  - `loadChartData(symbol)` - Load and display chart data for a symbol
  - `clearChartOverlays()` - Clear all chart overlays
  - Getter functions for chart series

- **`ui.js`** - Contains all UI rendering and display functions
  - `renderPositions()` - Render the positions list
  - `renderTrades()` - Render the trades list
  - `showError(message)` - Display error messages
  - `updateSelectedSymbol(symbol, status)` - Update the selected symbol display
  - Various UI state management functions

- **`app.js`** - Contains the main application logic and orchestration
  - `init()` - Initialize the application
  - `selectTicker(symbol)` - Handle ticker selection and data loading
  - `overlayOrdersOnChart(orders)` - Process and overlay orders on the chart
  - `addStopLossLines(stopLossOrders)` - Add stop loss lines to the chart
  - `refreshData()` - Refresh all data
  - `getSelectedSymbol()` - Get the currently selected symbol

## Dependencies

The modules depend on each other in the following order:
1. `api.js` - No dependencies
2. `chart.js` - No dependencies  
3. `ui.js` - Depends on `api.js` (uses `getPositions()`, `getHistoricalTrades()`)
4. `app.js` - Depends on all other modules

## Usage

The modules are loaded in the correct order in `index.html`:
```html
<script src="config.js"></script>
<script src="js/api.js"></script>
<script src="js/chart.js"></script>
<script src="js/ui.js"></script>
<script src="js/app.js"></script>
```

## Benefits of Separation

- **Maintainability**: Each module has a single responsibility
- **Reusability**: Functions can be easily reused across different parts of the application
- **Debugging**: Easier to isolate and fix issues in specific functionality
- **Testing**: Individual modules can be tested independently
- **Collaboration**: Different developers can work on different modules without conflicts
