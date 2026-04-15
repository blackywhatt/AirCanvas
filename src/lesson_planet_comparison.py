import cv2
import numpy as np
import random
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont, ImageDraw, Image

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
hover_planet = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Planet Sizes
# ==============================
planet_size = {
    "mercury": 1,
    "mars": 2,
    "venus": 3,
    "earth": 4,
    "neptune": 5,
    "uranus": 6,
    "saturn": 7,
    "jupiter": 8
}

planets = list(planet_size.keys())

# ==============================
# Generate Questions
# ==============================
questions = []

for _ in range(5):
    p1, p2 = random.sample(planets, 2)

    if planet_size[p1] > planet_size[p2]:
        answer = p1
    else:
        answer = p2

    questions.append({
        "question": f"Which is bigger? {p1.upper()} or {p2.upper()}",
        "answer": answer,
        "left": p1,
        "right": p2
    })

lesson = LessonEngine(questions)

# ==============================
# Positions
# ==============================
planet_positions = {
    "left": (400, 350),
    "right": (900, 350)
}

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Planet Comparison Lesson"
cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

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

# ==============================
# Detect selection
# ==============================
def detect_selected(ix, iy, q):

    for side, (x, y) in planet_positions.items():

        dist = np.hypot(ix - x, iy - y)

        if dist < 100:
            return q[side]

    return None


# ==============================
# Draw Planet
# ==============================
def draw_planet(frame, name, x, y, highlight=False):

    color_map = {
        "mercury": (200,200,200),
        "venus": (0,200,255),
        "earth": (255,100,0),
        "mars": (0,0,255),
        "jupiter": (0,165,255),
        "saturn": (0,255,255),
        "uranus": (255,255,0),
        "neptune": (255,0,0)
    }

    color = (0,255,255) if highlight else color_map[name]

    cv2.circle(frame, (x,y), 70, color, -1)

    frame = draw_text(
        frame,
        name.upper(),
        (x - 60, y + 90),
        24,
        (255,255,255),
        "Montserrat-SemiBold.ttf"
    )

    return frame
# ==============================
# Main Loop
# ==============================
while cap.isOpened():

    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame,1)
    frame = cv2.resize(frame,(1280,720))

    gesture,index_positions,thumb_positions,hand_count,frame = get_gesture(frame)

    lesson.update()

    if not lesson.lesson_finished():

        q = lesson.get_current_question()

        if q is None:
            continue

        # Question
        frame = draw_text(
            frame,
            q["question"],
            (0, 40),
            36,
            (255,255,255),
            "Orbitron-Bold.ttf",
            center=True
        )

        # Draw planets
        frame = draw_planet(frame, q["left"], 400, 350, hover_planet == q["left"])
        frame = draw_planet(frame, q["right"], 900, 350, hover_planet == q["right"])

        # Interaction
        if (
            hand_count > 0
            and len(index_positions) > 0
            and lesson.feedback is None
        ):

            ix, iy = index_positions[0]

            cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

            selected = detect_selected(ix, iy, q)

            if selected:

                if hover_planet == selected:
                    hover_frames += 1
                else:
                    hover_planet = selected
                    hover_frames = 0

                if hover_frames > HOVER_THRESHOLD:
                    lesson.check_answer(selected)
                    hover_frames = 0
                    hover_planet = None

            else:
                hover_planet = None
                hover_frames = 0

        # Feedback
        if lesson.feedback == "correct" and lesson.feedback_timer > 0:
            frame = draw_text(
                frame,
                "Correct!",
                (40, 100),
                30,
                (0,255,0),
                "Montserrat-SemiBold.ttf"
            )

        elif lesson.feedback == "wrong" and lesson.feedback_timer > 0:
            frame = draw_text(
                frame,
                "Try Again",
                (40, 100),
                30,
                (0,0,255),
                "Montserrat-SemiBold.ttf"
            )

    else:
        frame = draw_text(
            frame,
            "Lesson Complete!",
            (40, 30),
            36,
            (0,255,255),
            "Orbitron-Bold.ttf"
        )

        frame = draw_text(
            frame,
            f"Score: {lesson.score}",
            (40, 80),
            30,
            (255,255,255),
            "Montserrat-SemiBold.ttf"
        )

    if lesson.should_exit():
        break
    
    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()