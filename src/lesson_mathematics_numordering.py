import cv2
import numpy as np
import random
from gesture_engine import get_gesture
import os
from PIL import ImageFont, ImageDraw, Image
from lesson_engine import LessonEngine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")

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

# ==============================
# LOAD UI ASSETS
# ==============================
question_bar = cv2.imread(
    "assets/ui/question_bar.png",
    cv2.IMREAD_UNCHANGED
)
question_bar = cv2.resize(question_bar,(900,110))

progress_pill = cv2.imread(
    "assets/ui/progress_pill.png",
    cv2.IMREAD_UNCHANGED
)
progress_pill = cv2.resize(progress_pill,(115,70))

level_pill = cv2.imread(
    "assets/ui/level_pill.png",
    cv2.IMREAD_UNCHANGED
)
level_pill = cv2.resize(level_pill,(175,70))

correct_popup = cv2.imread(
    "assets/ui/correct_popup.png",
    cv2.IMREAD_UNCHANGED
)
correct_popup = cv2.resize(correct_popup,(230,80))

wrong_popup = cv2.imread(
    "assets/ui/wrong_popup.png",
    cv2.IMREAD_UNCHANGED
)
wrong_popup = cv2.resize(wrong_popup,(260,80))

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

start_x = 250
for i, num in enumerate(numbers_str):
    number_positions[num] = (start_x + i * 260, 340)

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
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

def draw_centered_text(frame, text, box_x, box_y, box_w, box_h,
                       size=30,
                       color=(255,255,255),
                       font_name="Montserrat-SemiBold.ttf"):

    font_path = os.path.join(FONT_DIR, font_name)

    try:
        font = ImageFont.truetype(font_path, size)
    except:
        return frame

    pil_image = Image.fromarray(frame)
    draw = ImageDraw.Draw(pil_image)

    bbox = draw.textbbox((0,0), text, font=font)

    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = box_x + (box_w - text_w) // 2
    y = box_y + (box_h - text_h) // 2 - 8

    draw.text((x, y), text, font=font, fill=color)

    return np.array(pil_image)

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

    if answer_cooldown == 0:
        feedback = None
    # ==============================
    # Draw Numbers
    # ==============================
    if not lesson.lesson_finished():

        for num, (x, y) in number_positions.items():

            selected = num in selected_sequence
            hovered = hover_number == num

            radius = 72 if hovered else 62

            if selected:
                circle_color = (0,255,120)

            elif hovered:
                circle_color = (0,255,255)

            else:
                circle_color = (255,255,255)

            cv2.circle(
                frame,
                (x,y),
                radius,
                circle_color,
                4,
                cv2.LINE_AA
            )

            frame = draw_text(
                frame,
                num,
                (x - 18, y - 32),
                52,
                (255,255,255),
                "Montserrat-SemiBold.ttf"
            )

    # ==============================
    # ORDER DISPLAY
    # ==============================
    if not lesson.lesson_finished():

        sequence_text = "  →  ".join(selected_sequence)

        frame = draw_text(
            frame,
            sequence_text,
            (0, 500),
            42,
            (0,255,255),
            "Montserrat-SemiBold.ttf",
            center=True
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

                    if selected_sequence == correct_sequence:
                        feedback = "correct_complete"
                        lesson.score += 1
                        lesson.current_question += 1

                        if not lesson.lesson_finished():
                            selected_sequence.clear()

                            numbers = random.sample(range(1,6), 4)
                            numbers_str = [str(n) for n in numbers]

                            start_x = 250
                            number_positions.clear()

                            for i, num in enumerate(numbers_str):
                                number_positions[num] = (start_x + i * 260, 340)

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
    if feedback == "correct_complete":

        frame = overlay_png(
            frame,
            correct_popup,
            30,
            120
        )

        frame = draw_text(
            frame,
            "Sequence Complete!",
            (75, 140),
            22,
            (255,255,255),
            "Montserrat-SemiBold.ttf"
        )

    elif feedback == "wrong":

        frame = overlay_png(
            frame,
            wrong_popup,
            30,
            120
        )

        frame = draw_text(
            frame,
            "Wrong Order",
            (95, 140),
            24,
            (255,255,255),
            "Montserrat-SemiBold.ttf"
        )

    # ==============================
    # TOP UI + COMPLETE
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

        # QUESTION BAR
        frame = overlay_png(
            frame,
            question_bar,
            25,
            20
        )

        if q is not None:

            frame = draw_text(
                frame,
                q["question"],
                (120, 50),
                30,
                (255,255,255),
                "Montserrat-SemiBold.ttf"
            )

        # PROGRESS
        frame = overlay_png(
            frame,
            progress_pill,
            1120,
            40
        )

        frame = draw_centered_text(
            frame,
            f"{current}/{total}",
            1120,
            40,
            115,
            70,
            24
        )

        # LEVEL
        frame = overlay_png(
            frame,
            level_pill,
            1060,
            90
        )

        frame = draw_centered_text(
            frame,
            level,
            1060,
            90,
            175,
            70,
            26
        )

    else:

        frame = draw_text(
            frame,
            "Lesson Complete!",
            (0, 260),
            42,
            (255,255,255),
            "Montserrat-SemiBold.ttf",
            center=True
        )

        frame = draw_text(
            frame,
            f"Score : {lesson.score}",
            (0, 330),
            30,
            (220,220,220),
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