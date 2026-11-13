# Working instructions

- The product is implemented. Read README.md for current behavior and project/STATUS.md for verification limits and next actions. project/PLAN.md is historical design intent, not a pending build instruction.
- Carry authorized maintenance through appropriate checks. No batch approvals, repeated planning, mandatory reports or separate documentation commits.
- Make routine implementation decisions yourself. Ask only for material scope changes, spending, public release/deployment, external messages or submission. No secrets in Git; no force-push or destruction of existing work.
- Keep the read-only scope and conservative evidence semantics. Reuse the accepted reader; preserve its original input archive. Claim only checks actually run. Use project/ACCEPTANCE.md as the finish checklist, not a reporting process.
- Commit meaningful progress and push to the private remote when available. Before stopping or switching agents, update project/STATUS.md with only what works, checks/failures, and what to do next. No duplicate logs or commit-hash bookkeeping; Git records history.
- Any harness/provider is fine except Astra, which remains prohibited. One writer at a time; no extra agents or delegation unless the human asks. Do not silently buy capacity.
- Keep documents short. No new process documents, broad research or parser-audit loops without a concrete need. Preserve existing evidence; do not resume WBTS.
- Use rg for search and RTK for shell commands when available here. Neither is an application dependency.
