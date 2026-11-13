#!/usr/bin/env python3
"""Regression replay of the six previously-fixed counterexamples (from
INVARIANTS-PACKAGE-REVIEW.md) PLUS the four v4 boundary counterexamples, through
the full pipeline (run_case with endpoint-shaped fixture inputs; no injected
verdict/completeness flags).

Usage: python3 repro_all.py   (from the payout-feasibility package directory)
Writes results/repro_all/*.json|txt and prints a summary. Exit 0 = all match
the required conservative classes.
"""
import contextlib, copy, importlib.util, io, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "repro_all"
OUT.mkdir(parents=True, exist_ok=True)

import payout_probe as pp

single = json.loads((HERE / "fixtures/fx_g1_drpc_observed.json").read_text())
grouped = json.loads((HERE / "fixtures/fx_g3_grouped_rows.json").read_text())
findings = {}

def run(name, case):
    case["name"] = name
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        report = pp.run_case(case, OUT)
    findings[name] = report["summary"]["overall"]
    return report

def group_two():
    c = copy.deepcopy(grouped)
    c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]["logs"] = \
        c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]["logs"][:2]
    rec = c["legs"]["bridge_raw"]["withdrawals"][0]
    other = copy.deepcopy(rec); other["data"]["transfer_tx_hash"] = "0x" + "4" * 64
    c["legs"]["bridge_raw"]["withdrawals"].append(other)
    return c

# --- the six previously-fixed cases -------------------------------------
c = group_two()
for rec in c["legs"]["bridge_raw"]["withdrawals"]:
    rec["status"] = "PENDING"; rec["data"]["transfer_tx_hash"] = None
c["legs"]["bridge_raw"]["withdrawals"][1]["data"]["tx_hash"] = "TX_G2"
c["legs"]["dest_receipts"] = {}
run("group_all_pending", c)

c = group_two(); c["legs"]["dest_unavailable"] = "timeout"
run("group_destination_unavailable", c)

c = group_two()
for rec in c["legs"]["bridge_raw"]["withdrawals"]:
    c["legs"]["dest_receipts"][rec["data"]["transfer_tx_hash"]] = \
        {"status": "0x1", "blockNumber": "0x64", "logs": []}
run("group_zero_matching_transfers", c)

c = copy.deepcopy(single)
c["legs"]["bridge_raw"]["withdrawals"][0]["data"]["withdrawal_fee"] = "999"
run("inconsistent_fee_arithmetic", c)

c = copy.deepcopy(single)
raw = c["legs"]["near_raw"]
raw["receipts_outcome"][0]["outcome"]["receipt_ids"] = ["missing-child"]
raw["receipts_outcome"].append({"id": "missing-child"})
run("reachable_outcome_wrapper_without_execution", c)

c = copy.deepcopy(single)
tx = next(iter(c["legs"]["dest_receipts"]))
c["legs"]["dest_receipts"][tx]["transactionHash"] = "0x" + "f" * 64
run("receipt_transaction_hash_mismatch", c)

# --- the four v4 boundary cases -----------------------------------------
c = copy.deepcopy(single)
del c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]["receipt_ids"]
run("missing_child_edges_field", c)

c = copy.deepcopy(single)
d = c["legs"]["bridge_raw"]["withdrawals"][0]["data"]
d["amount"] = 10000.75; d["withdrawal_fee"] = 2400.5; d["withdraw_amount"] = 7600.25
run("fractional_integer_fields", c)

c = copy.deepcopy(single)
c["legs"]["bridge_raw"]["withdrawals"].append(None)
run("malformed_extra_bridge_record", c)

c = copy.deepcopy(single)
oc = c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]
ev = json.loads(oc["logs"][0].split("EVENT_JSON:", 1)[1])
ev["data"][0]["amount"] = "not-an-integer"
oc["logs"][0] = "EVENT_JSON:" + json.dumps(ev)
run("malformed_source_burn_amount", c)   # must NOT raise

EXPECTED = {
    "group_all_pending": "IN_PROGRESS",
    "group_destination_unavailable": "INCONCLUSIVE",
    "group_zero_matching_transfers": "MISMATCH",
    "inconsistent_fee_arithmetic": "INVALID_EVIDENCE",
    "reachable_outcome_wrapper_without_execution": "INCOMPLETE_EVIDENCE",
    "receipt_transaction_hash_mismatch": "INCONCLUSIVE",
    "missing_child_edges_field": "INCOMPLETE_EVIDENCE",
    "fractional_integer_fields": "INVALID_EVIDENCE",
    "malformed_extra_bridge_record": "INVALID_EVIDENCE",
    "malformed_source_burn_amount": "INVALID_EVIDENCE",
}
bad = []
for name, overall in findings.items():
    want = EXPECTED[name]
    ok = overall.startswith(want)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {overall}")
    if not ok:
        bad.append(name)
(OUT / "summary.json").write_text(json.dumps(
    {"findings": findings, "expected": EXPECTED,
     "failures": bad}, indent=2) + "\n")
print(f"\n{'REPRO ALL PASSED (10/10)' if not bad else 'FAILURES: ' + ', '.join(bad)}")
sys.exit(1 if bad else 0)
