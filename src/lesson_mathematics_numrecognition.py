import cv2
import numpy as np
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont, ImageDraw, Image

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
hover_number = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Lesson Questions
# ==============================
questions = [

    # EASY
    {"question": "Select number ONE", "answer": "1"},
    {"question": "Select number THREE", "answer": "3"},
    {"question": "Select number TWO", "answer": "2"},
    {"question": "Select number FOUR", "answer": "4"},

    # MEDIUM
    {"question": "Select the BIGGEST number", "answer": "4"},
    {"question": "Select the SMALLEST number", "answer": "1"},
    {"question": "Select an EVEN number", "answer": "2"},

    # HARD
    {"question": "What is ONE + TWO ?", "answer": "3"},
    {"question": "What is TWO + TWO ?", "answer": "4"},
    {"question": "What is THREE - TWO ?", "answer": "1"}
]

lesson = LessonEngine(questions)
# ==============================
# Number Positions
# ==============================
base_positions = [
    (250, 360),
    (500, 360),
    (750, 360),
    (1000, 360)
]

number_positions = {}

def shuffle_numbers():

    global number_positions
    import random

    nums = ["1","2","3","4"]
    random_positions = base_positions.copy()
    random.shuffle(random_positions)

    number_positions = {
        nums[i]: random_positions[i]
        for i in range(4)
    }
shuffle_numbers()
# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Number Recognition Lesson"
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
        text_h = bbox[3] - bbox[1]

        x = pos[0] - text_w // 2
        y = pos[1] - text_h // 2 - 3

        draw.text((x, y), text, font=font, fill=color)
    else:
        draw.text(pos, text, font=font, fill=color)

    return np.array(img_pil)

# ==============================
# Detect selected number
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
    for num, (x, y) in number_positions.items():

        color = (0,255,255) if hover_number == num else (255,255,255)

        cv2.circle(frame,(x,y),55,color,2)

        frame = draw_text(
            frame,
            num,
            (x,y),
            42,
            color,
            "Montserrat-SemiBold.ttf",
            center=True
        )

    # ==============================
    # Lesson Running
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()
        if q is None:
            continue
        
        current, total = lesson.get_progress()
        frame = draw_text(frame, f"{current}/{total}", (1100,30), 30)

        if current <=4:
            level = "EASY"
        elif current <=7:
            level = "MEDIUM"
        else:
            level = "HARD"

        frame = draw_text(frame, f"LEVEL: {level}", (980,70), 28, (0,255,255))

        frame = draw_text(
            frame,
            q["question"],
            (40, 30),
            36,
            (255,255,255),
            "Orbitron-Bold.ttf"
        )

        if hand_count > 0 and len(index_positions) > 0:

            ix, iy = index_positions[0]

            # cursor
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

                    if lesson.feedback == "correct" and not lesson.lesson_finished():
                        shuffle_numbers()

                    answer_cooldown = 30
                    hover_frames = 0
                    hover_number = None

        # Feedback
        if lesson.feedback == "correct":
            frame = draw_text(
                frame,
                "Correct!",
                (40, 80),
                30,
                (0,255,0),
                "Montserrat-SemiBold.ttf"
            )

        elif lesson.feedback == "wrong":
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