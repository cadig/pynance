"""Regime detection configuration — single source of truth."""

REGIME_CONFIG = {
    'show_subplots': False,
    'outputFile': True,
    'showPlot': False,
    'plot_zoom': {
        'enabled': True,
        'days': 200
    },
    'nyse_cumulative_ad_zscore': {
        'enabled': True,
        'type': 'regime',
        'lookback_period': 252,
        'smoothing_period': 50,
        'threshold': -1.0,
        'confirmation_days': 0,
        'show_subplot': False
    },
    'mmth_cross': {
        'enabled': True,
        'type': 'entry-strong',
        'threshold': 25,
        'confirmation_days': 0,
        'period': 200,
        'show_subplot': False
    },
    'mmtw_cross': {
        'enabled': True,
        'type': 'entry-light',
        'threshold': 25,
        'confirmation_days': 3,
        'period': 50,
        'show_subplot': False
    },
    'mmfi_cross': {
        'enabled': True,
        'type': 'entry-light',
        'threshold': 25,
        'confirmation_days': 3,
        'period': 50,
        'show_subplot': False
    },
    'vix_bollinger_exit': {
        'enabled': True,
        'type': 'exit-light',
        'lookback_period': 20,
        'std_dev': 2.0,
        'percent_b_threshold': 0,
        'show_subplot': False
    },
    'combined_mm_signals': {
        'enabled': True,
        'threshold': 50,
        'indicators': {
            'MMTW': {
                'enabled': True,
                'period': 20
            },
            'MMFI': {
                'enabled': True,
                'period': 50
            },
            'MMTH': {
                'enabled': True,
                'period': 200
            }
        },
        'show_subplot': False
    },
    'output_json_results': True
}
