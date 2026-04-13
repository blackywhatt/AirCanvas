import sys
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
import cv2
import numpy as np
from gesture_engine import get_gesture 
import json
import time
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from datetime import datetime
import os
from PIL import ImageFont, ImageDraw, Image

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
# ==============================
# VOICE SETUP
# ==============================
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_PATH, "model")

vosk_model = Model(MODEL_PATH)

voice_commands = '["red","green","blue","bigger","smaller","clear canvas","undo","[unk]"]'
rec = KaldiRecognizer(vosk_model, 16000, voice_commands)

audio_queue = queue.Queue()

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
        x = (w - text_w) // 2
        draw.text((x, pos[1]), text, font=font, fill=color)
    else:
        draw.text(pos, text, font=font, fill=color)

    return np.array(img_pil)

def audio_callback(indata, frames, time, status):
    audio_queue.put(bytes(indata))

# ==============================
# DRAW DATA
# ==============================
strokes = []
current_stroke = []

current_color = (220,220,220)
thickness = 2

# ==============================
# SESSION STORAGE
# ==============================
SESSION_FOLDER = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSION_FOLDER, exist_ok=True)

current_session_file = None
last_autosave_time = time.time()
AUTOSAVE_INTERVAL = 10

# ==============================
# SAVE / LOAD
# ==============================
def save_session(session_name=None):
    global current_session_file

    if current_session_file is None:
        if not session_name:
            session_name = "draw_session"

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"{session_name}_{timestamp}.json"
        current_session_file = filename
    else:
        filename = current_session_file

    path = os.path.join(SESSION_FOLDER, filename)

    data = {
        "mode": "free_draw",
        "strokes": strokes
    }

    with open(path,"w") as f:
        json.dump(data,f)

    print("[INFO] Saved:", filename)

# ==============================
# RENDER
# ==============================
def render_strokes(frame):

    for stroke in strokes:
        pts = np.array(stroke["points"], np.int32)
        cv2.polylines(frame,[pts],False,stroke["color"],stroke["thickness"])

    if len(current_stroke) > 1:
        pts = np.array(current_stroke,np.int32)
        cv2.polylines(frame,[pts],False,current_color,thickness)

# ==============================
# CAMERA
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Voice Draw Module"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# ==============================
# AUDIO STREAM
# ==============================
with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype='int16',
        channels=1,
        callback=audio_callback):

    while cap.isOpened():

        ret,frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame,1)
        frame = cv2.resize(frame,(1280,720))

        gesture,index_positions,thumb_positions,hand_count,frame = get_gesture(frame)

        # Only allow draw gesture in this module
        if gesture not in ["draw"]:
            gesture = "idle"

        # ==============================
        # VOICE COMMAND PROCESSING
        # ==============================
        while not audio_queue.empty():

            data = audio_queue.get()

            if rec.AcceptWaveform(data):

                result = json.loads(rec.Result())
                command = result["text"]

                if command:

                    print("Voice:",command)

                    if "red" in command:
                        current_color = (0,0,255)

                    elif "green" in command:
                        current_color = (0,255,0)

                    elif "blue" in command:
                        current_color = (255,0,0)

                    elif "bigger" in command:
                        thickness = min(thickness + 1,15)

                    elif "smaller" in command:
                        thickness = max(thickness - 1,1)

                    elif "clear canvas" in command:
                        strokes.clear()
                        current_stroke.clear()

                    elif "undo" in command and strokes:
                        strokes.pop()

        # ==============================
        # GESTURE DRAWING
        # ==============================
        if hand_count >= 1 and len(index_positions) > 0:

            ix,iy = index_positions[0]

            if gesture == "draw":
                current_stroke.append((ix,iy))

            elif gesture == "idle":
                if len(current_stroke) > 2:
                    strokes.append({
                        "points": current_stroke.copy(),
                        "color": current_color,
                        "thickness": thickness
                    })
                current_stroke = []

        # ==============================
        # RENDER
        # ==============================
        render_strokes(frame)

        # ==============================
        # UI
        # ==============================
        frame = draw_text(
            frame,
            "VOICE DRAW MODE",
            (0, 30),
            36,
            (255,255,255),
            "Orbitron-Bold.ttf",
            center=True
        )

        frame = draw_text(
            frame,
            f"COLOR: {current_color}",
            (40, 80),
            26,
            (200,200,200),
            "Montserrat-Medium.ttf"
        )

        frame = draw_text(
            frame,
            f"THICKNESS: {thickness}",
            (40, 110),
            26,
            (200,200,200),
            "Montserrat-Medium.ttf"
        )

        frame = draw_text(
            frame,
            "Voice: red | green | blue | bigger | smaller | undo | clear canvas",
            (40, 670),
            22,
            (180,180,180),
            "Montserrat-Medium.ttf"
        )

        cv2.imshow(window_name,frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("b"):
            break
    

cap.release()
cv2.destroyAllWindows()