# NEAR USDC Payout Reconciler

Independent, read-only cross-chain payout audit tool for treasury operators. Reconciles NEAR token burns against Chaindefuser bridge records and Base USDC receipt transfers to verify payout delivery, identify deficits, and document unresolved legs.

Built with **Python 3.13+ standard library only** and plain HTML/CSS/JavaScript. No external package dependencies, no Node build step, no database, no wallet, and no paid API requirements.

---

## Supported Scope & Conservative Semantics

- **Supported Token & Route:**
  - Source token: `base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near`
  - Bridge: PoA Chaindefuser bridge (`https://bridge.chaindefuser.com/rpc`)
  - Destination asset: Base USDC (`0x833589fcd6edb6e08f4c7c32d4f71b54bda02913`), chain `eth:8453`, 6 decimals.
  - Everything else reports an explicit unsupported state; nothing is guessed.

- **Conservative Evidence Semantics:**
  - Provider observations (`OBSERVED_MATCH`) represent **receipt-level evidence with block confirmations**, never a claim of final settlement or cryptographic validity.
  - Missing observations or unrecorded burns are **ambiguous, not proof of permanent loss**.
  - No bridge root cause is inferred or established solely by the absence of records.
  - Indistinguishable rows (identical amounts and recipients) produce a **Group Finding**: identical gross amounts are never attributed arbitrarily to individual recipients.

---

## Saved Examples & Capture Dates

The application includes three reproducible offline examples with sealed capture provenance:

1. **QA1 — Ambiguous Group Deficit (`qa1`)**
   - NEAR Tx: `863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe`
   - Signer: `sponsor-staging.trezu.near`
   - Evidence Captured: `2026-11-10T22:26:58Z`
   - Finding: Three 0.01 USDC burns; 1 observed on Base (0.0076 USDC net after 0.0024 fee), 2 unrecorded; grouped finding because individual attribution is ambiguous.
2. **QA2 — Mixed Delivery Deficit (`qa2`)**
   - NEAR Tx: `CbyrTsdExtWDbBsdUNqQC65JMBFwXEzkeaGJGmQb2QDz`
   - Signer: `sponsor-staging.trezu.near`
   - Evidence Captured: `2026-11-10T22:32:14Z`
   - Finding: 0.19 USDC burn observed on Base (0.1876 USDC net after 0.0024 fee); 0.20 USDC burn without matching bridge record.
3. **Production Control (`prod_control`)**
   - NEAR Tx: `FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu`
   - Signer: `sponsor.trezu.near`
   - Evidence Captured: `2026-11-11T01:16:56Z` (from archive member `raw/probe_network_log_full_1794359827.jsonl`)
   - Finding: 1.00 USDC burn observed on Base (0.9976 USDC net after 0.0024 fee); verified via FastNEAR fallback when primary dRPC timed out.

---

## Quickstart

### 1. Run Offline Checks & Verifiers

Verify the reader test suites, invariant checks, and adapter parity tests offline without network access:

```sh
python3 main.py --check
```

### 2. Start the Local Web Application

Launch the local web server on port 8765:

```sh
python3 main.py --serve --port 8765
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765) in any modern desktop or mobile browser.

### 3. Command Line Usage

**Reconcile a saved example:**
```sh
# Human-readable output:
python3 main.py --saved qa1

# Raw schemaVersion "1" JSON export:
python3 main.py --saved prod_control --json
```

**Reconcile a live transaction:**
```sh
python3 main.py --live FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu --signer sponsor.trezu.near
```

---

## Architecture & Implementation Notes

- **Subprocess Worker Isolation:** Every reconciliation runs in an isolated subprocess (`app.worker`), ensuring that reader-global network logs and provider state cannot bleed between requests.
- **Concurrency Control:** At most one reconciliation worker runs at a time; busy requests are rejected with HTTP 429/503.
- **Bounded Live Deadline:** Live investigations enforce a 120-second deadline; incomplete work returns a conservative `INCONCLUSIVE` finding preserving collected evidence.
- **Exact Money Representation:** Monetary amounts are stored as exact atomic integer strings (e.g. `"1000000"`) and formatted via integer string arithmetic (e.g. `"1.000000"`), avoiding floating point inaccuracies.
- **Client-Side Export:** The "Download JSON Report" button exports the exact displayed JSON report envelope without triggering a new network request.

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
4. **JSON Export & Live Validation (25s):**
   - Click "Download JSON Report" to demonstrate export agreement.
   - Switch to the "Live Network" tab. Show input validation on empty fields and demonstrate live query with FastNEAR fallback.
   - Conclude with the conservative evidence disclaimer.
