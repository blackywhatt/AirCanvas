import cv2
import numpy as np
import random
from gesture_engine import get_gesture
from lesson_engine import LessonEngine

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

# ==============================
# Generate Questions
# ==============================
questions = []

for _ in range(5):
    p1, p2 = random.sample(planets, 2)

    if planet_size[p1] > planet_size[p2]:
        answer = p1
    else:
        answer = p2

    questions.append({
        "question": f"Which is bigger? {p1.upper()} or {p2.upper()}",
        "answer": answer,
        "left": p1,
        "right": p2
    })

lesson = LessonEngine(questions)

# ==============================
# Positions
# ==============================
planet_positions = {
    "left": (400, 350),
    "right": (900, 350)
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

answer_cooldown = 0

# ==============================
# Detect selection
# ==============================
def detect_selected(ix, iy, q):

    for side, (x, y) in planet_positions.items():

        dist = np.hypot(ix - x, iy - y)

        if dist < 100:
            return q[side]

    return None


# ==============================
# Draw Planet
# ==============================
def draw_planet(frame, name, x, y, highlight=False):

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

    color = (0,255,255) if highlight else color_map[name]

    cv2.circle(frame, (x,y), 70, color, -1)

    cv2.putText(frame, name.upper(),
                (x-80, y+110),
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

    lesson.update()

    if not lesson.lesson_finished():

        q = lesson.get_current_question()

        # Question
        cv2.putText(frame,q["question"],
                    (100,80),
                    cv2.FONT_HERSHEY_DUPLEX,
                    1,
                    (255,255,255),
                    2)

        # Draw planets
        draw_planet(frame, q["left"], 400, 350, hover_planet == q["left"])
        draw_planet(frame, q["right"], 900, 350, hover_planet == q["right"])

        # Interaction
        if hand_count > 0 and len(index_positions) > 0:

            ix, iy = index_positions[0]

            cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

            selected = detect_selected(ix, iy, q)

            if selected:

                if hover_planet == selected:
                    hover_frames += 1
                else:
                    hover_planet = selected
                    hover_frames = 0

                if hover_frames > HOVER_THRESHOLD and answer_cooldown == 0:
                    lesson.check_answer(selected)
                    answer_cooldown = 30
                    hover_frames = 0
                    hover_planet = None

        # Feedback
        if lesson.feedback == "correct":
            cv2.putText(frame,"Correct!",
                        (40,150),
                        cv2.FONT_HERSHEY_DUPLEX,
                        1,
                        (0,255,0),
                        2)

        elif lesson.feedback == "wrong":
            cv2.putText(frame,"Try Again",
                        (40,150),
                        cv2.FONT_HERSHEY_DUPLEX,
                        1,
                        (0,0,255),
                        2)

    else:
        cv2.putText(frame,"Lesson Complete!",
                    (40,60),
                    cv2.FONT_HERSHEY_DUPLEX,
                    1,
                    (0,255,255),
                    2)

        cv2.putText(frame,f"Score: {lesson.score}",
                    (40,120),
                    cv2.FONT_HERSHEY_DUPLEX,
                    1,
                    (255,255,255),
                    2)

    if answer_cooldown > 0:
        answer_cooldown -= 1

    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()