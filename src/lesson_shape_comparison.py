import cv2
import numpy as np
import random
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont, ImageDraw, Image
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
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
def draw_shape(frame,shape,pos):

    x,y = pos

    if shape == "circle":
        cv2.circle(frame,(x,y),80,(255,255,255),3)

    elif shape == "square":
        cv2.rectangle(frame,(x-70,y-70),(x+70,y+70),(255,255,255),3)

    elif shape == "triangle":
        pts = np.array([[x,y-80],[x-70,y+70],[x+70,y+70]],np.int32)
        cv2.polylines(frame,[pts],True,(255,255,255),3)

    elif shape == "rectangle":
        cv2.rectangle(frame,(x-90,y-60),(x+90,y+60),(255,255,255),3)

    elif shape == "pentagon":
        pts = np.array([
            [x,y-80],
            [x-70,y-20],
            [x-45,y+70],
            [x+45,y+70],
            [x+70,y-20]
        ], np.int32)
        cv2.polylines(frame,[pts],True,(255,255,255),3)

    elif shape == "star":
        pts = np.array([
            [x,y-80],
            [x-25,y-20],
            [x-80,y-20],
            [x-35,y+10],
            [x-50,y+75],
            [x,y+35],
            [x+50,y+75],
            [x+35,y+10],
            [x+80,y-20],
            [x+25,y-20]
        ], np.int32)
        cv2.polylines(frame,[pts],True,(255,255,255),3)

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

cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Shape Comparison Lesson"

cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

answer_cooldown = 0

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
    draw_shape(frame,left_shape,shape_positions["left"])
    draw_shape(frame,right_shape,shape_positions["right"])

    # ==============================
    # GET CURSOR
    # ==============================
    if hand_count > 0 and len(index_positions) > 0:

        ix,iy = index_positions[0]

        cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

        selected = detect_choice(ix,iy)

        if (not lesson.lesson_finished() and 
            answer_cooldown == 0 and 
            gesture == "draw" and 
            selected):

            q = lesson.get_current_question()
            if q is None:
                continue

            left_sides = shape_sides[left_shape]
            right_sides = shape_sides[right_shape]

            # ==============================
            # DETERMINE CORRECT
            # ==============================
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

            # inject answer
            q["answer"] = correct

            lesson.check_answer(selected)

            if not lesson.lesson_finished():
                q = lesson.get_current_question()
                left_shape, right_shape = generate_pair(q["type"])

            answer_cooldown = 30

    # ==============================
    # TEXT
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()
        current, total = lesson.get_progress()
        if current <=4:
            level = "EASY"
        elif current <=7:
            level = "MEDIUM"
        else:
            level = "HARD"

        frame = draw_text(frame, f"LEVEL: {level}", (980,70), 28, (0,255,255))
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