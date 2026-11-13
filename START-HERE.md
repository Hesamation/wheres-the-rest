# Start here

Read in order: [AGENTS.md](AGENTS.md), [status](project/STATUS.md), [decisions](project/DECISIONS.md), [build plan](project/PLAN.md), [acceptance](project/ACCEPTANCE.md), then [input provenance](inputs/README.md).

Inspect `git status --short`, `git log -3 --oneline` and `git remote -v`. Preserve existing changes. All paths below are relative to this repository; no parent checkout or chat is required.

## Bootstrap prompt for any harness

```text
Read START-HERE.md and its linked instructions, status, decisions, plan,
acceptance and input provenance. Inspect the actual Git state first.
Preserve existing work. Distinguish historical evidence from fresh checks.
Continue only the next authorized task recorded in project/STATUS.md.
Current checkpoint is preparation only; do not implement until the human
explicitly authorizes implementation. Never use Astra. No delegation,
spending, publication, deployment, external messages or submission.
Do not depend on another harness's memory, tools or conversation history.
```

## Implementation authorization template — human sends this separately

```text
Implement the approved plan, starting with Batch 1. Continue through the
routine batches using the acceptance gates. Commit/checkpoint each batch.
Keep scope fixed; escalate material architecture or scope changes.
No delegation, spending, public release, deployment or submission.
```

## Switching builders

Use the same checkout, or clone the product repository including its latest commits. If work is uncommitted, checkpoint it or transfer it explicitly first. Stop the previous writer before starting another. The new builder reads these files and verifies the recorded commit/checks before continuing. Harness-specific instructions may point here; do not duplicate the specification into competing memory stores.

No provider has been selected. GLM-5.3/ZCode was recommended, with Gemini/Antigravity as fallback; neither is a human selection. Do not automatically switch models or buy capacity on limit errors. Save a checkpoint and report the limitation.
