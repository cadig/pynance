"""
Regime-based asset allocator.

Determines asset allocation percentages based on SPX regime analysis results.
"""

import logging
from typing import Dict
from .config import ALLOCATION_RULES, REGIME_CONDITIONS
from .utils import load_spx_regime_data


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
    
    # Check VIX threshold first (overrides other conditions)
    vix_value = regime_data.get('VIX_close')
    if vix_value and vix_value > REGIME_CONDITIONS['vix_threshold']:
        logging.info(f"VIX ({vix_value}) exceeds threshold ({REGIME_CONDITIONS['vix_threshold']}), using risk_off allocation")
        return ALLOCATION_RULES['risk_off'].copy()
    
    # Check if below 200 MA (overrides background color)
    if not regime_data.get('above_200ma', True):
        logging.info("SPX below 200 MA, using risk_off allocation")
        return ALLOCATION_RULES['risk_off'].copy()
    
    # Determine allocation based on background color
    background_color = regime_data.get('background_color', 'yellow')
    allocation_key = REGIME_CONDITIONS['background_color'].get(background_color, 'moderate_risk')
    
    logging.info(f"Regime background color: {background_color}, using {allocation_key} allocation")
    allocation = ALLOCATION_RULES[allocation_key].copy()
    
    return allocation


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
    
    allocation = determine_allocation(regime_data)
    
    return {
        'regime': {
            'background_color': regime_data.get('background_color'),
            'above_200ma': regime_data.get('above_200ma'),
            'vix_close': regime_data.get('VIX_close'),
            'datetime': regime_data.get('datetime')
        },
        'allocation': allocation
    }
