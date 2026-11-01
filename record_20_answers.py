import os
import time
import numpy as np
import sounddevice as sd
from scipy.io import wavfile

FS = 16000
DURATION = 3.0
GAIN = 1.0

# قائمة الجمل وردودها المقترحة
SENTENCES = [
    ("v1.wav", "Say: Hello, I am fine, thank you."),
    ("v2.wav", "Say: My name is Pico Bot."),
    ("v3.wav", "Say: I am a smart voice assistant."),
    ("v4.wav", "Say: I was created just recently."),
    ("v5.wav", "Say: I cannot play music yet."),
    ("v6.wav", "Say: I do not have a clock."),
    ("v7.wav", "Say: I have 520 kilobytes of RAM."),
    ("v8.wav", "Say: I do not know the weather."),
    ("v9.wav", "Say: I can control LEDs and answer questions."),
    ("v10.wav", "Say: Good morning to you too."),
    ("v11.wav", "Say: Good night, sleep well."),
    ("v12.wav", "Say: Turning on the LED."),
    ("v13.wav", "Say: Turning off the LED."),
    ("v14.wav", "Say: Blinking the LED."),
    ("v15.wav", "Say: I cannot open the door."),
    ("v16.wav", "Say: I cannot close the door."),
    ("v17.wav", "Say: Increasing the volume."),
    ("v18.wav", "Say: Decreasing the volume."),
    ("v19.wav", "Say: I am listening."),
    ("v20.wav", "Say: Stopping listening.")
]

print("=== Recording 20 Voice Answers ===")
print("Make sure your microphone is connected.\n")

for filename, instruction in SENTENCES:
    if os.path.exists(filename):
        print(f"File {filename} already exists, skipping.")
        continue

    print(f"\n--- Recording {filename} ---")
    print(instruction)
    
    for count in [3, 2, 1]:
        print(f"Starting in {count}...")
        time.sleep(1)
    
    print("🔴 RECORDING NOW...")
    
    audio = sd.rec(int(DURATION * FS), samplerate=FS, channels=1, dtype="float32")
    sd.wait()
    
    audio = np.clip(audio[:, 0] * GAIN, -1.0, 1.0)
    peak = float(np.max(np.abs(audio)))
    
    wavfile.write(filename, FS, (audio * 32767).astype(np.int16))
    
    print(f"✅ Saved {filename} | Peak level: {peak:.3f}")
    if peak < 0.1:
        print("⚠️ Warning: Audio is too quiet!")
        
    print("-" * 30)

print("\n🎉 All 20 answers recorded! You can now run wav_to_header.py")
