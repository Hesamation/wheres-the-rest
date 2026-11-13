"""Worker process executing reconciliation in isolated subprocess.

Invoked with:
  python3 -m app.worker --mode saved --example-id <id> --out-file <path>
  python3 -m app.worker --mode live --tx <hash> --signer <acct> --out-file <path>

Isolates memory, network logs (RAW_LOG), and external provider requests.
Writes validated schemaVersion: "1" envelope directly to out-file.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.adapter import reconcile_live, reconcile_saved  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Payout reconciliation subprocess worker")
    parser.add_argument("--mode", required=True, choices=["live", "saved"])
    parser.add_argument("--example-id", dest="example_id", default=None)
    parser.add_argument("--tx", dest="tx_hash", default=None)
    parser.add_argument("--signer", dest="signer_id", default=None)
    parser.add_argument("--out-file", dest="out_file", required=True)

    args = parser.parse_args()
    out_path = Path(args.out_file)

    try:
        if args.mode == "saved":
            if not args.example_id:
                sys.stderr.write("Missing --example-id for saved mode\n")
                return 1
            envelope = reconcile_saved(args.example_id)
        else:
            if not args.tx_hash or not args.signer_id:
                sys.stderr.write("Missing --tx or --signer for live mode\n")
                return 1
            envelope = reconcile_live(args.tx_hash, args.signer_id)

        # Write envelope atomically to out_file
        temp_out = out_path.with_suffix(".tmp")
        temp_out.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
        temp_out.replace(out_path)
        return 0

    except Exception as exc:
        # Fallback conservative inconclusive report without leaking traceback or internal paths
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        fallback_envelope = {
            "schemaVersion": "1",
            "request": {
                "mode": args.mode,
                "exampleId": args.example_id,
                "txHash": args.tx_hash,
                "signerId": args.signer_id,
            },
            "summary": {
                "overall": f"INCONCLUSIVE — Worker reconciliation error: {type(exc).__name__}",
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
        try:
            out_path.write_text(json.dumps(fallback_envelope, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
