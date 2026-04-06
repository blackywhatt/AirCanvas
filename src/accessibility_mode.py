import cv2
import mediapipe as mp
import numpy as np
import time
import threading

current_stroke = []
strokes = []
VOICE_ENABLED = False
# ==============================
# OPTIONAL VOICE SETUP
# ==============================
try:
    import speech_recognition as sr
    VOICE_ENABLED = True
except:
    VOICE_ENABLED = False

DRAW_COLOR = (255, 0, 0)
ERASE_MODE = False
CLEAR_FLAG = False


# ==============================
# VOICE LISTENER
# ==============================
def voice_listener():
    global DRAW_COLOR, ERASE_MODE, CLEAR_FLAG

    r = sr.Recognizer()
    mic = sr.Microphone()

    while True:
        try:
            with mic as source:
                audio = r.listen(source, phrase_time_limit=2)

            command = r.recognize_google(audio).lower()
            print("Voice:", command)

            if "clear" in command:
                CLEAR_FLAG = True
            elif "red" in command:
                DRAW_COLOR = (0, 0, 255)
            elif "blue" in command:
                DRAW_COLOR = (255, 0, 0)
            elif "green" in command:
                DRAW_COLOR = (0, 255, 0)
            elif "erase" in command:
                ERASE_MODE = True
            elif "draw" in command:
                ERASE_MODE = False

        except:
            pass

def render_strokes(frame):
    for stroke in strokes:
        pts = np.array(stroke, np.int32)
        cv2.polylines(frame, [pts], False, (255, 0, 0), 3, cv2.LINE_AA)

    if len(current_stroke) > 1:
        pts = np.array(current_stroke, np.int32)
        cv2.polylines(frame, [pts], False, (255, 0, 0), 3, cv2.LINE_AA)
        
# ==============================
# MAIN FUNCTION
# ==============================
def run():

    global DRAW_COLOR, ERASE_MODE, CLEAR_FLAG, current_stroke, strokes

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
    DWELL_TIME = 1.0
    drawing = False

    alpha = 0.30  # smoother

    # Start voice thread
    if VOICE_ENABLED:
        threading.Thread(target=voice_listener, daemon=True).start()

    window_name = "Accessibility Mode"

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    while True:
        ret, frame = cap.read()
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
            landmarks = np.array([(lm.x, lm.y) for lm in face.landmark])
            center_x, center_y = landmarks.mean(axis=0)

            scale = 1.5

            raw_x = int((center_x - 0.5) * scale * w + w / 2)
            raw_y = int((center_y - 0.5) * scale * h + h / 2)

            # Clamp inside screen
            raw_x = max(0, min(w, raw_x))
            raw_y = max(0, min(h, raw_y))

            # Bounding box, buang if buruk
            x_min = int(np.min(landmarks[:, 0]) * w)
            y_min = int(np.min(landmarks[:, 1]) * h)
            x_max = int(np.max(landmarks[:, 0]) * w)
            y_max = int(np.max(landmarks[:, 1]) * h)

            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 1)

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
            # ======================
            # SMOOTHING
            # ======================
            cx = int(alpha * raw_x + (1 - alpha) * prev_x)
            cy = int(alpha * raw_y + (1 - alpha) * prev_y)

            # DEAD ZONE
            if abs(cx - prev_x) < 5:
                cx = prev_x
            if abs(cy - prev_y) < 5:
                cy = prev_y

            # LIMIT SPEED
            max_step = 80
            dx = cx - prev_x
            dy = cy - prev_y
            dx = max(-max_step, min(max_step, dx))
            dy = max(-max_step, min(max_step, dy))
            cx = prev_x + dx
            cy = prev_y + dy

            # ======================
            # DWELL DETECTION
            # ======================
            if abs(cx - prev_x) < 10 and abs(cy - prev_y) < 10:
                if dwell_start is None:
                    dwell_start = time.time()
                else:
                    elapsed = time.time() - dwell_start

                    # Draw progress circle
                    progress = int((elapsed / DWELL_TIME) * 360)
                    # Background circle
                    cv2.circle(frame, (cx, cy), 20, (80, 80, 80), 1)

                    # Progress arc (starts from top)
                    cv2.ellipse(frame, (cx, cy), (20, 20),
                                -90, 0, progress, (0, 255, 255), 3)

                    if elapsed > DWELL_TIME:
                        drawing = True
                        status_text = "Drawing..."
            else:
                dwell_start = None
                drawing = False

            prev_x, prev_y = cx, cy

            # Draw cursor
            cv2.circle(frame, (cx, cy), 10, (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 3, (0, 255, 0), -1)

            # ======================
            # DRAWING
            # ======================
            if drawing:
                if len(current_stroke) > 0:
                    prev_pt = current_stroke[-1]

                    # interpolate points between previous and current
                    steps = 5
                    for i in range(1, steps + 1):
                        ix = int(prev_pt[0] + (cx - prev_pt[0]) * i / steps)
                        iy = int(prev_pt[1] + (cy - prev_pt[1]) * i / steps)
                        current_stroke.append((ix, iy))
                else:
                    current_stroke.append((cx, cy))
            else:
                if len(current_stroke) > 2:
                    strokes.append(current_stroke.copy())
                current_stroke.clear()

        else:
            status_text = "Face not detected"

        render_strokes(frame)
        combined = frame
        # ======================
        # UI PANEL
        # ======================
        cv2.rectangle(combined, (0, 0), (w, 50), (30, 30, 30), -1)

        mode_text = "ERASE" if ERASE_MODE else "DRAW"
        color_text = f"Color: {DRAW_COLOR}"

        cv2.putText(combined, "Accessibility Mode", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.putText(combined, status_text, (300, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        cv2.putText(combined, mode_text, (500, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.putText(combined, color_text, (650, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow(window_name, combined)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
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