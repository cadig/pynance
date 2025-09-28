#!/bin/bash

# Script to check DST status and remind users about DST transitions
# This helps ensure cron jobs are properly configured for current DST status

set -e  # Exit on any error

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get current timezone
CURRENT_TZ=$(timedatectl show --property=Timezone --value 2>/dev/null || echo "Unknown")

print_header "DST STATUS CHECK"

print_status "Current system timezone: $CURRENT_TZ"

# Function to check if DST is currently active
is_dst_active() {
    local timezone="$1"
    if [ -z "$timezone" ]; then
        timezone="America/New_York"
    fi
    
    local current_month=$(TZ="$timezone" date +%m)
    
    # DST in US: Second Sunday in March to First Sunday in November
    # For simplicity, we'll use month-based detection
    if [ "$current_month" -ge 3 ] && [ "$current_month" -le 10 ]; then
        return 0  # DST is active
    else
        return 1  # DST is not active
    fi
}

# Check DST status for both timezones
print_status "Checking DST status..."

# Check Eastern Time DST
if is_dst_active "America/New_York"; then
    EST_STATUS="EDT (UTC-4)"
    print_success "Eastern Time: DST is active - $EST_STATUS"
else
    EST_STATUS="EST (UTC-5)"
    print_success "Eastern Time: DST is not active - $EST_STATUS"
fi

# Check local timezone DST
if is_dst_active "$CURRENT_TZ"; then
    LOCAL_STATUS="DST active"
    print_success "Local timezone: DST is active - $LOCAL_STATUS"
else
    LOCAL_STATUS="DST not active"
    print_success "Local timezone: DST is not active - $LOCAL_STATUS"
fi

# Calculate time difference
print_status "Calculating time difference..."

# Get current offsets
EST_OFFSET=$(TZ=America/New_York date +%z 2>/dev/null | sed 's/^+//' | sed 's/^\([0-9][0-9]\)\([0-9][0-9]\)$/-(\1*60+\2)/60/' | bc 2>/dev/null || echo "-4")
LOCAL_OFFSET=$(date +%z 2>/dev/null | sed 's/^+//' | sed 's/^\([0-9][0-9]\)\([0-9][0-9]\)$/-(\1*60+\2)/60/' | bc 2>/dev/null || echo "-7")

TIME_DIFF=$((EST_OFFSET - LOCAL_OFFSET))

print_status "Eastern Time offset: UTC$EST_OFFSET"
print_status "Local time offset: UTC$LOCAL_OFFSET"
print_status "Time difference: $TIME_DIFF hours"

# Check if DST transition is coming up
print_status "Checking for upcoming DST transitions..."

CURRENT_MONTH=$(date +%m)
CURRENT_DAY=$(date +%d)

# Check if we're in a DST transition month
if [ "$CURRENT_MONTH" -eq 3 ] || [ "$CURRENT_MONTH" -eq 11 ]; then
    print_warning "DST transition month detected!"
    
    if [ "$CURRENT_MONTH" -eq 3 ]; then
        print_warning "Spring Forward (PST → PDT) typically occurs in March"
        print_status "You may need to re-run setup_cron_jobs.sh after the transition"
    elif [ "$CURRENT_MONTH" -eq 11 ]; then
        print_warning "Fall Back (PDT → PST) typically occurs in November"
        print_status "You may need to re-run setup_cron_jobs.sh after the transition"
    fi
else
    print_success "No DST transition this month"
fi

# Check current cron jobs
print_status "Checking current cron jobs..."

if crontab -l 2>/dev/null | grep -q "run_alpaca_trend.sh\|run_risk_manager.sh"; then
    print_success "Trading cron jobs found:"
    crontab -l 2>/dev/null | grep "run_alpaca_trend.sh\|run_risk_manager.sh" | while read -r line; do
        echo "  $line"
    done
else
    print_warning "No trading cron jobs found"
    print_status "Run ./scripts/setup_cron_jobs.sh to set up cron jobs"
fi

# Recommendations
print_header "RECOMMENDATIONS"

if [ "$CURRENT_MONTH" -eq 3 ] || [ "$CURRENT_MONTH" -eq 11 ]; then
    print_warning "DST transition month - take action:"
    echo "1. Re-run setup script: ./scripts/setup_cron_jobs.sh"
    echo "2. Verify cron job times: crontab -l"
    echo "3. Test the system: ./scripts/run_alpaca_trend.sh"
    echo "4. Monitor logs: ./scripts/view_logs.sh"
else
    print_success "No immediate DST action needed"
    echo "1. Current setup should be working correctly"
    echo "2. Monitor for any timing issues"
    echo "3. Re-run setup script after DST transitions"
fi

# Show next DST transition dates
print_status "Next DST transitions:"
if [ "$CURRENT_MONTH" -le 3 ]; then
    echo "  - Spring Forward: March 2024 (Second Sunday)"
elif [ "$CURRENT_MONTH" -le 11 ]; then
    echo "  - Fall Back: November 2024 (First Sunday)"
else
    echo "  - Spring Forward: March 2025 (Second Sunday)"
fi

print_success "DST status check completed!"
