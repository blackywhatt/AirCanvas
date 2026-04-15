import cv2
import numpy as np
import random
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont, ImageDraw, Image

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
hover_option = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Pattern Types
# ==============================
patterns = [
    ["circle", "square", "circle", "square"],
    ["square", "circle", "square", "circle"]
]

# ==============================
# Generate Questions
# ==============================
questions = []

for _ in range(5):
    base_pattern = random.choice(patterns)
    answer = base_pattern[0]  # repeating pattern

    questions.append({
        "pattern": base_pattern,
        "answer": answer
    })

lesson = LessonEngine(questions)

# ==============================
# Positions
# ==============================
pattern_positions = [(300 + i*150, 300) for i in range(4)]

option_positions = {
    "circle": (500, 550),
    "square": (800, 550)
}

answer_cooldown = 0

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Pattern Drawing Lesson"
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
# Draw Shape
# ==============================
def draw_shape(frame, shape, x, y, highlight=False):

    color = (0,255,255) if highlight else (255,255,255)

    if shape == "circle":
        cv2.circle(frame, (x,y), 40, color, 3)
    elif shape == "square":
        cv2.rectangle(frame, (x-40,y-40),(x+40,y+40), color, 3)


# ==============================
# Detect selection
# ==============================
def detect_selected(ix, iy):

    for name,(x,y) in option_positions.items():
        dist = np.hypot(ix-x, iy-y)

        if dist < 70:
            return name

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

    if not lesson.lesson_finished():

        q = lesson.get_current_question()
        if q is None:
            continue

        # Instruction
        frame = draw_text(
            frame,
            "Complete the pattern",
            (0, 30),
            36,
            (255,255,255),
            "Orbitron-Bold.ttf",
            center=True
        )

        current, total = lesson.get_progress()
        frame = draw_text(frame, f"{current}/{total}", (1100,30), 30)   

        # Draw pattern
        for i, shape in enumerate(q["pattern"]):
            x, y = pattern_positions[i]
            draw_shape(frame, shape, x, y)

        # Draw question mark slot
        frame = draw_text(
            frame,
            "?",
            (300 + 4*150, 250),
            60,
            (0,255,255),
            "Orbitron-Bold.ttf"
        )

        # Draw options
        for name,(x,y) in option_positions.items():
            draw_shape(frame, name, x, y, hover_option == name)

        # ==============================
        # Interaction
        # ==============================
        if not lesson.lesson_finished() and hand_count > 0 and len(index_positions) > 0:

            ix, iy = index_positions[0]

            cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

            selected = detect_selected(ix, iy)

            if selected:

                if hover_option == selected:
                    hover_frames += 1
                else:
                    hover_option = selected
                    hover_frames = 0

                if hover_frames > HOVER_THRESHOLD and answer_cooldown == 0:

                    lesson.check_answer(selected)

                    answer_cooldown = 30
                    hover_frames = 0
                    hover_option = None

        # ==============================
        # Feedback
        # ==============================
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

    if answer_cooldown > 0:
        answer_cooldown -= 1

    if lesson.lesson_finished() and lesson.finish_timer == 1:
        hover_option = None

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