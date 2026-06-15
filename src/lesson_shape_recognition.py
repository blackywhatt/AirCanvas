import cv2
import numpy as np
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont, ImageDraw, Image
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")

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
# LOAD UI ASSETS
# ==============================
question_bar = cv2.imread(
    "assets/ui/question_bar.png",
    cv2.IMREAD_UNCHANGED
)
question_bar = cv2.resize(
    question_bar,
    (900, 110)
)

progress_pill = cv2.imread(
    "assets/ui/progress_pill.png",
    cv2.IMREAD_UNCHANGED
)
progress_pill = cv2.resize(
    progress_pill,
    (115, 70)
)

level_pill = cv2.imread(
    "assets/ui/level_pill.png",
    cv2.IMREAD_UNCHANGED
)
level_pill = cv2.resize(
    level_pill,
    (175, 70)
)

correct_popup = cv2.imread(
    "assets/ui/correct_popup.png",
    cv2.IMREAD_UNCHANGED
)
correct_popup = cv2.resize(
    correct_popup,
    (230, 80)
)

wrong_popup = cv2.imread(
    "assets/ui/wrong_popup.png",
    cv2.IMREAD_UNCHANGED
)
wrong_popup = cv2.resize(
    wrong_popup,
    (230, 80)
)

# ==============================
# Shape Positions
# ==============================
shape_positions = {
    "circle": (250, 240),
    "square": (640, 240),
    "triangle": (1030, 240),
    "rectangle": (250, 520),
    "pentagon": (640, 520),
    "star": (1030, 520)
}

# ==============================
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Shape Recognition Lesson"
cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

answer_cooldown = 0

def draw_text(frame, text, pos, size=40, color=(255,255,255),
              font_name="Montserrat-Medium.ttf", center=False):

    font_path = os.path.join(FONT_DIR, font_name)

    try:
        font = ImageFont.truetype(font_path, size)
    except:
        return frame

    # Convert ONLY once safely
    pil_image = Image.fromarray(frame)
    draw = ImageDraw.Draw(pil_image)

    if center:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]

        x = (frame.shape[1] - text_w) // 2
        draw.text((x, pos[1]), text, font=font, fill=color)

    else:
        draw.text(pos, text, font=font, fill=color)

    return np.array(pil_image)

def draw_centered_text(frame, text, box_x, box_y, box_w, box_h,
                       size=30,
                       color=(255,255,255),
                       font_name="Montserrat-SemiBold.ttf"):

    font_path = os.path.join(FONT_DIR, font_name)

    try:
        font = ImageFont.truetype(font_path, size)
    except:
        return frame

    pil_image = Image.fromarray(frame)
    draw = ImageDraw.Draw(pil_image)

    bbox = draw.textbbox((0,0), text, font=font)

    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = box_x + (box_w - text_w) // 2
    y = box_y + (box_h - text_h) // 2 - 8

    draw.text((x, y), text, font=font, fill=color)

    return np.array(pil_image)
# ==============================
# MODERN GLASS PANEL
# ==============================
def draw_panel(frame, x1, y1, x2, y2,
               color=(30,30,40),
               alpha=0.45):

    overlay = frame.copy()

    # filled rectangle
    cv2.rectangle(
        overlay,
        (x1, y1),
        (x2, y2),
        color,
        -1
    )

    # transparency blend
    frame = cv2.addWeighted(
        overlay,
        alpha,
        frame,
        1 - alpha,
        0
    )

    # subtle border
    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        (255,255,255),
        1,
        cv2.LINE_AA
    )

    return frame

# ==============================
# CLEAN SHAPE DRAWING 
# ==============================
def draw_glowing_shape(draw_function, color):

    # just draw normal sharp shape
    draw_function(frame, color, 4)

# ==============================
# PNG OVERLAY
# ==============================
def overlay_png(frame, png, x, y):

    h, w = png.shape[:2]

    # Prevent overflow
    if y + h > frame.shape[0] or x + w > frame.shape[1]:
        return frame

    # Split channels
    b, g, r, a = cv2.split(png)

    overlay_color = cv2.merge((b, g, r))

    mask = a.astype(float) / 255.0
    inverse_mask = 1.0 - mask

    # Blend
    for c in range(3):
        frame[y:y+h, x:x+w, c] = (
            mask * overlay_color[:,:,c] +
            inverse_mask * frame[y:y+h, x:x+w, c]
        )

    return frame

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
    
    # ==============================
    # CAMERA ENHANCEMENT
    # ==============================
    frame = cv2.convertScaleAbs(
        frame,
        alpha=1.12,
        beta=5
    )

    gesture,index_positions,thumb_positions,hand_count,frame = get_gesture(frame)

    lesson.update()

    # ==============================
    # DRAW SHAPES
    # ==============================
    # Circle
    circle_color = (255,255,255) if hover_shape == "circle" else (255, 196, 87)

    def draw_circle(target, color, thickness):
        radius = 68 if hover_shape == "circle" else 60
        cv2.circle(
            target,
            shape_positions["circle"],
            radius,
            color,
            thickness,
            cv2.LINE_AA
        )

    draw_glowing_shape(draw_circle, circle_color)


    # Square
    square_color = (255,255,255) if hover_shape == "square" else (90, 200, 255)

    def draw_square(target, color, thickness):
        x,y = shape_positions["square"]

        size = 68 if hover_shape == "square" else 60

        cv2.rectangle(
            target,
            (x-size,y-size),
            (x+size,y+size),
            color,
            thickness,
            cv2.LINE_AA
        )

    draw_glowing_shape(draw_square, square_color)


    # Triangle
    triangle_color = (255,255,255) if hover_shape == "triangle" else (210, 120, 255)

    def draw_triangle(target, color, thickness):
        x,y = shape_positions["triangle"]

        size = 78 if hover_shape == "triangle" else 70

        pts = np.array([
            [x,y-size],
            [x-(size-10),y+(size-10)],
            [x+(size-10),y+(size-10)]
        ], np.int32)

        cv2.polylines(
            target,
            [pts],
            True,
            color,
            thickness,
            cv2.LINE_AA
        )

    draw_glowing_shape(draw_triangle, triangle_color)


    # Rectangle
    rect_color = (255,255,255) if hover_shape == "rectangle" else (100, 255, 240)

    def draw_rectangle(target, color, thickness):
        x,y = shape_positions["rectangle"]

        w = 90 if hover_shape == "rectangle" else 80
        h = 58 if hover_shape == "rectangle" else 50

        cv2.rectangle(
            target,
            (x-w,y-h),
            (x+w,y+h),
            color,
            thickness,
            cv2.LINE_AA
        )

    draw_glowing_shape(draw_rectangle, rect_color)


    # Pentagon
    pen_color = (255,255,255) if hover_shape == "pentagon" else (140, 255, 160)

    def draw_pentagon(target, color, thickness):
        x,y = shape_positions["pentagon"]

        size = 78 if hover_shape == "pentagon" else 70
        pts = np.array([
            [x, y-size],
            [x-(size-5), y-20],
            [x-40, y+60],
            [x+40, y+60],
            [x+(size-5), y-20]
        ], np.int32)

        cv2.polylines(
            target,
            [pts],
            True,
            color,
            thickness,
            cv2.LINE_AA
        )

    draw_glowing_shape(draw_pentagon, pen_color)

    # Star
    star_color = (255,255,255) if hover_shape == "star" else (255, 240, 120)

    def draw_star(target, color, thickness):
        x,y = shape_positions["star"]
        size = 78 if hover_shape == "star" else 70
        pts = np.array([
            [x, y-size],
            [x-20, y-20],
            [x-size, y-20],
            [x-30, y+10],
            [x-45, y+65],
            [x, y+30],
            [x+45, y+65],
            [x+30, y+10],
            [x+size, y-20],
            [x+20, y-20]
        ], np.int32)

        cv2.polylines(
            target,
            [pts],
            True,
            color,
            thickness,
            cv2.LINE_AA
        )

    draw_glowing_shape(draw_star, star_color)

    # ==============================
    # LESSON RUNNING
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()
        if q is None:
            continue

        current, total = lesson.get_progress()
        
        frame = overlay_png(
            frame,
            progress_pill,
            1120,
            40
        )

        frame = draw_centered_text(
            frame,
            f"{current}/{total}",
            1120,
            40,
            115,
            70,
            24
        )

        # ==============================
        # QUESTION BAR PNG
        # ==============================
        frame = overlay_png(
            frame,
            question_bar,
            25,
            20
        )

        frame = draw_text(
            frame,
            q["question"],
            (130, 50),
            32,
            (255,255,255),
            "Montserrat-SemiBold.ttf"
        )

        if hand_count > 0 and len(index_positions) > 0:

            ix,iy = index_positions[0]

            # show cursor
            cv2.circle(frame,(ix,iy),6,(255,255,255),-1,cv2.LINE_AA)
            cv2.circle(frame,(ix,iy),14,(255,255,255),2,cv2.LINE_AA)
            
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

        frame = overlay_png(
            frame,
            level_pill,
            1060,
            90
        )

        frame = draw_centered_text(
            frame,
            level,
            1060,
            90,
            175,
            70,
            26
        )
        
        # ==============================
        # FEEDBACK
        # ==============================
        if lesson.feedback == "correct":

            frame = overlay_png(
                frame,
                correct_popup,
                30,
                100
            )

            frame = draw_text(
                frame,
                "Correct!",
                (105, 120),
                24,
                (255,255,255),
                "Montserrat-SemiBold.ttf"
            )

        elif lesson.feedback == "wrong":

            frame = overlay_png(
                frame,
                wrong_popup,
                30,
                100
            )

            frame = draw_text(
                frame,
                "Try Again",
                (105, 120),
                24,
                (255,255,255),
                "Montserrat-SemiBold.ttf"
            )

    # ==============================
    # LESSON FINISHED
    # ==============================
    else:

        # Finish Card
        frame = draw_panel(
            frame,
            390, 250,
            890, 450,
            color=(25,25,35),
            alpha=0.6,
            border=(0,255,255)
        )

        frame = draw_text(
            frame,
            "Lesson Complete",
            (0, 290),
            40,
            (255,255,255),
            "Montserrat-Bold.ttf",
            center=True
        )

        frame = draw_text(
            frame,
            f"Score : {lesson.score}",
            (0, 360),
            30,
            (220,220,220),
            "Montserrat-SemiBold.ttf",
            center=True
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