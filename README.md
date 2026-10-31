# 🎙️ Pico 2 W Voice Chatbot (TinyML & Local Audio)

A voice assistant project built around the **Raspberry Pi Pico 2 W (RP2350 + Wi-Fi)**.  
The PC captures raw microphone audio and streams it to the Pico. The Pico then performs the **Audio DSP (Low-pass Filter + Quantization + FFT + MFCC)** and runs a local TinyML model to recognize specific sentences. Finally, the Pico sends the recognized text and a pre-recorded human voice response back to the PC.

---

## 🏗️ System Architecture & Data Flow

1. **PC (Ear):** Captures raw microphone audio as `float32` and streams it via UDP to the Pico (Port `5005`).
2. **Pico (Brain - DSP):** Receives `float32` audio, applies a **Butterworth Low-pass Filter**, and performs **Quantization (float32 to int8)** locally.
3. **Pico (Brain - AI):** Runs FFT $\rightarrow$ MFCC $\rightarrow$ TinyML model (DS-CNN) to recognize 6 specific sentences.
4. **Pico (Mouth):** Sends the recognized text (UDP Port `5006`) and the audio answer file (UDP Port `5007`) to the PC.
5. **PC (Speaker):** Reassembles the audio packets and plays them using `mpv`. (Mic is muted during playback to prevent echo).

---

## 🛠️ Prerequisites

### Hardware
- Raspberry Pi Pico 2 W
- PC with Microphone and Speakers

### Software
- **Pico SDK** (ensure `PICO_SDK_PATH` is set)
- **TensorFlow Lite Micro** (`pico-tflmicro` cloned in the project root)
- **Python 3** (with a virtual environment `venv`)
- **mpv** (for audio playback on Linux)
- **Python Packages:** `sounddevice`, `scipy`, `numpy`

---

## ⚠️ IMPORTANT SETUP (Missing File)

The `wifi_config.h` file is excluded from this repository for security reasons.  
**You must create it manually** in the project root before building the Pico firmware:

```c
// Create a file named wifi_config.h and add your credentials:
#define WIFI_SSID    "YOUR_WIFI_NAME"
#define WIFI_PASS    "YOUR_WIFI_PASSWORD"
```

---

## 🚀 How to Build & Run

### 1. Build the Pico Firmware
```bash
cd ~/chatboot/build
cmake ..
make streaming
```

### 2. Setup PC Environment
```bash
cd ~/chatboot
python -m venv venv
source venv/bin/activate
pip install sounddevice scipy numpy
```

### 3. Run the System
You can start everything with the provided script:
```bash
./run_all.sh
```

---

## 🗣️ Supported Commands

| Spoken Command | System Action |
| :--- | :--- |
| `"hello how are you"` | Plays `v1.wav` |
| `"tell me about yourself"` | Plays `v4.wav` |
| `"what is your name"` | Plays `v7.wav` |
| `"blink the LED"` | Blinks the Pico LED |
| `"turn on the LED"` | LED ON |
| `"turn off the LED"` | LED OFF |

---

## ⚠️ Current Status & Next Steps (For the next developer)

### ✅ What works perfectly
- Audio streaming PC $\rightarrow$ Pico (raw `float32`).
- Pico handles all DSP locally (Filtering, Quantization, FFT, MFCC).
- UDP text and audio packet transmission Pico $\rightarrow$ PC.
- Audio playback and echo cancellation.

### 🚧 What needs fixing/improving
- **Model Accuracy for "hello" and "about":** The TinyML model sometimes confuses "hello" with "about". It needs to be retrained with more diverse samples.
- **Unknown Fallback (Local LLM):** If the Pico hears an unknown sentence, it does nothing. The next step is to send an `UNKNOWN` signal to the PC to trigger Whisper + Ollama.
- **Hardware Upgrade (I2S):** Connect an I2S Mic and Speaker directly to the Pico for standalone operation (since the Pico now handles filtering and quantization locally).

---

## 📂 Project Structure

```text
├── streaming.cpp        # Main Pico firmware (DSP + AI)
├── fft.h, mfcc.h        # Audio DSP processing
├── kws.h, model.h       # TinyML model
├── lwipopts.h           # Network config (optimized for float32 UDP)
├── audio_data.h         # 8-bit WAV files converted to C arrays
├── listen.py            # PC mic -> UDP streamer (float32)
├── pc_receiver.py       # Receives text & audio, plays audio
├── wav_to_header.py     # Converts .wav to audio_data.h
├── record_10_voices.py  # Records new voice answers
└── run_all.sh           # One-click script to run everything
```

---

## 📤 Pushing Changes to GitHub

```bash
cd ~/chatboot
git add .
git commit -m "Major Update: Moved Audio Filtering & Quantization to Pico (float32 streaming) + Updated README"
git push origin main
```