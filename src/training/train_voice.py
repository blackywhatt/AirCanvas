import os
import librosa
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
import pickle

# --- Configuration ---
DATA_PATH = "voice_data"
MODEL_NAME = "voice_model.h5"
LABEL_NAME = "voice_labels.pickle"
SAMPLERATE = 16000
DURATION = 1.0

# --- 1. Feature Extraction Function ---
def extract_features(file_path):
    # Load audio (1 sec)
    audio, _ = librosa.load(file_path, sr=SAMPLERATE, duration=DURATION)
    # Ensure length is exact
    if len(audio) < SAMPLERATE:
        audio = np.pad(audio, (0, SAMPLERATE - len(audio)))
    
    # Create Mel-Spectrogram
    # n_mels=64 creates a 64-pixel high image
    spectrogram = librosa.feature.melspectrogram(y=audio, sr=SAMPLERATE, n_mels=64)
    # Convert to log scale (Decibels)
    log_spec = librosa.power_to_db(spectrogram, ref=np.max)
    return log_spec

# --- 2. Load Dataset ---
X, y = [], []
classes = sorted(os.listdir(DATA_PATH)) # Get folder names

print(f"Loading data for classes: {classes}")

for idx, label in enumerate(classes):
    class_path = os.path.join(DATA_PATH, label)
    for file in os.listdir(class_path):
        if file.endswith(".wav"):
            feat = extract_features(os.path.join(class_path, file))
            X.append(feat)
            y.append(idx)

X = np.array(X)
y = np.array(y)

# Add a "channel" dimension (required for CNN)
X = X[..., np.newaxis]

print(f"Data Loaded: {X.shape[0]} samples. Shape: {X.shape[1:]}")

# --- 3. Build the CNN Model ---
model = models.Sequential([
    layers.Conv2D(32, (3, 3), activation='relu', input_shape=(64, 32, 1)),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.MaxPooling2D((2, 2)),
    layers.Dropout(0.25),
    layers.Flatten(),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.5),
    layers.Dense(len(classes), activation='softmax')
])

model.compile(optimizer='adam', 
              loss='sparse_categorical_crossentropy', 
              metrics=['accuracy'])

# --- 4. Training ---
print("\nStarting Training...")
model.fit(X, y, epochs=30, batch_size=8, shuffle=True)

# --- 5. Save Everything ---
model.save(MODEL_NAME)
with open(LABEL_NAME, 'wb') as f:
    pickle.dump(classes, f)

print(f"\nSuccess! '{MODEL_NAME}' and '{LABEL_NAME}' have been created.")