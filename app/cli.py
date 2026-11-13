"""CLI entrypoint for payout reader.

Commands:
  python3 main.py --serve [--port 8765] [--host 127.0.0.1]
  python3 main.py --saved <qa1|qa2|prod_control> [--json]
  python3 main.py --live <tx_hash> --signer <account_id> [--json]
  python3 main.py --check
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.adapter import SAVED_EXAMPLES_META  # noqa: E402
from app.formatting import report_to_csv  # noqa: E402
from app.runner import run_worker  # noqa: E402
from app.server import run_server  # noqa: E402
from app.validation import is_valid_near_account_id, is_valid_near_tx_hash  # noqa: E402


def print_human_report(envelope: dict) -> None:
    """Print readable human summary of report envelope."""
    req = envelope.get("request", {})
    prov = envelope.get("provenance", {})
    summary = envelope.get("summary", {})
    counts = envelope.get("counts", {})
    rows = envelope.get("rows", [])

    print("=" * 70)
    mode_str = req.get("mode", "unknown").upper()
    ex_id = req.get("exampleId")
    tx_hash = req.get("txHash")
    signer = req.get("signerId")

    title = f"PAYOUT RECONCILIATION REPORT ({mode_str})"
    if ex_id:
        title += f" [Example: {ex_id}]"
    print(title)
    print("=" * 70)
    print(f"Transaction : {tx_hash}")
    print(f"Signer      : {signer or '-'}")
    print(f"Captured At : {prov.get('capturedAt')}")
    print(f"Generated At: {prov.get('generatedAt')}")
    print(f"Source Leg  : {prov.get('sourceProvider')} (status: {prov.get('sourceStatus')}, finality: {prov.get('finalExecutionStatus')})")
    print("-" * 70)
    print(f"OVERALL     : {summary.get('overall')}")
    print(f"Counts      : {summary.get('counts')}")
    comp = summary.get("completeness") or {}
    print(f"Completeness: {comp.get('complete')} ({comp.get('reason')})")
    print("-" * 70)
    print("FINDINGS / WITHDRAWAL ROWS:")
    if not rows:
        print("  (No withdrawal rows found or processed)")
    for r in rows:
        r_kind = r.get("kind")
        r_indices = r.get("rowIndices") or []
        row_str = f"Row {r_indices}" if r_indices else f"[{r_kind}]"
        recip = r.get("recipient") or "-"
        amts = r.get("amounts") or {}
        gross_fmt = amts.get("grossFormatted") or "-"
        fee_fmt = amts.get("feeFormatted")
        net_fmt = amts.get("netFormatted")

        amt_display = f"{gross_fmt} USDC"
        if fee_fmt and net_fmt:
            amt_display += f" (fee: {fee_fmt}, net: {net_fmt})"

        print(f"  {row_str:<14} {amt_display:<35} -> {recip}")
        print(f"    Verdict : {r.get('verdict')}")
        if r.get("groupDetails"):
            gd = r["groupDetails"]
            print(f"    Group   : {gd['rowsInGroup']} rows, {gd['observed']} observed, {gd['unrecorded']} unrecorded, {gd['pending']} pending")
        print(f"    Note    : {r.get('note')}")
    print("-" * 70)
    print(f"DISCLAIMER  : {summary.get('disclaimer')}")
    print("=" * 70)


def run_checks() -> int:
    """Run all test suites and verifiers offline."""
    print("Running test suites and offline verifiers...\n")
    reader_dir = REPO_ROOT / "reader"

    all_passed = True
    # 1. Unchanged reader test suites
    for script in ["run_tests.py", "verify_outputs.py", "run_invariants.py", "repro_all.py"]:
        print(f"--> reader/{script}")
        res = subprocess.run([sys.executable, "-B", script], cwd=str(reader_dir), capture_output=True, text=True)
        passes = res.stdout.count("[PASS]")
        fails = res.stdout.count("[FAIL]")
        print(f"    Exit: {res.returncode}, PASS: {passes}, FAIL: {fails}")
        if res.returncode != 0 or fails > 0:
            all_passed = False
            print("    OUTPUT:\n", res.stdout[-600:])
            print("    ERROR:\n", res.stderr)

    # 2. Application tests
    test_files = sorted((REPO_ROOT / "tests").glob("test_*.py"))
    for tf in test_files:
        print(f"--> tests/{tf.name}")
        res = subprocess.run([sys.executable, "-B", str(tf)], cwd=str(REPO_ROOT), capture_output=True, text=True)
        print(f"    Exit: {res.returncode}")
        if res.returncode != 0:
            all_passed = False
            print("    OUTPUT:\n", res.stdout)
            print("    ERROR:\n", res.stderr)
        else:
            print("    " + res.stdout.strip().replace("\n", "\n    "))

    if all_passed:
        print("\nALL CHECKS PASSED SUCCESSFULLY (Exit 0).")
        return 0
    else:
        print("\nSOME CHECKS FAILED (Exit 1).")
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Payout Reader — NEAR USDC cross-chain payout audit tool")
    parser.add_argument("--serve", action="store_true", help="Start local web server")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Server port (default: 8765)")
    parser.add_argument("--saved", choices=list(SAVED_EXAMPLES_META.keys()), help="Run reconciliation on a saved example")
    parser.add_argument("--live", dest="live_tx", help="NEAR transaction hash for live reconciliation")
    parser.add_argument("--signer", dest="live_signer", help="NEAR signer account ID (required with --live)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON envelope instead of formatted text")
    parser.add_argument("--csv", action="store_true", help="Output reconciliation rows as CSV for accounting/spreadsheets")
    parser.add_argument("--check", action="store_true", help="Run full test suite and verifier checks offline")

    args = parser.parse_args(argv)

    if args.check:
        return run_checks()

    if args.serve:
        run_server(host=args.host, port=args.port)
        return 0

    if args.saved:
        envelope = run_worker(mode="saved", example_id=args.saved)
        if args.json:
            print(json.dumps(envelope, indent=2))
        elif args.csv:
            sys.stdout.write(report_to_csv(envelope))
        else:
            print_human_report(envelope)
        return 0

    if args.live_tx:
        if not args.live_signer:
            sys.stderr.write("Error: --live requires --signer <account_id>\n")
            return 1
        if not is_valid_near_tx_hash(args.live_tx):
            sys.stderr.write(f"Error: Invalid NEAR transaction hash: {args.live_tx}\n")
            return 1
        if not is_valid_near_account_id(args.live_signer):
            sys.stderr.write(f"Error: Invalid NEAR account ID: {args.live_signer}\n")
            return 1

        print(f"Reconciling live payout for tx {args.live_tx} (signer: {args.live_signer})...")
        envelope = run_worker(mode="live", tx_hash=args.live_tx, signer_id=args.live_signer)
        if args.json:
            print(json.dumps(envelope, indent=2))
        elif args.csv:
            sys.stdout.write(report_to_csv(envelope))
        else:
            print_human_report(envelope)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
