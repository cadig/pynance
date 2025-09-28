#!/bin/bash

# Script to check if conda is installed and the pynance-v2.0 environment exists
# If conda is not installed, it will install miniconda
# If the environment doesn't exist, it will be created from the yaml file

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

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    print_warning "Conda is not installed. Installing miniconda..."
    
    # Detect system architecture
    ARCH=$(uname -m)
    if [ "$ARCH" = "x86_64" ]; then
        CONDA_ARCH="x86_64"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        CONDA_ARCH="aarch64"
    else
        print_error "Unsupported architecture: $ARCH"
        exit 1
    fi
    
    # Download and install miniconda
    print_status "Downloading miniconda installer..."
    wget -O miniconda.sh "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-${CONDA_ARCH}.sh"
    
    print_status "Installing miniconda..."
    bash miniconda.sh -b -p $HOME/miniconda3
    
    # Add conda to PATH
    export PATH="$HOME/miniconda3/bin:$PATH"
    echo 'export PATH="$HOME/miniconda3/bin:$PATH"' >> ~/.bashrc
    
    # Initialize conda
    $HOME/miniconda3/bin/conda init bash
    source ~/.bashrc
    
    # Clean up installer
    rm miniconda.sh
    
    print_success "Miniconda installed successfully!"
else
    print_success "Conda is already installed."
fi

# Source conda to make sure it's available
if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
    source "/opt/conda/etc/profile.d/conda.sh"
fi

# Check if pynance-v2.0 environment exists
if conda env list | grep -q "pynance-v2.0"; then
    print_success "pynance-v2.0 environment already exists."
else
    print_warning "pynance-v2.0 environment not found. Creating from yaml file..."
    
    # Create environment from yaml file
    conda env create -f envs/pynance-v2.0.yml
    
    if [ $? -eq 0 ]; then
        print_success "pynance-v2.0 environment created successfully!"
    else
        print_error "Failed to create pynance-v2.0 environment."
        exit 1
    fi
fi

# Verify the environment has the required packages
print_status "Verifying environment packages..."
conda activate pynance-v2.0

# Check for key packages that trendTrader.py and RiskManager.py need
REQUIRED_PACKAGES=("pandas" "numpy" "matplotlib" "alpaca-trade-api" "finvizfinance" "backtrader" "yfinance" "tradingview-datafeed")

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python -c "import $package" 2>/dev/null; then
        print_success "$package is available"
    else
        print_warning "$package is not available - may need to install via pip"
    fi
done

print_success "Environment check completed!"
print_status "To activate the environment, run: conda activate pynance-v2.0"
