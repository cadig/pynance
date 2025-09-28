#!/bin/bash

# Script to set up cron jobs for trendTrader.py and RiskManager.py
# This script checks for existing cron jobs and adds them if they don't exist

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

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_status "Setting up cron jobs for Pynance trading system..."
print_status "Project root: $PROJECT_ROOT"

# Ensure scripts are executable
print_status "Making scripts executable..."
chmod +x "$PROJECT_ROOT/scripts/run_alpaca_trend.sh"
chmod +x "$PROJECT_ROOT/scripts/run_risk_manager.sh"
chmod +x "$PROJECT_ROOT/scripts/setup_logging.sh"
chmod +x "$PROJECT_ROOT/scripts/view_logs.sh"
chmod +x "$PROJECT_ROOT/scripts/view_risk_manager_logs.sh"
chmod +x "$PROJECT_ROOT/scripts/view_all_logs.sh"
print_success "Scripts are now executable"

# Detect system timezone and adjust cron job times accordingly
print_status "Detecting system timezone and adjusting cron job times..."

# Get current timezone
CURRENT_TZ=$(timedatectl show --property=Timezone --value 2>/dev/null || echo "Unknown")
print_status "Current system timezone: $CURRENT_TZ"

# Function to get current EST/EDT timezone offset dynamically
get_est_offset() {
    # Get the current UTC offset for Eastern Time
    local est_offset=$(TZ=America/New_York date +%z 2>/dev/null | sed 's/^+//' | sed 's/^\([0-9][0-9]\)\([0-9][0-9]\)$/-(\1*60+\2)/60/' | bc 2>/dev/null)
    
    if [ -n "$est_offset" ] && [ "$est_offset" != "0" ]; then
        echo "$est_offset"
    else
        # Fallback: determine based on current date
        local current_month=$(date +%m)
        local current_day=$(date +%d)
        
        # DST in US: Second Sunday in March to First Sunday in November
        # For simplicity, we'll use month-based detection
        if [ "$current_month" -ge 3 ] && [ "$current_month" -le 10 ]; then
            # Summer months: EDT (UTC-4)
            echo "-4"
        else
            # Winter months: EST (UTC-5)
            echo "-5"
        fi
    fi
}

# Function to get current local timezone offset dynamically
get_local_offset() {
    # Get the current UTC offset for the local timezone
    local local_offset=$(date +%z 2>/dev/null | sed 's/^+//' | sed 's/^\([0-9][0-9]\)\([0-9][0-9]\)$/-(\1*60+\2)/60/' | bc 2>/dev/null)
    
    if [ -n "$local_offset" ] && [ "$local_offset" != "0" ]; then
        echo "$local_offset"
    else
        # Fallback: determine based on timezone name
        case "$CURRENT_TZ" in
            *"America/Los_Angeles"*|*"PDT"*|*"PST"*)
                # Pacific Time: PDT is UTC-7, PST is UTC-8
                local current_month=$(date +%m)
                if [ "$current_month" -ge 3 ] && [ "$current_month" -le 10 ]; then
                    echo "-7"  # PDT
                else
                    echo "-8"  # PST
                fi
                ;;
            *"America/New_York"*|*"EST"*|*"EDT"*)
                # Eastern Time: EDT is UTC-4, EST is UTC-5
                local current_month=$(date +%m)
                if [ "$current_month" -ge 3 ] && [ "$current_month" -le 10 ]; then
                    echo "-4"  # EDT
                else
                    echo "-5"  # EST
                fi
                ;;
            *"America/Chicago"*|*"CST"*|*"CDT"*)
                # Central Time: CDT is UTC-5, CST is UTC-6
                local current_month=$(date +%m)
                if [ "$current_month" -ge 3 ] && [ "$current_month" -le 10 ]; then
                    echo "-5"  # CDT
                else
                    echo "-6"  # CST
                fi
                ;;
            *"America/Denver"*|*"MST"*|*"MDT"*)
                # Mountain Time: MDT is UTC-6, MST is UTC-7
                local current_month=$(date +%m)
                if [ "$current_month" -ge 3 ] && [ "$current_month" -le 10 ]; then
                    echo "-6"  # MDT
                else
                    echo "-7"  # MST
                fi
                ;;
            *)
                print_warning "Unknown timezone: $CURRENT_TZ"
                print_warning "Using dynamic detection. Please verify cron job times."
                # Try to get offset from date command
                local dynamic_offset=$(date +%z 2>/dev/null | sed 's/^+//' | sed 's/^\([0-9][0-9]\)\([0-9][0-9]\)$/-(\1*60+\2)/60/' | bc 2>/dev/null)
                if [ -n "$dynamic_offset" ]; then
                    echo "$dynamic_offset"
                else
                    echo "-7"  # Default fallback
                fi
                ;;
        esac
    fi
}

# Function to check if DST is currently active
is_dst_active() {
    local timezone="$1"
    if [ -z "$timezone" ]; then
        timezone="America/New_York"
    fi
    
    # Get current time in the specified timezone
    local current_time=$(TZ="$timezone" date +%Y-%m-%d\ %H:%M:%S)
    local current_month=$(TZ="$timezone" date +%m)
    local current_day=$(TZ="$timezone" date +%d)
    
    # DST in US: Second Sunday in March to First Sunday in November
    # For simplicity, we'll use month-based detection
    if [ "$current_month" -ge 3 ] && [ "$current_month" -le 10 ]; then
        return 0  # DST is active
    else
        return 1  # DST is not active
    fi
}

# Function to get DST status information
get_dst_status() {
    local est_dst=$(is_dst_active "America/New_York" && echo "EDT" || echo "EST")
    local local_dst=$(is_dst_active "$CURRENT_TZ" && echo "DST" || echo "STD")
    
    echo "EST/EDT: $est_dst, Local: $local_dst"
}

# Calculate time differences
EST_OFFSET=$(get_est_offset)
LOCAL_OFFSET=$(get_local_offset)

# Calculate the difference between EST and local time
TIME_DIFF=$((EST_OFFSET - LOCAL_OFFSET))

print_status "EST offset: UTC$EST_OFFSET"
print_status "Local offset: UTC$LOCAL_OFFSET"
print_status "Time difference: $TIME_DIFF hours"
print_status "DST Status: $(get_dst_status)"

# Adjust cron job times based on timezone difference
if [ "$TIME_DIFF" -eq 0 ]; then
    # Already in Eastern Time
    TREND_TRADER_HOUR="8"
    RISK_MANAGER_HOURS="9-16"
    print_status "System is in Eastern Time - no adjustment needed"
elif [ "$TIME_DIFF" -gt 0 ]; then
    # Local time is behind EST (e.g., Pacific Time)
    TREND_TRADER_HOUR=$((8 - TIME_DIFF))
    RISK_MANAGER_START=$((9 - TIME_DIFF))
    RISK_MANAGER_END=$((16 - TIME_DIFF))
    RISK_MANAGER_HOURS="${RISK_MANAGER_START}-${RISK_MANAGER_END}"
    print_status "Local time is $TIME_DIFF hours behind EST"
    print_status "Adjusted TrendTrader to run at ${TREND_TRADER_HOUR}:55 local time"
    print_status "Adjusted RiskManager to run from ${RISK_MANAGER_START}:00 to ${RISK_MANAGER_END}:00 local time"
else
    # Local time is ahead of EST (e.g., European time)
    TREND_TRADER_HOUR=$((8 - TIME_DIFF))
    RISK_MANAGER_START=$((9 - TIME_DIFF))
    RISK_MANAGER_END=$((16 - TIME_DIFF))
    RISK_MANAGER_HOURS="${RISK_MANAGER_START}-${RISK_MANAGER_END}"
    print_status "Local time is $((-TIME_DIFF)) hours ahead of EST"
    print_status "Adjusted TrendTrader to run at ${TREND_TRADER_HOUR}:55 local time"
    print_status "Adjusted RiskManager to run from ${RISK_MANAGER_START}:00 to ${RISK_MANAGER_END}:00 local time"
fi

# Define the cron jobs with adjusted times
TREND_TRADER_CRON="55 ${TREND_TRADER_HOUR} * * 1-5 cd $PROJECT_ROOT && ./scripts/run_alpaca_trend.sh"
RISK_MANAGER_CRON="0 ${RISK_MANAGER_HOURS} * * 1-5 cd $PROJECT_ROOT && ./scripts/run_risk_manager.sh"

# Function to check if a cron job exists
cron_job_exists() {
    local job_pattern="$1"
    crontab -l 2>/dev/null | grep -F "$job_pattern" >/dev/null
}

# Function to add a cron job if it doesn't exist
add_cron_job_if_missing() {
    local job="$1"
    local job_name="$2"
    
    if cron_job_exists "$job"; then
        print_success "$job_name cron job already exists"
        return 0
    fi
    
    print_status "Adding $job_name cron job..."
    
    # Get current crontab, add new job, and update
    (crontab -l 2>/dev/null; echo "$job") | crontab -
    
    if [ $? -eq 0 ]; then
        print_success "$job_name cron job added successfully"
    else
        print_error "Failed to add $job_name cron job"
        return 1
    fi
}

# Function to remove old/outdated cron jobs
cleanup_old_cron_jobs() {
    print_status "Checking for old cron jobs to clean up..."
    
    # Look for the old alpacaTrend job pattern
    local old_pattern="alpaca_trend.sh"
    if cron_job_exists "$old_pattern"; then
        print_warning "Found old alpaca_trend.sh cron job. Removing..."
        crontab -l 2>/dev/null | grep -v "$old_pattern" | crontab -
        print_success "Old cron job removed"
    fi
    
    # Look for any other old patterns that might exist
    local old_script_pattern="alpacaTrend"
    if cron_job_exists "$old_script_pattern"; then
        print_warning "Found old alpacaTrend references. Removing..."
        crontab -l 2>/dev/null | grep -v "$old_script_pattern" | crontab -
        print_success "Old references removed"
    fi
}

# Function to display current cron jobs
show_current_cron_jobs() {
    print_status "Current cron jobs:"
    echo
    crontab -l 2>/dev/null | grep -E "(trend|risk|alpaca)" || echo "No trading-related cron jobs found"
    echo
}

# Function to validate cron job format
validate_cron_job() {
    local job="$1"
    local job_name="$2"
    
    # Basic validation - check if the job contains the expected elements
    if [[ "$job" == *"cd $PROJECT_ROOT"* ]] && [[ "$job" == *"scripts/"* ]]; then
        print_success "$job_name cron job format is valid"
        return 0
    else
        print_error "$job_name cron job format is invalid"
        return 1
    fi
}

# Main execution
print_status "Starting cron job setup..."

# Show current cron jobs before making changes
print_status "Current cron jobs before setup:"
show_current_cron_jobs

# Clean up any old cron jobs
cleanup_old_cron_jobs

# Add trendTrader cron job
print_status "Setting up trendTrader cron job..."
print_status "TrendTrader will run at ${TREND_TRADER_HOUR}:55 local time (equivalent to 8:55 AM EST)"
add_cron_job_if_missing "$TREND_TRADER_CRON" "trendTrader"

# Add RiskManager cron job
print_status "Setting up RiskManager cron job..."
print_status "RiskManager will run every hour from ${RISK_MANAGER_START}:00 to ${RISK_MANAGER_END}:00 local time (equivalent to 9 AM - 4 PM EST)"
add_cron_job_if_missing "$RISK_MANAGER_CRON" "RiskManager"

# Validate the cron jobs
print_status "Validating cron jobs..."
validate_cron_job "$TREND_TRADER_CRON" "trendTrader"
validate_cron_job "$RISK_MANAGER_CRON" "RiskManager"

# Show final cron jobs
print_status "Final cron jobs after setup:"
show_current_cron_jobs

# Additional setup recommendations
print_status "Additional setup recommendations:"
echo
echo "1. Ensure your system timezone is set correctly (EST/EDT for US market hours)"
echo "2. Test the scripts manually before relying on cron jobs:"
echo "   - Test trendTrader: cd $PROJECT_ROOT && ./scripts/run_alpaca_trend.sh"
echo "   - Test RiskManager: cd $PROJECT_ROOT && ./scripts/run_risk_manager.sh"
echo "3. Monitor logs to ensure scripts are running correctly:"
echo "   - View trendTrader logs: ./scripts/view_logs.sh"
echo "   - View RiskManager logs: ./scripts/view_risk_manager_logs.sh"
echo "   - View all logs: ./scripts/view_all_logs.sh"
echo "4. Set up log rotation if needed to prevent disk space issues"
echo

print_success "Cron job setup completed!"
print_status "Your trading system is now configured to run automatically:"
print_status "  - trendTrader: Daily at ${TREND_TRADER_HOUR}:55 local time (equivalent to 8:55 AM EST/EDT)"
print_status "  - RiskManager: Every hour from ${RISK_MANAGER_START}:00 to ${RISK_MANAGER_END}:00 local time (equivalent to 9 AM - 4 PM EST/EDT)"
print_status "  - System timezone: $CURRENT_TZ"
print_status "  - Market timezone: Eastern Time (EST/EDT)"

# DST transition warning
print_warning "IMPORTANT: Daylight Saving Time Transitions"
print_status "DST transitions occur on:"
print_status "  - Spring Forward: Second Sunday in March (2:00 AM → 3:00 AM)"
print_status "  - Fall Back: First Sunday in November (2:00 AM → 1:00 AM)"
print_warning "You may need to re-run this script after DST transitions to ensure correct timing."
print_status "To re-run: ./scripts/setup_cron_jobs.sh"
