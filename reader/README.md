# payout_probe — setup and run instructions

Read-only reconciliation probe for NEAR bulk payouts that cross the PoA bridge.
**Python 3.13.16 (3.9+ syntax), standard library only. No keys, no funds, no installation.**

## Layout

```
payout_probe.py        the probe (live + fixture modes; completeness gate; view_list leg)
run_invariants.py      generated matrix + semantic invariant assertions (full pipeline)
run_tests.py           v3 assertion runner: parsers/normalizers/traversal/matcher units,
                       fixture expectations, OFFLINE raw-evidence e2e; --live adds 5 live cases
verify_outputs.py      INDEPENDENT verifier: re-derives facts from raw/ (no probe import)
fixtures/*.json        24 labeled SYNTHETIC fixtures + 3 offline raw-evidence cases
results/               v3 outputs (suite/, smoke/, live_v3/) (new timestamps; reconstruction after the
                       original out/ directory was lost to snapshot exclusion policy —
                       see PAYOUT-FEASIBILITY-ADDENDUM.md for the disclosure)
raw/                   raw request/response evidence with UTC timestamps (original trial,
                       untouched) + appended probe network logs from later runs
source-pins/           pinned competitor source at a168f7d8d41ac6791fbe04ee3cefaa600deef450
```

## Run

```bash
cd payout-feasibility

# 1) full suite: units + fixtures + offline raw e2e (no network) — 106 assertions
python3 run_tests.py
python3 verify_outputs.py   # independent re-derivation from raw/ (20 assertions)

# 2) fixture + five live-case assertions (network, labeled)
python3 run_tests.py --live

python3 run_invariants.py  # generated combination suite + semantic invariants (83)
python3 run_tests.py --live  # + five live-case assertions

# 3) individual live cases (read-only public RPCs)
python3 payout_probe.py --live 863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe --signer sponsor-staging.trezu.near
python3 payout_probe.py --live CbyrTsdExtWDbBsdUNqQC65JMBFwXEzkeaGJGmQb2QDz --signer sponsor-staging.trezu.near
python3 payout_probe.py --live EEDiWnLCkLGd8MizuqRut9K6GeBgLR9vU1WjdaQEJXCo --signer intents.near
python3 payout_probe.py --live FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu --signer sponsor.trezu.near
python3 payout_probe.py --live 2t5s6uZjxQgdTwgdkxuW69FGWmwx4EvWnBdAZrSTw4xf --signer sponsor.trezu.near

# 4) obligation binding (Trezu view_list, aggregate only)
python3 payout_probe.py --live 863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe \
  --signer sponsor-staging.trezu.near \
  --list f90c44fb4931e2bae2a6436dfa971260f76029a96bfb822a98d92ffabecfbe12 \
  --list-account bulkpayment.near --outdir results/live_with_list

# 5) plain probe run (prints and writes .txt/.json; default --outdir results)
python3 payout_probe.py --fixtures
```

## Endpoints used (all public, keyless)

| Leg | Endpoint | Notes |
|---|---|---|
| NEAR tx (primary) | `POST https://near.drpc.org` `EXPERIMENTAL_tx_status` | free plan throttles heavy calls (observed HTTP 408 "upgrade to paid plan") |
| NEAR tx (fallback) | `POST https://tx.main.fastnear.com/v0/transactions` `{"tx_hashes":[...]}` | normalized; finality reported as `not_reported_by_fastnear` |
| Trezu status | `POST https://rpc.mainnet.near.org` `query` `view_list` | read-only; aggregate obligation binding only |
| Bridge | `POST https://bridge.chaindefuser.com/rpc` `withdrawal_status` `params:[{withdrawal_hash}]` | array-of-object params; echoes record[0] in top-level `data` (deduped) |
| Destination | `POST https://mainnet.base.org` `eth_getTransactionReceipt`, `eth_blockNumber` | eth:8453 only; receipt success reported separately from finality |

## Known limitations (also in PAYOUT-FEASIBILITY-ADDENDUM.md)

- Receipt trees are checked for completeness every run (`analyze_completeness`); a
  truncated/unproven tree forces `INCOMPLETE_EVIDENCE` and can never yield ALL_DELIVERED.
  Receipt expansion via FastNEAR `/v0/receipt` is NOT yet implemented — remaining work.
- Destination chains other than eth:8453 report `UNSUPPORTED_DEST`.
- Identical rows are never paired individually: pairing ambiguity and count deficits are reported.
- Absent observations are labeled ambiguous/pending, never "lost"; no root cause from absence.
- No third-party repository code is executed by this probe.
