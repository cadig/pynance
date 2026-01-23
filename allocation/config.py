"""
Configuration for the asset allocation system.

Defines allocation rules based on regime conditions, sleeve parameters, and output settings.
"""

# Allocation rules based on SPX regime conditions
# Each rule maps regime conditions to allocation percentages
ALLOCATION_RULES = {
    # Risk-on regime (green background, above 200 MA, low VIX)
    'risk_on': {
        'equity': 0.60,
        'fixed_income': 0.20,
        'commodities': 0.10,
        'crypto': 0.05,
        'managed_futures': 0.03,
        'alternatives': 0.02
    },
    # Moderate risk regime (yellow background)
    'moderate_risk': {
        'equity': 0.40,
        'fixed_income': 0.35,
        'commodities': 0.15,
        'crypto': 0.05,
        'managed_futures': 0.03,
        'alternatives': 0.02
    },
    # Elevated risk regime (orange background)
    'elevated_risk': {
        'equity': 0.25,
        'fixed_income': 0.45,
        'commodities': 0.15,
        'crypto': 0.05,
        'managed_futures': 0.05,
        'alternatives': 0.05
    },
    # Risk-off regime (red background, below 200 MA, high VIX)
    'risk_off': {
        'equity': 0.10,
        'fixed_income': 0.60,
        'commodities': 0.15,
        'crypto': 0.00,
        'managed_futures': 0.10,
        'alternatives': 0.05
    }
}

# Regime condition mappings
# Maps SPX regime data to allocation rule keys
REGIME_CONDITIONS = {
    'background_color': {
        'green': 'risk_on',
        'yellow': 'moderate_risk',
        'orange': 'elevated_risk',
        'red': 'risk_off'
    },
    'above_200ma': {
        True: None,  # Used as additional filter
        False: 'risk_off'  # Override to risk_off if below 200 MA
    },
    'vix_threshold': 30  # If VIX > 30, use risk_off
}

# Sleeve configuration
# Controls which sleeves are enabled and their parameters
SLEEVE_CONFIG = {
    'equity': {
        'enabled': True,
        'sub_modules': {
            'ex_us': {'enabled': True},
            'us_large_cap': {'enabled': True},
            'small_caps': {'enabled': True},
            'total_market': {'enabled': True},
            'sector_etfs': {'enabled': True},
            'custom_etfs': {'enabled': True}
        }
    },
    'commodities': {
        'enabled': True
    },
    'crypto': {
        'enabled': True
    },
    'managed_futures': {
        'enabled': True
    },
    'alternatives': {
        'enabled': True
    },
    'fixed_income': {
        'enabled': True
    }
}

# Output configuration
OUTPUT_CONFIG = {
    'save_json': True,
    'json_filename': 'allocation-results.json',
    'save_png': False,  # Can be enabled later
    'png_filename': 'allocation-summary.png',
    'save_html': False,  # Can be enabled later
    'html_filename': 'allocation-summary.html'
}
