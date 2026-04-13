import cv2
import numpy as np
from gesture_engine import get_gesture
import os
from PIL import ImageFont, ImageDraw, Image

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
hover_planet = None
hover_frames = 0
HOVER_THRESHOLD = 25

selected_planet = None

# ==============================
# Planet Info
# ==============================
planet_info = {
    "mercury": {"type": "Terrestrial", "moons": "0", "fact": "Closest to Sun"},
    "venus": {"type": "Terrestrial", "moons": "0", "fact": "Hottest planet"},
    "earth": {"type": "Terrestrial", "moons": "1", "fact": "Supports life"},
    "mars": {"type": "Terrestrial", "moons": "2", "fact": "Red planet"}
}

# ==============================
# Positions
# ==============================
planet_positions = {
    "mercury": (250, 350),
    "venus": (450, 350),
    "earth": (650, 350),
    "mars": (850, 350)
}

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Planet Information Exploration"
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
# Detect selection
# ==============================
def detect_selected(ix, iy):

    for name, (x, y) in planet_positions.items():
        dist = np.hypot(ix - x, iy - y)

        if dist < 80:
            return name

    return None

# ==============================
# Draw Planet
# ==============================
def draw_planet(frame, name, x, y, hover=False):

    color_map = {
        "mercury": (200,200,200),
        "venus": (0,200,255),
        "earth": (255,100,0),
        "mars": (0,0,255)
    }

    color = (0,255,255) if hover else color_map[name]

    cv2.circle(frame, (x,y), 50, color, -1)

    frame = draw_text(
        frame,
        name.upper(),
        (x - 50, y + 80),
        22,
        (255,255,255),
        "Montserrat-SemiBold.ttf"
    )

# ==============================
# Draw Info Panel
# ==============================
def draw_info_panel(frame, planet):

    info = planet_info[planet]

    x_start = 950

    cv2.rectangle(frame, (900,150), (1250,500), (50,50,50), -1)

    frame = draw_text(
        frame,
        planet.upper(),
        (920, 180),
        28,
        (0,255,255),
        "Orbitron-Bold.ttf"
    )

    frame = draw_text(
        frame,
        f"Type: {info['type']}",
        (920, 240),
        24,
        (255,255,255),
        "Montserrat-Medium.ttf"
    )

    frame = draw_text(
        frame,
        f"Moons: {info['moons']}",
        (920, 280),
        24,
        (255,255,255),
        "Montserrat-Medium.ttf"
    )

    frame = draw_text(
        frame,
        "Fact:",
        (920, 330),
        24,
        (255,255,255),
        "Montserrat-SemiBold.ttf"
    )

    frame = draw_text(
        frame,
        info["fact"],
        (920, 370),
        22,
        (200,200,200),
        "Montserrat-Medium.ttf"
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

    # Instruction
    frame = draw_text(
        frame,
        "Select a planet to explore",
        (0, 30),
        36,
        (255,255,255),
        "Orbitron-Bold.ttf",
        center=True
    )

    # Draw planets
    for name, (x, y) in planet_positions.items():

        frame = draw_planet(frame, name, x, y, hover_planet == name)

    # Interaction
    if hand_count > 0 and len(index_positions) > 0:

        ix, iy = index_positions[0]

        cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

        selected = detect_selected(ix, iy)

        if selected:

            if hover_planet == selected:
                hover_frames += 1
            else:
                hover_planet = selected
                hover_frames = 0

            if hover_frames > HOVER_THRESHOLD:
                selected_planet = selected

    # Show info panel
    if selected_planet:
        frame = draw_info_panel(frame, selected_planet)

    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()