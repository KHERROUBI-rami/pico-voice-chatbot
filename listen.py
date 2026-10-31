import os
import sounddevice as sd
import numpy as np
import socket

# --- Configuration ---
UDP_IP = "172.17.246.10"
UDP_PORT = 5005
FS = 16000
BLOCKSIZE = 1024
GAIN = 1.0

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
peak_level = 0.0

def audio_callback(indata, frames, time_info, status):
    global peak_level
    if status:
        print(status)

    # إذا كان الكمبيوتر يتحدث، أرسل صمتاً (float32)
    if os.path.exists("mute_mic"):
        silent_data = np.zeros(BLOCKSIZE, dtype=np.float32)
        try:
            sock.sendto(silent_data.tobytes(), (UDP_IP, UDP_PORT))
        except OSError:
            pass
        return

    audio_chunk = indata[:, 0] * GAIN
    peak_level = max(peak_level, float(np.max(np.abs(audio_chunk))))

    # إرسال الصوت الخام float32 كما هو
    try:
        sock.sendto(audio_chunk.astype(np.float32).tobytes(), (UDP_IP, UDP_PORT))
    except OSError as e:
        print("Send error:", e)

print("Microphone open: sending raw float32 to Pico...")
try:
    with sd.InputStream(samplerate=FS, channels=1, dtype='float32',
                        blocksize=BLOCKSIZE, callback=audio_callback):
        while True:
            sd.sleep(1000)
            print(f"peak level: {peak_level:.2f}")
            peak_level = 0.0
except KeyboardInterrupt:
    print("\nStreaming stopped.")
