# GLM video production handoff

Open the local coding agent at `/home/alisa/Projects/ongoing/near/payout-reader` and use GLM 5.3. This is a production task, not a new product build. No other agent should write to this repo concurrently.

## Inputs ready

- `video/BRIEF.md`: narrative, shot list, evidence boundaries, URLs and delivery requirements.
- `video/assets/narration.wav`: human-supplied final narration, 102.28 seconds, 24 kHz mono PCM WAV. Preserve the original. Format/duration checked; listening and transcript verification remain pending.
- `video/narration-reference.txt`: brief's intended script, not a verified transcript of the WAV. The human may have inserted pauses or changed words. Listen before creating captions.
- Product instructions: root `AGENTS.md`, `README.md`, `project/STATUS.md`. No product START-HERE file exists at this handoff. `project/PLAN.md` is historical.

All new production code, dependencies, assets, recordings and renders belong under `video/`. Do not require the old sibling video folder or any parent-chat history. That folder was preserved as the original; this copy is the production handoff.

## Paste into GLM

> Produce the complete Where's the Rest? demo video from `video/BRIEF.md` and `video/assets/narration.wav`. Read `AGENTS.md`, the product README/status and this handoff first. Work entirely inside `video/` for new production files; leave application code, imported reader, existing evidence and deployment unchanged.
>
> First listen to the supplied WAV and verify the words against `video/narration-reference.txt`. Use the audio's actual duration and delivery for scene timing and captions. Do not regenerate narration. If an audible factual claim conflicts with fresh explorer results or product behavior, explain the exact mismatch and ask for a decision on that claim; continue independent work meanwhile. Never fabricate a result to match the soundtrack.
>
> Rehearse and capture genuine app interactions using Playwright, then build the edit with Remotion and local FFmpeg. Run the app from the repo root with `python3 main.py --serve` (default http://127.0.0.1:8765). Capture saved Control, QA1, evidence inspection, actual Copy Proof contents, and genuine same-hash explorer searches as described in the brief. Saved evidence must remain labelled with its capture date; fresh explorer searches have their own date. Do not represent manual explorer checks as app integrations. A provider failure is not a successful live result or an empty search result.
>
> Keep usage economical. Reuse available tools, make one straightforward composition, and avoid optional animation, broad research, music generation, repeated design rounds or extra agents. Pin local dependencies and keep a lockfile. No global installs, paid services, new subscriptions or cloud rendering. Check licensing for the intended use before adopting production tools; if any proposed tool requires payment, use a free local alternative. Shell commands use RTK when available.
>
> Render and inspect a 10–15 second sample containing genuine footage, narration and captions. Fix issues and continue through the full film without routine approval pauses. Inspect representative frames, important transitions and the final audio; do not repeatedly dump screenshots or long render logs. Keep captions and shot timings in an editable manifest. Target approximately 105–115 seconds with the supplied audio and a brief end hold, maximum 120; adjust to actual speech rather than stretching or truncating it.
>
> Deliver `video/out/wheres-the-rest.mp4` (1920×1080, 30fps, H.264/AAC, fast-start, under 200 MB), `video/out/captions.srt`, a poster, editable source/lockfile and short reproduction instructions. Keep original narration and raw recordings locally. Verify amounts, QA attribution, grouped ambiguity, provider-trust limits, caption accuracy, audio continuity and ending readability. No publishing, deployment, repository visibility change, external messages or submission. Leave a short status with what works, checks/failures and next action.

## Local production notes

At handoff, Node 22, npm, FFmpeg, FFprobe, Chromium and UV were found on PATH. Remotion/Playwright setup has not been performed or verified. Check the local coding agent's terminal/browser capabilities before assuming capture works.

Raw captures, audio, renders and dependency directories are ignored by `video/.gitignore`. They remain local and will not accompany a Git clone; transfer the WAV separately if changing computers. Keep source, manifests, captions and the lockfile suitable for Git; inspect staged files before committing. `video/` is excluded from Docker build uploads.

Production status: handoff prepared; WAV format/duration verified; no footage, captions, render or listening QA yet. Next: GLM verifies narration and rehearses genuine capture.
