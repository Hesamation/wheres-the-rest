import contextlib, copy, hashlib, importlib.util, io, json, re, shutil, subprocess, sys, tarfile, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parent / "payout-source-closeout-v5-20261111.tar.gz"
checks = {"archive_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(), "python": sys.version}
with tempfile.TemporaryDirectory(prefix="payout-reconciled-check-") as td:
    root = Path(td)
    with tarfile.open(ARCHIVE) as t:
        for m in t.getmembers():
            assert not Path(m.name).is_absolute() and ".." not in Path(m.name).parts and (m.isfile() or m.isdir())
        t.extractall(root, filter="data")
    pkg = root / "payout-feasibility"
    manifest = []
    for line in (root / "MANIFEST.txt").read_text().splitlines():
        m = re.match(r"^([a-f0-9]{64})  (.+)$", line)
        if m:
            f = root / m[2]
            manifest.append((m[2], f.is_file(), f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest() == m[1], m[1]))
    checks["manifest"] = {"entries": len(manifest), "present_matches": sum(x[2] for x in manifest), "present_mismatches": [x[0] for x in manifest if x[1] and not x[2]], "absent_references": [{"path": x[0], "matches_existing_workspace_copy": (HERE.parent / x[0]).is_file() and hashlib.sha256((HERE.parent / x[0]).read_bytes()).hexdigest() == x[3]} for x in manifest if not x[1]]}
    # Remove packaged outputs so the verifier MUST read the just-generated suite outputs.
    shutil.rmtree(pkg / "results")
    for script, label in [("run_tests.py", "suite"), ("verify_outputs.py", "verifier_fresh"), ("run_invariants.py", "generated_invariants"), ("repro_all.py", "ten_regressions")]:
        r = subprocess.run([sys.executable, "-B", script], cwd=pkg, capture_output=True, text=True)
        (HERE / (label + ".txt")).write_text(r.stdout + r.stderr)
        checks[label] = {"exit_code": r.returncode, "pass_assertions": r.stdout.count("[PASS]"), "fail_assertions": r.stdout.count("[FAIL]")}
    spec = importlib.util.spec_from_file_location("v5_probe", pkg / "payout_probe.py")
    pp = importlib.util.module_from_spec(spec); spec.loader.exec_module(pp)
    single = json.loads((pkg / "fixtures/fx_g1_drpc_observed.json").read_text())
    grouped = json.loads((pkg / "fixtures/fx_g3_grouped_rows.json").read_text())
    findings = {}
    def run(name, case):
        case["name"] = name
        with contextlib.redirect_stdout(io.StringIO()):
            report = pp.run_case(case, root / "adversarial")
        (HERE / (name + ".json")).write_text(json.dumps(report, indent=2) + "\n")
        findings[name] = {"overall": report["summary"]["overall"], "results": report["results"], "completeness": report["summary"]["completeness"]}
        return report
    def group_two():
        c = copy.deepcopy(grouped)
        c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]["logs"] = c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]["logs"][:2]
        rec = c["legs"]["bridge_raw"]["withdrawals"][0]
        other = copy.deepcopy(rec); other["data"]["transfer_tx_hash"] = "0x" + "4" * 64
        c["legs"]["bridge_raw"]["withdrawals"].append(other)
        return c
    c = group_two()
    for rec in c["legs"]["bridge_raw"]["withdrawals"]:
        rec["status"] = "PENDING"; rec["data"]["transfer_tx_hash"] = None
        # Keep unique source record IDs so normalization preserves the two records.
    c["legs"]["bridge_raw"]["withdrawals"][1]["data"]["tx_hash"] = "TX_G2"
    c["legs"]["dest_receipts"] = {}
    run("group_all_pending", c)
    c = group_two(); c["legs"]["dest_unavailable"] = "timeout"
    run("group_destination_unavailable", c)
    c = group_two()
    for rec in c["legs"]["bridge_raw"]["withdrawals"]:
        c["legs"]["dest_receipts"][rec["data"]["transfer_tx_hash"]] = {"status": "0x1", "blockNumber": "0x64", "logs": []}
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
    ev = json.loads(oc["logs"][0].split("EVENT_JSON:",1)[1]); ev["data"][0]["amount"]="not-an-integer"
    oc["logs"][0] = "EVENT_JSON:" + json.dumps(ev)
    try:
        run("malformed_source_burn_amount", c)
    except Exception as exc:
        findings["malformed_source_burn_amount"]={"exception": type(exc).__name__, "message": str(exc)}
    c = copy.deepcopy(single)
    oc = c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]
    ev = json.loads(oc["logs"][0].split("EVENT_JSON:",1)[1]); ev["data"] = "malformed-data-array"
    oc["logs"].append("EVENT_JSON:" + json.dumps(ev))
    run("malformed_additional_burn_data_array", c)
    isp = importlib.util.spec_from_file_location("v5_case_builders", pkg / "run_invariants.py")
    ib = importlib.util.module_from_spec(isp); isp.loader.exec_module(ib)
    c = ib.build_case("fastnear_missing_transaction_root", 1, 1, "full", source="fastnear")
    c["legs"]["near_raw"].pop("execution_outcome")
    run("fastnear_missing_transaction_root", c)
    c = copy.deepcopy(single)
    c["legs"]["near_raw"]["receipts_outcome"].append(None)
    try:
        run("malformed_source_outcome_entry", c)
    except Exception as exc:
        findings["malformed_source_outcome_entry"] = {"exception": type(exc).__name__, "message": str(exc)}
    expected = {
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
        "malformed_additional_burn_data_array": "INVALID_EVIDENCE",
        "fastnear_missing_transaction_root": "INCOMPLETE_EVIDENCE",
        "malformed_source_outcome_entry": "UNSUPPORTED_SOURCE",
    }
    checks["independent_regression_gate"] = {"cases": len(expected), "failures": [name for name, prefix in expected.items() if not findings[name].get("overall", "").startswith(prefix)]}
    assert not checks["independent_regression_gate"]["failures"], checks["independent_regression_gate"]
    checks["counterexamples"] = findings
    # Independently verify that the original principal parser/scope/ordering regressions
    # are present in the supplied suite outputs, not just claims in the report.
    checks["suite_scenarios"] = sorted(p.stem for p in (pkg / "fixtures").glob("*.json"))
    checks["verifier_limit"] = "Verifier consumes transfer identities in selected saved examples and synthetic cases, but is not an exhaustive independent parser/graph validator or production audit."
(HERE / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
print(json.dumps({k:v for k,v in checks.items() if k not in ("counterexamples", "suite_scenarios")}, indent=2))
for name, r in checks["counterexamples"].items():
    print(name, "=>", r.get("overall", r))
