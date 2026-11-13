"""Exact monetary conversions and integer-string formatting for payout reader.

All monetary arithmetic and conversions are exact standard-library string and integer operations:
USDC has 6 decimals on Base (eth:8453).
1 USDC = 1,000,000 atomic units.
"""


def format_usdc(atomic_units: int | str | None, decimals: int = 6) -> str | None:
    """Convert an atomic unit integer to an exact decimal string representation.

    e.g. 1000000 -> "1.000000"
         10000 -> "0.010000"
         2400 -> "0.002400"
         7600 -> "0.007600"
         0 -> "0.000000"
         None -> None

    Zero floating point math is used.
    """
    if atomic_units is None:
        return None

    if isinstance(atomic_units, str):
        atomic_units = int(atomic_units)

    sign = "-" if atomic_units < 0 else ""
    val = abs(atomic_units)
    padded = str(val).zfill(decimals + 1)
    integer_part = padded[:-decimals]
    fractional_part = padded[-decimals:]
    return f"{sign}{integer_part}.{fractional_part}"


def to_str_amount(val: int | str | None) -> str | None:
    """Serialize atomic unit amount strictly as a string for JSON export, or None."""
    if val is None:
        return None
    return str(val)
