import os
import time
import numpy as np
import sounddevice as sd
from scipy.io import wavfile

FS = 16000
DURATION = 2.5
GAIN = 1.0

# الجمل الـ 14 الجديدة فقط
SENTENCES = [
    ("4", "when were you created"),
    ("5", "can you play music"),
    ("6", "what time is it"),
    ("7", "what is your memory size"),
    ("8", "how is the weather"),
    ("9", "what can you do"),
    ("10", "good morning"),
    ("11", "good night"),
    ("15", "open the door"),
    ("16", "close the door"),
    ("17", "turn up the volume"),
    ("18", "turn down the volume"),
    ("19", "start listening"),
    ("20", "stop listening")
]

print("=== Recording 3 samples per sentence ===")
print("Please speak clearly and keep peak level between 0.2 and 0.8.\n")

for label_id, text in SENTENCES:
    os.makedirs(f"my_real_voice/{label_id}", exist_ok=True)
    
    for take in range(1, 4):
        print(f"\nClass {label_id} | Take {take}/3")
        print(f"Please say: \"{text}\"")
        
        for count in [3, 2, 1]:
            print(f"Starting in {count}...")
            time.sleep(1)
        
        print("🔴 RECORDING NOW...")
        audio = sd.rec(int(DURATION * FS), samplerate=FS, channels=1, dtype="float32")
        sd.wait()
        
        audio = np.clip(audio[:, 0] * GAIN, -1.0, 1.0)
        peak = float(np.max(np.abs(audio)))
        
        filename = f"my_real_voice/{label_id}/take_{take}.wav"
        wavfile.write(filename, FS, (audio * 32767).astype(np.int16))
        
        print(f"✅ Saved {filename} | Peak: {peak:.3f}")
        if peak > 0.9:
            print("⚠️ Warning: Clipping! Speak a bit further from the mic next time.")
        elif peak < 0.1:
            print("⚠️ Warning: Too quiet! Speak louder.")

print("\n🎉 All recordings finished! Now compress the folder to upload:")
print("tar czf my_real_voice.tar.gz my_real_voice")
