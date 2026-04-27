import cv2
import numpy as np
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont, ImageDraw, Image

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
hover_planet = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Questions
# ==============================
questions = [

    # EASY
    {"question":"Select the smallest planet near the sun", "answer":"mercury"},
    {"question":"Select the hottest planet with thick clouds", "answer":"venus"},
    {"question":"Select the only planet that supports life", "answer":"earth"},
    {"question":"Select the red planet with huge volcanoes", "answer":"mars"},

    # MEDIUM
    {"question":"Select the planet called Morning Star", "answer":"venus"},
    {"question":"Select the planet with blue oceans", "answer":"earth"},
    {"question":"Select the planet closest to the Sun", "answer":"mercury"},

    # HARD
    {"question":"Select the 4th planet from the Sun", "answer":"mars"},
    {"question":"Select the fastest orbiting planet", "answer":"mercury"},
    {"question":"Select the planet humans call home", "answer":"earth"}
]

lesson = LessonEngine(questions)

# ==============================
# Planet Positions
# ==============================
planet_positions = {
    "mercury": (250, 360),
    "venus": (500, 360),
    "earth": (750, 360),
    "mars": (1000, 360)
}

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Planet Identification Lesson"
cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

answer_cooldown = 0

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
        bbox = draw.textbbox((0,0), text, font=font)
        text_w = bbox[2] - bbox[0]

        x = (frame.shape[1] - text_w) // 2

        if x < 20:
            x = 20

        draw.text((x, pos[1]), text, font=font, fill=color)
    else:
        draw.text(pos, text, font=font, fill=color)

    return np.array(img_pil)

# ==============================
# Detect selection
# ==============================
def detect_selected_planet(ix, iy):

    for name, (px, py) in planet_positions.items():
        dist = np.hypot(ix - px, iy - py)

        if dist < 80:
            return name

    return None


# ==============================
# Draw Planets (simple circles)
# ==============================
def draw_planets(frame):

    for name, (x, y) in planet_positions.items():

        if name == "mercury":
            color = (200,200,200)
        elif name == "venus":
            color = (0,200,255)
        elif name == "earth":
            color = (255,100,0)
        elif name == "mars":
            color = (0,0,255)

        if hover_planet == name:
            color = (0,255,255)

        size_map = {
            "mercury":50,
            "venus":65,
            "earth":67,
            "mars":55
        }

        r = size_map[name]

        cv2.circle(frame, (x,y), r, color, -1)

        label = name.upper()

        img_pil = Image.fromarray(frame)
        draw = ImageDraw.Draw(img_pil)

        font_path = os.path.join(FONT_DIR, "Montserrat-SemiBold.ttf")

        try:
            font = ImageFont.truetype(font_path, 22)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0,0), label, font=font)
        text_w = bbox[2] - bbox[0]

        text_x = x - text_w // 2
        text_y = y + r + 25

        draw.text((text_x, text_y), label, font=font, fill=(255,255,255))

        frame = np.array(img_pil)

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

    frame = draw_planets(frame)

    # ==============================
    # Lesson Running
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()

        current, total = lesson.get_progress()

        if current <= 3:
            level = "EASY"
        elif current <= 6:
            level = "MEDIUM"
        else:
            level = "HARD"

        frame = draw_text(
            frame,
            f"LEVEL: {level}",
            (980,40),
            28,
            (0,255,255),
            "Montserrat-SemiBold.ttf"
        )

        if q is None:
            continue

        frame = draw_text(
            frame,
            f"Score: {lesson.score}",
            (1100, 650),
            24,
            (255,255,255),
            "Montserrat-Medium.ttf"
        )

        frame = draw_text(
            frame,
            q["question"],
            (0, 100),
            36,
            (255,255,255),
            "Orbitron-Bold.ttf",
            center=True
        )

        if (
            hand_count > 0
            and len(index_positions) > 0
            and lesson.feedback is None
        ):

            ix, iy = index_positions[0]

            cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

            selected = detect_selected_planet(ix, iy)

            if selected:

                if hover_planet == selected:
                    hover_frames += 1
                else:
                    hover_planet = selected
                    hover_frames = 0

                if hover_frames > HOVER_THRESHOLD and answer_cooldown == 0:
                    lesson.check_answer(selected)
                    answer_cooldown = 30
                    hover_frames = 0
                    hover_planet = None

        # Feedback
        if lesson.feedback == "correct" and lesson.feedback_timer > 0:
            frame = draw_text(
                frame,
                "Correct!",
                (40, 80),
                30,
                (0,255,0),
                "Montserrat-SemiBold.ttf"
            )

        elif lesson.feedback == "wrong" and lesson.feedback_timer > 0:
            frame = draw_text(
                frame,
                "Try Again",
                (40, 80),
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

    if answer_cooldown > 0:
        answer_cooldown -= 1

    cv2.imshow(window_name,frame)

    if lesson.should_exit():
        break

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()