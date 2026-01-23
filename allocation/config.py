"""
Configuration for the asset allocation system.

Defines allocation rules based on regime conditions, sleeve parameters, and output settings.
"""

# Allocation rules based on SPX regime conditions
# Each rule maps regime conditions to allocation percentages
ALLOCATION_RULES = {
    # Risk-on regime (green background, above 200 MA, low VIX)
    # Strong Risk-On: Equities 50%, MF 20%, Commodities 20%, Crypto 5%, Bonds/Cash/Other 5%
    'risk_on': {
        'equity': 0.50,
        'fixed_income': 0.05,
        'commodities': 0.20,
        'crypto': 0.05,
        'managed_futures': 0.20,
        'alternatives': 0.00
    },
    # Moderate risk regime (yellow background)
    # Normal/Mixed: Equities 40%, MF 30%, Commodities 20%, Crypto 5%, Bonds/Cash/Other 5%
    'moderate_risk': {
        'equity': 0.40,
        'fixed_income': 0.05,
        'commodities': 0.20,
        'crypto': 0.05,
        'managed_futures': 0.30,
        'alternatives': 0.00
    },
    # Elevated risk regime (orange background)
    # Using Normal/Mixed allocation for orange as well
    'elevated_risk': {
        'equity': 0.40,
        'fixed_income': 0.05,
        'commodities': 0.20,
        'crypto': 0.05,
        'managed_futures': 0.30,
        'alternatives': 0.00
    },
    # Risk-off regime (red background, below 200 MA, high VIX)
    # Risk-Off: Equities 15%, MF 45%, Commodities 25%, Crypto 0-2%, Bonds/Cash/Other 13-15%
    # Using middle values: Crypto 1%, Bonds/Cash/Other 14%
    'risk_off': {
        'equity': 0.15,
        'fixed_income': 0.14,
        'commodities': 0.25,
        'crypto': 0.01,
        'managed_futures': 0.45,
        'alternatives': 0.00
    },
    # Crisis regime (extreme risk-off conditions)
    # Crisis: Equities 5%, MF 55%, Commodities 20%, Crypto 0%, Bonds/Cash/Other 20%
    'crisis': {
        'equity': 0.05,
        'fixed_income': 0.20,
        'commodities': 0.20,
        'crypto': 0.00,
        'managed_futures': 0.55,
        'alternatives': 0.00
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
    'vix_threshold': 30,  # If VIX > 30, use risk_off
    'vix_crisis_threshold': 40  # If VIX > 40, use crisis allocation
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
