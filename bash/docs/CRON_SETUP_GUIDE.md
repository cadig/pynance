# Cron Job Setup Guide

## Overview
This guide explains the cron job setup for the Pynance trading system.

## Cron Jobs Created

### 1. TrendTrader (Daily)
- **Schedule**: `55 8 * * 1-5`
- **Time**: 8:55 AM EST (before market opens at 9:30 AM EST)
- **Days**: Monday through Friday
- **Command**: `cd /path/to/pynance && ./bash/run_alpaca_trend.sh`

### 2. RiskManager (Hourly)
- **Schedule**: `0 9-16 * * 1-5`
- **Time**: Every hour from 9:00 AM to 4:00 PM EST
- **Days**: Monday through Friday
- **Command**: `cd /path/to/pynance && ./bash/run_risk_manager.sh`

## Setup Scripts

### Quick Setup
```bash
# Run the comprehensive machine setup
./bash/setup_machine.sh
```

### Individual Setup Steps
```bash
# 1. Setup conda environment
./bash/setup/check_conda_environment.sh

# 2. Setup logging directories
./bash/setup/setup_logging.sh

# 3. Setup cron jobs
./bash/setup_cron_jobs.sh
```

## Manual Cron Job Management

### View Current Cron Jobs
```bash
crontab -l
```

### Edit Cron Jobs
```bash
crontab -e
```

### Remove All Cron Jobs
```bash
crontab -r
```

## Cron Job Examples

### Your Current Job (will be updated)
```
55 12 * * 1-5 cd /home/jjcadiga/github/pynance && ./bash/run_alpaca_trend.sh
```

### New Jobs (after running setup)
```
# TrendTrader - runs before market opens
55 8 * * 1-5 cd /home/jjcadiga/github/pynance && ./bash/run_alpaca_trend.sh

# RiskManager - runs every hour during market hours
0 9-16 * * 1-5 cd /home/jjcadiga/github/pynance && ./bash/run_risk_manager.sh
```

## Timezone Considerations

### EST/EDT (Eastern Time)
- **EST**: Eastern Standard Time (UTC-5)
- **EDT**: Eastern Daylight Time (UTC-4)
- Market hours: 9:30 AM - 4:00 PM EST/EDT

### Setting System Timezone
```bash
# Check current timezone
timedatectl status

# Set timezone (Linux)
sudo timedatectl set-timezone America/New_York

# Set timezone (macOS)
sudo systemsetup -settimezone America/New_York
```

## Monitoring and Troubleshooting

### Check Cron Job Execution
```bash
# View cron logs (Linux)
grep CRON /var/log/syslog

# View cron logs (macOS)
grep CRON /var/log/system.log

# View recent cron activity
grep "$(date +%b\ %d)" /var/log/syslog | grep CRON
```

### Test Scripts Manually
```bash
# Test trendTrader
cd /path/to/pynance
./bash/run_alpaca_trend.sh

# Test RiskManager
cd /path/to/pynance
./bash/run_risk_manager.sh
```

### View Logs
```bash
# View trendTrader logs
./bash/view_logs.sh

# View RiskManager logs
./bash/logs/view_risk_manager_logs.sh

# View all logs
./bash/logs/view_all_logs.sh
```

## Log File Locations

### Directory Structure
```
logs/
├── 01_alpaca/
│   ├── trendTrader/
│   │   ├── 2024-01/
│   │   │   ├── 2024-01-15-Monday.log
│   │   │   └── ...
│   │   └── ...
│   └── RiskManager/
│       ├── 2024-01/
│       │   ├── 2024-01-15-Monday.log
│       │   └── ...
│       └── ...
└── README.md
```

### Log File Naming
- Format: `YYYY-MM-DD-DayOfWeek.log`
- Examples: `2024-01-15-Monday.log`, `2024-01-16-Tuesday.log`

## Security Considerations

### File Permissions
```bash
# Ensure scripts are executable
chmod +x bash/*.sh

# Protect config files
chmod 600 config/alpaca-config.ini
```

### Cron Job Security
- Cron jobs run with the user's permissions
- Ensure API keys are stored securely
- Monitor logs for any unauthorized access

## Troubleshooting Common Issues

### 1. Scripts Not Running
- Check if scripts are executable: `ls -la bash/`
- Verify paths in cron jobs are correct
- Check system timezone settings

### 2. Permission Issues
- Ensure user has execute permissions
- Check file ownership
- Verify directory permissions

### 3. Environment Issues
- Conda environment not activated in cron
- Python path issues
- Missing dependencies

### 4. Log Issues
- Check if log directories exist
- Verify write permissions
- Monitor disk space

## Maintenance

### Regular Tasks
1. Monitor log file sizes
2. Check for errors in logs
3. Verify cron jobs are running
4. Update API credentials as needed
5. Review and rotate old logs

### Log Rotation
```bash
# Example logrotate configuration
# /etc/logrotate.d/pynance
/path/to/logs/*/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
```

## Support

For issues or questions:
1. Check the logs first
2. Verify cron job syntax
3. Test scripts manually
4. Review system timezone
5. Check file permissions
