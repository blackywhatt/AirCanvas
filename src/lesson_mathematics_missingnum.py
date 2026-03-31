import cv2
import numpy as np
import random
from gesture_engine import get_gesture
from lesson_engine import LessonEngine

hover_number = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Generate Questions
# ==============================
questions = []

for _ in range(5):
    total = random.randint(2, 6)
    first = random.randint(1, total - 1)
    missing = total - first

    questions.append({
        "question": f"{first} + _ = {total}",
        "answer": str(missing)
    })

lesson = LessonEngine(questions)

# ==============================
# Number Positions
# ==============================
number_positions = {
    "1": (300, 500),
    "2": (500, 500),
    "3": (700, 500),
    "4": (900, 500),
    "5": (1100, 500)
}

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Missing Number Lesson"
cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

answer_cooldown = 0

# ==============================
# Detect number selection
# ==============================
def detect_selected_number(ix, iy):

    for num, (nx, ny) in number_positions.items():
        dist = np.hypot(ix - nx, iy - ny)

        if dist < 80:
            return num

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
    # Lesson Running
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()

        # Draw equation BIG (center)
        cv2.putText(frame, q["question"],
                    (400,250),
                    cv2.FONT_HERSHEY_DUPLEX,
                    2,
                    (255,255,255),
                    3)

        # Draw answer options
        for num, (x, y) in number_positions.items():

            color = (0,255,255) if hover_number == num else (255,255,255)

            cv2.putText(frame, num,
                        (x-20, y+20),
                        cv2.FONT_HERSHEY_DUPLEX,
                        2,
                        color,
                        3)

        # ==============================
        # Hand Interaction
        # ==============================
        if hand_count > 0 and len(index_positions) > 0:

            ix, iy = index_positions[0]

            cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

            selected_number = detect_selected_number(ix, iy)

            if selected_number:

                if hover_number == selected_number:
                    hover_frames += 1
                else:
                    hover_number = selected_number
                    hover_frames = 0

                if hover_frames > HOVER_THRESHOLD and answer_cooldown == 0:
                    lesson.check_answer(selected_number)
                    answer_cooldown = 30
                    hover_frames = 0
                    hover_number = None

        # ==============================
        # Feedback
        # ==============================
        if lesson.feedback == "correct":
            cv2.putText(frame,"Correct!",
                        (40,100),
                        cv2.FONT_HERSHEY_DUPLEX,
                        1,
                        (0,255,0),
                        2)

        elif lesson.feedback == "wrong":
            cv2.putText(frame,"Try Again",
                        (40,100),
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

    # cooldown
    if answer_cooldown > 0:
        answer_cooldown -= 1

    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()