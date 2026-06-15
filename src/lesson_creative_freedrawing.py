import cv2
import numpy as np
from gesture_engine import get_gesture
import os
from PIL import ImageFont, ImageDraw, Image

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
# ==============================
# Canvas Setup
# ==============================
canvas = np.zeros((720,1280,3), dtype=np.uint8)

draw_color = (0,255,255)
brush_thickness = 5

prev_x, prev_y = 0, 0

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
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Free Drawing Lesson"
cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

# ==============================
# Main Loop
# ==============================
while cap.isOpened():

    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame,1)
    frame = cv2.resize(frame,(1280,720))

    gesture,index_positions,thumb_positions,hand_count,frame = get_gesture(frame)

    # Instruction
    frame = draw_text(
        frame,
        "Free Drawing Mode",
        (0, 30),
        36,
        (255,255,255),
        "Orbitron-Bold.ttf",
        center=True
    )

    # ==============================
    # Drawing Logic
    # ==============================
    if hand_count > 0 and len(index_positions) > 0:

        x, y = index_positions[0]

        cv2.circle(frame,(x,y),8,(0,255,255),-1)

        # DRAW
        if gesture == "draw":   # adjust based on your gesture system

            if prev_x == 0 and prev_y == 0:
                prev_x, prev_y = x, y

            cv2.line(canvas, (prev_x, prev_y), (x, y), draw_color, brush_thickness)

            prev_x, prev_y = x, y

        else:
            prev_x, prev_y = 0, 0

        # CLEAR
        if gesture == "clear":
            canvas[:] = 0

        # CHANGE COLOR
        if gesture == "pinch":
            draw_color = tuple(np.random.randint(0,255,3).tolist())

    # ==============================
    # Combine canvas + frame
    # ==============================
    gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY_INV)
    mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

    frame = cv2.bitwise_and(frame, mask)
    frame = cv2.bitwise_or(frame, canvas)

    cv2.imshow(window_name,frame)

    if cv2.waitKey(1) & 0xFF == ord('b'):
        break

cap.release()
cv2.destroyAllWindows()