"""
Configuration for the asset allocation system.

Defines allocation rules based on regime conditions, sleeve parameters, and output settings.
"""

# Allocation rules based on SPX regime conditions
# Each rule maps regime conditions to allocation percentages
ALLOCATION_RULES = {
    # Risk-on regime (green background, above 200 MA, low VIX)
    # Strong Risk-On: Vol hedge instruments decay — don't hold
    'risk_on': {
        'equity': 0.50,
        'fixed_income': 0.05,
        'commodities': 0.20,
        'crypto': 0.05,
        'managed_futures': 0.20,
        'alternatives': 0.00
    },
    # Moderate risk regime (yellow background)
    # Small hedge allocation available if VIX triggers entry
    'moderate_risk': {
        'equity': 0.38,
        'fixed_income': 0.05,
        'commodities': 0.20,
        'crypto': 0.05,
        'managed_futures': 0.30,
        'alternatives': 0.02
    },
    # Elevated risk regime (orange background)
    # Meaningful hedge allocation — VIX likely rising
    'elevated_risk': {
        'equity': 0.35,
        'fixed_income': 0.05,
        'commodities': 0.20,
        'crypto': 0.05,
        'managed_futures': 0.30,
        'alternatives': 0.05
    },
    # Risk-off regime (red background, below 200 MA, high VIX)
    # Active hedge — reallocated from equities
    'risk_off': {
        'equity': 0.10,
        'fixed_income': 0.10,
        'commodities': 0.25,
        'crypto': 0.01,
        'managed_futures': 0.45,
        'alternatives': 0.09
    },
    # Crisis regime (extreme risk-off conditions)
    # Max hedge allocation — vol instruments pay off here
    'crisis': {
        'equity': 0.00,
        'fixed_income': 0.15,
        'commodities': 0.20,
        'crypto': 0.00,
        'managed_futures': 0.50,
        'alternatives': 0.15
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
            'us_large_cap': {'enabled': True, 'symbols': ['SPY', 'QQQ', 'NTSX', 'SCHD', 'USMV', 'RSP' ]},
            'ex_us': {'enabled': True, 'symbols': ['CWI', 'EEM', 'DFIV', 'FXI']},
            'small_caps': {'enabled': True, 'symbols': ['IWM', 'AVUV']},
            'total_market': {'enabled': True, 'symbols': ['VTI']},
            'sector_etfs': {'enabled': False, 'symbols': ['XLRE', 'XLB', 'XLE', 'XLK', 'XLV', 'XLF', 'XLP', 'XLU', 'XLI', 'XLC']},
            'custom_etfs': {'enabled': True, 'symbols': ['CHAT', 'TOPT', 'MAGS', 'BRK-B']}
        }
    },
    'commodities': {
        'enabled': True,
        'symbols': ['DBC', 'GLD', 'SLV', 'GDX', 'SIL', 'COPX', 'URNM', 'USO', 'DBA'],
        # Mutual exclusion pairs: only the higher-ranked of each pair is selected
        'exclusive_pairs': [['GLD', 'GDX'], ['SLV', 'SIL']]
    },
    'crypto': {
        'enabled': True,
        'symbols': ['IBIT', 'ETHA', 'BITO', 'NODE']
    },
    'managed_futures': {
        'enabled': True,
        'symbols': ['KMLM', 'DBMF', 'CTA', 'WTMF', 'FMF']
    },
    'alternatives': {
        'enabled': True,
        'symbols': ['UVXY', 'TAIL', 'CAOS']
    },
    'fixed_income': {
        'enabled': True,
        'symbols': ['TLT', 'SGOV', 'TIP', 'AGG'],
        # Which ETFs are eligible in each regime.
        # Risk-on/moderate: no long duration (TLT excluded) — rates may rise.
        # Elevated: TLT allowed as a hedge option.
        # Risk-off/crisis: all eligible — long duration rallies in flight to quality.
        'regime_eligible': {
            'risk_on':       ['SGOV', 'AGG', 'TIP'],
            'moderate_risk': ['SGOV', 'AGG', 'TIP'],
            'elevated_risk': ['SGOV', 'AGG', 'TIP', 'TLT'],
            'risk_off':      ['TLT', 'AGG', 'TIP', 'SGOV'],
            'crisis':        ['TLT', 'AGG', 'TIP', 'SGOV'],
        }
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
