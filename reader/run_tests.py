#!/usr/bin/env python3
"""run_tests.py v3 — exercises parsers, normalizers, traversal and matcher directly,
plus fixture expectations and OFFLINE end-to-end runs on saved raw evidence.

  python3 run_tests.py            # synthetic fixtures + units + offline raw e2e (no network)
  python3 run_tests.py --live     # + live-case assertions (network, labeled)
Exit 0 = all passed.
"""
import json, sys
from pathlib import Path
import payout_probe as pp

FAILURES = []

def check(name, cond, detail):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}: {detail}")
    if not cond:
        FAILURES.append(name)

VOCAB = {"OBSERVED_MATCH", "PENDING", "NOT_RECORDED", "INCONCLUSIVE", "GROUP_FINDING",
         "UNSUPPORTED_SCOPE", "UNSUPPORTED_BRIDGE", "UNMATCHED_BRIDGE_RECORD",
         "UNMATCHED_DEST_TRANSFER", "UNVERIFIED_DEST", "INVALID_RECORD",
         "INVALID_EVENT_ROW"}

def run_case_assert(path: Path):
    case = json.loads(path.read_text())
    expect = case.get("expect")
    if not expect:
        check(f"{path.name}.expect", False, "missing expect block")
        return
    report = pp.run_case(case, Path("results/suite"))
    s = report["summary"]
    if "overall_prefix" in expect:
        check(f"{case['name']}.overall", s["overall"].startswith(expect["overall_prefix"]),
              f"got {s['overall']!r} want prefix {expect['overall_prefix']!r}")
    if "forbidden_overall" in expect:
        bad = [o for o in expect["forbidden_overall"] if s["overall"].startswith(o)]
        check(f"{case['name']}.forbidden_overall", not bad,
              f"overall {s['overall']!r} must not start with {bad}")
    if "counts" in expect:
        got, want = s["counts"], expect["counts"]
        keys = set(got) | set(want)
        diff = {k: (got.get(k, 0), want.get(k, 0)) for k in keys
                if got.get(k, 0) != want.get(k, 0)}
        check(f"{case['name']}.counts", not diff, f"got {got} want {want} diff {diff or '{}'}")
    if "note_contains" in expect:
        blob = json.dumps(report.get("results", [])) + json.dumps(report.get("list_advisory", []))
        check(f"{case['name']}.note_contains", expect["note_contains"] in blob,
              f"expected {expect['note_contains']!r} in results")
    if "forbidden_row_verdicts" in expect:
        bad = [r.get("verdict") for r in report.get("results", [])
               if r.get("verdict") in expect["forbidden_row_verdicts"]]
        check(f"{case['name']}.forbidden_row_verdicts", not bad,
              f"row-level verdicts {bad} must not appear (grouping required)")
    if "advisory_contains" in expect:
        adv = " ".join(report.get("list_advisory", []))
        check(f"{case['name']}.advisory", expect["advisory_contains"] in adv,
              f"advisory {adv!r} must contain {expect['advisory_contains']!r}")
    if "list_state_contains" in expect:
        st = s.get("list_check", "")
        check(f"{case['name']}.list_state", expect["list_state_contains"] in st,
              f"list_check {st!r} must contain {expect['list_state_contains']!r}")
    bad_v = [r.get("verdict") for r in report.get("results", [])
             if r.get("verdict") not in VOCAB]
    check(f"{case['name']}.vocab", not bad_v, f"unknown verdicts {bad_v or 'none'}")

def units():
    print("== UNIT: normalize_status (native shapes) ==")
    check("status.failure", pp.normalize_status({"Failure": {"x": 1}}) == "Failure", "dict Failure")
    check("status.success", pp.normalize_status({"SuccessValue": "MA=="}) == "SuccessValue", "dict SuccessValue")
    check("status.pending", pp.normalize_status({"Pending": None}) == "Pending", "dict Pending")
    check("status.str", pp.normalize_status("SuccessReceiptId") == "SuccessReceiptId", "bare str")
    check("status.none", pp.normalize_status(None) == "Unknown", "None -> Unknown")

    print("== UNIT: normalize_bridge (scope validation + idempotency) ==")
    usdc = pp.SUPPORTED["dest_token"]
    good = {"withdrawals": [{"status": "COMPLETED", "data": {
        "tx_hash": "T1", "transfer_tx_hash": "0x" + "1"*64, "chain": "eth:8453",
        "decimals": 6, "amount": "10000", "withdrawal_fee": "2400",
        "withdraw_amount": "7600", "near_token_id": pp.SUPPORTED["source_token"],
        "defuse_asset_identifier": f"eth:8453:{usdc}"}}]}
    r1, mf1 = pp.normalize_bridge(good)
    r2, mf2 = pp.normalize_bridge({"withdrawals": good["withdrawals"] * 2})
    check("bridge.single", len(r1) == 1 and not r1[0]["scope_problems"] and not mf1,
          "valid record accepted, no malformed flag")
    check("bridge.idempotent", len(r2) == 1 and not mf2,
          "identical repeated record deduped once")
    bad_chain = json.loads(json.dumps(good)); bad_chain["withdrawals"][0]["data"]["chain"] = "solana:101"
    rb, _ = pp.normalize_bridge(bad_chain)
    check("bridge.wrong_chain", bool(rb[0]["scope_problems"]), "wrong chain flagged")
    bad_tok = json.loads(json.dumps(good)); bad_tok["withdrawals"][0]["data"]["near_token_id"] = "evil.omft.near"
    rt, _ = pp.normalize_bridge(bad_tok)
    check("bridge.wrong_token", bool(rt[0]["scope_problems"]), "wrong source token flagged")

    print("== UNIT: boundary validation — monetary JSON types (no int() truncation) ==")
    def money_case(label, amount, fee, net, want_problem=True):
        payload = json.loads(json.dumps(good))
        d = payload["withdrawals"][0]["data"]
        d["amount"], d["withdrawal_fee"], d["withdraw_amount"] = amount, fee, net
        recs, mflag = pp.normalize_bridge(payload)
        r = recs[0]
        has_problem = bool(r.get("invalid_accounting"))
        check(f"money.{label}", has_problem == want_problem and mflag == want_problem,
              f"amount={amount!r} fee={fee!r} net={net!r} -> "
              f"invalid_accounting={r.get('invalid_accounting')!r} malformed={mflag}")
    money_case("float", 10000.75, 2400.5, 7600.25)
    money_case("float_int_valued", 10000.0, 2400.0, 7600.0)
    money_case("bool", True, False, True)
    money_case("negative", -10000, -2400, -7600)
    money_case("string_garbage", "not-an-integer", "2400", "7600")
    money_case("null", None, None, None)
    money_case("list_type", [10000], 2400, 7600)
    money_case("hex_string", "0x2710", "0x960", "0x1db0")
    money_case("mixed_valid_int_str", 10000, "2400", "7600", want_problem=False)
    money_case("all_str", "10000", "2400", "7600", want_problem=False)
    money_case("valid_ints", 10000, 2400, 7600, want_problem=False)
    money_case("neg_string", "10000", "-2400", "7600")

    print("== UNIT: boundary validation — malformed entries surfaced, not skipped ==")
    for label, extra in (("null", None), ("string", "junk"), ("number", 5),
                         ("list", [1, 2]), ("bool", True)):
        payload = json.loads(json.dumps(good))
        payload["withdrawals"].append(extra)
        recs, mflag = pp.normalize_bridge(payload)
        check(f"entry.{label}", len(recs) == 2 and mflag
              and recs[1].get("malformed_entry") is True
              and bool(recs[1].get("invalid_accounting")),
              f"extra {type(extra).__name__} entry preserved as INVALID_RECORD, "
              f"records={len(recs)} malformed={mflag}")
    payload = json.loads(json.dumps(good))
    payload["withdrawals"][0]["data"] = "not-an-object"
    recs, mflag = pp.normalize_bridge(payload)
    check("entry.data_not_object", len(recs) == 1 and mflag
          and recs[0].get("malformed_entry") is True,
          "withdrawal with non-object data preserved as invalid record")
    payload = {"withdrawals": "not-a-list"}
    check("entry.withdrawals_not_list", pp.normalize_bridge(payload) is None,
          "withdrawals not a list -> whole response malformed (None)")

    print("== UNIT: boundary validation — burn event amounts (no crash) ==")
    def burn_case(label, amount, want_malformed=True):
        log = "EVENT_JSON:" + json.dumps({
            "standard": "nep141", "version": "1.0.0", "event": "ft_burn",
            "data": [{"owner_id": "intents.near", "amount": amount,
                      "memo": "WITHDRAW_TO:0x" + "c" * 40}]})
        got = pp._burn_from_log(log, pp.SUPPORTED["source_token"], "r1", 0,
                                "SuccessValue")
        if want_malformed:
            check(f"burn.{label}", bool(got) and got[0].get("malformed_event"),
                  f"amount={amount!r} -> malformed_event "
                  f"{got[0].get('malformed_event') if got else None!r}")
        else:
            want_value = int(amount) if isinstance(amount, str) else amount
            check(f"burn.{label}", bool(got) and got[0]["amount"] == want_value
                  and not got[0].get("malformed_event"),
                  f"amount={amount!r} parsed to {got[0]['amount'] if got else None!r}")
    burn_case("string_garbage", "not-an-integer")
    burn_case("float", 10000.75)
    burn_case("bool", True)
    burn_case("negative", -1)
    burn_case("null", None)
    burn_case("missing", None, want_malformed=True)
    burn_case("valid_int", 10000, want_malformed=False)
    burn_case("valid_str", "10000", want_malformed=False)
    burn_case("zero", 0, want_malformed=False)
    # non-object data entries and non-list data
    log = "EVENT_JSON:" + json.dumps({
        "standard": "nep141", "version": "1.0.0", "event": "ft_burn",
        "data": ["not-an-object"]})
    got = pp._burn_from_log(log, pp.SUPPORTED["source_token"], "r1", 0, "SuccessValue")
    check("burn.data_entry_not_object", bool(got) and got[0].get("malformed_event"),
          "non-object event data entry -> malformed_event row")
    # [v5] recognized supported-scope ft_burn with non-list data is INVALID evidence,
    # not an empty event (silent skip would enshrine the C2 bug the reviewer found)
    log = "EVENT_JSON:" + json.dumps({
        "standard": "nep141", "version": "1.0.0", "event": "ft_burn", "data": "nope"})
    got = pp._burn_from_log(log, pp.SUPPORTED["source_token"], "r1", 0, "SuccessValue")
    check("burn.data_not_list", bool(got) and got[0].get("malformed_event"),
          f"non-list event data -> malformed_event row "
          f"({got[0].get('malformed_event') if got else None!r}), never silent skip")
    # non-string memo is not a withdrawal row
    log = "EVENT_JSON:" + json.dumps({
        "standard": "nep141", "version": "1.0.0", "event": "ft_burn",
        "data": [{"owner_id": "o", "amount": "1", "memo": 123}]})
    got = pp._burn_from_log(log, pp.SUPPORTED["source_token"], "r1", 0, "SuccessValue")
    check("burn.memo_not_string", got == [], "non-string memo ignored, no crash")

    print("== UNIT: [v5] burn-event data shape policy (exact) ==")
    SRC = pp.SUPPORTED["source_token"]

    def burn_log(data, standard="nep141", event="ft_burn"):
        return "EVENT_JSON:" + json.dumps(
            {"standard": standard, "version": "1.0.0", "event": event, "data": data})

    # supported executor: absent/null/string/object data -> INVALID_EVENT evidence
    for label, data in (("data_absent", "ABSENT"), ("data_null", None),
                        ("data_string", "malformed-data-array"),
                        ("data_object", {"memo": "WITHDRAW_TO:0x" + "c" * 40})):
        payload = None if data == "ABSENT" else data
        got = pp._burn_from_log(burn_log(payload), SRC, "r1", 0, "SuccessValue")
        check(f"policy.{label}", bool(got) and got[0].get("malformed_event"),
              f"supported burn {label} -> malformed_event "
              f"{got[0].get('malformed_event') if got else None!r}")
    # valid array data -> normal row
    got = pp._burn_from_log(burn_log([{"owner_id": "o", "amount": "1",
                                       "memo": "WITHDRAW_TO:0x" + "c" * 40}]),
                            SRC, "r1", 0, "SuccessValue")
    check("policy.data_valid_array", bool(got) and got[0]["amount"] == 1
          and not got[0].get("malformed_event"),
          f"valid data array -> row amount={got[0]['amount'] if got else None!r}")
    # unrelated event types: ignored, never failures, never rows
    for label, standard, event in (("ft_transfer", "nep141", "ft_transfer"),
                                   ("other_standard", "nep245", "ft_burn"),
                                   ("other_event", "nep141", "ft_metadata")):
        got = pp._burn_from_log(burn_log([], standard=standard, event=event),
                                SRC, "r1", 0, "SuccessValue")
        check(f"policy.{label}_ignored", got is None,
              f"{standard}/{event} is not a withdrawal burn -> ignored (no row)")
    # valid non-withdrawal burns (list data, no WITHDRAW_TO memo): ignored, not failures
    for label, data in (
            ("plain_burn", [{"owner_id": "o", "amount": "1"}]),
            ("other_memo", [{"owner_id": "o", "amount": "1", "memo": "note"}]),
            ("memo_null", [{"owner_id": "o", "amount": "1", "memo": None}]),
            ("memo_number", [{"owner_id": "o", "amount": "1", "memo": 9}])):
        got = pp._burn_from_log(burn_log(data), SRC, "r1", 0, "SuccessValue")
        check(f"policy.{label}_not_failure", got == [],
              f"data={label} without string WITHDRAW_TO memo -> no rows, not a failure")
    # malformed data emitted by an OUT-OF-SCOPE executor -> unsupported, not a
    # withdrawal failure of the supported task
    rows, diag = pp.extract_burns(
        {"receipts_outcome": [
            {"id": "x1", "outcome": {"status": {"SuccessValue": ""},
                                     "receipt_ids": [], "executor_id": "other.omft.near",
                                     "logs": [burn_log("junk")]}}],
         "transaction_outcome": {"id": "tx", "outcome": {
             "status": {"SuccessValue": ""}, "receipt_ids": ["x1"]}}},
        "drpc")
    check("policy.out_of_scope_malformed_burn",
          diag["unsupported_executor"] == 1 and not diag["malformed_events"]
          and rows and rows[0].get("unsupported"),
          "malformed burn from unsupported executor -> UNSUPPORTED_SCOPE, not INVALID")

    print("== UNIT: [v5] source outcome collections (null/non-object entries) ==")
    # null / string / number entries beside a valid drpc outcome -> structured, no crash
    for label, extra in (("null", None), ("string", "junk"), ("number", 7)):
        near = {"receipts_outcome": [
                    {"id": "r1", "outcome": {"status": {"SuccessValue": ""},
                                             "receipt_ids": [], "executor_id": SRC,
                                             "logs": [burn_log(
                                                 [{"owner_id": "o", "amount": "1",
                                                   "memo": "WITHDRAW_TO:0x" + "c" * 40}])]}}],
                "transaction_outcome": {"id": "tx", "outcome": {
                    "status": {"SuccessValue": ""}, "receipt_ids": ["r1"]}}}
        near["receipts_outcome"].append(extra)
        try:
            rows, diag = pp.extract_burns(near, "drpc")
            check(f"outcome.{label}_entry_no_crash", True,
                  f"null/str entry tolerated by extract_burns "
                  f"(rows={len(rows)}, malformed_entries={diag['malformed_entries']})")
        except Exception as exc:
            check(f"outcome.{label}_entry_no_crash", False,
                  f"crashed: {type(exc).__name__}: {exc}")
        check(f"outcome.{label}_entry_counted", diag["malformed_entries"] == 1,
              f"malformed_entries={diag['malformed_entries']} (expect 1)")
    # outcome entry whose nested outcome is a non-object
    near = {"receipts": [{"receipt_id": "r1", "receiver_id": SRC}],
            "receipts_outcome": [
                {"id": "r1", "outcome": {"status": {"SuccessValue": ""},
                                         "receipt_ids": [], "executor_id": SRC,
                                         "logs": [burn_log(
                                             [{"owner_id": "o", "amount": "1",
                                               "memo": "WITHDRAW_TO:0x" + "c" * 40}])]}},
                {"id": "r2", "outcome": "not-an-object"}],
            "transaction_outcome": {"id": "tx", "outcome": {
                "status": {"SuccessValue": ""}, "receipt_ids": ["r1", "r2"]}}}
    rows, diag = pp.extract_burns(near, "drpc")
    check("outcome.nested_non_object_no_crash", len(rows) == 1
          and diag["outcomes_seen"] == 3,
          "nested non-object outcome tolerated; valid row survives")
    comp = pp.analyze_completeness(near, "drpc")
    check("outcome.nested_non_object_incomplete", comp["complete"] is False
          and comp.get("missing") == 1,
          f"reachable wrapper without execution evidence unresolved: {comp['reason']}")
    # FastNEAR null/non-object receipt entries
    for label, extra in (("null", None), ("string", "junk")):
        near = {"receipts": [
                    {"receipt_id": "r1", "receiver_id": SRC,
                     "execution_outcome": {"id": "r1", "outcome": {
                         "status": {"SuccessValue": ""}, "receipt_ids": [],
                         "logs": [burn_log(
                             [{"owner_id": "o", "amount": "1",
                               "memo": "WITHDRAW_TO:0x" + "c" * 40}])]}},
                     "receipt": {"Action": {}}},
                    extra],
                "execution_outcome": {"id": "tx", "outcome": {
                    "status": {"SuccessValue": ""}, "receipt_ids": ["r1"]}}}
        try:
            rows, diag = pp.extract_burns(near, "fastnear")
            check(f"fn_receipt.{label}_entry_no_crash", diag["malformed_entries"] == 1,
                  f"FastNEAR null/str entry counted: rows={len(rows)} "
                  f"malformed_entries={diag['malformed_entries']}")
        except Exception as exc:
            check(f"fn_receipt.{label}_entry_no_crash", False,
                  f"crashed: {type(exc).__name__}: {exc}")
    # FastNEAR receipt entry with non-object nested execution_outcome
    near = {"receipts": [
                {"receipt_id": "r1", "receiver_id": SRC,
                 "execution_outcome": "not-an-object",
                 "receipt": {"Action": {}}}],
            "execution_outcome": {"id": "tx", "outcome": {
                "status": {"SuccessValue": ""}, "receipt_ids": ["r1"]}}}
    rows, diag = pp.extract_burns(near, "fastnear")
    comp = pp.analyze_completeness(near, "fastnear")
    check("fn_receipt.nested_non_object",
          diag["outcomes_seen"] == 2 and comp["complete"] is False
          and comp.get("missing") == 1,
          f"non-object execution_outcome -> incomplete: {comp['reason']} "
          f"(receipt + root outcomes seen, receipt unresolved)")

    print("== UNIT: [v5] transaction-root requirement (drpc + FastNEAR) ==")
    # drpc: root absent / null / non-object / receipt_ids missing / not-a-list
    # (receipts list included so the earlier collection check passes and the
    # ROOT rule is what fails)
    good_ro = {"receipts": [],
               "receipts_outcome": [
                   {"id": "r1", "outcome": {"status": {"SuccessValue": ""},
                                            "receipt_ids": [], "executor_id": SRC,
                                            "logs": []}}]}

    def with_root(root):
        d = json.loads(json.dumps(good_ro))
        if root is not None:
            d["transaction_outcome"] = root
        return d

    for label, root in (
            ("root_absent", None),
            ("root_null", None),
            ("root_non_object", "junk"),
            ("root_outcome_missing", {"id": "tx"}),
            ("root_receipt_ids_missing",
             {"id": "tx", "outcome": {"status": {"SuccessValue": ""}}}),
            ("root_receipt_ids_not_list", {"id": "tx", "outcome": {
                "status": {"SuccessValue": ""}, "receipt_ids": "r1"}})):
        near = with_root(root)
        if label == "root_null":
            near["transaction_outcome"] = None
        comp = pp.analyze_completeness(near, "drpc")
        check(f"drpc.{label}", comp["complete"] is False
              and "transaction root" in comp["reason"],
              f"{comp['reason']}")
    # valid roots still complete
    comp = pp.analyze_completeness(
        with_root({"id": "tx", "outcome": {"status": {"SuccessValue": ""},
                                           "receipt_ids": ["r1"]}}), "drpc")
    check("drpc.root_valid", comp["complete"] is True, f"{comp['reason']}")
    # FastNEAR: root absent / non-object / receipt_ids not a list
    good_fn = {"receipts": [
                   {"receipt_id": "r1", "receiver_id": SRC,
                    "execution_outcome": {"id": "r1", "outcome": {
                        "status": {"SuccessValue": ""}, "receipt_ids": []}},
                    "receipt": {"Action": {}}}]}

    def fn_with_root(root):
        d = json.loads(json.dumps(good_fn))
        if root is not None:
            d["execution_outcome"] = root
        return d

    for label, root in (
            ("root_absent", None),
            ("root_non_object", "junk"),
            ("root_outcome_non_object", {"id": "tx", "outcome": "nope"}),
            ("root_receipt_ids_missing",
             {"id": "tx", "outcome": {"status": {"SuccessValue": ""}}}),
            ("root_receipt_ids_not_list", {"id": "tx", "outcome": {
                "status": {"SuccessValue": ""}, "receipt_ids": "r1"}})):
        comp = pp.analyze_completeness(fn_with_root(root), "fastnear")
        check(f"fn.{label}", comp["complete"] is False
              and ("transaction root" in comp["reason"]
                   or "execution_outcome" in comp["reason"]),
              f"{comp['reason']}")
    comp = pp.analyze_completeness(
        fn_with_root({"id": "tx", "outcome": {"status": {"SuccessValue": ""},
                                               "receipt_ids": ["r1"]}}), "fastnear")
    check("fn.root_valid", comp["complete"] is True, f"{comp['reason']}")

    print("== UNIT: matcher gross-only + order independence ==")
    rows = [{"recipient": "0x" + "c"*40, "amount": 10000, "source": "ft_burn_outcome_log"}] * 3
    recs = [{"status": "COMPLETED", "tx_hash": "A", "transfer_tx_hash": "0x" + "a"*64,
             "chain": "eth:8453", "amount": 10000, "fee": 2400, "withdraw_amount": 7600,
             "decimals": 6, "scope_problems": []},
            {"status": "COMPLETED", "tx_hash": "B", "transfer_tx_hash": "0x" + "b"*64,
             "chain": "eth:8453", "amount": 10000, "fee": 2400, "withdraw_amount": 7600,
             "decimals": 6, "scope_problems": []}]
    def mk_dest():
        return {("eth:8453", "0x" + "a"*64, "10000"):
                {"receipt_status": "0x1", "block": 1, "tip": 10, "confirmations": 9,
                 "transfers": [{"to": "0x" + "c"*40, "amount": 7600, "log_index": 1}]},
                ("eth:8453", "0x" + "b"*64, "10000"):
                {"receipt_status": "0x1", "block": 2, "tip": 10, "confirmations": 8,
                 "transfers": [{"to": "0x" + "c"*40, "amount": 7600, "log_index": 1}]}}
    fwd = pp.reconcile(rows, recs, mk_dest())
    rev = pp.reconcile(rows, list(reversed(recs)), mk_dest())
    def agg(rs):
        out = {}
        for r in rs:
            out[r["verdict"]] = out.get(r["verdict"], 0) + 1
        return out
    check("matcher.order_independent", agg(fwd) == agg(rev),
          f"forward {agg(fwd)} == reversed {agg(rev)}")
    g = [r for r in fwd if r.get("verdict") == "GROUP_FINDING"]
    check("matcher.group_counts", g and g[0]["observed"] == 2 and g[0]["unrecorded"] == 1,
          f"group observed/unrecorded = {g[0]['observed'] if g else None}/"
          f"{g[0]['unrecorded'] if g else None} (2/1 expected)")
    check("matcher.no_arbitrary_pick",
          not any(r.get("verdict") in ("OBSERVED_MATCH", "NOT_RECORDED") for r in fwd),
          "no row-level picks for indistinguishable rows")
    # net coincidence refused
    rec_net = [dict(recs[0], amount=20000, fee=10000, withdraw_amount=10000)]
    single = [{"recipient": "0x" + "c"*40, "amount": 10000, "source": "ft_burn_outcome_log"}]
    out = pp.reconcile(single, rec_net, {})
    check("matcher.gross_only", any(r["verdict"] == "NOT_RECORDED" for r in out),
          "gross 10000 does not match record gross 20000 even if net equals 10000")

    print("== UNIT: distinct equal-amount bridge records (identity must survive) ==")
    base = {"withdrawals": [{"status": "COMPLETED", "data": {
        "tx_hash": "T1", "transfer_tx_hash": "0x" + "1"*64, "chain": "eth:8453",
        "decimals": 6, "amount": "10000", "withdrawal_fee": "2400",
        "withdraw_amount": "7600", "near_token_id": pp.SUPPORTED["source_token"],
        "defuse_asset_identifier": f"eth:8453:{pp.SUPPORTED['dest_token']}"}}]}
    twin = json.loads(json.dumps(base))
    twin["withdrawals"][0]["data"]["transfer_tx_hash"] = "0x" + "2"*64
    both, _ = pp.normalize_bridge({"withdrawals": base["withdrawals"] + twin["withdrawals"]})
    check("bridge.distinct_destinations", len(both) == 2,
          f"same source tx + amount, distinct destination tx -> {len(both)} records (expect 2)")
    check("bridge.dup_is_idempotent", len(pp.normalize_bridge(
        {"withdrawals": base["withdrawals"] * 2})[0]) == 1, "exact repeat deduped to 1")

    print("== UNIT: equal-amount two recipients, both record orders ==")
    A, B = "0x" + "c"*40, "0x" + "d"*40
    rows2 = [{"recipient": A, "amount": 10000, "source": "x"},
             {"recipient": B, "amount": 10000, "source": "x"}]
    def mk_rec(tx, tr): return dict(recs[0], tx_hash=tx, transfer_tx_hash=tr)
    def mk_dest(tx, to): return (("eth:8453", tx, "10000"),
        {"receipt_status": "0x1", "block": 1, "tip": 9, "confirmations": 8,
         "transfers": [{"to": to, "amount": 7600, "log_index": 1}]})
    ra, rb = mk_rec("TA", "0x" + "a"*64), mk_rec("TB", "0x" + "b"*64)
    dm2 = dict([mk_dest("0x" + "a"*64, A), mk_dest("0x" + "b"*64, B)])
    f2 = agg(pp.reconcile(rows2, [ra, rb], dm2))
    r2 = agg(pp.reconcile(rows2, [rb, ra], dm2))
    check("matcher.two_recipients_orders", f2 == r2 and f2.get("OBSERVED_MATCH") == 2,
          f"forward {f2} reversed {r2} — both orders observe both (2/2)")

    print("== UNIT: traversal/completeness (derived, no injected flags) ==")
    print("  (graph builders exercised via fixtures fx_g4_*)")

    print("== UNIT: parser edge cases via fixtures fx_g1_* ==")
    print("  (attempt-vs-burn, native Failure, token mismatch exercised as cases)")

def main():
    print("== FIXTURE + OFFLINE assertions (synthetic labeled; offline = saved raw evidence) ==")
    for f in sorted(Path("fixtures").glob("*.json")):
        run_case_assert(f)
    units()
    if "--live" in sys.argv:
        print("== LIVE assertions (network-dependent, labeled) ==")
        LIVE = [
            ("863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe", "sponsor-staging.trezu.near",
             {"rows": 3, "prefix": "MISMATCH"},
             "QA №324: 3 burns, bridge keeps 1 -> grouped 1 observed / 2 unrecorded"),
            ("CbyrTsdExtWDbBsdUNqQC65JMBFwXEzkeaGJGmQb2QDz", "sponsor-staging.trezu.near",
             {"rows": 2, "prefix": "MISMATCH"},
             "QA №327: 2 burns (distinct), 1 observed / 1 not recorded"),
            ("FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu", "sponsor.trezu.near",
             {"rows": 1, "prefix": "ALL_ROWS_OBSERVED"},
             "production control #1: fully observed"),
            ("2t5s6uZjxQgdTwgdkxuW69FGWmwx4EvWnBdAZrSTw4xf", "sponsor.trezu.near",
             {"rows": 1, "prefix": "ALL_ROWS_OBSERVED"},
             "production control #2: fully observed"),
            ("EEDiWnLCkLGd8MizuqRut9K6GeBgLR9vU1WjdaQEJXCo", "intents.near",
             {"rows": 1, "prefix": "ALL_ROWS_OBSERVED"},
             "intents-order control: fully observed"),
        ]
        for tx, signer, want, label in LIVE:
            case = {"name": f"livetest_{tx[:12]}", "kind": "live", "near_tx": tx,
                    "signer": signer}
            try:
                rep = pp.run_case(case, Path("results/live_v3"))
            except Exception as e:
                check(f"live {tx[:12]}", False, f"{label}: raised {type(e).__name__}: {e}")
                continue
            s = rep["summary"]
            check(f"live {tx[:12]} rows", rep["rows_found"] == want["rows"],
                  f"{label}: rows={rep['rows_found']} want {want['rows']}")
            check(f"live {tx[:12]} overall", s["overall"].startswith(want["prefix"]),
                  f"{label}: {s['overall']!r} want prefix {want['prefix']!r}")
    print(f"\n{'ALL PASSED' if not FAILURES else 'FAILURES: ' + ', '.join(FAILURES)}")
    return 1 if FAILURES else 0

if __name__ == "__main__":
    sys.exit(main())
