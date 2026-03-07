import pandas as pd
import numpy as np
import tensorflow as tf
from keras import layers, models
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
import pickle
import os

DATA_PATH = 'gesture_data.csv'
if not os.path.exists(DATA_PATH):
    print(f"Error: {DATA_PATH} not found!")
    exit()

data = pd.read_csv(DATA_PATH, header=None)
X = data.iloc[:, :-1].values
y = data.iloc[:, -1].values

encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)

with open('labels.pickle', 'wb') as f:
    pickle.dump(encoder.classes_, f)

print(f"Labels found: {encoder.classes_}")

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y_encoded,
    test_size=0.2,
    random_state=42,
    stratify=y_encoded
)

# Normalize
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

with open('scaler.pickle', 'wb') as f:
    pickle.dump(scaler, f)

model = models.Sequential([
    layers.Input(shape=(42,)),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.3),
    layers.Dense(64, activation='relu'),
    layers.Dense(32, activation='relu'),
    layers.Dense(len(encoder.classes_), activation='softmax')
])

model.compile(
    optimizer='adam',
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

early_stop = tf.keras.callbacks.EarlyStopping(
    monitor='val_loss',
    patience=10,
    restore_best_weights=True
)

print("\nStarting Training...")
model.fit(
    X_train,
    y_train,
    epochs=100,
    batch_size=32,
    validation_data=(X_test, y_test),
    callbacks=[early_stop],
    verbose=1
)

loss, acc = model.evaluate(X_test, y_test, verbose=0)
print(f"\nTest Accuracy: {acc*100:.2f}%")

model.save('aircanvas_model.h5')
print("\n✅ Model saved as 'aircanvas_model.h5'")
print("✅ Labels saved as 'labels.pickle'")
print("✅ Scaler saved as 'scaler.pickle'")