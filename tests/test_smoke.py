"""
Smoke tests for the allocation engine.

Runs the full allocation engine against fixture data and validates that
output is structurally sane: all sleeves present, allocations sum to ~100%,
selected ETFs are from configured universes, no NaN values in scores.

These are not unit tests — they verify end-to-end output quality.
"""

import json
import math
import sys
from pathlib import Path

import pytest

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

FIXTURE_DIR = Path(__file__).parent / 'fixtures'

# All configured sleeve names
EXPECTED_SLEEVES = {'equity', 'commodities', 'crypto', 'managed_futures',
                    'vol_hedges', 'fixed_income'}


@pytest.fixture
def allocation_results(tmp_path, monkeypatch):
    """
    Run the allocation engine against fixture data and return the results dict.

    Uses monkeypatching to redirect data_dir and docs_dir to fixtures/tmp.
    """
    import allocation.utils as utils

    # Point data loading at fixtures
    monkeypatch.setattr(utils, 'get_data_dir', lambda: FIXTURE_DIR)
    monkeypatch.setattr(utils, 'get_docs_dir', lambda: FIXTURE_DIR)

    # Disable yfinance so we only use fixture CSVs
    monkeypatch.setattr(utils, 'YFINANCE_AVAILABLE', False)

    from allocation.allocation_engine import run_allocation_analysis
    return run_allocation_analysis()


def test_all_sleeves_present(allocation_results):
    """Every configured sleeve should appear in output."""
    sleeve_keys = set(allocation_results['sleeve_analyses'].keys())
    assert sleeve_keys == EXPECTED_SLEEVES, f"Missing sleeves: {EXPECTED_SLEEVES - sleeve_keys}"


def test_allocations_sum_to_100(allocation_results):
    """Regime allocation percentages should sum to ~100%."""
    total = sum(allocation_results['allocation_percentages'].values())
    assert math.isclose(total, 1.0, abs_tol=0.02), f"Allocations sum to {total:.2%}, not ~100%"


def test_selected_etfs_from_universe(allocation_results):
    """Selected ETFs in each sleeve should come from the configured universe."""
    from allocation.config import SLEEVE_CONFIG

    for sleeve_name, sleeve_result in allocation_results['sleeve_analyses'].items():
        selected = sleeve_result.get('selected_etfs', [])
        if not selected:
            continue

        # Get the configured universe for this sleeve
        if sleeve_name == 'equity':
            universe = set()
            for sub in SLEEVE_CONFIG['equity'].get('sub_modules', {}).values():
                if sub.get('enabled', True):
                    universe.update(sub.get('symbols', []))
        elif sleeve_name in SLEEVE_CONFIG:
            universe = set(SLEEVE_CONFIG[sleeve_name].get('symbols', []))
        else:
            continue

        if not universe:
            continue

        for etf in selected:
            sym = etf.get('symbol') if isinstance(etf, dict) else etf
            assert sym in universe, f"{sleeve_name}: {sym} not in configured universe {universe}"


def test_no_nan_in_scores(allocation_results):
    """No NaN values should appear in composite scores or returns."""
    for sleeve_name, sleeve_result in allocation_results['sleeve_analyses'].items():
        selected = sleeve_result.get('selected_etfs', [])
        for etf in selected:
            if not isinstance(etf, dict):
                continue

            # Check composite score
            score = etf.get('composite_score')
            if score is not None:
                assert not math.isnan(score), f"{sleeve_name}/{etf.get('symbol')}: NaN composite_score"

            # Check returns
            returns = etf.get('returns', {})
            for period, val in returns.items():
                if val is not None:
                    assert not math.isnan(val), f"{sleeve_name}/{etf.get('symbol')}: NaN return for {period}"


def test_regime_info_present(allocation_results):
    """Regime info should be populated."""
    regime = allocation_results.get('regime', {})
    assert regime.get('background_color') is not None, "Missing background_color"
    assert regime.get('vix_close') is not None, "Missing VIX close"


def test_datetime_present(allocation_results):
    """Results should have a datetime."""
    assert 'datetime' in allocation_results
    assert allocation_results['datetime'] is not None


def test_warnings_is_list(allocation_results):
    """Warnings field should be a list (may be empty)."""
    warnings = allocation_results.get('warnings')
    assert isinstance(warnings, list), f"Expected warnings to be list, got {type(warnings)}"


def test_sleeve_allocation_percentages_match(allocation_results):
    """Each sleeve's allocation_percentage should match the top-level allocation."""
    alloc_pcts = allocation_results['allocation_percentages']
    for sleeve_name, sleeve_result in allocation_results['sleeve_analyses'].items():
        expected = alloc_pcts.get(sleeve_name, 0.0)
        actual = sleeve_result.get('allocation_percentage', -1)
        assert math.isclose(expected, actual, abs_tol=0.001), \
            f"{sleeve_name}: allocation_percentage {actual} != expected {expected}"
