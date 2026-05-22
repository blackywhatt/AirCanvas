import cv2
import numpy as np
import random
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont, ImageDraw, Image

# ==============================
# LAYOUT CONFIG (EDIT THIS ONLY)
# ==============================
CENTER_X = 640
QUESTION_POS = (CENTER_X, 60)
FEEDBACK_POS = (CENTER_X, 110)

ANSWER_Y = 220
ANSWER_SPACING = 180   

SHAPE_Y_MIN = 320
SHAPE_Y_MAX = 600
SHAPE_X_MIN = 200
SHAPE_X_MAX = 1000

SHAPE_SIZE = 40
NUMBER_RADIUS = 45

# ==============================
# FONT SETUP
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")

def draw_text(frame, text, pos, size=40, color=(255,255,255),
              font_name="Montserrat-Medium.ttf", center=False):

    font_path = os.path.join(FONT_DIR, font_name)

    try:
        font = ImageFont.truetype(font_path, size)
    except:
        return frame

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
# LESSON QUESTIONS
# ==============================

questions = [

    # EASY
    {"question": "How many TRIANGLES?", "shape": "triangle"},
    {"question": "How many CIRCLES?", "shape": "circle"},
    {"question": "How many SQUARES?", "shape": "square"},
    {"question": "How many RECTANGLES?", "shape": "rectangle"},

    # MEDIUM
    {"question": "How many PENTAGONS?", "shape": "pentagon"},
    {"question": "How many STARS?", "shape": "star"},
    {"question": "How many TRIANGLES?", "shape": "triangle"},

    # HARD
    {"question": "How many SHAPES have 4 sides?", "shape": "fourside"},
    {"question": "How many SHAPES have corners?", "shape": "corners"},
    {"question": "How many ROUND shapes?", "shape": "round"}
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
# PNG OVERLAY
# ==============================
def overlay_png(frame, png, x, y):

    h, w = png.shape[:2]

    if y + h > frame.shape[0] or x + w > frame.shape[1]:
        return frame

    b, g, r, a = cv2.split(png)

    overlay_color = cv2.merge((b, g, r))

    mask = a.astype(float) / 255.0
    inverse_mask = 1.0 - mask

    for c in range(3):
        frame[y:y+h, x:x+w, c] = (
            mask * overlay_color[:,:,c] +
            inverse_mask * frame[y:y+h, x:x+w, c]
        )

    return frame

# ==============================
# NUMBER POSITIONS
# ==============================
numbers = [1,2,3,4,5,6]

total_width = (len(numbers) - 1) * ANSWER_SPACING
start_x = CENTER_X - total_width // 2

number_positions = {
    n: (start_x + i * ANSWER_SPACING, ANSWER_Y)
    for i, n in enumerate(numbers)
}

# ==============================
# GENERATE RANDOM SHAPES
# ==============================
def generate_shapes(target_shape):

    shapes = []
    positions = []

    num_shapes = random.randint(2,6)

    # -------------------------
    # Decide correct count
    # -------------------------
    if target_shape in ["corners", "fourside"]:
        target_count = random.randint(1, num_shapes)

    elif target_shape == "round":
        target_count = random.randint(1, num_shapes)

    else:
        target_count = random.randint(1, num_shapes)

    # -------------------------
    # helper add shape
    # -------------------------
    def add_shape(shape_name):
        tries = 0
        while tries < 100:
            x = random.randint(SHAPE_X_MIN, SHAPE_X_MAX)
            y = random.randint(SHAPE_Y_MIN, SHAPE_Y_MAX)

            valid = True
            for px, py in positions:
                if np.hypot(x-px, y-py) < 120:
                    valid = False
                    break

            if valid:
                shapes.append((shape_name, (x,y)))
                positions.append((x,y))
                return

            tries += 1

    # -------------------------
    # Add correct shapes
    # -------------------------
    for _ in range(target_count):

        if target_shape == "corners":
            add_shape(random.choice([
                "triangle","square","rectangle","pentagon","star"
            ]))

        elif target_shape == "fourside":
            add_shape(random.choice(["square","rectangle"]))

        elif target_shape == "round":
            add_shape("circle")

        else:
            add_shape(target_shape)

    # -------------------------
    # Fill remaining wrong shapes
    # -------------------------
    while len(shapes) < num_shapes:

        wrong_pool = [
            "circle","square","triangle",
            "rectangle","pentagon","star"
        ]

        shape = random.choice(wrong_pool)

        add_shape(shape)

    return shapes

q = lesson.get_current_question()

if q is not None:
    shapes = generate_shapes(q["shape"])
else:
    shapes = []

# ==============================
# DRAW SHAPE FUNCTION
# ==============================
def draw_shape(frame,shape,pos):

    x,y = pos

    if shape == "circle":
        cv2.circle(frame,(x,y),SHAPE_SIZE,(255,255,255),3)

    elif shape == "square":
        cv2.rectangle(frame,(x-SHAPE_SIZE,y-SHAPE_SIZE),
                     (x+SHAPE_SIZE,y+SHAPE_SIZE),(255,255,255),3)

    elif shape == "triangle":
        pts = np.array([
            [x, y-SHAPE_SIZE-10],
            [x-SHAPE_SIZE, y+SHAPE_SIZE],
            [x+SHAPE_SIZE, y+SHAPE_SIZE]
        ], np.int32)
        cv2.polylines(frame,[pts],True,(255,255,255),3)

    elif shape == "rectangle":
        cv2.rectangle(frame,(x-55,y-35),(x+55,y+35),(255,255,255),3)

    elif shape == "pentagon":
        pts = np.array([
            [x, y-45],
            [x-40, y-10],
            [x-25, y+40],
            [x+25, y+40],
            [x+40, y-10]
        ], np.int32)
        cv2.polylines(frame,[pts],True,(255,255,255),3)

    elif shape == "star":
        pts = np.array([
            [x, y-45],
            [x-15, y-10],
            [x-45, y-10],
            [x-20, y+10],
            [x-30, y+40],
            [x, y+20],
            [x+30, y+40],
            [x+20, y+10],
            [x+45, y-10],
            [x+15, y-10]
        ], np.int32)
        cv2.polylines(frame,[pts],True,(255,255,255),3)

# ==============================
# DETECT NUMBER SELECTION
# ==============================
def detect_number(ix,iy):

    for number,(nx,ny) in number_positions.items():

        dist = np.hypot(ix-nx,iy-ny)

        if dist < 95:
            return number

    return None

# ==============================
# CAMERA
# ==============================
cap = cv2.VideoCapture(0,cv2.CAP_DSHOW)

cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Shape Counting Lesson"

cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

answer_cooldown = 0

hover_number = None
hover_frames = 0
HOVER_THRESHOLD = 25

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
    # DRAW SHAPES
    # ==============================
    for s in shapes:
        draw_shape(frame,s[0],s[1])

    # ==============================
    # DRAW NUMBERS
    # ==============================
    for n,(x,y) in number_positions.items():

        hovered = hover_number == n

        radius = 55 if hovered else NUMBER_RADIUS

        circle_color = (0,255,255) if hovered else (255,255,255)

        cv2.circle(
            frame,
            (x,y),
            radius,
            circle_color,
            3,
            cv2.LINE_AA
        )

        frame = draw_text(
            frame,
            str(n),
            (x - 8, y - 18),
            30,
            (255,255,255),
            "Montserrat-SemiBold.ttf"
        )

    # ==============================
    # GET CURSOR
    # ==============================
    if hand_count > 0 and len(index_positions) > 0:

        ix,iy = index_positions[0]

        # Cursor
        cv2.circle(frame,(ix,iy),6,(255,255,255),-1,cv2.LINE_AA)
        cv2.circle(frame,(ix,iy),14,(255,255,255),2,cv2.LINE_AA)

        selected = detect_number(ix,iy)

        if selected:

            if hover_number == selected:
                hover_frames += 1
            else:
                hover_number = selected
                hover_frames = 0

            if hover_frames > HOVER_THRESHOLD and answer_cooldown == 0:

                q = lesson.get_current_question()

                if q["shape"] == "fourside":
                    count = sum(1 for s in shapes if s[0] in ["square","rectangle"])

                elif q["shape"] == "corners":
                    count = sum(1 for s in shapes if s[0] != "circle")

                elif q["shape"] == "round":
                    count = sum(1 for s in shapes if s[0] == "circle")

                else:
                    count = sum(1 for s in shapes if s[0] == q["shape"])

                q["answer"] = count

                lesson.check_answer(selected)

                if not lesson.lesson_finished():
                    q = lesson.get_current_question()
                    shapes = generate_shapes(q["shape"])

                answer_cooldown = 30

                hover_frames = 0
                hover_number = None

        else:
            hover_number = None
            hover_frames = 0

    else:
        hover_number = None
        hover_frames = 0

    if not lesson.lesson_finished():

        q = lesson.get_current_question()
        current, total = lesson.get_progress()

        # ==============================
        # PROGRESS PILL
        # ==============================
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
        # LEVEL
        # ==============================
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
        # QUESTION BAR
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

    else:

        frame = draw_text(
            frame,
            "Lesson Complete!",
            (0, 260),
            42,
            (255,255,255),
            "Montserrat-Bold.ttf",
            center=True
        )

        frame = draw_text(
            frame,
            f"Score : {lesson.score}",
            (0, 330),
            30,
            (220,220,220),
            "Montserrat-SemiBold.ttf",
            center=True
        )

    if answer_cooldown > 0:
        answer_cooldown -= 1

    if lesson.should_exit():
        break

    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()