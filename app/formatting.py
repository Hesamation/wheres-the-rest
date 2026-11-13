"""Exact monetary conversions, CSV export, and Markdown audit proof formatting.

All monetary arithmetic and conversions are exact standard-library string and integer operations:
USDC has 6 decimals on Base (eth:8453).
1 USDC = 1,000,000 atomic units.
"""
from __future__ import annotations

import csv
import io


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


def report_to_csv(envelope: dict) -> str:
    """Format report envelope rows as RFC 4180 CSV for spreadsheet and accounting import."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "row_indices",
        "row_type",
        "recipient",
        "gross_usdc",
        "fee_usdc",
        "net_usdc",
        "verdict",
        "near_tx",
        "base_tx",
        "base_block",
        "note",
    ])
    req_tx = envelope.get("request", {}).get("txHash", "")
    for r in envelope.get("rows", []):
        row_indices = ",".join(str(i) for i in (r.get("rowIndices") or []))
        row_type = r.get("kind", "")
        recipient = r.get("recipient", "")
        amts = r.get("amounts") or {}
        gross = amts.get("grossFormatted", "") or ""
        fee = amts.get("feeFormatted", "") or ""
        net = amts.get("netFormatted", "") or ""
        verdict = r.get("verdict", "")
        evidence = r.get("evidence") or {}
        dest_tx = (evidence.get("destTransfer") or {}).get("transferTxHash") or (evidence.get("bridgeRecord") or {}).get("transferTxHash") or ""
        observations = evidence.get("observedTransfers") or []
        if observations:
            dest_tx = ";".join(dict.fromkeys(x["destTransfer"]["transferTxHash"] for x in observations))
        dest_block = (evidence.get("destTransfer") or {}).get("block", "")
        note = r.get("note", "")
        writer.writerow([
            row_indices,
            row_type,
            recipient,
            gross,
            fee,
            net,
            verdict,
            req_tx,
            dest_tx,
            dest_block,
            note,
        ])
    return output.getvalue()


def report_to_markdown_proof(envelope: dict) -> str:
    """Generate a clean Markdown audit summary suitable for DAO proposals or Trezu comments."""
    req = envelope.get("request", {})
    summary = envelope.get("summary", {})
    prov = envelope.get("provenance", {})
    rows = envelope.get("rows", [])

    tx_hash = req.get("txHash", "-")
    signer = req.get("signerId", "-")
    overall = summary.get("overall", "UNKNOWN")
    overall_code = summary.get("overallCode", "UNKNOWN")
    captured = prov.get("capturedAt", "-")
    sha_raw = prov.get("readerSha256", "")
    reader_sha = f"{sha_raw[:16]}..." if sha_raw else "-"

    lines = [
        "### NEAR USDC Cross-Chain Payout Audit Proof",
        f"- **Transaction**: `{tx_hash}`",
        f"- **Signer**: `{signer}`",
        f"- **Audit Status**: **{overall_code}** ({overall})",
        "- **Route**: `base-0x8335...omft.near` → Base USDC (`eth:8453`)",
        f"- **Evidence Timestamp**: {captured}",
        f"- **Auditor**: Where's the Rest? (SHA-256 `{reader_sha}`)",
        "",
        "| Row(s) | Recipient | Gross/burn (USDC) | Observed fees (USDC) | Observed net (USDC) | Verdict | Base Tx |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in rows:
        indices = ",".join(str(i) for i in (r.get("rowIndices") or []))
        recip = r.get("recipient", "-")
        if len(recip) > 12:
            recip = f"`{recip[:6]}...{recip[-4:]}`"
        amts = r.get("amounts") or {}
        gross = amts.get("grossFormatted") or "-"
        fee = amts.get("feeFormatted") or "-"
        net = amts.get("netFormatted") or "-"
        verdict = r.get("verdict", "-")
        evidence = r.get("evidence") or {}
        dest_tx = (evidence.get("destTransfer") or {}).get("transferTxHash") or (evidence.get("bridgeRecord") or {}).get("transferTxHash")
        dest_txs = list(dict.fromkeys(x["destTransfer"]["transferTxHash"]
                                     for x in evidence.get("observedTransfers", [])))
        if not dest_txs and dest_tx:
            dest_txs = [dest_tx]
        dest_link = " ".join(f"[`{tx[:8]}...`](https://basescan.org/tx/{tx})" for tx in dest_txs) or "-"
        lines.append(f"| {indices} | {recip} | {gross} | {fee} | {net} | {verdict} | {dest_link} |")

    lines.append("")
    for r in rows:
        if r.get("groupDetails"):
            gd = r["groupDetails"]
            indices = ",".join(str(i) for i in r.get("rowIndices", []))
            lines.append(f"Group [{indices}]: {gd['observed']} observed; {gd['unrecorded']} unrecorded. Source-burn attribution remains ambiguous.")
    lines.append(f"Evidence mode: {req.get('mode', 'unknown')}. Amounts are provider observations; “proof” is not a cryptographic proof.")
    lines.extend([
        "> **Conservative Evidence Disclaimer**: Missing observations are ambiguous, not proof of permanent loss. OBSERVED_MATCH represents receipt-level provider evidence with block confirmations, not final settlement.",
    ])
    return "\n".join(lines)
