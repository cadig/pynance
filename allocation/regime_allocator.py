"""
Regime-based asset allocator.

Determines asset allocation percentages based on SPX regime analysis results.
"""

import logging
from typing import Dict
from .config import ALLOCATION_RULES, REGIME_CONDITIONS
from .utils import load_spx_regime_data


def determine_regime_key(regime_data: Dict = None) -> str:
    """
    Determine the regime key string from SPX regime data.

    Priority: VIX crisis > VIX risk-off > below 200MA > background color.

    Returns one of: 'crisis', 'risk_off', 'risk_on', 'moderate_risk', 'elevated_risk'.
    """
    if regime_data is None:
        regime_data = load_spx_regime_data()

    vix_value = regime_data.get('VIX_close')

    if vix_value and vix_value > REGIME_CONDITIONS['vix_crisis_threshold']:
        return 'crisis'

    if vix_value and vix_value > REGIME_CONDITIONS['vix_threshold']:
        return 'risk_off'

    if not regime_data.get('above_200ma', True):
        return 'risk_off'

    background_color = regime_data.get('background_color', 'yellow')
    return REGIME_CONDITIONS['background_color'].get(background_color, 'moderate_risk')


def determine_allocation(regime_data: Dict = None) -> Dict[str, float]:
    """
    Determine asset allocation percentages based on SPX regime data.

    Args:
        regime_data: Optional SPX regime data dictionary. If None, loads from file.

    Returns:
        dict: Dictionary mapping asset sleeves to allocation percentages
        Example: {'equity': 0.60, 'fixed_income': 0.20, 'commodities': 0.10, ...}
    """
    if regime_data is None:
        regime_data = load_spx_regime_data()

    regime_key = determine_regime_key(regime_data)
    logging.info(f"Determined regime: {regime_key}")
    return ALLOCATION_RULES[regime_key].copy()


def get_allocation_summary(regime_data: Dict = None) -> Dict:
    """
    Get allocation summary including regime information and allocation percentages.
    
    Args:
        regime_data: Optional SPX regime data dictionary. If None, loads from file.
        
    Returns:
        dict: Dictionary containing regime info and allocation percentages
    """
    if regime_data is None:
        regime_data = load_spx_regime_data()
    
    regime_key = determine_regime_key(regime_data)
    allocation = ALLOCATION_RULES[regime_key].copy()

    return {
        'regime': {
            'background_color': regime_data.get('background_color'),
            'above_200ma': regime_data.get('above_200ma'),
            'vix_close': regime_data.get('VIX_close'),
            'datetime': regime_data.get('datetime')
        },
        'regime_key': regime_key,
        'allocation': allocation
    }
