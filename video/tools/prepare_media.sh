#!/usr/bin/env bash
# Prepare media for the Remotion edit:
#  - transcode raw webm recordings to CFR 30fps H.264 mp4 (crf 16, high profile)
#  - normalize narration to -16 LUFS integrated / -1.5 dBTP (original stays untouched)
#  - write raw/prepared/index.json with clip durations for the manifest builder
set -euo pipefail
cd "$(dirname "$0")/.."

PREP=raw/prepared
mkdir -p "$PREP" out

echo "== transcode clips =="
python3 - <<'EOF'
import json, subprocess, os, sys
src = json.load(open("raw/footage/index.json"))
out = {}
for name, meta in src["clips"].items():
    infile = meta["file"]
    outfile = f"raw/prepared/{name}.mp4"
    if not os.path.exists(outfile) or os.path.getmtime(outfile) < os.path.getmtime(infile):
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-i", infile,
            "-c:v", "libx264", "-preset", "medium", "-crf", "16",
            "-pix_fmt", "yuv420p", "-r", "30", "-fps_mode", "cfr",
            "-an", "-movflags", "+faststart", outfile,
        ], check=True)
    d = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", outfile], capture_output=True, text=True, check=True).stdout.strip()
    out[name] = {"file": f"raw/prepared/{name}.mp4", "duration": float(d)}
    print(f"  {name:20s} {float(d):6.2f}s")
json.dump(out, open("raw/prepared/index.json", "w"), indent=2)
EOF

echo "== stage render assets into public/ =="
mkdir -p public/clips public/stills public/fonts
cp -f raw/prepared/*.mp4 public/clips/
for f in control-wide control-row control-evidence qa1-wide qa1-kpis qa1-evidence-bridge qa1-evidence-dest live-prefill live-result basescan explorer-ni explorer-range; do
  [ -f "raw/stills/$f.png" ] && cp -f "raw/stills/$f.png" public/stills/
done
cp -f assets/narration-normalized.wav public/
cp -f assets/fonts/*.woff2 public/fonts/

echo "== normalize narration (-16 LUFS / -1.5 dBTP) =="
if [ ! -f assets/narration-normalized.wav ] || [ assets/narration.wav -nt assets/narration-normalized.wav ]; then
  # measured: I=-18.6 LUFS, TP=-1.2 dBFS, LRA=3.7 -> linear gain +2.6 dB with a true-peak-safe limiter
  ffmpeg -y -v error -i assets/narration.wav \
    -af "volume=2.6dB,alimiter=limit=0.8413:level=false:attack=5:release=80" \
    -ar 48000 -c:a pcm_s16le assets/narration-normalized.wav
fi
ffmpeg -hide_banner -nostats -i assets/narration-normalized.wav -af ebur128=peak=true -f null - 2>&1 | grep -E "I:|Peak:" | head -3
echo "== done =="
