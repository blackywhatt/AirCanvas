import cv2
import numpy as np
import random
from gesture_engine import get_gesture
from lesson_engine import LessonEngine

hover_color = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Colors
# ==============================
colors = {
    "red": (0,0,255),
    "green": (0,255,0),
    "blue": (255,0,0),
    "yellow": (0,255,255)
}

# ==============================
# Questions
# ==============================
questions = []

for _ in range(5):
    color_name = random.choice(list(colors.keys()))

    questions.append({
        "question": f"Color the circle {color_name.upper()}",
        "answer": color_name
    })

lesson = LessonEngine(questions)

# ==============================
# Color Button Positions
# ==============================
color_positions = {
    "red": (300,600),
    "green": (500,600),
    "blue": (700,600),
    "yellow": (900,600)
}

selected_fill = None
answer_cooldown = 0

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Color Learning Lesson"
cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

# ==============================
# Detect selection
# ==============================
def detect_selected(ix, iy):

    for name, (x, y) in color_positions.items():
        dist = np.hypot(ix - x, iy - y)

        if dist < 60:
            return name

    return None


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
    # Draw Question
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()

        cv2.putText(frame,q["question"],
                    (40,60),
                    cv2.FONT_HERSHEY_DUPLEX,
                    1,
                    (255,255,255),
                    2)

        # Draw shape (circle)
        if selected_fill:
            cv2.circle(frame,(640,300),100,colors[selected_fill],-1)
        else:
            cv2.circle(frame,(640,300),100,(255,255,255),3)

        # Draw color buttons
        for name,(x,y) in color_positions.items():

            color = colors[name]

            if hover_color == name:
                color = (0,255,255)

            cv2.circle(frame,(x,y),40,color,-1)

            cv2.putText(frame,name.upper(),
                        (x-40,y+80),
                        cv2.FONT_HERSHEY_DUPLEX,
                        0.6,
                        (255,255,255),
                        2)

        # ==============================
        # Interaction
        # ==============================
        if hand_count > 0 and len(index_positions) > 0:

            ix, iy = index_positions[0]

            cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

            selected = detect_selected(ix, iy)

            if selected:

                if hover_color == selected:
                    hover_frames += 1
                else:
                    hover_color = selected
                    hover_frames = 0

                if hover_frames > HOVER_THRESHOLD and answer_cooldown == 0:

                    lesson.check_answer(selected)

                    if lesson.feedback == "correct":
                        selected_fill = selected

                    else:
                        selected_fill = None

                    answer_cooldown = 30
                    hover_frames = 0
                    hover_color = None

        # ==============================
        # Feedback
        # ==============================
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