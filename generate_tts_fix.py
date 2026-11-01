import os
import asyncio
import edge_tts
import subprocess

# الفئات الجديدة فقط (4 إلى 20)
SENTENCES = {
    "4": "when were you created",
    "5": "can you play music",
    "6": "what time is it",
    "7": "what is your memory size",
    "8": "how is the weather",
    "9": "what can you do",
    "10": "good morning",
    "11": "good night",
    "15": "open the door",
    "16": "close the door",
    "17": "turn up the volume",
    "18": "turn down the volume",
    "19": "start listening",
    "20": "stop listening"
}

VOICES = ["en-US-AriaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural"]
RATES = ["+0%", "-10%", "+10%"]
PITCHES = ["+0Hz", "+10Hz"]

async def generate_audio(text, voice, rate, pitch, mp3_file, wav_file):
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(mp3_file)
    # تحويل إلى WAV بجودة 16kHz Mono
    subprocess.run(["ffmpeg", "-i", mp3_file, "-ar", "16000", "-ac", "1", wav_file, "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(mp3_file): os.remove(mp3_file)

async def main():
    base_dir = "my_tts_fix"
    os.makedirs(base_dir, exist_ok=True)

    for label, sentence in SENTENCES.items():
        class_dir = os.path.join(base_dir, label)
        os.makedirs(class_dir, exist_ok=True)
        print(f"Generating data for class {label}: '{sentence}'...")
        
        count = 0
        for voice in VOICES:
            for rate in RATES:
                for pitch in PITCHES:
                    mp3_file = os.path.join(class_dir, f"tts_{count:03d}.mp3")
                    wav_file = os.path.join(class_dir, f"tts_{count:03d}.wav")
                    try:
                        await generate_audio(sentence, voice, rate, pitch, mp3_file, wav_file)
                        count += 1
                    except Exception as e:
                        print(f"Error: {e}")
        print(f"  -> Generated {count} WAV samples.")

if __name__ == "__main__":
    asyncio.run(main())
