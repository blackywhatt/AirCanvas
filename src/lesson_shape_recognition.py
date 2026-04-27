import cv2
import numpy as np
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont, ImageDraw, Image
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")

hover_shape = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Lesson Questions
# ==============================
questions = [

    # EASY
    {"question": "Select the CIRCLE", "answer": "circle"},
    {"question": "Select the RECTANGLE", "answer": "rectangle"},
    {"question": "Select the STAR", "answer": "star"},
    {"question": "Select the TRIANGLE", "answer": "triangle"},

    # MEDIUM
    {"question": "Select the shape with 4 equal sides", "answer": "square"},
    {"question": "Select the shape with 5 sides", "answer": "pentagon"},
    {"question": "Select the only curved shape", "answer": "circle"},

    # HARD
    {"question": "Select the shape used in flags and rewards", "answer": "star"},
    {"question": "Select the wider version of square", "answer": "rectangle"},
    {"question": "Select the 3-corner shape", "answer": "triangle"},
]

lesson = LessonEngine(questions)

# ==============================
# Shape Positions
# ==============================
shape_positions = {
    "circle": (220, 250),
    "square": (500, 250),
    "triangle": (780, 250),

    "rectangle": (1060, 250),
    "pentagon": (380, 520),
    "star": (860, 520)
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
# Helper: detect shape selection
# ==============================
def detect_selected_shape(ix,iy):

    for shape,(sx,sy) in shape_positions.items():

        dist = np.hypot(ix-sx,iy-sy)

        if dist < 120:
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

    # Rectangle
    rect_color = (0,255,255) if hover_shape == "rectangle" else (255,255,255)
    x,y = shape_positions["rectangle"]
    cv2.rectangle(frame,(x-80,y-50),(x+80,y+50),rect_color,3)

    # Pentagon
    pen_color = (0,255,255) if hover_shape == "pentagon" else (255,255,255)
    x,y = shape_positions["pentagon"]
    pts = np.array([
        [x, y-70],
        [x-65, y-20],
        [x-40, y+60],
        [x+40, y+60],
        [x+65, y-20]
    ], np.int32)
    cv2.polylines(frame,[pts],True,pen_color,3)

    # Star
    star_color = (0,255,255) if hover_shape == "star" else (255,255,255)
    x,y = shape_positions["star"]
    pts = np.array([
        [x, y-70],
        [x-20, y-20],
        [x-70, y-20],
        [x-30, y+10],
        [x-45, y+65],
        [x, y+30],
        [x+45, y+65],
        [x+30, y+10],
        [x+70, y-20],
        [x+20, y-20]
    ], np.int32)
    cv2.polylines(frame,[pts],True,star_color,3)

    # ==============================
    # LESSON RUNNING
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()
        if q is None:
            continue

        current, total = lesson.get_progress()
        frame = draw_text(frame, f"{current}/{total}", (1100,30), 30)

        frame = draw_text(
            frame,
            q["question"],
            (40, 30),
            36,
            (255,255,255),
            "Orbitron-Bold.ttf"
        )

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

        
        if current <=4:
            level = "EASY"
        elif current <=7:
            level = "MEDIUM"
        else:
            level = "HARD"

        frame = draw_text(frame, f"LEVEL: {level}", (1000,70), 28, (0,255,255))
        
        # Feedback
        if lesson.feedback == "correct":

            frame = draw_text(
                frame,
                "Correct!",
                (40, 80),
                30,
                (0,255,0),
                "Montserrat-SemiBold.ttf"
            )

        elif lesson.feedback == "wrong":

            frame = draw_text(
                frame,
                "Try Again",
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
    # Cooldown
    # ==============================
    if answer_cooldown > 0:
        answer_cooldown -= 1

    # ==============================
    # AUTO EXIT AFTER FINISH
    # ==============================
    if lesson.should_exit():
        break

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