#!/bin/bash

# Script to set up the pynance-v2.0 conda environment
# This script assumes conda is already installed

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

print_status "Setting up pynance-v2.0 environment..."

# Remove existing environment if it exists
if conda env list | grep -q "pynance-v2.0"; then
    print_warning "pynance-v2.0 environment already exists. Removing it first..."
    conda env remove -n pynance-v2.0 -y
fi

# Create environment from yaml file with fallback approach
print_status "Creating environment from pynance-v2.0.yml..."

# First try to create from yaml file
if conda env create -f envs/pynance-v2.0.yml; then
    print_success "Environment created successfully from yaml file!"
else
    print_warning "Failed to create environment from yaml file. Trying alternative approach..."
    
    # Create environment with core packages first
    print_status "Creating environment with core packages..."
    conda create -n pynance-v2.0 python=3.12 -y
    
    # Activate environment
    conda activate pynance-v2.0
    
    # Install core packages via conda
    print_status "Installing core packages via conda..."
    conda install -c conda-forge -c anaconda \
        pandas numpy matplotlib jupyter ipython \
        requests beautifulsoup4 lxml pyyaml pip \
        scikit-learn scipy seaborn -y
    
    # Install additional packages via pip
    print_status "Installing additional packages via pip..."
    pip install backtrader finvizfinance yfinance tradingview-datafeed alpaca-py configparser
    
    if [ $? -eq 0 ]; then
        print_success "Environment created successfully with alternative approach!"
    else
        print_error "Failed to create environment with alternative approach."
        exit 1
    fi
fi

# Activate environment and install additional packages that might be missing
print_status "Activating environment and installing additional packages..."
conda activate pynance-v2.0

# Install additional packages that are commonly needed but might not be in the yaml
print_status "Installing additional packages via pip..."

# Install alpaca-py (the main alpaca package)
pip install alpaca-py

# Install any other packages that might be missing
pip install configparser

print_success "Environment setup completed!"
print_status "Environment is ready. You can now run alpacaTrend.py"
