"""
Record background clips for the "unknown" class (PC side), no keypress needed.

Usage:   python record_noise.py <mode> [clips]        (default 40 clips)

  silence : stay quiet (only your room noise is recorded)
  noise   : make normal desk noises: type, move the chair, cough, open a drawer
  talk    : speak ordinary sentences (NOT the 6 command sentences)

Each clip is 2.5 s, saved into my_data/unknown/ so train_sentences.py uses it.
Use the same microphone, distance and GAIN as in real use.
"""
import os
import sys
import time

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

FS = 16000
CLIP_S = 2.5
OUT_DIR = os.path.join("my_data", "unknown")
GAIN = 1.0          # use the SAME value as GAIN in listen.py

HINTS = {
    "silence": "Stay quiet. Do not speak or move much.",
    "noise":   "Make normal noises: type on the keyboard, move the chair, cough, open a drawer...",
    "talk":    "Speak ordinary sentences (any topic, English or Arabic), but NOT the 6 commands.",
}

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "silence"
    clips = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    if mode not in HINTS:
        print("mode must be one of: silence, noise, talk")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"\nMode: {mode}. {HINTS[mode]}")
    for i in (3, 2, 1):
        print(f"Starting in {i}...")
        time.sleep(1)

    for i in range(clips):
        audio = sd.rec(int(CLIP_S * FS), samplerate=FS, channels=1, dtype="float32")
        sd.wait()
        audio = np.clip(audio[:, 0] * GAIN, -1.0, 1.0)
        peak = float(np.max(np.abs(audio)))
        path = os.path.join(OUT_DIR, f"{mode}_{int(time.time() * 1000)}.wav")
        wavfile.write(path, FS, (audio * 32767).astype(np.int16))
        print(f"  {i + 1}/{clips} saved, peak {peak:.3f}")

    print("Done.")

if __name__ == "__main__":
    main()
