# Daylight Saving Time (DST) Handling Guide

## Overview
The Pynance trading system now includes improved DST handling, but requires some manual attention during DST transition periods.

## How DST Affects Your System

### DST Transition Dates
- **Spring Forward**: Second Sunday in March (2:00 AM → 3:00 AM)
- **Fall Back**: First Sunday in November (2:00 AM → 1:00 AM)

### Your PDT System During DST Transitions

#### Spring Forward (March)
- **Before**: PST (UTC-8) → **After**: PDT (UTC-7)
- **Time Difference Change**: 3 hours behind EST → 3 hours behind EDT
- **Cron Jobs**: No change needed (same 3-hour difference)

#### Fall Back (November)
- **Before**: PDT (UTC-7) → **After**: PST (UTC-8)
- **Time Difference Change**: 3 hours behind EDT → 4 hours behind EST
- **Cron Jobs**: Need to be updated

## Current DST Handling

### ✅ **What the Script Does**
1. **Detects current DST status** for both your timezone and Eastern Time
2. **Calculates correct offsets** based on current DST status
3. **Shows DST status** in the output
4. **Warns about DST transitions**

### ⚠️ **What You Need to Do**
1. **Re-run the setup script** after DST transitions
2. **Verify cron job times** are correct
3. **Monitor the first few runs** after transitions

## DST Transition Checklist

### Before DST Transitions
1. **Note current cron job times**:
   ```bash
   crontab -l
   ```

2. **Check current DST status**:
   ```bash
   ./bash/setup_cron_jobs.sh
   ```

### After DST Transitions
1. **Re-run the setup script**:
   ```bash
   ./bash/setup_cron_jobs.sh
   ```

2. **Verify new cron job times**:
   ```bash
   crontab -l
   ```

3. **Test the system**:
   ```bash
   # Test TrendTrader
   ./bash/run_alpaca_trend.sh
   
   # Test RiskManager
   ./bash/run_risk_manager.sh
   ```

## Example DST Transitions

### Spring Forward (March 2024)
**Before (PST → PDT)**:
```bash
# TrendTrader: 5:55 AM PST (8:55 AM EST)
55 5 * * 1-5 cd /path/to/pynance && ./bash/run_alpaca_trend.sh

# RiskManager: 6:00 AM - 1:00 PM PST (9:00 AM - 4:00 PM EST)
0 6-13 * * 1-5 cd /path/to/pynance && ./bash/run_risk_manager.sh
```

**After (PDT)**:
```bash
# TrendTrader: 5:55 AM PDT (8:55 AM EDT)
55 5 * * 1-5 cd /path/to/pynance && ./bash/run_alpaca_trend.sh

# RiskManager: 6:00 AM - 1:00 PM PDT (9:00 AM - 4:00 PM EDT)
0 6-13 * * 1-5 cd /path/to/pynance && ./bash/run_risk_manager.sh
```

### Fall Back (November 2024)
**Before (PDT → PST)**:
```bash
# TrendTrader: 5:55 AM PDT (8:55 AM EDT)
55 5 * * 1-5 cd /path/to/pynance && ./bash/run_alpaca_trend.sh

# RiskManager: 6:00 AM - 1:00 PM PDT (9:00 AM - 4:00 PM EDT)
0 6-13 * * 1-5 cd /path/to/pynance && ./bash/run_risk_manager.sh
```

**After (PST)**:
```bash
# TrendTrader: 4:55 AM PST (8:55 AM EST)
55 4 * * 1-5 cd /path/to/pynance && ./bash/run_alpaca_trend.sh

# RiskManager: 5:00 AM - 12:00 PM PST (9:00 AM - 4:00 PM EST)
0 5-12 * * 1-5 cd /path/to/pynance && ./bash/run_risk_manager.sh
```

## Automated DST Handling (Future Enhancement)

### Current Limitations
- **Manual re-run required** after DST transitions
- **No automatic detection** of transition dates
- **Simplified month-based detection** (not exact dates)

### Potential Improvements
1. **Exact DST date calculation** (Second Sunday in March, First Sunday in November)
2. **Automatic cron job updates** on transition dates
3. **Pre-transition warnings** and notifications
4. **Transition date monitoring** and alerts

## Monitoring DST Transitions

### Check Current Status
```bash
# Check system timezone
timedatectl status

# Check Eastern Time
TZ=America/New_York date

# Check your local time
date

# Check DST status
./bash/setup_cron_jobs.sh
```

### Verify Market Hours
```bash
# Check if it's market hours in Eastern Time
TZ=America/New_York date
# Should show 9:30 AM - 4:00 PM EDT/EST for market hours
```

## Troubleshooting DST Issues

### Common Problems
1. **Scripts running at wrong time** after DST transition
2. **Cron jobs not updated** after timezone change
3. **Market hours mismatch** due to incorrect offsets

### Solutions
1. **Re-run setup script**:
   ```bash
   ./bash/setup_cron_jobs.sh
   ```

2. **Check timezone settings**:
   ```bash
   timedatectl status
   ```

3. **Verify market hours**:
   ```bash
   TZ=America/New_York date
   ```

4. **Test manually**:
   ```bash
   ./bash/run_alpaca_trend.sh
   ./bash/run_risk_manager.sh
   ```

## Best Practices

### 1. **Pre-Transition Preparation**
- Note current cron job times
- Test the setup script
- Plan for manual intervention

### 2. **Post-Transition Verification**
- Re-run setup script immediately
- Verify new cron job times
- Test system functionality
- Monitor first few runs

### 3. **Ongoing Monitoring**
- Check system timezone regularly
- Verify market hours alignment
- Monitor log files for timing issues

## Summary

### ✅ **What's Automated**
- DST status detection
- Timezone offset calculation
- Cron job time adjustment
- Status reporting

### ⚠️ **What's Manual**
- Re-running setup after DST transitions
- Verifying correct timing
- Testing after transitions

### 🔄 **Required Actions**
1. **Re-run setup script** after DST transitions
2. **Verify cron job times** are correct
3. **Test system** after transitions
4. **Monitor logs** for timing issues

The system handles DST much better now, but still requires manual intervention during transition periods to ensure optimal timing!
