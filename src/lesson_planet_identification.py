import cv2
import numpy as np
from gesture_engine import get_gesture
from lesson_engine import LessonEngine

hover_planet = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Questions
# ==============================
questions = [
    {"question": "Select MERCURY", "answer": "mercury"},
    {"question": "Select VENUS", "answer": "venus"},
    {"question": "Select EARTH", "answer": "earth"},
    {"question": "Select MARS", "answer": "mars"}
]

lesson = LessonEngine(questions)

# ==============================
# Planet Positions
# ==============================
planet_positions = {
    "mercury": (250, 360),
    "venus": (500, 360),
    "earth": (750, 360),
    "mars": (1000, 360)
}

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Planet Identification Lesson"
cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

answer_cooldown = 0

# ==============================
# Detect selection
# ==============================
def detect_selected_planet(ix, iy):

    for name, (px, py) in planet_positions.items():
        dist = np.hypot(ix - px, iy - py)

        if dist < 80:
            return name

    return None


# ==============================
# Draw Planets (simple circles)
# ==============================
def draw_planets(frame):

    for name, (x, y) in planet_positions.items():

        if name == "mercury":
            color = (200,200,200)
        elif name == "venus":
            color = (0,200,255)
        elif name == "earth":
            color = (255,100,0)
        elif name == "mars":
            color = (0,0,255)

        if hover_planet == name:
            color = (0,255,255)

        cv2.circle(frame, (x,y), 50, color, -1)

        cv2.putText(frame, name.upper(),
                    (x-60, y+90),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.7,
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

    draw_planets(frame)

    # ==============================
    # Lesson Running
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()

        cv2.putText(frame,q["question"],
                    (40,60),
                    cv2.FONT_HERSHEY_DUPLEX,
                    1,
                    (255,255,255),
                    2)

        if hand_count > 0 and len(index_positions) > 0:

            ix, iy = index_positions[0]

            cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

            selected = detect_selected_planet(ix, iy)

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
                        (40,120),
                        cv2.FONT_HERSHEY_DUPLEX,
                        1,
                        (0,255,0),
                        2)

        elif lesson.feedback == "wrong":
            cv2.putText(frame,"Try Again",
                        (40,120),
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