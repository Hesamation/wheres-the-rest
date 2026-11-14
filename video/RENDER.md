# Video render notes

Production workspace for the hackathon demo film. Everything lives under `video/`; the
application is untouched. Runtime: local only, no paid services.

## Reproduce

```sh
cd video
npm install                 # pinned deps (package-lock.json)
uv venv .venv --python 3.12 # only needed to re-transcribe narration
uv pip install -r requirements-stt.lock

# 1. Start the app (repo root) and capture footage (overwrites raw/ + public/):
#    (cd .. && python3 main.py --serve)
#    node tools/capture_footage.mjs all       # app, explorers, live — about 3 minutes
# 2. Prepare media (transcode clips, normalize narration, stage public/):
#    ./tools/prepare_media.sh
# 3. Rebuild the edit manifest from the narration word timings:
#    node tools/build_manifest.mjs
# 4. Render + captions:
#    npx remotion render src/index.ts WheresTheRest out/wheres-the-rest.mp4 \
#      --browser-executable=/usr/bin/chromium
#    node tools/build-srt.mjs
```

`--browser-executable` points Remotion at the system Chromium (Arch `/usr/bin/chromium`);
drop the flag to let Remotion download its own headless shell.

## Sync architecture

- `assets/narration.wav` is the human-supplied narration (102.28 s). The original is never modified; `prepare_media.sh` writes `assets/narration-normalized.wav` (−16 LUFS / −1.3 dBTP).
- `tools/transcribe_narration.py` (faster-whisper, local) produces `assets/narration-timing.json` with word-level timestamps.
- `tools/build_manifest.mjs` anchors every scene boundary, caption cue and overlay to those word timestamps (`src/manifest.json`). Re-transcribing a revised narration re-syncs the whole edit.
- Scene/caption/overlay tables live in `src/manifest.json`; card copy in `src/Cards.tsx`; look in `src/theme.ts`.

## Evidence rules followed

Captured 2026-11-14 against the app at commit `edf37ff`. Saved cases keep their dated
labels; explorer searches and the live query carry their own capture date; the Copy Proof
card shows the genuine clipboard contents (`raw/footage/copy-proof-contents.txt`).
Raw recordings are Git-ignored (`raw/`, `out/`, `public/`).
