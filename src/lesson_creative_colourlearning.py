import cv2
import numpy as np
import random
from gesture_engine import get_gesture
from lesson_engine import LessonEngine
import os
from PIL import ImageFont, ImageDraw, Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")
hover_color = None
hover_frames = 0
HOVER_THRESHOLD = 25

# ==============================
# Colors
# ==============================
colors = {
    "red": (0,0,255),
    "green": (0,255,0),
    "blue": (255,0,0),
    "yellow": (0,255,255)
}

shapes = [
    "circle",
    "square",
    "triangle"
]

# ==============================
# Questions
# ==============================
questions = []

for _ in range(5):

    color_name = random.choice(list(colors.keys()))
    shape_name = random.choice(shapes)

    questions.append({
        "question": f"Choose the color {color_name.upper()} and paint the {shape_name.upper()}",
        "answer": color_name,
        "shape": shape_name
    })

lesson = LessonEngine(questions)

# ==============================
# Color Button Positions
# ==============================
color_positions = {
    "red": (340,490),
    "green": (540,490),
    "blue": (740,490),
    "yellow": (940,490)
}

selected_fill = None
answer_cooldown = 0
game_phase = "choose_color"  
selected_color = None        
painted_color = None
paint_points = []
final_paint_points = []
round_delay = 0
pending_answer = None
current_shape = None    

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
# Camera Setup
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Color Learning Lesson"
cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

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
# Detect selection
# ==============================
def detect_selected(ix, iy):

    for name, (x, y) in color_positions.items():
        dist = np.hypot(ix - x, iy - y)

        if dist < 60:
            return name

    return None

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
# Main Loop
# ==============================
while cap.isOpened():

    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame,1)
    frame = cv2.resize(frame,(1280,720))

    gesture,index_positions,thumb_positions,hand_count,frame = get_gesture(frame)

    lesson.update()
    # ==============================
    # Draw Question
    # ==============================
    if not lesson.lesson_finished():

        q = lesson.get_current_question()
        current_shape = q["shape"]
        
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
            30,
            (255,255,255),
            "Montserrat-SemiBold.ttf"
        )

        if selected_color:
            frame = draw_text(
                frame,
                f"Selected: {selected_color.upper()}",
                (80, 650),
                26,
                (255,255,255),
                "Montserrat-SemiBold.ttf"
            )
        else:
            frame = draw_text(
                frame,
                "Step 1: Choose a color",
                (80, 650),
                26,
                (200,200,200),
                "Montserrat-SemiBold.ttf"
            )

        shape_x = 640
        shape_y = 300

        border_color = (255,255,255)

        if game_phase == "paint_shape":
            border_color = (0,255,255)

        overlay = frame.copy()

        # ==============================
        # CIRCLE
        # ==============================
        if current_shape == "circle":

            if painted_color:
                cv2.circle(
                    overlay,
                    (shape_x, shape_y),
                    95,
                    colors[painted_color],
                    -1,
                    cv2.LINE_AA
                )

            cv2.circle(
                frame,
                (shape_x, shape_y),
                100,
                border_color,
                3,
                cv2.LINE_AA
            )

        # ==============================
        # SQUARE
        # ==============================
        elif current_shape == "square":

            if painted_color:
                cv2.rectangle(
                    overlay,
                    (shape_x-90, shape_y-90),
                    (shape_x+90, shape_y+90),
                    colors[painted_color],
                    -1,
                    cv2.LINE_AA
                )

            cv2.rectangle(
                frame,
                (shape_x-95, shape_y-95),
                (shape_x+95, shape_y+95),
                border_color,
                3,
                cv2.LINE_AA
            )

        # ==============================
        # TRIANGLE
        # ==============================
        elif current_shape == "triangle":

            pts = np.array([
                [shape_x, shape_y-100],
                [shape_x-100, shape_y+80],
                [shape_x+100, shape_y+80]
            ], np.int32)

            if painted_color:
                cv2.fillPoly(
                    overlay,
                    [pts],
                    colors[painted_color],
                    cv2.LINE_AA
                )

            cv2.polylines(
                frame,
                [pts],
                True,
                border_color,
                3,
                cv2.LINE_AA
            )

        # ==============================
        # REAL PAINT STROKES
        # ==============================
        # smooth connected paint strokes
        active_points = final_paint_points if round_delay > 0 else paint_points

        for i in range(1, len(active_points)):  

            x1, y1, color1 = active_points[i - 1]
            x2, y2, color2 = active_points[i]

            cv2.line(
                overlay,
                (x1, y1),
                (x2, y2),
                colors[color2],
                14,
                cv2.LINE_AA
            )

        frame = cv2.addWeighted(
            overlay,
            0.75,
            frame,
            0.25,
            0
        )

        # Draw color buttons
        for name,(x,y) in color_positions.items():

            color = colors[name]

            # hover grow effect
            radius = 52 if hover_color == name else 40

            # selected color stays slightly bigger
            if selected_color == name:
                radius = 48

            cv2.circle(
                frame,
                (x,y),
                radius,
                color,
                -1,
                cv2.LINE_AA
            )

            label = name.upper()

            # properly center text using actual width
            font_path = os.path.join(FONT_DIR, "Montserrat-SemiBold.ttf")
            font = ImageFont.truetype(font_path, 22)

            dummy_img = Image.new("RGB", (1,1))
            draw = ImageDraw.Draw(dummy_img)

            bbox = draw.textbbox((0,0), label, font=font)
            text_width = bbox[2] - bbox[0]

            label_x = x - (text_width // 2)

            frame = draw_text(
                frame,
                label,
                (label_x, y + 55),
                22,
                (255,255,255),
                "Montserrat-SemiBold.ttf"
            )

        # ==============================
        # Interaction
        # ==============================
        if not lesson.lesson_finished() and hand_count > 0 and len(index_positions) > 0:

            ix, iy = index_positions[0]

            cv2.circle(frame,(ix,iy),10,(0,255,255),-1)

            selected = detect_selected(ix, iy)

            if not lesson.lesson_finished() and hand_count > 0 and len(index_positions) > 0:
                ix, iy = index_positions[0]

                cv2.circle(frame, (ix, iy), 10, (0,255,255), -1)

                selected = detect_selected(ix, iy)

                # STEP 1: choose a color
                if game_phase == "choose_color":
                    if selected:
                        if hover_color == selected:
                            hover_frames += 1
                        else:
                            hover_color = selected
                            hover_frames = 0

                        if hover_frames > HOVER_THRESHOLD and answer_cooldown == 0:
                            selected_color = selected
                            game_phase = "paint_shape"
                            hover_frames = 0
                            hover_color = None
                            answer_cooldown = 15

                # STEP 2: paint the shape
                elif game_phase == "paint_shape":
                    shape_center_x, shape_center_y = shape_x, shape_y
                    dist_to_shape = np.hypot(ix - shape_center_x, iy - shape_center_y)

                    # ==============================
                    # REAL COLORING
                    # ==============================
                    inside_shape = False

                    # circle
                    if current_shape == "circle":

                        inside_shape = (
                            np.hypot(ix - shape_x, iy - shape_y) < 95
                        )

                    # square
                    elif current_shape == "square":

                        inside_shape = (
                            shape_x-90 < ix < shape_x+90 and
                            shape_y-90 < iy < shape_y+90
                        )

                    # triangle
                    elif current_shape == "triangle":

                        pts = np.array([
                            [shape_x, shape_y-100],
                            [shape_x-100, shape_y+80],
                            [shape_x+100, shape_y+80]
                        ], np.int32)

                        inside_shape = (
                            cv2.pointPolygonTest(
                                pts,
                                (ix, iy),
                                False
                            ) >= 0
                        )

                    if inside_shape and selected_color and round_delay == 0:
                        
                        # add paint points
                        paint_points.append(
                            (ix, iy, selected_color)
                        )

                        # keep limit
                        if len(paint_points) > 3000:
                            paint_points.pop(0)

                        # check answer after enough painting
                        if len(paint_points) > 180 and round_delay == 0:

                            # freeze final painted result
                            final_paint_points = paint_points.copy()

                            # save answer temporarily
                            pending_answer = selected_color

                            # start 1 second delay
                            round_delay = 30

        # ==============================
        # Feedback
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
    # ROUND TRANSITION DELAY
    # ==============================
    if round_delay > 0:

        round_delay -= 1

        # after 1 second
        if round_delay == 0:

            # NOW advance to next question
            if pending_answer:
                lesson.check_answer(pending_answer)
                pending_answer = None

            # reset
            pending_answer = None
            game_phase = "choose_color"
            selected_color = None

            hover_frames = 0
            hover_color = None

            # clear drawing for next round
            paint_points.clear()
            final_paint_points.clear()

            answer_cooldown = 15

    if lesson.lesson_finished() and lesson.finish_timer == 1:
        selected_color = None
        painted_color = None
        hover_color = None
        hover_frames = 0
        game_phase = "choose_color"

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