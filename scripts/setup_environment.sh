#!/bin/bash

# Script to set up the pynance-v2.0 conda environment
# This script assumes conda is already installed

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

print_status "Setting up pynance-v2.0 environment..."

# Remove existing environment if it exists
if conda env list | grep -q "pynance-v2.0"; then
    print_warning "pynance-v2.0 environment already exists. Removing it first..."
    conda env remove -n pynance-v2.0 -y
fi

# Create environment from yaml file
print_status "Creating environment from pynance-v2.0.yml..."
conda env create -f envs/pynance-v2.0.yml

if [ $? -eq 0 ]; then
    print_success "Environment created successfully!"
else
    print_error "Failed to create environment from yaml file."
    exit 1
fi

# Activate environment and install additional packages that might be missing
print_status "Activating environment and installing additional packages..."
conda activate pynance-v2.0

# Install additional packages that are commonly needed but might not be in the yaml
print_status "Installing additional packages via pip..."

# Install alpaca-trade-api (the main alpaca package)
pip install alpaca-trade-api

# Install any other packages that might be missing
pip install configparser

print_success "Environment setup completed!"
print_status "Environment is ready. You can now run alpacaTrend.py"
