#!/usr/bin/env bash
#
# Run the allocation pipeline locally.
#
# Usage:
#   ./scripts/run_local.sh                  # Full run (uses yfinance cache)
#   ./scripts/run_local.sh --fixtures       # Use fixture data (no network)
#   ./scripts/run_local.sh --force-refresh  # Bypass yfinance cache
#   ./scripts/run_local.sh --alloc-only     # Skip data fetch + regime detection
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

USE_FIXTURES=false
FORCE_REFRESH=false
ALLOC_ONLY=false
SKIP_FETCH=false
NO_LLM=false

for arg in "$@"; do
    case "$arg" in
        --fixtures)      USE_FIXTURES=true ;;
        --force-refresh) FORCE_REFRESH=true ;;
        --alloc-only)    ALLOC_ONLY=true ;;
        --skip-fetch)    SKIP_FETCH=true ;;
        --no-llm)        NO_LLM=true ;;
        -h|--help)
            echo "Usage: $0 [--fixtures] [--force-refresh] [--alloc-only] [--skip-fetch] [--no-llm]"
            echo ""
            echo "  --fixtures       Use test fixture data (no network calls)"
            echo "  --force-refresh  Bypass yfinance CSV cache"
            echo "  --alloc-only     Skip Stage 1 (data fetch) and Stage 2 (regime detection)"
            echo "  --skip-fetch     Skip TradingView API, use cached CSVs only"
            echo "  --no-llm         Skip LLM regime analysis"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            exit 1
            ;;
    esac
done

if [ "$USE_FIXTURES" = true ]; then
    echo "==> Using fixture data from tests/fixtures/"

    # Copy fixture regime JSON to docs/
    mkdir -p docs
    cp tests/fixtures/spx-regime-results.json docs/spx-regime-results.json

    # Run allocation engine with fixtures as data dir
    # We override data_dir by setting an env var that the engine can read
    PYNANCE_DATA_DIR="$PROJECT_ROOT/tests/fixtures" python allocation/allocation_engine.py
    echo "==> Results saved to docs/allocation-results.json"
    exit 0
fi

if [ "$ALLOC_ONLY" = false ]; then
    echo "==> Stage 1: Fetching data..."
    if [ "$SKIP_FETCH" = true ]; then
        python data/fetch_data.py --skip-fetch
    else
        python data/fetch_data.py || {
            echo "WARNING: Stage 1 failed (TradingView). Proceeding with existing data."
        }
    fi

    echo "==> Stage 2: Regime detection..."
    python -m regime
fi

echo "==> Stage 3: Allocation engine..."
ALLOC_ARGS=""
if [ "$FORCE_REFRESH" = true ]; then
    ALLOC_ARGS="$ALLOC_ARGS --force-refresh"
fi
if [ "$NO_LLM" = true ]; then
    ALLOC_ARGS="$ALLOC_ARGS --no-llm"
fi
python allocation/allocation_engine.py $ALLOC_ARGS

echo "==> Done. Results in docs/allocation-results.json"
echo ""

# Quick summary
if command -v python &>/dev/null; then
    python -c "
import json
with open('docs/allocation-results.json') as f:
    r = json.load(f)
regime = r.get('regime', {})
print(f\"Regime: {regime.get('background_color', '?')} | VIX: {regime.get('vix_close', '?')} | Above 200MA: {regime.get('above_200ma', '?')}\")
for name, sleeve in r.get('sleeve_analyses', {}).items():
    pct = sleeve.get('allocation_percentage', 0)
    selected = sleeve.get('selected_etfs', [])
    syms = [e.get('symbol', '?') if isinstance(e, dict) else e for e in selected[:4]]
    print(f\"  {name}: {pct:.0%} -> {', '.join(syms) if syms else '(none)'}\"
    )
warnings = r.get('warnings', [])
if warnings:
    print(f\"\nWarnings ({len(warnings)}):\")
    for w in warnings:
        print(f\"  - {w}\")
"
fi
