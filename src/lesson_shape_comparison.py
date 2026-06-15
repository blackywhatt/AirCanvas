import cv2
import numpy as np
import random
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont, ImageDraw, Image
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")
# ==============================
# QUESTIONS
# ==============================
questions = [

    # EASY
    {"question":"Which has MORE SIDES?", "type":"more"},
    {"question":"Which has LESS SIDES?", "type":"less"},
    {"question":"Which has MORE SIDES?", "type":"more"},
    {"question":"Which has LESS SIDES?", "type":"less"},

    # MEDIUM
    {"question":"Which has MORE CORNERS?", "type":"corners"},
    {"question":"Which is ROUND?", "type":"round"},
    {"question":"Which has 4 SIDES?", "type":"four"},

    # HARD
    {"question":"Which has 5 SIDES?", "type":"five"},
    {"question":"Which is a STAR?", "type":"points"},
    {"question":"Which has the MOST EDGES?", "type":"more"}
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
# SHAPE DATA
# ==============================
shape_sides = {
    "triangle":3,
    "square":4,
    "rectangle":4,
    "pentagon":5,
    "star":10,
    "circle":0
}

shape_positions = {
    "left":(400,360),
    "right":(880,360)
}

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
# GENERATE QUESTION
# ==============================
def generate_pair(qtype):

    all_shapes = [
        "triangle",
        "square",
        "rectangle",
        "pentagon",
        "star",
        "circle"
    ]

    # EASY / comparison questions
    if qtype in ["more", "less", "corners"]:
        s1 = random.choice(all_shapes)
        s2 = random.choice(all_shapes)

        while s1 == s2 or shape_sides[s1] == shape_sides[s2]:
            s2 = random.choice(all_shapes)

        return s1, s2

    # ROUND question
    elif qtype == "round":
        correct_side = random.choice(["left","right"])
        wrong = random.choice(["triangle","square","rectangle","pentagon","star"])

        if correct_side == "left":
            return "circle", wrong
        else:
            return wrong, "circle"

    # FOUR SIDES
    elif qtype == "four":
        correct = random.choice(["square","rectangle"])
        wrong = random.choice(["triangle","circle","pentagon","star"])

        if random.choice([True,False]):
            return correct, wrong
        else:
            return wrong, correct

    # FIVE SIDES
    elif qtype == "five":
        wrong = random.choice(["triangle","square","rectangle","circle","star"])

        if random.choice([True,False]):
            return "pentagon", wrong
        else:
            return wrong, "pentagon"

    # STAR question
    elif qtype == "points":
        wrong = random.choice(["circle","square","rectangle"])

        if random.choice([True,False]):
            return "star", wrong
        else:
            return wrong, "star"

    return "triangle", "square"

q = lesson.get_current_question()
left_shape, right_shape = generate_pair(q["type"])

# ==============================
# DRAW SHAPE
# ==============================
def draw_shape(frame,shape,pos,hovered=False):

    x,y = pos

    color = (0,255,255) if hovered else (255,255,255)

    thickness = 4 if hovered else 3

    scale = 1.12 if hovered else 1.0

    if shape == "circle":

        radius = int(80 * scale)

        cv2.circle(
            frame,
            (x,y),
            radius,
            color,
            thickness,
            cv2.LINE_AA
        )

    elif shape == "square":

        size = int(70 * scale)

        cv2.rectangle(
            frame,
            (x-size,y-size),
            (x+size,y+size),
            color,
            thickness,
            cv2.LINE_AA
        )

    elif shape == "triangle":

        size = int(80 * scale)

        pts = np.array([
            [x,y-size],
            [x-size+10,y+size-10],
            [x+size-10,y+size-10]
        ],np.int32)

        cv2.polylines(frame,[pts],True,color,thickness,cv2.LINE_AA)

    elif shape == "rectangle":

        w = int(90 * scale)
        h = int(60 * scale)

        cv2.rectangle(
            frame,
            (x-w,y-h),
            (x+w,y+h),
            color,
            thickness,
            cv2.LINE_AA
        )

    elif shape == "pentagon":

        size = int(80 * scale)

        pts = np.array([
            [x,y-size],
            [x-size+10,y-20],
            [x-45,y+70],
            [x+45,y+70],
            [x+size-10,y-20]
        ], np.int32)

        cv2.polylines(frame,[pts],True,color,thickness,cv2.LINE_AA)

    elif shape == "star":

        size = int(80 * scale)

        pts = np.array([
            [x,y-size],
            [x-25,y-20],
            [x-size,y-20],
            [x-35,y+10],
            [x-50,y+75],
            [x,y+35],
            [x+50,y+75],
            [x+35,y+10],
            [x+size,y-20],
            [x+25,y-20]
        ], np.int32)

        cv2.polylines(frame,[pts],True,color,thickness,cv2.LINE_AA)

# ==============================
# DETECT SELECTION
# ==============================
def detect_choice(ix,iy):

    for side,(x,y) in shape_positions.items():

        if np.hypot(ix-x,iy-y) < 120:
            return side

    return None

# ==============================
# CAMERA
# ==============================
cap = cv2.VideoCapture(0,cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Shape Comparison Lesson"

cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

answer_cooldown = 0
hover_side = None
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
    draw_shape(
        frame,
        left_shape,
        shape_positions["left"],
        hover_side == "left"
    )

    draw_shape(
        frame,
        right_shape,
        shape_positions["right"],
        hover_side == "right"
    )

    # ==============================
    # GET CURSOR
    # ==============================
    if hand_count > 0 and len(index_positions) > 0:

        ix,iy = index_positions[0]

        cv2.circle(frame,(ix,iy),6,(255,255,255),-1,cv2.LINE_AA)
        cv2.circle(frame,(ix,iy),14,(255,255,255),2,cv2.LINE_AA)

        selected = detect_choice(ix,iy)

        if selected:

            if hover_side == selected:
                hover_frames += 1
            else:
                hover_side = selected
                hover_frames = 0

            if hover_frames > HOVER_THRESHOLD and answer_cooldown == 0:

                q = lesson.get_current_question()
                if q is None:
                    continue

                left_sides = shape_sides[left_shape]
                right_sides = shape_sides[right_shape]

                if q["type"] == "more":
                    correct = "left" if left_sides > right_sides else "right"

                elif q["type"] == "less":
                    correct = "left" if left_sides < right_sides else "right"

                elif q["type"] == "corners":
                    correct = "left" if left_sides > right_sides else "right"

                elif q["type"] == "round":
                    correct = "left" if left_shape == "circle" else "right"

                elif q["type"] == "four":
                    correct = "left" if left_shape in ["square","rectangle"] else "right"

                elif q["type"] == "five":
                    correct = "left" if left_shape == "pentagon" else "right"

                elif q["type"] == "points":
                    correct = "left" if left_shape == "star" else "right"

                q["answer"] = correct

                lesson.check_answer(selected)

                if not lesson.lesson_finished():
                    q = lesson.get_current_question()
                    left_shape, right_shape = generate_pair(q["type"])

                answer_cooldown = 30

                hover_frames = 0
                hover_side = None

        else:
            hover_side = None
            hover_frames = 0

    else:
        hover_side = None
        hover_frames = 0

    # ==============================
    # TEXT
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()
        current, total = lesson.get_progress()

        # ==============================
        # PROGRESS
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
            "Montserrat-SemiBold.ttf",
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

    # ==============================
    # AUTO EXIT AFTER FINISH
    # ==============================
    if lesson.should_exit():
        break

    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break


cap.release()
cv2.destroyAllWindows()