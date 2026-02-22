#!/bin/bash

# Collects heartbeat data into server-health.json and pushes to gh-pages.
# Designed to run on a cron schedule (e.g., every 30 minutes).
#
# Usage: ./monitoring/collect_and_push.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "[HEALTH] Starting health collection at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Step 1: Run the collector to build server-health.json
python3 "$SCRIPT_DIR/collect_health.py"

HEALTH_FILE="$SCRIPT_DIR/server-health.json"
if [ ! -f "$HEALTH_FILE" ]; then
    echo "[HEALTH] ERROR: server-health.json was not created"
    exit 1
fi

# Step 2: Push to gh-pages using a temporary worktree
WORKTREE_DIR=$(mktemp -d)
CLEANUP() {
    cd "$PROJECT_ROOT"
    git worktree remove "$WORKTREE_DIR" --force 2>/dev/null || true
    rm -rf "$WORKTREE_DIR" 2>/dev/null || true
}
trap CLEANUP EXIT

echo "[HEALTH] Setting up gh-pages worktree..."

# Fetch latest gh-pages
git -C "$PROJECT_ROOT" fetch origin gh-pages --depth=1 2>/dev/null || true

# Create worktree from gh-pages
if git -C "$PROJECT_ROOT" worktree add "$WORKTREE_DIR" origin/gh-pages --detach 2>/dev/null; then
    echo "[HEALTH] Worktree created from gh-pages"
else
    echo "[HEALTH] ERROR: Could not create worktree from gh-pages branch"
    exit 1
fi

# Step 3: Copy health file and the dashboard page
cp "$HEALTH_FILE" "$WORKTREE_DIR/server-health.json"

# Also deploy server-health.html if it exists in docs/
if [ -f "$PROJECT_ROOT/docs/server-health.html" ]; then
    cp "$PROJECT_ROOT/docs/server-health.html" "$WORKTREE_DIR/server-health.html"
fi

# Step 4: Commit and push
cd "$WORKTREE_DIR"
git add server-health.json server-health.html 2>/dev/null || git add server-health.json

if git diff --cached --quiet 2>/dev/null; then
    echo "[HEALTH] No changes to push"
else
    git commit -m "update server health $(date -u +%Y-%m-%dT%H:%M:%SZ)" --quiet
    git push origin HEAD:gh-pages --quiet
    echo "[HEALTH] Pushed server-health.json to gh-pages"
fi

echo "[HEALTH] Done"
