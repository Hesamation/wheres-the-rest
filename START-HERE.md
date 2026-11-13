# Start here

Open this repository directly in your chosen agent harness. No parent workspace or prior conversation is needed.

1. Read AGENTS.md, project/STATUS.md and project/PLAN.md.
2. Inspect Git status and preserve existing changes.
3. Once authorized, build the complete app and run project/ACCEPTANCE.md. Keep going without batch approval stops.

## Paste this to the builder when ready to start

```text
Build this wheres-the-rest app end to end. Read START-HERE.md, AGENTS.md,
project/STATUS.md and project/PLAN.md. Preserve existing work and reuse
our accepted reader. Implement, test, check the actual UI and prepare the
local demo. Make routine decisions yourself; don't stop between phases
or generate extra plans/reports. Commit useful progress. Before stopping,
leave a short STATUS with checks, known problems and next steps.
Create a private GitHub remote with gh if needed and push, using the
account I specify. No public release, deployment, purchases, external
messages, submission or additional agents. Never use Astra.
```

Sending that prompt authorizes implementation; merely opening the repo does not.

## Private remote

From this directory, after confirming the correct GitHub account:

```sh
gh repo create OWNER/wheres-the-rest --private --source=. --remote=origin --push
```

Replace OWNER with the human's account/organization. If origin already exists, inspect it and push rather than creating/replacing it blindly. Account access must work; the earlier parent-workspace push returned Repository not found. No private remote exists for this product yet.

## Switching agents

Stop the old writer. Open the same checkout in the new harness and say:

```text
Read START-HERE.md and project/STATUS.md, inspect the current work and
continue the authorized build. Preserve changes. Don't restart planning.
```

Git plus a short STATUS is the handoff. Harness memory is optional. On a different machine, push/clone first, or explicitly transfer the current checkout including uncommitted work.
