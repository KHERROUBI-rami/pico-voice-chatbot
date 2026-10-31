import os
import time
import numpy as np
import sounddevice as sd
from scipy.io import wavfile

FS = 16000
DURATION = 3.0
GAIN = 1.0

SENTENCES = [
    "Hello, I am your Pico robot.",
    "I am working perfectly today.",
    "This is the third audio test.",
    "مرحباً، أنا الروبوت الخاص بك.",
    "أنا أسمعك بوضوح تام.",
    "Testing the new audio streaming feature.",
    "My name is Pico, nice to meet you.",
    "اسمي بيكو، وتشرفت بمعرفتك.",
    "The network is fast and stable.",
    "Goodbye for now, see you later!"
]

print("=== 10 Voice Recording Script ===")
print("Make sure your microphone is connected and working.\n")

for i in range(10):
    filename = f"v{i+1}.wav"
    if os.path.exists(filename):
        print(f"File {filename} already exists, skipping.")
        continue

    print(f"\n--- Recording {filename} ---")
    print(f"Please say: \"{SENTENCES[i]}\"")
    
    for count in [3, 2, 1]:
        print(f"Starting in {count}...")
        time.sleep(1)
    
    print("🔴 RECORDING NOW...")
    
    # تسجيل الصوت
    audio = sd.rec(int(DURATION * FS), samplerate=FS, channels=1, dtype="float32")
    sd.wait()
    
    # معالجة الصوت
    audio = np.clip(audio[:, 0] * GAIN, -1.0, 1.0)
    peak = float(np.max(np.abs(audio)))
    
    # الحفظ بصيغة int16 WAV (المطلوبة للـ Pico)
    wavfile.write(filename, FS, (audio * 32767).astype(np.int16))
    
    print(f"✅ Saved {filename} | Peak level: {peak:.3f}")
    if peak < 0.1:
        print("⚠️ Warning: Audio is too quiet! Please speak louder next time.")
    elif peak >= 0.99:
        print("⚠️ Warning: Audio clipped (too loud). Try moving away from the mic.")
        
    print("-" * 30)

print("\n🎉 All recordings finished! You can now run wav_to_header.py")
