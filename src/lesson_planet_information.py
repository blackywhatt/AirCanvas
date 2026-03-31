import cv2
import numpy as np
from gesture_engine import get_gesture

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

    cv2.putText(frame, name.upper(),
                (x-60, y+90),
                cv2.FONT_HERSHEY_DUPLEX,
                0.7,
                (255,255,255),
                2)


# ==============================
# Draw Info Panel
# ==============================
def draw_info_panel(frame, planet):

    info = planet_info[planet]

    x_start = 950

    cv2.rectangle(frame, (900,150), (1250,500), (50,50,50), -1)

    cv2.putText(frame, planet.upper(),
                (920,200),
                cv2.FONT_HERSHEY_DUPLEX,
                1,
                (0,255,255),
                2)

    cv2.putText(frame, f"Type: {info['type']}",
                (920,260),
                cv2.FONT_HERSHEY_DUPLEX,
                0.7,
                (255,255,255),
                2)

    cv2.putText(frame, f"Moons: {info['moons']}",
                (920,310),
                cv2.FONT_HERSHEY_DUPLEX,
                0.7,
                (255,255,255),
                2)

    cv2.putText(frame, f"Fact:",
                (920,360),
                cv2.FONT_HERSHEY_DUPLEX,
                0.7,
                (255,255,255),
                2)

    cv2.putText(frame, info["fact"],
                (920,400),
                cv2.FONT_HERSHEY_DUPLEX,
                0.7,
                (200,200,200),
                2)


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
    cv2.putText(frame,"Select a planet to explore",
                (40,60),
                cv2.FONT_HERSHEY_DUPLEX,
                1,
                (255,255,255),
                2)

    # Draw planets
    for name, (x, y) in planet_positions.items():

        draw_planet(frame, name, x, y, hover_planet == name)

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
        draw_info_panel(frame, selected_planet)

    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()