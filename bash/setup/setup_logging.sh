#!/bin/bash

# Script to set up the logging directory structure
# This creates the logs directory as a sibling to the repo to avoid accidental commits

set -e  # Exit on any error

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(dirname "$SCRIPT_DIR")/common.sh"

# Get the directory where this script is located
PROJECT_ROOT="$(get_project_root_direct)"
LOGS_DIR="$(dirname "$PROJECT_ROOT")/logs"

print_status "Setting up logging directory structure..."

# Create logs directory
print_status "Creating logs directory at: $LOGS_DIR"
mkdir -p "$LOGS_DIR"

# Create system directories for different trading systems
SYSTEMS=("01_alpaca")

for system in "${SYSTEMS[@]}"; do
    SYSTEM_DIR="$LOGS_DIR/$system"
    if [ ! -d "$SYSTEM_DIR" ]; then
        print_status "Creating system directory: $SYSTEM_DIR"
        mkdir -p "$SYSTEM_DIR"
        print_success "Created $SYSTEM_DIR"
    else
        print_success "System directory already exists: $SYSTEM_DIR"
    fi
    
    # Create script subdirectories for each system
    SCRIPTS=("trendTrader" "RiskManager")
    for script in "${SCRIPTS[@]}"; do
        SCRIPT_DIR="$SYSTEM_DIR/$script"
        if [ ! -d "$SCRIPT_DIR" ]; then
            print_status "Creating script directory: $SCRIPT_DIR"
            mkdir -p "$SCRIPT_DIR"
            print_success "Created $SCRIPT_DIR"
        else
            print_success "Script directory already exists: $SCRIPT_DIR"
        fi
    done
done

# Create current month directories for alpaca system scripts
CURRENT_YEAR_MONTH=$(date +%Y-%m)
SCRIPTS=("trendTrader" "RiskManager")

for script in "${SCRIPTS[@]}"; do
    YEAR_MONTH_DIR="$LOGS_DIR/01_alpaca/$script/$CURRENT_YEAR_MONTH"
    if [ ! -d "$YEAR_MONTH_DIR" ]; then
        print_status "Creating current month directory: $YEAR_MONTH_DIR"
        mkdir -p "$YEAR_MONTH_DIR"
        print_success "Created $YEAR_MONTH_DIR"
    else
        print_success "Month directory already exists: $YEAR_MONTH_DIR"
    fi
done

# Create a README for the logs directory
README_FILE="$LOGS_DIR/README.md"
if [ ! -f "$README_FILE" ]; then
    print_status "Creating README for logs directory..."
    cat > "$README_FILE" << EOF
# Pynance Logs Directory

This directory contains log files from various Pynance trading systems.

## Directory Structure

\`\`\`
parent-directory/
├── pynance/           # Main repository
│   ├── alpaca/
│   ├── bash/
│   └── ...
└── logs/              # Log files (this directory)
    ├── 01_alpaca/         # Alpaca trading system logs
    │   ├── trendTrader/    # Trend trader script logs
    │   │   ├── 2024-01/   # Year-Month directories
    │   │   │   ├── 2024-01-15-Monday.log
    │   │   │   ├── 2024-01-16-Tuesday.log
    │   │   │   └── ...
    │   │   ├── 2024-02/
    │   │   └── ...
    │   ├── RiskManager/    # Risk manager script logs
    │   │   ├── 2024-01/
    │   │   │   ├── 2024-01-15-Monday.log
    │   │   │   └── ...
    │   │   └── ...
    ├── 02_ibkrSystem/     # Interactive Brokers system logs
    │   ├── 2024-01/
    │   └── ...
    │   └── ...
    └── README.md
\`\`\`

## System Identifiers

- \`01_alpaca\` - Alpaca trading system
  - \`trendTrader\` - Trend trading script
  - \`RiskManager\` - Risk management script

## Log File Naming

Log files are named using the format: \`YYYY-MM-DD-DayOfWeek.log\`

Examples:
- \`2024-01-15-Monday.log\`
- \`2024-01-16-Tuesday.log\`
- \`2024-02-01-Thursday.log\`

## Log Content

Each log file contains:
- Complete output from the respective trading system
- Both stdout and stderr
- Timestamped execution logs
- Trading decisions and results
- Error messages and debugging information

## Maintenance

- Log files are organized by system and year-month for easy navigation
- Old logs can be archived or deleted as needed
- This directory is excluded from version control via .gitignore
- Each system maintains its own log directory structure
EOF
    print_success "Created $README_FILE"
else
    print_success "README already exists at $README_FILE"
fi

print_success "Logging directory setup completed!"
print_status "Logs directory: $LOGS_DIR"
print_status "Current month directory: $YEAR_MONTH_DIR"
