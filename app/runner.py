"""Process manager and isolated subprocess runner for payout reader reconciliations.

Enforces:
- Single active reconciliation worker (busy rejection)
- Subprocess isolation
- Request-local temporary output file
- Bounded execution deadline (120s max for live, 15s for saved)
- Guaranteed cleanup of temp files and processes
- Conservative inconclusive report on timeout or worker crash
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_WORKER_LOCK = threading.Lock()


class BusyError(Exception):
    """Raised when another reconciliation worker is already running."""
    pass


def run_worker(
    mode: str,
    example_id: str | None = None,
    tx_hash: str | None = None,
    signer_id: str | None = None,
    timeout: int | None = None,
) -> dict:
    """Run reconciliation in a fresh subprocess with strict isolation and timeout."""
    if timeout is None:
        timeout = 15 if mode == "saved" else 120

    # Permit one active reconciliation; reject overlap
    if not _WORKER_LOCK.acquire(blocking=False):
        raise BusyError("Reconciliation worker busy. Only one reconciliation may run at a time.")

    fd, temp_path_str = tempfile.mkstemp(prefix="payout-worker-", suffix=".json")
    os.close(fd)
    temp_path = Path(temp_path_str)

    cmd = [
        sys.executable,
        "-m",
        "app.worker",
        "--mode",
        mode,
        "--out-file",
        str(temp_path),
    ]
    if mode == "saved" and example_id:
        cmd.extend(["--example-id", example_id])
    if mode == "live":
        if tx_hash:
            cmd.extend(["--tx", tx_hash])
        if signer_id:
            cmd.extend(["--signer", signer_id])

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(timeout=timeout)
        exit_code = proc.returncode

        if temp_path.exists() and temp_path.stat().st_size > 0:
            content = temp_path.read_text(encoding="utf-8")
            data = json.loads(content)
            return data

        # If worker produced no output file
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return {
            "schemaVersion": "1",
            "request": {"mode": mode, "exampleId": example_id, "txHash": tx_hash, "signerId": signer_id},
            "summary": {
                "overall": f"INCONCLUSIVE — Worker failed with exit code {exit_code}",
                "overallCode": "INCONCLUSIVE",
                "counts": {"INCONCLUSIVE": 1},
                "completeness": None,
                "disclaimer": "missing observations are ambiguous, not proof of permanent loss; OBSERVED_MATCH is receipt-level evidence, not final settlement; no bridge root cause is established by absence of records",
            },
            "rows": [],
            "counts": {"findings": 0, "observedMatches": 0, "unrecorded": 0, "pending": 0},
            "provenance": {
                "generatedAt": now_ts,
                "capturedAt": now_ts,
                "sourceProvider": "error",
            },
        }

    except subprocess.TimeoutExpired:
        if proc:
            proc.kill()
            try:
                proc.communicate(timeout=5)
            except Exception:
                pass
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return {
            "schemaVersion": "1",
            "request": {"mode": mode, "exampleId": example_id, "txHash": tx_hash, "signerId": signer_id},
            "summary": {
                "overall": f"INCONCLUSIVE — Overall investigation deadline exceeded ({timeout}s)",
                "overallCode": "INCONCLUSIVE",
                "counts": {"INCONCLUSIVE": 1},
                "completeness": None,
                "disclaimer": "missing observations are ambiguous, not proof of permanent loss; OBSERVED_MATCH is receipt-level evidence, not final settlement; no bridge root cause is established by absence of records",
            },
            "rows": [],
            "counts": {"findings": 0, "observedMatches": 0, "unrecorded": 0, "pending": 0},
            "provenance": {
                "generatedAt": now_ts,
                "capturedAt": now_ts,
                "sourceProvider": "timeout",
            },
        }

    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        _WORKER_LOCK.release()
