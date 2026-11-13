# Payout Reader — Cross-Chain Payout Reconciler

[![CI](https://github.com/Hesamation/payout-reader/actions/workflows/ci.yml/badge.svg)](https://github.com/Hesamation/payout-reader/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![NEAR Hackathon 2026](https://img.shields.io/badge/NEAR%20Hackathon%202026-realworld%20%7C%20social-orange)](https://nearhackathon.com)

A successful NEAR payout transaction doesn’t tell a treasury operator whether every cross-chain withdrawal reached its destination. **Payout Reader** brings source execution, bridge records and destination transfer observations into one inspectable report.

For the supported NEAR-to-Base USDC route, operators enter a transaction and signer to inspect withdrawals, fees, observed destination amounts and unresolved gaps, with supporting transaction references and a downloadable JSON or CSV report. When identical withdrawals prevent individual attribution, the report preserves that ambiguity instead of guessing.

Three replayable public examples demonstrate a successful transfer, a mixed outcome and a grouped discrepancy. Live lookup supports fresh investigations; saved examples retain their capture dates for reproducibility.

The application is read-only: it moves no funds and requires no wallet connection. Findings reflect provider-supplied receipt observations, not final-settlement proofs; missing records do not establish permanent loss.

Built with **Python 3.13+ standard library only** and plain HTML/CSS/JavaScript (Carbon Design System Dark Gray 90/100 palette). Zero external pip dependencies, zero Node build steps, zero databases, and zero API keys required for offline verification.

---

## Supported Scope & Conservative Semantics

- **Supported Route & Asset:**
  - Source token: `base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near`
  - Bridge: PoA Chaindefuser bridge (`https://bridge.chaindefuser.com/rpc`)
  - Destination asset: Base USDC (`0x833589fcd6edb6e08f4c7c32d4f71b54bda02913`), chain `eth:8453`, 6 decimals.
  - Any transaction outside this exact route reports an explicit `UNSUPPORTED` finding; nothing is guessed.

- **Conservative Evidence Semantics:**
  - Provider observations (`OBSERVED_MATCH`) represent **receipt-level evidence with block confirmations**, never a claim of final settlement or cryptographic validity.
  - Missing observations or unrecorded burns are **ambiguous, not proof of permanent loss**.
  - No bridge root cause is inferred or established solely by the absence of records.
  - Indistinguishable rows (identical amounts and recipients) produce a **Group Finding**: identical gross amounts are never attributed arbitrarily to individual recipients.

---

## Reproducible Machine Verification ("Do X &rarr; See Y")

For automated code evaluators (Claude Code, Codex) and human reviewers:

### Step 1: Run Full Offline Test Suite (372 Checks)
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
# ALL CHECKS PASSED SUCCESSFULLY (Exit 0).
```

### Step 2: Audit a Production Payout via CLI
```sh
# Do:
python3 main.py --saved prod_control --csv

# See:
# row_indices,row_type,recipient,gross_usdc,fee_usdc,net_usdc,verdict,near_tx,base_tx,base_block,note
# 0,single,0x3139dB7DAa48Bbb8a311734DB70423578F50E9CF,1.000000,0.002400,0.997600,OBSERVED_MATCH,FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu,0x6f845a0325d9762b0584d01dfdf789513ac3e2f33639e3d27f9f60d6055ab21a,44162800,"dest tx ... log 831 pays 997600 (= gross 1000000 − fee 2400); receipt 0x1 block 44162800 confirmations 11684459 ... — OBSERVED_MATCH, not final settlement"
```

### Step 3: Run the Local Web Workbench
```sh
# Do:
python3 main.py --serve --port 8765

# See:
# Payout Reader server listening on http://127.0.0.1:8765
# Open in browser: Preloads QA1 Ambiguous Group Deficit within 5 seconds.
```

---

## Saved Examples & Provenance

The application ships with three offline cases with sealed provenance:

1. **QA1 — Ambiguous Group Deficit (`qa1`)**
   - NEAR Tx: `863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe`
   - Signer: `sponsor-staging.trezu.near`
   - Captured: `2026-11-10T22:26:58Z`
   - Finding: 3 burns of 0.01 USDC; 1 observed on Base (0.0076 USDC net after 0.0024 fee), 2 unrecorded. Grouped finding because individual attribution is ambiguous.
2. **QA2 — Mixed Delivery Deficit (`qa2`)**
   - NEAR Tx: `CbyrTsdExtWDbBsdUNqQC65JMBFwXEzkeaGJGmQb2QDz`
   - Signer: `sponsor-staging.trezu.near`
   - Captured: `2026-11-10T22:32:14Z`
   - Finding: 0.19 USDC burn observed on Base (0.1876 USDC net after 0.0024 fee); 0.20 USDC burn without matching bridge record.
3. **Production Control (`prod_control`)**
   - NEAR Tx: `FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu`
   - Signer: `sponsor.trezu.near`
   - Captured: `2026-11-11T01:16:56Z` (from archive member `raw/probe_network_log_full_1794359827.jsonl`)
   - Finding: 1.00 USDC burn observed on Base (0.9976 USDC net after 0.0024 fee); verified via FastNEAR fallback when primary dRPC timed out.

---

## Web Workbench Features

- **5-Second Legibility:** Direct Carbon Design System UI hierarchy preloading the QA1 test fixture with immediate metric tiles, status banner, and multi-leg audit disclosure.
- **Deep-Linking URLs:** Directly link to any saved case via query parameter:
  - `http://127.0.0.1:8765/?example=qa1`
  - `http://127.0.0.1:8765/?example=prod_control`
  - `http://127.0.0.1:8765/?example=qa2`
- **One-Click Audit Exports:**
  - **Download JSON:** SchemaVersion `"1"` envelope preserving raw atomic integer strings and full leg provenance.
  - **Download CSV:** Standard accounting/spreadsheet RFC 4180 export ready for DAO bookkeeping and QuickBooks import.
  - **Copy Proof:** Generates a copy-pasteable Markdown audit proof block ready to post directly into Trezu proposals, Sputnik DAO forum threads, or GitHub issues.

---

## Docker Execution

To run Payout Reader in an isolated container:

```sh
# Build the container:
docker build -t payout-reader .

# Run containerized server:
docker run -p 8765:8765 payout-reader

# Run offline checks in container:
docker run payout-reader python3 main.py --check
```

---

## Local Demo Walkthrough (90–120 Seconds Guide)

When recording or presenting the local demo:

1. **Introduction (15s):**
   - State the core operator problem: A DAO or company treasury executes a batch payout transaction on NEAR, but needs verifiable proof of which recipients actually received USDC on Base.
   - Point to the scope badge: `base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near` &rarr; Base USDC.
2. **Production Control (`prod_control`) (30s):**
   - Click the "Production Control" example card.
   - Show the green `ALL_ROWS_OBSERVED` banner with the receipt-level qualification.
   - Highlight the exact breakdown: Gross `1.000000 USDC`, Evidenced Fee `0.002400 USDC`, Evidenced Net `0.997600 USDC`.
   - Click "Inspect" to reveal the NearBlocks outcome ID, the Chaindefuser bridge transaction, and the BaseScan receipt with confirmation count.
3. **QA1 Ambiguous Group Deficit (`qa1`) (30s):**
   - Click the "QA1" card.
   - Show the amber `MISMATCH` banner.
   - Explain the group finding: 3 burns of 0.01 USDC were executed on NEAR, but only 1 bridge withdrawal was recorded. The app honestly groups rows `[0, 1, 2]` rather than arbitrarily guessing which employee/vendor was paid.
4. **JSON, CSV & Governance Proof Export (25s):**
   - Click "Download CSV" to demonstrate spreadsheet accounting export.
   - Click "Copy Proof" to show pre-formatted Markdown for Trezu/DAO governance threads.
   - Switch to the "Live Network" tab. Show input validation on empty fields and demonstrate live query with FastNEAR fallback.
   - Conclude with the conservative evidence disclaimer.
