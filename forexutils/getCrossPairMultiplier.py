def getCrossPairMultiplier(instrument):
    "Check for existence of JPY or HUF in the oanda fx pair input string and return .01 if it exists, or .0001 if it doesn't"
    if "JPY" not in instrument and "HUF" not in instrument:
        multiplier = .0001
    elif "JPY" in instrument or "HUF" in instrument:
        multiplier = .01
    else:
        print('ERROR :: getCrossPairMultiplier() :: Invalid instrument')
        
    return multiplier