# Acceptance gates

Unchecked until actually run in this product checkout. Record commands, implementation hash, results and limitations at each batch closeout.

## Foundation

- [ ] Archive SHA-256 and 478-entry manifest verified before runtime import.
- [ ] Reader suite, independent verifier, generated invariants and ten regressions pass locally.
- [ ] Separate thirteen-case harness passes, with no parent-workspace dependency. Run original harness in a disposable copy: it writes outputs beside itself.
- [ ] Three public examples have complete provenance; FD7g production control is not EEDi offline_control.
- [ ] All necessary inputs tracked; no implicit dependency on private parent or ignored evidence.

## Adapter/API

- [ ] Original runner parity on saved/synthetic cases: verdicts, counts, completeness.
- [ ] Exact six-decimal formatting, integer strings and large amounts; UI/export agree.
- [ ] Group ambiguity, single log consumption, unsupported/mixed scope and extras preserved.
- [ ] Source failure, missing graph, malformed data, provider unavailable, pending, revert and missing transfer stay conservative.
- [ ] Worker isolation, busy requests, timeout cleanup and unknown-state handling exercised.
- [ ] Live inputs validated; saved IDs allowlisted; no paths/secrets/tracebacks leaked; provider content rendered safely.
- [ ] Saved mode tested without network; never silently substituted for live.

## UI/delivery

- [ ] QA1, QA2 and production control match saved observations in PLAN.md.
- [ ] Actual browser flow checked at desktop/mobile widths; keyboard/focus, long IDs and errors/loading/download work.
- [ ] Clean clone reproduces setup, offline checks and app startup outside this workspace.
- [ ] One bounded three-example live refresh recorded with timestamps/provider failures; not treated as guaranteed historical results.
- [ ] README states scope, provider trust, no receipt proofs/finality threshold, no permanent-loss inference and no obligation checking.
- [ ] Video shows real user flow and explicit saved/live provenance.
- [ ] Release reviewed for credentials, personal data and third-party material; license/name/publication approved separately.

No blanket parser audit, fresh competitor research or WBTS tests by default. Reopen only for concrete new evidence relevant to delivery.
