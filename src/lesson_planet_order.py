import cv2
import numpy as np
import random
from gesture_engine import get_gesture
import os
from PIL import ImageFont, ImageDraw, Image
from lesson_engine import LessonEngine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")
hover_planet = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Planet Order Reference
# ==============================
planet_order = [
    "mercury",
    "venus",
    "earth",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune"
]

questions = [

    {
        "question":"Order planets from CLOSEST to FURTHEST from Sun",
        "planets":["earth","mars","venus","mercury"],
        "answer":["mercury","venus","earth","mars"]
    },

    {
        "question":"Order planets from CLOSEST to FURTHEST from Sun",
        "planets":["neptune","saturn","uranus","jupiter"],
        "answer":["jupiter","saturn","uranus","neptune"]
    },

    {
        "question":"Order planets from CLOSEST to FURTHEST from Sun",
        "planets":["venus","mars","mercury","earth"],
        "answer":["mercury","venus","earth","mars"]
    }

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

selected_sequence = []
planet_positions = {}

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

planet_images = {}

for name in planet_order:
    path = os.path.join(ASSETS_DIR, f"{name}.png")
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is not None:
        planet_images[name] = img

def load_round():

    global selected_sequence
    global planet_positions
    global correct_sequence

    selected_sequence.clear()
    planet_positions.clear()

    q = lesson.get_current_question()

    if q is None:
        return

    planets = q["planets"]
    correct_sequence = q["answer"]

    start_x = 120

    for i, planet in enumerate(planets):
        planet_positions[planet] = (start_x + i * 320, 360)

load_round()  

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Planet Order Lesson"
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
def detect_selected(ix, iy):

    for name, (x, y) in planet_positions.items():
        dist = np.hypot(ix - x, iy - y)

        if dist < 100:
            return name

    return None

def overlay_image(frame, img, x, y, size):
    img = cv2.resize(img, (size, size))

    h, w = img.shape[:2]

    x1 = int(x - w / 2)
    y1 = int(y - h / 2)
    x2 = x1 + w
    y2 = y1 + h

    if x1 < 0 or y1 < 0 or x2 > frame.shape[1] or y2 > frame.shape[0]:
        return frame

    if img.shape[2] == 4:
        alpha = img[:, :, 3] / 255.0
        for c in range(3):
            frame[y1:y2, x1:x2, c] = (
                alpha * img[:, :, c] +
                (1 - alpha) * frame[y1:y2, x1:x2, c]
            )
    else:
        frame[y1:y2, x1:x2] = img

    return frame

# ==============================
# Draw Planet
# ==============================
def draw_planet(frame, name, x, y, selected=False, hover=False):

    r = 60
    display_r = int(r * 1.18) if hover else r

    if selected:
        display_r = int(display_r * 1.15)

    # Draw image
    if name in planet_images:
        size = int(display_r * 2.2)
        frame = overlay_image(frame, planet_images[name], x, y, size)
    else:
        cv2.circle(frame, (x,y), r, (255,255,255), -1)

    # Label
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
    # ==============================
    # Instruction
    # ==============================
    q = lesson.get_current_question()

    current, total = lesson.get_progress()

    if current == 0:
        level = "EASY"
    elif current == 1:
        level = "MEDIUM"
    else:
        level = "HARD"

    # ==============================
    # QUESTION BAR
    # ==============================
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
            28,
            (255,255,255),
            "Montserrat-SemiBold.ttf"
        )

    # ==============================
    # PROGRESS
    # ==============================
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

    # ==============================
    # LEVEL
    # ==============================
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

    # ==============================
    # Draw Planets
    # ==============================
    for name, (x, y) in planet_positions.items():

        frame = draw_planet(
            frame,
            name,
            x,
            y,
            selected=name in selected_sequence,
            hover=(hover_planet == name)
        )

    # ==============================
    # Show Progress
    # ==============================
    sequence_text = "  →  ".join(selected_sequence)

    frame = draw_text(
        frame,
        sequence_text,
        (0, 620),
        42,
        (0,255,255),
        "Montserrat-SemiBold.ttf",
        center=True
    )
    
    # ==============================
    # Hand Interaction
    # ==============================
    if not lesson.lesson_finished() and hand_count > 0 and len(index_positions) > 0:

        ix, iy = index_positions[0]

        cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

        selected = detect_selected(ix, iy)

        if selected and selected not in selected_sequence:

            if hover_planet == selected:
                hover_frames += 1
            else:
                hover_planet = selected
                hover_frames = 0

            if hover_frames > HOVER_THRESHOLD and answer_cooldown == 0:

                selected_sequence.append(selected)

                index_now = len(selected_sequence) - 1

                # Wrong immediately
                if selected_sequence[index_now] != correct_sequence[index_now]:

                    lesson.feedback = "wrong"
                    lesson.feedback_timer = 25
                    selected_sequence.clear()

                # Completed correctly
                elif len(selected_sequence) == len(correct_sequence):

                    lesson.feedback = "correct"
                    lesson.feedback_timer = 25

                    lesson.score += 1
                    lesson.current_question += 1

                    selected_sequence.clear()

                    if not lesson.lesson_finished():
                        load_round()

                answer_cooldown = 25
                hover_frames = 0
                hover_planet = None

    if lesson.feedback == "correct":

        frame = overlay_png(
            frame,
            correct_popup,
            30,
            120
        )

        frame = draw_text(
            frame,
            "Correct Order!",
            (80, 140),
            22,
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
            "Wrong Order",
            (95, 140),
            24,
            (255,255,255),
            "Montserrat-SemiBold.ttf"
        )

    # ==============================
    # Completed
    # ==============================
    if lesson.lesson_finished():

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

    if answer_cooldown > 0:
        answer_cooldown -= 1

    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()