# Payout Reader — Cross-Chain Payout Reconciler for NEAR

<div align="center">

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Railway-0B0D0E?logo=railway)](https://payout-reader.up.railway.app)
[![CI](https://github.com/Hesamation/payout-reader/actions/workflows/ci.yml/badge.svg)](https://github.com/Hesamation/payout-reader/actions)
[![Tests: 372 Passed](https://img.shields.io/badge/Tests-372%20PASS%20(offline)-2ba84a)](#try-it-reproducible-do-x--see-y-verification)
[![Python: 3.13+ Stdlib](https://img.shields.io/badge/Python-3.13+%20(Stdlib%20Only)-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![NEAR Hackathon 2026](https://img.shields.io/badge/NEAR%20Hackathon%202026-realworld%20%7C%20social-orange)](https://nearhackathon.com)

**A successful NEAR payout transaction doesn't tell a treasury operator whether every cross-chain withdrawal reached its destination. Payout Reader brings source execution, bridge records, and destination transfer observations into one inspectable report.**

**[Live Hosted App](https://payout-reader.up.railway.app)** · **[CLI Quickstart](#try-it-reproducible-do-x--see-y-verification)** · **[3-Way Reconciliation Architecture](#how-it-works-3-way-reconciliation)** · **[Mainnet Proof](#proof-real-mainnet-evidence)** · **[Conservative Semantics & Limits](#conservative-evidence-semantics--known-limits)** · **[NEAR Disclosures](#when-and-how-it-was-built-near-hackathon-disclosures)**

Built for **NEAR HACKATHON 2026**, tracks [`realworld`](https://github.com/nearai/near-hackathon-prompt-examples/blob/main/tracks/08-realworld.md) (Real-World Money) and [`social`](https://github.com/nearai/near-hackathon-prompt-examples/blob/main/tracks/12-social.md) (Social Money / Trezu & Sputnik DAO).

</div>

---

## What It Is

**Payout Reader** is an automated cross-chain reconciliation workbench and CLI for Web3 treasuries, DAOs (Trezu, Sputnik DAO), and crypto payroll operators. 

For the supported NEAR-to-Base USDC payout route, operators enter a NEAR transaction hash and signer account to instantly audit the complete multi-leg settlement lifecycle:
1. **Source Execution on NEAR:** Validates `ft_burn` events on the bridged OMFT contract (`base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near`).
2. **Bridge Leg:** Queries the Chaindefuser PoA bridge RPC (`https://bridge.chaindefuser.com/rpc`) for matching withdrawal records, observed fees, and destination dispatch nonces.
3. **Destination Observation on Base:** Fetches BaseScan EVM receipts with block numbers and confirmation depths for Base USDC transfers (`0x833589fcd6edb6e08f4c7c32d4f71b54bda02913`).

The application is **read-only**: it moves no funds, requires no wallet connection, and depends on **Python 3.13+ standard library only** (zero pip dependencies, zero Node build steps, zero databases).

---

## The Problem It Solves

When a DAO or company uses NEAR multisigs (like Trezu) to pay international contractors, employees, or grant recipients on Base, the NEAR blockchain transaction always reports **`Success`** as long as the initial NEAR token burns succeeded.

However, cross-chain execution often fails silently downstream:
- **Dropped or Delayed Bridge Legs:** Bridge relayers can drop transactions or stall under network congestion. A "successful" NEAR transaction can leave recipients completely unpaid.
- **Undocumented Bridge Fees:** Relayers deduct dynamic bridge fees (e.g. 0.002400 USDC). Without automated matching, bookkeepers cannot verify whether a contractor received their exact net payment or was shortchanged.
- **Batch Ambiguity on Identical Payouts:** When a treasury executes batch payouts of identical amounts (e.g. three $10.00 bounties to the same vendor or different contractors), bridge relayers frequently aggregate them without preserving 1-to-1 ordering. Naive tools pick recipients arbitrarily, falsifying accounting ledgers.
- **No Exportable Accounting Proof:** Accountants cannot paste a raw NEAR explorer link into QuickBooks or a DAO governance proposal to prove vendor delivery.

### How Payout Reader Solves This
- **Deficit & Revert Detection:** Immediately distinguishes `ALL_ROWS_OBSERVED` from `MISMATCH` (deficit, dropped bridge record, or EVM revert).
- **Exact 6-Decimal Money Math:** Tracks atomic amounts with exact six-decimal precision (`1.000000 gross − 0.002400 fee = 0.997600 net USDC`), eliminating floating-point rounding errors.
- **Honest Group Attribution:** Identical burns with partial deliveries produce an explicit **`GROUP_FINDING`** preserving the ambiguity rather than guessing who was paid.
- **1-Click Accountant & Governance Exports:** Generates standard RFC 4180 CSVs for spreadsheets and pre-formatted Markdown audit proofs ready to paste directly into Trezu proposals and Sputnik DAO forum threads.

---

## How It Works: 3-Way Reconciliation

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   NEAR Payout Transaction (Trezu / DAO)                │
│            e.g. ft_burn on base-...omft.near (Gross: 1.000000 USDC)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                       (1) Query Receipt Graph
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Payout Reader Core Engine                       │
│    • Zero pip dependencies (Python 3.13 stdlib only)                   │
│    • Process-isolated workers · 120s live deadline · Concurrency locks  │
│    • FastNEAR fallback when primary dRPC endpoints stall               │
└───────────────┬────────────────────────────────────────┬───────────────┘
                │                                        │
     (2) Query Bridge RPC                     (3) Query BaseScan EVM
                │                                        │
                ▼                                        ▼
┌───────────────────────────────┐        ┌───────────────────────────────┐
│     Chaindefuser Bridge       │        │        Base L2 Network        │
│  • PoA withdrawal records     │        │  • USDC Transfer event logs   │
│  • Observed fee: 0.002400 USDC│        │  • Net delivered: 0.997600    │
│  • Destination tx hash link   │        │  • Block & 11M+ confirmations │
└───────────────┬───────────────┘        └───────────────┬───────────────┘
                │                                        │
                └───────────────────┬────────────────────┘
                                    │
                          3-Way Ledger Matching
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         Audited Deliverables                           │
│  • Web Workbench: Carbon Design System Dark Theme (preloads in <5s)   │
│  • RFC 4180 CSV Export: Ready for accounting & QuickBooks             │
│  • SchemaVersion "1" JSON: Full provenance for automated pipelines    │
│  • Trezu Markdown Proof: Instant copy-paste for DAO forum governance   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Try It: Reproducible "Do X &rarr; See Y" Verification

Designed for automated screening bots (Claude Code, Codex) and human evaluators. Zero installation or credentials required.

### Step 1: Run Full Offline Verification Suite (372 Checks)
Runs all unit tests, invariants, regressions, and fixture parity checks completely offline without external network calls:

```sh
# Do:
python3 main.py --check

# See:
# --> reader/run_tests.py       Exit: 0, PASS: 177, FAIL: 0
# --> reader/verify_outputs.py  Exit: 0, PASS: 30, FAIL: 0
# --> reader/run_invariants.py  Exit: 0, PASS: 142, FAIL: 0
# --> reader/repro_all.py       Exit: 0, PASS: 10, FAIL: 0
# --> tests/test_adapter_parity.py   Exit: 0 (27/27 fixture parity)
# --> tests/test_api_server.py       Exit: 0 (saved, live validation, concurrency lock)
# --> tests/test_cli.py              Exit: 0 (--json, --csv, --saved, --check)
# --> tests/test_formatting.py       Exit: 0 (exact 6-decimal integer-string math)
# --> tests/test_validation.py       Exit: 0 (NEAR account & tx hash validation)
# ALL CHECKS PASSED SUCCESSFULLY (Exit 0).
```

### Step 2: Instant CLI Audit (Production Control & CSV Export)
Run a complete reconciliation of a production payout from the CLI and export RFC 4180 CSV:

```sh
# Do:
python3 main.py --saved prod_control --csv

# See:
# row_indices,row_type,recipient,gross_usdc,fee_usdc,net_usdc,verdict,near_tx,base_tx,base_block,note
# 0,single,0x3139dB7DAa48Bbb8a311734DB70423578F50E9CF,1.000000,0.002400,0.997600,OBSERVED_MATCH,FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu,0x6f845a0325d9762b0584d01dfdf789513ac3e2f33639e3d27f9f60d6055ab21a,44162800,"dest tx ... log 831 pays 997600 (= gross 1000000 − fee 2400); receipt 0x1 block 44162800 confirmations 11684459 ... — OBSERVED_MATCH, not final settlement"
```

### Step 3: Ambiguous Group Deficit via CLI (QA1 JSON Export)
Audit an ambiguous grouped payout case where 3 burns were executed on NEAR but only 1 reached Base:

```sh
# Do:
python3 main.py --saved qa1 --json

# See:
# JSON report printed to stdout with schemaVersion "1", overallVerdict "MISMATCH",
# and rows[0].verdict "GROUP_FINDING" spanning indices [0, 1, 2] with 2 unrecorded burns.
```

### Step 4: Run the Local Web Workbench
Start the local HTTP service on port 8765:

```sh
# Do:
python3 main.py --serve --port 8765

# See:
# Payout Reader server listening on http://127.0.0.1:8765
# Open in browser: preloads QA1 Ambiguous Group Deficit within 5 seconds with zero setup.
```

### Step 5: Query HTTP API via curl
```sh
# Do:
curl -sS -X POST http://127.0.0.1:8765/api/report \
  -H "Content-Type: application/json" \
  -d '{"mode":"saved","exampleId":"prod_control"}' | grep -o '"overallVerdict":"[^"]*"'

# See:
# "overallVerdict":"ALL_ROWS_OBSERVED"
```

### Step 6: Run via Docker Container
```sh
# Build container:
docker build -t payout-reader .

# Run containerized server:
docker run -p 8765:8765 payout-reader

# Run offline test suite inside container:
docker run payout-reader python3 main.py --check
```

---

## Proof: Real Mainnet Evidence

Nothing here is a mockup. Payout Reader ships with three replayable fixtures with sealed cryptographic provenance, all cross-referenced against live explorer records:

| Case ID | NEAR Payout Transaction | Signer | Base Delivered Tx | Outcome & Key Finding |
| :--- | :--- | :--- | :--- | :--- |
| **`prod_control`** | [`FD7gA9L45Btw...`](https://nearblocks.io/txns/FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu) | `sponsor.trezu.near` | [`0x6f845a03...`](https://basescan.org/tx/0x6f845a0325d9762b0584d01dfdf789513ac3e2f33639e3d27f9f60d6055ab21a) | **`ALL_ROWS_OBSERVED`**: 1.000000 USDC gross &rarr; 0.002400 fee &rarr; 0.997600 USDC delivered (Base Block 44162800, 11M+ confirmations). |
| **`qa1`** | [`863ZDaRijV6j...`](https://nearblocks.io/txns/863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe) | `sponsor-staging.trezu.near` | [`0xcc876a99...`](https://basescan.org/tx/0xcc876a99edda48c8a3d754bc3237438de0b903ad6967aebe41bbc7b624261e6e) | **`MISMATCH`**: 3 burns of 0.01 USDC executed on NEAR, but only 1 delivered on Base. Reported as honest **`GROUP_FINDING`** across rows `[0, 1, 2]`. |
| **`qa2`** | [`CbyrTsdExtWD...`](https://nearblocks.io/txns/CbyrTsdExtWDbBsdUNqQC65JMBFwXEzkeaGJGmQb2QDz) | `sponsor-staging.trezu.near` | [`0x6c45df6e...`](https://basescan.org/tx/0x6c45df6eb72f605d34a63ca4836536125c9c3cb0969a98cffa51ff34af6be708) | **`MISMATCH`**: 0.19 USDC burn delivered (0.1876 USDC net), but 0.20 USDC burn has no matching bridge record on Base. |

---

## Web Workbench Features

- **5-Second Legibility:** Clean Carbon Design System Dark Theme (Gray 90/100 palette) displaying status banners, metric tiles, and expandable multi-leg audit disclosure.
- **Deep-Linking URLs:** Real-time state synchronization via URL parameters:
  - `https://payout-reader.up.railway.app/?example=qa1`
  - `https://payout-reader.up.railway.app/?example=prod_control`
  - `https://payout-reader.up.railway.app/?example=qa2`
- **1-Click Audit Exports:**
  - **Download CSV:** RFC 4180 compliant spreadsheet export formatted for direct import into QuickBooks, Excel, and DAO accounting systems.
  - **Download JSON:** Machine-readable SchemaVersion `"1"` envelope preserving atomic integer strings, timestamps, and per-leg errors.
  - **Copy Proof:** Generates formatted Markdown audit blocks ready to paste directly into Trezu proposals, Sputnik DAO forum threads, or GitHub issues.
- **Keyboard & Accessibility Support:** Full keyboard navigation (Enter/Space on table rows to toggle evidence drawers), high-contrast labels, and mobile-responsive layout.

---

## Conservative Evidence Semantics & Known Limits

Payout Reader strictly adheres to the principle of intellectual honesty:

- **Receipt-Level Observation &ne; Final Settlement:** Verified receipts (`OBSERVED_MATCH`) represent on-chain receipt-level logs with block confirmations from public RPC providers. They are not cryptographic zero-knowledge finality proofs.
- **Absence of Evidence &ne; Proof of Permanent Loss:** Missing bridge records or unobserved transfers are categorized as ambiguous delivery deficits (`NOT_RECORDED`), not definitive claims of permanent fund destruction or theft.
- **Honest Group Findings on Identical Burns:** When multiple identical amounts are burned in the same batch and only a subset reaches Base, the engine refuses to guess which recipient was paid, grouping them explicitly.
- **Strict Scope Boundaries:** Strictly restricted to the supported route: source token `base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near` &rarr; Base USDC `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913` (chain `eth:8453`, 6 decimals). Any transaction outside this route yields an explicit `UNSUPPORTED` verdict.
- **Concurrency & Resource Limits:** Live reconciliations run in isolated Python subprocesses with a 120-second hard deadline. Server enforces a concurrency busy lock to prevent denial-of-service on public deployments.

---

## When and How It Was Built (NEAR Hackathon Disclosures)

In compliance with NEAR HACKATHON rules (Q-001, Q-002, Q-003, Q-005, Q-014, Q-015):

- **Hackathon Window & Dates:** Built between 2026-11-01 and 2026-11-14 within the official hackathon window.
- **Baseline & Pre-existing Code Disclosure:**
  - Fresh repository initialized for NEAR HACKATHON 2026.
  - The underlying extraction and matching engine was imported from the verified closeout archive `inputs/source-closeout/payout-source-closeout-v5-20261111.tar.gz` (SHA-256: `0ac8f7364292f5e9268bbcc465f433f9ac2ff48c7aeb9d2facfc0f24ce99f4a2`).
  - All web workbench UI, API server, CLI interface, CSV/Markdown proof generators, FastNEAR fallback mechanisms, Docker containerization, and Railway deployment were built during the hackathon.
- **Libraries, Templates & Boilerplate Used:**
  - **Runtime Dependencies:** 100% Python 3.13+ standard library (`http.server`, `urllib`, `json`, `csv`, `subprocess`, `argparse`, `hashlib`, `unittest`). **Zero external pip packages.**
  - **Frontend:** Vanilla JavaScript (ES6+), semantic HTML5, pure CSS3 styled to IBM Carbon Design System design tokens. **Zero npm packages, zero Node build steps.**
  - **Infrastructure:** Docker minimal Alpine container; deployed on Railway.
  - **AI Assistance:** Code was developed with AI assistance (Antigravity / Claude Code) under human architectural supervision following `project/PLAN.md` and `project/ACCEPTANCE.md`.
- **Prior Chain Disclosure:** This project did **not** exist on any other blockchain before NEAR HACKATHON 2026. It was conceived and built specifically for NEAR's cross-chain bridge ecosystem.
- **Multi-Project Disclosure:** Solo entry. This author/team is entering only this single project into NEAR HACKATHON 2026.
- **License:** Open source under the [MIT License](LICENSE). The repository remains public throughout judging.

---

## Demo Video Script (90–120 Seconds Guide)

When presenting or recording the walkthrough for the public post on X:

1. **The Hook & Problem (0:00–0:20):**
   - *"When a Web3 treasury or DAO uses NEAR to pay contractors in USDC on Base, NEAR says 'Success' as soon as the burn transaction confirms. But did the money actually arrive on Base? Often, bridge relayers drop legs or take unexpected fees. Today, bookkeepers have no way to verify cross-chain delivery."*
2. **Production Control Walkthrough (0:20–0:50):**
   - Open [https://payout-reader.up.railway.app](https://payout-reader.up.railway.app).
   - Click **Production Control**.
   - Point out the green `ALL_ROWS_OBSERVED` banner: *"Here's a 1.00 USDC payout. Payout Reader checks the NEAR burn, queries the Chaindefuser bridge RPC, and verifies the BaseScan receipt with 11 million confirmations. Notice the exact fee math: 1.000000 gross minus 0.002400 fee equals 0.997600 delivered."*
3. **The Ambiguous Deficit Problem — QA1 (0:50–1:20):**
   - Click **QA1**.
   - Show the amber `MISMATCH` banner: *"Here, the treasury burned 3 payments of 0.01 USDC on NEAR, but only 1 reached Base. Instead of guessing which contractor got paid, Payout Reader honestly flags this as an ambiguous Group Finding across rows 0, 1, and 2."*
4. **Accountant Exports & Wrap-up (1:20–1:40):**
   - Click **Download CSV**: *"One click gives the accountant an RFC 4180 CSV for QuickBooks."*
   - Click **Copy Proof**: *"One click copies a formatted Markdown proof ready to paste into Trezu or Sputnik DAO governance proposals."*
   - Highlight: *"Built with Python 3.13 standard library only—zero pip dependencies, zero build steps, completely open source on NEAR."*

---

## License

[MIT](LICENSE) © 2026 Payout Reader Contributors.
