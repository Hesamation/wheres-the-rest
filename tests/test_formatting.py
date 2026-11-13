"""Unit tests for app.formatting."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.formatting import format_usdc, to_str_amount


def test_format_usdc():
    assert format_usdc(None) is None
    assert format_usdc(0) == "0.000000"
    assert format_usdc(1) == "0.000001"
    assert format_usdc(10) == "0.000010"
    assert format_usdc(2400) == "0.002400"
    assert format_usdc(7600) == "0.007600"
    assert format_usdc(10000) == "0.010000"
    assert format_usdc(187600) == "0.187600"
    assert format_usdc(190000) == "0.190000"
    assert format_usdc(200000) == "0.200000"
    assert format_usdc(997600) == "0.997600"
    assert format_usdc(1000000) == "1.000000"
    assert format_usdc(24950000) == "24.950000"
    assert format_usdc("1000000") == "1.000000"


def test_to_str_amount():
    assert to_str_amount(None) is None
    assert to_str_amount(1000000) == "1000000"
    assert to_str_amount(0) == "0"
    assert to_str_amount("2400") == "2400"


if __name__ == "__main__":
    test_format_usdc()
    test_to_str_amount()
    print("test_formatting PASSED")
