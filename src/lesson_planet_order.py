import cv2
import numpy as np
import random
from gesture_engine import get_gesture

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

    cv2.putText(frame, name.upper(),
                (x-80, y+100),
                cv2.FONT_HERSHEY_DUPLEX,
                0.8,
                (255,255,255),
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

    # ==============================
    # Instruction
    # ==============================
    cv2.putText(frame,"Select planets from CLOSEST to FARTHEST from the Sun",
                (40,60),
                cv2.FONT_HERSHEY_DUPLEX,
                1,
                (255,255,255),
                2)

    # ==============================
    # Draw Planets
    # ==============================
    for name, (x, y) in planet_positions.items():

        draw_planet(
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
    cv2.putText(frame,"Your Order: " + " → ".join(selected_sequence),
                (40,120),
                cv2.FONT_HERSHEY_DUPLEX,
                1,
                (0,255,255),
                2)

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
        cv2.putText(frame,"Good!",
                    (40,180),
                    cv2.FONT_HERSHEY_DUPLEX,
                    1,
                    (0,255,0),
                    2)

    elif feedback == "wrong":
        cv2.putText(frame,"Wrong Order! Try Again",
                    (40,180),
                    cv2.FONT_HERSHEY_DUPLEX,
                    1,
                    (0,0,255),
                    2)

    # ==============================
    # Completed
    # ==============================
    if selected_sequence == correct_sequence:

        cv2.putText(frame,"Completed!",
                    (450,500),
                    cv2.FONT_HERSHEY_DUPLEX,
                    2,
                    (0,255,255),
                    3)

    # cooldown
    if answer_cooldown > 0:
        answer_cooldown -= 1

    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()