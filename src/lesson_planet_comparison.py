import cv2
import numpy as np
import random
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont, ImageDraw, Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")
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

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

planet_images = {}

for planet in planets:
    path = os.path.join(ASSETS_DIR, f"{planet}.png")
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is not None:
        planet_images[planet] = img

# ==============================
# Generate Questions
# ==============================
questions = [

    # EASY
    {"question":"Which planet is BIGGER?", "type":"bigger", "left":"earth", "right":"mars", "answer":"correct"},
    {"question":"Which planet is BIGGER?", "type":"bigger", "left":"jupiter", "right":"venus", "answer":"correct"},
    {"question":"Which planet is SMALLER?", "type":"smaller", "left":"saturn", "right":"neptune", "answer":"correct"},
    {"question":"Which planet is BIGGER?", "type":"bigger", "left":"uranus", "right":"mercury", "answer":"correct"},

    # MEDIUM
    {"question":"Which planet has RINGS?", "type":"rings", "left":"saturn", "right":"earth", "answer":"correct"},
    {"question":"Which planet is known as RED planet?", "type":"red", "left":"mars", "right":"venus", "answer":"correct"},
    {"question":"Which planet do humans live on?", "type":"home", "left":"earth", "right":"neptune", "answer":"correct"},

    # HARD
    {"question":"Which planet is BIGGEST?", "type":"bigger", "left":"jupiter", "right":"saturn", "answer":"correct"},
    {"question":"Which planet is SMALLEST?", "type":"smaller", "left":"mercury", "right":"mars", "answer":"correct"},
    {"question":"Which planet is farther from Sun?", "type":"farther", "left":"venus", "right":"neptune", "answer":"correct"},
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
wrong_popup = cv2.resize(wrong_popup,(230,80))

def get_correct_answer(q):

    left = q["left"]
    right = q["right"]

    if q["type"] == "bigger":
        return left if planet_size[left] > planet_size[right] else right

    elif q["type"] == "smaller":
        return left if planet_size[left] < planet_size[right] else right

    elif q["type"] == "rings":
        return "saturn"

    elif q["type"] == "red":
        return "mars"

    elif q["type"] == "home":
        return "earth"

    elif q["type"] == "farther":
        return left if planet_size[left] > planet_size[right] else right

    return left

# ==============================
# Positions
# ==============================
planet_positions = {
    "left": (350, 390),
    "right": (930, 390)
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
        bbox = draw.textbbox((0,0), text, font=font)

        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        x = (frame.shape[1] - text_w) // 2
        y = pos[1]

        if x < 20:
            x = 20

        draw.text((x, y), text, font=font, fill=color)
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
def detect_selected(ix, iy, q):

    for side, (x, y) in planet_positions.items():

        dist = np.hypot(ix - x, iy - y)

        if dist < 100:
            return q[side]

    return None

def overlay_image(frame, img, x, y, size):
    img = cv2.resize(img, (size, size))

    h, w = img.shape[:2]

    x1 = int(x - w / 2)
    y1 = int(y - h / 2)
    x2 = x1 + w
    y2 = y1 + h

    # Prevent crash (VERY IMPORTANT)
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
def draw_planet(frame, name, x, y, highlight=False):

    color_map = {
        "mercury": (180,180,180),
        "venus": (0,220,255),
        "earth": (255,120,0),
        "mars": (0,0,255),
        "jupiter": (0,165,255),
        "saturn": (0,255,255),
        "uranus": (255,255,0),
        "neptune": (255,0,0)
    }

    # Visual sizes
    radius_map = {
        "mercury": 45,
        "mars": 50,
        "venus": 60,
        "earth": 62,
        "neptune": 70,
        "uranus": 75,
        "saturn": 85,
        "jupiter": 95
    }

    color = color_map[name]
    r = radius_map[name]   

    display_r = int(r * 1.18) if highlight else r

    # Planet body
    if name in planet_images:
        size = int(display_r * 2.2)
        frame = overlay_image(frame, planet_images[name], x, y, size)
    else:
        cv2.circle(frame, (x,y), r, color, -1)

    # Planet name
    label = name.upper()

    img_pil = Image.fromarray(frame)
    draw = ImageDraw.Draw(img_pil)

    font_path = os.path.join(FONT_DIR, "Montserrat-SemiBold.ttf")

    try:
        font = ImageFont.truetype(font_path, 24)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0,0), label, font=font)
    text_w = bbox[2] - bbox[0]

    text_x = x - text_w // 2
    text_y = y + display_r + 35

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

    if not lesson.lesson_finished():

        q = lesson.get_current_question()

        current, total = lesson.get_progress()

        if current <= 3:
            level = "EASY"
        elif current <= 6:
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

        frame = draw_text(
            frame,
            q["question"],
            (120, 50),
            30,
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

        # Draw planets
        frame = draw_planet(
            frame,
            q["left"],
            planet_positions["left"][0],
            planet_positions["left"][1],
            hover_planet == q["left"]
        )        
        frame = draw_planet(
            frame,
            q["right"],
            planet_positions["right"][0],
            planet_positions["right"][1],
            hover_planet == q["right"]
        )
        # Interaction
        if (
            hand_count > 0
            and len(index_positions) > 0
            and lesson.feedback is None
        ):

            ix, iy = index_positions[0]

            cv2.circle(frame,(ix,iy),6,(255,255,255),-1,cv2.LINE_AA)
            cv2.circle(frame,(ix,iy),14,(255,255,255),2,cv2.LINE_AA)

            selected = detect_selected(ix, iy, q)

            if selected:

                if hover_planet == selected:
                    hover_frames += 1
                else:
                    hover_planet = selected
                    hover_frames = 0

                if hover_frames > HOVER_THRESHOLD:
                    correct = get_correct_answer(q)
                    if selected == correct:
                        lesson.check_answer("correct")
                    else:
                        lesson.feedback = "wrong"
                        lesson.feedback_timer = 25
                    hover_frames = 0
                    hover_planet = None

            else:
                hover_planet = None
                hover_frames = 0

        # Feedback
        if lesson.feedback == "correct" and lesson.feedback_timer > 0:

            frame = overlay_png(
                frame,
                correct_popup,
                30,
                120
            )

            frame = draw_text(
                frame,
                "Correct!",
                (105, 140),
                24,
                (255,255,255),
                "Montserrat-SemiBold.ttf"
            )

    elif lesson.feedback == "wrong" and lesson.feedback_timer > 0:

        frame = overlay_png(
            frame,
            wrong_popup,
            30,
            120
        )

        frame = draw_text(
            frame,
            "Try Again",
            (105, 140),
            24,
            (255,255,255),
            "Montserrat-SemiBold.ttf"
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

    if lesson.should_exit():
        break
    
    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()