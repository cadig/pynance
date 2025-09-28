#!/bin/bash

# Simplified script to create pynance environment without problematic packages
# This avoids the brotli-bin and other package conflicts

set -e  # Exit on any error

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(dirname "$SCRIPT_DIR")/common.sh"

# Check if we're in the right directory
check_project_directory "envs/pynance-v2.0.yml"

# Check if conda is available
if ! check_conda; then
    exit 1
fi

# Source conda
source_conda

print_status "Creating simplified pynance-v2.0 environment..."

# Remove existing environment if it exists
if conda env list | grep -q "pynance-v2.0"; then
    print_warning "pynance-v2.0 environment already exists. Removing it first..."
    conda env remove -n pynance-v2.0 -y
fi

# Create environment with Python 3.12
print_status "Creating base environment with Python 3.12..."
conda create -n pynance-v2.0 python=3.12 -y

# Activate environment
conda activate pynance-v2.0

# Install core packages via conda (avoiding problematic ones)
print_status "Installing core packages via conda..."
conda install -c conda-forge -c anaconda \
    pandas numpy matplotlib jupyter ipython \
    requests beautifulsoup4 lxml pyyaml pip \
    scikit-learn scipy seaborn \
    sqlite tzdata -y

# Install additional packages via pip
print_status "Installing additional packages via pip..."
pip install \
    backtrader \
    finvizfinance \
    yfinance \
    tradingview-datafeed \
    alpaca-py \
    configparser \
    peewee \
    websocket-client \
    websockets \
    httpx \
    curl-cffi

# Install jupyter and related packages
print_status "Installing Jupyter packages..."
pip install \
    jupyter \
    jupyterlab \
    notebook \
    ipywidgets \
    bokeh

print_success "Environment created successfully!"
print_status "Environment is ready. You can now run alpacaTrend.py"
