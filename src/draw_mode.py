import cv2
import numpy as np
from gesture_engine import get_gesture
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QInputDialog
import sys
import time

qt_app = QApplication.instance()
if not qt_app:
    qt_app = QApplication(sys.argv)

# ==============================
# DATA STORAGE (JSON READY)
# ==============================
strokes = []
current_stroke = []
current_session_file = None
last_autosave_time = time.time()
AUTOSAVE_INTERVAL = 10  # seconds
autosave_flash_time = 0
FLASH_DURATION = 2  # seconds
current_color = (220, 220, 220)
thickness = 2

# ==============================
# SESSION STORAGE
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_SRC = os.path.dirname(BASE_DIR)
SESSION_FOLDER = os.path.join(PROJECT_SRC, "sessions")
os.makedirs(SESSION_FOLDER, exist_ok=True)

# erase
erase_progress = 0
selected_index = -1

def draw_modern_eraser(frame, x, y, progress):
    cv2.circle(frame, (x, y), 25, (100, 100, 100), 2, cv2.LINE_AA)
    angle = int((progress / 100) * 360)
    cv2.ellipse(frame, (x, y), (25, 25), -90, 0, angle, (0, 0, 255), 3, cv2.LINE_AA)

def save_session(session_name=None):
    global current_session_file, last_autosave_time

    # If session already loaded → overwrite
    if current_session_file is not None:
        filename = current_session_file

    else:
        if not session_name or session_name.strip() == "":
            session_name = "session"

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"{session_name}_{timestamp}.json"

        current_session_file = filename

    path = os.path.join(SESSION_FOLDER, filename)

    data = {
        "mode": "free_draw",
        "strokes": strokes
    }

    with open(path, "w") as f:
        json.dump(data, f)

    print(f"[INFO] Session saved: {filename}")

def load_session(filename):
    global strokes, current_stroke, current_session_file

    path = os.path.join(SESSION_FOLDER, filename)

    if not os.path.exists(path):
        print("[ERROR] File not found")
        return

    with open(path, "r") as f:
        data = json.load(f)

    loaded_strokes = data.get("strokes", [])

    # convert color lists back to tuple
    for stroke in loaded_strokes:
        stroke["color"] = tuple(stroke["color"])

    strokes = loaded_strokes
    current_session_file = filename
    current_stroke = []

    print(f"[INFO] Session loaded: {filename}")

# auto-load session if provided by menu
if len(sys.argv) > 2 and sys.argv[1] == "--load":
    load_session(sys.argv[2])

def list_sessions():
    files = [f for f in os.listdir(SESSION_FOLDER) if f.endswith(".json")]
    files.sort()
    return files

# ==============================
# RENDER FUNCTION
# ==============================
def render_strokes(frame):
    for stroke in strokes:
        pts = np.array(stroke["points"], np.int32)
        cv2.polylines(frame, [pts], False,
                      stroke["color"], stroke["thickness"])

    if len(current_stroke) > 1:
        pts = np.array(current_stroke, np.int32)
        cv2.polylines(frame, [pts], False,
                      current_color, thickness)


cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)

window_name = "Free Draw Module"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

maximized = False

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (1280, 720))

    gesture, index_positions, thumb_positions, hand_count, frame = get_gesture(frame)
    if hand_count >= 1:
        ix, iy = index_positions[0]
    else:
        ix, iy = None, None

    if hand_count >= 1 and ix is not None:

        # =========================
        # ERASE TARGETING
        # =========================
        closest_dist = 40
        temp_idx = -1

        for i, stroke in enumerate(strokes):
            pts = np.array(stroke["points"])
            dists = np.linalg.norm(pts - [ix, iy], axis=1)
            if np.min(dists) < closest_dist:
                closest_dist = np.min(dists)
                temp_idx = i

        selected_index = temp_idx

        if gesture == "erase" and selected_index != -1:
            erase_progress += 6
            if erase_progress >= 100:
                strokes.pop(selected_index)
                erase_progress = 0
                selected_index = -1
        else:
            erase_progress = max(0, erase_progress - 8)

        # =========================
        # DRAW LOGIC
        # =========================
        if gesture == "draw":
            current_stroke.append((ix, iy))
        else:
            if len(current_stroke) > 2:
                strokes.append({
                    "points": current_stroke.copy(),
                    "color": current_color,
                    "thickness": thickness
                })
            current_stroke = []

        # =========================
        # CLEAR ALL
        # =========================
        if gesture == "clear":
            strokes.clear()
            current_stroke = []

    # =============================
    # RENDER
    # =============================
    render_strokes(frame)

    if erase_progress > 0:
        draw_modern_eraser(frame, ix, iy, erase_progress)

    cv2.putText(frame, "FREE DRAW MODE", (40, 60),
                cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 1, cv2.LINE_AA)

    # =============================
    # AUTOSAVE FLASH MESSAGE
    # =============================
    if time.time() - autosave_flash_time < FLASH_DURATION:
        cv2.putText(frame,
                    "Autosaved",
                    (40, 95),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA)

    cv2.imshow(window_name, frame)

    # =============================
    # AUTO SAVE SYSTEM
    # =============================
    current_time = time.time()

    if current_session_file is not None:
        if current_time - last_autosave_time > AUTOSAVE_INTERVAL:
            save_session()
            last_autosave_time = current_time
            autosave_flash_time = current_time

    key = cv2.waitKey(1) & 0xFF

    if key == ord('b'):
        break

    # =========================
    # SAVE SESSION (press S)
    # =========================
    if key == ord('s'):

        # Quick save if session already loaded
        if current_session_file is not None:
            save_session()

        else:
            name, ok = QInputDialog.getText(
                None,
                "Save Session",
                "Enter session name:"
            )

            if ok and name:
                save_session(name)

cap.release()
cv2.destroyAllWindows()