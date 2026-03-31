import cv2
import numpy as np
import random
from gesture_engine import get_gesture

hover_number = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Generate Numbers
# ==============================
numbers = random.sample(range(1,6), 4)  # e.g. [3,1,4,2]
numbers_str = [str(n) for n in numbers]

correct_sequence = sorted(numbers_str)
selected_sequence = []

# ==============================
# Positions
# ==============================
number_positions = {}

start_x = 300
for i, num in enumerate(numbers_str):
    number_positions[num] = (start_x + i * 200, 350)

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Number Ordering Lesson"
cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

answer_cooldown = 0
feedback = None

# ==============================
# Detect selection
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

    # ==============================
    # Draw Instruction
    # ==============================
    cv2.putText(frame,"Select numbers from SMALLEST to LARGEST",
                (40,60),
                cv2.FONT_HERSHEY_DUPLEX,
                1,
                (255,255,255),
                2)

    # ==============================
    # Draw Numbers
    # ==============================
    for num, (x, y) in number_positions.items():

        if num in selected_sequence:
            color = (0,255,0)  # already selected
        elif hover_number == num:
            color = (0,255,255)
        else:
            color = (255,255,255)

        cv2.putText(frame, num,
                    (x-20, y+20),
                    cv2.FONT_HERSHEY_DUPLEX,
                    2,
                    color,
                    3)

    # ==============================
    # Draw Progress
    # ==============================
    cv2.putText(frame,"Your Order: " + " ".join(selected_sequence),
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

        selected_number = detect_selected_number(ix, iy)

        if selected_number and selected_number not in selected_sequence:

            if hover_number == selected_number:
                hover_frames += 1
            else:
                hover_number = selected_number
                hover_frames = 0

            if hover_frames > HOVER_THRESHOLD and answer_cooldown == 0:

                expected = correct_sequence[len(selected_sequence)]

                if selected_number == expected:
                    selected_sequence.append(selected_number)
                    feedback = "correct_step"
                else:
                    selected_sequence.clear()
                    feedback = "wrong"

                answer_cooldown = 25
                hover_frames = 0
                hover_number = None

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
                    (500,500),
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