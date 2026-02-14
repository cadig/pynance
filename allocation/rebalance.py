"""
Rebalance signal and daily summary generator.

Compares today's allocation results against the most recent historical entry
to detect meaningful changes. Produces a human-readable summary:
- "No action today" when nothing changed
- Specific buy/sell instructions when ETFs enter/leave sleeves
- Regime shift alerts when the regime changes

Reads from docs/history/allocation-log.jsonl (produced by B+.1 archiving).
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load_previous_result(docs_dir: Path) -> Optional[Dict]:
    """
    Load the most recent entry from the JSONL history log.

    Returns None if no history exists or the file has fewer than 2 entries
    (the current run's entry is the last line).
    """
    log_path = docs_dir / 'history' / 'allocation-log.jsonl'
    if not log_path.exists():
        logging.info("No history log found — skipping change detection")
        return None

    lines = []
    try:
        with open(log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(line)
    except Exception as e:
        logging.warning(f"Failed to read history log: {e}")
        return None

    # Need at least 2 entries: previous + current (current was just appended)
    if len(lines) < 2:
        logging.info("History log has fewer than 2 entries — no previous to compare")
        return None

    try:
        return json.loads(lines[-2])  # second-to-last = previous day
    except json.JSONDecodeError as e:
        logging.warning(f"Failed to parse previous history entry: {e}")
        return None


def extract_sleeve_etfs(result: Dict) -> Dict[str, set]:
    """Extract the set of selected ETF symbols from each sleeve."""
    etfs_by_sleeve = {}
    for sleeve_name, sleeve_data in result.get('sleeve_analyses', {}).items():
        selected = sleeve_data.get('selected_etfs', [])
        symbols = set()
        for etf in selected:
            if isinstance(etf, dict):
                sym = etf.get('symbol')
                if sym:
                    symbols.add(sym)
        etfs_by_sleeve[sleeve_name] = symbols
    return etfs_by_sleeve


def detect_changes(current: Dict, previous: Dict) -> List[str]:
    """
    Compare current results against previous and return a list of change descriptions.

    Detects:
    - Regime shifts (background_color change)
    - ETFs entering or leaving a sleeve
    - Allocation percentage changes > 2%
    """
    changes = []

    # Regime change
    curr_regime = current.get('regime', {})
    prev_regime = previous.get('regime', {})

    curr_color = curr_regime.get('background_color')
    prev_color = prev_regime.get('background_color')
    if curr_color != prev_color:
        changes.append(f"REGIME SHIFT: {prev_color} -> {curr_color}")

    curr_above = curr_regime.get('above_200ma')
    prev_above = prev_regime.get('above_200ma')
    if curr_above != prev_above:
        direction = "crossed above" if curr_above else "crossed below"
        changes.append(f"SPX {direction} 200-day moving average")

    # Allocation percentage changes
    curr_alloc = current.get('allocation_percentages', {})
    prev_alloc = previous.get('allocation_percentages', {})
    for sleeve_name in set(list(curr_alloc.keys()) + list(prev_alloc.keys())):
        curr_pct = curr_alloc.get(sleeve_name, 0)
        prev_pct = prev_alloc.get(sleeve_name, 0)
        if abs(curr_pct - prev_pct) > 0.02:
            changes.append(
                f"{sleeve_name} allocation: {prev_pct:.0%} -> {curr_pct:.0%}"
            )

    # ETF changes per sleeve
    curr_etfs = extract_sleeve_etfs(current)
    prev_etfs = extract_sleeve_etfs(previous)

    all_sleeves = set(list(curr_etfs.keys()) + list(prev_etfs.keys()))
    for sleeve_name in sorted(all_sleeves):
        curr_set = curr_etfs.get(sleeve_name, set())
        prev_set = prev_etfs.get(sleeve_name, set())

        added = curr_set - prev_set
        removed = prev_set - curr_set

        if added:
            changes.append(f"{sleeve_name}: added {', '.join(sorted(added))}")
        if removed:
            changes.append(f"{sleeve_name}: removed {', '.join(sorted(removed))}")

    return changes


def generate_daily_summary(current: Dict, previous: Optional[Dict]) -> str:
    """
    Generate a human-readable daily summary.

    Returns a multi-line string suitable for display on the dashboard
    or saving to docs/daily-summary.txt.
    """
    lines = []
    regime = current.get('regime', {})
    color = regime.get('background_color', '?')
    vix = regime.get('vix_close', '?')
    above_ma = regime.get('above_200ma', '?')

    lines.append(f"Regime: {color} | VIX: {vix} | Above 200MA: {above_ma}")
    lines.append("")

    if previous is None:
        lines.append("First run — no previous data to compare.")
        lines.append("")
        # Still show current selections
        for sleeve_name, sleeve_data in current.get('sleeve_analyses', {}).items():
            pct = sleeve_data.get('allocation_percentage', 0)
            selected = sleeve_data.get('selected_etfs', [])
            syms = []
            for etf in selected[:4]:
                if isinstance(etf, dict):
                    syms.append(etf.get('symbol', '?'))
            sym_str = ', '.join(syms) if syms else '(none)'
            lines.append(f"  {sleeve_name} ({pct:.0%}): {sym_str}")
        return '\n'.join(lines)

    changes = detect_changes(current, previous)

    if not changes:
        lines.append("NO ACTION TODAY — no changes from previous run.")
    else:
        lines.append(f"ACTION REQUIRED — {len(changes)} change(s) detected:")
        lines.append("")
        for change in changes:
            lines.append(f"  - {change}")

    # Warnings
    warnings = current.get('warnings', [])
    if warnings:
        lines.append("")
        lines.append(f"Warnings ({len(warnings)}):")
        for w in warnings:
            lines.append(f"  - {w}")

    return '\n'.join(lines)


def run_rebalance_check(results: Dict, docs_dir: Path) -> Tuple[str, List[str]]:
    """
    Run the full rebalance check: load previous, detect changes, generate summary.

    Returns:
        Tuple of (summary_text, list_of_changes)
    """
    previous = load_previous_result(docs_dir)
    summary = generate_daily_summary(results, previous)
    changes = detect_changes(results, previous) if previous else []
    return summary, changes
