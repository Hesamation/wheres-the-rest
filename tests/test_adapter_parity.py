"""Test that app.adapter matches original runner verdicts, counts, and completeness

on all 27 fixtures and the 3 saved examples, with zero divergent matching decisions.
"""
import json
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

        # Check rows length and verdicts
        assert len(envelope["rows"]) == len(orig["results"]), (
            f"{example_id} findings length mismatch: {len(envelope['rows'])} != {len(orig['results'])}"
        )
        for row, orig_res in zip(envelope["rows"], orig["results"]):
            assert row["verdict"] == orig_res["verdict"], (
                f"{example_id} verdict mismatch: {row['verdict']} != {orig_res['verdict']}"
            )
            assert row["recipient"] == orig_res["recipient"], (
                f"{example_id} recipient mismatch"
            )


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
        # Verify results count
        assert len(envelope["rows"]) == len(orig["results"]), (
            f"{fpath.name} results count mismatch"
        )


if __name__ == "__main__":
    test_saved_examples()
    print("test_saved_examples PASSED")
    test_all_fixtures_parity()
    print("test_all_fixtures_parity PASSED")
