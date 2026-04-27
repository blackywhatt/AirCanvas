import cv2
import numpy as np
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
from shapes_mode import get_perfect_shape
import os
from PIL import ImageFont, ImageDraw, Image

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
# ==============================
# LESSON QUESTIONS
# ==============================
questions = [

    # EASY
    {"question": "EASY 1: Draw a CIRCLE", "answer": "circle"},
    {"question": "EASY 2: Draw a TRIANGLE", "answer": "triangle"},
    {"question": "EASY 3: Draw a SQUARE", "answer": "square"},
    {"question": "EASY 4: Draw another CIRCLE", "answer": "circle"},

    # MEDIUM
    {"question": "MEDIUM 1: Draw a RECTANGLE", "answer": "rectangle"},
    {"question": "MEDIUM 2: Draw a PENTAGON", "answer": "pentagon"},
    {"question": "MEDIUM 3: Draw a STAR", "answer": "star"},

    # HARD
    {"question": "HARD 1: Draw shape with 3 sides", "answer": "triangle"},
    {"question": "HARD 2: Draw shape with 5 sides", "answer": "pentagon"},
    {"question": "HARD 3: Draw reward shape", "answer": "star"},
]

lesson = LessonEngine(questions)


# ==============================
# DRAW STORAGE
# ==============================
current_stroke = []
thickness = 3

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
    if not lesson.lesson_finished() and hand_count == 1 and ix is not None:

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

                        x,y,w,h = cv2.boundingRect(approx)
                        ratio = w / float(h)

                        if 0.85 <= ratio <= 1.15:
                            detected_shape = "square"
                        else:
                            detected_shape = "rectangle"

                    elif sides == 5:
                        detected_shape = "pentagon"

                    elif sides >= 8:
                        detected_shape = "star"

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
        if q is None:
            continue
        
        current, total = lesson.get_progress()
        if current <=4:
            level = "EASY"
        elif current <=7:
            level = "MEDIUM"
        else:
            level = "HARD"

        frame = draw_text(frame, f"LEVEL: {level}", (1000,70), 28, (0,255,255))

        frame = draw_text(frame, f"{current}/{total}", (1100,30), 30)

        frame = draw_text(
            frame,
            q["question"],
            (40, 30),
            36,
            (255,255,255),
            "Orbitron-Bold.ttf"
        )

        if lesson.feedback == "correct":

            frame = draw_text(
                frame,
                "Great Job!",
                (40, 80),
                30,
                (0,255,0),
                "Montserrat-SemiBold.ttf"
            )

        elif lesson.feedback == "wrong":

            frame = draw_text(
                frame,
                "Wrong Shape! Try Again",
                (40, 80),
                30,
                (0,0,255),
                "Montserrat-SemiBold.ttf"
            )

    # ==============================
    # LESSON FINISHED
    # ==============================
    else:

        frame = draw_text(
            frame,
            "Lesson Complete!",
            (40, 30),
            36,
            (0,255,255),
            "Orbitron-Bold.ttf"
        )

        frame = draw_text(
            frame,
            f"Score: {lesson.score}",
            (40, 80),
            30,
            (255,255,255),
            "Montserrat-SemiBold.ttf"
        )

    # ==============================
    # AUTO EXIT AFTER FINISH
    # ==============================
    if lesson.should_exit():
        break
 
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