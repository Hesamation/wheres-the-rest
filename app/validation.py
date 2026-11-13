"""Validation module for user inputs to the payout reader API and CLI.

Enforces bounds and strict checks:
- JSON payload size limit
- Base58 decoded 32-byte NEAR transaction hash
- Named or implicit NEAR account ID
- Saved example ID allowlist
"""
import re

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE = len(ALPHABET)
ALPHABET_MAP = {c: i for i, c in enumerate(ALPHABET)}

# NEAR accounts: implicit (64 hex lowercase) or named (2-64 chars, lowercase alphanumeric + separators)
NEAR_NAMED_REGEX = re.compile(r"^(?=.{2,64}$)[a-z0-9]+([._-][a-z0-9]+)*$")
NEAR_HEX_REGEX = re.compile(r"^[0-9a-f]{64}$")

ALLOWLISTED_SAVED_IDS = {"qa1", "qa2", "prod_control"}
MAX_REQUEST_BYTES = 65536  # 64 KB limit


def b58decode(s: str) -> bytes | None:
    """Decode a base58 string to raw bytes, returning None if invalid."""
    if not isinstance(s, str) or not s:
        return None
    val = 0
    for c in s:
        idx = ALPHABET_MAP.get(c)
        if idx is None:
            return None
        val = val * BASE + idx
    num_bytes = (val.bit_length() + 7) // 8
    raw = val.to_bytes(num_bytes, "big") if num_bytes > 0 else b""
    pad = 0
    for c in s:
        if c == "1":
            pad += 1
        else:
            break
    return b"\x00" * pad + raw


def is_valid_near_tx_hash(tx_hash: str) -> bool:
    """A valid NEAR transaction hash is base58-encoded 32 bytes."""
    if not isinstance(tx_hash, str) or len(tx_hash) < 40 or len(tx_hash) > 46:
        return False
    raw = b58decode(tx_hash)
    return raw is not None and len(raw) == 32


def is_valid_near_account_id(account_id: str) -> bool:
    """A valid NEAR account ID is either an implicit 64-hex ID or a valid named account ID."""
    if not isinstance(account_id, str):
        return False
    if NEAR_HEX_REGEX.match(account_id):
        return True
    return bool(NEAR_NAMED_REGEX.match(account_id))


def validate_report_request(payload: dict) -> tuple[bool, str, dict]:
    """Validate request payload for /api/report.

    Returns (is_valid, error_message, sanitized_params).
    """
    if not isinstance(payload, dict):
        return False, "Request body must be a JSON object", {}

    mode = payload.get("mode")
    if mode not in ("live", "saved"):
        return False, "Field 'mode' must be 'live' or 'saved'", {}

    if mode == "saved":
        example_id = payload.get("exampleId")
        if not example_id or example_id not in ALLOWLISTED_SAVED_IDS:
            return (
                False,
                f"Invalid or missing 'exampleId'. Must be one of: {sorted(ALLOWLISTED_SAVED_IDS)}",
                {},
            )
        return True, "", {"mode": "saved", "exampleId": example_id}

    # mode == "live"
    tx_hash = payload.get("txHash")
    signer_id = payload.get("signerId")

    if not tx_hash or not is_valid_near_tx_hash(tx_hash):
        return (
            False,
            "Field 'txHash' must be a valid 32-byte base58 NEAR transaction hash",
            {},
        )

    if not signer_id or not is_valid_near_account_id(signer_id):
        return (
            False,
            "Field 'signerId' must be a valid NEAR account ID (named or implicit 64-hex)",
            {},
        )

    return True, "", {"mode": "live", "txHash": tx_hash, "signerId": signer_id}
