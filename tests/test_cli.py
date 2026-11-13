"""Tests for app.cli command line interface."""
import json
import contextlib
import io
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from app import cli


def test_cli_help():
    res = subprocess.run([sys.executable, "main.py", "--help"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    assert "Payout Reader" in res.stdout
    assert "--serve" in res.stdout
    assert "--saved" in res.stdout
    assert "--live" in res.stdout
    assert "--check" in res.stdout


def test_cli_saved_json():
    for ex_id in ["qa1", "qa2", "prod_control"]:
        res = subprocess.run(
            [sys.executable, "main.py", "--saved", ex_id, "--json"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"Saved {ex_id} failed: {res.stderr}"
        data = json.loads(res.stdout)
        assert data["schemaVersion"] == "1"
        assert data["request"]["exampleId"] == ex_id
        assert "overallCode" in data["summary"]
        assert len(data["rows"]) >= 1


def test_cli_saved_csv():
    res = subprocess.run(
        [sys.executable, "main.py", "--saved", "prod_control", "--csv"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "row_indices,row_type,recipient,gross_usdc" in res.stdout
    assert "OBSERVED_MATCH" in res.stdout
    assert "0.997600" in res.stdout


def test_cli_saved_human():
    res = subprocess.run(
        [sys.executable, "main.py", "--saved", "prod_control"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "PAYOUT RECONCILIATION REPORT (SAVED)" in res.stdout
    assert "ALL_ROWS_OBSERVED" in res.stdout
    assert "0.997600" in res.stdout  # net payout


def test_cli_validation_errors():
    # Live without signer
    res = subprocess.run(
        [sys.executable, "main.py", "--live", "FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "requires --signer" in res.stderr

    # Live with invalid tx
    res = subprocess.run(
        [sys.executable, "main.py", "--live", "not-a-valid-tx", "--signer", "sponsor.trezu.near"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "Invalid NEAR transaction hash" in res.stderr


def test_live_machine_output():
    report = {"schemaVersion": "1", "request": {}, "rows": [], "summary": {}}
    for flag in ("--json", "--csv"):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(cli, "run_worker", return_value=report), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            assert cli.main(["--live", "FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu",
                             "--signer", "sponsor.trezu.near", flag]) == 0
        assert "Reconciling" in stderr.getvalue()
        if flag == "--json":
            assert json.loads(stdout.getvalue()) == report
        else:
            assert stdout.getvalue().startswith("row_indices,row_type,")


def test_check_failure_is_not_reported_as_passed():
    failed = subprocess.CompletedProcess([], 1, stdout="", stderr="simulated failure")
    stdout = io.StringIO()
    with patch.object(cli.subprocess, "run", return_value=failed), contextlib.redirect_stdout(stdout):
        assert cli.run_checks() == 1
    assert "PASSED." not in stdout.getvalue()
    assert "failures above" in stdout.getvalue()


if __name__ == "__main__":
    test_cli_help()
    test_cli_saved_json()
    test_cli_saved_csv()
    test_cli_saved_human()
    test_cli_validation_errors()
    test_live_machine_output()
    test_check_failure_is_not_reported_as_passed()
    print("test_cli PASSED")
