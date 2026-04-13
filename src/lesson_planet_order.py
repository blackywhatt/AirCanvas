import cv2
import numpy as np
import random
from gesture_engine import get_gesture
import os
from PIL import ImageFont, ImageDraw, Image

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

# Select subset (for simplicity)
selected_planets = random.sample(planet_order[:4], 4)  # first 4 planets
correct_sequence = sorted(selected_planets, key=lambda x: planet_order.index(x))

selected_sequence = []

# ==============================
# Positions
# ==============================
planet_positions = {}

start_x = 250
for i, planet in enumerate(selected_planets):
    planet_positions[planet] = (start_x + i * 250, 350)

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

    # ==============================
    # Instruction
    # ==============================
    frame = draw_text(
        frame,
        "Select planets from CLOSEST to FARTHEST from the Sun",
        (0, 30),
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
        (40, 80),
        28,
        (0,255,255),
        "Montserrat-Medium.ttf"
    )

    # ==============================
    # Hand Interaction
    # ==============================
    if hand_count > 0 and len(index_positions) > 0:

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

                expected = correct_sequence[len(selected_sequence)]

                if selected == expected:
                    selected_sequence.append(selected)
                    feedback = "correct_step"
                else:
                    selected_sequence.clear()
                    feedback = "wrong"

                answer_cooldown = 25
                hover_frames = 0
                hover_planet = None

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
    if selected_sequence == correct_sequence:

        frame = draw_text(
            frame,
            "Completed!",
            (0, 300),
            60,
            (0,255,255),
            "Orbitron-Bold.ttf",
            center=True
        )

    # cooldown
    if answer_cooldown > 0:
        answer_cooldown -= 1

    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()