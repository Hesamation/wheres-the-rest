"""Unit tests for app.validation."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.validation import (
    b58decode,
    is_valid_near_account_id,
    is_valid_near_tx_hash,
    validate_report_request,
)


def test_b58decode():
    assert b58decode("") is None
    assert b58decode(None) is None
    assert b58decode("0") is None  # '0' is not in base58
    assert b58decode("I") is None  # 'I' is not in base58
    assert b58decode("l") is None  # 'l' is not in base58
    assert b58decode("O") is None  # 'O' is not in base58

    # Leading '1's represent zero bytes
    raw = b58decode("11")
    assert raw == b"\x00\x00"


def test_near_tx_hash():
    valid_hashes = [
        "863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe",
        "CbyrTsdExtWDbBsdUNqQC65JMBFwXEzkeaGJGmQb2QDz",
        "FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu",
        "EEDiWnLCkLGd8MizuqRut9K6GeBgLR9vU1WjdaQEJXCo",
    ]
    for h in valid_hashes:
        assert is_valid_near_tx_hash(h), f"Expected valid tx hash: {h}"

    invalid_hashes = [
        "",
        "short",
        "not-base-58-with-invalid-chars-0000000000000000",
        "863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zReExtraTooLong",
        None,
        12345,
    ]
    for h in invalid_hashes:
        assert not is_valid_near_tx_hash(h), f"Expected invalid tx hash: {h}"


def test_near_account_id():
    valid_accounts = [
        "sponsor.trezu.near",
        "sponsor-staging.trezu.near",
        "alice.near",
        "bob_smith.near",
        "0" * 64,  # implicit hex account
        "abcdef0123456789" * 4,
    ]
    for a in valid_accounts:
        assert is_valid_near_account_id(a), f"Expected valid account: {a}"

    invalid_accounts = [
        "",
        "a",  # too short (< 2)
        "A.near",  # uppercase
        "-start.near",
        "end-.near",
        ".start.near",
        "double..dots.near",
        "has space.near",
        "x" * 65,  # too long (> 64)
        None,
        123,
    ]
    for a in invalid_accounts:
        assert not is_valid_near_account_id(a), f"Expected invalid account: {a}"


def test_validate_report_request():
    # Valid saved
    ok, err, sanitized = validate_report_request({"mode": "saved", "exampleId": "qa1"})
    assert ok and not err
    assert sanitized == {"mode": "saved", "exampleId": "qa1"}

    # Invalid saved exampleId
    ok, err, _ = validate_report_request({"mode": "saved", "exampleId": "invalid_example"})
    assert not ok and "Must be one of" in err

    # Valid live
    ok, err, sanitized = validate_report_request({
        "mode": "live",
        "txHash": "FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu",
        "signerId": "sponsor.trezu.near",
    })
    assert ok and not err
    assert sanitized["mode"] == "live"

    # Missing signerId in live
    ok, err, _ = validate_report_request({
        "mode": "live",
        "txHash": "FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu",
    })
    assert not ok and "signerId" in err

    # Missing txHash in live
    ok, err, _ = validate_report_request({
        "mode": "live",
        "signerId": "sponsor.trezu.near",
    })
    assert not ok and "txHash" in err


if __name__ == "__main__":
    test_b58decode()
    test_near_tx_hash()
    test_near_account_id()
    test_validate_report_request()
    print("test_validation PASSED")
