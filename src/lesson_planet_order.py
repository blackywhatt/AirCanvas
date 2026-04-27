import cv2
import numpy as np
import random
from gesture_engine import get_gesture
import os
from PIL import ImageFont, ImageDraw, Image
from lesson_engine import LessonEngine

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
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
selected_sequence = []
planet_positions = {}

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

    start_x = 200

    for i, planet in enumerate(planets):
        planet_positions[planet] = (start_x + i * 250, 320)

load_round()  

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
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
# Detect selection
# ==============================
def detect_selected(ix, iy):

    for name, (x, y) in planet_positions.items():
        dist = np.hypot(ix - x, iy - y)

        if dist < 100:
            return name

    return None


# ==============================
# Draw Planet
# ==============================
def draw_planet(frame, name, x, y, selected=False, hover=False):

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

    if selected:
        color = (0,255,0)
    elif hover:
        color = (0,255,255)
    else:
        color = color_map[name]

    cv2.circle(frame, (x,y), 60, color, -1)

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

    frame = draw_text(
        frame,
        f"LEVEL: {level}",
        (980, 90),
        28,
        (0,255,255),
        "Montserrat-SemiBold.ttf"
    )

    if q is not None:
        frame = draw_text(
            frame,
            q["question"],
            (0, 40),
            34,
            (255,255,255),
            "Orbitron-Bold.ttf",
            center=True
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
    frame = draw_text(
        frame,
        "Your Order: " + " → ".join(selected_sequence),
        (40, 120),
        28,
        (0,255,255),
        "Montserrat-Medium.ttf"
    )

    frame = draw_text(
        frame,
        f"{len(selected_sequence)} / {len(correct_sequence)} selected",
        (40, 160),
        24,
        (255,255,255),
        "Montserrat-Medium.ttf"
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
        frame = draw_text(
            frame,
            "Correct!",
            (40, 220),
            30,
            (0,255,0),
            "Montserrat-SemiBold.ttf"
        )

    elif lesson.feedback == "wrong":
        frame = draw_text(
            frame,
            "Wrong Order! Try Again",
            (40, 220),
            30,
            (0,0,255),
            "Montserrat-SemiBold.ttf"
        )

    # ==============================
    # Completed
    # ==============================
    if lesson.lesson_finished():

        frame = draw_text(
            frame,
            "Completed!",
            (0, 260),
            60,
            (0,255,255),
            "Orbitron-Bold.ttf",
            center=True
        )

        frame = draw_text(
            frame,
            f"Score: {lesson.score}",
            (0, 340),
            40,
            (255,255,255),
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