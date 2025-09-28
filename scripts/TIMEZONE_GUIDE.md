# Timezone Handling Guide

## Overview
The Pynance trading system automatically adjusts cron job times based on your system's timezone to align with US market hours (Eastern Time).

## Market Hours
- **Market Open**: 9:30 AM EST/EDT
- **Market Close**: 4:00 PM EST/EDT
- **Pre-Market**: 4:00 AM - 9:30 AM EST/EDT
- **After Hours**: 4:00 PM - 8:00 PM EST/EDT

## Script Execution Times
- **TrendTrader**: 8:55 AM EST (before market opens)
- **RiskManager**: 9:00 AM - 4:00 PM EST (during market hours)

## Timezone Detection and Adjustment

### Supported Timezones
The system automatically detects and adjusts for:

1. **Pacific Time (PDT/PST)**
   - PDT: UTC-7 (March - November)
   - PST: UTC-8 (November - March)
   - **Adjustment**: -3 hours from EST

2. **Mountain Time (MDT/MST)**
   - MDT: UTC-6 (March - November)
   - MST: UTC-7 (November - March)
   - **Adjustment**: -2 hours from EST

3. **Central Time (CDT/CST)**
   - CDT: UTC-5 (March - November)
   - CST: UTC-6 (November - March)
   - **Adjustment**: -1 hour from EST

4. **Eastern Time (EDT/EST)**
   - EDT: UTC-4 (March - November)
   - EST: UTC-5 (November - March)
   - **Adjustment**: No adjustment needed

### Example Adjustments

#### Pacific Time (PDT) - Your Current Setup
- **System Timezone**: PDT (UTC-7)
- **Market Timezone**: EDT (UTC-4)
- **Time Difference**: 3 hours behind EST
- **Adjusted Times**:
  - TrendTrader: 5:55 AM PDT (equivalent to 8:55 AM EST)
  - RiskManager: 6:00 AM - 1:00 PM PDT (equivalent to 9:00 AM - 4:00 PM EST)

#### Mountain Time (MDT)
- **System Timezone**: MDT (UTC-6)
- **Market Timezone**: EDT (UTC-4)
- **Time Difference**: 2 hours behind EST
- **Adjusted Times**:
  - TrendTrader: 6:55 AM MDT (equivalent to 8:55 AM EST)
  - RiskManager: 7:00 AM - 2:00 PM MDT (equivalent to 9:00 AM - 4:00 PM EST)

#### Central Time (CDT)
- **System Timezone**: CDT (UTC-5)
- **Market Timezone**: EDT (UTC-4)
- **Time Difference**: 1 hour behind EST
- **Adjusted Times**:
  - TrendTrader: 7:55 AM CDT (equivalent to 8:55 AM EST)
  - RiskManager: 8:00 AM - 3:00 PM CDT (equivalent to 9:00 AM - 4:00 PM EST)

## How It Works

### 1. Timezone Detection
```bash
# The script detects your system timezone
CURRENT_TZ=$(timedatectl show --property=Timezone --value)
```

### 2. Offset Calculation
```bash
# Calculates the difference between your timezone and Eastern Time
TIME_DIFF=$((EST_OFFSET - LOCAL_OFFSET))
```

### 3. Cron Job Adjustment
```bash
# Adjusts the cron job hours based on the time difference
TREND_TRADER_HOUR=$((8 - TIME_DIFF))
RISK_MANAGER_HOURS="${RISK_MANAGER_START}-${RISK_MANAGER_END}"
```

## Verification

### Check Your Timezone
```bash
timedatectl status
```

### Check Cron Jobs
```bash
crontab -l
```

### Test Timezone Conversion
```bash
# Check what time it is in Eastern Time
TZ=America/New_York date
```

## Daylight Saving Time Considerations

### Automatic Handling
The system uses a simplified approach:
- **Summer (March - November)**: Assumes EDT (UTC-4)
- **Winter (November - March)**: Assumes EST (UTC-5)

### Manual Adjustment (if needed)
If you need to account for DST changes, you can manually update the cron jobs:

```bash
# For DST transition periods, you might need to adjust
crontab -e
```

## Troubleshooting

### Common Issues

1. **Wrong Timezone Detected**
   - Check: `timedatectl status`
   - Fix: `sudo timedatectl set-timezone America/Los_Angeles`

2. **Cron Jobs Running at Wrong Time**
   - Check: `crontab -l`
   - Re-run: `./scripts/setup_cron_jobs.sh`

3. **Market Hours Mismatch**
   - Verify: `TZ=America/New_York date`
   - Check: Your system time vs Eastern Time

### Debug Information
The setup script will show:
- Current system timezone
- EST/EDT offset
- Local time offset
- Time difference calculation
- Adjusted cron job times

## Best Practices

### 1. **Use System Timezone**
- Don't change your system timezone
- Let the script handle the conversion
- This is more robust and maintainable

### 2. **Verify After Setup**
- Check the cron job times
- Test with a manual run
- Monitor the logs

### 3. **DST Transitions**
- The script handles most cases automatically
- For critical periods, verify times manually
- Consider using UTC for production systems

## Example Output

### Pacific Time Setup
```
[INFO] Current system timezone: America/Los_Angeles
[INFO] EST offset: UTC-4
[INFO] Local offset: UTC-7
[INFO] Time difference: 3 hours
[INFO] Local time is 3 hours behind EST
[INFO] Adjusted TrendTrader to run at 5:55 local time
[INFO] Adjusted RiskManager to run from 6:00 to 13:00 local time
```

### Final Cron Jobs
```
# TrendTrader - runs at 5:55 AM PDT (8:55 AM EST)
55 5 * * 1-5 cd /path/to/pynance && ./scripts/run_alpaca_trend.sh

# RiskManager - runs 6:00 AM to 1:00 PM PDT (9:00 AM to 4:00 PM EST)
0 6-13 * * 1-5 cd /path/to/pynance && ./scripts/run_risk_manager.sh
```

This ensures your trading system runs at the correct times regardless of your system's timezone!
