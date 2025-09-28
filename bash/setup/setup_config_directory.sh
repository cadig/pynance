#!/bin/bash

# Script to set up the config directory structure
# This creates a sibling config directory to avoid accidentally committing credentials

set -e  # Exit on any error

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(dirname "$SCRIPT_DIR")/common.sh"

# Get the directory where this script is located
PROJECT_ROOT="$(get_project_root_direct)"
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
