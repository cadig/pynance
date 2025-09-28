#!/bin/bash

# Script to view recent logs from RiskManager.py
# This script helps you navigate and view log files

set -e  # Exit on any error

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get the logs directory
LOGS_DIR="../logs"
SYSTEM_ID="01_alpaca"
SCRIPT_ID="RiskManager"

# Check if logs directory exists
if [ ! -d "$LOGS_DIR" ]; then
    print_error "Logs directory not found at $LOGS_DIR"
    print_status "Run bash/setup/setup_logging.sh first to create the logs directory"
    exit 1
fi

# Check if system directory exists
SYSTEM_DIR="$LOGS_DIR/$SYSTEM_ID"
if [ ! -d "$SYSTEM_DIR" ]; then
    print_error "System directory not found at $SYSTEM_DIR"
    print_status "Run bash/setup/setup_logging.sh first to create the system directories"
    exit 1
fi

# Check if script directory exists
SCRIPT_DIR="$SYSTEM_DIR/$SCRIPT_ID"
if [ ! -d "$SCRIPT_DIR" ]; then
    print_error "Script directory not found at $SCRIPT_DIR"
    print_status "Run bash/setup/setup_logging.sh first to create the script directories"
    exit 1
fi

# Function to list available log files
list_logs() {
    print_status "Available log files for $SYSTEM_ID/$SCRIPT_ID:"
    echo
    find "$SCRIPT_DIR" -name "*.log" -type f | sort -r | while read -r logfile; do
        filename=$(basename "$logfile")
        filedir=$(dirname "$logfile")
        month_dir=$(basename "$filedir")
        filesize=$(du -h "$logfile" | cut -f1)
        mod_time=$(stat -c %y "$logfile" 2>/dev/null || stat -f %Sm "$logfile" 2>/dev/null)
        echo -e "${BLUE}$month_dir/${GREEN}$filename${NC} (${YELLOW}$filesize${NC}) - $mod_time"
    done
}

# Function to view a specific log file
view_log() {
    local logfile="$1"
    if [ -f "$logfile" ]; then
        print_status "Viewing log file: $logfile"
        echo "=========================================="
        cat "$logfile"
        echo "=========================================="
    else
        print_error "Log file not found: $logfile"
    fi
}

# Function to view the most recent log
view_latest() {
    local latest_log=$(find "$SCRIPT_DIR" -name "*.log" -type f | sort -r | head -n 1)
    if [ -n "$latest_log" ]; then
        view_log "$latest_log"
    else
        print_warning "No log files found for $SYSTEM_ID/$SCRIPT_ID"
    fi
}

# Function to view logs from today
view_today() {
    local today=$(date +%Y-%m-%d)
    local today_logs=$(find "$SCRIPT_DIR" -name "${today}-*.log" -type f | sort -r)
    if [ -n "$today_logs" ]; then
        print_status "Today's log files for $SYSTEM_ID/$SCRIPT_ID:"
        echo "$today_logs" | while read -r logfile; do
            view_log "$logfile"
            echo
        done
    else
        print_warning "No log files found for today ($today) in $SYSTEM_ID/$SCRIPT_ID"
    fi
}

# Function to search logs
search_logs() {
    local search_term="$1"
    if [ -z "$search_term" ]; then
        print_error "Please provide a search term"
        return 1
    fi
    
    print_status "Searching for '$search_term' in $SYSTEM_ID/$SCRIPT_ID log files..."
    find "$SCRIPT_DIR" -name "*.log" -type f -exec grep -l "$search_term" {} \; | while read -r logfile; do
        filename=$(basename "$logfile")
        filedir=$(dirname "$logfile")
        month_dir=$(basename "$filedir")
        echo -e "${GREEN}Found in: $month_dir/$filename${NC}"
        grep -n "$search_term" "$logfile" | head -5 | sed 's/^/  /'
        echo
    done
}

# Main script logic
case "${1:-list}" in
    "list"|"ls")
        list_logs
        ;;
    "latest"|"last")
        view_latest
        ;;
    "today")
        view_today
        ;;
    "view"|"cat")
        if [ -z "$2" ]; then
            print_error "Please provide a log filename"
            print_status "Usage: $0 view <logfile>"
            print_status "Use '$0 list' to see available log files"
            exit 1
        fi
        view_log "$2"
        ;;
    "search"|"grep")
        if [ -z "$2" ]; then
            print_error "Please provide a search term"
            print_status "Usage: $0 search <term>"
            exit 1
        fi
        search_logs "$2"
        ;;
    "help"|"-h"|"--help")
        echo "Pynance Risk Manager Log Viewer"
        echo
        echo "Usage: $0 [command] [options]"
        echo
        echo "Commands:"
        echo "  list, ls              List all available log files"
        echo "  latest, last          View the most recent log file"
        echo "  today                 View all log files from today"
        echo "  view <filename>       View a specific log file"
        echo "  search <term>         Search for a term in all log files"
        echo "  help                  Show this help message"
        echo
        echo "Examples:"
        echo "  $0 list"
        echo "  $0 latest"
        echo "  $0 view 2024-01-15-Monday.log"
        echo "  $0 search 'ERROR'"
        ;;
    *)
        print_error "Unknown command: $1"
        print_status "Use '$0 help' for usage information"
        exit 1
        ;;
esac
