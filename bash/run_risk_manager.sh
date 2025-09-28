#!/bin/bash

# Script to run RiskManager.py with proper environment activation
# This script assumes the pynance-v2.0 environment is already set up

set -e  # Exit on any error

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Check if we're in the right directory
check_project_directory "alpaca/RiskManager.py"

# Check if conda is available
if ! check_conda; then
    exit 1
fi

# Source conda
source_conda

# Check if pynance-v2.0 environment exists
if ! check_pynance_env; then
    exit 1
fi

# Activate environment
activate_pynance_env

# Setup config files
setup_config_files

# Set up logging directory structure
print_status "Setting up logging directory structure..."
LOGS_DIR="../logs"
SYSTEM_ID="01_alpaca"
SCRIPT_ID="RiskManager"

LOG_FILE_ABS=$(setup_logging_structure "$LOGS_DIR" "$SYSTEM_ID" "$SCRIPT_ID")

# Change to alpaca directory to run the script
print_status "Running RiskManager.py..."
cd alpaca

# Run the script and capture output
# Redirect both stdout and stderr to the log file and also display in real-time using tee
python RiskManager.py 2>&1 | tee "$LOG_FILE_ABS"

# Check exit status
if [ $? -eq 0 ]; then
    print_success "RiskManager.py completed successfully!"
else
    print_error "RiskManager.py failed with exit code $?"
    exit 1
fi
