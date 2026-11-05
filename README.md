# 🎙️ Pico 2 W Voice Chatbot (TinyML & Local Audio)

An end-to-end, low-latency Edge AI voice assistant built on the **Raspberry Pi Pico 2 W (RP2350)**. The host PC streams raw microphone audio over UDP to the Pico, where all Audio Signal Processing (Filtering, Quantization, STFT/FFT, and MFCC extraction) and TinyML Keyword Spotting (KWS) inference take place locally on-device in real-time.

## 🏗️ System Architecture & Data Flow

```
+-----------------------------------------------------------------------------------+
|                                      HOST PC                                      |
|                                                                                   |
|  [ Micro ] ---> (float32 PCM) ---[ UDP : Port 5005 ]---> [ UDP Receiver ]         |
|  [ mpv   ] <--- (int8 WAV)    <--[ UDP : Port 5007 ]---  [ Audio Engine ]         |
|  [ Terminal ] <--- (Plain Text) <--[ UDP : Port 5006 ]-- [ KWS Result   ]         |
+-----------------------------------------------------------------------|-----------+
                                                                        |
                                                                        v
+-----------------------------------------------------------------------------------+
|                              RASPBERRY PI PICO 2 W (RP2350)                       |
|                                                                                   |
|  1. Audio LPF      : Butterworth Low-Pass Filter (Anti-aliasing & Noise filter)   |
|  2. Quantization   : Local float32 -> int8 conversion                             |
|  3. Spectral DSP   : STFT / FFT -> Mel-Frequency Cepstral Coefficients (MFCC)     |
|  4. TinyML KWS     : Depthwise Separable CNN (DS-CNN via TensorFlow Lite Micro)   |
|  5. Action Driver  : Triggers onboard GPIO / Returns WAV audio array to PC        |
+-----------------------------------------------------------------------------------+
```

## 🛠️ Key Technical Features

* **On-Device Audio DSP Pipeline:** Full C++ implementation of Butterworth Low-Pass Filtering, float32 to int8 quantization, FFT, and 13-band MFCC feature extraction running directly on the RP2350 micro-architecture.

* **TinyML Keyword Spotting (KWS):** Executes a quantized Depthwise Separable CNN (DS-CNN) locally using **TensorFlow Lite Micro** (`pico-tflmicro`).

* **Low-Latency Network Stack:** Real-time raw UDP streaming optimized via custom `lwipopts.h` settings.

* **Embedded Audio Engine:** Pre-recorded voice responses stored as 8-bit WAV byte arrays (`audio_data.h`) and transmitted via UDP to the host media player (`mpv`).

* **Echo Suppression:** Automated microphone muting on the PC during response playback to prevent acoustic feedback loops.

## 📂 Repository Structure

```
.
├── streaming.cpp          # Main Pico firmware entry point (Audio DSP + TFLM pipeline)
├── fft.h, mfcc.h          # Audio Signal Processing algorithms (FFT & MFCC)
├── kws.h, model.h         # TinyML model wrapper and quantized weights
├── lwipopts.h             # LwIP network configuration tuned for real-time UDP streams
├── audio_data.h           # Pre-recorded human audio responses converted to C arrays
├── listen.py              # PC Client: Captures microphone audio & streams via UDP
├── pc_receiver.py         # PC Server: Listens for text/audio results and triggers mpv
├── wav_to_header.py       # Utility: Converts raw .wav files into C header arrays
├── record_10_voices.py    # Utility: Automation script to record new response voices
└── run_all.sh             # One-click launch script for PC client & receiver
```

> **Note on Audio Files:** Raw `.wav` audio recordings are intentionally excluded from the repository via `.gitignore` to keep the repository lightweight. The embedded firmware uses the generated `audio_data.h` C byte arrays directly.

## 🛠️ Prerequisites & Setup

### Hardware Requirements

* **Raspberry Pi Pico 2 W** (RP2350 with CYW43439 Wi-Fi chip)

* Host PC running Linux/macOS with built-in Microphone and Speakers

* Micro-USB / USB-C data cable

### Software Dependencies

* **Pico SDK** (Ensure `PICO_SDK_PATH` environment variable is exported)

* **ARM GNU Toolchain** (`arm-none-eabi-gcc`) & **CMake** (v3.13+)

* **TensorFlow Lite Micro** (Cloned at project root as `pico-tflmicro`)

* **Python 3.8+** with `venv`

* **mpv** audio player:
  * **Arch Linux / EndeavourOS:** `sudo pacman -S mpv`
  * **Debian / Ubuntu:** `sudo apt install mpv`

## 🔒 Configuration (Missing Header File)

For security reasons, Wi-Fi credentials are excluded from the repository. You must manually create `wifi_config.h` in the project root before compiling:

```cpp
#ifndef WIFI_CONFIG_H
#define WIFI_CONFIG_H

#define WIFI_SSID "YOUR_WIFI_NAME"
#define WIFI_PASS "YOUR_WIFI_PASSWORD"

#endif // WIFI_CONFIG_H
```

## 🚀 Build & Execution Guide

### 1. Build Pico 2 W Firmware

```bash
cd ~/chatboot
mkdir -p build && cd build
cmake ..
make -j8 streaming
```

*Flash the generated `streaming.uf2` to your Pico 2 W by entering BOOTSEL mode.*

### 2. Configure Host PC Environment

```bash
cd ~/chatboot
python3 -m venv venv
source venv/bin/activate
pip install sounddevice scipy numpy
```

### 3. Launch System

Run the host streamer and receiver scripts simultaneously:

```bash
chmod +x run_all.sh
./run_all.sh
```

> **Firewall Note:** `run_all.sh` automatically configures Linux `iptables` firewall rules prior to execution to ensure incoming UDP streams on ports 5006 and 5007 are not dropped by system security policies.

## 🗣️ Supported Voice Commands

| Spoken Command | Triggered Pico Action | Audio / Hardware Output | 
| ----- | ----- | ----- | 
| `"hello how are you"` | Intent #1 Identified | Plays `v1.wav` | 
| `"tell me about yourself"` | Intent #2 Identified | Plays `v4.wav` | 
| `"what is your name"` | Intent #3 Identified | Plays `v7.wav` | 
| `"blink the LED"` | Drives GPIO Sequence | Blinks Onboard Pico LED | 
| `"turn on the LED"` | Drives GPIO High | Onboard LED ON | 
| `"turn off the LED"` | Drives GPIO Low | Onboard LED OFF | 

## 🚧 Development Status & Future Roadmap

* [x] Real-time float32 raw audio streaming over UDP (PC $\rightarrow$ Pico).
* [x] On-device Butterworth Low-Pass Filter & INT8 Quantization on RP2350.
* [x] Local STFT / FFT & MFCC feature extraction pipeline.
* [x] TensorFlow Lite Micro DS-CNN model execution.
* [x] Automated host echo suppression during response playback.
* [ ] **Dataset Expansion:** Retrain the DS-CNN model with broader acoustic samples to fix inter-class confusion between `"hello"` and `"about"`.
* [ ] **Local LLM Fallback:** Emit an `UNKNOWN` packet over UDP when KWS confidence drops below threshold to trigger host-side Whisper + Ollama pipeline.
* [ ] **Hardware Standalone Mode:** Migrate from PC UDP audio to direct I2S Microphone (INMP441) and I2S DAC (MAX98357A) hardware interface.