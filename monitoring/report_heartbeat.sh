#!/bin/bash

# Reports a heartbeat for a process after it runs.
# Usage: report_heartbeat.sh <system> <process> <exit_code> [log_file]
#
# Example:
#   ./monitoring/report_heartbeat.sh alpaca trend_trader 0 /path/to/logfile.log
#   ./monitoring/report_heartbeat.sh alpaca risk_manager 1 /path/to/logfile.log

SYSTEM="$1"
PROCESS="$2"
EXIT_CODE="$3"
LOG_FILE="$4"

if [ -z "$SYSTEM" ] || [ -z "$PROCESS" ] || [ -z "$EXIT_CODE" ]; then
    echo "[HEARTBEAT] Usage: report_heartbeat.sh <system> <process> <exit_code> [log_file]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEARTBEAT_DIR="$SCRIPT_DIR/heartbeats"
mkdir -p "$HEARTBEAT_DIR"

HEARTBEAT_FILE="$HEARTBEAT_DIR/${SYSTEM}__${PROCESS}.json"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Determine status
if [ "$EXIT_CODE" -eq 0 ]; then
    STATUS="ok"
else
    STATUS="error"
fi

# Capture last 20 lines of log on error
LAST_ERROR="null"
if [ "$STATUS" = "error" ] && [ -n "$LOG_FILE" ] && [ -f "$LOG_FILE" ]; then
    # Escape JSON special characters and capture last 20 lines
    LAST_ERROR=$(tail -20 "$LOG_FILE" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo '"unable to read log"')
fi

# Write heartbeat JSON
cat > "$HEARTBEAT_FILE" << EOF
{
  "system": "$SYSTEM",
  "process": "$PROCESS",
  "status": "$STATUS",
  "last_run": "$TIMESTAMP",
  "exit_code": $EXIT_CODE,
  "last_error": $LAST_ERROR
}
EOF

echo "[HEARTBEAT] Reported: $SYSTEM/$PROCESS status=$STATUS exit_code=$EXIT_CODE"
