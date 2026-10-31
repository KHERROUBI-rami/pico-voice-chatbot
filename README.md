# 🎙️ Pico 2 W Voice Chatbot (TinyML & Local Audio)

A voice assistant project built around the **Raspberry Pi Pico 2 W (RP2350 + Wi-Fi)**. 
The PC captures audio and streams it to the Pico, which runs a local TinyML model to recognize specific sentences. The Pico then sends the recognized text and a pre-recorded human voice response back to the PC to be played through the speakers.

## 🏗️ System Architecture & Data Flow

1. **PC (Ear):** Captures microphone audio, filters it, quantizes it to `int8`, and streams it via UDP to the Pico (Port `5005`).
2. **Pico (Brain):** Runs DSP (FFT -> MFCC) and a TinyML model (DS-CNN) to recognize 6 specific sentences.
3. **Pico (Mouth):** Sends the recognized text (UDP Port `5006`) and the corresponding audio answer file (UDP Port `5007` in 512-byte packets) back to the PC.
4. **PC (Speaker):** Reassembles the audio packets and plays them using `mpv`. During playback, the microphone is muted (via a `mute_mic` file) to prevent echo and feedback loops.

## 🛠️ Prerequisites

### Hardware
* Raspberry Pi Pico 2 W
* PC with Microphone and Speakers

### Software
* **Pico SDK** (ensure `PICO_SDK_PATH` is set)
* **TensorFlow Lite Micro** (`pico-tflmicro` cloned in the project root)
* **Python 3** (with a virtual environment `venv`)
* **mpv** (for audio playback on Linux)
* **Python Packages:** `sounddevice`, `scipy`, `numpy`

## ⚠️ IMPORTANT SETUP (Missing File)

The `wifi_config.h` file is excluded from this repository for security reasons (to protect your Wi-Fi credentials). 
**You must create it manually** in the project root before building the Pico firmware:

```c
// Create a file named wifi_config.h and add your credentials:
#define WIFI_SSID    "YOUR_WIFI_NAME"
#define WIFI_PASS    "YOUR_WIFI_PASSWORD"
```

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
*Alternatively, run the components manually in two separate terminals:*
* **Terminal 1:** `python pc_receiver.py`
* **Terminal 2:** `python listen.py`

## 🗣️ Supported Commands

Say one of these sentences to trigger a response:

| Spoken Command | System Action |
| :--- | :--- |
| `"hello how are you"` | Plays `v1.wav` |
| `"tell me about yourself"`| Plays `v4.wav` |
| `"what is your name"` | Plays `v7.wav` |
| `"blink the LED"` | Blinks the Pico LED |
| `"turn on the LED"` | LED ON |
| `"turn off the LED"`| LED OFF |

## 🎙️ How to Record New Voices

If you want to change the voice answers:
1. Run: `python record_10_voices.py` (records 10 new `.wav` files).
2. Run: `python wav_to_header.py` (converts them to `audio_data.h`).
3. Rebuild the Pico firmware (`cd build && make streaming`) and re-flash it to the board.

## ⚠️ Current Status & Next Steps (For the next developer)

### ✅ What works perfectly
* Audio streaming PC -> Pico.
* UDP text and audio packet transmission Pico -> PC.
* Audio playback and echo cancellation (mute logic).
* Core commands: *what is your name, blink, on, off*.

### 🚧 What needs fixing/improving
* **Model Accuracy for "hello" and "about":** The TinyML model sometimes confuses "hello" with "about". It needs to be retrained with more diverse samples (using Edge Impulse or Google Colab) to improve accuracy. The training script is `train_sentences_v3.py`.
* **Unknown Fallback (Local LLM):** Currently, if the Pico hears an unknown sentence, it does nothing. The next step is to modify `streaming.cpp` to send an `UNKNOWN` signal to the PC. A Python script can then use Whisper (Speech-to-Text) and Ollama (Local LLM) to generate and speak an answer.
* **Hardware Upgrade (I2S):** Currently, the PC handles the Mic and Speaker. The final goal is to connect an I2S Mic (e.g., INMP441) and I2S Speaker (e.g., MAX98357A) directly to the Pico for standalone operation.

## 📂 Project Structure

```text
├── streaming.cpp        # Main Pico firmware
├── fft.h, mfcc.h        # Audio DSP processing
├── kws.h, model.h       # TinyML model (Keyword Spotting)
├── audio_data.h         # 8-bit WAV files converted to C arrays (v1-v10)
├── listen.py            # PC mic -> UDP streamer
├── pc_receiver.py       # Receives text & audio from Pico, plays audio
├── wav_to_header.py     # Converts .wav files into audio_data.h
├── record_10_voices.py  # Script to record new voice answers
└── run_all.sh           # One-click script to run everything
```