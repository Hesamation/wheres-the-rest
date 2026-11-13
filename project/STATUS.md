# Status

Updated 2026-11-13. Two demo-blocking evidence bugs found and fixed; all checks pass.

- Works:
  - Preserved reader imported with SHA-256 `0ac8f7364292f5e9268bbcc465f433f9ac2ff48c7aeb9d2facfc0f24ce99f4a2`.
  - Offline fixtures: QA1 (group deficit), QA2 (mixed delivery), and production control FD7g (1.00 USDC observed via FastNEAR fallback) with sealed capture provenance.
  - Thin adapter, process-isolated workers, concurrency busy lock, and 120s live deadline.
  - Exact 6-decimal USDC money conversion and string integer serialization (`schemaVersion: "1"`).
  - Restrained reconciliation workbench (Carbon Design System hierarchy, Dark Gray 90/100 theme, zero external dependencies).
  - Preloaded QA1 view on first load: immediate 5-second legibility for outcome, exact USDC amounts, and group ambiguity.
  - Accurate KPI metric tiles for both single rows and group findings (1 observed, 2 unrecorded deficit).
  - Carbon data-table with inline expandable rows disclosing multi-leg audit trails (NEAR ft_burn -> Chaindefuser bridge -> Base USDC receipt) and keyboard accessibility (Enter/Space toggling).
  - Stale results warning banner and dimmed table upon editing inputs.
  - Full CLI (`main.py --serve`, `--saved`, `--live`, `--check`).
- Fixes committed (2026-11-13):
  - **Wrong evidence on equal-amount rows**: OBSERVED_MATCH bridge record was looked up by gross amount only; when two rows shared the same amount both received the same bridge record. Fixed: use dest tx hash extracted from the reader note (authoritative), fall back to amount only when no note tx is present. Reproducer: `fx_r_equal_two_recipients`.
  - **Missing evidence on group findings**: GROUP_FINDING rows never received `bridgeRecord` or `destTransfer` evidence even when `groupDetails.observed >= 1`. Fixed: same note-based lookup applied to group findings. QA1 drawer now shows bridge leg and destination leg. Reproducer: `offline_qa1`.
  - **Misleading zero observed count in UI for group findings**: Header metrics previously read `0 OBSERVED ON BASE` on QA1. Fixed: KPI tiles aggregate both single rows and group details dynamically.
- Checks run:
  - Reader suite (177 PASS), verifier (30 PASS), invariants (142 PASS), 10 regressions (10 PASS), disposable 13-case harness (13/13 PASS).
  - Adapter parity tests across all 27 fixtures and saved examples (0 mismatches).
  - Validation, formatting, server API, and CLI test suites (all PASS).
  - Interactive headless browser verification for desktop (1280px) and mobile (375px): auto-preload, expandable row keyboard toggling (Enter/Space), stale banner detection on input change, form validation errors, and JSON export.
- Next steps:
  - Review proposed QA1 workbench screen with human.
  - Record 90-120s walkthrough video following the script in README.md.
  - Confirm GitHub account/organization to create private remote with `gh repo create` and push.
  - Final product name, license, and public submission authorization remain with the human.
