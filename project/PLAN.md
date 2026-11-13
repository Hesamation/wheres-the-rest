# Payout reader — implementation plan

Prepared 2026-11-13 from the full conversational plan. Builder unselected; preparation does not authorize implementation. Once authorized, execute this plan continuously without phase approvals.

## Outcome and scope

A treasury operator enters a supported NEAR payout transaction and signer, then sees executed withdrawals, bridge records, observed Base USDC transfers, unresolved gaps and supporting evidence. One local page, live mode, three saved examples, JSON download, reproducible README and short video.

Only source token `base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near` to Base USDC `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913`, chain `eth:8453`, six decimals. Receipt-level provider observations, no cryptographic proofs or final-settlement claim. Missing graph expansion means incomplete evidence.

Exclude lists/invoices, CSV, auth/history, extra chains/assets, custody/execution/recovery and forced AI functionality. Preserve WBTS unchanged. Independent product repo; deadline-first local demo; intended Real-World Money track.

## Reader and server

- Python 3.13+, runtime standard library only; plain HTML/CSS/JavaScript. No Node build or database.
- Start by verifying the accepted archive hash/manifest and imports the reader/tests/evidence needed for reproduction. Preserve reader source unchanged with hashes/provenance; historical README counts are stale.
- Thin adapter calls existing extraction, completeness, normalization, destination validation, reconcile and summarize functions. Matching/verdict precedence stay inside the reader. Compare adapter findings against original run_case on saved/synthetic inputs. Concrete semantic fixes require failing cases and recorded patches.
- Serve static assets and same-origin API on 127.0.0.1:8765 by default, port overridable. Fresh subprocess per reconciliation isolates reader-global network logs. Permit one active reconciliation; busy responses reject overlap. Terminate/clean up workers after success, failure or timeout.
- Preserve NEAR primary/FastNEAR fallback behavior and fixed reviewed provider endpoints. Configuration stays server-side; no arbitrary URL fetch API. No wallet, paid API requirement, polling or persistent report storage. Retry is user initiated.
- Overall live deadline 120 seconds: unfinished work becomes inconclusive, retaining collected evidence and identifying unfinished legs. Never turn deadline/resource/provider failure into a positive finding.
- Worker emits report and evidence to request-local temporary files; server loads validated output then cleans up. Do not include tracebacks, local paths, credentials or credential-bearing URLs in responses/exports. Browser holds report for download.

## Interfaces and data contract

- GET /api/examples: three IDs/labels, tx hashes/signers, capture dates.
- POST /api/report: `{mode:"live", txHash, signerId}` or `{mode:"saved", exampleId}`. Live requires both tx and signer. Validate bounded JSON, base58 32-byte transaction hash and valid named/implicit NEAR account. Saved requests use an allowlisted ID, never a path.
- HTTP errors for invalid input, busy or internal failures. Provider-unavailable/incomplete investigations return conservative report findings. Local CLI exposes equivalent live/saved reconciliation and JSON output.
- Envelope `schemaVersion:"1"`: request identity/mode, exact supported configuration, reader hash/version, generation time and separate capture times; original overall/row/group findings and completeness/limitations; normalized source/bridge/destination evidence with stable IDs and per-leg errors; source outcome/log and destination tx/log references where available; counts and explorer links. Unknown/missing fields stay explicit.
- Monetary integers serialize as strings, displayed by exact six-decimal conversion. Show gross, evidenced fee/net separately. Omit hypothetical net estimates from main UI. Do not reconstruct matching decisions by parsing prose notes; use reader findings and structured normalized evidence. Retain original notes for inspection.
- JSON download is the displayed report envelope, without another provider request. UI/export must agree. No invented row/invoice identity or netting away extra records.

## Page behavior

Responsive restrained layout: tx/signer form, live/saved controls and three examples; plain-language overall finding with mode/capture time; source/bridge/destination counts; group/withdrawal details with recipient, gross/fee/net and unresolved counts; expandable evidence/provider errors, explorer links and download.

Separate source success from destination observation. Only ALL_ROWS_OBSERVED gets all-observed presentation, with receipt-level qualification. Preserve distinct failed, incomplete, unsupported, pending, invalid, mismatch and unmatched-evidence states. Unknown states are neutral needs-inspection. Text labels supplement color; keyboard/focus, contrast and mobile wrapping work. Render provider content as text.

## Saved examples and provenance

1. QA1 `863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe`, signer `sponsor-staging.trezu.near`: three 0.01 burns; one 0.0076 observed after 0.0024 fee, two unrecorded; individual attribution ambiguous.
2. QA2 `CbyrTsdExtWDbBsdUNqQC65JMBFwXEzkeaGJGmQb2QDz`, same signer: 0.19 -> 0.1876 observed; 0.20 without matching observed bridge record.
3. Production control `FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu`, signer `sponsor.trezu.near`: 1 -> 0.9976 observed.

Production saved evidence is in archive member payout-feasibility/raw/probe_network_log_full_1794359827.jsonl (full source/bridge/Base exchanges). Build a fixture with original capture provenance. Existing offline_control is a DIFFERENT EEDi… transaction: retain it for regression, never relabel it FD7g…. QA fixtures are already present. Saved mode never performs network requests or silently appears live.

## Build order (no approval stops)

1. Foundation (2–3 focused hours): verified import, portable records/provenance, three replayable examples, fresh reader checks. Product CLI/check commands documented.
2. Adapter/API (3–5 h): isolated workers, contract, evidence, live/saved endpoints, conservative errors/timeouts and original-runner parity.
3. UI (3–5 h): complete flow, exact money/group findings, evidence, export, responsive usability.
4. Acceptance/demo (3–5 h): integrated checks, bounded live refresh, clean-clone rehearsal, README and video preparation.

Total estimate 11–18 focused builder hours, not a promise; excludes provider/limit/human delays. Human availability is unknown. Use ACCEPTANCE.md to verify the finished build. The sequence and estimates are guidance, not process gates. Commit meaningful progress; keep one short STATUS when stopping. No separate documentation commits, decision ledger or per-phase approval. Starter preparation is not implementation.

## Demo, contingencies and release

90–120 second video: operator question, successful control/evidence, QA1 grouped deficit, QA2/export, limits. Refresh three live cases once before recording; record actual outcomes, without requiring historical discrepancies to persist. If providers fail, show failure explicitly and use labeled saved evidence with capture dates; never silently substitute it.

Current official deadline checked 2026-11-13: November 14, 2026, 23:59 UTC. Local demo permitted with public repo, reproducible README and video-linked public post. Source: https://nearhackathon.com/HACKATHON.md . Refresh rules again before submission. Hosting deferred, not a delivery dependency. Remove optional polish before evidence honesty, required checks or reproducibility.

Human inputs: builder/implementation authorization now; name, license/third-party release review, remote/publication destination and release approval before publication; actual contact/team/payout/demo-post details and exact payload approval before submission. Human publishes the public post. Never guess personal inputs, send external messages, deploy or submit automatically. No numerical win odds, proved demand, recovered funds, permanent loss or final settlement claims.
