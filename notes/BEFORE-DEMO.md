# Before the demo

## What the follow-up inspection found (2026-11-13)

The implementation exists and the offline suites pass. Codex reran `python3 main.py --check`: reader 177, verifier 30, invariants 142 and regressions 10 passed, as did adapter/CLI/formatting/validation. The API test initially could not create sockets in the sandbox; rerunning it with localhost access passed. No fresh live RPC run or browser verification was done in this review: the browser access host was unavailable. Gemini's earlier live/browser results remain builder-reported.

Fix before recording:

1. **Confirmed counter bug:** `reconcile_saved("qa1")` returns headline `observedMatches=0, unrecorded=0`, despite group details `observed=1, unrecorded=2`. The UI displays those incorrect headline values. Aggregate row outcomes including groups without double counting. Keep the original reader summary counts intact.
2. **Evidence association risk:** in `app/adapter.py`, an OBSERVED_MATCH row picks the first completed bridge record with the same gross amount, then a destination entry by transaction and recipient. It does not follow the reader's exact consumed transfer identity or check all matching conditions. Add a reproducer with equal gross amounts, different recipients/fees and reordered records; verify every row's fee/net/transaction/log reference. Existing parity tests mostly compare verdicts/counts, so passing them does not establish evidence-reference correctness. Do not parse prose notes to reconstruct associations.
3. **Timeout gap:** `app/worker.py` writes its report only after reconciliation finishes; `app/runner.py` kills it on timeout and returns empty rows with no normalized evidence. Collected partial evidence is lost, contrary to PLAN/README. Preserve safe partial evidence with a consistent envelope, or explicitly resolve the narrower behavior with the human; don't claim it already works.
4. **Stale-result risk:** starting a new request leaves the previous report/export visible; switching to Live can still show a saved report. Clearly identify the displayed report and disable or distinguish stale export while a new lookup runs/fails. Test this rather than silently relabeling saved results as live.

These are bounded review targets, not a request to re-audit the original reader from scratch.

## Review prompt (paste into a fresh Sonnet session in this repo)

```text
Review the current implementation for demo-blocking correctness bugs.
Read AGENTS.md, project/STATUS.md, project/PLAN.md and notes/BEFORE-DEMO.md.
Verify the four targets above with concrete reproducers; also inspect input
handling, worker cleanup and failure states. Prioritize wrong evidence,
misleading results and crashes over style. Expand parity tests to assert
row evidence identities and amounts, not only summary verdicts/counts.
Fix confirmed issues with small patches and regression checks; preserve
the accepted reader and sealed archive. Don't rewrite the stack, add
features, start subagents or publish. Report remaining bugs with file/line
references and checks actually run. Keep STATUS short and commit fixes.
```

Use one reviewer first. If it cannot resolve a concrete issue, take that issue and reproducer to Opus; no review committee needed. Stop the previous writer before another agent edits.

## Your manual check (about 10 minutes)

Run `python3 main.py --serve --port 8765` in this repo, then open http://127.0.0.1:8765.

1. **Production Control:** confirm saved mode/date; 1.000000 gross, 0.002400 fee, 0.997600 net. The positive finding must say receipt-level observation, not settlement proof. Open Inspect and a Base explorer link.
2. **QA1:** confirm 3 burns, 1 observed, 2 unrecorded, with group ambiguity prominent. No invented attribution to individual rows. Headline counts and details must agree.
3. **QA2:** confirm 0.190000 gross / 0.187600 observed net and a separate 0.200000 unrecorded burn. Missing delivery evidence must not be described as proven permanent loss.
4. **Export:** download QA1 JSON. Open it in an editor and compare transaction, saved mode/date, counts and group details with the screen. It must describe the displayed report.
5. **Live and errors:** submit empty inputs, then junk inputs. Both should give useful errors. Try the production tx/signer from README once. A provider error is acceptable if honest; a silent saved substitution is not. While it loads or after failure, ensure an older green report/export cannot be mistaken for this lookup.
6. **Offline:** disable network in browser devtools or disconnect internet; load the saved cases again. Their reports should still work while the local server runs. Restore connectivity afterward.
7. **Usability:** use Tab/Enter to select a case, expand details and export. At a roughly 390px-wide browser viewport, check clipped controls, overlapping text and readable amounts; horizontal scrolling confined to a table is acceptable.
8. **Rehearsal:** explain the control and QA1 in 90–120 seconds without reading technical paragraphs. If you cannot quickly find the outcome or evidence, the screen needs simplification before recording.

No need to manually repeat the parser suite. Your main contribution is checking whether the story and interactions make sense. Send the builder a screenshot plus the exact step that failed.

## Design pass after correctness fixes

Choose one concrete reference screenshot, then iterate against browser screenshots; a skill or a longer adjective-filled prompt cannot replace that loop. Suggested direction: a restrained reconciliation workbench with the finding and amounts first, one main action, compact example selection, and technical provenance below expandable details. Keep saved/live/date distinctions visible. Remove implementation copy such as “isolated subprocess” and the Python stack footer from the product flow. Preserve evidence limitations in plain language.

Reference guidance: [Carbon data tables](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines), [USWDS table guidance](https://designsystem.digital.gov/components/table/) and [typography](https://designsystem.digital.gov/components/typography/). Borrow layout/spacing/hierarchy principles; no component-library installation or framework migration needed.

```text
Polish this existing UI after the correctness fixes. First capture the
initial screen and QA1 result at desktop and mobile widths. Use the visual
reference I provide; keep the current Python/plain-web stack and API.
Make outcome, amounts and uncertainty readable within five seconds.
Simplify jargon, redundant badges/cards and technical chrome. Keep exact
amounts, evidence access, saved/live/date labels and conservative semantics.
Show a screenshot of the proposed QA1 layout before changing the whole UI.
After implementation compare screenshots and test keyboard, errors, stale
results and JSON export. No new features or backend rewrite.
```

The video has not been recorded or checked by this review. Private remote backup, release/license decisions and submission remain outstanding.
