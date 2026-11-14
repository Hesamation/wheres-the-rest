#!/usr/bin/env python3
"""Transcribe narration.wav with word-level timestamps (local, faster-whisper).

Outputs:
  - assets/narration-timing.json  (segments + words, the sync backbone)
  - stdout transcript for comparison against narration-reference.txt
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

WHISPER_RATE = 16000

VIDEO = Path(__file__).resolve().parent.parent
WAV = VIDEO / "assets" / "narration.wav"
OUT = VIDEO / "assets" / "narration-timing.json"

MODEL_SIZE = sys.argv[1] if len(sys.argv) > 1 else "small.en"


def load_wav_f32(path: Path) -> np.ndarray:
    """Decode PCM16 mono WAV to float32 at 16 kHz without PyAV (av 19 broke decode_audio)."""
    with wave.open(str(path), "rb") as w:
        assert w.getnchannels() == 1, f"expected mono, got {w.getnchannels()} channels"
        rate = w.getframerate()
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    audio = samples.astype(np.float32) / 32768.0
    if rate != WHISPER_RATE:
        n_out = int(round(len(audio) * WHISPER_RATE / rate))
        audio = np.interp(
            np.linspace(0.0, len(audio) - 1, num=n_out),
            np.arange(len(audio)),
            audio,
        ).astype(np.float32)
    return audio


def main() -> None:
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    audio = load_wav_f32(WAV)
    segments_iter, info = model.transcribe(
        audio,
        language="en",
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=False,
        beam_size=5,
    )
    segments = []
    for seg in segments_iter:
        words = [
            {"w": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
            for w in seg.words
            if w.word.strip()
        ]
        segments.append(
            {
                "text": seg.text.strip(),
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "words": words,
            }
        )

    payload = {
        "source": "assets/narration.wav",
        "model": MODEL_SIZE,
        "language": info.language,
        "duration": round(info.duration, 3),
        "segments": segments,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")

    print(f"duration={info.duration:.2f}s  segments={len(segments)}  -> {OUT.relative_to(VIDEO)}")
    print("--- transcript ---")
    for seg in segments:
        print(f"[{seg['start']:7.2f} - {seg['end']:7.2f}] {seg['text']}")


if __name__ == "__main__":
    main()
