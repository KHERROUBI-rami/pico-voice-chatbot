"""
Record training samples for the sentence model (PC side).

Usage:   python record_samples.py [takes_per_sentence]      (default 40)

Files are saved as my_data/<id>/take_<time>.wav  (16 kHz, mono, 16-bit, 2.5 s).
You can stop at any time and run it again: it continues where you stopped.
"""
import os
import sys
import time

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

FS = 16000
CLIP_S = 2.5
OUT_DIR = "my_data"
GAIN = 1.0          # use the SAME value as GAIN in listen.py / assistant.py

SENTENCES = [
    ("hello",   "hello how are you"),
    ("about",   "tell me about yourself"),
    ("name",    "what is your name"),
    ("blink",   "blink the LED"),
    ("on",      "turn on the LED"),
    ("off",     "turn off the LED"),
    ("unknown", "ANY OTHER sentence (different every time), or just noise / silence"),
]

def count_wavs(folder):
    if not os.path.isdir(folder):
        return 0
    return len([f for f in os.listdir(folder) if f.endswith(".wav")])

def record_one():
    audio = sd.rec(int(CLIP_S * FS), samplerate=FS, channels=1, dtype="float32")
    sd.wait()
    audio = np.clip(audio[:, 0] * GAIN, -1.0, 1.0)
    return audio

def main():
    takes = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    os.makedirs(OUT_DIR, exist_ok=True)

    for idx, (slug, text) in enumerate(SENTENCES, start=1):
        folder = os.path.join(OUT_DIR, slug)
        os.makedirs(folder, exist_ok=True)
        target = takes * 2 if slug == "unknown" else takes

        while count_wavs(folder) < target:
            n = count_wavs(folder)
            cmd = input(f'[{idx}/{len(SENTENCES)}] "{text}"  ({n}/{target})   '
                        f'Enter = record, s = skip, q = quit > ').strip().lower()
            if cmd == "q":
                print("Saved. Run the script again to continue.")
                return
            if cmd == "s":
                break

            print("   Speak now...")
            audio = record_one()
            peak = float(np.max(np.abs(audio)))
            wavfile.write(os.path.join(folder, f"take_{int(time.time() * 1000)}.wav"),
                          FS, (audio * 32767).astype(np.int16))
            note = ""
            if slug != "unknown" and peak < 0.03:
                note = "   (very quiet! speak louder or closer)"
            print(f"   saved, peak {peak:.2f}{note}")

    print("Done. All sentences recorded.")

if __name__ == "__main__":
    main()
