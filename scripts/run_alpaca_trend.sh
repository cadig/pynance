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

# Check if required config file exists (in sibling directory)
CONFIG_DIR="../config"
CONFIG_FILE="$CONFIG_DIR/alpaca-config.ini"

if [ ! -f "$CONFIG_FILE" ]; then
    print_warning "alpaca-config.ini not found. Creating template in sibling config directory..."
    mkdir -p "$CONFIG_DIR"
    cat > "$CONFIG_FILE" << EOF
[paper]
API_KEY = your_api_key_here
API_SECRET = your_api_secret_here

[live]
API_KEY = your_live_api_key_here
API_SECRET = your_live_api_secret_here
EOF
    print_warning "Please edit $CONFIG_FILE with your actual API credentials."
    print_warning "The config directory is located outside the repository for security."
    print_warning "The script will continue but may fail without proper credentials."
fi

# Set up logging directory structure
print_status "Setting up logging directory structure..."
LOGS_DIR="../logs"
SYSTEM_ID="01_alpacaTrend"
CURRENT_DATE=$(date +%Y-%m-%d)
CURRENT_YEAR_MONTH=$(date +%Y-%m)
CURRENT_DAY_OF_WEEK=$(date +%A)

# Create system directory if it doesn't exist
SYSTEM_DIR="$LOGS_DIR/$SYSTEM_ID"
if [ ! -d "$SYSTEM_DIR" ]; then
    print_status "Creating system log directory: $SYSTEM_DIR"
    mkdir -p "$SYSTEM_DIR"
fi

# Create year-month directory if it doesn't exist
YEAR_MONTH_DIR="$SYSTEM_DIR/$CURRENT_YEAR_MONTH"
if [ ! -d "$YEAR_MONTH_DIR" ]; then
    print_status "Creating log directory: $YEAR_MONTH_DIR"
    mkdir -p "$YEAR_MONTH_DIR"
fi

# Create log filename: YYYY-MM-DD-DayOfWeek.log
LOG_FILENAME="${CURRENT_DATE}-${CURRENT_DAY_OF_WEEK}.log"
LOG_FILE="$YEAR_MONTH_DIR/$LOG_FILENAME"

print_status "Logging output to: $LOG_FILE"

# Change to alpaca directory to run the script
print_status "Running alpacaTrend.py..."
cd alpaca

# Run the script and capture output
# Redirect both stdout and stderr to the log file and also display in real-time using tee
python alpacaTrend.py 2>&1 | tee "$LOG_FILE"

# Check exit status
if [ $? -eq 0 ]; then
    print_success "alpacaTrend.py completed successfully!"
else
    print_error "alpacaTrend.py failed with exit code $?"
    exit 1
fi
