import cv2
import mediapipe as mp
import numpy as np
import time
import threading
from PIL import ImageFont, ImageDraw, Image
import os
import queue
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
vosk_model = Model(MODEL_PATH)

voice_commands = """
[
"clear","red","blue","green",
"erase","draw","stop",
"undo","bigger","smaller"
]
"""

rec = KaldiRecognizer(vosk_model, 16000, voice_commands)

audio_queue = queue.Queue()

current_stroke = []
strokes = []
VOICE_ENABLED = False

current_color = (255, 0, 0)
thickness = 3

ERASE_MODE = False
CLEAR_FLAG = False

# ==============================
# LOAD UI ASSETS
# ==============================
question_bar = cv2.imread(
    "assets/ui/question_bar.png",
    cv2.IMREAD_UNCHANGED
)
question_bar = cv2.resize(
    question_bar,
    (900, 110)
)

correct_popup = cv2.imread(
    "assets/ui/correct_popup.png",
    cv2.IMREAD_UNCHANGED
)
correct_popup = cv2.resize(
    correct_popup,
    (230, 80)
)

wrong_popup = cv2.imread(
    "assets/ui/wrong_popup.png",
    cv2.IMREAD_UNCHANGED
)
wrong_popup = cv2.resize(
    wrong_popup,
    (230, 80)
)

def audio_callback(indata, frames, time, status):
    audio_queue.put(bytes(indata))

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

# ==============================
# PNG OVERLAY
# ==============================
def overlay_png(frame, png, x, y):

    h, w = png.shape[:2]

    if y + h > frame.shape[0] or x + w > frame.shape[1]:
        return frame

    b, g, r, a = cv2.split(png)

    overlay_color = cv2.merge((b, g, r))

    mask = a.astype(float) / 255.0
    inverse_mask = 1.0 - mask

    for c in range(3):
        frame[y:y+h, x:x+w, c] = (
            mask * overlay_color[:,:,c] +
            inverse_mask * frame[y:y+h, x:x+w, c]
        )

    return frame

def render_strokes(frame):

    for stroke in strokes:
        pts = np.array(stroke["points"], np.int32)
        cv2.polylines(
            frame,
            [pts],
            False,
            stroke["color"],
            stroke["thickness"],
            cv2.LINE_AA
        )

    if len(current_stroke) > 1:
        pts = np.array(current_stroke, np.int32)
        cv2.polylines(
            frame,
            [pts],
            False,
            current_color,
            thickness,
            cv2.LINE_AA
        )
        
# ==============================
# MAIN FUNCTION
# ==============================
def run():

    global current_color, thickness, ERASE_MODE, CLEAR_FLAG, current_stroke, strokes
    command = ""
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap.isOpened():
        print("❌ Cannot open camera")
        return

    # Better MediaPipe config
    mp_face = mp.solutions.face_mesh
    face_mesh = mp_face.FaceMesh(
        refine_landmarks=True,
        max_num_faces=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )

    prev_x, prev_y = 0, 0
    dwell_start = None
    DWELL_TIME = 1.5
    drawing = False
    alpha = 0.45
    window_name = "Accessibility Mode"

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=audio_callback):

        while True:
            ret, frame = cap.read()
            while not audio_queue.empty():

                data = audio_queue.get()

                if rec.AcceptWaveform(data):

                    result = json.loads(rec.Result())
                    command = result["text"]

                    if command:
                        print("Voice:", command)

                        if "clear" in command:
                            CLEAR_FLAG = True

                        elif "red" in command:
                            current_color = (0, 0, 255)

                        elif "blue" in command:
                            current_color = (255, 0, 0)

                        elif "green" in command:
                            current_color = (0, 255, 0)

                        elif "erase" in command:
                            strokes.clear()

                        elif "draw" in command:
                            drawing = True

                        elif "stop" in command:
                            drawing = False
                            if len(current_stroke) > 2:
                                strokes.append({
                                    "points": current_stroke.copy(),
                                    "color": current_color,
                                    "thickness": thickness
                                })
                            current_stroke.clear()

                        elif "bigger" in command:
                            thickness = min(thickness + 1, 15)

                        elif "smaller" in command:
                            thickness = max(thickness - 1, 1)

                        elif "undo" in command and strokes:
                            strokes.pop()

            if not ret:
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            if CLEAR_FLAG:
                strokes.clear()
                current_stroke.clear()
                CLEAR_FLAG = False

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)

            status_text = "Tracking face"

            if results.multi_face_landmarks:
                face = results.multi_face_landmarks[0]

                # ======================
                # FULL FACE CENTER (ULTRA STABLE)
                # ======================
                nose = face.landmark[1]
                center_x, center_y = nose.x, nose.y

                landmarks = np.array([(lm.x, lm.y) for lm in face.landmark])

                scale = 1.15

                raw_x = int((center_x - 0.5) * scale * w + w / 2)
                raw_y = int((center_y - 0.5) * scale * h + h / 2)

                # Clamp inside screen
                raw_x = max(0, min(w, raw_x))
                raw_y = max(0, min(h, raw_y))

                # Bounding box, buang if buruk
                # x_min = int(np.min(landmarks[:, 0]) * w)
                # y_min = int(np.min(landmarks[:, 1]) * h)
                # x_max = int(np.max(landmarks[:, 0]) * w)
                # y_max = int(np.max(landmarks[:, 1]) * h)

                # cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 1)

                mp_drawing = mp.solutions.drawing_utils
                mp_styles = mp.solutions.drawing_styles

                mp_drawing.draw_landmarks(
                    frame,
                    face,
                    mp_face.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_styles.get_default_face_mesh_tesselation_style()
                )

                # Draw ONLY center (clean look)
                cv2.circle(frame, (raw_x, raw_y), 6, (0, 255, 255), -1)

                cx = int(alpha * raw_x + (1 - alpha) * prev_x)
                cy = int(alpha * raw_y + (1 - alpha) * prev_y)

                # DEAD ZONE
                if abs(cx - prev_x) < 3:
                    cx = prev_x
                if abs(cy - prev_y) < 3:
                    cy = prev_y

                # LIMIT SPEED
                max_step = 120
                dx = cx - prev_x
                dy = cy - prev_y
                dx = max(-max_step, min(max_step, dx))
                dy = max(-max_step, min(max_step, dy))
                cx = prev_x + dx
                cy = prev_y + dy

                # ======================
                # DWELL START DRAW
                # ======================
                move_x = abs(cx - prev_x)
                move_y = abs(cy - prev_y)

                if not drawing:
                    if move_x < 10 and move_y < 12:

                        if dwell_start is None:
                            dwell_start = time.time()

                        else:
                            elapsed = time.time() - dwell_start

                            progress = int((elapsed / DWELL_TIME) * 360)

                            cv2.circle(frame, (cx, cy), 20, (80,80,80), 1)

                            cv2.ellipse(
                                frame,
                                (cx, cy),
                                (20,20),
                                -90,
                                0,
                                progress,
                                (0,255,255),
                                3
                            )

                            if elapsed >= DWELL_TIME:
                                drawing = True
                                dwell_start = None

                    else:
                        dwell_start = None
                else:
                    dwell_start = None

                prev_x, prev_y = cx, cy

                status_text = "DRAWING..." if drawing else "HOLD TO START"

                cv2.circle(
                    frame,
                    (cx, cy),
                    16,
                    (255,255,255),
                    2,
                    cv2.LINE_AA
                )

                cv2.circle(
                    frame,
                    (cx, cy),
                    5,
                    current_color,
                    -1,
                    cv2.LINE_AA
                )

                # ======================
                # DRAWING
                # ======================
                if drawing:
                    if len(current_stroke) > 0:
                        prev_pt = current_stroke[-1]

                        # interpolate points between previous and current
                        dist = int(np.hypot(cx - prev_pt[0], cy - prev_pt[1]))
                        steps = max(5, dist // 8)

                        for i in range(1, steps + 1):
                            ix = int(prev_pt[0] + (cx - prev_pt[0]) * i / steps)
                            iy = int(prev_pt[1] + (cy - prev_pt[1]) * i / steps)
                            current_stroke.append((ix, iy))
                    else:
                        current_stroke.append((cx, cy))
                else:
                    if len(current_stroke) > 2:
                        strokes.append({
                            "points": current_stroke.copy(),
                            "color": current_color,
                            "thickness": thickness
                        })
                    current_stroke.clear()

            else:
                status_text = "Face not detected"

            render_strokes(frame)
            combined = frame
            # ======================
            # UI PANEL
            # ======================
            combined = overlay_png(
                combined,
                question_bar,
                25,
                20
            )
            
            combined = draw_text(
                combined,
                "Accessibility Drawing",
                (120, 50),
                32,
                (255,255,255),
                "Montserrat-SemiBold.ttf"
            )

            combined = draw_text(
                combined,
                status_text,
                (70, 120),
                22,
                (255,255,255),
                "Montserrat-SemiBold.ttf"
            )

            combined = draw_text(
                combined,
                "Brush :",
                (1080, 60),
                24,
                (255,255,255),
                "Montserrat-SemiBold.ttf"
            )

            cv2.circle(
                combined,
                (1200, 75),
                18,
                current_color,
                -1,
                cv2.LINE_AA
            )

            voice_text = command

            if voice_text:

                combined = draw_text(
                    combined,
                    voice_text.upper(),
                    (145, 122),
                    22,
                    (255,255,255),
                    "Montserrat-SemiBold.ttf",
                    center=True
                )

            cv2.imshow(window_name, combined)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('b'):
                break

            if key == ord('f'):
                cv2.setWindowProperty(window_name,
                    cv2.WND_PROP_FULLSCREEN,
                    cv2.WINDOW_FULLSCREEN)

            if key == ord('w'):
                cv2.setWindowProperty(window_name,
                    cv2.WND_PROP_FULLSCREEN,
                    cv2.WINDOW_NORMAL)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run()