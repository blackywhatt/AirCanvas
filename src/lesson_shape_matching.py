import cv2
import numpy as np
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

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

    cv2.putText(frame,"Circle",(280,610),
            cv2.FONT_HERSHEY_DUPLEX,0.7,(255,255,255),1)

    cv2.putText(frame,"Square",(600,610),
                cv2.FONT_HERSHEY_DUPLEX,0.7,(255,255,255),1)

    cv2.putText(frame,"Triangle",(900,610),
                cv2.FONT_HERSHEY_DUPLEX,0.7,(255,255,255),1)
    # ==============================
    # DRAW OBJECT (PNG)
    # ==============================

    if not lesson.lesson_finished():
        q = lesson.get_current_question()
        obj = q["object"]
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

    if hand_count >= 1 and ix is not None:

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

                if target:
                    object_pos[:] = shape_positions[target]
                    lesson.check_answer(target)
                    object_pos[:] = [640,200]

            dragging = False

        # move object
        if dragging:
            object_pos[:] = np.array([ix,iy]) + drag_offset

    # ==============================
    # LESSON TEXT
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


    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break


cap.release()
cv2.destroyAllWindows()