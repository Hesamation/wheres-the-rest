#!/usr/bin/env python3
"""verify_outputs.py — INDEPENDENT check of actual outputs.

Deliberately does NOT import payout_probe. Re-derives key facts from the saved raw
evidence with simple independent logic (regex/JSON walks) and compares them against the
structured results produced by the probe. Same-session limitation disclosed in
CORRECTNESS.md: this is code-path independence, not researcher independence.

  python3 verify_outputs.py
Exit 0 = independent facts agree with probe outputs.
"""
import json, re, sys
from pathlib import Path

RAW, RES = Path("raw"), Path("results")
fails = []

def check(name, cond, detail):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}: {detail}")
    if not cond:
        fails.append(name)

def burns_from_obj(obj):
    """Independent walk of a parsed JSON structure: count nep141 ft_burn events
    carrying WITHDRAW_TO memos (does not use the probe's parser)."""
    n = 0
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if cur.get("standard") == "nep141" and cur.get("event") == "ft_burn":
                for d in cur.get("data", []):
                    if str(d.get("memo", "")).startswith("WITHDRAW_TO:"):
                        n += 1
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
        elif isinstance(cur, str) and cur.startswith("EVENT_JSON:"):
            try:
                stack.append(json.loads(cur[len("EVENT_JSON:"):]))
            except Exception:
                pass
    return n

def burns_from_raw_file(name):
    return burns_from_obj(json.loads((RAW / name).read_text()))

def load(name):
    return json.loads((RAW / name).read_text())

def result(name):
    # FRESH suite outputs take precedence over any archived/stale outputs
    # (packaged smoke files previously shadowed fresh results — fixed per brief).
    for d in ("suite", "offline_v3", "smoke"):
        p = RES / d / f"{name}.json"
        if p.exists():
            return json.loads(p.read_text())
    raise SystemExit(f"no result for {name}; run `python3 run_tests.py` first")

print("== INDEPENDENT: offline_qa1 (raw near/bridge/base vs probe output) ==")
check("qa1.burns_independent", burns_from_raw_file("near_qa1_full.json") == 3,
      f"independent ft_burn+WITHDRAW_TO count = "
      f"{burns_from_raw_file('near_qa1_full.json')} (expect 3)")
b = load("bridge_qa1.json")["result"]
check("qa1.bridge_records", len(b["withdrawals"]) == 1,
      f"independent bridge withdrawals = {len(b['withdrawals'])} (expect 1)")
check("qa1.bridge_gross", int(b["withdrawals"][0]["data"]["amount"]) == 10000,
      f"bridge record gross = {int(b['withdrawals'][0]['data']['amount'])}")
rec = load("base_receipt.txt".replace(".txt", ".txt")) if False else None
# base receipt lives in base_receipt.txt (json after header)
txt = (RAW / "base_receipt.txt").read_text()
i = txt.find('{"jsonrpc"')
base = json.loads(txt[i:])
transfers = [int(lg["data"], 16) for lg in base["result"]["logs"]
             if lg["topics"][0].startswith("0xddf252ad")]
check("qa1.base_transfer", transfers == [7600],
      f"independent Base USDC transfers = {transfers} (expect [7600])")
r = result("offline_qa1")
check("qa1.probe_rows", r["rows_found"] == 3, f"probe rows_found = {r['rows_found']}")
g = [x for x in r["results"] if x.get("verdict") == "GROUP_FINDING"]
check("qa1.group", bool(g) and g[0]["observed"] == 1 and g[0]["unrecorded"] == 2,
      f"probe group observed/unrecorded = {g[0]['observed'] if g else None}/"
      f"{g[0]['unrecorded'] if g else None} (expect 1/2 — matches independent counts)")
check("qa1.mismatch", r["summary"]["overall"].startswith("MISMATCH"),
      f"probe overall = {r['summary']['overall']!r}")

print("== INDEPENDENT: offline_qa2 ==")
check("qa2.burns_independent", burns_from_raw_file("near_qa2_full.json") == 2,
      f"independent burn count = {burns_from_raw_file('near_qa2_full.json')} (expect 2)")
b2 = load("bridge_qa2.json")["result"]
check("qa2.bridge_records", len(b2["withdrawals"]) == 1, "bridge records = 1")
check("qa2.bridge_gross", int(b2["withdrawals"][0]["data"]["amount"]) == 190000,
      f"bridge record gross = {int(b2['withdrawals'][0]['data']['amount'])} "
      f"(the OTHER burn, 200000, has no record)")
base2 = load("base_qa2_receipt.json")["result"]
t2 = [int(lg["data"], 16) for lg in base2["logs"] if lg["topics"][0].startswith("0xddf252ad")]
check("qa2.base_transfer", t2 == [187600], f"Base transfers = {t2} (expect [187600])")
r2 = result("offline_qa2")
check("qa2.probe_rows", r2["rows_found"] == 2, f"probe rows = {r2['rows_found']}")
check("qa2.counts", r2["summary"]["counts"].get("OBSERVED_MATCH") == 1 and
      r2["summary"]["counts"].get("NOT_RECORDED") == 1,
      f"probe counts = {r2['summary']['counts']} (expect 1 observed / 1 not recorded)")

print("== INDEPENDENT: offline_control (fastnear raw) ==")
probe_txs = load("fastnear_txs_probe.json")["transactions"]
ctrl = [t for t in probe_txs if t["transaction"]["hash"].startswith("EEDiWnLC")][0]
check("control.burns_independent", burns_from_obj(ctrl) == 1,
      f"independent burn count = {burns_from_obj(ctrl)} (expect 1)")
bc = load("bridge_control.json")["result"]
check("control.bridge_gross", int(bc["withdrawals"][0]["data"]["amount"]) == 24950000,
      f"bridge gross = {int(bc['withdrawals'][0]['data']['amount'])}")
basec = load("base_control_receipt.json")["result"]
tc = [int(lg["data"], 16) for lg in basec["logs"] if lg["topics"][0].startswith("0xddf252ad")]
check("control.base_transfer", tc == [24947600],
      f"Base transfer = {tc} (expect [24947600] = 24950000 - 2400)")
rc = result("offline_control")
check("control.probe_all_observed",
      rc["summary"]["overall"].startswith("ALL_ROWS_OBSERVED") and rc["rows_found"] == 1,
      f"probe overall = {rc['summary']['overall']!r}, rows = {rc['rows_found']}")

print("== INDEPENDENT: fee arithmetic across all three ==")
for nm, gross, fee, net in [("qa1", 10000, 2400, 7600), ("qa2", 190000, 2400, 187600),
                            ("control", 24950000, 2400, 24947600)]:
    check(f"{nm}.fee_math", gross - fee == net, f"{gross} - {fee} == {net}")

# ---- independent matching-fact inspection (not hardcoded counts) ----
print("== INDEPENDENT: cardinality of observed vs uncovered (offline cases) ==")
from collections import Counter

def burns_list(obj):
    out, stack = [], [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if cur.get("standard") == "nep141" and cur.get("event") == "ft_burn":
                for d in cur.get("data", []):
                    memo = str(d.get("memo", ""))
                    if memo.startswith("WITHDRAW_TO:"):
                        out.append((memo.split(":", 1)[1].lower(), int(d["amount"])))
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
        elif isinstance(cur, str) and cur.startswith("EVENT_JSON:"):
            try:
                stack.append(json.loads(cur[len("EVENT_JSON:"):]))
            except Exception:
                pass
    return out

def receipt_transfers(receipt):
    """[v4] UNIQUE (tx, log_index) identities of destination USDC transfers —
    not a set of (recipient, amount) pairs. A repeated copy of one log yields one
    identity; multiplicity must come from distinct logs."""
    out = {}
    for lg in receipt.get("logs", []):
        if lg.get("topics") and lg["topics"][0].startswith("0xddf252ad") and \
                lg.get("address", "").lower() == USDC_TOK.lower():
            ident = (str(receipt.get("transactionHash") or "?").lower(),
                     str(lg.get("logIndex", "?")).lower())
            out[ident] = ("0x" + lg["topics"][2][-40:].lower(), int(lg["data"], 16))
    return out

# kept for reference/back-compat; independent_cardinality now consumes identities
def receipt_pairs(receipt):
    return set(receipt_transfers(receipt).values())

USDC_TOK = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"

def independent_cardinality(burns, withdrawals, receipt):
    """Recompute observed/uncovered WITHOUT the probe. Multiset of (recipient, gross)
    burns; a withdrawal settles one burn iff the destination receipt contains a
    NOT-YET-CONSUMED distinct log (tx, log_index) transferring (recipient, net) for
    a burn with that gross. One transfer identity can satisfy at most one burn:
    recipient+amount set membership alone never proves transfer multiplicity."""
    remaining = Counter(burns)
    transfers = receipt_transfers(receipt)
    used = set()
    observed = 0
    for w in withdrawals:
        d = w.get("data", {})
        gross, net = int(d["amount"]), int(d["withdraw_amount"])
        for k in list(remaining):
            if k[1] != gross:
                continue
            for ident, (to, amt) in transfers.items():
                if ident in used:
                    continue
                if to == k[0] and amt == net:
                    used.add(ident)
                    remaining[k] -= 1
                    if remaining[k] == 0:
                        del remaining[k]
                    observed += 1
                    break
            else:
                continue
            break
    return observed, sum(remaining.values())

def off_result(name):
    return json.loads((RES / "suite" / f"{name}.json").read_text())

for name, near_file, bridge_file, receipt_file in [
        ("offline_qa1", "near_qa1_full.json", "bridge_qa1.json", "base_receipt.txt"),
        ("offline_qa2", "near_qa2_full.json", "bridge_qa2.json", "base_qa2_receipt.json"),
        ("offline_control", None, "bridge_control.json", "base_control_receipt.json")]:
    if near_file:
        near = json.loads((RAW / near_file).read_text())["result"]
    else:
        near = [t for t in json.loads((RAW / "fastnear_txs_probe.json").read_text())["transactions"]
                if t["transaction"]["hash"].startswith("EEDiWnLC")][0]
    burns = burns_list(near)
    wds = json.loads((RAW / bridge_file).read_text())["result"]["withdrawals"]
    rtxt = (RAW / receipt_file).read_text()
    i = rtxt.find('{"jsonrpc"')
    receipt = json.loads(rtxt[i:] if i >= 0 else rtxt)
    if "result" in receipt:
        receipt = receipt["result"]
    i_obs, i_unc = independent_cardinality(burns, wds, receipt)
    rep = off_result(name)
    # identity check: receipt must be for the requested destination tx
    want_tx = wds[0]["data"].get("transfer_tx_hash")
    ident_ok = (not receipt.get("transactionHash")) or \
        receipt["transactionHash"].lower() == str(want_tx).lower()
    check(f"{name}.dest_identity", ident_ok,
          f"receipt transactionHash matches requested {str(want_tx)[:14]}…")
    # compare with probe's report state
    g = [x for x in rep["results"] if x.get("verdict") == "GROUP_FINDING"]
    if g:
        p_obs, p_unc = g[0]["observed"], g[0]["unrecorded"]
    else:
        p_obs = sum(1 for x in rep["results"] if x.get("verdict") == "OBSERVED_MATCH")
        p_unc = sum(1 for x in rep["results"] if x.get("verdict") == "NOT_RECORDED")
    check(f"{name}.cardinality", (p_obs, p_unc) == (i_obs, i_unc),
          f"independent observed/uncovered = {i_obs}/{i_unc}; probe report = {p_obs}/{p_unc}")

print("== INDEPENDENT: transfer-multiplicity oracle consumes unique identities [v4] ==")
# Two burns, one destination tx, one real log repeated as an exact copy: set
# membership of (recipient, amount) would allow 2 observations; only ONE distinct
# (tx, logIndex) identity exists, so a correct identity-consuming oracle observes 1.
R = "0x" + "c" * 40
B2 = [(R, 10000), (R, 10000)]
def wdup(transfer):
    return {"data": {"amount": 10000, "withdraw_amount": 7600,
                     "transfer_tx_hash": transfer}}
def dup_log_receipt():
    lg = {"address": USDC_TOK,
          "topics": ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                     "0x" + "0" * 24 + "2cff890f0378a11913b6129b2e97417a2c302680",
                     "0x" + "0" * 24 + R[2:]],
          "data": "0x" + hex(7600)[2:].zfill(64), "logIndex": "0x1"}
    return {"transactionHash": "0x" + "1" * 64, "logs": [lg, dict(lg)]}
o, u = independent_cardinality(B2, [wdup("0x" + "1" * 64)] * 2, dup_log_receipt())
check("oracle.repeated_log_identity", (o, u) == (1, 1),
      f"one log copied twice, two burns -> observed/uncovered = {o}/{u} (expect 1/1)")

# Same shape but with TWO DISTINCT logIndex values: both burns are settled.
def two_log_receipt():
    lg = {"address": USDC_TOK,
          "topics": ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                     "0x" + "0" * 24 + "2cff890f0378a11913b6129b2e97417a2c302680",
                     "0x" + "0" * 24 + R[2:]],
          "data": "0x" + hex(7600)[2:].zfill(64), "logIndex": "0x1"}
    lg2 = dict(lg, logIndex="0x2")
    return {"transactionHash": "0x" + "1" * 64, "logs": [lg, lg2]}
o, u = independent_cardinality(B2, [wdup("0x" + "1" * 64)] * 2, two_log_receipt())
check("oracle.distinct_log_identity", (o, u) == (2, 0),
      f"two distinct logs, two burns -> observed/uncovered = {o}/{u} (expect 2/0)")

# One burn, repeated identical withdrawal records: idempotent, one observation.
o, u = independent_cardinality([(R, 10000)], [wdup("0x" + "1" * 64)] * 2,
                               two_log_receipt())
check("oracle.duplicate_records_idempotent", (o, u) == (1, 0),
      f"duplicate records, one burn -> observed/uncovered = {o}/{u} (expect 1/0)")

# Mixed recipients, equal amounts: identity consumption must not cross-assign.
R2B = "0x" + "d" * 40
def mixed_receipt():
    lgA = {"address": USDC_TOK,
           "topics": ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                      "0x" + "0" * 24 + "2cff890f0378a11913b6129b2e97417a2c302680",
                      "0x" + "0" * 24 + R[2:]],
           "data": "0x" + hex(7600)[2:].zfill(64), "logIndex": "0x1"}
    lgB = dict(lgA, logIndex="0x2",
               topics=[lgA["topics"][0], lgA["topics"][1],
                       "0x" + "0" * 24 + R2B[2:]])
    return {"transactionHash": "0x" + "1" * 64, "logs": [lgA, lgB]}
o, u = independent_cardinality([(R, 10000), (R2B, 10000)],
                               [wdup("0x" + "1" * 64)] * 2, mixed_receipt())
check("oracle.mixed_recipients_identity", (o, u) == (2, 0),
      f"mixed recipients equal gross -> observed/uncovered = {o}/{u} (expect 2/0)")

print(f"\n{'INDEPENDENT CHECK PASSED' if not fails else 'FAILURES: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
