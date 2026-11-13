#!/usr/bin/env python3
"""run_invariants.py — generated combination suite through the FULL pipeline
(parse -> completeness -> normalize -> match -> summarize) with SEMANTIC invariant
assertions over observed cardinality/state (not a copy of the summary implementation).

Matrix: group size 1/2/3; record count 0/1/equal/excess; destination
pending/unavailable/reverted/zero-matching/partial/full; shared destination tx with
distinct logs vs repeated same log; mixed recipients; reordered/repeated observations;
drpc/FastNEAR missing/empty outcomes; valid/invalid fee accounting; receipt identity
mismatch. Legitimate full observations must pass green. Unsupported combinations are
classified distinctly from correctness failures.

  python3 run_invariants.py        (no network)  exit 0 = all green
"""
import contextlib, io, json, sys, copy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import payout_probe as pp

SRC = pp.SUPPORTED["source_token"]
USDC = pp.SUPPORTED["dest_token"]
TOPIC = pp.TRANSFER_TOPIC
R1 = "0xc366efeff224ea755118b19c30202869c5a85490"
R2 = "0x1111111111111111111111111111111111111111"
OUT = Path("results/invariants")
FAILS = []

def burn_log(to, amt):
    return "EVENT_JSON:" + json.dumps({"standard": "nep141", "version": "1.0.0",
        "event": "ft_burn", "data": [{"owner_id": "intents.near", "amount": str(amt),
        "memo": f"WITHDRAW_TO:{to}"}]})

def outcome(rid, executor, logs=None, status=None, receipt_ids=None):
    return {"block_hash": "7" + "z" * 43, "id": rid, "proof": None,
            "outcome": {"executor_id": executor, "gas_burnt": 0, "logs": logs or [],
                        "metadata": None, "receipt_ids": receipt_ids or [],
                        "status": status if status is not None else {"SuccessValue": "MA=="},
                        "tokens_burnt": 0}}

def body(rid, receiver):
    return {"receipt_id": rid, "predecessor_id": "p.near", "priority": 0,
            "receiver_id": receiver,
            "receipt": {"Action": {"receiver_id": receiver, "actions": [],
                                   "gas": "0", "deposit": "0"}}}

def txo(rids):
    return {"block_hash": "7" + "y" * 43, "id": "tx", "proof": None,
            "outcome": {"executor_id": None, "gas_burnt": 0, "logs": [], "metadata": None,
                        "receipt_ids": rids, "status": {"SuccessValue": "MA=="},
                        "tokens_burnt": 0}}

def recipients_for(n, mode):
    if mode == "mixed" and n >= 2:
        return [R1 if i % 2 == 0 else R2 for i in range(n)]
    return [R1] * n

def drpc_near(n, recip_mode, status=None, extra_outcome=None):
    rcpts = recipients_for(n, recip_mode)
    logs = [burn_log(r, 10000) for r in rcpts]
    out = [outcome("r1", SRC, logs, receipt_ids=[])]
    if extra_outcome:
        out.append(extra_outcome)
    return {"status": status if status is not None else {"SuccessValue": "MA=="},
            "final_execution_status": "FINAL",
            "receipts": [body("r1", SRC)] + ([body("r2", SRC)] if extra_outcome else []),
            "receipts_outcome": out,
            "transaction_outcome": txo([o["id"] for o in out])}

def wrec(tx, transfer, amount=10000, fee=2400, status="COMPLETED", net=None):
    net = amount - fee if net is None else net
    return {"status": status, "data": {"tx_hash": tx, "transfer_tx_hash": transfer,
            "chain": "eth:8453", "decimals": 6, "amount": str(amount),
            "withdrawal_fee": str(fee), "withdraw_amount": str(net),
            "near_token_id": SRC, "defuse_asset_identifier": f"eth:8453:{USDC}",
            "created_at": "SYNTHETIC"}}

def receipt_of(transfers, block=100, status="0x1", txhash=None, token=USDC):
    logs = []
    for i, (to, amt) in enumerate(transfers):
        logs.append({"address": token, "topics": [TOPIC,
            "0x" + "0" * 24 + "2cff890f0378a11913b6129b2e97417a2c302680",
            "0x" + "0" * 24 + to[2:]], "data": "0x" + hex(amt)[2:].zfill(64),
            "logIndex": hex(i + 1), "blockNumber": hex(block)})
    r = {"status": status, "blockNumber": hex(block), "logs": logs}
    if txhash:
        r["transactionHash"] = txhash
    return r

def build_case(name, n, r_count, dest_state, recip_mode="same", fee_valid=True,
               source="drpc"):
    """Fixture-shaped case through the full pipeline."""
    rcpts = recipients_for(n, recip_mode)
    if source == "drpc":
        near = drpc_near(n, recip_mode)
    else:
        # FastNEAR-shaped: receipts entries with execution_outcome + nested Action
        logs = [burn_log(r, 10000) for r in rcpts]
        near = {"transaction": {"hash": "SYN", "receiver_id": SRC},
                "execution_outcome": {"id": "tx", "outcome": {
                    "status": {"SuccessValue": "MA=="}, "logs": [],
                    "receipt_ids": ["r1"]}},
                "receipts": [{"receipt_id": "r1", "execution_outcome": {"id": "r1",
                    "outcome": {"status": {"SuccessValue": "MA=="}, "logs": logs,
                                "receipt_ids": []}},
                    "receipt": {"Action": {"receiver_id": SRC, "actions": []}}}],
                "data_receipts": []}
    withdrawals, dest_receipts, dest_unavailable = [], {}, None
    fee = 2400 if fee_valid else 999
    for i in range(r_count):
        tx = f"TX{i}"
        transfer = None if dest_state == "pending" else f"0x{i:02x}" * 32
        status = "PENDING" if dest_state == "pending" else "COMPLETED"
        # fee_invalid must violate gross == fee + net (fee 999 with net 7600)
        net = 7600 if not fee_valid else None
        withdrawals.append(wrec(tx, transfer, status=status, fee=fee, net=net))
        if dest_state == "pending":
            continue
        recip = rcpts[i % len(rcpts)] if i < n else rcpts[-1]
        if dest_state == "unavailable":
            dest_unavailable = "timeout"
            continue
        if dest_state == "reverted":
            dest_receipts[transfer] = receipt_of([(recip, 7600)], status="0x0")
        elif dest_state == "zero_matching":
            dest_receipts[transfer] = receipt_of([])
        elif dest_state == "partial":
            # first record full, remaining zero-matching
            dest_receipts[transfer] = (receipt_of([(recip, 7600)]) if i == 0
                                       else receipt_of([]))
        else:  # full
            dest_receipts[transfer] = receipt_of([(recip, 7600)])
    legs = {"near_source": source, "near_raw": near,
            "bridge_raw": {"withdrawals": withdrawals},
            "dest_receipts": dest_receipts, "dest_tip": 1000}
    if dest_unavailable:
        legs["dest_unavailable"] = dest_unavailable
    return {"name": name, "kind": "fixture", "synthetic": True, "legs": legs}

def expected_class(n, r_count, dest_state, fee_valid=True, source="drpc",
                   override=None):
    if override:
        return override
    if not fee_valid:
        return "INVALID_EVIDENCE"
    if source in ("fastnear_missing", "fastnear_empty", "wrapper", "pending_outcome"):
        return "INCOMPLETE"
    if r_count == 0:
        return "MISMATCH"
    if dest_state == "pending":
        return "IN_PROGRESS"
    if dest_state == "unavailable":
        return "INCONCLUSIVE"
    if dest_state in ("reverted", "zero_matching"):
        return "MISMATCH"
    if dest_state == "partial":
        # partial is MISMATCH only when >=2 records can be processed for the group
        # (first full, rest zero-matching); with just one processable record the
        # covered burn behaves like the full case, surplus records become extras.
        if min(r_count, n) >= 2:
            return "MISMATCH"
    # full
    if r_count == n:
        return "ALL_ROWS_OBSERVED"
    if r_count > n:
        return "MATCH_WITH_UNMATCHED"
    return "MISMATCH"   # r < n: unrecorded burns

def transfers_in(case):
    """Distinct destination Transfer logs provided in the case's RAW receipts."""
    seen = set()
    for key, r in case["legs"].get("dest_receipts", {}).items():
        for lg in r.get("logs", []) or []:
            if lg.get("topics") and lg["topics"][0].startswith("0xddf252ad"):
                seen.add((key, lg.get("logIndex")))
    return len(seen)

def assert_invariants(report, case, name):
    errs = []
    s = report["summary"]
    results = report["results"]
    counts = s["counts"]
    groups = [x for x in results if x.get("verdict") == "GROUP_FINDING"]
    singles = [x for x in results if isinstance(x.get("row"), int)]
    burns = report["rows_found"]
    obs = (sum(g.get("observed", 0) for g in groups)
           + sum(1 for x in singles if x.get("verdict") == "OBSERVED_MATCH"))
    green = s["overall"].startswith("ALL_ROWS_OBSERVED")
    # I2 bounds / I3 no negatives
    if not (0 <= obs <= burns):
        errs.append(f"observed {obs} outside [0, burns {burns}]")
    for g in groups:
        n = g.get("rows_in_group", 0)
        for k in ("observed", "unrecorded", "records_matched", "pending", "unavailable",
                  "invalid_dest", "invalid_record", "reverted", "no_transfer"):
            v = g.get(k, 0)
            if v < 0:
                errs.append(f"negative group {k}={v}")
        if g.get("observed", 0) > n or g.get("unrecorded", 0) > n:
            errs.append("group count exceeds rows_in_group")
        if g.get("records_matched", 0) > n:
            errs.append("records_matched exceeds rows_in_group (slot cap broken)")
        if g.get("observed", 0) > g.get("records_matched", 0):
            errs.append("observed exceeds records_matched")
    # I4 one transfer cannot satisfy two burns: observed <= distinct transfers provided
    if obs > transfers_in(case):
        errs.append(f"observed {obs} > distinct destination transfers "
                    f"{transfers_in(case)} (transfer reuse?)")
    unresolved = (sum(g.get(k, 0) for g in groups for k in
                      ("pending", "unavailable", "invalid_dest", "invalid_record",
                       "reverted", "no_transfer", "unrecorded"))
                  + counts.get("PENDING", 0) + counts.get("INCONCLUSIVE", 0)
                  + counts.get("NOT_RECORDED", 0) + counts.get("UNVERIFIED_DEST", 0)
                  + counts.get("INVALID_RECORD", 0))
    # I1 green => complete, full coverage, no unresolved, no extras/foreign verdicts
    if green:
        if s.get("completeness", {}).get("complete") is not True:
            errs.append("green despite incomplete graph")
        if burns == 0 or obs != burns:
            errs.append(f"green but observed {obs} != burns {burns}")
        foreign = set(counts) - {"OBSERVED_MATCH", "GROUP_FINDING"}
        if foreign:
            errs.append(f"green with foreign verdicts {foreign}")
        if unresolved:
            errs.append(f"green with unresolved states {unresolved}")
        if any(g.get("observed", 0) != g.get("rows_in_group", 0) for g in groups):
            errs.append("green with partially observed group")
        if any(x.get("verdict") != "OBSERVED_MATCH" for x in singles):
            errs.append("green with non-observed single row")
    # I5/I7 unresolved or incomplete => never green (covered above; explicit)
    if s.get("completeness", {}).get("complete") is False and green:
        errs.append("incomplete graph but green")
    # I6 invalid fee => never green
    if any(x.get("verdict") == "INVALID_RECORD" for x in results) and green:
        errs.append("invalid record but green")
    # expected class (input-derived, independent of summary code)
    exp = case.get("_expected")
    if exp and not s["overall"].startswith(exp):
        errs.append(f"expected class {exp}, got {s['overall']!r}")
    tag = "PASS" if not errs else "FAIL"
    print(f"  [{tag}] {name}: {s['overall']}"
          + ("" if not errs else f"  << {errs}"))
    if errs:
        FAILS.append(name)

def run(name, case, exp):
    case["name"] = name
    case["_expected"] = exp
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rep = pp.run_case(case, OUT)
    assert_invariants(rep, case, name)

def main():
    print("== GENERATED MATRIX: group size x record count x destination state ==")
    for n in (1, 2, 3):
        r_counts = sorted({0, 1, n, n + 1})
        for rc in r_counts:
            for ds in ("full", "partial", "pending", "unavailable", "reverted",
                       "zero_matching"):
                c = build_case(f"m_n{n}_r{rc}_{ds}", n, rc, ds)
                run(c["name"], c, expected_class(n, rc, ds))

    print("== MIXED RECIPIENTS (full destination only) ==")
    for n, rc in ((2, 2), (3, 3), (2, 1), (2, 3)):
        c = build_case(f"mix_n{n}_r{rc}", n, rc, "full", recip_mode="mixed")
        run(c["name"], c, expected_class(n, rc, "full"))

    print("== FEE ACCOUNTING ==")
    c = build_case("fee_valid", 1, 1, "full"); run(c["name"], c, "ALL_ROWS_OBSERVED")
    c = build_case("fee_invalid", 1, 1, "full", fee_valid=False)
    run(c["name"], c, "INVALID_EVIDENCE")

    print("== RECEIPT IDENTITY / DEST STATES ==")
    c = build_case("hash_mismatch", 1, 1, "full")
    tx = next(iter(c["legs"]["dest_receipts"]))
    c["legs"]["dest_receipts"][tx]["transactionHash"] = "0x" + "f" * 64
    run("hash_mismatch", c, "INCONCLUSIVE")

    print("== EXECUTION-EVIDENCE (drpc + FastNEAR) ==")
    c = build_case("wrapper_no_status", 1, 1, "full")
    c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]["receipt_ids"] = ["w1"]
    c["legs"]["near_raw"]["receipts_outcome"].append({"id": "w1"})
    c["legs"]["near_raw"]["receipts"].append(body("w1", SRC))
    run("wrapper_no_status", c, "INCOMPLETE")

    c = build_case("pending_outcome", 1, 1, "full")
    c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]["status"] = {"Pending": None}
    run("pending_outcome", c, "INCOMPLETE")

    # [v4] absent vs EMPTY child-edge arrays: absent receipt_ids on an executed
    # reachable outcome is missing graph structure -> INCOMPLETE; an explicit empty
    # list is a positively-evidenced leaf -> green stays possible.
    c = build_case("child_edges_absent", 1, 1, "full")
    del c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]["receipt_ids"]
    run("child_edges_absent", c, "INCOMPLETE")

    c = build_case("child_edges_empty", 1, 1, "full")
    c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]["receipt_ids"] = []
    run("child_edges_empty", c, "ALL_ROWS_OBSERVED")

    c = build_case("child_edges_not_list", 1, 1, "full")
    c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]["receipt_ids"] = "not-a-list"
    run("child_edges_not_list", c, "INCOMPLETE")

    c = build_case("outcome_missing_id", 1, 1, "full")
    del c["legs"]["near_raw"]["receipts_outcome"][0]["id"]
    run("outcome_missing_id", c, "INCOMPLETE")

    c = build_case("outcome_unknown_status", 1, 1, "full")
    c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]["status"] = {"Weird": 1}
    run("outcome_unknown_status", c, "INCOMPLETE")

    c = build_case("fastnear_child_edges_absent", 1, 1, "full", source="fastnear")
    del c["legs"]["near_raw"]["receipts"][0]["execution_outcome"]["outcome"]["receipt_ids"]
    run("fastnear_child_edges_absent", c, "INCOMPLETE")

    c = build_case("fastnear_full", 1, 1, "full", source="fastnear")
    run("fastnear_full", c, "ALL_ROWS_OBSERVED")

    c = build_case("fastnear_missing_outcome", 1, 1, "full", source="fastnear")
    c["legs"]["near_raw"]["receipts"][0]["execution_outcome"] = {}
    run("fastnear_missing_outcome", c, "INCOMPLETE")

    c = build_case("fastnear_empty_receipts", 1, 1, "full", source="fastnear")
    c["legs"]["near_raw"]["receipts"] = []
    run("fastnear_empty_receipts", c, "INCOMPLETE")

    print("== SHARED DESTINATION TX / REPEATED OBSERVATIONS / ORDER ==")
    # one record, destination tx carrying TWO distinct logs (duplicate delivery)
    c = build_case("shared_dest_two_logs", 1, 1, "full")
    tx = next(iter(c["legs"]["dest_receipts"]))
    rcp = c["legs"]["dest_receipts"][tx]
    second = dict(rcp["logs"][0])
    second["logIndex"] = "0x2"
    rcp["logs"].append(second)   # same destination tx, second distinct log
    run("shared_dest_two_logs", c, "MATCH_WITH_UNMATCHED")

    # [v4] TWO burns, TWO records, ONE destination tx, TWO DISTINCT logs:
    # identity consumption must satisfy both burns (each log consumed once).
    c = build_case("shared_dest_two_burns_two_logs", 2, 2, "full")
    w = c["legs"]["bridge_raw"]["withdrawals"]
    w[1]["data"]["transfer_tx_hash"] = w[0]["data"]["transfer_tx_hash"]
    txk = next(iter(c["legs"]["dest_receipts"]))
    rcp = c["legs"]["dest_receipts"][txk]
    second = dict(rcp["logs"][0])
    second["logIndex"] = "0x2"
    rcp["logs"].append(second)
    run("shared_dest_two_burns_two_logs", c, "ALL_ROWS_OBSERVED")

    # [v4] TWO burns, TWO records, ONE destination tx, ONE log REPEATED (exact
    # copy): recipient+amount set-membership would match twice, but there is only
    # one real transfer identity -> ONE observation, one deficit, never green.
    c = build_case("shared_dest_two_burns_one_log_copied", 2, 2, "full")
    w = c["legs"]["bridge_raw"]["withdrawals"]
    w[1]["data"]["transfer_tx_hash"] = w[0]["data"]["transfer_tx_hash"]
    txk = next(iter(c["legs"]["dest_receipts"]))
    rcp = c["legs"]["dest_receipts"][txk]
    rcp["logs"].append(dict(rcp["logs"][0]))   # identical copy, same logIndex
    run("shared_dest_two_burns_one_log_copied", c, "MISMATCH")

    # same destination receipt observed twice (repeated observation -> idempotent)
    c = build_case("repeated_dest_obs", 1, 1, "full")
    tx = next(iter(c["legs"]["dest_receipts"]))
    c["legs"]["dest_receipts"][tx] = dict(c["legs"]["dest_receipts"][tx])
    run("repeated_dest_obs", c, "ALL_ROWS_OBSERVED")

    # exact duplicate bridge record (repeated observation -> idempotent)
    c = build_case("duplicate_record_obs", 1, 1, "full")
    c["legs"]["bridge_raw"]["withdrawals"].append(
        copy.deepcopy(c["legs"]["bridge_raw"]["withdrawals"][0]))
    run("duplicate_record_obs", c, "ALL_ROWS_OBSERVED")

    # reordered records -> same class as base
    c = build_case("reordered_records", 2, 2, "full")
    c["legs"]["bridge_raw"]["withdrawals"].reverse()
    run("reordered_records", c, "ALL_ROWS_OBSERVED")

    # reversed + duplicated destination observations together
    c = build_case("reordered_dup_observations", 2, 2, "full")
    w = c["legs"]["bridge_raw"]["withdrawals"]
    c["legs"]["bridge_raw"]["withdrawals"] = [w[1], w[0], copy.deepcopy(w[0])]
    run("reordered_dup_observations", c, "ALL_ROWS_OBSERVED")

    print("== BOUNDARY VALIDATION: monetary types / malformed records & events [v4] ==")
    # fractional monetary fields: floats must be rejected, not int()-truncated
    for label, amt, fee, net in (
            ("float_fractional", 10000.75, 2400.5, 7600.25),
            ("float_int_valued", 10000.0, 2400.0, 7600.0),
            ("bool_values", True, False, True),
            ("negative_ints", -10000, -2400, -7600),
            ("garbage_strings", "not-an-integer", "x", "y"),
            ("null_values", None, None, None)):
        c = build_case(f"money_{label}", 1, 1, "full")
        d = c["legs"]["bridge_raw"]["withdrawals"][0]["data"]
        d["amount"], d["withdrawal_fee"], d["withdraw_amount"] = amt, fee, net
        run(f"money_{label}", c, "INVALID_EVIDENCE")

    # string and int monetary forms that real saved responses use stay green
    c = build_case("money_str_forms", 1, 1, "full")
    d = c["legs"]["bridge_raw"]["withdrawals"][0]["data"]
    d["amount"], d["withdrawal_fee"], d["withdraw_amount"] = "10000", "2400", "7600"
    run("money_str_forms", c, "ALL_ROWS_OBSERVED")
    c = build_case("money_int_forms", 1, 1, "full")
    d = c["legs"]["bridge_raw"]["withdrawals"][0]["data"]
    d["amount"], d["withdrawal_fee"], d["withdraw_amount"] = 10000, 2400, 7600
    run("money_int_forms", c, "ALL_ROWS_OBSERVED")

    # malformed burn amount in the source log: structured INVALID_EVIDENCE, no crash
    for label, bad in (("garbage", "not-an-integer"), ("float", 10000.75),
                       ("bool", True), ("negative", -5), ("null", None)):
        c = build_case(f"burn_amount_{label}", 1, 1, "full")
        oc = c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]
        ev = json.loads(oc["logs"][0].split("EVENT_JSON:", 1)[1])
        ev["data"][0]["amount"] = bad
        oc["logs"][0] = "EVENT_JSON:" + json.dumps(ev)
        run(f"burn_amount_{label}", c, "INVALID_EVIDENCE")

    # non-object event data entry -> structured INVALID_EVIDENCE
    c = build_case("burn_event_data_entry_not_object", 1, 1, "full")
    oc = c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]
    ev = json.loads(oc["logs"][0].split("EVENT_JSON:", 1)[1])
    ev["data"] = ["not-an-object"]
    oc["logs"][0] = "EVENT_JSON:" + json.dumps(ev)
    run("burn_event_data_entry_not_object", c, "INVALID_EVIDENCE")

    # malformed entries beside a valid bridge record (null / string / list)
    for label, extra in (("null", None), ("string", "junk"), ("list", [1])):
        c = build_case(f"bridge_extra_{label}", 1, 1, "full")
        c["legs"]["bridge_raw"]["withdrawals"].append(extra)
        run(f"bridge_extra_{label}", c, "INVALID_EVIDENCE")

    # withdrawal whose data is not an object
    c = build_case("bridge_data_not_object", 1, 1, "full")
    c["legs"]["bridge_raw"]["withdrawals"][0]["data"] = "not-an-object"
    run("bridge_data_not_object", c, "INVALID_EVIDENCE")

    # missing status on the bridge record -> PENDING (not silently COMPLETED)
    c = build_case("bridge_status_missing", 1, 1, "full")
    del c["legs"]["bridge_raw"]["withdrawals"][0]["status"]
    run("bridge_status_missing", c, "IN_PROGRESS")

    # missing destination tx identity -> PENDING (no tx to observe)
    c = build_case("bridge_missing_transfer_tx", 1, 1, "full")
    c["legs"]["bridge_raw"]["withdrawals"][0]["data"]["transfer_tx_hash"] = None
    run("bridge_missing_transfer_tx", c, "IN_PROGRESS")

    print("== [v5] SOURCE-BOUNDARY: transaction root / outcome entries / burn data ==")
    # FastNEAR without the top-level execution_outcome root: roots are never
    # guessed from receipt ordering -> INCOMPLETE_EVIDENCE, never green.
    c = build_case("fastnear_root_absent", 1, 1, "full", source="fastnear")
    c["legs"]["near_raw"].pop("execution_outcome")
    run("fastnear_root_absent", c, "INCOMPLETE")

    for label, root in (
            ("fastnear_root_non_object", "junk"),
            ("fastnear_root_outcome_non_object", {"id": "tx", "outcome": "nope"}),
            ("fastnear_root_receipt_ids_missing",
             {"id": "tx", "outcome": {"status": {"SuccessValue": ""}}}),
            ("fastnear_root_receipt_ids_not_list", {"id": "tx", "outcome": {
                "status": {"SuccessValue": ""}, "receipt_ids": "r1"}})):
        c = build_case(label, 1, 1, "full", source="fastnear")
        c["legs"]["near_raw"]["execution_outcome"] = root
        run(label, c, "INCOMPLETE")

    # FastNEAR valid root control (real saved shape) stays green
    c = build_case("fastnear_root_valid_control", 1, 1, "full", source="fastnear")
    run("fastnear_root_valid_control", c, "ALL_ROWS_OBSERVED")

    # drpc transaction-root variants
    for label, mutate in (
            ("drpc_root_absent", lambda raw: raw.pop("transaction_outcome")),
            ("drpc_root_null", lambda raw: raw.__setitem__("transaction_outcome", None)),
            ("drpc_root_non_object", lambda raw: raw.__setitem__(
                "transaction_outcome", "junk")),
            ("drpc_root_outcome_missing", lambda raw: raw.__setitem__(
                "transaction_outcome", {"id": "tx"})),
            ("drpc_root_receipt_ids_missing", lambda raw: raw.__setitem__(
                "transaction_outcome", {"id": "tx", "outcome": {
                    "status": {"SuccessValue": ""}}})),
            ("drpc_root_receipt_ids_not_list", lambda raw: raw.__setitem__(
                "transaction_outcome", {"id": "tx", "outcome": {
                    "status": {"SuccessValue": ""}, "receipt_ids": "r1"}}))):
        c = build_case(label, 1, 1, "full")
        mutate(c["legs"]["near_raw"])
        run(label, c, "INCOMPLETE")

    # null / non-object entries inside the source outcome collections
    for label, extra in (("null", None), ("string", "junk"), ("number", 7)):
        c = build_case(f"outcome_extra_{label}", 1, 1, "full")
        c["legs"]["near_raw"]["receipts_outcome"].append(extra)
        run(f"outcome_extra_{label}", c, "UNSUPPORTED_SOURCE")

    for label, extra in (("null", None), ("string", "junk")):
        c = build_case(f"fn_receipt_extra_{label}", 1, 1, "full", source="fastnear")
        c["legs"]["near_raw"]["receipts"].append(extra)
        run(f"fn_receipt_extra_{label}", c, "UNSUPPORTED_SOURCE")

    # nested non-object outcome / execution_outcome on an otherwise-valid response
    c = build_case("drpc_nested_outcome_not_object", 1, 1, "full")
    raw = c["legs"]["near_raw"]
    raw["receipts_outcome"][0]["outcome"]["receipt_ids"] = ["r2"]
    raw["receipts_outcome"].append({"id": "r2", "outcome": "not-an-object"})
    raw["transaction_outcome"]["outcome"]["receipt_ids"] = ["r1", "r2"]
    run("drpc_nested_outcome_not_object", c, "INCOMPLETE")

    c = build_case("fn_nested_outcome_not_object", 1, 1, "full", source="fastnear")
    c["legs"]["near_raw"]["receipts"][0]["execution_outcome"] = "not-an-object"
    run("fn_nested_outcome_not_object", c, "INCOMPLETE")

    # burn-event data shape: absent/null/string/object on a SUPPORTED executor
    # beside a VALID withdrawal burn -> INVALID_EVIDENCE (never silent skip)
    for label, data in (("absent", "ABSENT"), ("null", None),
                        ("string", "malformed-data-array"),
                        ("object", {"memo": "WITHDRAW_TO:0x" + "c" * 40})):
        c = build_case(f"burn_data_{label}", 1, 1, "full")
        oc = c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]
        ev = json.loads(oc["logs"][0].split("EVENT_JSON:", 1)[1])
        extra = json.loads(json.dumps(ev))
        if data == "ABSENT":
            extra.pop("data")
        else:
            extra["data"] = data
        oc["logs"].append("EVENT_JSON:" + json.dumps(extra))
        run(f"burn_data_{label}", c, "INVALID_EVIDENCE")

    # the primary burn itself carrying non-list data (no valid burn beside it)
    for label, data in (("primary_string", "malformed-data-array"),
                        ("primary_object", {"memo": "WITHDRAW_TO:0x" + "c" * 40})):
        c = build_case(f"burn_primary_data_{label}", 1, 1, "full")
        oc = c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]
        ev = json.loads(oc["logs"][0].split("EVENT_JSON:", 1)[1])
        ev["data"] = data
        oc["logs"][0] = "EVENT_JSON:" + json.dumps(ev)
        run(f"burn_primary_data_{label}", c, "INVALID_EVIDENCE")

    # unrelated event types beside a valid burn: NOT failures, report stays green
    for label, standard, event in (
            ("ft_transfer", "nep141", "ft_transfer"),
            ("other_standard", "nep245", "ft_burn"),
            ("other_event", "nep141", "ft_metadata")):
        c = build_case(f"unrelated_{label}", 1, 1, "full")
        oc = c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]
        oc["logs"].append("EVENT_JSON:" + json.dumps(
            {"standard": standard, "version": "1.0.0", "event": event,
             "data": [{"owner_id": "o", "amount": "1"}]}))
        run(f"unrelated_{label}", c, "ALL_ROWS_OBSERVED")

    # valid non-withdrawal burns (no WITHDRAW_TO memo) beside a valid withdrawal:
    # ignored, never withdrawal failures
    for label, entry in (("plain_burn", {"owner_id": "o", "amount": "1"}),
                         ("other_memo", {"owner_id": "o", "amount": "1",
                                         "memo": "note"})):
        c = build_case(f"non_withdrawal_{label}", 1, 1, "full")
        oc = c["legs"]["near_raw"]["receipts_outcome"][0]["outcome"]
        ev = json.loads(oc["logs"][0].split("EVENT_JSON:", 1)[1])
        ev["data"].append(entry)
        oc["logs"][0] = "EVENT_JSON:" + json.dumps(ev)
        run(f"non_withdrawal_{label}", c, "ALL_ROWS_OBSERVED")

    # malformed burn emitted by an OUT-OF-SCOPE executor: unsupported scope, not a
    # withdrawal failure of the supported task
    c = build_case("out_of_scope_malformed_burn", 1, 1, "full")
    raw = c["legs"]["near_raw"]
    raw["receipts_outcome"].append({
        "id": "x1", "outcome": {"status": {"SuccessValue": ""}, "receipt_ids": [],
                                 "executor_id": "other.omft.near",
                                 "logs": ["EVENT_JSON:" + json.dumps(
                                     {"standard": "nep141", "version": "1.0.0",
                                      "event": "ft_burn", "data": "junk"})]}})
    raw["transaction_outcome"]["outcome"]["receipt_ids"].append("x1")
    run("out_of_scope_malformed_burn", c, "UNSUPPORTED_SCOPE")

    print(f"\n{'ALL INVARIANTS PASSED' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0

if __name__ == "__main__":
    sys.exit(main())
