"""Test that app.adapter matches original runner verdicts, counts, completeness,
and per-row evidence identities (outcome IDs, amounts, dest tx hashes)
on all 27 fixtures and the 3 saved examples, with zero divergent matching decisions.
"""
import json
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.adapter import SAVED_EXAMPLES_META, reconcile_fixture, reconcile_saved
import reader.payout_probe as pp
READER_DIR = REPO_ROOT / "reader"
FIXTURES_DIR = READER_DIR / "fixtures"


def _note_dest_tx(note: str | None) -> str | None:
    """Extract the dest tx hash the reader recorded in a note."""
    if not note:
        return None
    m = re.search(r"dest tx (0x[0-9a-fA-F]+)\s", note)
    return m.group(1) if m else None


def _assert_row_evidence(envelope_row: dict, orig_res: dict, label: str) -> None:
    """Assert per-row evidence identities and amounts match original reader output."""
    verdict = orig_res["verdict"]
    # Amount: adapter gross must equal original amount (as string)
    orig_amount_str = str(orig_res.get("amount", "")) if orig_res.get("amount") is not None else None
    env_gross = envelope_row["amounts"]["gross"]
    assert env_gross == orig_amount_str, (
        f"{label} gross amount mismatch: {env_gross!r} != {orig_amount_str!r}"
    )

    # For OBSERVED_MATCH and GROUP_FINDING: the dest tx in evidence must match the note
    expected_dest_tx = _note_dest_tx(orig_res.get("note"))
    if verdict == "OBSERVED_MATCH":
        # bridgeRecord must be populated
        bridge_ev = envelope_row["evidence"]["bridgeRecord"]
        assert bridge_ev is not None, f"{label} OBSERVED_MATCH missing bridgeRecord"
        if expected_dest_tx:
            assert bridge_ev["transferTxHash"] == expected_dest_tx, (
                f"{label} bridgeRecord.transferTxHash {bridge_ev['transferTxHash']!r} "
                f"!= note dest tx {expected_dest_tx!r}"
            )
        # destTransfer must be populated
        dest_ev = envelope_row["evidence"]["destTransfer"]
        assert dest_ev is not None, f"{label} OBSERVED_MATCH missing destTransfer"
        if expected_dest_tx:
            assert dest_ev["transferTxHash"] == expected_dest_tx, (
                f"{label} destTransfer.transferTxHash {dest_ev['transferTxHash']!r} "
                f"!= note dest tx {expected_dest_tx!r}"
            )
        # evidenced fee and net must be populated and non-negative
        assert envelope_row["amounts"]["fee"] is not None, f"{label} fee must be set for OBSERVED_MATCH"
        assert envelope_row["amounts"]["net"] is not None, f"{label} net must be set for OBSERVED_MATCH"

    elif verdict == "GROUP_FINDING":
        # groupBurns must list all row indices in the group
        orig_row_indices = orig_res.get("row", [])
        group_burns = envelope_row["evidence"]["groupBurns"] or []
        gb_indices = [b["rowIndex"] for b in group_burns]
        assert sorted(gb_indices) == sorted(orig_row_indices), (
            f"{label} groupBurns rowIndices {sorted(gb_indices)} != orig {sorted(orig_row_indices)}"
        )
        # If there is an observed match in the group (noted dest tx), bridge/dest evidence must be set
        if expected_dest_tx:
            bridge_ev = envelope_row["evidence"]["bridgeRecord"]
            assert bridge_ev is not None, f"{label} GROUP_FINDING with observed match missing bridgeRecord"
            assert bridge_ev["transferTxHash"] == expected_dest_tx, (
                f"{label} GROUP_FINDING bridgeRecord.transferTxHash {bridge_ev['transferTxHash']!r} "
                f"!= note dest tx {expected_dest_tx!r}"
            )
            dest_ev = envelope_row["evidence"]["destTransfer"]
            assert dest_ev is not None, f"{label} GROUP_FINDING with observed match missing destTransfer"
            assert dest_ev["transferTxHash"] == expected_dest_tx, (
                f"{label} GROUP_FINDING destTransfer.transferTxHash {dest_ev['transferTxHash']!r} "
                f"!= note dest tx {expected_dest_tx!r}"
            )

    elif verdict == "NOT_RECORDED":
        # No bridge/dest evidence should be attached
        assert envelope_row["evidence"]["bridgeRecord"] is None, (
            f"{label} NOT_RECORDED should have no bridgeRecord"
        )
        assert envelope_row["evidence"]["destTransfer"] is None, (
            f"{label} NOT_RECORDED should have no destTransfer"
        )
        # Fee and net must be absent (not evidence)
        assert envelope_row["amounts"]["fee"] is None, f"{label} NOT_RECORDED fee must be None"
        assert envelope_row["amounts"]["net"] is None, f"{label} NOT_RECORDED net must be None"


def test_saved_examples():
    """Verify the 3 saved examples in app.adapter match pp.run_case."""
    for example_id in ("qa1", "qa2", "prod_control"):
        meta = SAVED_EXAMPLES_META[example_id]
        fixture_file = READER_DIR / meta["fixture"]
        case = json.loads(fixture_file.read_text())

        # Original runner
        with tempfile.TemporaryDirectory() as td:
            orig = pp.run_case(case, Path(td))

        # Adapter
        envelope = reconcile_saved(example_id)

        # Check overall finding
        assert envelope["summary"]["overall"] == orig["summary"]["overall"], (
            f"{example_id} overall mismatch: {envelope['summary']['overall']} != {orig['summary']['overall']}"
        )

        # Check counts
        assert envelope["summary"]["counts"] == orig["summary"]["counts"], (
            f"{example_id} counts mismatch: {envelope['summary']['counts']} != {orig['summary']['counts']}"
        )

        # Check completeness
        assert envelope["summary"]["completeness"] == orig["summary"]["completeness"], (
            f"{example_id} completeness mismatch"
        )

        # Check rows length and per-row evidence
        assert len(envelope["rows"]) == len(orig["results"]), (
            f"{example_id} findings length mismatch: {len(envelope['rows'])} != {len(orig['results'])}"
        )
        for row, orig_res in zip(envelope["rows"], orig["results"]):
            label = f"{example_id} row={orig_res.get('row')} verdict={orig_res['verdict']}"
            assert row["verdict"] == orig_res["verdict"], (
                f"{label}: verdict mismatch {row['verdict']!r} != {orig_res['verdict']!r}"
            )
            assert row["recipient"] == orig_res["recipient"], (
                f"{label}: recipient mismatch"
            )
            _assert_row_evidence(row, orig_res, label)

        # Confirm no duplicate bridge record associations across OBSERVED_MATCH rows
        seen_bridge_txs = {}
        for row in envelope["rows"]:
            if row["verdict"] == "OBSERVED_MATCH":
                btx = (row["evidence"]["bridgeRecord"] or {}).get("transferTxHash")
                ri = row["rowIndices"][0] if row["rowIndices"] else None
                if btx:
                    assert btx not in seen_bridge_txs, (
                        f"{example_id}: bridgeRecord tx {btx} assigned to both row "
                        f"{seen_bridge_txs[btx]} and row {ri} (duplicate evidence)"
                    )
                    seen_bridge_txs[btx] = ri


def test_all_fixtures_parity():
    """Run all 27 fixtures through both pp.run_case and reconcile_fixture."""
    fixtures = sorted(FIXTURES_DIR.glob("*.json"))
    assert len(fixtures) >= 27

    for fpath in fixtures:
        case = json.loads(fpath.read_text())
        with tempfile.TemporaryDirectory() as td:
            orig = pp.run_case(case, Path(td))

        envelope = reconcile_fixture(case)

        # Verify overall
        assert envelope["summary"]["overall"] == orig["summary"]["overall"], (
            f"{fpath.name} overall mismatch: {envelope['summary']['overall']} != {orig['summary']['overall']}"
        )
        # Verify counts
        assert envelope["summary"]["counts"] == orig["summary"]["counts"], (
            f"{fpath.name} counts mismatch"
        )
        # Verify results count and per-row evidence
        assert len(envelope["rows"]) == len(orig["results"]), (
            f"{fpath.name} results count mismatch"
        )
        for row, orig_res in zip(envelope["rows"], orig["results"]):
            label = f"{fpath.name} row={orig_res.get('row')} verdict={orig_res['verdict']}"
            assert row["verdict"] == orig_res["verdict"], (
                f"{label}: verdict mismatch"
            )
            _assert_row_evidence(row, orig_res, label)

        # No duplicate bridge record associations across OBSERVED_MATCH rows in fixture
        seen_bridge_txs: dict[str, object] = {}
        for row in envelope["rows"]:
            if row["verdict"] == "OBSERVED_MATCH":
                btx = (row["evidence"]["bridgeRecord"] or {}).get("transferTxHash")
                ri = row["rowIndices"][0] if row["rowIndices"] else None
                if btx:
                    assert btx not in seen_bridge_txs, (
                        f"{fpath.name}: bridgeRecord tx {btx} assigned to both row "
                        f"{seen_bridge_txs[btx]} and row {ri}"
                    )
                    seen_bridge_txs[btx] = ri


def test_group_observed_totals_and_log_identity():
    # These fixtures exposed a projection bug: the reader found 2/3 payments,
    # but the application exported the fee and net for only the first one.
    for fixture, observed in [("fx_g3_permutation_rev.json", 2), ("fx_g6_list_spans_txs.json", 3)]:
        case = json.loads((FIXTURES_DIR / fixture).read_text())
        row = reconcile_fixture(case)["rows"][0]
        assert row["groupDetails"]["observed"] == observed
        assert row["amounts"]["fee"] == str(observed * 2400)
        assert row["amounts"]["net"] == str(observed * 7600)
        observations = row["evidence"]["observedTransfers"]
        assert len(observations) == observed
        from app.formatting import report_to_csv, report_to_markdown_proof
        envelope = reconcile_fixture(case)
        for observation in observations:
            tx = observation["destTransfer"]["transferTxHash"]
            assert tx in report_to_csv(envelope)
            assert tx in report_to_markdown_proof(envelope)
        assert len({(x["destTransfer"]["transferTxHash"], x["destTransfer"]["logIndex"])
                    for x in observations}) == observed


if __name__ == "__main__":
    test_saved_examples()
    print("test_saved_examples PASSED")
    test_all_fixtures_parity()
    print("test_all_fixtures_parity PASSED")
    test_group_observed_totals_and_log_identity()
    print("test_group_observed_totals_and_log_identity PASSED")
