import cv2
import numpy as np
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont
from PIL import ImageDraw, Image

def draw_text(frame, text, position, font, color=(255,255,255), center=False):
    
    img_pil = Image.fromarray(frame)
    draw = ImageDraw.Draw(img_pil)

    color_rgb = (color[2], color[1], color[0])

    if center:
        bbox = draw.textbbox((0,0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        position = (position[0] - w//2, position[1] - h//2)

    draw.text(position, text, font=font, fill=color_rgb)

    return np.array(img_pil)

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
FONTS = os.path.join(os.path.dirname(__file__), "fonts")
font_title = ImageFont.truetype(os.path.join(FONTS, "Orbitron-Bold.ttf"), 48)
font_large = ImageFont.truetype(os.path.join(FONTS, "Montserrat-SemiBold.ttf"), 40)
font_medium = ImageFont.truetype(os.path.join(FONTS, "Montserrat-SemiBold.ttf"), 30)
font_small = ImageFont.truetype(os.path.join(FONTS, "Montserrat-SemiBold.ttf"), 24)
ICON_SIZE = 140

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

def load_icon(name):

    path = os.path.join(ASSETS,name)
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)

    if img is None:
        raise Exception(f"Image not found: {path}")

    img = cv2.resize(img,(ICON_SIZE,ICON_SIZE))

    # If image only has RGB
    if img.shape[2] == 3:

        b,g,r = cv2.split(img)
        alpha = np.ones_like(b)*255

        mask = (b > 240) & (g > 240) & (r > 240)
        alpha[mask] = 0

        img = cv2.merge([b,g,r,alpha])

    # If image already has RGBA but background still white
    else:

        b,g,r,a = cv2.split(img)

        mask = (b > 240) & (g > 240) & (r > 240)
        a[mask] = 0

        img = cv2.merge([b,g,r,a])

    return img

ball_img = load_icon("ball.png")
clock_img = load_icon("clock.png")
window_img = load_icon("window.png")
giftbox_img = load_icon("giftbox.png")
dice_img = load_icon("dice.png")
pizza_img = load_icon("pizza.png")
sandwich_img = load_icon("sandwich.png")
phone_img = load_icon("phone.png")
door_img = load_icon("door.png")
starfish_img = load_icon("starfish.png")

def draw_png(frame, png, x, y):

    h, w = png.shape[:2]

    x1 = int(x - w/2)
    y1 = int(y - h/2)
    x2 = x1 + w
    y2 = y1 + h

    if x1 < 0 or y1 < 0 or x2 > frame.shape[1] or y2 > frame.shape[0]:
        return

    alpha = png[:,:,3] / 255.0
    rgb = png[:,:,:3]

    for c in range(3):
        frame[y1:y2,x1:x2,c] = (
            alpha * rgb[:,:,c] +
            (1-alpha) * frame[y1:y2,x1:x2,c]
        )

# ==============================
# LESSON QUESTIONS
# ==============================
questions = [

    # EASY
    {"question":"Match BALL to its shape","answer":"circle","object":"ball"},
    {"question":"Match WINDOW to its shape","answer":"square","object":"window"},
    {"question":"Match PIZZA to its shape","answer":"triangle","object":"pizza"},

    # MEDIUM
    {"question":"Match CLOCK to its shape","answer":"circle","object":"clock"},
    {"question":"Match GIFTBOX to its shape","answer":"square","object":"giftbox"},
    {"question":"Match SANDWICH to its shape","answer":"triangle","object":"sandwich"},

    # HARD
    {"question":"Match PHONE to its shape","answer":"rectangle","object":"phone"},
    {"question":"Match DOOR to its shape","answer":"rectangle","object":"door"},
    {"question":"Match STARFISH to its shape","answer":"star","object":"starfish"},
    {"question":"Match DICE to its shape","answer":"square","object":"dice"}

]

lesson = LessonEngine(questions)

# ==============================
# LOAD UI ASSETS
# ==============================
question_bar = cv2.imread(
    "assets/ui/question_bar.png",
    cv2.IMREAD_UNCHANGED
)
question_bar = cv2.resize(question_bar,(900,110))

progress_pill = cv2.imread(
    "assets/ui/progress_pill.png",
    cv2.IMREAD_UNCHANGED
)
progress_pill = cv2.resize(progress_pill,(115,70))

level_pill = cv2.imread(
    "assets/ui/level_pill.png",
    cv2.IMREAD_UNCHANGED
)
level_pill = cv2.resize(level_pill,(175,70))

correct_popup = cv2.imread(
    "assets/ui/correct_popup.png",
    cv2.IMREAD_UNCHANGED
)
correct_popup = cv2.resize(correct_popup,(230,80))

wrong_popup = cv2.imread(
    "assets/ui/wrong_popup.png",
    cv2.IMREAD_UNCHANGED
)
wrong_popup = cv2.resize(wrong_popup,(230,80))

# ==============================
# SHAPE POSITIONS
# ==============================
shape_positions = {

    # LEFT
    "circle":(190,410),

    # TOP LEFT
    "square":(410,250),

    # TOP CENTER
    "triangle":(640,200),

    # TOP RIGHT
    "rectangle":(870,250),

    # RIGHT
    "star":(1090,410)

}

# ==============================
# OBJECT START POSITION
# ==============================
object_pos = np.array([640,450])
dragging = False
drag_offset = np.array([0,0])
drop_cooldown = 0
# ==============================
# CAMERA SETUP
# ==============================
cap = cv2.VideoCapture(0,cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Shape Matching Lesson"

cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)


# ==============================
# HELPER: DETECT DROP TARGET
# ==============================
def detect_shape_target(x,y):

    for shape,(sx,sy) in shape_positions.items():

        dist = np.hypot(x-sx,y-sy)

        if dist < 100:
            return shape

    return None


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
    # GET CURSOR
    # ==============================
    if hand_count >= 1 and len(index_positions) >= 1:
        ix,iy = index_positions[0]
    else:
        ix,iy = None,None

    # ==============================
    # DRAW SHAPES
    # ==============================

    # CIRCLE
    cv2.circle(frame,shape_positions["circle"],45,(255,255,255),3)

    # SQUARE
    x,y = shape_positions["square"]
    cv2.rectangle(frame,(x-45,y-45),(x+45,y+45),(255,255,255),3)

    # TRIANGLE
    x,y = shape_positions["triangle"]
    pts = np.array([[x,y-55],[x-45,y+45],[x+45,y+45]],np.int32)
    cv2.polylines(frame,[pts],True,(255,255,255),3)

    # RECTANGLE
    x,y = shape_positions["rectangle"]
    cv2.rectangle(frame,(x-70,y-40),(x+70,y+40),(255,255,255),3)

    # STAR
    x,y = shape_positions["star"]

    star_pts = np.array([
        [x,y-50],
        [x-15,y-15],
        [x-50,y-15],
        [x-22,y+8],
        [x-35,y+45],
        [x,y+22],
        [x+35,y+45],
        [x+22,y+8],
        [x+50,y-15],
        [x+15,y-15]
    ], np.int32)

    cv2.polylines(frame,[star_pts],True,(255,255,255),3)

    # LABELS
    frame = draw_text(frame,"Circle",(190,480),font_small,center=True)

    frame = draw_text(frame,"Square",(410,330),font_small,center=True)

    frame = draw_text(frame,"Triangle",(640,290),font_small,center=True)

    frame = draw_text(frame,"Rectangle",(870,330),font_small,center=True)

    frame = draw_text(frame,"Star",(1090,480),font_small,center=True)
    
    # ==============================
    # DRAW OBJECT (PNG)
    # ==============================

    if not lesson.lesson_finished():
        q = lesson.get_current_question()
        if q is not None:
            obj = q["object"]
        else:
            obj = None
    else:
        obj = None

    x,y = object_pos.astype(int)

    if obj == "ball":
        draw_png(frame,ball_img,x,y)

    elif obj == "clock":
        draw_png(frame,clock_img,x,y)

    elif obj == "window":
        draw_png(frame,window_img,x,y)

    elif obj == "giftbox":
        draw_png(frame,giftbox_img,x,y)

    elif obj == "dice":
        draw_png(frame,dice_img,x,y)

    elif obj == "pizza":
        draw_png(frame,pizza_img,x,y)

    elif obj == "sandwich":
        draw_png(frame,sandwich_img,x,y)

    elif obj == "phone":
        draw_png(frame,phone_img,x,y)

    elif obj == "door":
        draw_png(frame,door_img,x,y)

    elif obj == "starfish":
        draw_png(frame,starfish_img,x,y)


    # ==============================
    # DRAG LOGIC (MOVE GESTURE)
    # ==============================

    if not lesson.lesson_finished() and hand_count >= 1 and ix is not None:

        cv2.circle(frame,(ix,iy),10,(255,255,0),-1)

        dist = np.hypot(ix-object_pos[0],iy-object_pos[1])

        # start dragging
        if gesture == "move" and dist < 140 and not dragging:
            dragging = True
            drag_offset = object_pos - np.array([ix,iy])

        # stop dragging
        elif gesture != "move":
            if dragging:

                target = detect_shape_target(object_pos[0],object_pos[1])

                if target and drop_cooldown == 0:
                    object_pos[:] = shape_positions[target]
                    lesson.check_answer(target)
                    object_pos[:] = [640,450]

                    drop_cooldown = 20

            dragging = False

        # move object
        if dragging:
            object_pos[:] = np.array([ix,iy]) + drag_offset

    # ==============================
    # LESSON TEXT
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()
        current, total = lesson.get_progress()

        # LEVEL
        if current <= 3:
            level = "EASY"
        elif current <= 6:
            level = "MEDIUM"
        else:
            level = "HARD"

        # QUESTION BAR
        frame = overlay_png(
            frame,
            question_bar,
            25,
            20
        )

        frame = draw_text(
            frame,
            q["question"],
            (120,50),
            font_medium,
            (255,255,255)
        )

        # PROGRESS
        frame = overlay_png(
            frame,
            progress_pill,
            1120,
            40
        )

        frame = draw_text(
            frame,
            f"{current}/{total}",
            (1177,70),
            font_small,
            (255,255,255),
            center=True
        )

        # LEVEL
        frame = overlay_png(
            frame,
            level_pill,
            1060,
            90
        )

        frame = draw_text(
            frame,
            level,
            (1150,115),
            font_small,
            (255,255,255),
            center=True
        )

        # FEEDBACK
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
                (155, 130),
                font_small,
                (255,255,255),
                center=True
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
                (155, 130),
                font_small,
                (255,255,255),
                center=True
            )

    else:

        frame = draw_text(
            frame,
            "Lesson Complete!",
            (640,260),
            font_title,
            (255,255,255),
            center=True
        )

        frame = draw_text(
            frame,
            f"Score : {lesson.score}",
            (640,330),
            font_medium,
            (220,220,220),
            center=True
        )   

    if drop_cooldown > 0:
        drop_cooldown -= 1

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