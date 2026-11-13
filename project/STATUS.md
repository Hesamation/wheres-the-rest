# Status

Updated 2026-11-13. Application implemented; follow-up found demo-blocking count/evidence concerns. See notes/BEFORE-DEMO.md for repro, focused review prompt, manual checks and design direction. Correctness fixes should precede recording/polish. Earlier browser/live checks below are Gemini-reported; this follow-up could not access a browser. Codex reran offline checks successfully and API checks passed with localhost permissions. No fresh live run. Timeout currently loses partial evidence; QA1 headline counters omit group outcomes; per-row evidence association needs a reproducer/review.

- Works:
  - Preserved reader imported with SHA-256 `0ac8f7364292f5e9268bbcc465f433f9ac2ff48c7aeb9d2facfc0f24ce99f4a2`.
  - Offline fixtures: QA1 (group deficit), QA2 (mixed delivery), and production control FD7g (1.00 USDC observed via FastNEAR fallback) with sealed capture provenance.
  - Thin adapter, process-isolated workers, concurrency busy lock, and 120s live deadline.
  - Exact 6-decimal USDC money conversion and string integer serialization (`schemaVersion: "1"`).
  - Web UI (HTTP server on 127.0.0.1:8765) with saved examples, live reconciliation, group ambiguity callout, inspect drawers, and client-side JSON download.
  - Full CLI (`main.py --serve`, `--saved`, `--live`, `--check`).
- Checks run:
  - Reader suite (177 PASS), verifier (30 PASS), invariants (142 PASS), 10 regressions (10 PASS), disposable 13-case harness (13/13 PASS).
  - Adapter parity tests across all 27 fixtures and saved examples (0 mismatches).
  - Validation, formatting, server API, and CLI test suites (all PASS).
  - Live RPC queries tested for FD7g (ALL_ROWS_OBSERVED via FastNEAR fallback), QA1 (MISMATCH), QA2 (MISMATCH).
  - Browser verification subagent confirmed UI load, card interactions, inspection drawers, JSON download, and form validation.
- Next steps:
  - Record 90-120s walkthrough video following the script in README.md.
  - Confirm GitHub account/organization to create private remote with `gh repo create` and push.
  - Final product name, license, and public submission authorization remain with the human.
