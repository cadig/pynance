#!/usr/bin/env python3
"""
Collects heartbeat files and builds a unified server-health.json.
Checks staleness based on systems.json configuration.
"""

import json
import glob
import os
import socket
from datetime import datetime, timezone, timedelta
from pathlib import Path


def is_weekday(dt: datetime) -> bool:
    return dt.weekday() < 5  # Mon=0, Fri=4


def check_staleness(last_run_str: str, stale_after_hours: float, weekdays_only: bool) -> bool:
    """Returns True if the process is stale (hasn't run when expected)."""
    now = datetime.now(timezone.utc)

    try:
        last_run = datetime.fromisoformat(last_run_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return True  # Can't parse = treat as stale

    elapsed = now - last_run
    elapsed_hours = elapsed.total_seconds() / 3600

    if weekdays_only:
        # Don't flag as stale on weekends if last run was Friday
        if not is_weekday(now):
            # It's weekend — check if last run was the most recent Friday
            days_since_friday = (now.weekday() - 4) % 7
            friday_cutoff = now - timedelta(days=days_since_friday, hours=now.hour, minutes=now.minute)
            friday_cutoff = friday_cutoff.replace(hour=22, minute=0, second=0)  # End of trading day UTC
            if last_run >= friday_cutoff - timedelta(hours=stale_after_hours):
                return False
            # If last run was before Friday's expected window, it's stale
            return elapsed_hours > (stale_after_hours + (days_since_friday * 24))

    return elapsed_hours > stale_after_hours


def main():
    script_dir = Path(__file__).parent
    heartbeat_dir = script_dir / 'heartbeats'
    systems_config_path = script_dir / 'systems.json'
    output_path = script_dir / 'server-health.json'

    # Load systems config
    with open(systems_config_path) as f:
        config = json.load(f)

    server_name = config.get('server_name', socket.gethostname())

    # Load all heartbeat files
    heartbeats = {}
    for hb_file in glob.glob(str(heartbeat_dir / '*.json')):
        try:
            with open(hb_file) as f:
                hb = json.load(f)
            key = f"{hb['system']}__{hb['process']}"
            heartbeats[key] = hb
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: skipping malformed heartbeat file {hb_file}: {e}")

    # Build output
    now = datetime.now(timezone.utc)
    all_healthy = True
    systems_output = {}

    for system_id, system_config in config.get('systems', {}).items():
        system_healthy = True
        processes_output = {}

        for process_id, process_config in system_config.get('processes', {}).items():
            key = f"{system_id}__{process_id}"
            hb = heartbeats.get(key)

            if hb is None:
                # No heartbeat file — process has never reported
                processes_output[process_id] = {
                    'label': process_config['label'],
                    'status': 'unknown',
                    'last_run': None,
                    'exit_code': None,
                    'schedule': process_config['schedule'],
                    'stale': True,
                    'last_error': None,
                }
                system_healthy = False
            else:
                stale = check_staleness(
                    hb.get('last_run', ''),
                    process_config.get('stale_after_hours', 24),
                    process_config.get('weekdays_only', False),
                )

                status = hb.get('status', 'unknown')
                if status == 'ok' and stale:
                    status = 'stale'

                if status != 'ok':
                    system_healthy = False

                processes_output[process_id] = {
                    'label': process_config['label'],
                    'status': status,
                    'last_run': hb.get('last_run'),
                    'exit_code': hb.get('exit_code'),
                    'schedule': process_config['schedule'],
                    'stale': stale,
                    'last_error': hb.get('last_error'),
                }

        if not system_healthy:
            all_healthy = False

        systems_output[system_id] = {
            'label': system_config['label'],
            'healthy': system_healthy,
            'processes': processes_output,
        }

    output = {
        'collected_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'server': server_name,
        'all_healthy': all_healthy,
        'systems': systems_output,
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    status_str = 'HEALTHY' if all_healthy else 'ISSUES DETECTED'
    print(f"[HEALTH] Collected status: {status_str} -> {output_path}")


if __name__ == '__main__':
    main()
