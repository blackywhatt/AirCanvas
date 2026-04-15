import cv2
import numpy as np
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont
from PIL import ImageDraw, Image

def draw_text(frame, text, position, font, color=(0,0,0), center=False):
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
font_medium = ImageFont.truetype(os.path.join(FONTS, "Montserrat-Regular.ttf"), 30)
font_small = ImageFont.truetype(os.path.join(FONTS, "Montserrat-Regular.ttf"), 24)
ICON_SIZE = 90

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
pizza_img = load_icon("pizza.png")
window_img = load_icon("window.png")

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
    {"question":"Match BALL to its shape","answer":"circle","object":"ball"},
    {"question":"Match WINDOW to its shape","answer":"square","object":"window"},
    {"question":"Match PIZZA to its shape","answer":"triangle","object":"pizza"}
]

lesson = LessonEngine(questions)


# ==============================
# SHAPE POSITIONS
# ==============================
shape_positions = {
    "circle":(320,500),
    "square":(640,500),
    "triangle":(960,500)
}


# ==============================
# OBJECT START POSITION
# ==============================
object_pos = np.array([640,200])
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

        if dist < 120:
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
    cv2.circle(frame,shape_positions["circle"],60,(255,255,255),3)

    x,y = shape_positions["square"]
    cv2.rectangle(frame,(x-60,y-60),(x+60,y+60),(255,255,255),3)

    x,y = shape_positions["triangle"]
    pts = np.array([[x,y-70],[x-60,y+60],[x+60,y+60]],np.int32)
    cv2.polylines(frame,[pts],True,(255,255,255),3)

    frame = draw_text(frame, "Circle", (320, 610), font_small, center=True)
    frame = draw_text(frame, "Square", (640, 610), font_small, center=True)
    frame = draw_text(frame, "Triangle", (960, 610), font_small, center=True)
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

    elif obj == "window":
        draw_png(frame,window_img,x,y)

    elif obj == "pizza":
        draw_png(frame,pizza_img,x,y)


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
                    object_pos[:] = [640,200]

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
        frame = draw_text(frame, f"{current}/{total}", (1100,40), font_small)
        frame = draw_text(frame, q["question"], (40,40), font_large)

        if lesson.feedback == "correct":
            frame = draw_text(frame, "Correct!", (640, 110), font_large, (0,255,0), center=True)

        elif lesson.feedback == "wrong":
            frame = draw_text(frame, "Try Again", (640, 110), font_large, (255,0,0), center=True)

    else:

        frame = draw_text(frame, "Lesson Complete!", (640, 60), font_title, (0,255,255), center=True)
        frame = draw_text(frame, f"Score: {lesson.score}", (640, 130), font_medium, center=True)   

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