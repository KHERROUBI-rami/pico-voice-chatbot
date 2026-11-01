import os
import asyncio
import edge_tts

# قائمة الجمل العشرين (بالترتيب من 1 إلى 20)
SENTENCES = [
    "hello how are you",          # 1
    "what is your name",          # 2
    "tell me about yourself",     # 3
    "when were you created",      # 4
    "can you play music",         # 5
    "what time is it",            # 6
    "what is your memory size",   # 7
    "how is the weather",         # 8
    "what can you do",            # 9
    "good morning",               # 10
    "good night",                 # 11
    "turn on the led",            # 12
    "turn off the led",           # 13
    "blink the led",              # 14
    "open the door",              # 15
    "close the door",             # 16
    "turn up the volume",         # 17
    "turn down the volume",       # 18
    "start listening",            # 19
    "stop listening"              # 20
]

# أصوات مختلفة (رجال، نساء، لهجات) لتوليد تنوع في البيانات
VOICES = [
    "en-US-AriaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural", 
    "en-GB-RyanNeural", "en-AU-NatashaNeural", "en-CA-ClaraNeural"
]

# إعدادات النبرة والسرعة لتوليد تنوع إضافي
RATES = ["+0%", "-10%", "+10%", "-20%"]
PITCHES = ["+0Hz", "+10Hz", "-10Hz"]

async def generate_audio(text, voice, rate, pitch, output_file):
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_file)

async def main():
    base_dir = "my_data_v20"
    os.makedirs(base_dir, exist_ok=True)

    for i, sentence in enumerate(SENTENCES, start=1):
        class_dir = os.path.join(base_dir, str(i))
        os.makedirs(class_dir, exist_ok=True)
        print(f"Generating data for class {i}: '{sentence}'...")
        
        count = 0
        for voice in VOICES:
            for rate in RATES:
                for pitch in PITCHES:
                    filename = os.path.join(class_dir, f"tts_{count:03d}.wav")
                    try:
                        await generate_audio(sentence, voice, rate, pitch, filename)
                        count += 1
                    except Exception as e:
                        print(f"Error: {e}")
        
        print(f"  -> Generated {count} samples.")

    # نسخ بيانات الـ unknown من المجلد القديم (إذا وجدت)
    print("Copying 'unknown' data from previous dataset...")
    os.system(f"cp -r my_data/unknown {base_dir}/0 2>/dev/null")
    
    print("\nDone! Dataset 'my_data_v20' is ready.")

if __name__ == "__main__":
    asyncio.run(main())
