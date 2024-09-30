def getCrossPairMultiplier(instrument):
    """Return multiplier to use for conversions"""
    if "JPY" not in instrument and "HUF" not in instrument:
        return .0001
    elif "JPY" in instrument or "HUF" in instrument:
        return .01