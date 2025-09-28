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

# Define the cron jobs
# TrendTrader: Run once per day at 8:55 AM EST (before market opens at 9:30 AM EST)
TREND_TRADER_CRON="55 8 * * 1-5 cd $PROJECT_ROOT && ./scripts/run_alpaca_trend.sh"

# RiskManager: Run every hour during market hours (9 AM - 4 PM EST, Monday-Friday)
# This runs at 9:00, 10:00, 11:00, 12:00, 1:00, 2:00, 3:00, 4:00 PM EST
RISK_MANAGER_CRON="0 9-16 * * 1-5 cd $PROJECT_ROOT && ./scripts/run_risk_manager.sh"

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
print_status "TrendTrader will run at 8:55 AM EST (before market opens)"
add_cron_job_if_missing "$TREND_TRADER_CRON" "trendTrader"

# Add RiskManager cron job
print_status "Setting up RiskManager cron job..."
print_status "RiskManager will run every hour from 9 AM to 4 PM EST during market hours"
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
print_status "  - trendTrader: Daily at 8:55 AM EST (before market opens)"
print_status "  - RiskManager: Every hour from 9 AM to 4 PM EST (during market hours)"
