import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import logging
logging.getLogger('mediapipe').setLevel(logging.ERROR)

import cv2
import mediapipe as mp
import numpy as np
import tensorflow as tf
import pickle

# ==============================
# Load Model, Labels, Scaler
# ==============================
MODEL_PATH = "aircanvas_model.h5"
LABEL_PATH = "labels.pickle"
SCALER_PATH = "scaler.pickle"

if not os.path.exists(MODEL_PATH) or \
   not os.path.exists(LABEL_PATH) or \
   not os.path.exists(SCALER_PATH):
    raise FileNotFoundError("Model, label, or scaler file not found.")

model = tf.keras.models.load_model(MODEL_PATH)

with open(LABEL_PATH, "rb") as f:
    label_map = pickle.load(f)

with open(SCALER_PATH, "rb") as f:
    scaler = pickle.load(f)

frame_counter = 0
PREDICT_EVERY_N_FRAMES = 3
last_gesture = "idle"

# ==============================
# MediaPipe Setup
# ==============================
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=2,  # supports 2 hands
    model_complexity=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.4
)

# ==============================
# Gesture Detection Function
# ==============================
def get_gesture(frame):
    global frame_counter, last_gesture

    h, w, _ = frame.shape
    gesture_label = "idle"
    hand_count = 0

    index_positions = []  # store index finger positions
    thumb_positions = []  # store thumb positions
    landmarks_out = []

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb_frame.flags.writeable = False
    result = hands.process(rgb_frame)
    rgb_frame.flags.writeable = True

    if result.multi_hand_landmarks:
        hand_count = len(result.multi_hand_landmarks)

        for hl in result.multi_hand_landmarks:
            landmarks_out.append(hl)

            # Draw key landmarks
            for idx in [4, 8, 12, 16, 20]:
                px = int(hl.landmark[idx].x * w)
                py = int(hl.landmark[idx].y * h)
                cv2.circle(frame, (px, py), 4, (0, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(frame, (px, py), 8, (0, 255, 255), 1, cv2.LINE_AA)

            # index finger position
            ix = int(hl.landmark[8].x * w)
            iy = int(hl.landmark[8].y * h)
            index_positions.append((ix, iy))

            # thumb position
            tx = int(hl.landmark[4].x * w)
            ty = int(hl.landmark[4].y * h)
            thumb_positions.append((tx, ty))

            cv2.line(frame, (ix - 15, iy), (ix + 15, iy), (255, 255, 255), 1)
            cv2.line(frame, (ix, iy - 15), (ix, iy + 15), (255, 255, 255), 1)

        # ==============================
        # ML Classification ONLY if 1 hand
        # ==============================
        if hand_count == 1:
            hl = result.multi_hand_landmarks[0]
            base_x = hl.landmark[0].x
            base_y = hl.landmark[0].y

            lm_input = []
            for lm in hl.landmark:
                lm_input.extend([lm.x - base_x, lm.y - base_y])

            lm_input = scaler.transform([lm_input])

            frame_counter += 1

            if frame_counter % PREDICT_EVERY_N_FRAMES == 0:
                try:
                    pred = model.predict(lm_input, verbose=0)
                    last_gesture = label_map[np.argmax(pred)]
                except:
                    last_gesture = "idle"

            gesture_label = last_gesture

        else:
            # If 2 hands → depth mode (no ML)
            gesture_label = "two_hands"

    return gesture_label, index_positions, thumb_positions, hand_count, frame