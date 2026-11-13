# Status

Updated 2026-11-13. Two demo-blocking evidence bugs found and fixed; all checks pass.

- Works:
  - Preserved reader imported with SHA-256 `0ac8f7364292f5e9268bbcc465f433f9ac2ff48c7aeb9d2facfc0f24ce99f4a2`.
  - Offline fixtures: QA1 (group deficit), QA2 (mixed delivery), and production control FD7g (1.00 USDC observed via FastNEAR fallback) with sealed capture provenance.
  - Thin adapter, process-isolated workers, concurrency busy lock, and 120s live deadline.
  - Exact 6-decimal USDC money conversion and string integer serialization (`schemaVersion: "1"`).
  - Web UI (HTTP server on 127.0.0.1:8765) with saved examples, live reconciliation, group ambiguity callout, inspect drawers, and client-side JSON download.
  - Full CLI (`main.py --serve`, `--saved`, `--live`, `--check`).
- Fixes committed (2026-11-13):
  - **Wrong evidence on equal-amount rows**: OBSERVED_MATCH bridge record was looked up by gross amount only; when two rows shared the same amount both received the same bridge record. Fixed: use dest tx hash extracted from the reader note (authoritative), fall back to amount only when no note tx is present. Reproducer: `fx_r_equal_two_recipients`.
  - **Missing evidence on group findings**: GROUP_FINDING rows never received `bridgeRecord` or `destTransfer` evidence even when `groupDetails.observed >= 1`. Fixed: same note-based lookup applied to group findings. QA1 drawer now shows bridge leg and destination leg. Reproducer: `offline_qa1`.
- Checks run:
  - Reader suite (177 PASS), verifier (30 PASS), invariants (142 PASS), 10 regressions (10 PASS), disposable 13-case harness (13/13 PASS).
  - Adapter parity tests across all 27 fixtures and saved examples (0 mismatches); now also assert per-row evidence identities (gross amounts, dest tx hashes, no duplicate bridge record assignment, group burn indices).
  - Validation, formatting, server API, and CLI test suites (all PASS).
  - Live RPC queries tested for FD7g (ALL_ROWS_OBSERVED via FastNEAR fallback), QA1 (MISMATCH), QA2 (MISMATCH). No fresh live run this session.
- Next steps:
  - Record 90-120s walkthrough video following the script in README.md.
  - Confirm GitHub account/organization to create private remote with `gh repo create` and push.
  - Final product name, license, and public submission authorization remain with the human.
