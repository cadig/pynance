"""
LLM Regime Analysis — daily second opinion on market conditions.

Reads the same data the rule-based system uses, constructs a compact data
snapshot, and asks an LLM for an independent regime assessment. Runs
alongside (not instead of) the existing rule-based regime.

Requires: anthropic SDK and ANTHROPIC_API_KEY env var.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd


def _safe_read_csv(filepath: Path) -> Optional[pd.DataFrame]:
    """Read a CSV file, returning None on failure."""
    try:
        if filepath.exists():
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            if not df.index.is_monotonic_increasing:
                df = df.sort_index()
            return df
    except Exception as e:
        logging.warning(f"Could not read {filepath}: {e}")
    return None


def _format_price_vs_ma(df: pd.DataFrame, label: str, ma_window: int = 200) -> Optional[str]:
    """Format a 'SYMBOL: price (X% above/below 200DMA at Y)' string."""
    if df is None or df.empty or 'close' not in df.columns:
        return None
    close = df['close'].iloc[-1]
    if pd.isna(close):
        return None
    if len(df) >= ma_window:
        sma = df['close'].rolling(window=ma_window, min_periods=ma_window).mean().iloc[-1]
        if pd.notna(sma) and sma != 0:
            pct = (close / sma - 1) * 100
            direction = "above" if pct >= 0 else "below"
            return f"{label}: {close:,.2f} ({abs(pct):.1f}% {direction} 200DMA at {sma:,.2f})"
    return f"{label}: {close:,.2f}"


def _format_returns(df: pd.DataFrame, periods: Dict[str, int]) -> str:
    """Format return percentages for given day-count periods."""
    if df is None or df.empty or 'close' not in df.columns:
        return ""
    parts = []
    close = df['close']
    for label, days in periods.items():
        if len(close) > days:
            ret = (close.iloc[-1] / close.iloc[-days] - 1) * 100
            parts.append(f"{label} {ret:+.1f}%")
    return ", ".join(parts)


def _format_vix_detail(vix_df: pd.DataFrame) -> Optional[str]:
    """Format VIX with Bollinger %B and SMA."""
    if vix_df is None or vix_df.empty or 'close' not in vix_df.columns:
        return None
    close = vix_df['close']
    if len(close) < 20:
        return f"VIX: {close.iloc[-1]:.1f}"
    vix = close.iloc[-1]
    sma20 = close.rolling(20).mean().iloc[-1]
    std20 = close.rolling(20).std().iloc[-1]
    if pd.notna(std20) and std20 > 0:
        pct_b = (vix - (sma20 - 2 * std20)) / (4 * std20)
        trend = "rising" if close.iloc[-1] > close.iloc[-5] else "falling"
        return f"VIX: {vix:.1f} (SMA20: {sma20:.1f}, %B: {pct_b:.2f}, {trend})"
    return f"VIX: {vix:.1f} (SMA20: {sma20:.1f})"


def _format_breadth(data_dir: Path) -> Optional[str]:
    """Format breadth indicators."""
    parts = []
    for sym, label in [('MMTH-200-day', 'MMTH'), ('MMFI-50-day', 'MMFI'), ('MMTW-20-day', 'MMTW')]:
        df = _safe_read_csv(data_dir / f'{sym}.csv')
        if df is not None and 'close' in df.columns:
            val = df['close'].iloc[-1]
            if pd.notna(val):
                parts.append(f"{label} {val:.0f}%")
    if parts:
        return "Breadth: " + ", ".join(parts)
    return None


def _format_vix_term_structure(data_dir: Path) -> Optional[str]:
    """Format VIX term structure if data is available."""
    vix_df = _safe_read_csv(data_dir / 'VIX.csv')
    vix3m_df = _safe_read_csv(data_dir / 'VIX3M.csv')
    if vix_df is None or vix3m_df is None:
        return None
    if 'close' not in vix_df.columns or 'close' not in vix3m_df.columns:
        return None
    vix = vix_df['close'].iloc[-1]
    vix3m = vix3m_df['close'].iloc[-1]
    if pd.isna(vix) or pd.isna(vix3m) or vix3m == 0:
        return None
    ratio = vix / vix3m
    structure = "backwardation" if ratio > 1.0 else "contango"
    return f"VIX term structure: VIX/VIX3M = {ratio:.2f} ({structure})"


def _format_yield_curve(data_dir: Path) -> Optional[str]:
    """Format yield curve spread if data is available."""
    us02y = _safe_read_csv(data_dir / 'US02Y.csv')
    us10y = _safe_read_csv(data_dir / 'US10Y.csv')
    if us02y is None or us10y is None:
        return None
    if 'close' not in us02y.columns or 'close' not in us10y.columns:
        return None
    y2 = us02y['close'].iloc[-1]
    y10 = us10y['close'].iloc[-1]
    if pd.isna(y2) or pd.isna(y10):
        return None
    spread = y10 - y2
    # 6 month ago comparison
    lookback = min(126, len(us10y) - 1, len(us02y) - 1)
    if lookback > 20:
        old_spread = us10y['close'].iloc[-lookback] - us02y['close'].iloc[-lookback]
        direction = "steepening" if spread > old_spread else "flattening"
        return f"10Y-2Y spread: {spread:+.2f}% ({direction}, was {old_spread:+.2f}% ~6mo ago)"
    return f"10Y-2Y spread: {spread:+.2f}%"


def _format_adrn(data_dir: Path) -> Optional[str]:
    """Format NYSE Advance/Decline ratio."""
    df = _safe_read_csv(data_dir / 'ADRN.csv')
    if df is None or 'close' not in df.columns or len(df) < 5:
        return None
    current = df['close'].iloc[-1]
    avg_5d = df['close'].iloc[-5:].mean()
    trend = "rising" if current > avg_5d else "declining"
    return f"NYSE AD ratio: {current:.2f} (5-day avg: {avg_5d:.2f}, {trend})"


def build_data_snapshot(data_dir: Path, regime_data: Dict,
                        allocation_results: Optional[Dict] = None) -> str:
    """
    Build a compact data snapshot for the LLM from CSV files and regime data.

    Returns a formatted string (~500-800 tokens) summarizing current market conditions.
    """
    lines = []

    # SPX
    spx_df = _safe_read_csv(data_dir / 'SPX.csv')
    spx_line = _format_price_vs_ma(spx_df, "SPX")
    if spx_line:
        lines.append(spx_line)
        rets = _format_returns(spx_df, {"1d": 1, "5d": 5, "20d": 20})
        if rets:
            lines.append(f"SPX returns: {rets}")

    # VIX
    vix_df = _safe_read_csv(data_dir / 'VIX.csv')
    vix_line = _format_vix_detail(vix_df)
    if vix_line:
        lines.append(vix_line)

    # Breadth
    breadth = _format_breadth(data_dir)
    if breadth:
        lines.append(breadth)

    # NYSE AD
    adrn = _format_adrn(data_dir)
    if adrn:
        lines.append(adrn)

    # VIX term structure
    vts = _format_vix_term_structure(data_dir)
    if vts:
        lines.append(vts)

    # Yield curve
    yc = _format_yield_curve(data_dir)
    if yc:
        lines.append(yc)

    # Gold
    gold_df = _safe_read_csv(data_dir / 'GOLD.csv')
    gold_line = _format_price_vs_ma(gold_df, "Gold")
    if gold_line:
        rets = _format_returns(gold_df, {"1mo": 21})
        lines.append(f"{gold_line}" + (f" ({rets})" if rets else ""))

    # BTC
    btc_df = _safe_read_csv(data_dir / 'BTCUSD.csv')
    btc_line = _format_price_vs_ma(btc_df, "BTC")
    if btc_line:
        rets = _format_returns(btc_df, {"1mo": 21})
        lines.append(f"{btc_line}" + (f" ({rets})" if rets else ""))

    # Rule-based regime
    bg_color = regime_data.get('background_color', 'unknown')
    above_200 = regime_data.get('above_200ma', 'unknown')
    vix_close = regime_data.get('VIX_close', 'unknown')
    lines.append(f"Rule-based regime: {bg_color} | SPX above 200MA: {above_200} | VIX close: {vix_close}")

    # Sleeve picks (if available)
    if allocation_results and 'sleeve_analyses' in allocation_results:
        sleeve_lines = []
        for name, sleeve in allocation_results['sleeve_analyses'].items():
            selected = sleeve.get('selected_etfs', [])
            if selected:
                syms = [e.get('symbol', '?') if isinstance(e, dict) else str(e) for e in selected[:4]]
                sleeve_lines.append(f"{name}: {', '.join(syms)}")
        if sleeve_lines:
            lines.append("Current picks: " + " | ".join(sleeve_lines))

    return "\n".join(lines)


SYSTEM_PROMPT = """You are a market regime analyst. You will receive a structured data snapshot
of current market conditions. Your job is to:

1. REGIME ASSESSMENT: State the current market regime in one sentence.
   Use one of: Risk-On, Moderate Caution, Elevated Risk, Risk-Off, Crisis.

2. RULE DIVERGENCE: The rule-based system says "{rule_regime}".
   Do you agree? If not, explain why in 1-2 sentences.

3. KEY RISKS: What are the top 1-2 risks visible in this data?
   Focus on divergences, trend changes, or unusual readings.

4. WATCH LIST: What specific data point would change your assessment
   if it moved? (e.g., "If MMFI drops below 50%, this becomes Risk-Off")

5. CONFIDENCE: High / Medium / Low — and one sentence why.

Be concise. Total response should be under 200 words."""


def build_prompt(data_snapshot: str, regime_data: Dict) -> tuple:
    """
    Build the system prompt and user message for the LLM call.

    Returns (system_prompt, user_message).
    """
    bg_color = regime_data.get('background_color', 'unknown')
    system = SYSTEM_PROMPT.replace("{rule_regime}", bg_color)
    return system, data_snapshot


def call_llm(system_prompt: str, user_message: str) -> Optional[str]:
    """
    Call the Anthropic API with the given prompts.

    Returns the response text, or None on failure.
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        logging.warning("ANTHROPIC_API_KEY not set — skipping LLM regime analysis")
        return None

    try:
        import anthropic
    except ImportError:
        logging.warning("anthropic SDK not installed — skipping LLM regime analysis")
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        return message.content[0].text
    except Exception as e:
        logging.warning(f"LLM API call failed: {e}")
        return None


def parse_llm_response(response_text: str) -> Dict:
    """
    Parse structured fields from the LLM's free-text response.

    Returns a dict with best-effort extraction of regime assessment,
    confidence, and the full reasoning text.
    """
    result = {
        'llm_raw_response': response_text,
        'llm_regime_assessment': None,
        'llm_confidence': None,
    }

    text_lower = response_text.lower()

    # Extract regime assessment
    regime_keywords = {
        'risk-on': 'Risk-On',
        'moderate caution': 'Moderate Caution',
        'elevated risk': 'Elevated Risk',
        'risk-off': 'Risk-Off',
        'crisis': 'Crisis',
    }
    for keyword, label in regime_keywords.items():
        if keyword in text_lower:
            result['llm_regime_assessment'] = label
            break

    # Extract confidence
    for level in ['high', 'medium', 'low']:
        if f'confidence: {level}' in text_lower or f'confidence — {level}' in text_lower:
            result['llm_confidence'] = level.capitalize()
            break

    return result


def run_llm_regime_analysis(data_dir: Path, regime_data: Dict,
                             allocation_results: Optional[Dict] = None) -> Dict:
    """
    Run the full LLM regime analysis pipeline.

    Returns a dict suitable for inclusion in allocation results under 'llm_analysis'.
    Returns a minimal dict with 'skipped' reason if LLM is unavailable.
    """
    snapshot = build_data_snapshot(data_dir, regime_data, allocation_results)
    logging.info(f"LLM data snapshot ({len(snapshot)} chars):\n{snapshot}")

    system_prompt, user_message = build_prompt(snapshot, regime_data)

    response = call_llm(system_prompt, user_message)
    if response is None:
        return {'skipped': True, 'reason': 'LLM unavailable (no API key or SDK)'}

    parsed = parse_llm_response(response)
    parsed['data_snapshot'] = snapshot
    parsed['skipped'] = False

    logging.info(f"LLM regime assessment: {parsed.get('llm_regime_assessment')} "
                 f"(confidence: {parsed.get('llm_confidence')})")

    return parsed
