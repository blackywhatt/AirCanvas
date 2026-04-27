import cv2
import numpy as np
from gesture_engine import get_gesture
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QInputDialog
import sys
import time
from PIL import ImageFont, ImageDraw, Image


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
SESSION_FOLDER = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSION_FOLDER, exist_ok=True)
FONT_DIR = os.path.join(BASE_DIR, "fonts")

# erase
erase_progress = 0
clear_progress = 0
selected_index = -1
lost_hand_frames = 0
MAX_LOST_FRAMES = 5
last_raw_gesture = "idle"
stable_gesture = "idle"
same_gesture_frames = 0
smooth_ix = None
smooth_iy = None

def draw_text(frame, text, pos, size=40, color=(255,255,255),
              font_name="Montserrat-Medium.ttf", center=False):

    font_path = os.path.join(FONT_DIR, font_name)

    img_pil = Image.fromarray(frame)
    draw = ImageDraw.Draw(img_pil)

    try:
        font = ImageFont.truetype(font_path, size)
    except:
        font = ImageFont.load_default()

    if center:
        w = frame.shape[1]
        bbox = draw.textbbox((0,0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (w - text_w)//2
        draw.text((x, pos[1]), text, font=font, fill=color)
    else:
        draw.text(pos, text, font=font, fill=color)

    return np.array(img_pil)

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

    # Lightweight gesture stabilizer
    if gesture == last_raw_gesture:
        same_gesture_frames += 1
    else:
        same_gesture_frames = 0
        last_raw_gesture = gesture

    if same_gesture_frames >= 1:
        stable_gesture = gesture
    
    if hand_count >= 1:
        raw_x, raw_y = index_positions[0]

        if smooth_ix is None:
            smooth_ix = raw_x
            smooth_iy = raw_y
        else:
            smooth_ix = int(smooth_ix * 0.45 + raw_x * 0.55)
            smooth_iy = int(smooth_iy * 0.45 + raw_y * 0.55)

        ix, iy = smooth_ix, smooth_iy

    else:
        ix, iy = None, None
        smooth_ix = None
        smooth_iy = None

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

        if stable_gesture == "erase" and selected_index != -1:
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
        if stable_gesture == "draw":

            lost_hand_frames = 0

            if len(current_stroke) == 0:
                current_stroke.append((ix, iy))
            else:
                last_x, last_y = current_stroke[-1]
                dist = np.hypot(ix - last_x, iy - last_y)

                if dist >= 5:
                    current_stroke.append((ix, iy))

        else:
            lost_hand_frames += 1

            if lost_hand_frames > MAX_LOST_FRAMES:
                if len(current_stroke) > 2:
                    strokes.append({
                        "points": current_stroke.copy(),
                        "color": current_color,
                        "thickness": thickness
                    })

                current_stroke = []
                lost_hand_frames = 0

        # =========================
        # CLEAR ALL
        # =========================
        if stable_gesture == "clear":

            clear_progress += 4

            if clear_progress >= 100:
                strokes.clear()
                current_stroke = []
                clear_progress = 0

        else:
            clear_progress = max(0, clear_progress - 6)

    # =============================
    # RENDER
    # =============================
    render_strokes(frame)

    if erase_progress > 0:
        draw_modern_eraser(frame, ix, iy, erase_progress)

    if clear_progress > 0 and ix is not None:
        draw_modern_eraser(frame, ix, iy, clear_progress)

        frame = draw_text(
            frame,
            "CLEARING...",
            (ix - 60, iy - 45),
            22,
            (0,0,255),
            "Montserrat-SemiBold.ttf"
        )

    frame = draw_text(
        frame,
        "FREE DRAW MODE",
        (0, 30),
        36,
        (255,255,255),
        "Orbitron-Bold.ttf",
        center=True
    )

    # =============================
    # AUTOSAVE FLASH MESSAGE
    # =============================
    if time.time() - autosave_flash_time < FLASH_DURATION:
        frame = draw_text(
            frame,
            "Autosaved",
            (40, 80),
            26,
            (0,255,0),
            "Montserrat-SemiBold.ttf"
        )

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