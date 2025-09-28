#!/bin/bash

# Master installation script that runs all setup steps
# This script will check for conda, install miniconda if needed, and set up the environment

set -e  # Exit on any error

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get the directory where this script is located
PROJECT_ROOT="$(get_project_root_direct)"

print_header "PYNANCE INSTALLATION SCRIPT"

# Change to project root directory
print_status "Changing to project root directory: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Step 1: Check and install conda if needed
print_status "Step 1: Checking conda installation..."
if ! command -v conda &> /dev/null; then
    print_warning "Conda not found. Installing miniconda..."
    
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

# Step 2: Set up the conda environment
print_status "Step 2: Setting up pynance-v2.0 environment..."

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

# Step 3: Install additional packages
print_status "Step 3: Installing additional packages..."
conda activate pynance-v2.0

# Install additional packages that are commonly needed
print_status "Installing additional packages via pip..."
pip install alpaca-py configparser

print_success "Additional packages installed!"

# Step 4: Create config template
print_status "Step 4: Creating configuration template..."
CONFIG_DIR="../config"
CONFIG_FILE="$CONFIG_DIR/alpaca-config.ini"

if [ ! -f "$CONFIG_FILE" ]; then
    mkdir -p "$CONFIG_DIR"
    cat > "$CONFIG_FILE" << EOF
[paper]
API_KEY = your_api_key_here
API_SECRET = your_api_secret_here

[live]
API_KEY = your_live_api_key_here
API_SECRET = your_live_api_secret_here
EOF
    print_warning "Created $CONFIG_FILE template. Please edit with your actual API credentials."
else
    print_success "Configuration file already exists at $CONFIG_FILE"
fi

# Step 5: Verify installation
print_status "Step 5: Verifying installation..."

# Check for key packages
REQUIRED_PACKAGES=("pandas" "numpy" "matplotlib" "alpaca_trade_api" "finvizfinance" "backtrader" "yfinance" "tradingview_datafeed")

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python -c "import $package" 2>/dev/null; then
        print_success "$package is available"
    else
        print_warning "$package is not available - may need manual installation"
    fi
done

print_success "Installation completed successfully!"
print_status "To run alpacaTrend.py, use: ./scripts/run_alpaca_trend.sh"
print_status "Make sure to configure your API credentials in ../config/alpaca-config.ini first!"
print_status "The config directory is located outside the repository for security."
