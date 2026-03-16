import cv2
import numpy as np
from gesture_engine import get_gesture
from lesson_engine import LessonEngine

hover_shape = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Lesson Questions
# ==============================
questions = [
    {"question": "Select the CIRCLE", "answer": "circle"},
    {"question": "Select the SQUARE", "answer": "square"},
    {"question": "Select the TRIANGLE", "answer": "triangle"}
]

lesson = LessonEngine(questions)

# ==============================
# Shape Positions
# ==============================
shape_positions = {
    "circle": (320, 360),
    "square": (640, 360),
    "triangle": (960, 360)
}

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Shape Recognition Lesson"
cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

answer_cooldown = 0

# ==============================
# Helper: detect shape selection
# ==============================
def detect_selected_shape(ix,iy):

    for shape,(sx,sy) in shape_positions.items():

        dist = np.hypot(ix-sx,iy-sy)

        if dist < 100:
            return shape

    return None


# ==============================
# Main Loop
# ==============================
while cap.isOpened():

    ret,frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame,1)
    frame = cv2.resize(frame,(1280,720))

    gesture,index_positions,thumb_positions,hand_count,frame = get_gesture(frame)

    lesson.update()

    # ==============================
    # DEBUG INFO
    # ==============================
    cv2.putText(frame,f"Hands: {hand_count}",(40,160),
                cv2.FONT_HERSHEY_DUPLEX,0.7,(255,255,0),1)

    cv2.putText(frame,f"Gesture: {gesture}",(40,190),
                cv2.FONT_HERSHEY_DUPLEX,0.7,(255,255,0),1)

    # ==============================
    # DRAW SHAPES
    # ==============================

    # Circle
    circle_color = (0,255,255) if hover_shape == "circle" else (255,255,255)
    cv2.circle(frame,shape_positions["circle"],60,circle_color,3)

    # Square
    square_color = (0,255,255) if hover_shape == "square" else (255,255,255)
    x,y = shape_positions["square"]
    cv2.rectangle(frame,(x-60,y-60),(x+60,y+60),square_color,3)

    # Triangle
    triangle_color = (0,255,255) if hover_shape == "triangle" else (255,255,255)
    x,y = shape_positions["triangle"]
    pts = np.array([[x,y-70],[x-60,y+60],[x+60,y+60]],np.int32)
    cv2.polylines(frame,[pts],True,triangle_color,3)

    # ==============================
    # LESSON RUNNING
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

            ix,iy = index_positions[0]

            # show cursor
            cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

            selected_shape = detect_selected_shape(ix,iy)

            if selected_shape:

                if hover_shape == selected_shape:
                    hover_frames += 1
                else:
                    hover_shape = selected_shape
                    hover_frames = 0

                if hover_frames > HOVER_THRESHOLD and answer_cooldown == 0:
                    lesson.check_answer(selected_shape)
                    answer_cooldown = 30
                    hover_frames = 0
                    hover_shape = None

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

    # ==============================
    # LESSON FINISHED
    # ==============================
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

    # ==============================
    # Cooldown
    # ==============================
    if answer_cooldown > 0:
        answer_cooldown -= 1

    # ==============================
    # Display
    # ==============================
    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

# ==============================
# Cleanup
# ==============================
cap.release()
cv2.destroyAllWindows()