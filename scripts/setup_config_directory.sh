#!/bin/bash

# Script to set up the config directory structure
# This creates a sibling config directory to avoid accidentally committing credentials

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

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$(dirname "$PROJECT_ROOT")/config"

print_status "Setting up config directory structure..."

# Create config directory
print_status "Creating config directory at: $CONFIG_DIR"
mkdir -p "$CONFIG_DIR"

# Create alpaca config file if it doesn't exist
CONFIG_FILE="$CONFIG_DIR/alpaca-config.ini"
if [ ! -f "$CONFIG_FILE" ]; then
    print_status "Creating alpaca-config.ini template..."
    cat > "$CONFIG_FILE" << EOF
[paper]
API_KEY = your_api_key_here
API_SECRET = your_api_secret_here

[live]
API_KEY = your_live_api_key_here
API_SECRET = your_live_api_secret_here
EOF
    print_success "Created $CONFIG_FILE"
else
    print_success "Config file already exists at $CONFIG_FILE"
fi

# Set secure permissions on config file
print_status "Setting secure permissions on config file..."
chmod 600 "$CONFIG_FILE"

print_success "Config directory setup completed!"
print_status "Config directory: $CONFIG_DIR"
print_status "Please edit $CONFIG_FILE with your actual API credentials"
