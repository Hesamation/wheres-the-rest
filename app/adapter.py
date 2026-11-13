"""Thin adapter between the application server/worker and the unchanged reader.

Calls existing reader functions:
- extract_burns
- analyze_completeness
- normalize_bridge
- build_dest_from_receipt / fetch_dest
- reconcile
- summarize
Preserves exact reader verdicts, matching logic, and precedence without duplication.
Constructs the schemaVersion: "1" report envelope.
"""
from __future__ import annotations

import copy
import json
import re
import sys
import time
from pathlib import Path

from app.formatting import format_usdc, to_str_amount

# Path to imported reader directory
REPO_ROOT = Path(__file__).resolve().parent.parent
READER_DIR = REPO_ROOT / "reader"
if str(READER_DIR) not in sys.path:
    sys.path.insert(0, str(READER_DIR))

import payout_probe as pp  # noqa: E402

READER_SHA256 = "0ac8f7364292f5e9268bbcc465f433f9ac2ff48c7aeb9d2facfc0f24ce99f4a2"
READER_VERSION = "payout_probe.py v4/v5 closeout"

SAVED_EXAMPLES_META = {
    "qa1": {
        "id": "qa1",
        "label": "QA1 Ambiguous Group Deficit (0.01 x 3 USDC)",
        "txHash": "863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe",
        "signerId": "sponsor-staging.trezu.near",
        "capturedAt": "2026-11-10T22:26:58Z",
        "fixture": "fixtures/offline_qa1.json",
        "summary": "3 burns of 0.01 USDC; 1 observed on Base (0.0076 USDC net after 0.0024 fee), 2 unrecorded; grouped finding because individual attribution is ambiguous.",
    },
    "qa2": {
        "id": "qa2",
        "label": "QA2 Mixed Delivery (0.19 USDC observed, 0.20 USDC unrecorded)",
        "txHash": "CbyrTsdExtWDbBsdUNqQC65JMBFwXEzkeaGJGmQb2QDz",
        "signerId": "sponsor-staging.trezu.near",
        "capturedAt": "2026-11-10T22:32:14Z",
        "fixture": "fixtures/offline_qa2.json",
        "summary": "0.19 USDC burn observed on Base (0.1876 USDC net after 0.0024 fee); 0.20 USDC burn without matching bridge record.",
    },
    "prod_control": {
        "id": "prod_control",
        "label": "Production Control (1.00 USDC observed via FastNEAR fallback)",
        "txHash": "FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu",
        "signerId": "sponsor.trezu.near",
        "capturedAt": "2026-11-11T01:16:56Z",
        "fixture": "fixtures/control_prod_fd7g.json",
        "summary": "1.00 USDC burn observed on Base (0.9976 USDC net after 0.0024 fee); verified via FastNEAR fallback when primary dRPC timed out.",
    },
}


def _classify_overall(overall_text: str) -> str:
    """Classify plain overall text into canonical UI verdict code."""
    prefix_map = [
        ("ALL_ROWS_OBSERVED", "ALL_ROWS_OBSERVED"),
        ("MISMATCH", "MISMATCH"),
        ("IN_PROGRESS", "IN_PROGRESS"),
        ("INCONCLUSIVE", "INCONCLUSIVE"),
        ("INVALID_EVIDENCE", "INVALID_EVIDENCE"),
        ("UNSUPPORTED_SOURCE", "UNSUPPORTED_SOURCE"),
    ]
    for prefix, code in prefix_map:
        if overall_text.startswith(prefix):
            return code
    return "NEEDS_INSPECTION"


def _build_envelope(
    mode: str,
    example_id: str | None,
    tx_hash: str,
    signer_id: str | None,
    source: str,
    source_status: str,
    final_execution_status: str,
    captured_at: str,
    generated_at: str,
    summary: dict,
    results: list[dict],
    rows: list[dict],
    records: list[dict],
    dest: dict,
    per_leg_errors: dict | None = None,
) -> dict:
    """Build the structured schemaVersion: "1" report envelope."""
    per_leg_errors = per_leg_errors or {}
    overall_text = summary.get("overall", "INCONCLUSIVE — unknown finding")
    overall_code = _classify_overall(overall_text)

    # Normalize evidence collections with stable IDs
    norm_burns = []
    for idx, r in enumerate(rows):
        norm_burns.append({
            "id": f"burn-{idx}",
            "rowIndex": idx,
            "recipient": r.get("recipient"),
            "amount": to_str_amount(r.get("amount")),
            "amountFormatted": format_usdc(r.get("amount")),
            "burnOwner": r.get("burn_owner"),
            "executor": r.get("executor"),
            "outcomeId": r.get("outcome_id"),
            "logIndex": r.get("log_index"),
            "outcomeStatus": r.get("outcome_status"),
            "source": r.get("source"),
            "unsupported": r.get("unsupported"),
            "malformedEvent": r.get("malformed_event"),
        })

    norm_records = []
    for idx, r in enumerate(records or []):
        norm_records.append({
            "id": f"bridge-{idx}",
            "recordIndex": idx,
            "status": r.get("status"),
            "txHash": r.get("tx_hash"),
            "transferTxHash": r.get("transfer_tx_hash"),
            "chain": r.get("chain"),
            "amount": to_str_amount(r.get("amount")),
            "amountFormatted": format_usdc(r.get("amount")),
            "fee": to_str_amount(r.get("fee")),
            "feeFormatted": format_usdc(r.get("fee")),
            "withdrawAmount": to_str_amount(r.get("withdraw_amount")),
            "withdrawAmountFormatted": format_usdc(r.get("withdraw_amount")),
            "decimals": r.get("decimals"),
            "nearTokenId": r.get("near_token_id"),
            "defuseAsset": r.get("defuse_asset"),
            "createdAt": r.get("created_at"),
            "scopeProblems": r.get("scope_problems") or [],
            "invalidAccounting": r.get("invalid_accounting"),
        })

    norm_dest = []
    dest_tx_links = []
    for key, d in dest.items():
        chain, transfer_tx, amt_str = key
        transfers = d.get("transfers") or []
        for t_idx, t in enumerate(transfers):
            transfer_entry = {
                "id": f"dest-{len(norm_dest)}",
                "chain": chain,
                "transferTxHash": transfer_tx,
                "amount": to_str_amount(t.get("amount")),
                "amountFormatted": format_usdc(t.get("amount")),
                "to": t.get("to"),
                "logIndex": t.get("log_index"),
                "receiptStatus": d.get("receipt_status"),
                "block": d.get("block"),
                "confirmations": d.get("confirmations"),
                "tip": d.get("tip"),
                "label": d.get("label"),
                "error": d.get("error"),
                "explorerUrl": f"https://basescan.org/tx/{transfer_tx}",
            }
            norm_dest.append(transfer_entry)
            if f"https://basescan.org/tx/{transfer_tx}" not in dest_tx_links:
                dest_tx_links.append(f"https://basescan.org/tx/{transfer_tx}")

    # Process row findings
    structured_rows = []
    for f_idx, item in enumerate(results):
        row_val = item.get("row")
        verdict = item.get("verdict", "UNKNOWN")
        recipient = item.get("recipient")
        amount = item.get("amount")
        note = item.get("note", "")

        # Group finding vs single row vs extras
        if verdict == "GROUP_FINDING" and isinstance(row_val, list):
            kind = "group"
            row_indices = row_val
            group_details = {
                "rowsInGroup": item.get("rows_in_group", len(row_indices)),
                "recordsMatched": item.get("records_matched", 0),
                "observed": item.get("observed", 0),
                "unrecorded": item.get("unrecorded", 0),
                "pending": item.get("pending", 0),
                "unavailable": item.get("unavailable", 0),
                "invalidDest": item.get("invalid_dest", 0),
                "invalidRecord": item.get("invalid_record", 0),
                "reverted": item.get("reverted", 0),
                "noTransfer": item.get("no_transfer", 0),
            }
        elif row_val is not None:
            kind = "single"
            row_indices = [row_val] if isinstance(row_val, int) else row_val
            group_details = None
        elif verdict == "UNMATCHED_BRIDGE_RECORD":
            kind = "unmatched_bridge"
            row_indices = []
            group_details = None
        elif verdict == "UNMATCHED_DEST_TRANSFER":
            kind = "unmatched_dest"
            row_indices = []
            group_details = None
        elif verdict == "INVALID_RECORD":
            kind = "invalid_record"
            row_indices = []
            group_details = None
        else:
            kind = "extra"
            row_indices = []
            group_details = None

        # Project the reader's recorded matches by exact destination log identity.
        # This selects evidence already named by the reader; it makes no new
        # matching decisions. Keep all observed group members, not just the first.
        observed_transfers = []
        seen_logs = set()
        expected_observed = (group_details["observed"] if group_details
                             else int(verdict == "OBSERVED_MATCH"))
        for transfer_tx, log_index in re.findall(
            r"dest tx (0x[0-9a-fA-F]{64}) log (\d+) pays ", note
        ):
            identity = (transfer_tx, int(log_index))
            if identity in seen_logs:
                continue
            seen_logs.add(identity)
            dest_ref = next((d for d in norm_dest
                             if d["transferTxHash"] == transfer_tx
                             and d["logIndex"] == int(log_index)
                             and (d["to"] or "").lower() == (recipient or "").lower()), None)
            bridge_ref = next((b for b in norm_records
                               if dest_ref and b["transferTxHash"] == transfer_tx
                               and b["status"] == "COMPLETED"
                               and b["amount"] == to_str_amount(amount)
                               and b["withdrawAmount"] == dest_ref["amount"]), None)
            if not dest_ref or not bridge_ref:
                continue
            observed_transfers.append({
                "bridgeRecord": {key: bridge_ref[key] for key in (
                    "transferTxHash", "chain", "fee", "feeFormatted",
                    "withdrawAmount", "withdrawAmountFormatted")},
                "destTransfer": {key: dest_ref[key] for key in (
                    "transferTxHash", "logIndex", "receiptStatus", "block",
                    "confirmations", "explorerUrl")},
            })

        projection_warning = None
        if len(observed_transfers) != expected_observed:
            # Never publish a partial monetary total as the whole observed total.
            projection_warning = "Observed evidence projection incomplete; inspect original reader note."
            observed_transfers = []
        evidence_bridge = observed_transfers[0]["bridgeRecord"] if observed_transfers else None
        evidence_dest = observed_transfers[0]["destTransfer"] if observed_transfers else None
        evidenced_fee = (sum(int(x["bridgeRecord"]["fee"]) for x in observed_transfers)
                         if observed_transfers else None)
        evidenced_net = (sum(int(x["bridgeRecord"]["withdrawAmount"]) for x in observed_transfers)
                         if observed_transfers else None)
        evidence_burn = None
        group_burns = None
        if kind == "group":
            group_burns = [
                {"rowIndex": idx, **{key: norm_burns[idx][key] for key in (
                    "outcomeId", "logIndex", "executor")}}
                for idx in row_indices if idx < len(norm_burns)
            ]
        elif kind == "single" and row_indices and row_indices[0] < len(norm_burns):
            evidence_burn = {key: norm_burns[row_indices[0]][key] for key in (
                "outcomeId", "logIndex", "burnOwner", "executor")}

        structured_rows.append({
            "id": f"finding-{f_idx}",
            "kind": kind,
            "rowIndices": row_indices,
            "recipient": recipient,
            "verdict": verdict,
            "amounts": {
                "gross": to_str_amount(amount),
                "grossFormatted": format_usdc(amount),
                "fee": to_str_amount(evidenced_fee),
                "feeFormatted": format_usdc(evidenced_fee),
                "net": to_str_amount(evidenced_net),
                "netFormatted": format_usdc(evidenced_net),
            },
            "groupDetails": group_details,
            "evidence": {
                "sourceBurn": evidence_burn,
                "groupBurns": group_burns,
                "bridgeRecord": evidence_bridge,
                "destTransfer": evidence_dest,
                "observedTransfers": observed_transfers,
                "projectionWarning": projection_warning,
            },
            "note": note,
        })

    # Summary counts
    counts = summary.get("counts", {})
    completeness = summary.get("completeness", {})

    envelope = {
        "schemaVersion": "1",
        "request": {
            "mode": mode,
            "exampleId": example_id,
            "txHash": tx_hash,
            "signerId": signer_id,
        },
        "supported": {
            "sourceToken": pp.SUPPORTED["source_token"],
            "bridgeChain": pp.SUPPORTED["bridge_chain"],
            "bridgeAsset": pp.SUPPORTED["bridge_asset"],
            "destChain": pp.SUPPORTED["dest_chain"],
            "destToken": pp.SUPPORTED["dest_token"],
            "decimals": pp.SUPPORTED["decimals"],
        },
        "provenance": {
            "readerVersion": READER_VERSION,
            "readerSha256": READER_SHA256,
            "generatedAt": generated_at,
            "capturedAt": captured_at,
            "sourceProvider": source,
            "sourceStatus": source_status,
            "finalExecutionStatus": final_execution_status,
        },
        "summary": {
            "overall": overall_text,
            "overallCode": overall_code,
            "counts": counts,
            "completeness": completeness,
            "burnDiag": summary.get("burn_diag", {}),
            "listCheck": summary.get("list_state", "not requested"),
            "disclaimer": pp.DISCLAIMER,
        },
        "counts": {
            "sourceBurns": len(norm_burns),
            "bridgeRecords": len(norm_records),
            "destTransfers": len(norm_dest),
            "findings": len(structured_rows),
            "observedMatches": counts.get("OBSERVED_MATCH", 0),
            "unrecorded": counts.get("NOT_RECORDED", 0),
            "pending": counts.get("IN_PROGRESS", 0),
            "groupFindings": counts.get("GROUP_FINDING", 0),
        },
        "rows": structured_rows,
        "normalizedEvidence": {
            "sourceBurns": norm_burns,
            "bridgeWithdrawals": norm_records,
            "destTransfers": norm_dest,
            "perLegErrors": per_leg_errors,
        },
        "explorerLinks": {
            "nearTx": f"https://nearblocks.io/txns/{tx_hash}" if tx_hash else None,
            "nearSigner": f"https://nearblocks.io/address/{signer_id}" if signer_id else None,
            "bridge": "https://bridge.chaindefuser.com",
            "baseToken": f"https://basescan.org/token/{pp.SUPPORTED['dest_token']}",
            "destTransfers": dest_tx_links,
        },
    }
    return envelope


def reconcile_fixture(case_data: dict, example_id: str | None = None) -> dict:
    """Run reconciliation over a saved fixture using unchanged reader functions."""
    now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    legs = case_data.get("legs", {})
    tx_hash = case_data.get("near_tx", "")
    signer_id = case_data.get("signer")
    captured_at = case_data.get("captured_at") or case_data.get("capture_time") or now_ts

    near = legs.get("near_raw", {})
    source = legs.get("near_source", "drpc")
    if source == "fastnear" and "transaction" in near and "receipts" not in near:
        near = pp._normalize_fastnear_tx(near)
        near["_source"] = "fastnear"

    if source == "drpc":
        source_status = pp.normalize_status(near.get("status")) if isinstance(near.get("status"), (dict, str)) else "Unknown"
    else:
        eo = near.get("execution_outcome")
        eo_out = eo.get("outcome") if isinstance(eo, dict) else None
        source_status = pp.normalize_status(eo_out.get("status")) if isinstance(eo_out, dict) else "Unknown"

    finality = near.get("final_execution_status", "fixture")

    rows, diag = pp.extract_burns(near, source)
    completeness = pp.analyze_completeness(near, source)

    bridge_raw = legs.get("bridge_raw", {"withdrawals": []})
    nbridged = pp.normalize_bridge(bridge_raw)
    if nbridged is None:
        summary = {"overall": "INCONCLUSIVE — bridge raw response malformed", "counts": {"INCONCLUSIVE": 1}, "completeness": completeness}
        return _build_envelope(
            mode="saved",
            example_id=example_id,
            tx_hash=tx_hash,
            signer_id=signer_id,
            source=source,
            source_status=source_status,
            final_execution_status=finality,
            captured_at=captured_at,
            generated_at=now_ts,
            summary=summary,
            results=[],
            rows=rows,
            records=[],
            dest={},
            per_leg_errors={"bridge": "bridge raw response malformed"},
        )

    records, bridge_malformed = nbridged
    dest = {}
    tip = legs.get("dest_tip")
    for rec in records:
        if rec.get("scope_problems") or rec["chain"] != pp.SUPPORTED["dest_chain"] or not rec["transfer_tx_hash"] or rec["status"] != "COMPLETED":
            continue
        entry_spec = legs.get("dest_receipts")
        if isinstance(entry_spec, dict):
            receipt = entry_spec.get(rec["transfer_tx_hash"])
        else:
            receipt = legs.get("dest_receipt")
        key, entry = pp.build_dest_from_receipt(receipt, rec, tip)
        if legs.get("dest_unavailable"):
            entry = {"error": f"destination RPC unavailable: {legs['dest_unavailable']}"}
        dest[key] = entry

    fee_hint = None
    for r in (records or []):
        if r.get("fee"):
            fee_hint = r["fee"]
            break

    results = pp.reconcile(rows, records or [], dest, fee_hint=fee_hint)
    summary = pp.summarize(
        rows,
        diag,
        completeness,
        source_status,
        results,
        "not requested",
        bridge_malformed=bridge_malformed,
    )

    return _build_envelope(
        mode="saved",
        example_id=example_id,
        tx_hash=tx_hash,
        signer_id=signer_id,
        source=source,
        source_status=source_status,
        final_execution_status=finality,
        captured_at=captured_at,
        generated_at=now_ts,
        summary=summary,
        results=results,
        rows=rows,
        records=records or [],
        dest=dest,
    )


def reconcile_saved(example_id: str) -> dict:
    """Load allowlisted saved example and reconcile offline without network."""
    meta = SAVED_EXAMPLES_META.get(example_id)
    if not meta:
        raise ValueError(f"Unknown saved example ID: {example_id}")

    fixture_path = READER_DIR / meta["fixture"]
    case_data = json.loads(fixture_path.read_text())
    # Ensure signer is set from metadata if missing in fixture
    if not case_data.get("signer"):
        case_data["signer"] = meta["signerId"]
    case_data["captured_at"] = meta["capturedAt"]
    return reconcile_fixture(case_data, example_id=example_id)


def reconcile_live(tx_hash: str, signer_id: str) -> dict:
    """Fetch live data from NEAR, Bridge, and Base RPC providers and reconcile."""
    now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    per_leg_errors = {}

    # Leg 1: NEAR
    try:
        near = pp.fetch_near(tx_hash, signer_id)
    except Exception as e:
        err_msg = f"NEAR leg unavailable: {type(e).__name__}: {e}"
        per_leg_errors["near"] = err_msg
        summary = {
            "overall": f"INCONCLUSIVE — {err_msg}",
            "counts": {"INCONCLUSIVE": 1},
            "completeness": None,
        }
        return _build_envelope(
            mode="live",
            example_id=None,
            tx_hash=tx_hash,
            signer_id=signer_id,
            source="unavailable",
            source_status="Unknown",
            final_execution_status="unavailable",
            captured_at=now_ts,
            generated_at=now_ts,
            summary=summary,
            results=[],
            rows=[],
            records=[],
            dest={},
            per_leg_errors=per_leg_errors,
        )

    source = near.get("_source", "drpc")
    if source == "drpc":
        source_status = pp.normalize_status(near.get("status")) if isinstance(near.get("status"), (dict, str)) else "Unknown"
    else:
        eo = near.get("execution_outcome")
        eo_out = eo.get("outcome") if isinstance(eo, dict) else None
        source_status = pp.normalize_status(eo_out.get("status")) if isinstance(eo_out, dict) else "Unknown"
    finality = near.get("final_execution_status", "not_reported")

    rows, diag = pp.extract_burns(near, source)
    completeness = pp.analyze_completeness(near, source)

    # Leg 2: Bridge
    records = []
    bridge_malformed = False
    try:
        nbridged = pp.fetch_bridge(tx_hash)
        if nbridged is None:
            per_leg_errors["bridge"] = "bridge response malformed"
            summary = {
                "overall": "INCONCLUSIVE — bridge response malformed",
                "counts": {"INCONCLUSIVE": 1},
                "completeness": completeness,
            }
            return _build_envelope(
                mode="live",
                example_id=None,
                tx_hash=tx_hash,
                signer_id=signer_id,
                source=source,
                source_status=source_status,
                final_execution_status=finality,
                captured_at=now_ts,
                generated_at=now_ts,
                summary=summary,
                results=[],
                rows=rows,
                records=[],
                dest={},
                per_leg_errors=per_leg_errors,
            )
        records, bridge_malformed = nbridged
    except Exception as e:
        err_msg = f"bridge leg unavailable: {type(e).__name__}: {e}"
        per_leg_errors["bridge"] = err_msg
        summary = {
            "overall": f"INCONCLUSIVE — {err_msg}",
            "counts": {"INCONCLUSIVE": 1},
            "completeness": completeness,
        }
        return _build_envelope(
            mode="live",
            example_id=None,
            tx_hash=tx_hash,
            signer_id=signer_id,
            source=source,
            source_status=source_status,
            final_execution_status=finality,
            captured_at=now_ts,
            generated_at=now_ts,
            summary=summary,
            results=[],
            rows=rows,
            records=[],
            dest={},
            per_leg_errors=per_leg_errors,
        )

    # Leg 3: Destination (Base)
    dest = {}
    try:
        dest = pp.fetch_dest(records)
    except Exception as e:
        err_msg = f"destination leg error: {type(e).__name__}: {e}"
        per_leg_errors["destination"] = err_msg

    fee_hint = None
    for r in (records or []):
        if r.get("fee"):
            fee_hint = r["fee"]
            break

    results = pp.reconcile(rows, records or [], dest, fee_hint=fee_hint)
    summary = pp.summarize(
        rows,
        diag,
        completeness,
        source_status,
        results,
        "not requested",
        bridge_malformed=bridge_malformed,
    )

    return _build_envelope(
        mode="live",
        example_id=None,
        tx_hash=tx_hash,
        signer_id=signer_id,
        source=source,
        source_status=source_status,
        final_execution_status=finality,
        captured_at=now_ts,
        generated_at=now_ts,
        summary=summary,
        results=results,
        rows=rows,
        records=records or [],
        dest=dest,
        per_leg_errors=per_leg_errors,
    )
