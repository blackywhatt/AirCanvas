import sounddevice as sd
from scipy.io.wavfile import write
import os
import time

COMMANDS = ["circle", "square", "triangle", "red", "green", "blue", "clear", "background"]
SAMPLES_PER_COMMAND = 50 
SAMPLERATE = 16000
DURATION = 1.0
DATA_PATH = "voice_data"

if not os.path.exists(DATA_PATH): os.makedirs(DATA_PATH)

for label in COMMANDS:
    label_path = os.path.join(DATA_PATH, label)
    if not os.path.exists(label_path): os.makedirs(label_path)
    
    print(f"\n--- NEXT COMMAND: {label.upper()} ---")
    time.sleep(2)
    
    for i in range(SAMPLES_PER_COMMAND):
        print(f"Recording {label} #{i+1}/50... SPEAK!")
        # If label is 'background', remind user to be quiet
        if label == "background": print("(STAY SILENT...)")
        
        recording = sd.rec(int(DURATION * SAMPLERATE), samplerate=SAMPLERATE, channels=1, dtype='float32')
        sd.wait()
        write(os.path.join(label_path, f"{label}_{i}.wav"), SAMPLERATE, recording)
        time.sleep(0.2)