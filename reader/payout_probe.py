#!/usr/bin/env python3
"""payout_probe.py v4 — fresh external acceptance repair (see CORRECTNESS.md for the
gate map; boundary-validation changes are marked  [v4]  throughout).

Supported scope (explicit): burns of the source token
  base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near
  bridged by the PoA bridge to eth:8453 USDC (0x833589fcd6edb6e08f4c7c32d4f71b54bda02913, 6 decimals).
Everything else returns an explicit unsupported state; nothing is guessed.

Ingestion (gate 1): rows come ONLY from successful execution-outcome logs
(nep141 ft_burn with memo WITHDRAW_TO:), each carrying executor token, outcome id and
log index. An attempted ft_withdraw with no successful burn is never a row.
Status objects are native NEAR shapes ({"Failure":..}, {"SuccessValue":..}, ...).
[v4] Boundary validation precedes matching: malformed JSON types (floats, booleans,
negative or non-numeric monetary fields, non-object records/events, non-list
child-edge arrays) are rejected as structured unsupported/inconclusive findings —
never truncated by int(), never silently skipped, never a crash.

Matching (gate 3): gross-to-gross only; indistinguishable rows produce a GROUP finding
(no arbitrary per-row "this one was paid"); destinations consumed once as
(chain, tx, log_index); equal records/transfers preserved; repeated observations
idempotent; unmatched extras are evidence, not overpayments.
[v4] The consumer key now includes the bridge record's own destination-transfer
identity (chain, transfer_tx_hash, log_index) so two burns pointing at one
destination tx with DISTINCT logs consume two distinct transfers, while repeated
copies of ONE log cannot satisfy two burns (identity reuse is reported, not counted).

Completeness (gate 4): endpoint-shaped graph walk over action receipts, execution
outcomes and data receipts. Pending/missing/empty/malformed => incomplete. No injected
`complete` flag, no assumed API cap (observed sizes documented in CORRECTNESS.md).
[v4] A valid executed drpc/FastNEAR outcome must carry the receipt_ids child-edge
array (present AND a list) — an executed outcome without the child-edge field is not
evidence of an empty child set. Real successful saved responses (drpc
near_qa1_full.json, FastNEAR fastnear_txs_probe.json) always carry it.

Status (gate 5): destination label is OBSERVED_MATCH — receipt success with
confirmations, never a finality/settlement claim. Overall surfaces source failure,
unmatched extras, required-leg failures and list-check availability.

List check (gate 6): optional/advisory only. Lists may span transactions; a row with no
burn in THIS tx is "not observed here", never a missed obligation. Failure => visibly
unavailable.

Modes: --live <tx> --signer <acct> [--list <id> --list-account <acct>] [--outdir DIR]
       --case <file>   --fixtures   --offline <name>   (offline = raw saved evidence)
No keys, funds, transactions, deployment. Exit 0 = ran; 1 = failure.
"""
import base64, json, re, sys, time, urllib.request
from pathlib import Path

BRIDGE_RPC = "https://bridge.chaindefuser.com/rpc"
NEAR_RPC = "https://near.drpc.org"
NEAR_VIEW_RPC = "https://rpc.mainnet.near.org"
FASTNEAR_TX = "https://tx.main.fastnear.com/v0/transactions"
BASE_RPC = "https://mainnet.base.org"

SUPPORTED = {
    "source_token": "base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near",
    "bridge_chain": "eth:8453",
    "bridge_asset": "eth:8453:0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    "dest_chain": "eth:8453",
    "dest_token": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    "decimals": 6,
}
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
EVM_RECIPIENT = re.compile(r"^0x[0-9a-fA-F]{40}$")
DISCLAIMER = ("missing observations are ambiguous, not proof of permanent loss; "
              "OBSERVED_MATCH is receipt-level evidence, not final settlement; "
              "no bridge root cause is established by absence of records")
RAW_LOG = []
FULL_BODY_CAP = 5_000_000


def _http(url, payload, timeout=25):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={
        "content-type": "application/json", "User-Agent": "curl/8.5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body, code = r.read().decode(), r.status
    except Exception as e:
        RAW_LOG.append((ts, url, payload, f"ERROR {type(e).__name__}: {e}", True))
        raise
    RAW_LOG.append((ts, url, payload, body[:FULL_BODY_CAP], False))
    return code, json.loads(body)


def normalize_status(st):
    """Native NEAR status -> label. Never stringifies dicts blindly."""
    if isinstance(st, dict) and st:
        return list(st.keys())[0]
    if isinstance(st, str):
        return st
    return "Unknown"


def success_outcome(status_label):
    return status_label in ("SuccessValue", "SuccessReceiptId")


# ------------------------------------------------- boundary validation [v4]
def _uint_from_json(v):
    """Integer >= 0 from an endpoint JSON value WITHOUT silent coercion.

    Accepts the two forms real saved successful responses use (JSON int, or decimal
    string of an int: bridge_qa1 '2400', trezu '10000'). Everything else — float
    (10000.75), bool, None, negative, non-decimal string, empty string — is rejected
    (returns None) so the caller reports unsupported/inconclusive instead of
    truncating. int() truncation of fractional values is never used for money.
    """
    if isinstance(v, bool):          # bool is an int subclass; never money
        return None
    if isinstance(v, int):
        return v if v >= 0 else None
    if isinstance(v, str):
        if not v or not v.isascii() or not v.isdigit():
            return None
        try:
            return int(v, 10)
        except ValueError:
            return None
    return None                      # float/None/list/dict/anything else


def _monetary_or_problem(field, raw):
    """(value, None) for a valid nonnegative integer monetary field, else
    (None, problem-string) describing the rejected JSON type/value."""
    if isinstance(raw, bool):
        return None, f"{field}={raw!r} is a boolean, not an integer amount"
    if isinstance(raw, float):
        return None, f"{field}={raw!r} is a float, fractional amounts unsupported"
    if isinstance(raw, int):
        if raw < 0:
            return None, f"{field}={raw} is negative"
        return raw, None
    if isinstance(raw, str):
        v = _uint_from_json(raw)
        if v is not None:
            return v, None
        return None, f"{field}={raw!r} is not a decimal integer string"
    if raw is None:
        return None, f"{field} is missing/null"
    return None, f"{field} has unsupported JSON type {type(raw).__name__}"


# ---------------------------------------------------------------- burns (gate 1)
def _burn_from_log(log, executor, outcome_id, log_index, outcome_status):
    """[v4] Malformed event data never raises: a burn whose amount/memo is unusable
    becomes a structured 'malformed_event' row instead of crashing the parser.
    [v5] A RECOGNIZED supported-scope withdrawal burn (nep141 ft_burn emitted by the
    supported token, i.e. exactly the class this reader is chartered to reconcile)
    whose `data` is absent/null or not a JSON array is malformed evidence and is
    reported as an INVALID_EVENT_ROW — an absent/invalid child set is NOT evidence of
    an empty child set. Policy for other content (exact, no guessing):
      - not an EVENT_JSON string, unparsable JSON, non-object JSON, or a different
        standard/event (ft_transfer, ft_metadata, …) -> not a withdrawal burn:
        ignored, no row, never a failure (unrelated event types are not ours).
      - nep141 ft_burn whose data IS a list but an entry is not an object ->
        malformed_event row (v4 rule, unchanged).
      - nep141 ft_burn with list data whose entries lack a WITHDRAW_TO: memo ->
        a valid non-withdrawal burn (e.g. a plain token burn): ignored, never a
        withdrawal failure (memo decides scope, and its absence is a fact, not a
        defect). A missing/None-typed memo is also ignored here; only a
        string-typed memo that starts with WITHDRAW_TO: claims withdrawal scope.
      - ft_burn from an executor OUTSIDE the supported token -> surfaced as an
        UNSUPPORTED_SCOPE row (v4 rule, unchanged); the v5 data-shape rules above
        apply only to supported-executor burns because that is the supported task."""
    if not isinstance(log, str) or not log.startswith("EVENT_JSON:"):
        return None
    try:
        ev = json.loads(log[len("EVENT_JSON:"):])
    except Exception:
        return None
    if not isinstance(ev, dict) or \
            ev.get("standard") != "nep141" or ev.get("event") != "ft_burn":
        return None
    data = ev.get("data")
    if not isinstance(data, list):
        # [v5] recognized burn event with absent/null/non-list data. Whether this
        # is *invalid evidence* (rather than ignorable) depends on whether the
        # emitting executor is in supported scope; the caller knows the executor,
        # so mark the row and let extract_burns apply scope.
        why = ("data is missing/null" if "data" not in ev or data is None
               else f"data is not a JSON array (got {type(data).__name__})")
        return [{"recipient": None, "amount": None, "burn_owner": None,
                 "executor": executor, "outcome_id": outcome_id,
                 "log_index": log_index, "outcome_status": outcome_status,
                 "source": "ft_burn_outcome_log",
                 "malformed_event": f"nep141 ft_burn {why}"}]
    out = []
    for d in data:
        if not isinstance(d, dict):
            out.append({"recipient": None, "amount": None, "burn_owner": None,
                        "executor": executor, "outcome_id": outcome_id,
                        "log_index": log_index, "outcome_status": outcome_status,
                        "source": "ft_burn_outcome_log",
                        "malformed_event": "burn event data entry is not an object"})
            continue
        memo = d.get("memo")
        if not isinstance(memo, str) or not memo.startswith("WITHDRAW_TO:"):
            continue
        amount, problem = _monetary_or_problem("amount", d.get("amount"))
        row = {
            "recipient": memo.split(":", 1)[1],
            "amount": amount,
            "burn_owner": d.get("owner_id"),
            "executor": executor,          # token contract that executed the burn
            "outcome_id": outcome_id,
            "log_index": log_index,
            "outcome_status": outcome_status,
            "source": "ft_burn_outcome_log",
        }
        if problem is not None:
            row["malformed_event"] = problem
        out.append(row)
    return out


def _fn_executor(r):
    """FastNEAR receipt entries appear both flat ({receiver_id,...}) and doubly
    nested ({receipt:{...,receipt:{Action:{receiver_id}}}}) — handle both."""
    if not isinstance(r, dict):
        return None
    if r.get("receiver_id"):
        return r["receiver_id"]
    h = r.get("receipt")
    if isinstance(h, dict):
        if h.get("receiver_id"):
            return h["receiver_id"]
        if "Action" in h and isinstance(h["Action"], dict):
            return h["Action"].get("receiver_id")
        inner = h.get("receipt")
        if isinstance(inner, dict) and "Action" in inner:
            return inner["Action"].get("receiver_id")
    return None


def _fn_receipt_kind(r):
    """Action vs data receipt for a FastNEAR entry (handles flat and nested holders)."""
    if not isinstance(r, dict):
        return "action"
    h = r.get("receipt")
    if isinstance(h, dict):
        if "Action" in h:
            return "action"
        if "DataReceipt" in h or "Data" in h or "ReceiptId" in h:
            return "data"
        inner = h.get("receipt")
        if isinstance(inner, dict):
            if "Action" in inner:
                return "action"
            if "DataReceipt" in inner or "Data" in inner or "ReceiptId" in inner:
                return "data"
    return "action"


def _fn_receipt_id(r):
    if not isinstance(r, dict):
        return None
    if r.get("receipt_id"):
        return r["receipt_id"]
    h = r.get("receipt")
    if isinstance(h, dict) and h.get("receipt_id"):
        return h["receipt_id"]
    oc = r.get("execution_outcome", {})
    return oc.get("id")


def extract_burns(near, source):
    """Return (rows, diag). rows only from SUCCESSFUL outcomes of the SUPPORTED token.
    Unsupported executor/memo forms become explicit row states, never silent drops.
    [v5] Source-boundary validation of the outcome collections themselves: every
    entry of receipts_outcome / receipts (drpc) and receipts (FastNEAR) must be an
    object with an object-typed nested outcome before dereferencing; a null or
    non-object entry makes the source malformed (UNSUPPORTED_SOURCE / never green)
    instead of raising, and is counted in diag['malformed_entries']."""
    rows, diag = [], {"attempts_no_burn": 0, "unsupported_executor": 0,
                      "unsupported_recipient_form": 0, "failed_outcome_logs": 0,
                      "outcomes_seen": 0, "malformed": False,
                      "malformed_events": 0, "malformed_entries": 0}
    outcomes = []   # (executor, outcome_id, status_label, logs)

    if source == "drpc":
        if not isinstance(near, dict) or not isinstance(
                near.get("receipts_outcome"), list):
            diag["malformed"] = True
            return rows, diag
        # real drpc outcomes carry {block_hash, id, outcome, proof} — no receiver_id;
        # executor (token contract) is mapped from the receipt body by id
        body_recv = {r.get("receipt_id"): r.get("receiver_id")
                     for r in near.get("receipts", []) if isinstance(r, dict)}
        for o in near.get("receipts_outcome", []):
            if not isinstance(o, dict):
                # [v5] null/str/num entry beside valid outcomes: structured, no crash
                diag["malformed_entries"] += 1
                continue
            rid = o.get("receipt_id") or o.get("id")
            oc = o.get("outcome")
            if not isinstance(oc, dict):
                # wrapper without an object outcome -> no execution evidence here;
                # completeness still holds the reachability verdict for this rid.
                oc = {}
            executor = (oc.get("executor_id") or o.get("receiver_id")
                        or body_recv.get(rid))
            outcomes.append((executor, rid,
                             normalize_status(oc.get("status")),
                             oc.get("logs", []) if isinstance(oc.get("logs"), list)
                             else []))
        txo = near.get("transaction_outcome")
        if isinstance(txo, dict):
            oc = txo.get("outcome")
            oc = oc if isinstance(oc, dict) else {}
            outcomes.append((oc.get("executor_id") or txo.get("receiver_id") or
                             body_recv.get(txo.get("id") or txo.get("receipt_id")),
                             txo.get("id") or txo.get("receipt_id"),
                             normalize_status(oc.get("status")),
                             oc.get("logs", []) if isinstance(oc.get("logs"), list)
                             else []))
    elif source == "fastnear":
        if not isinstance(near, dict) or not isinstance(near.get("receipts"), list):
            diag["malformed"] = True
            return rows, diag
        for r in near.get("receipts", []):
            if not isinstance(r, dict):
                # [v5] null/non-object receipt entry: structured, no crash
                diag["malformed_entries"] += 1
                continue
            oc = r.get("execution_outcome")
            inner = oc.get("outcome") if isinstance(oc, dict) else None
            if not isinstance(inner, dict):
                inner = {}
            executor = _fn_executor(r)
            outcomes.append((executor, _fn_receipt_id(r),
                             normalize_status(inner.get("status")),
                             inner.get("logs", []) if isinstance(inner.get("logs"), list)
                             else []))
        top = near.get("execution_outcome")
        if isinstance(top, dict):
            oc = top.get("outcome")
            oc = oc if isinstance(oc, dict) else {}
            outcomes.append((near.get("transaction", {}).get("receiver_id"),
                             top.get("id"),
                             normalize_status(oc.get("status")),
                             oc.get("logs", []) if isinstance(oc.get("logs"), list)
                             else []))
    else:
        diag["malformed"] = True
        return rows, diag

    for executor, oid, st, logs in outcomes:
        diag["outcomes_seen"] += 1
        for li, log in enumerate(logs):
            got = _burn_from_log(log, executor, oid, li, st)
            if got is None:
                continue
            if not success_outcome(st):
                diag["failed_outcome_logs"] += 1
                continue          # a burn log on a failed/pending outcome is not verified
            for g in got:
                # [v4] malformed burn evidence is surfaced, never dropped or crashed on
                if g.get("malformed_event"):
                    if executor != SUPPORTED["source_token"]:
                        # [v5] malformed burn emitted by an out-of-scope executor:
                        # malformed AND unsupported — treat as unsupported scope,
                        # not a withdrawal failure of the supported task.
                        diag["unsupported_executor"] += 1
                        g["unsupported"] = (f"executor token {executor} outside "
                                            f"supported scope (malformed event "
                                            f"ignored: {g['malformed_event']})")
                        rows.append(g)
                        continue
                    diag["malformed_events"] += 1
                    rows.append(g)      # carried as INVALID_EVENT_ROW at match time
                    continue
                if executor != SUPPORTED["source_token"]:
                    diag["unsupported_executor"] += 1
                    g["unsupported"] = f"executor token {executor} outside supported scope"
                    rows.append(g)
                    continue
                if not EVM_RECIPIENT.match(g["recipient"]):
                    diag["unsupported_recipient_form"] += 1
                    g["unsupported"] = (f"recipient form {g['recipient'][:16]}… not an EVM "
                                        f"address; destination chain outside scope")
                rows.append(g)

    if not rows:
        # attempted ft_withdraw with memo but no successful burn => not a withdrawal
        def count_attempts(o):
            n = 0
            if isinstance(o, dict):
                if "FunctionCall" in o and o["FunctionCall"].get("method_name") == "ft_withdraw":
                    try:
                        args = json.loads(base64.b64decode(o["FunctionCall"].get("args", "")))
                        if str(args.get("memo", "")).startswith("WITHDRAW_TO:"):
                            n += 1
                    except Exception:
                        pass
                for v in o.values():
                    n += count_attempts(v)
            elif isinstance(o, list):
                for v in o:
                    n += count_attempts(v)
            return n
        diag["attempts_no_burn"] = count_attempts(near.get("receipts", []) if isinstance(near, dict) else [])
    return rows, diag


# ------------------------------------------------------------ completeness (gate 4)
def analyze_completeness(near, source):
    """Endpoint-shaped reachable-graph walk. Returns complete True/False/None reasons.
    Distinguishes action receipts (have outcomes), execution outcomes, data receipts.
    Empty/malformed/pending => never complete."""
    res = {"complete": False, "reason": "", "action_outcomes": 0, "referenced": 0,
           "resolved": 0, "data_receipts": 0, "pending": False}
    if not isinstance(near, dict) or not near:
        res["reason"] = "empty or non-dict response"
        return res
    if source == "drpc":
        receipts = near.get("receipts")
        outcs = near.get("receipts_outcome")
        if not isinstance(receipts, list) or not isinstance(outcs, list) or not outcs:
            res["reason"] = "malformed: receipts/receipts_outcome missing or not lists"
            return res
        fetched_bodies = {}
        for r in receipts:
            if isinstance(r, dict) and r.get("receipt_id"):
                kind = "data" if ("Data" in r.get("receipt", {}) or
                                  "DataReceipt" in r.get("receipt", {})) else "action"
                fetched_bodies[r["receipt_id"]] = kind
        by_id = {}          # rid -> outcome dict ONLY when execution evidence is valid
        wrappers = set()    # rid present as an outcome wrapper without execution status
        structure_bad = []  # rids whose executed outcome lacks child-edge evidence [v4]
        for o in outcs:
            if not isinstance(o, dict):
                continue
            rid = o.get("receipt_id") or o.get("id")
            oc = o.get("outcome")
            if not isinstance(oc, dict) or not oc or "status" not in oc:
                wrappers.add(rid)      # wrapper/body without execution evidence
                continue
            st = normalize_status(oc.get("status"))
            if st.startswith("Pending"):
                res["pending"] = True
            elif st not in ("SuccessValue", "SuccessReceiptId", "Failure"):
                wrappers.add(rid)      # unknown/uninterpretable status
                continue
            # [v4] an EXECUTED outcome must carry its child-edge array receipt_ids
            # (present and a list): an executed outcome without the child-edge field
            # is missing graph structure, NOT evidence of an empty child set. Every
            # saved successful drpc response (near_qa1_full/qa2) carries it.
            if "receipt_ids" not in oc or not isinstance(oc["receipt_ids"], list):
                if rid:
                    structure_bad.append(rid)
                res["action_outcomes"] += 1
                continue
            by_id[rid] = oc            # executed (Failure counts as executed)
            res["action_outcomes"] += 1
        # reachable set: start at tx outcome receipt_ids, walk outcome.receipt_ids
        # [v5] The transaction root (transaction_outcome.outcome.receipt_ids) is
        # REQUIRED graph structure, not an optional hint: without it there is no
        # evidence the reachable set started at the requested transaction, and
        # roots must never be guessed from receipt ordering. A missing, non-object
        # or non-list-child root makes the graph incomplete. Every saved successful
        # drpc response (near_qa1_full/qa2) carries transaction_outcome.outcome
        # .receipt_ids as a list.
        root_problem = None
        txo = near.get("transaction_outcome")
        txo_outcome = txo.get("outcome") if isinstance(txo, dict) else None
        if not isinstance(txo, dict):
            root_problem = "transaction_outcome missing"
        elif not isinstance(txo_outcome, dict):
            root_problem = "transaction_outcome.outcome missing or not an object"
        elif "receipt_ids" not in txo_outcome:
            root_problem = "transaction root missing receipt_ids child-edge array"
        elif not isinstance(txo_outcome["receipt_ids"], list):
            root_problem = ("transaction root receipt_ids is not a list "
                            f"(got {type(txo_outcome['receipt_ids']).__name__})")
        if root_problem is not None:
            res["reason"] = f"malformed transaction root: {root_problem}"
            res["missing"] = 1
            return res
        roots = []
        roots.extend(txo_outcome.get("receipt_ids") or [])
        seen, stack = set(), list(roots)
        while stack:
            rid = stack.pop()
            if rid in seen:
                continue
            seen.add(rid)
            oc = by_id.get(rid)
            if oc is not None:
                for c in oc.get("receipt_ids", []) or []:
                    stack.append(c)
        res["referenced"] = len(seen)
        missing = []
        for rid in seen:
            if rid in by_id:
                res["resolved"] += 1
            elif fetched_bodies.get(rid) == "data":
                res["data_receipts"] += 1
                res["resolved"] += 1
            elif rid in wrappers:
                missing.append(rid)    # reachable wrapper without execution evidence
            elif rid in structure_bad:
                # [v4] executed outcome reachable but child edges not evidenced
                missing.append(rid)
            else:
                # action body without outcome, or neither body nor outcome: unresolved
                missing.append(rid)
        if res["pending"]:
            res["reason"] = "pending outcome in reachable graph"
        elif missing:
            res["reason"] = (f"{len(missing)} reachable action(s) without valid executed "
                             f"outcome/data resolution"
                             + (f" ({len(structure_bad)} executed outcome(s) missing "
                                f"required receipt_ids child-edge array)"
                                if structure_bad else ""))
        elif res["action_outcomes"] == 0:
            res["reason"] = "no execution outcomes in response"
        else:
            res["complete"] = True
            res["reason"] = "reachable graph fully resolved"
        res["missing"] = len(set(missing))
        return res
    elif source == "fastnear":
        receipts = near.get("receipts")
        if not isinstance(receipts, list) or not receipts:
            res["reason"] = "malformed: receipts missing/empty"
            return res
        by_id, data_ids = {}, set()
        for dr in near.get("data_receipts", []) or []:
            if isinstance(dr, dict) and dr.get("id"):
                data_ids.add(dr["id"])
        wrappers = set()
        structure_bad = []  # rids whose executed outcome lacks child-edge evidence [v4]
        for r in receipts:
            if not isinstance(r, dict):
                continue
            if _fn_receipt_kind(r) == "data":
                oid = _fn_receipt_id(r)
                if oid:
                    data_ids.add(oid)
                continue
            oc = r.get("execution_outcome") or {}
            inner = oc.get("outcome") if isinstance(oc, dict) else None
            oid = _fn_receipt_id(r)
            if not isinstance(inner, dict) or not inner or "status" not in inner:
                if oid:
                    wrappers.add(oid)   # receipt present, no execution evidence
                continue
            st = normalize_status(inner.get("status"))
            if st.startswith("Pending"):
                res["pending"] = True
            elif st not in ("SuccessValue", "SuccessReceiptId", "Failure"):
                if oid:
                    wrappers.add(oid)
                continue
            # [v4] executed FastNEAR outcome must carry receipt_ids child edges
            # (raw fastnear_txs_probe.json outcomes all carry the field)
            if "receipt_ids" not in inner or not isinstance(inner["receipt_ids"], list):
                if oid:
                    structure_bad.append(oid)
                res["action_outcomes"] += 1
                continue
            if oid:
                by_id[oid] = inner
            res["action_outcomes"] += 1
        # [v5] FastNEAR transaction root is REQUIRED, mirroring drpc: without the
        # top-level execution_outcome (with its receipt_ids child-edge list) there
        # is no evidence the reachable set started at the requested transaction.
        # Roots are never guessed from receipt ordering. Every saved successful
        # FastNEAR response (fastnear_txs_probe.json, offline_control fixture)
        # carries execution_outcome.outcome.receipt_ids as a list.
        root_problem = None
        top = near.get("execution_outcome")
        top_outcome = top.get("outcome") if isinstance(top, dict) else None
        if not isinstance(top, dict):
            root_problem = "execution_outcome (transaction root) missing"
        elif not isinstance(top_outcome, dict):
            root_problem = ("execution_outcome.outcome missing or not an object "
                            f"(got {type(top.get('outcome')).__name__})")
        elif "receipt_ids" not in top_outcome:
            root_problem = "transaction root missing receipt_ids child-edge array"
        elif not isinstance(top_outcome["receipt_ids"], list):
            root_problem = ("transaction root receipt_ids is not a list "
                            f"(got {type(top_outcome['receipt_ids']).__name__})")
        if root_problem is not None:
            res["reason"] = f"malformed transaction root: {root_problem}"
            res["missing"] = 1
            return res
        roots = []
        roots.extend(top_outcome.get("receipt_ids") or [])
        seen, stack = set(), [x for x in roots if x]
        while stack:
            rid = stack.pop()
            if rid in seen:
                continue
            seen.add(rid)
            oc = by_id.get(rid)
            if oc is not None:
                for c in oc.get("receipt_ids", []) or []:
                    stack.append(c)
        res["referenced"] = len(seen)
        missing = [rid for rid in seen
                   if rid not in by_id and rid not in data_ids and rid not in wrappers
                   and rid not in structure_bad]
        # wrappers reachable but invalid count as unresolved too
        missing += [rid for rid in seen if rid in wrappers]
        missing += [rid for rid in seen if rid in structure_bad]   # [v4]
        missing = list(dict.fromkeys(missing))
        res["resolved"] = len(seen) - len(missing)
        res["data_receipts"] = len(data_ids)
        if res["pending"]:
            res["reason"] = "pending outcome in reachable graph"
        elif missing:
            res["reason"] = (f"{len(missing)} reachable receipt(s) unresolved"
                             + (f" ({len(structure_bad)} executed outcome(s) missing "
                                f"required receipt_ids child-edge array)"
                                if structure_bad else ""))
        else:
            res["complete"] = True
            res["reason"] = "reachable graph fully resolved"
        res["missing"] = len(missing)
        return res
    res["reason"] = "unknown source"
    return res


# ---------------------------------------------------------------- NEAR fetch
def _normalize_fastnear_tx(txobj):
    # preserve the original receipt structure (flat or nested); only add labels
    out = dict(txobj)
    out["_source"] = "fastnear"
    # [v5] type-check before dereferencing (malformed root evidence)
    eo = txobj.get("execution_outcome")
    eo_out = eo.get("outcome") if isinstance(eo, dict) else None
    out["status"] = normalize_status(eo_out.get("status")) \
        if isinstance(eo_out, dict) else None
    out["final_execution_status"] = "not_reported_by_fastnear"
    return out


def fetch_near(tx, signer):
    err = None
    for attempt in range(2):
        try:
            _, resp = _http(NEAR_RPC, {"jsonrpc": "2.0", "id": 1,
                                       "method": "EXPERIMENTAL_tx_status",
                                       "params": [tx, signer]})
            if "result" in resp:
                r = resp["result"]
                r["_source"] = "drpc"
                return r
            err = f"RPC error {resp.get('error')}"
            break
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            time.sleep(2 * (attempt + 1))
    try:
        _, resp = _http(FASTNEAR_TX, {"tx_hashes": [tx]}, timeout=30)
        txs = resp.get("transactions") or []
        if txs:
            return _normalize_fastnear_tx(txs[0])
        err = (err or "") + " | FastNEAR: hash not found"
    except Exception as e:
        err = (err or "") + f" | FastNEAR {type(e).__name__}: {e}"
    raise RuntimeError(f"NEAR leg unavailable ({err})")


# ---------------------------------------------------------------- bridge
def normalize_bridge(result):
    """Validate scope per record; preserve equal records; idempotent on exact repeats.
    [v4] Boundary validation: monetary fields must be genuine nonnegative integer
    JSON values (int or decimal-int string, as in the saved live responses);
    floats/bools/negatives/non-numeric are rejected with a per-record
    invalid_accounting problem instead of int()-truncated. Non-object entries in
    withdrawals[] are preserved as explicit INVALID_RECORD records (never silently
    skipped), so malformed returned evidence cannot hide behind a completeness claim.
    Returns (records, malformed_flag)."""
    records, seen = [], set()
    malformed = False
    if not isinstance(result, dict) or "withdrawals" not in result:
        return None            # malformed -> caller returns unsupported
    wds = result.get("withdrawals")
    if not isinstance(wds, list):
        return None
    for w in wds:
        if not isinstance(w, dict):
            # [v4] null/str/int entries beside valid records are surfaced, not skipped
            malformed = True
            records.append({"status": None, "tx_hash": None, "transfer_tx_hash": None,
                            "chain": None, "amount": None, "fee": None,
                            "withdraw_amount": None, "decimals": None,
                            "near_token_id": None, "defuse_asset": None,
                            "created_at": None,
                            "invalid_accounting": (
                                f"bridge withdrawal entry is not an object "
                                f"(got {type(w).__name__})"),
                            "scope_problems": [], "malformed_entry": True})
            continue
        d = w.get("data")
        if not isinstance(d, dict):
            malformed = True
            records.append({"status": w.get("status"), "tx_hash": None,
                            "transfer_tx_hash": None, "chain": None, "amount": None,
                            "fee": None, "withdraw_amount": None, "decimals": None,
                            "near_token_id": None, "defuse_asset": None,
                            "created_at": None,
                            "invalid_accounting": (
                                f"bridge withdrawal data is not an object "
                                f"(got {type(d).__name__})"),
                            "scope_problems": [], "malformed_entry": True})
            continue
        key = (d.get("tx_hash"), str(d.get("amount")), d.get("transfer_tx_hash"))
        if key in seen:
            continue           # repeated observation: idempotent
        seen.add(key)
        raw_amount, raw_fee = d.get("amount"), d.get("withdrawal_fee")
        raw_net = d.get("withdraw_amount")
        # [v4] strict integer typing: no int() truncation of fractional values
        amount, p_amt = _monetary_or_problem("amount", raw_amount)
        fee, p_fee = _monetary_or_problem("withdrawal_fee", raw_fee)
        net, p_net = _monetary_or_problem("withdraw_amount", raw_net)
        rec = {"status": w.get("status"), "tx_hash": d.get("tx_hash"),
               "transfer_tx_hash": d.get("transfer_tx_hash"), "chain": d.get("chain"),
               "amount": amount, "fee": fee, "withdraw_amount": net,
               "decimals": d.get("decimals"),
               "near_token_id": d.get("near_token_id"),
               "defuse_asset": d.get("defuse_asset_identifier"),
               "created_at": d.get("created_at")}
        if p_amt or p_fee or p_net:
            malformed = True
        problems = []
        if rec["chain"] != SUPPORTED["bridge_chain"]:
            problems.append(f"chain {rec['chain']} outside supported scope")
        if rec["defuse_asset"] and rec["defuse_asset"] != SUPPORTED["bridge_asset"]:
            problems.append(f"bridge asset {rec['defuse_asset']} != supported USDC asset")
        if rec["near_token_id"] and rec["near_token_id"] != SUPPORTED["source_token"]:
            problems.append(f"near token {rec['near_token_id']} != supported source token")
        try:
            dec_ok = rec["decimals"] is None or int(rec["decimals"]) == SUPPORTED["decimals"]
        except (TypeError, ValueError):
            dec_ok = False
        if not dec_ok:
            problems.append(f"decimals {rec['decimals']!r} != {SUPPORTED['decimals']}")
        # integer monetary accounting: gross > 0, fee/net >= 0, gross == fee + net
        money_problems = [p for p in (p_amt, p_fee, p_net) if p]
        if money_problems:
            rec["invalid_accounting"] = "; ".join(money_problems)
        elif amount is None or fee is None or net is None:
            rec["invalid_accounting"] = (
                f"non-integer monetary fields amount={raw_amount!r} "
                f"fee={raw_fee!r} net={raw_net!r}")
        elif amount <= 0:
            rec["invalid_accounting"] = f"gross must be positive, got {amount}"
        elif fee < 0 or net < 0:
            rec["invalid_accounting"] = f"fee/net must be nonnegative, got {fee}/{net}"
        elif amount != fee + net:
            rec["invalid_accounting"] = (
                f"gross {amount} != fee {fee} + net {net}")
        else:
            rec["invalid_accounting"] = None
        rec["scope_problems"] = problems
        records.append(rec)
    return records, malformed


def fetch_bridge(tx):
    _, resp = _http(BRIDGE_RPC, {"jsonrpc": "2.0", "id": 1, "method": "withdrawal_status",
                                 "params": [{"withdrawal_hash": tx}]})
    if "error" in resp:
        raise RuntimeError(f"bridge error: {resp['error']}")
    return normalize_bridge(resp.get("result"))


# ---------------------------------------------------------------- destination
def build_dest_from_receipt(receipt, record, tip=None):
    key = (record["chain"], record["transfer_tx_hash"], str(record["amount"]))
    if record["chain"] != SUPPORTED["dest_chain"]:
        return key, {"unsupported": record["chain"]}
    if not record["transfer_tx_hash"] or record["status"] != "COMPLETED":
        return key, {"pending": True, "status": record["status"]}
    if receipt is None:
        return key, {"error": "destination receipt not found — observation absent, "
                              "not proof of loss"}
    if not isinstance(receipt, dict):
        return key, {"error": "invalid: destination receipt is not an object"}
    # response identity: when the endpoint returns transactionHash it must be the
    # requested destination tx (guards stale/malformed provider responses)
    rhash = receipt.get("transactionHash")
    if rhash and str(rhash).lower() != str(record["transfer_tx_hash"]).lower():
        return key, {"error": f"invalid: receipt transactionHash {rhash} != requested "
                              f"{record['transfer_tx_hash']}"}
    to = receipt.get("to")
    if to and str(to).lower() != SUPPORTED["dest_token"].lower():
        return key, {"error": f"invalid: receipt `to` {to} is not the expected USDC "
                              f"contract"}
    status = receipt.get("status")
    try:
        block = int(receipt.get("blockNumber", "0x0"), 16)
    except (TypeError, ValueError):
        return key, {"error": "invalid: destination receipt blockNumber malformed"}
    conf = (tip - block) if isinstance(tip, int) else None
    if status == "0x0":
        # executed but reverted: evidence of failure, not of absence
        return key, {"reverted": True, "receipt_status": status, "transfers": [],
                     "block": block, "tip": tip, "confirmations": conf}
    if status != "0x1":
        return key, {"error": f"invalid: destination receipt status {status!r} "
                              f"missing or malformed"}
    transfers = []
    for lg in receipt.get("logs", []) or []:
        if (isinstance(lg, dict) and lg.get("topics")
                and lg["topics"][0] == TRANSFER_TOPIC
                and lg.get("address", "").lower() == SUPPORTED["dest_token"].lower()
                and len(lg["topics"]) >= 3):
            try:
                amt = int(lg["data"], 16)
                lgi = int(lg.get("logIndex", "0x0"), 16)
            except (TypeError, ValueError):
                continue
            transfers.append({"to": "0x" + lg["topics"][2][-40:],
                              "amount": amt, "log_index": lgi})
    return key, {"receipt_status": status, "transfers": transfers,
                 "block": block, "tip": tip, "confirmations": conf,
                 "label": "DEST_OBSERVED (receipt success; not final settlement)"}


def fetch_dest(records):
    out = {}
    try:
        _, r = _http(BASE_RPC, {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber",
                                "params": []}, timeout=15)
        tip = int(r.get("result", "0x0"), 16)
    except Exception:
        tip = None
    for rec in records:
        if rec.get("scope_problems"):
            continue            # out-of-scope records are reported at match time
        if rec["chain"] != SUPPORTED["dest_chain"]:
            out[(rec["chain"], rec["transfer_tx_hash"], str(rec["amount"]))] = \
                {"unsupported": rec["chain"]}
            continue
        if not rec["transfer_tx_hash"] or rec["status"] != "COMPLETED":
            out[(rec["chain"], rec["transfer_tx_hash"], str(rec["amount"]))] = \
                {"pending": True, "status": rec["status"]}
            continue
        try:
            _, resp = _http(BASE_RPC, {"jsonrpc": "2.0", "id": 1,
                                       "method": "eth_getTransactionReceipt",
                                       "params": [rec["transfer_tx_hash"]]}, timeout=20)
            key, entry = build_dest_from_receipt(resp.get("result"), rec, tip)
            out[key] = entry
        except Exception as e:
            out[(rec["chain"], rec["transfer_tx_hash"], str(rec["amount"]))] = {
                "error": f"destination RPC unavailable: {type(e).__name__}: {e}"}
    return out


# ---------------------------------------------------------------- list (gate 6)
def fetch_view_list(account, list_id):
    args_b64 = base64.b64encode(json.dumps({"list_id": list_id}).encode()).decode()
    _, resp = _http(NEAR_VIEW_RPC, {"jsonrpc": "2.0", "id": 1, "method": "query",
                                    "params": {"request_type": "call_function",
                                               "finality": "final", "account_id": account,
                                               "method_name": "view_list",
                                               "args_base64": args_b64}}, timeout=25)
    if "result" not in resp:
        raise RuntimeError(f"view_list error: {resp.get('error')}")
    obj = json.loads(bytes(resp["result"]["result"]))
    obligations = []
    for p in obj.get("payments", []):
        st = p.get("status", {})
        label = list(st.keys())[0] if isinstance(st, dict) and st else str(st)
        obligations.append({"recipient": p.get("recipient"), "amount": int(p.get("amount", 0)),
                            "status": label})
    return {"list_id": list_id, "account": account, "list_status": obj.get("status"),
            "obligations": obligations}


def list_advisory(obligations, rows):
    """Advisory aggregate only. A row without a burn in THIS tx is 'not observed here'
    — lists may span transactions; never a missed obligation (gate 6)."""
    from collections import Counter
    obl = Counter((o["recipient"], o["amount"]) for o in obligations)
    brn = Counter((r["recipient"], r["amount"]) for r in rows if not r.get("unsupported"))
    notes = []
    for key in sorted(set(obl) | set(brn), key=str):
        no, nb = obl.get(key, 0), brn.get(key, 0)
        if no > nb:
            notes.append(f"list approves {no}x {key[1]} to {key[0][:10]}… but this tx shows "
                         f"{nb} burn(s) — not observed in THIS tx (list may span "
                         f"transactions; not a missed obligation)")
        elif nb > no:
            notes.append(f"this tx burns {nb}x {key[1]} to {key[0][:10]}… beyond the list's "
                         f"{no} (advisory)")
    return notes


# ---------------------------------------------------------------- matching (gate 3)
def reconcile(rows, records, dest, fee_hint=None):
    results = []
    # out-of-scope rows
    scoped, unsupported_rows = [], []
    for i, r in enumerate(rows):
        # [v5] scope precedence: an event emitted by an out-of-scope executor is
        # UNSUPPORTED_SCOPE whether or not its payload is also malformed — the
        # supported task never claims (or fails on) other contracts' events.
        if r.get("unsupported"):
            unsupported_rows.append((i, r))
        elif r.get("malformed_event"):
            # [v4] malformed burn evidence: structured row verdict, never a crash
            results.append({"row": i, "recipient": r.get("recipient"),
                            "amount": r.get("amount"),
                            "verdict": "INVALID_EVENT_ROW",
                            "note": f"burn event unusable: {r['malformed_event']}"})
        else:
            scoped.append((i, r))
    for i, r in unsupported_rows:
        results.append({"row": i, "recipient": r["recipient"], "amount": r["amount"],
                        "verdict": "UNSUPPORTED_SCOPE", "note": r["unsupported"]})
    # out-of-scope / malformed bridge records
    usable_records = []
    for r in records:
        if r.get("scope_problems"):
            results.append({"row": None, "recipient": None, "amount": r["amount"],
                            "verdict": "UNSUPPORTED_BRIDGE",
                            "note": "; ".join(r["scope_problems"])})
        else:
            usable_records.append(r)

    # group indistinguishable scoped rows (recipient, amount) — no arbitrary row picking
    groups = {}
    for i, r in scoped:
        groups.setdefault((r["recipient"], r["amount"]), []).append((i, r))

    rec_used = set()
    consumed = set()   # (chain, tx, log_index)

    # --- record -> group assignment (gate: reversed equal-amount records must not
    # change the finding, and equal-amount records for DIFFERENT recipients must each
    # find their recipient). Bridge records carry no recipient; destination evidence
    # provides it. Pass A: assign via dest-evidenced recipient. Pass B: unambiguous
    # fallback (single needy group). Multi-group leftovers stay unattributed rather
    # than being guessed.
    assignment = {k: [] for k in groups}
    by_amount = {}
    for r in usable_records:
        by_amount.setdefault(r["amount"], []).append(r)
    for amt, recs in by_amount.items():
        gkeys = sorted([k for k in groups if k[1] == amt], key=str)
        if not gkeys:
            continue
        recs_sorted = sorted(recs, key=lambda r: str(r.get("tx_hash")))
        evidenced, leftovers = {k: [] for k in gkeys}, []
        for r in recs_sorted:
            hit = None
            if (r["chain"] == SUPPORTED["dest_chain"] and r["status"] == "COMPLETED"
                    and r["transfer_tx_hash"]):
                d = dest.get((r["chain"], r["transfer_tx_hash"], str(amt)), {})
                for gk in gkeys:
                    recip = gk[0]
                    if any(t["to"].lower() == recip.lower()
                           and t["amount"] == r["withdraw_amount"]
                           for t in d.get("transfers", [])):
                        hit = gk
                        break
            if hit is not None:
                evidenced[hit].append(r)
            else:
                leftovers.append(r)
        needy = [gk for gk in gkeys if not evidenced[gk]]
        if len(needy) == 1 and leftovers:
            evidenced[needy[0]].extend(leftovers)
            leftovers = []
        # leftover records with no needy single group remain unattributed (unmatched)
        for gk in gkeys:
            assignment[gk] = list(evidenced[gk])

    for (recipient, amount), members in sorted(groups.items(), key=lambda kv: str(kv[0])):
        matched_recs = assignment.get((recipient, amount), [])
        n = len(members)
        observed = 0
        details = []
        # per-record state counters (never negative; a record fills at most one slot)
        st = {"pending": 0, "unavailable": 0, "invalid_dest": 0,
              "invalid_record": 0, "reverted": 0, "no_transfer": 0}
        slots = 0
        for r in matched_recs:
            if slots >= n:
                break   # surplus record beyond the group's burns: leave UNUSED so it
                        # surfaces as UNMATCHED_BRIDGE_RECORD (no silent absorption)
            rec_used.add((r["tx_hash"], str(r["amount"]), r["transfer_tx_hash"]))
            slots += 1
            if r.get("invalid_accounting"):
                st["invalid_record"] += 1
                details.append(f"bridge record unusable ({r['invalid_accounting']})")
                continue
            if r["chain"] != SUPPORTED["dest_chain"] or r["status"] != "COMPLETED" \
                    or not r["transfer_tx_hash"]:
                st["pending"] += 1
                details.append(f"bridge {r['status'] or 'no-destination-tx'}")
                continue
            d = dest.get((r["chain"], r["transfer_tx_hash"], str(r["amount"])), {})
            if d.get("error"):
                if str(d.get("error")).startswith("invalid:"):
                    st["invalid_dest"] += 1
                    details.append(str(d["error"]))
                else:
                    st["unavailable"] += 1
                    details.append(f"dest unavailable ({d['error'][:60]})")
                continue
            if d.get("reverted"):
                st["reverted"] += 1
                details.append(f"destination receipt reverted (status 0x0) at "
                               f"{r['transfer_tx_hash']}")
                continue
            if not d:
                st["unavailable"] += 1
                details.append("dest observation missing")
                continue
            same = [t for t in d.get("transfers", [])
                    if t["to"].lower() == recipient.lower()
                    and t["amount"] == r["withdraw_amount"]]
            free = [t for t in same
                    if (SUPPORTED["dest_chain"], r["transfer_tx_hash"], t["log_index"])
                    not in consumed]
            if free:
                t = free[0]
                consumed.add((SUPPORTED["dest_chain"], r["transfer_tx_hash"], t["log_index"]))
                observed += 1
                details.append(
                    f"dest tx {r['transfer_tx_hash']} log {t['log_index']} pays "
                    f"{t['amount']} (= gross {r['amount']} − fee {r['fee']}); "
                    f"receipt {d.get('receipt_status')} block {d.get('block')} "
                    f"confirmations {d.get('confirmations')} vs tip {d.get('tip')} — "
                    f"OBSERVED_MATCH, not final settlement")
            elif same:
                st["no_transfer"] += 1
                details.append(f"{len(same)} identical transfer(s) in "
                               f"{r['transfer_tx_hash']} already consumed — count deficit")
            else:
                st["no_transfer"] += 1
                details.append(f"destination tx {r['transfer_tx_hash']} has no USDC "
                               f"transfer of {r['withdraw_amount']} to {recipient} — "
                               f"check manually")
        unrecorded = max(0, n - slots)
        if n == 1:
            i, r = members[0]
            if slots == 0:
                note = ("burned on NEAR; no bridge record with this gross amount — "
                        "ambiguous, NOT proof of permanent loss")
                if fee_hint:
                    note += (f"; gross {amount}, hypothetical net {amount - fee_hint} after "
                             f"the fee observed elsewhere — ESTIMATE, not evidence")
                results.append({"row": i, "recipient": recipient, "amount": amount,
                                "verdict": "NOT_RECORDED", "note": note})
            else:
                if observed:
                    verdict = "OBSERVED_MATCH"
                elif st["unavailable"]:
                    verdict = "INCONCLUSIVE"
                elif st["invalid_dest"]:
                    verdict = "INCONCLUSIVE"
                elif st["invalid_record"]:
                    verdict = "INVALID_RECORD"
                elif st["reverted"] or st["no_transfer"]:
                    verdict = "UNVERIFIED_DEST"
                else:
                    verdict = "PENDING"
                results.append({"row": i, "recipient": recipient, "amount": amount,
                                "verdict": verdict, "note": "; ".join(details) or
                                "bridge completed; destination unmatched"})
        else:
            member_rows = [i for i, _ in members]
            results.append({"row": member_rows, "recipient": recipient, "amount": amount,
                            "verdict": "GROUP_FINDING", "observed": observed,
                            "rows_in_group": n, "records_matched": slots,
                            "unrecorded": unrecorded,
                            "pending": st["pending"], "unavailable": st["unavailable"],
                            "invalid_dest": st["invalid_dest"],
                            "invalid_record": st["invalid_record"],
                            "reverted": st["reverted"],
                            "no_transfer": st["no_transfer"],
                            "note": (f"{n} indistinguishable rows; records matched "
                                     f"{slots}; OBSERVED_MATCH {observed}; pending "
                                     f"{st['pending']}; unavailable {st['unavailable']}; "
                                     f"invalid_dest {st['invalid_dest']}; invalid_record "
                                     f"{st['invalid_record']}; reverted {st['reverted']}; "
                                     f"no_matching_transfer {st['no_transfer']}; "
                                     f"unrecorded {unrecorded}; WHICH row is paid is not "
                                     f"determinable — grouped, never picked arbitrarily. "
                                     + " | ".join(details))})
    # unmatched records / transfers = evidence, not overpayments
    for r in usable_records:
        if (r["tx_hash"], str(r["amount"]), r["transfer_tx_hash"]) not in rec_used:
            if r.get("invalid_accounting"):
                results.append({"row": None, "recipient": None, "amount": r["amount"],
                                "verdict": "INVALID_RECORD",
                                "note": f"bridge record unusable: "
                                        f"{r['invalid_accounting']} — explicit "
                                        f"unsupported evidence, never green"})
            else:
                results.append({"row": None, "recipient": None, "amount": r["amount"],
                                "verdict": "UNMATCHED_BRIDGE_RECORD",
                                "note": f"bridge record {r['amount']} matches no burn in "
                                        f"this tx — unmatched evidence, not a confirmed "
                                        f"overpayment"})
    for (chain, tx, amt), d in dest.items():
        for t in (d.get("transfers", []) if isinstance(d, dict) else []):
            if (chain, tx, t["log_index"]) not in consumed:
                results.append({"row": None, "recipient": t["to"], "amount": t["amount"],
                                "verdict": "UNMATCHED_DEST_TRANSFER",
                                "note": f"transfer {t['amount']} at {tx}:{t['log_index']} "
                                        f"consumed by nothing — unmatched evidence, "
                                        f"not automatically an overpayment"})
    return results


def summarize(rows, diag, completeness, source_status, results, list_state,
              bridge_malformed=False):
    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    base = {"counts": counts, "completeness": completeness, "source_status": source_status,
            "burn_diag": diag, "list_check": list_state,
            "bridge_malformed": bool(bridge_malformed or diag.get("malformed_events"))}
    groups = [r for r in results if r.get("verdict") == "GROUP_FINDING"]
    g = lambda k: sum(x.get(k, 0) for x in groups)
    g_rows = sum(x.get("rows_in_group", 0) for x in groups)
    g_observed = sum(x.get("observed", 0) for x in groups)
    singles = [r for r in results if isinstance(r.get("row"), int)]
    singles_observed = sum(1 for r in singles if r.get("verdict") == "OBSERVED_MATCH")
    burns_total = sum(1 for r in rows
                      if not r.get("unsupported") and not r.get("malformed_event"))
    obs_total = g_observed + singles_observed
    # unresolved / negative guards
    unresolved = (g("pending") + g("unavailable") + g("invalid_dest") +
                  g("invalid_record") + g("reverted") + g("no_transfer") +
                  g("unrecorded") + counts.get("PENDING", 0) +
                  counts.get("INCONCLUSIVE", 0) + counts.get("NOT_RECORDED", 0) +
                  counts.get("UNVERIFIED_DEST", 0) + counts.get("INVALID_RECORD", 0) +
                  counts.get("INVALID_EVENT_ROW", 0))
    extras = bool(counts.get("UNMATCHED_DEST_TRANSFER") or
                  counts.get("UNMATCHED_BRIDGE_RECORD"))
    groups_full = all(x.get("observed", 0) == x.get("rows_in_group", 0)
                      for x in groups)
    singles_ok = all(r.get("verdict") == "OBSERVED_MATCH" for r in singles)
    full = (groups_full and singles_ok and g_rows + len(singles) == burns_total
            and obs_total == burns_total)
    if source_status == "Failure":
        return dict(base, overall="SOURCE_FAILED — transaction execution failed")
    if diag.get("malformed"):
        return dict(base, overall="UNSUPPORTED_SOURCE — response shape not recognized")
    if diag.get("malformed_entries"):
        # [v5] null/non-object entries inside the source outcome collections:
        # the evidence set is provably incomplete, so success is impossible.
        return dict(base, overall=("UNSUPPORTED_SOURCE — malformed source entries "
                                   f"({diag['malformed_entries']} null/non-object "
                                   "outcome/receipt entries)"))
    if completeness and completeness.get("complete") is False:
        return dict(base, overall="INCOMPLETE_EVIDENCE — reachable graph unresolved "
                                  "(never complete success)")
    if counts.get("INCONCLUSIVE") or g("unavailable") or g("invalid_dest"):
        return dict(base, overall="INCONCLUSIVE — required leg unavailable or "
                                  "destination response malformed")
    if (counts.get("INVALID_RECORD") or counts.get("INVALID_EVENT_ROW")
            or g("invalid_record")):
        return dict(base, overall="INVALID_EVIDENCE — monetary/accounting/record fields "
                                  "malformed (fractional, non-integer, non-object or "
                                  "gross != fee + net)")
    if diag.get("attempts_no_burn") and not rows:
        return dict(base, overall="NO_BURN_OBSERVED — attempted ft_withdraw present but "
                                  "no successful burn (not a verified withdrawal)")
    if not rows:
        return dict(base, overall="NO_ROWS — no supported-scope burns in this tx")
    if counts.get("PENDING") or g("pending"):
        return dict(base, overall="IN_PROGRESS — bridge/destination pending")
    if (counts.get("NOT_RECORDED") or counts.get("UNVERIFIED_DEST") or
            g("unrecorded") or g("reverted") or g("no_transfer")):
        return dict(base, overall="MISMATCH — some intended payments lack observed "
                                  "delivery (deficit, revert or unmatched transfer)")
    if extras and full:
        return dict(base, overall="MATCH_WITH_UNMATCHED_EVIDENCE — all burns observed "
                                  "plus unmatched extras (surface, do not net away)")
    if counts.get("UNSUPPORTED_SCOPE") or counts.get("UNSUPPORTED_BRIDGE"):
        if full and obs_total:
            return dict(base, overall="MIXED_SCOPE — supported burns observed, others "
                                      "outside supported scope")
        return dict(base, overall="UNSUPPORTED_SCOPE — rows/records outside the supported "
                                  "source-token→Base-USDC scope")
    if full and not extras and set(counts) <= {"OBSERVED_MATCH", "GROUP_FINDING"}:
        return dict(base, overall="ALL_ROWS_OBSERVED (receipt-level; not final settlement)"
                                  if obs_total == burns_total and burns_total > 0
                                  else "SEE_ROWS")
    return dict(base, overall="SEE_ROWS")


# ---------------------------------------------------------------- case runner
def inconclusive(case, outdir, meta, reason, completeness=None, list_state=None):
    name = case.get("name", "case")
    report = {"case": name, "synthetic": case.get("synthetic", False),
              "near_tx": case.get("near_tx"), "meta": meta,
              "summary": {"overall": f"INCONCLUSIVE — {reason}",
                          "counts": {"INCONCLUSIVE": 1}, "completeness": completeness,
                          "list_check": list_state},
              "results": [], "disclaimer": DISCLAIMER,
              "generated_at": _now()}
    _emit(outdir, name, report, f"== {name} ==\nOVERALL: INCONCLUSIVE — {reason}")
    return report


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _emit(outdir, name, report, text):
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{name}.json").write_text(json.dumps(report, indent=1, default=str))
    (outdir / f"{name}.txt").write_text(text + "\n")
    print(text)


def run_case(case, outdir):
    name = case.get("name", "case")
    synthetic = case.get("synthetic", False)
    kind = case.get("kind", "fixture")
    list_state = "not requested"
    obligations = None
    bridge_malformed = False        # [v4] set when returned bridge evidence is malformed

    if kind in ("live", "offline"):
        if kind == "live":
            try:
                near = fetch_near(case["near_tx"], case["signer"])
            except Exception as e:
                return inconclusive(case, outdir, {"source": "live"},
                                    f"NEAR leg unavailable: {type(e).__name__}: {e}")
            source = near.get("_source", "drpc")
        else:  # offline: raw saved evidence, no network
            near = case["legs"]["near_raw"]
            source = case["legs"].get("near_source", "drpc")
            if source == "fastnear" and "transaction" in near:
                near = _normalize_fastnear_tx(near) if "receipts" not in near else near
                near["_source"] = "fastnear"
        if source == "drpc":
            source_status = normalize_status(near.get("status"))
        else:
            # [v5] execution_outcome may be absent/null/non-object in malformed
            # evidence; never dereference before type-checking the whole chain.
            eo = near.get("execution_outcome")
            eo_out = eo.get("outcome") if isinstance(eo, dict) else None
            source_status = normalize_status(eo_out.get("status")) \
                if isinstance(eo_out, dict) else "Unknown"
        if source == "drpc" and not isinstance(near.get("status"), (dict, str)):
            source_status = "Unknown"
        finality = near.get("final_execution_status", "not_reported")
        rows, diag = extract_burns(near, source)
        completeness = analyze_completeness(near, source)

        if kind == "live" and case.get("list_id"):
            try:
                lv = fetch_view_list(case.get("list_account", "bulkpayment.near"),
                                     case["list_id"])
                obligations, list_state = lv["obligations"], "available"
            except Exception as e:
                list_state = f"UNAVAILABLE ({type(e).__name__}: {e})"
            if kind == "live" and case.get("list_id") and list_state != "available":
                pass

        if kind == "offline":
            nbridged = normalize_bridge(case["legs"]["bridge_raw"])   # [v4] tuple return
            if nbridged is None:
                return inconclusive(case, outdir, {"source": source},
                                    "bridge raw response malformed", completeness, list_state)
            records, bridge_malformed = nbridged
            dest = {}
            tip = case["legs"].get("dest_tip")
            for rec in records:
                if rec.get("scope_problems") or rec["chain"] != SUPPORTED["dest_chain"] \
                        or not rec["transfer_tx_hash"] or rec["status"] != "COMPLETED":
                    continue
                key, entry = build_dest_from_receipt(case["legs"].get("dest_receipt"),
                                                     rec, tip)
                dest[key] = entry
        else:
            try:
                nbridged = fetch_bridge(case["near_tx"])              # [v4] tuple return
                if nbridged is None:
                    return inconclusive(case, outdir, {"source": source},
                                        "bridge response malformed", completeness, list_state)
                records, bridge_malformed = nbridged
            except Exception as e:
                return inconclusive(case, outdir, {"source": source},
                                    f"bridge leg unavailable: {type(e).__name__}: {e}",
                                    completeness, list_state)
            dest = fetch_dest(records)
    else:  # fixture with endpoint-shaped raw legs
        near = case["legs"].get("near_raw", {})
        source = case["legs"].get("near_source", "drpc")
        if source == "fastnear" and "receipts" in near and "_source" not in near:
            near = dict(near, _source="fastnear")
        # [v5] type-check the whole chain before dereferencing (malformed root
        # evidence must reach a structured report, not raise here)
        if source == "drpc":
            source_status = normalize_status(near.get("status"))
        else:
            eo = near.get("execution_outcome")
            eo_out = eo.get("outcome") if isinstance(eo, dict) else None
            source_status = normalize_status(eo_out.get("status")) \
                if isinstance(eo_out, dict) else "Unknown"
        source_status = case["legs"].get("source_status") or source_status
        finality = case["legs"].get("finality", "fixture")
        rows, diag = extract_burns(near, source)
        completeness = analyze_completeness(near, source)
        if case["legs"].get("bridge_unavailable"):
            return inconclusive(case, outdir, {"source": source},
                                f"bridge leg unavailable: {case['legs']['bridge_unavailable']}",
                                completeness, list_state)
        nbridged = normalize_bridge(case["legs"].get("bridge_raw", {"withdrawals": []}))
        if nbridged is None:
            return inconclusive(case, outdir, {"source": source}, "bridge response malformed",
                                completeness, list_state)
        records, bridge_malformed = nbridged
        dest = {}
        tip = case["legs"].get("dest_tip")
        for rec in records:
            if rec.get("scope_problems"):
                continue
            entry_spec = case["legs"].get("dest_receipts", {})
            receipt = entry_spec.get(rec["transfer_tx_hash"])
            key, entry = build_dest_from_receipt(receipt, rec, tip)
            if case["legs"].get("dest_unavailable"):
                entry = {"error": f"destination RPC unavailable: {case['legs']['dest_unavailable']}"}
            dest[key] = entry
        if case["legs"].get("list_unavailable"):
            list_state = f"UNAVAILABLE ({case['legs']['list_unavailable']})"
        elif "view_list" in case["legs"]:
            obligations = case["legs"]["view_list"]["obligations"]
            list_state = "available (fixture)"

    advisory = list_advisory(obligations, rows) if obligations is not None else []
    fee_hint = None
    for r in (records or []):
        if r.get("fee"):
            fee_hint = r["fee"]
            break
    results = reconcile(rows, records or [], dest, fee_hint=fee_hint)
    summary = summarize(rows, diag, completeness, source_status, results, list_state,
                        bridge_malformed=bridge_malformed)
    report = {"case": name, "synthetic": synthetic, "kind": kind,
              "near_tx": case.get("near_tx"), "source": source,
              "source_status": source_status, "final_execution_status": finality,
              "rows_found": len(rows), "bridge_records": len(records or []),
              "obligations_found": (len(obligations) if obligations is not None else None),
              "list_advisory": advisory,
              "list_binding": ("aggregate advisory only; lists may span transactions; "
                               "no per-row tx linkage" if obligations is not None else None),
              "summary": summary, "results": results, "disclaimer": DISCLAIMER,
              "generated_at": _now()}
    lines = [f"== {name} {'(SYNTHETIC FIXTURE)' if synthetic else f'({kind})'} ==",
             f"source_status: {source_status}  finality: {finality}  source: {source}",
             f"completeness: {completeness['complete']} ({completeness['reason']})",
             f"burn_diag: {diag}",
             f"rows(supported-scope burns)={sum(1 for r in rows if not r.get('unsupported'))} "
             f"bridge_records={len(records or [])}"
             + (f" obligations={len(obligations)}" if obligations is not None else ""),
             f"list_check: {list_state}"]
    for a in advisory:
        lines.append(f"  LIST_ADVISORY: {a}")
    lines.append(f"OVERALL: {summary['overall']}  counts={summary['counts']}")
    for r in results:
        who = r.get("recipient") or "-"
        rows_lbl = r.get("row")
        lines.append(f"  row {str(rows_lbl):>6} {str(r.get('amount')):>9} -> {who} : "
                     f"{r['verdict']} — {r.get('note', '')}")
    lines.append(f"NOTE: {DISCLAIMER}")
    _emit(outdir, name, report, "\n".join(lines))
    return report


def main():
    args = sys.argv[1:]
    outdir = Path(args[args.index("--outdir") + 1]) if "--outdir" in args else Path("results")
    cases = []
    if "--fixtures" in args:
        for f in sorted(Path("fixtures").glob("*.json")):
            cases.append(json.loads(f.read_text()))
    elif "--case" in args:
        cases.append(json.loads(Path(args[args.index("--case") + 1]).read_text()))
    elif "--offline" in args:
        nm = args[args.index("--offline") + 1]
        cases.append(json.loads(Path(f"fixtures/offline_{nm}.json").read_text()))
    elif "--live" in args:
        tx = args[args.index("--live") + 1]
        if "--signer" not in args:
            print("live needs --signer")
            return 1
        c = {"name": f"live_{tx[:12]}", "kind": "live", "near_tx": tx,
             "signer": args[args.index("--signer") + 1]}
        if "--list" in args:
            c["list_id"] = args[args.index("--list") + 1]
            c["list_account"] = args[args.index("--list-account")] \
                if "--list-account" in args else "bulkpayment.near"
        cases.append(c)
    else:
        print(__doc__)
        return 1
    ok = True
    for c in cases:
        try:
            run_case(c, outdir)
        except Exception as e:
            ok = False
            print(f"CASE {c.get('name')} FAILED: {type(e).__name__}: {e}")
    if RAW_LOG:
        Path("raw").mkdir(exist_ok=True)
        p = Path("raw") / f"probe_network_log_full_{int(time.time())}.jsonl"
        with p.open("a") as fh:
            for ts, url, req, resp, is_err in RAW_LOG:
                fh.write(json.dumps({"ts": ts, "url": url, "request": req,
                                     "response": resp, "error": is_err}) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
