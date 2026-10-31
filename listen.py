import os
import sounddevice as sd
import numpy as np
from scipy.signal import butter, lfilter
import socket

# --- Configuration ---
UDP_IP = "172.17.246.10"   # Pico IP (check the serial monitor if it changes)
UDP_PORT = 5005
FS = 16000                 # sample rate (16 kHz)
CUTOFF = 7500.0            # low-pass cutoff
BLOCKSIZE = 1024           # samples per packet (= 1024 bytes in int8)
GAIN = 1.0                 # raise it if the printed peak is too low (see below)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# --- Digital filter ---
def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    b, a = butter(order, cutoff / nyq, btype='low', analog=False)
    return b, a

b, a = butter_lowpass(CUTOFF, FS)
zi = np.zeros(max(len(a), len(b)) - 1)
peak_level = 0.0           # loudest sample since the last printout

# --- Real-time callback ---
def audio_callback(indata, frames, time_info, status):
    global zi, peak_level
    if status:
        print(status)

    # --- MUTE CHECK ---
    # إذا كان الكمبيوتر يتحدث، أرسل صمتاً للـ Pico ولا ترسل صوت المايك
    if os.path.exists("mute_mic"):
        silent_data = np.zeros(BLOCKSIZE, dtype=np.int8)
        try:
            sock.sendto(silent_data.tobytes(), (UDP_IP, UDP_PORT))
        except OSError:
            pass
        return
    # ------------------

    audio_chunk = indata[:, 0] * GAIN

    filtered, zi = lfilter(b, a, audio_chunk, zi=zi)

    peak_level = max(peak_level, float(np.max(np.abs(filtered))))

    quantized = np.rint(np.clip(filtered, -1.0, 1.0) * 127).astype(np.int8)

    try:
        sock.sendto(quantized.tobytes(), (UDP_IP, UDP_PORT))
    except OSError as e:
        print("Send error:", e)

print("Microphone open: listening, processing, streaming...")
print("Speak normally: the peak should reach about 0.2 - 0.8 (1.0 = clipping).")
print("(Press Ctrl+C to stop)")

try:
    with sd.InputStream(samplerate=FS, channels=1, dtype='float32',
                        blocksize=BLOCKSIZE, callback=audio_callback):
        while True:
            sd.sleep(1000)
            print(f"peak level: {peak_level:.2f}")
            peak_level = 0.0
except KeyboardInterrupt:
    print("\nStreaming stopped.")
