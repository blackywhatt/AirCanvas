import cv2
import numpy as np
import random
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont, ImageDraw, Image

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
hover_number = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Generate Questions
# ==============================
questions = [

    # EASY
    {"question":"1 + _ = 3", "answer":"2"},
    {"question":"_ + 1 = 2", "answer":"1"},
    {"question":"_ + 2 = 4", "answer":"2"},
    {"question":"1 + _ = 5", "answer":"4"},

    # MEDIUM
    {"question":"2 + _ + 2 = 9", "answer":"5"},
    {"question":"_ + 1 + 3 = 8", "answer":"4"},
    {"question":"2 + 3 + _ = 10", "answer":"5"},

    # HARD
    {"question":"_ + 3 - 2 = 7", "answer":"6"},
    {"question":"7 - _ + 8 = 9", "answer":"6"},
    {"question":"_ - 5 + 4 = 6", "answer":"7"}
]

lesson = LessonEngine(questions)

# ==============================
# Number Positions
# ==============================
number_positions = {
    "1": (120,500),
    "2": (280,500),
    "3": (440,500),
    "4": (600,500),
    "5": (760,500),
    "6": (920,500),
    "7": (1080,500)
}

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Missing Number Lesson"
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
        w = frame.shape[1]
        bbox = draw.textbbox((0,0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (w - text_w) // 2
        draw.text((x, pos[1]), text, font=font, fill=color)
    else:
        draw.text(pos, text, font=font, fill=color)

    return np.array(img_pil)

# ==============================
# Detect number selection
# ==============================
def detect_selected_number(ix, iy):

    for num, (nx, ny) in number_positions.items():
        dist = np.hypot(ix - nx, iy - ny)

        if dist < 80:
            return num

    return None


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

    # ==============================
    # Lesson Running
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()
        if q is None:
            continue
        
        current, total = lesson.get_progress()
        frame = draw_text(frame, f"{current}/{total}", (1100,30), 30)

        if current <= 3:
            level = "EASY"
        elif current <= 6:
            level = "MEDIUM"
        else:
            level = "HARD"

        frame = draw_text(
            frame,
            f"LEVEL: {level}",
            (980,70),
            28,
            (0,255,255),
            "Montserrat-SemiBold.ttf"
        )

        # Draw equation BIG (center)
        frame = draw_text(
            frame,
            q["question"],
            (0, 180),
            64,
            (255,255,255),
            "Orbitron-Bold.ttf",
            center=True
        )

        # Draw answer options
        for num, (x, y) in number_positions.items():

            color = (0,255,255) if hover_number == num else (255,255,255)

            frame = draw_text(
                frame,
                num,
                (x - 15, y - 25),
                48,
                color,
                "Montserrat-SemiBold.ttf"
            )

        # ==============================
        # Hand Interaction
        # ==============================
        if hand_count > 0 and len(index_positions) > 0:

            ix, iy = index_positions[0]

            cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

            selected_number = detect_selected_number(ix, iy)

            if selected_number:

                if hover_number == selected_number:
                    hover_frames += 1
                else:
                    hover_number = selected_number
                    hover_frames = 0

                if hover_frames > HOVER_THRESHOLD and answer_cooldown == 0:
                    lesson.check_answer(selected_number)
                    answer_cooldown = 30
                    hover_frames = 0
                    hover_number = None

        # ==============================
        # Feedback
        # ==============================
        if lesson.feedback == "correct":
            frame = draw_text(
                frame,
                "Correct!",
                (40, 60),
                30,
                (0,255,0),
                "Montserrat-SemiBold.ttf"
            )

        elif lesson.feedback == "wrong":
            frame = draw_text(
                frame,
                "Try Again",
                (40, 60),
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

    # cooldown
    if answer_cooldown > 0:
        answer_cooldown -= 1

    # ==============================
    # AUTO EXIT AFTER FINISH
    # ==============================
    if lesson.should_exit():
        break

    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()