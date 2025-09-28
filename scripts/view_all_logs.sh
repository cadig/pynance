#!/bin/bash

# Universal script to view logs from all trading systems
# This script helps you navigate and view log files across all systems

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

# Get the logs directory
LOGS_DIR="../logs"

# Check if logs directory exists
if [ ! -d "$LOGS_DIR" ]; then
    print_error "Logs directory not found at $LOGS_DIR"
    print_status "Run setup_logging.sh first to create the logs directory"
    exit 1
fi

# Function to list all systems
list_systems() {
    print_status "Available trading systems:"
    echo
    for system_dir in "$LOGS_DIR"/*; do
        if [ -d "$system_dir" ]; then
            system_name=$(basename "$system_dir")
            log_count=$(find "$system_dir" -name "*.log" -type f | wc -l)
            if [ "$log_count" -gt 0 ]; then
                latest_log=$(find "$system_dir" -name "*.log" -type f | sort -r | head -n 1)
                latest_date=$(basename "$latest_log" | cut -d'-' -f1-3)
                echo -e "${CYAN}$system_name${NC} - ${YELLOW}$log_count${NC} log files (latest: $latest_date)"
                
                # List scripts within the system
                for script_dir in "$system_dir"/*; do
                    if [ -d "$script_dir" ]; then
                        script_name=$(basename "$script_dir")
                        script_log_count=$(find "$script_dir" -name "*.log" -type f | wc -l)
                        if [ "$script_log_count" -gt 0 ]; then
                            echo -e "  ${BLUE}$script_name${NC} - ${YELLOW}$script_log_count${NC} log files"
                        fi
                    fi
                done
            else
                echo -e "${CYAN}$system_name${NC} - ${YELLOW}0${NC} log files"
            fi
        fi
    done
}

# Function to list log files for a specific system
list_system_logs() {
    local system_id="$1"
    local system_dir="$LOGS_DIR/$system_id"
    
    if [ ! -d "$system_dir" ]; then
        print_error "System directory not found: $system_dir"
        return 1
    fi
    
    print_status "Log files for $system_id:"
    echo
    
    # List all scripts within the system
    for script_dir in "$system_dir"/*; do
        if [ -d "$script_dir" ]; then
            script_name=$(basename "$script_dir")
            echo -e "${CYAN}=== $script_name ===${NC}"
            find "$script_dir" -name "*.log" -type f | sort -r | while read -r logfile; do
                filename=$(basename "$logfile")
                filedir=$(dirname "$logfile")
                month_dir=$(basename "$filedir")
                filesize=$(du -h "$logfile" | cut -f1)
                mod_time=$(stat -c %y "$logfile" 2>/dev/null || stat -f %Sm "$logfile" 2>/dev/null)
                echo -e "${BLUE}$month_dir/${GREEN}$filename${NC} (${YELLOW}$filesize${NC}) - $mod_time"
            done
            echo
        fi
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

# Function to view the most recent log from any system
view_latest() {
    local latest_log=$(find "$LOGS_DIR" -name "*.log" -type f | sort -r | head -n 1)
    if [ -n "$latest_log" ]; then
        system_name=$(basename "$(dirname "$(dirname "$latest_log")")")
        print_status "Most recent log from $system_name:"
        view_log "$latest_log"
    else
        print_warning "No log files found in any system"
    fi
}

# Function to view logs from today across all systems
view_today() {
    local today=$(date +%Y-%m-%d)
    local found_logs=false
    
    print_status "Today's log files across all systems:"
    echo
    
    for system_dir in "$LOGS_DIR"/*; do
        if [ -d "$system_dir" ]; then
            system_name=$(basename "$system_dir")
            today_logs=$(find "$system_dir" -name "${today}-*.log" -type f | sort -r)
            if [ -n "$today_logs" ]; then
                found_logs=true
                echo -e "${CYAN}=== $system_name ===${NC}"
                echo "$today_logs" | while read -r logfile; do
                    view_log "$logfile"
                    echo
                done
            fi
        fi
    done
    
    if [ "$found_logs" = false ]; then
        print_warning "No log files found for today ($today) in any system"
    fi
}

# Function to search logs across all systems
search_logs() {
    local search_term="$1"
    if [ -z "$search_term" ]; then
        print_error "Please provide a search term"
        return 1
    fi
    
    print_status "Searching for '$search_term' across all systems..."
    echo
    
    for system_dir in "$LOGS_DIR"/*; do
        if [ -d "$system_dir" ]; then
            system_name=$(basename "$system_dir")
            found_in_system=$(find "$system_dir" -name "*.log" -type f -exec grep -l "$search_term" {} \;)
            if [ -n "$found_in_system" ]; then
                echo -e "${CYAN}=== $system_name ===${NC}"
                echo "$found_in_system" | while read -r logfile; do
                    filename=$(basename "$logfile")
                    filedir=$(dirname "$logfile")
                    month_dir=$(basename "$filedir")
                    echo -e "${GREEN}Found in: $month_dir/$filename${NC}"
                    grep -n "$search_term" "$logfile" | head -5 | sed 's/^/  /'
                    echo
                done
            fi
        fi
    done
}

# Main script logic
case "${1:-systems}" in
    "systems"|"list-systems")
        list_systems
        ;;
    "logs"|"list-logs")
        if [ -z "$2" ]; then
            print_error "Please provide a system ID"
            print_status "Usage: $0 logs <system_id>"
            print_status "Use '$0 systems' to see available systems"
            exit 1
        fi
        list_system_logs "$2"
        ;;
    "latest"|"last")
        view_latest
        ;;
    "today")
        view_today
        ;;
    "view"|"cat")
        if [ -z "$2" ]; then
            print_error "Please provide a log file path"
            print_status "Usage: $0 view <logfile_path>"
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
        echo "Pynance Universal Log Viewer"
        echo
        echo "Usage: $0 [command] [options]"
        echo
        echo "Commands:"
        echo "  systems, list-systems    List all available trading systems"
        echo "  logs <system_id>         List log files for a specific system"
        echo "  latest, last             View the most recent log from any system"
        echo "  today                    View all log files from today across all systems"
        echo "  view <logfile_path>      View a specific log file"
        echo "  search <term>            Search for a term across all systems"
        echo "  help                     Show this help message"
        echo
        echo "Examples:"
        echo "  $0 systems"
        echo "  $0 logs 01_alpaca"
        echo "  $0 latest"
        echo "  $0 view ../logs/01_alpaca/trendTrader/2024-01/2024-01-15-Monday.log"
        echo "  $0 search 'ERROR'"
        ;;
    *)
        print_error "Unknown command: $1"
        print_status "Use '$0 help' for usage information"
        exit 1
        ;;
esac
