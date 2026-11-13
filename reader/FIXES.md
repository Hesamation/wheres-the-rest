# FIXES.md — success-invariant repair (2026-11-11)

## What was broken (reproduced from RECONCILED-PACKAGE-REVIEW / check_reconciled.py)

1. **Bridge record treated as observed transfer** — group `unrecorded` used record
   count (`n - matched`); pending/unavailable/zero-matching states were lost in group
   details; `ALL_ROWS_OBSERVED` could be claimed with observed=0. Surplus records could
   drive `unrecorded` negative.
2. **Outcome wrapper treated as executed outcome** — `receipts_outcome` entries without
   an `outcome`/`status` (and FastNEAR `{}` execution_outcomes) counted as resolved;
   completeness could be true with no execution evidence.
3. **No monetary/identity validation** — `gross == fee + net` never checked (fee=999,
   net=7600, gross=10000 passed green); destination receipt `transactionHash` never
   compared to the requested tx; reverted (`0x0`) receipts not distinguished.
4. **Verifier output selection** — `verify_outputs.py` preferred archived
   `results/smoke` over fresh `results/suite`.

## Fixes (payout_probe.py)

- **Group state machine:** per-group counters `observed / records_matched / pending /
  unavailable / invalid_dest / invalid_record / reverted / no_transfer / unrecorded`
  (all `max(0, …)`, slot-capped at group size — one transfer satisfies one burn; surplus
  records stay unused and surface as `UNMATCHED_BRIDGE_RECORD`; surplus transfers as
  `UNMATCHED_DEST_TRANSFER`). Single-row verdicts classify into `INVALID_RECORD` and
  precise `INCONCLUSIVE`/`UNVERIFIED_DEST`/`PENDING`.
- **Summarize precedence:** `SOURCE_FAILED > UNSUPPORTED_SOURCE > INCOMPLETE >
  INCONCLUSIVE (unavail/malformed dest) > INVALID_EVIDENCE (accounting) > NO_BURN >
  NO_ROWS > IN_PROGRESS > MISMATCH (deficit/revert/no-transfer) >
  MATCH_WITH_UNMATCHED (full + extras) > scope > ALL_ROWS_OBSERVED` — green requires:
  completeness true, `observed == burns`, every group fully observed, counts ⊆
  {OBSERVED_MATCH, GROUP_FINDING}, zero unresolved states.
- **Completeness:** drpc and FastNEAR now require a *valid executed outcome*
  (outcome dict with interpretable status ∈ Success*/Failure); wrappers without status,
  unknown statuses and FastNEAR `{}` outcomes are unresolved; data receipts handled
  explicitly by receipt kind (`_fn_receipt_kind`); pending ⇒ incomplete. Failure remains
  distinct from missing evidence.
- **Money validation:** safe integer parsing; `gross > 0`, `fee/net >= 0`,
  `gross == fee + net`; violations → `invalid_accounting` → `INVALID_RECORD` /
  `INVALID_EVIDENCE` (never green, never crash).
- **Receipt identity:** `transactionHash` must equal the requested destination tx when
  present; `to` must be the expected USDC contract; status must be `0x1`/`0x0`
  (`0x0` ⇒ `reverted` evidence, not absence); malformed ⇒ `invalid:` → INCONCLUSIVE.
- **`_fn_executor`:** added direct `holder.Action.receiver_id` path (flat/nested
  FastNEAR holder shapes).

## Their six counterexamples — reproduced, then fixed (adaptation: paths only)

| Case | Before | After |
|---|---|---|
| group_all_pending | ALL_ROWS_OBSERVED, observed=0 | **IN_PROGRESS** |
| group_destination_unavailable | ALL_ROWS_OBSERVED | **INCONCLUSIVE** |
| group_zero_matching_transfers | ALL_ROWS_OBSERVED | **MISMATCH** |
| inconsistent_fee_arithmetic | ALL_ROWS_OBSERVED | **INVALID_EVIDENCE** |
| reachable_outcome_wrapper_without_execution | complete=true, ALL_ROWS_OBSERVED | **INCOMPLETE_EVIDENCE** |
| receipt_transaction_hash_mismatch | ALL_ROWS_OBSERVED | **INCONCLUSIVE** |

No review case was found invalid; three issues hit while building the generated suite
were *my harness* bugs (transfer counting on raw receipts, partial-class rule for r<n,
a fee-invalid fixture that accidentally satisfied the equation) — fixed in the harness,
not by weakening assertions.

## Generated combination suite (`run_invariants.py`)

83 cases through the full pipeline: group size {1,2,3} × record count {0,1,equal,excess}
× destination {full, partial, pending, unavailable, reverted, zero-matching} (66) +
mixed recipients (4) + fee valid/invalid + receipt identity mismatch + drpc wrapper/pending
+ FastNEAR full/missing/empty + shared-destination-tx two distinct logs + repeated
destination observation + duplicate record + reordered/reversed+duplicated records.
**Semantic invariants asserted on observed cardinality/state** (not a summary clone):
green ⇒ complete ∧ observed==burns ∧ no unresolved ∧ no foreign verdicts; observed ∈
[0, burns]; group counts non-negative and ≤ rows; observed ≤ records_matched ≤ rows;
observed ≤ distinct destination transfers provided; unresolved/incomplete/invalid never
green; expected class derived from inputs, independent of the summary code. Legitimate
full observations (drpc and FastNEAR) pass green.

## Clean-output runs (final, this batch — `rm -rf results` first)

```
python3 run_tests.py        -> exit 0, 106/106 PASS
python3 verify_outputs.py   -> exit 0,  26/26  PASS  (suite-first selection + independent
                               cardinality/identity checks; no probe import)
python3 run_invariants.py   -> exit 0,  83/83  PASS
python3 /tmp/repro_six.py   -> exit 0,    6/6  PASS  (their six, adapted paths only)
total automated runtime ≈ 1 s; one fresh live read-only qa1 run -> MISMATCH,
GROUP_FINDING observed 1 / unrecorded 2 with full state breakdown (results/live_final/)
```

## Honest residuals (unchanged, not buried)

- No `/v0/receipt` graph expansion: unresolved graphs return INCOMPLETE (policy).
- No finality *threshold*: green means receipt-level observed match, labelled as such.
- Trezu list comparison remains advisory-only.
- Same-session independence disclosure stands; verifier is code-path independent, not a
  second researcher.
- Runtime baseline comparison, demand breadth, track selection, human capacity:
  unresolved. No prize odds. No pivot. **Automated elapsed time (≈1 s suites; ~46 min
  agent wall-clock for this repair batch, 0 min human) is not a delivery commitment.**
