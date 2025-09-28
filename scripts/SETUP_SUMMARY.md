# Pynance Machine Setup Summary

## Overview
I've created comprehensive scripts to set up your machine for running the Pynance trading system with proper cron job scheduling.

## New Scripts Created

### 1. `setup_cron_jobs.sh`
- **Purpose**: Sets up cron jobs for trendTrader and RiskManager
- **Features**:
  - Checks for existing cron jobs
  - Adds missing cron jobs
  - Cleans up old/outdated cron jobs
  - Validates cron job format
  - Shows current cron jobs

### 2. `setup_machine.sh`
- **Purpose**: Comprehensive machine setup script
- **Features**:
  - Checks system requirements
  - Sets up conda environment
  - Creates logging directories
  - Configures cron jobs
  - Verifies configuration
  - Tests the setup
  - Shows next steps

### 3. `CRON_SETUP_GUIDE.md`
- **Purpose**: Detailed guide for cron job management
- **Features**:
  - Cron job schedules explained
  - Manual cron management
  - Troubleshooting guide
  - Security considerations
  - Maintenance tips

## Cron Job Schedules

### TrendTrader
- **Schedule**: `55 8 * * 1-5` (8:55 AM EST, Monday-Friday)
- **Purpose**: Runs before market opens
- **Script**: `./scripts/run_alpaca_trend.sh`

### RiskManager
- **Schedule**: `0 9-16 * * 1-5` (Every hour 9 AM - 4 PM EST, Monday-Friday)
- **Purpose**: Runs during market hours
- **Script**: `./scripts/run_risk_manager.sh`

## Usage

### Quick Setup (Recommended)
```bash
# Run the comprehensive setup
./scripts/setup_machine.sh
```

### Individual Setup Steps
```bash
# 1. Setup conda environment
./scripts/check_conda_environment.sh

# 2. Setup logging directories
./scripts/setup_logging.sh

# 3. Setup cron jobs
./scripts/setup_cron_jobs.sh
```

## What the Scripts Do

### Automatic Cleanup
- Removes old `alpaca_trend.sh` cron jobs
- Removes old `alpacaTrend` references
- Updates to new script names and structure

### Smart Detection
- Checks if cron jobs already exist
- Only adds missing cron jobs
- Preserves existing cron jobs for other systems

### Validation
- Validates cron job format
- Checks script executability
- Verifies directory structure
- Tests script syntax

## Your Current Cron Job
```
55 12 * * 1-5 cd /home/jjcadiga/github/pynance && ./scripts/run_alpaca_trend.sh
```

## New Cron Jobs (After Setup)
```
# TrendTrader - before market opens
55 8 * * 1-5 cd /home/jjcadiga/github/pynance && ./scripts/run_alpaca_trend.sh

# RiskManager - during market hours
0 9-16 * * 1-5 cd /home/jjcadiga/github/pynance && ./scripts/run_risk_manager.sh
```

## Key Features

### 1. **Automatic Detection**
- Detects existing cron jobs
- Only adds what's missing
- Preserves other cron jobs

### 2. **Smart Scheduling**
- TrendTrader: 8:55 AM EST (before market opens)
- RiskManager: Every hour 9 AM - 4 PM EST (during market hours)

### 3. **Comprehensive Setup**
- Environment setup
- Logging structure
- Cron job configuration
- Validation and testing

### 4. **Error Handling**
- Checks system requirements
- Validates configurations
- Provides clear error messages
- Offers troubleshooting guidance

## Configuration Requirements

### Required Config Files
The system requires two configuration files in the `../config/` directory:

1. **alpaca-config.ini** - Alpaca trading API credentials
   ```ini
   [paper]
   API_KEY = your_api_key_here
   API_SECRET = your_api_secret_here
   
   [live]
   API_KEY = your_live_api_key_here
   API_SECRET = your_live_api_secret_here
   ```

2. **finnhub-config.ini** - Finnhub API credentials (for earnings data)
   ```ini
   [finnhub]
   API_KEY = your_finnhub_api_key_here
   ```

## Next Steps

1. **Pull the latest changes** from your repository
2. **Run the setup script**: `./scripts/setup_machine.sh`
3. **Configure your API credentials** in both config files
4. **Test the system** manually before relying on cron jobs
5. **Monitor the logs** to ensure everything is working

## Benefits

- **Automated Setup**: One script sets up everything
- **Smart Detection**: Won't duplicate existing cron jobs
- **Proper Scheduling**: Optimized for market hours
- **Easy Maintenance**: Clear structure and documentation
- **Troubleshooting**: Comprehensive guides and error handling

## Files Created/Modified

### New Files
- `scripts/setup_cron_jobs.sh`
- `scripts/setup_machine.sh`
- `scripts/CRON_SETUP_GUIDE.md`
- `scripts/SETUP_SUMMARY.md`

### Updated Files
- All existing scripts updated for new structure
- Logging structure updated
- Documentation updated

Your trading system is now ready for automated operation with proper scheduling!
