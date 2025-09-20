#!/bin/bash

# Script to run alpacaTrend.py with proper environment activation
# This script assumes the pynance-v2.0 environment is already set up

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
if [ ! -f "alpaca/alpacaTrend.py" ]; then
    print_error "alpacaTrend.py not found. Please run this script from the project root directory."
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

# Check if pynance-v2.0 environment exists
if ! conda env list | grep -q "pynance-v2.0"; then
    print_error "pynance-v2.0 environment not found. Please run setup_environment.sh first."
    exit 1
fi

# Activate environment
print_status "Activating pynance-v2.0 environment..."
conda activate pynance-v2.0

# Check if required config file exists
if [ ! -f "config/alpaca-config.ini" ]; then
    print_warning "alpaca-config.ini not found. Creating template..."
    mkdir -p config
    cat > config/alpaca-config.ini << EOF
[paper]
API_KEY = your_api_key_here
API_SECRET = your_api_secret_here

[live]
API_KEY = your_live_api_key_here
API_SECRET = your_live_api_secret_here
EOF
    print_warning "Please edit config/alpaca-config.ini with your actual API credentials."
    print_warning "The script will continue but may fail without proper credentials."
fi

# Change to alpaca directory to run the script
print_status "Running alpacaTrend.py..."
cd alpaca

# Run the script
python alpacaTrend.py

# Check exit status
if [ $? -eq 0 ]; then
    print_success "alpacaTrend.py completed successfully!"
else
    print_error "alpacaTrend.py failed with exit code $?"
    exit 1
fi
