import cv2
import numpy as np
import random
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont, ImageDraw, Image
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")
ASSETS_DIR = os.path.join(BASE_DIR, "..", "assets")
hover_number = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# LOAD OBJECT PNGS
# ==============================
object_images = {}

for obj in ["star","phone","ball","pizza"]:

    path = os.path.join(ASSETS_DIR, f"{obj}.png")

    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)

    if img is not None:
        object_images[obj] = img

# ==============================
# Generate Questions
# ==============================
questions = []

object_types = ["star","phone","ball","pizza"]

# ==============================
# ADDITION QUESTIONS
# ==============================
for _ in range(5):

    a = random.randint(1,3)
    b = random.randint(1,3)

    questions.append({

        "operation":"+",
        "a":a,
        "b":b,
        "answer":str(a+b),
        "object":random.choice(object_types)

    })

# ==============================
# SUBTRACTION QUESTIONS
# ==============================
for _ in range(5):

    a = random.randint(3,6)
    b = random.randint(1,a-1)

    questions.append({

        "operation":"-",
        "a":a,
        "b":b,
        "answer":str(a-b),
        "object":random.choice(object_types)

    })

random.shuffle(questions)

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

correct_popup = cv2.imread(
    "assets/ui/correct_popup.png",
    cv2.IMREAD_UNCHANGED
)
correct_popup = cv2.resize(correct_popup,(230,80))

wrong_popup = cv2.imread(
    "assets/ui/wrong_popup.png",
    cv2.IMREAD_UNCHANGED
)
wrong_popup = cv2.resize(wrong_popup,(230,80))

# ==============================
# Number Positions
# ==============================
number_positions = {
    "1": (190,240),
    "2": (370,240),
    "3": (550,240),
    "4": (730,240),
    "5": (910,240),
    "6": (1090,240)
}

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Basic Addition Lesson"
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

# ==============================
# Detect selection
# ==============================
def detect_selected_number(ix, iy):

    for num, (nx, ny) in number_positions.items():
        dist = np.hypot(ix - nx, iy - ny)

        if dist < 70:
            return num

    return None

def draw_objects(frame, count, center_x, object_name):

    img = object_images[object_name]

    # Use a slightly smaller size so 6 objects never feel cramped
    obj_size = 80
    gap_x = 90
    gap_y = 95

    # One row for small counts, two rows for larger counts
    if count <= 3:
        y = 430
        total_width = (count - 1) * gap_x
        start_x = center_x - total_width // 2

        positions = [(start_x + i * gap_x, y) for i in range(count)]

    else:
        top_count = (count + 1) // 2
        bottom_count = count - top_count

        top_total_width = (top_count - 1) * gap_x
        bottom_total_width = (bottom_count - 1) * gap_x

        top_start_x = center_x - top_total_width // 2
        bottom_start_x = center_x - bottom_total_width // 2

        positions = []

        # top row
        for i in range(top_count):
            positions.append((top_start_x + i * gap_x, 400))

        # bottom row
        for i in range(bottom_count):
            positions.append((bottom_start_x + i * gap_x, 495))

    for x, y in positions:

        resized = cv2.resize(img, (obj_size, obj_size))
        h, w = resized.shape[:2]

        x1 = x - w // 2
        y1 = y - h // 2

        if x1 < 0 or y1 < 0 or x1 + w > frame.shape[1] or y1 + h > frame.shape[0]:
            continue

        alpha = resized[:, :, 3] / 255.0

        for c in range(3):
            frame[y1:y1+h, x1:x1+w, c] = (
                alpha * resized[:, :, c] +
                (1 - alpha) * frame[y1:y1+h, x1:x1+w, c]
            )
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
        # QUESTION BAR
        frame = overlay_png(
            frame,
            question_bar,
            25,
            20
        )

        frame = draw_text(
            frame,
            "Solve the math question",
            (130,50),
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

        frame = draw_text(
            frame,
            f"{current}/{total}",
            (1150,55),
            26,
            (255,255,255),
            "Montserrat-SemiBold.ttf",
        )

        draw_objects(
            frame,
            q["a"],
            320,
            q["object"]
        )
        
        frame = draw_text(
            frame,
            q["operation"],
            (545,395),
            72,
            (255,255,255),
            "Orbitron-Bold.ttf"
        )
        
        draw_objects(
            frame,
            q["b"],
            820,
            q["object"]
        )
   
        frame = draw_text(
            frame,
            "=",
            (965,395),
            72,
            (255,255,255),
            "Orbitron-Bold.ttf"
        )
        
        # Draw question mark
        frame = draw_text(
            frame,
            "?",
            (1110,395),
            64,
            (0,255,255),
            "Orbitron-Bold.ttf"
        )

        # ==============================
        # Draw Answer Choices
        # ==============================
        for num, (x, y) in number_positions.items():

            hovered = (hover_number == num)

            radius = 58 if hovered else 50

            color = (0,255,255) if hovered else (255,255,255)

            cv2.circle(
                frame,
                (x,y),
                radius,
                color,
                3,
                cv2.LINE_AA
            )

            frame = draw_text(
                frame,
                num,
                (x-14,y-26),
                38,
                (255,255,255),
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

            frame = overlay_png(
                frame,
                correct_popup,
                30,
                120
            )

            frame = draw_text(
                frame,
                "Correct!",
                (105,140),
                24,
                (255,255,255),
                "Montserrat-SemiBold.ttf"
            )

        elif lesson.feedback == "wrong":

            frame = overlay_png(
                frame,
                wrong_popup,
                30,
                120
            )

            frame = draw_text(
                frame,
                "Try Again",
                (105,140),
                24,
                (255,255,255),
                "Montserrat-SemiBold.ttf"
            )

    else:
        frame = draw_text(
            frame,
            "Lesson Complete!",
            (0,260),
            42,
            (255,255,255),
            "Montserrat-SemiBold.ttf",
            center=True
        )

        frame = draw_text(
            frame,
            f"Score : {lesson.score}",
            (0,330),
            30,
            (220,220,220),
            "Montserrat-SemiBold.ttf",
            center=True
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