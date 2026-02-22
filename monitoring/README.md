# Server Health Monitoring

Lightweight heartbeat system that reports whether cron-scheduled trading processes are running successfully. Pushes status to GitHub Pages so you can monitor the algo trading server from any browser.

## How It Works

1. **Each cron job reports a heartbeat** — `report_heartbeat.sh` is called at the end of `run_alpaca_trend.sh` and `run_risk_manager.sh`, writing a JSON file to `heartbeats/` with status, exit code, and error log tail on failure.

2. **Collector aggregates and pushes** — `collect_and_push.sh` runs every 30 minutes via cron, calls `collect_health.py` to merge all heartbeat files into a single `server-health.json`, checks staleness (weekend-aware), and pushes to gh-pages via a temporary git worktree.

3. **Dashboard renders status** — `docs/server-health.html` fetches `server-health.json` and shows color-coded status cards (green/yellow/red) with time-ago display and error details. Auto-refreshes every 5 minutes. Accessible from the "Server Health" button on the main regime analysis page.

## Files

| File | Purpose |
|------|---------|
| `report_heartbeat.sh` | Called by process run scripts to write per-process heartbeat JSON |
| `collect_health.py` | Aggregates heartbeats, checks staleness, builds `server-health.json` |
| `collect_and_push.sh` | Runs collector then pushes to gh-pages |
| `systems.json` | Defines systems, processes, schedules, and staleness thresholds |
| `heartbeats/` | Runtime directory for per-process JSON files (gitignored) |
| `server-health.json` | Aggregated output (gitignored, lives on gh-pages) |

## Adding a New System

1. Add an entry to `systems.json`:
```json
{
  "new_system": {
    "label": "My New System",
    "processes": {
      "main_job": {
        "label": "Main Job",
        "schedule": "Weekdays 9:00 AM EST",
        "stale_after_hours": 25,
        "weekdays_only": true
      }
    }
  }
}
```

2. Call `report_heartbeat.sh` from the process run script:
```bash
./monitoring/report_heartbeat.sh "new_system" "main_job" "$EXIT_CODE" "$LOG_FILE"
```

The new system will automatically appear on the dashboard.

## Setup

Run `./bash/setup_cron_jobs.sh` on the server to register the collector cron job (every 30 min). The server needs push access to the repo for gh-pages updates.
