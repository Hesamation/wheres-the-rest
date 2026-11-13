"""Unit tests for app.formatting."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.formatting import format_usdc, report_to_csv, report_to_markdown_proof, to_str_amount


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


def test_report_to_csv():
    mock_envelope = {
        "request": {"txHash": "NEAR_TX_123"},
        "rows": [
            {
                "rowIndices": [0],
                "kind": "single",
                "recipient": "0xRecipient1",
                "amounts": {
                    "grossFormatted": "1.000000",
                    "feeFormatted": "0.002400",
                    "netFormatted": "0.997600",
                },
                "verdict": "OBSERVED_MATCH",
                "evidence": {
                    "destTransfer": {"transferTxHash": "0xBaseTx", "block": 12345}
                },
                "note": "observed note",
            }
        ],
    }
    csv_str = report_to_csv(mock_envelope)
    assert "row_indices,row_type,recipient,gross_usdc" in csv_str
    assert "0,single,0xRecipient1,1.000000,0.002400,0.997600,OBSERVED_MATCH,NEAR_TX_123,0xBaseTx,12345,observed note" in csv_str


def test_report_to_markdown_proof():
    mock_envelope = {
        "request": {"txHash": "NEAR_TX_123", "signerId": "signer.near"},
        "summary": {"overall": "ALL_ROWS_OBSERVED", "overallCode": "ALL_ROWS_OBSERVED"},
        "provenance": {"capturedAt": "2026-11-13T00:00:00Z", "readerSha256": "0123456789abcdef0123456789abcdef"},
        "rows": [
            {
                "rowIndices": [0],
                "kind": "single",
                "recipient": "0x3139dB7DAa48Bbb8a311734DB70423578F50E9CF",
                "amounts": {
                    "grossFormatted": "1.000000",
                    "feeFormatted": "0.002400",
                    "netFormatted": "0.997600",
                },
                "verdict": "OBSERVED_MATCH",
                "evidence": {
                    "destTransfer": {"transferTxHash": "0x6f845a0325d9762b0584d01dfdf789513ac3e2f33639e3d27f9f60d6055ab21a"}
                },
                "note": "note",
            }
        ],
    }
    proof = report_to_markdown_proof(mock_envelope)
    assert "### NEAR USDC Cross-Chain Payout Audit Proof" in proof
    assert "`NEAR_TX_123`" in proof
    assert "ALL_ROWS_OBSERVED" in proof
    assert "0.997600" in proof


if __name__ == "__main__":
    test_format_usdc()
    test_to_str_amount()
    test_report_to_csv()
    test_report_to_markdown_proof()
    print("test_formatting PASSED")
