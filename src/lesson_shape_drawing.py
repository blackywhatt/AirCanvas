import cv2
import numpy as np
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
from shapes_mode import get_perfect_shape


# ==============================
# LESSON QUESTIONS
# ==============================
questions = [
    {"question": "Draw a CIRCLE", "answer": "circle"},
    {"question": "Draw a SQUARE", "answer": "square"},
    {"question": "Draw a TRIANGLE", "answer": "triangle"}
]

lesson = LessonEngine(questions)


# ==============================
# DRAW STORAGE
# ==============================
current_stroke = []
thickness = 3


# ==============================
# RENDER CURRENT STROKE
# ==============================
def render_stroke(frame):

    if len(current_stroke) > 1:
        pts = np.array(current_stroke, np.int32)
        cv2.polylines(frame, [pts], False, (220,220,220), thickness)


# ==============================
# CAMERA SETUP
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Shape Drawing Lesson"

cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)


# ==============================
# MAIN LOOP
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
    # GET FINGER POSITION
    # ==============================
    if hand_count == 1 and len(index_positions) >= 1:
        ix,iy = index_positions[0]
    else:
        ix,iy = None,None


    # ==============================
    # DRAWING LOGIC
    # ==============================
    if hand_count == 1 and ix is not None:

        # cursor
        cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

        if gesture == "draw":

            current_stroke.append((ix,iy))

        else:

            if len(current_stroke) > 15:

                stroke = current_stroke.copy()

                # ----------------------------
                # 1. Auto close shape
                # ----------------------------
                if np.linalg.norm(np.array(stroke[0]) - np.array(stroke[-1])) > 20:
                    stroke.append(stroke[0])

                # ----------------------------
                # 2. Convert stroke to image
                # ----------------------------
                canvas = np.zeros((720,1280), dtype=np.uint8)

                for i in range(1, len(stroke)):
                    cv2.line(canvas, stroke[i-1], stroke[i], 255, 8)

                # ----------------------------
                # 3. Find contour
                # ----------------------------
                contours, _ = cv2.findContours(canvas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                detected_shape = "unknown"

                if contours:
                    cnt = max(contours, key=cv2.contourArea)

                    peri = cv2.arcLength(cnt, True)
                    approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)

                    sides = len(approx)

                    if sides == 3:
                        detected_shape = "triangle"

                    elif sides == 4:
                        detected_shape = "square"

                    else:
                        area = cv2.contourArea(cnt)
                        circularity = 4 * np.pi * area / (peri * peri)

                        if circularity > 0.65:
                            detected_shape = "circle"

                lesson.check_answer(detected_shape)

            current_stroke.clear()


    # ==============================
    # DRAW STROKE
    # ==============================
    render_stroke(frame)


    # ==============================
    # LESSON RUNNING
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()

        cv2.putText(frame,
                    q["question"],
                    (40,60),
                    cv2.FONT_HERSHEY_DUPLEX,
                    1,
                    (255,255,255),
                    2)

        if lesson.feedback == "correct":

            cv2.putText(frame,
                        "Correct!",
                        (40,120),
                        cv2.FONT_HERSHEY_DUPLEX,
                        1,
                        (0,255,0),
                        2)

        elif lesson.feedback == "wrong":

            cv2.putText(frame,
                        "Try Again",
                        (40,120),
                        cv2.FONT_HERSHEY_DUPLEX,
                        1,
                        (0,0,255),
                        2)


    # ==============================
    # LESSON FINISHED
    # ==============================
    else:

        cv2.putText(frame,
                    "Lesson Complete!",
                    (40,60),
                    cv2.FONT_HERSHEY_DUPLEX,
                    1,
                    (0,255,255),
                    2)

        cv2.putText(frame,
                    f"Score: {lesson.score}",
                    (40,120),
                    cv2.FONT_HERSHEY_DUPLEX,
                    1,
                    (255,255,255),
                    2)


    # ==============================
    # DISPLAY
    # ==============================
    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break


# ==============================
# CLEANUP
# ==============================
cap.release()
cv2.destroyAllWindows()