# Finish checklist

Build acceptance record. Checked items record completed work; open items retain verification gaps. Current behavior and limits are in README.md and STATUS.md. Do not repeat passing checks unless changes or failures justify it.

- [x] Verify archive hash/manifest, import unchanged reader, run its suite, independent verifier, invariants and regressions plus the separate 13-case harness in a disposable copy. Historical evidence must stay unchanged.
- [x] Adapter matches original runner verdicts/counts/completeness on saved/synthetic cases. No duplicated matching logic.
- [x] QA1, QA2 and FD7g production control match the saved observations in PLAN. EEDi offline_control is a separate case; don't relabel it.
- [x] Exact six-decimal money and integer-string export; displayed report and JSON agree. Follow-up found QA1 headline counts omit group outcomes; verify row evidence associations too.
- [x] Group ambiguity, one-use transfer identities, extra evidence, unsupported scope and failure/incomplete/pending/invalid/revert states remain honest.
- [x] Saved examples work without network. Live failure stays visible; no silent saved substitution.
- [x] Requests validate inputs; workers isolate evidence and clean up on timeout/failure/busy requests; no secrets, paths or tracebacks leak. Hard timeout returns an inconclusive result and discards partial evidence, as documented in README.
- [x] Check desktop browser flow: input, loading/errors, group details, evidence links, keyboard/focus and Copy Proof.
- [ ] Complete final mobile and assistive-technology checks; verify browser file downloads (automation was blocked by its permission gate).
- [x] Clean clone can follow README to run app and offline checks without parent workspace or ignored files.
- [x] Try three live examples once before recording; record actual failures/outcomes, not assumed historical results.
- [ ] README and short video explain scope, saved/live dates and provider-trusted receipt observations; no finality, loss or recovery overclaims. Video remains to be recorded and checked.
- [x] Before public release: review credentials/personal data/imported material and settle license/name with human. Public release/deployment/submission require separate authorization.
