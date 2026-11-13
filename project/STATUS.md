# Status

Updated 2026-11-13. Ready-to-submit repository initialized on GitHub; high-leverage operator features and CI added; all 372 checks pass.

- Works:
  - Private GitHub remote established at `https://github.com/Hesamation/payout-reader` with MIT license and GitHub Actions CI workflow.
  - Multi-format audit exports: SchemaVersion "1" JSON export, RFC 4180 CSV export (`--csv` CLI and "Download CSV" UI button), and one-click "Copy Proof" formatted Markdown for Trezu and DAO forums.
  - URL Deep-Linking support (`?example=qa1`, `?example=prod_control`, `?example=qa2`) syncing state in real-time.
  - Minimal Dockerfile containerizing the zero-dependency Python 3.13 stdlib service.
  - Preserved reader imported with SHA-256 `0ac8f7364292f5e9268bbcc465f433f9ac2ff48c7aeb9d2facfc0f24ce99f4a2`.
  - Offline fixtures: QA1 (group deficit), QA2 (mixed delivery), and production control FD7g (1.00 USDC observed via FastNEAR fallback) with sealed capture provenance.
  - Thin adapter, process-isolated workers, concurrency busy lock, and 120s live deadline.
  - Exact 6-decimal USDC money conversion and string integer serialization (`schemaVersion: "1"`).
  - Restrained reconciliation workbench (Carbon Design System hierarchy, Dark Gray 90/100 theme, zero external dependencies).
  - Preloaded QA1 view on first load: immediate 5-second legibility for outcome, exact USDC amounts, and group ambiguity.
  - Accurate KPI metric tiles for both single rows and group findings (1 observed, 2 unrecorded deficit).
  - Carbon data-table with inline expandable rows disclosing multi-leg audit trails (NEAR ft_burn -> Chaindefuser bridge -> Base USDC receipt) and keyboard accessibility (Enter/Space toggling).
  - Stale results warning banner and dimmed table upon editing inputs.
  - Full CLI (`main.py --serve`, `--saved`, `--live`, `--csv`, `--json`, `--check`).
- Fixes committed:
  - Authoritative note-based bridge/dest evidence lookup on equal-amount rows and group findings.
  - Aggregated KPI tiles correctly accounting for group findings.
  - RFC 4180 CSV serialization and clipboard Markdown proof generators.
- Checks run:
  - Reader suite (177 PASS), verifier (30 PASS), invariants (142 PASS), 10 regressions (10 PASS), disposable 13-case harness (13/13 PASS).
  - Adapter parity tests across all 27 fixtures and saved examples (0 mismatches).
  - Validation, formatting, server API, and CLI test suites including CSV and proof tests (all PASS).
  - Interactive headless browser verification for desktop (1280px) and mobile (375px).
- Next steps:
  - Record 90-120s walkthrough video following the script in README.md.
  - Human publishes demo post on X tagging @NEARProtocol and #NEARHackathon with video attached.
  - Switch repository visibility to Public before deadline: `gh repo edit Hesamation/payout-reader --visibility public`.
  - Review and confirm final hackathon submission payload (tracks: `["realworld", "social"]`) for `POST https://nearhackathon.com/api/applications`.
