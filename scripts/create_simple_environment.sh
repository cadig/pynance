#!/bin/bash

# Simplified script to create pynance environment without problematic packages
# This avoids the brotli-bin and other package conflicts

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "envs/pynance-v2.0.yml" ]; then
    print_error "pynance-v2.0.yml not found. Please run this script from the project root directory."
    exit 1
fi

# Check if conda is available
if ! command -v conda &> /dev/null; then
    print_error "Conda is not installed. Please run check_conda_environment.sh first."
    exit 1
fi

# Source conda
if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
    source "/opt/conda/etc/profile.d/conda.sh"
fi

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
