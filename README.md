# Where's the Rest?

**NEAR says the payout executed. Did the USDC arrive on Base?**

Where's the Rest? is a **read-only investigation tool for NEAR → Base USDC payouts**. Trace supported withdrawals from executed NEAR burns through bridge records to Base USDC transfer logs. Account for observed fees, see unresolved gaps, and inspect or export the evidence behind each finding as JSON, CSV, or Markdown. Use it to investigate a payout discrepancy, check a completed withdrawal, or share the supporting evidence with someone reviewing the payment.

[Open the hosted demo](https://payout-reader.up.railway.app) · [Try the grouped deficit](https://payout-reader.up.railway.app/?example=qa1) · [Try the successful control](https://payout-reader.up.railway.app/?example=prod_control)

## Where this could go

The ambition is to make cross-chain payouts explainable: what left, what arrived, what fees were observed, and what remains unresolved. Today, Where's the Rest? investigates one NEAR → Base USDC route. A next step could reconcile intended payout lists against observed transfers and revisit unresolved withdrawals over time. Additional routes would require their own evidence adapters and validation. These are future directions; the demo implements the single-route investigation described above.

Built for **NEAR HACKATHON 2026**. Intended tracks: **Real-World Money** (payout reconciliation) and **Social Money** (inspectable treasury payout evidence for Trezu/DAO workflows).

**Replay a [real mainnet QA discrepancy](https://github.com/NEAR-DevHub/trezu/issues/1924):** three identical burns to one recipient, one observed destination transfer, and two burns without matching bridge records. The public report includes reproduction steps, screenshots and transaction links. A separate successful payout provides the control.

![Saved QA1 evidence: three NEAR burns, one Base observation, two unrecorded burns](docs/workbench.jpg)

## See the problem in 30 seconds

1. Open **QA1: Group Deficit**. This real mainnet staging transaction contains three identical 0.010000 USDC burns to the **same Base recipient**.
2. See **1 observed transfer and 2 unrecorded burns**. The observed transfer is 0.007600 USDC after an evidenced 0.002400 USDC fee. The reader cannot assign it to a particular source burn; it preserves the group.
3. Inspect the expanded finding (reopen it if collapsed) for NEAR outcome/log identities, the bridge record, and the Base receipt link. Switch to **Control: 1.00 USDC** to see a fully observed payout.
4. **Download JSON**, **Download CSV**, or **Copy Proof** exports the displayed investigation without another provider query.

Saved evidence is explicitly labeled and dated. To refresh an example, select **Live Query**: an empty form is prefilled from the displayed report. Click **Reconcile** to request fresh provider observations. Existing form entries are preserved; you can also enter another supported transaction and signer. Live mode never substitutes a saved result.

## Why this exists

Checking a cross-chain payout means connecting several observations: what executed on NEAR, what the bridge recorded, and what USDC transfer appeared on Base. Source success alone does not answer that whole question. Where's the Rest? brings those observations into one report, with three matching rules that matter in practice:

- **Follow executed withdrawals.** Read the NEAR receipt graph and executed `ft_burn` logs, then compare source gross amounts, bridge fees and net amounts, and destination USDC transfer logs. A submitted action or completed bridge record alone is not enough for an observed match.
- **Count each destination transfer once.** Match by transaction and log identity so repeated evidence cannot satisfy multiple burns. Keep indistinguishable burns grouped when the evidence cannot identify which individual burn matches an observed transfer.
- **Keep incomplete evidence visible.** Missing records, pending execution, provider failures and invalid evidence retain distinct findings rather than becoming an all-observed result.

**Inspect and reproduce the investigation:** expand the source, bridge and destination evidence; follow receipt links; export the displayed findings; or replay dated captures offline. Regression cases exercise partial groups, repeated observations, distinct logs in one destination transaction, incomplete receipt graphs and invalid fee accounting ([matching checks](reader/run_invariants.py)).

**NEAR's role is concrete:** executed `ft_burn` evidence from the supported bridged-USDC OMFT contract is the starting point for tracing the withdrawal through Chaindefuser to Base. The exact supported route and evidence limits are below.

### From a reported discrepancy to a repeatable investigation

The [Trezu QA report](https://github.com/NEAR-DevHub/trezu/issues/1924) provides a concrete starting case: the application reported executed payments while destination observations covered only part of the batch. The reader takes a transaction and signer, reads chain and bridge evidence directly, and applies the same matching rules to every supported input. It requires no Trezu application login or issue-specific error code.

Try the three examples to see the distinction: **Control** traces a successful withdrawal and its fee; **QA1** preserves ambiguous source-burn attribution; **QA2** separates an observed transfer from an unrecorded withdrawal in the same transaction. The report supports payout review and technical investigation without requiring the reviewer to reconstruct the matching across separate services.

## Run it locally

Requires **Python 3.13+**. Runtime and offline checks use the standard library: no pip install, Node build, database, wallet, or API key.

```sh
git clone https://github.com/Hesamation/wheres-the-rest.git
cd wheres-the-rest
python3 main.py --check
python3 main.py --serve
```

Expected: checks exit 0 and print `ALL CHECKS PASSED SUCCESSFULLY`. The server prints `Where's the Rest? server running at http://127.0.0.1:8765/`. Open that address; QA1 loads automatically.

The offline suite currently runs **359 reader checks and 19 application tests (378 total)**. It covers reader regressions/invariants, parity across all 27 fixtures, grouped monetary totals, input validation, API boundaries, and CLI output. It requires no provider access.

Optional frontend controller regressions, for contributors with Node 22+: `node tests/test_frontend.js`. This checks all fixture render paths, large exact totals, grouped observations, and browser/CLI CSV data parity; Node is not required to run the app or the Python suite.

### CLI: do X, see Y

```sh
python3 main.py --saved prod_control --json
# summary.overallCode: "ALL_ROWS_OBSERVED"
# rows[0].amounts: gross "1000000", fee "2400", net "997600"

python3 main.py --saved qa1 --json
# summary.overallCode: "MISMATCH"
# rows[0]: GROUP_FINDING, rowIndices [0,1,2], observed 1, unrecorded 2

python3 main.py --saved prod_control --csv
# RFC 4180 CSV, with gross 1.000000 / fee 0.002400 / net 0.997600

python3 main.py --live FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu --signer sponsor.trezu.near --json
# Fresh provider observations, or an explicit conservative inconclusive result.
# Progress goes to stderr; stdout contains only the selected report format.
```

CLI success means the investigation ran; the report's `summary.overallCode` determines its finding. A `MISMATCH` report is not a CLI execution failure. Money is exported as atomic integer strings with exact six-decimal display strings. In group findings, gross is **per burn**, while fee/net sum **observed transfers in that group**; unknown amounts remain absent.

### HTTP API

```sh
curl -sS http://127.0.0.1:8765/api/examples
curl -sS -X POST http://127.0.0.1:8765/api/report \
  -H 'Content-Type: application/json' \
  -d '{"mode":"saved","exampleId":"prod_control"}'
# JSON envelope with summary.overallCode "ALL_ROWS_OBSERVED".
```

`POST /api/report` also accepts `{ "mode": "live", "txHash": "…", "signerId": "…" }`. Invalid inputs return 400; a busy worker returns 429. `GET /healthz` reports service health. Example deep links: `?example=qa1`, `?example=qa2`, `?example=prod_control`.

### Docker (optional)

```sh
docker build -t wheres-the-rest .
docker run -p 8765:8765 wheres-the-rest
docker run wheres-the-rest python3 main.py --check
```

## Real mainnet examples

| Case / saved capture (UTC) | NEAR transaction / signer | Saved finding |
|---|---|---|
| **[QA1 report](https://github.com/NEAR-DevHub/trezu/issues/1924)** · Nov 10, 22:26:58 | [863ZDa…](https://nearblocks.io/txns/863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe) · `sponsor-staging.trezu.near` | Three 0.01 burns to one recipient; one 0.0076 transfer observed, two burns unrecorded. Source-burn attribution remains grouped. |
| **[QA2 follow-up](https://github.com/NEAR-DevHub/trezu/issues/1924#issuecomment-6746057831)** · Nov 10, 22:32:14 | [CbyrTs…](https://nearblocks.io/txns/CbyrTsdExtWDbBsdUNqQC65JMBFwXEzkeaGJGmQb2QDz) · `sponsor-staging.trezu.near` | 0.19 → 0.1876 observed; a separate 0.20 burn has no matching bridge record. |
| **Control** · Nov 11, 01:16:56 | [FD7gA9…](https://nearblocks.io/txns/FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu) · `sponsor.trezu.near` | 1.000000 − 0.002400 fee = 0.997600 USDC observed on Base. |

All dates are **2026**. Destination receipts: [QA1](https://basescan.org/tx/0xcc876a99edda48c8a3d754bc3237438de0b903ad6967aebe41bbc7b624261e6e), [QA2](https://basescan.org/tx/0x6c45df6eb72f605d34a63ca4836536125c9c3cb0969a98cffa51ff34af6be708), [Control](https://basescan.org/tx/0x6f845a0325d9762b0584d01dfdf789513ac3e2f33639e3d27f9f60d6055ab21a). Saved captures retain historical observations; confirmation depth in a capture is not a current network reading. Capture provenance is in [reader/PROVENANCE.json](reader/PROVENANCE.json).

The QA cases were reported on Trezu staging against mainnet. The reporter's [scope clarification](https://github.com/NEAR-DevHub/trezu/issues/1924#issuecomment-6744636005) says confidential bulk payments and Near Business were unaffected.

## How it works

```text
NEAR transaction + signer
    → receipt graph → executed, supported ft_burn rows
    → Chaindefuser withdrawal records → gross / fee / net
    → Base RPC receipts → USDC Transfer logs
    → conservative reconciliation → workbench / JSON / CSV / Markdown
```

The preserved reader owns extraction, matching, one-use destination log identities, group findings, and verdict precedence. A thin adapter builds a versioned report. The adapter projects observed log identities recorded in reader notes into structured evidence; it preserves all observations in a group and withholds totals if that projection is incomplete. The original notes remain inspectable.

The server uses a fresh subprocess per investigation, a single-worker lock, and a 120-second live deadline. NEAR queries use the reviewed dRPC endpoint with FastNEAR fallback; bridge records come from `bridge.chaindefuser.com/rpc`; Base receipts come from `mainnet.base.org`. Explorer links are for inspection, not data providers. Saved replay makes no network calls.

## Scope and limits

- **One route:** NEAR `base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near` → Base USDC `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913`, chain `eth:8453`, six decimals. Other contracts, tokens, recipients, or incomplete evidence can produce unsupported, invalid, inconclusive, or needs-inspection findings; this is not a universal payout explorer.
- **Provider-trusted observations:** a successful receipt and matching Transfer log support `OBSERVED_MATCH`, not cryptographic proof or final settlement. Source success alone never proves destination delivery.
- **Missing records are unresolved evidence:** unrecorded does not establish why a transfer is absent, who is at fault, permanent loss, or grounds to pay again.
- **Failures remain visible:** pending, reverted, invalid, unmatched, and incomplete observations retain separate findings. On hard worker timeout, the report is inconclusive; partial in-flight evidence is currently discarded. Retry is manual.
- **Small public demo:** one investigation at a time; concurrent requests can receive 429. No persistent history, background monitoring, authentication, payment execution, custody, recovery, or invoice/list reconciliation.
- **Exports:** CSV is a generic reconciliation table for spreadsheets, not a tested QuickBooks import format. “Copy Proof” copies a provider-evidence summary, not a cryptographic proof or direct Trezu/Sputnik API integration. JSON preserves the full report and group metadata.

## Provenance and disclosures

The standalone application was built on **November 13, 2026**. Its reader was developed during the same hackathon period and imported from the November 11 closeout archive. This is a new NEAR project, not a product ported from another chain.

- Python standard library and vanilla HTML/CSS/JavaScript; no third-party runtime libraries or frontend templates. Styling follows IBM Carbon design tokens without using its component library.
- AI coding agents assisted implementation and review.
- The imported reader is preserved unchanged. Source archive, file hashes and capture provenance: [reader/PROVENANCE.json](reader/PROVENANCE.json).
- Single project entry; no second project is being submitted by this author/team. [MIT license](LICENSE).
