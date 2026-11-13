# Finish checklist

Run these during the build; summarize results in STATUS when stopping. No separate reports or approval gates. Don't repeat passing checks unless changes or failures justify it.

- [x] Verify archive hash/manifest, import unchanged reader, run its suite, independent verifier, invariants and regressions plus the separate 13-case harness in a disposable copy. Historical evidence must stay unchanged.
- [x] Adapter matches original runner verdicts/counts/completeness on saved/synthetic cases. No duplicated matching logic.
- [x] QA1, QA2 and FD7g production control match the saved observations in PLAN. EEDi offline_control is a separate case; don't relabel it.
- [ ] Exact six-decimal money and integer-string export; displayed report and JSON agree. Follow-up found QA1 headline counts omit group outcomes; verify row evidence associations too.
- [x] Group ambiguity, one-use transfer identities, extra evidence, unsupported scope and failure/incomplete/pending/invalid/revert states remain honest.
- [x] Saved examples work without network. Live failure stays visible; no silent saved substitution.
- [ ] Requests validate inputs; workers isolate evidence and clean up on timeout/failure/busy requests; no secrets, paths or tracebacks leak. Timeout partial-evidence preservation remains unresolved.
- [x] Check actual desktop/mobile browser flow: input, loading/errors, group details, evidence links, keyboard/focus and JSON download.
- [x] Clean clone can follow README to run app and offline checks without parent workspace or ignored files.
- [x] Try three live examples once before recording; record actual failures/outcomes, not assumed historical results.
- [ ] README and short video explain scope, saved/live dates and provider-trusted receipt observations; no finality, loss or recovery overclaims. Video remains to be recorded and checked.
- [ ] Before public release: review credentials/personal data/imported material and settle license/name with human. Public release/deployment/submission require separate authorization.
