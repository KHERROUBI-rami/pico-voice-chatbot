import os
import wave
import numpy as np

# الملفات من v1 إلى v10
files = [f"v{i}.wav" for i in range(1, 11)]

with open("audio_data.h", "w") as f:
    f.write("// Auto-generated audio data for Pico\n")
    f.write("#pragma once\n\n")
    
    for filename in files:
        if not os.path.exists(filename):
            print(f"Warning: {filename} not found, skipping.")
            continue
            
        with wave.open(filename, 'rb') as wav:
            if wav.getframerate() != 16000 or wav.getnchannels() != 1:
                print(f"Error: {filename} must be 16000 Hz and Mono.")
                continue
                
            # قراءة الصوت 16-bit
            frames = wav.readframes(wav.getnframes())
            audio_int16 = np.frombuffer(frames, dtype=np.int16)
            
            # تحويل من 16-bit إلى 8-bit (unsigned)
            audio_uint8 = ((audio_int16 >> 8) + 128).astype(np.uint8)
            frames_8bit = audio_uint8.tobytes()
            
            var_name = filename.replace(".wav", "")
            
            f.write(f"const unsigned char audio_{var_name}[] = {{\n")
            for i, byte in enumerate(frames_8bit):
                f.write(f"0x{byte:02X}, ")
                if (i + 1) % 16 == 0:
                    f.write("\n")
            f.write("\n};\n")
            f.write(f"const unsigned int audio_{var_name}_len = {len(frames_8bit)};\n\n")
            print(f"Processed {filename} -> {len(frames_8bit)} bytes")

print("\nDone! audio_data.h created.")
