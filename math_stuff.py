def percent_to_decimal(percent):
    """
    Convert a percent (like 25 or -25) to decimal 0.25 or -0.25.
    We don't assert bounds here because Unciv uniques may include negative or >100 values.
    """
    return float(percent) / 100.0
