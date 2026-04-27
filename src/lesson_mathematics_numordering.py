import cv2
import numpy as np
import random
from gesture_engine import get_gesture
import os
from PIL import ImageFont, ImageDraw, Image
from lesson_engine import LessonEngine

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")

hover_number = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Generate Numbers
# ==============================
numbers = random.sample(range(1,6), 4)  # e.g. [3,1,4,2]
numbers_str = [str(n) for n in numbers]

selected_sequence = []

questions = [
    {"question":"Arrange from SMALLEST to LARGEST", "mode":"asc", "answer":"done"},
    {"question":"Arrange from LARGEST to SMALLEST", "mode":"desc", "answer":"done"},
    {"question":"Arrange EVEN numbers first", "mode":"even", "answer":"done"},
]

lesson = LessonEngine(questions)

def update_correct_sequence():

    global correct_sequence

    q = lesson.get_current_question()

    if q is None:
        return

    if q["mode"] == "asc":
        correct_sequence = sorted(numbers_str, key=int)

    elif q["mode"] == "desc":
        correct_sequence = sorted(numbers_str, key=int, reverse=True)

    elif q["mode"] == "even":
        evens = [n for n in numbers_str if int(n) % 2 == 0]
        odds = [n for n in numbers_str if int(n) % 2 == 1]
        correct_sequence = evens + odds

update_correct_sequence()

# ==============================
# Positions
# ==============================
number_positions = {}

start_x = 300
for i, num in enumerate(numbers_str):
    number_positions[num] = (start_x + i * 200, 350)

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Number Ordering Lesson"
cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

answer_cooldown = 0
feedback = None

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
    # Draw Numbers
    # ==============================
    if not lesson.lesson_finished():

        for num, (x, y) in number_positions.items():

            if num in selected_sequence:
                color = (0,255,0)
            elif hover_number == num:
                color = (0,255,255)
            else:
                color = (255,255,255)

            frame = draw_text(
                frame,
                num,
                (x - 15, y - 25),
                48,
                color,
                "Montserrat-SemiBold.ttf"
            )

    # ==============================
    # Draw Progress
    # ==============================
    if not lesson.lesson_finished():
        frame = draw_text(
            frame,
            "Your Order: " + " ".join(selected_sequence),
            (40, 80),
            30,
            (0,255,255),
            "Montserrat-Medium.ttf"
        )

    # ==============================
    # Hand Interaction
    # ==============================
    if hand_count > 0 and len(index_positions) > 0:

        ix, iy = index_positions[0]

        cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

        selected_number = detect_selected_number(ix, iy)

        if selected_number and selected_number not in selected_sequence:

            if hover_number == selected_number:
                hover_frames += 1
            else:
                hover_number = selected_number
                hover_frames = 0

            if hover_frames > HOVER_THRESHOLD and answer_cooldown == 0:

                if len(selected_sequence) >= len(correct_sequence):
                    continue

                expected = correct_sequence[len(selected_sequence)]

                if selected_number == expected:
                    selected_sequence.append(selected_number)
                    feedback = "correct_step"

                    if selected_sequence == correct_sequence:
                        lesson.score += 1
                        lesson.current_question += 1

                        if not lesson.lesson_finished():
                            selected_sequence.clear()

                            numbers = random.sample(range(1,6), 4)
                            numbers_str = [str(n) for n in numbers]

                            start_x = 300
                            number_positions.clear()

                            for i, num in enumerate(numbers_str):
                                number_positions[num] = (start_x + i * 200, 350)

                            update_correct_sequence()
                else:
                    selected_sequence.clear()
                    feedback = "wrong"

                answer_cooldown = 25
                hover_frames = 0
                hover_number = None

    # ==============================
    # Feedback
    # ==============================
    if feedback == "correct_step":
        frame = draw_text(
            frame,
            "Good!",
            (40, 130),
            30,
            (0,255,0),
            "Montserrat-SemiBold.ttf"
        )

    elif feedback == "wrong":
        frame = draw_text(
            frame,
            "Wrong Order! Try Again",
            (40, 130),
            30,
            (0,0,255),
            "Montserrat-SemiBold.ttf"
        )

    # ==============================
    # Completed
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()
        current, total = lesson.get_progress()

        if current == 0:
            level = "EASY"
        elif current == 1:
            level = "MEDIUM"
        else:
            level = "HARD"

        frame = draw_text(
            frame,
            f"LEVEL: {level}",
            (980, 30),
            28,
            (0,255,255),
            "Montserrat-SemiBold.ttf"
        )

        if q is not None:
            frame = draw_text(
                frame,
                q["question"],
                (40, 30),
                36,
                (255,255,255),
                "Orbitron-Bold.ttf"
            )

    else:
        frame = draw_text(
            frame,
            "Lesson Complete!",
            (0, 250),
            60,
            (0,255,255),
            "Orbitron-Bold.ttf",
            center=True
        )

        frame = draw_text(
            frame,
            f"Score: {lesson.score}",
            (0, 400),
            36,
            (255,255,255),
            "Montserrat-SemiBold.ttf",
            center=True
        )

    if lesson.lesson_finished() and lesson.finish_timer == 1:
        selected_sequence.clear()

    # cooldown
    if answer_cooldown > 0:
        answer_cooldown -= 1

    if lesson.should_exit():
        break

    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()