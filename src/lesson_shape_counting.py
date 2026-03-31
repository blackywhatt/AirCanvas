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

# Screen
CENTER_X = 640

# Question
QUESTION_POS = (CENTER_X, 60)

# Feedback
FEEDBACK_POS = (CENTER_X, 110)

# Answer row
ANSWER_Y = 190
ANSWER_SPACING = 180   # distance between numbers

# Shapes area
SHAPE_Y_MIN = 320
SHAPE_Y_MAX = 600
SHAPE_X_MIN = 200
SHAPE_X_MAX = 1000

# Shape size
SHAPE_SIZE = 40

# Number circle size
NUMBER_RADIUS = 45

# ==============================
# FONT SETUP
# ==============================
FONTS = os.path.join(os.path.dirname(__file__), "fonts")

font_title = ImageFont.truetype(os.path.join(FONTS, "Orbitron-Bold.ttf"), 48)
font_question = ImageFont.truetype(os.path.join(FONTS, "Montserrat-SemiBold.ttf"), 40)
font_medium = ImageFont.truetype(os.path.join(FONTS, "Montserrat-Regular.ttf"), 30)
font_small = ImageFont.truetype(os.path.join(FONTS, "Montserrat-Regular.ttf"), 26)


def draw_text(frame, text, position, font, color=(30,30,30), center=False):
    img_pil = Image.fromarray(frame)
    draw = ImageDraw.Draw(img_pil)

    color_rgb = (color[2], color[1], color[0])

    if center:
        draw.text(position, text, font=font, fill=color_rgb, anchor="mm")
    else:
        draw.text(position, text, font=font, fill=color_rgb)

    return np.array(img_pil)

# ==============================
# LESSON QUESTIONS
# ==============================

questions = [
    {"question": "How many TRIANGLES?", "shape": "triangle"},
    {"question": "How many SQUARES?", "shape": "square"},
    {"question": "How many CIRCLES?", "shape": "circle"}
]

lesson = LessonEngine(questions)

# ==============================
# NUMBER POSITIONS
# ==============================
numbers = [1,2,3,4,5]

start_x = CENTER_X - (len(numbers)//2) * ANSWER_SPACING

number_positions = {
    n: (start_x + i*ANSWER_SPACING, ANSWER_Y)
    for i, n in enumerate(numbers)
}

# ==============================
# GENERATE RANDOM SHAPES
# ==============================
def generate_shapes(target_shape):

    shapes = []
    positions = []

    num_shapes = random.randint(3,5)

    # ✅ Force at least one correct shape
    x = random.randint(SHAPE_X_MIN, SHAPE_X_MAX)
    y = random.randint(SHAPE_Y_MIN, SHAPE_Y_MAX)
    shapes.append((target_shape,(x,y)))
    positions.append((x,y))

    while len(shapes) < num_shapes:

        shape = random.choice(["circle","square","triangle"])

        x = random.randint(SHAPE_X_MIN, SHAPE_X_MAX)
        y = random.randint(SHAPE_Y_MIN, SHAPE_Y_MAX)

        valid = True
        for px,py in positions:
            if np.hypot(x-px,y-py) < 120:
                valid = False
                break

        if valid:
            shapes.append((shape,(x,y)))
            positions.append((x,y))

    return shapes

q = lesson.get_current_question()
shapes = generate_shapes(q["shape"])

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

# ==============================
# DETECT NUMBER SELECTION
# ==============================
def detect_number(ix,iy):

    for number,(nx,ny) in number_positions.items():

        dist = np.hypot(ix-nx,iy-ny)

        if dist < 80:
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

    # ==============================
    # DRAW SHAPES
    # ==============================
    for s in shapes:
        draw_shape(frame,s[0],s[1])

    # ==============================
    # DRAW NUMBERS
    # ==============================
    for n,(x,y) in number_positions.items():

        cv2.circle(frame,(x,y),NUMBER_RADIUS,(255,255,255),2)

        frame = draw_text(frame, str(n), (x, y), font_small, center=True)

    # ==============================
    # GET CURSOR
    # ==============================
    if hand_count > 0 and len(index_positions) > 0:

        ix,iy = index_positions[0]

        cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

        selected = detect_number(ix,iy)

        if not lesson.lesson_finished() and answer_cooldown == 0 and gesture == "draw" and selected:

            q = lesson.get_current_question()

            count = sum(1 for s in shapes if s[0] == q["shape"])

            q["answer"] = count

            lesson.check_answer(selected)

            if not lesson.lesson_finished():
                q = lesson.get_current_question()
                shapes = generate_shapes(q["shape"])

            answer_cooldown = 30


    # ==============================
    # LESSON TEXT
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()

        frame = draw_text(frame, q["question"], QUESTION_POS, font_question, center=True)

        if lesson.feedback == "correct":
            frame = draw_text(frame, "Correct!", FEEDBACK_POS, font_medium, (0,255,0), center=True)

        elif lesson.feedback == "wrong":
            frame = draw_text(frame, "Try Again", FEEDBACK_POS, font_medium, (255,0,0), center=True)

    else:

        frame = draw_text(frame, "Lesson Complete!", QUESTION_POS, font_title, (0,150,150), center=True)

        frame = draw_text(frame, f"Score: {lesson.score}", FEEDBACK_POS, font_medium, center=True)


    if answer_cooldown > 0:
        answer_cooldown -= 1


    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break


cap.release()
cv2.destroyAllWindows()