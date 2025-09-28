#!/bin/bash

# Script to fix alpaca package installation
# This script removes alpaca-trade-api and installs alpaca-py

set -e  # Exit on any error

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Check if conda is available
if ! check_conda; then
    exit 1
fi

# Source conda
source_conda

# Activate environment
print_status "Activating pynance-v2.0 environment..."
conda activate pynance-v2.0

# Check what alpaca packages are currently installed
print_status "Checking current alpaca packages..."
pip list | grep -i alpaca

# Uninstall old alpaca-trade-api if it exists
print_status "Removing old alpaca-trade-api package..."
pip uninstall alpaca-trade-api -y 2>/dev/null || print_warning "alpaca-trade-api not found or already removed"

# Install the correct alpaca-py package
print_status "Installing alpaca-py package..."
pip install alpaca-py

# Verify the installation
print_status "Verifying alpaca-py installation..."
if python -c "from alpaca.trading.client import TradingClient; print('alpaca-py imported successfully')" 2>/dev/null; then
    print_success "alpaca-py is working correctly!"
else
    print_error "Failed to import alpaca-py. Please check the installation."
    exit 1
fi

# Test the specific imports used in alpacaTrend.py
print_status "Testing alpacaTrend.py imports..."
if python -c "
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.requests import MarketOrderRequest, StopOrderRequest, GetOrdersRequest, StopLossRequest, StopLimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus, PositionIntent
print('All alpaca imports successful!')
" 2>/dev/null; then
    print_success "All alpaca imports are working correctly!"
else
    print_error "Some alpaca imports failed. Please check the installation."
    exit 1
fi

print_success "Alpaca package fix completed!"
print_status "You can now run: python alpaca/alpacaTrend.py"
