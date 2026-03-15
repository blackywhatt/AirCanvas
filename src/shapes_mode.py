import cv2
import numpy as np
import time
import json
import os
import sys
from datetime import datetime
from gesture_engine import get_gesture
from PyQt6.QtWidgets import QApplication, QInputDialog
from PIL import ImageFont, ImageDraw, Image

# QT APPLICATION INITIALIZATION
qt_app = QApplication.instance()
if not qt_app:
    qt_app = QApplication(sys.argv)

# GLOBAL STATE VARIABLES
rotate_start_angle = None
shape_start_angle = None

hand_missing_frames = 0

HAND_LOST_TOLERANCE = 3

active_gesture = "none"
gesture_memory = "none"
gesture_hold_frames = 0

GESTURE_STABILITY = 3

last_ix, last_iy = 640, 360

# ERASE / ANIMATION VARIABLES
erase_progress = 0
imploding_shapes = []

# INTERPOLATION SETTINGS
lerp_factor = 0.1

# SELECTION SETTINGS
SELECTION_RADIUS = 100

# DRAGGING VARIABLES
drag_offset = np.array([0, 0])
is_dragging = False

# GORILLA ARM FATIGUE SYSTEM
fatigue_start_time = None
fatigue_active = False
FATIGUE_LIMIT = 60
fatigue_warning = False
rest_start_time = None
REST_DURATION = 10

# ROTATION HELPERS
rotate_start_pos = None
shape_start_ax = 0
shape_start_ay = 0

# UI ANIMATION
pulse_frame = 0

# FONT PATH
FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")

# MODERN FONT TEXT DRAWING
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
        w, h = frame.shape[1], frame.shape[0]
        bbox = draw.textbbox((0,0), text, font=font)

        text_w = bbox[2] - bbox[0]
        x = (w - text_w) // 2
        y = pos[1]

        draw.text((x,y), text, font=font, fill=color)

    else:
        draw.text(pos, text, font=font, fill=color)

    return np.array(img_pil)

# SESSION STORAGE SYSTEM
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_SRC = os.path.dirname(BASE_DIR)
SESSION_FOLDER = os.path.join(PROJECT_SRC, "sessions")

os.makedirs(SESSION_FOLDER, exist_ok=True)

current_session_file = None

# ERASER UI
def draw_modern_eraser(frame, x, y, progress):

    cv2.circle(frame, (x, y), 25, (100, 100, 100), 2, cv2.LINE_AA)

    angle = int((progress / 100) * 360)

    cv2.ellipse(
        frame,
        (x, y),
        (25, 25),
        -90,
        0,
        angle,
        (0, 0, 255),
        3,
        cv2.LINE_AA
    )

# MAIN UI PANEL
def draw_ui_accent(frame, active_gesture, depth_val):

    global pulse_frame
    pulse_frame += 1

    h, w = frame.shape[:2]

    overlay = frame.copy()

    # modern panel
    panel_w = 200
    panel_h = 70

    x1, y1 = 20, 20
    x2, y2 = x1 + panel_w, y1 + panel_h

    cv2.rectangle(overlay, (x1,y1), (x2,y2), (0,0,0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    # green accent
    cv2.rectangle(frame, (x1, y1), (x1+4, y2), (0,255,0), -1)

    gesture_label = "WAITING" if active_gesture == "none" else active_gesture.upper()

    frame = draw_text(
        frame,
        "GESTURE",
        (x1+16, y1+6),
        16,
        (160,160,160),
        "Montserrat-Medium.ttf"
    )

    frame = draw_text(
        frame,
        gesture_label,
        (x1+16, y1+28),
        24,
        (255,255,255),
        "Orbitron-Bold.ttf"
    )

    # PULSE INDICATOR
    pulse_radius = 5 + int(2*np.sin(pulse_frame * 0.2))

    indicator_x = x2 - 18
    indicator_y = y1 + panel_h // 2

    cv2.circle(frame, (indicator_x, indicator_y), pulse_radius, (0,255,0), -1)

    # DEPTH BAR
    bar_top = 160
    bar_bottom = h - 160

    cv2.rectangle(frame, (w-70, bar_top), (w-50, bar_bottom), (35,35,35), -1)

    fill_h = int((bar_bottom - bar_top) * depth_val)

    cv2.rectangle(
        frame,
        (w-70, bar_bottom),
        (w-50, bar_bottom - fill_h),
        (0,255,0),
        -1
    )

    frame = draw_text(
        frame,
        "DEPTH",
        (w-90, bar_top-35),
        18,
        (170,170,170),
        "Montserrat-Medium.ttf"
    )

    return frame

def draw_mode_title(frame):
    h, w = frame.shape[:2]

    frame = draw_text(
        frame,
        "SHAPES MODE",
        (w//2 - 250, 20),
        60,
        (255,255,255),
        "Orbitron-Bold.ttf"
    )

    return frame

def project_3d(x, y, z, w, h, ax, ay):
    cx, cy = x - w//2, y - h//2
    rx = cx * np.cos(ay) + z * np.sin(ay)
    rz = -cx * np.sin(ay) + z * np.cos(ay)
    ry = cy * np.cos(ax) - rz * np.sin(ax)
    rz = cy * np.sin(ax) + rz * np.cos(ax)
    focal = 500
    factor = focal / (rz + focal)
    return (int(rx * factor) + w//2, int(ry * factor) + h//2)

class GeometricShape:
    def __init__(self, color=(0, 0, 255), thickness=2):
        self.color = color
        self.thickness = thickness
        self.current_depth = 0.0
        self.ax, self.ay = 0.0, 0.0
        self.center = np.array([0, 0])
        self.is_locked = False
        self.scale_factor = 1.0

class Circle(GeometricShape):
    def __init__(self, center, radius):
        super().__init__((255, 255, 0))
        self.center = np.array(center)
        self.original_radius = radius
        self.current_radius = radius
        self.label = "CIRCLE"

    def scale(self, factor):
        self.current_radius = int(self.original_radius * factor)

    def draw(self, frame, is_selected=False):
        h, w, _ = frame.shape
        color = (0, 0, 255) if self.is_locked else ((255, 255, 255) if is_selected else self.color)
        thick = 4 if is_selected else 2
        r = int(self.current_radius * self.scale_factor)

        for i in range(0, 180, 60):
            pts = []
            for deg in range(0, 360, 30):
                rad = np.radians(deg)
                x = self.center[0] + np.cos(rad) * r
                y = self.center[1] + np.sin(rad) * r * np.cos(np.radians(i) * self.current_depth)
                z = np.sin(rad) * r * np.sin(np.radians(i) * self.current_depth)
                pts.append(project_3d(x, y, z, w, h, self.ax, self.ay))
            cv2.polylines(frame, [np.array(pts)], True, color, thick, cv2.LINE_AA)

class Polygon(GeometricShape):
    def __init__(self, points, label):
        super().__init__((0, 100, 255))
        self.center = np.mean(points, axis=0)
        self.relative_points = np.array(points, dtype=np.float32) - self.center
        self.label = label.upper()

    def scale(self, factor):
        self.scale_factor = factor

    def draw(self, frame, is_selected=False):
        h, w, _ = frame.shape
        color = (0, 0, 255) if self.is_locked else ((255, 255, 255) if is_selected else self.color)
        thick = 4 if is_selected else 2
        z_val = 100 * self.current_depth
        current_pts = self.center + self.relative_points * self.scale_factor
        f_pts = [project_3d(p[0], p[1], -z_val * self.scale_factor, w, h, self.ax, self.ay) for p in current_pts]

        if self.label in ["SQUARE", "RECTANGLE"]:
            b_pts = [project_3d(p[0], p[1], z_val * self.scale_factor, w, h, self.ax, self.ay) for p in current_pts]
            for i in range(4):
                cv2.line(frame, f_pts[i], f_pts[(i+1)%4], color, thick, cv2.LINE_AA)
                if self.current_depth > 0.1:
                    cv2.line(frame, b_pts[i], b_pts[(i+1)%4], color, thick, cv2.LINE_AA)
                    cv2.line(frame, f_pts[i], b_pts[i], (200, 200, 200), 1, cv2.LINE_AA)
        else:
            tip = project_3d(self.center[0], self.center[1], z_val * 2 * self.scale_factor, w, h, self.ax, self.ay)
            for i in range(len(f_pts)):
                cv2.line(frame, f_pts[i], f_pts[(i+1)%len(f_pts)], color, thick, cv2.LINE_AA)
                if self.current_depth > 0.1:
                    cv2.line(frame, f_pts[i], tip, (200, 200, 200), 1, cv2.LINE_AA)

def generate_star(center, outer_r, inner_r=0.5, points=5):
    cx, cy = center
    pts = []

    for i in range(points * 2):
        r = outer_r if i % 2 == 0 else outer_r * inner_r
        angle = np.pi * i / points - np.pi/2
        x = cx + r * np.cos(angle)
        y = cy + r * np.sin(angle)
        pts.append([x, y])

    return np.array(pts)

def generate_regular_polygon(center, radius, sides):
    cx, cy = center
    pts = []

    for i in range(sides):
        angle = 2 * np.pi * i / sides - np.pi/2
        x = cx + radius * np.cos(angle)
        y = cy + radius * np.sin(angle)
        pts.append([x, y])

    return np.array(pts)

def get_perfect_shape(points):
    if len(points) < 5:
        return None

    start_pt = np.array(points[0])
    end_pt = np.array(points[-1])
    dist_start_end = np.linalg.norm(start_pt - end_pt)

    if dist_start_end < 70:
        cnt = np.array(points).reshape((-1, 1, 2)).astype(np.int32)
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)

        if len(approx) == 3:
            (x, y), r = cv2.minEnclosingCircle(cnt)
            pts = generate_regular_polygon((x, y), r, 3)
            return Polygon(pts, "triangle")
        
        elif len(approx) == 4:
            x, y, w, h = cv2.boundingRect(cnt)

            aspect_ratio = w / float(h)

            pts = np.array([
                [x, y],
                [x+w, y],
                [x+w, y+h],
                [x, y+h]
            ])

            if 0.8 <= aspect_ratio <= 1.5:
                return Polygon(pts, "square")
            else:
                return Polygon(pts, "rectangle")
        
        elif len(approx) == 5:
            (x, y), r = cv2.minEnclosingCircle(cnt)
            pts = generate_regular_polygon((x, y), r, 5)
            return Polygon(pts, "pentagon")
        
        elif len(approx) == 6:
            (x, y), r = cv2.minEnclosingCircle(cnt)
            pts = generate_regular_polygon((x, y), r, 6)
            return Polygon(pts, "hexagon")

        elif len(approx) >= 8:
            (x, y), r = cv2.minEnclosingCircle(cnt)
            pts = generate_star((x, y), r)
            return Polygon(pts, "star")
  
        else:
            area = cv2.contourArea(cnt)
            if peri > 0:
                circularity = (4 * np.pi * area) / (peri * peri)
                if circularity > 0.6:
                    (x, y), r = cv2.minEnclosingCircle(cnt)
                    return Circle((int(x), int(y)), int(r))
    return None

def save_session(session_name=None):
    global current_session_file

    if current_session_file is not None:
        filename = current_session_file
    else:
        if not session_name:
            session_name = "shapes_session"

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"{session_name}_{timestamp}.json"
        current_session_file = filename

    path = os.path.join(SESSION_FOLDER, filename)

    shapes_data = []

    for s in shapes_list:

        shape_info = {
            "type": s.label.lower(),
            "center": s.center.tolist(),
            "depth": s.current_depth,
            "ax": s.ax,
            "ay": s.ay,
            "scale": s.scale_factor,
            "locked": s.is_locked
        }

        if isinstance(s, Circle):
            shape_info["radius"] = s.current_radius

        elif isinstance(s, Polygon):
            shape_info["points"] = (s.center + s.relative_points).tolist()

        shapes_data.append(shape_info)

    data = {
        "mode": "shapes",
        "shapes": shapes_data
    }

    with open(path, "w") as f:
        json.dump(data, f)

    print(f"[INFO] Shapes session saved: {filename}")

def load_session(filename):
    global shapes_list, current_session_file

    path = os.path.join(SESSION_FOLDER, filename)

    if not os.path.exists(path):
        return

    with open(path, "r") as f:
        data = json.load(f)

    loaded_shapes = []

    for s in data.get("shapes", []):
        if s["type"] == "circle":
            shape = Circle(tuple(s["center"]), s["radius"])

        else:
            shape = Polygon(np.array(s["points"]), s["type"])

        shape.current_depth = s["depth"]
        shape.ax = s["ax"]
        shape.ay = s["ay"]
        shape.scale_factor = s["scale"]
        shape.is_locked = s["locked"]

        loaded_shapes.append(shape)

    shapes_list = loaded_shapes
    current_session_file = filename

    print(f"[INFO] Shapes session loaded: {filename}")

# main loop
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # better quality on Windows
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)

shapes_list, current_stroke = [], []
target_depth_ui = 0.0
selected_index = -1
lock_cooldown = 0

# auto-load session if launched from menu
if len(sys.argv) > 2 and sys.argv[1] == "--load":
    load_session(sys.argv[2])

window_name = "Shapes Module"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (1280, 720))
    h, w, _ = frame.shape

    gesture, index_positions, thumb_positions, hand_count, frame = get_gesture(frame)

    # reconstruct cursor + hand presence
    if hand_count >= 1:
        ix, iy = index_positions[0]
        landmarks_present = True
    else:
        landmarks_present = False
    
    frame = draw_text(
        frame,
        f"Hand: {'Yes' if landmarks_present else 'No'}",
        (20,100),
        28,
        (0,255,0),
        "Montserrat-Medium.ttf"
    )

    # if no hand detected, cursor stay at center
    if not landmarks_present:
        hand_missing_frames += 1

        if hand_missing_frames < HAND_LOST_TOLERANCE:
            ix, iy = last_ix, last_iy  # keep cursor stable
        else:
            active_gesture = "none"    # stop drawing after real loss
    else:
        hand_missing_frames = 0
        last_ix, last_iy = ix, iy

    # gesture smoothing
    if gesture == gesture_memory:
        gesture_hold_frames += 1
    else:
        gesture_memory = gesture
        gesture_hold_frames = 0

    if gesture_hold_frames >= GESTURE_STABILITY:
        active_gesture = gesture_memory
    else:
        active_gesture = "none"

    # ==============================
    # FATIGUE TIMER LOGIC (HAND-BASED)
    # ==============================
    hand_present = (landmarks_present)

    if hand_present:
        if not fatigue_active:
            fatigue_start_time = time.time()
            fatigue_active = True
    else:
        # hand lowered → full reset
        fatigue_active = False
        fatigue_warning = False
        fatigue_start_time = None
        rest_start_time = None

    if fatigue_active:
        elapsed = time.time() - fatigue_start_time

        if elapsed >= FATIGUE_LIMIT:
            fatigue_warning = True
            
            if rest_start_time is None:
                rest_start_time = time.time()

    # disable interaction during rest
    if fatigue_warning:
        active_gesture = "none"

    # show active usage timer
    if fatigue_active and not fatigue_warning:
        active_time = int(time.time() - fatigue_start_time)

        frame = draw_text(
            frame,
            f"Active: {active_time}s",
            (20,130),
            28,
            (0,255,0),
            "Montserrat-Medium.ttf"
        )

    if landmarks_present:
        closest_dist = SELECTION_RADIUS
        temp_idx = -1

        for i, s in enumerate(shapes_list):
            dist = np.hypot(s.center[0] - ix, s.center[1] - iy)
            if dist < closest_dist:
                closest_dist = dist
                temp_idx = i

        # Select new shape ONLY when hovering close
        if temp_idx != -1:
            selected_index = temp_idx

        if active_gesture == "erase" and selected_index != -1:
            erase_progress += 6
            if erase_progress >= 100:
                target_s = shapes_list.pop(selected_index)
                imploding_shapes.append(target_s)
                erase_progress = 0
                selected_index = -1
        else:
            erase_progress = max(0, erase_progress - 8)

            if selected_index != -1:
                target_s = shapes_list[selected_index]
                target_depth_ui = target_s.current_depth

                if active_gesture == "clear" and lock_cooldown == 0:
                    target_s.is_locked = not target_s.is_locked
                    lock_cooldown = 20

                if not target_s.is_locked:

                    # ==========================
                    # TWO-HAND DEPTH CONTROL
                    # ==========================
                    if hand_count == 2 and selected_index != -1:

                        (x1, y1), (x2, y2) = index_positions
                        distance = np.hypot(x1 - x2, y1 - y2)

                        depth_value = np.clip(
                            np.interp(distance, [80, 350], [0.0, 1.0]),
                            0, 1
                        )

                        target_s.current_depth += (depth_value - target_s.current_depth) * lerp_factor
                        target_depth_ui = target_s.current_depth

                        is_dragging = False


                    # ==========================
                    # MOVE (Grip Pose)
                    # ==========================
                    elif active_gesture == "move":

                        if not is_dragging:
                            drag_offset = target_s.center - np.array([ix, iy])
                            is_dragging = True

                        target_s.center = np.array([ix, iy]) + drag_offset

                    # ==========================
                    # RESIZE (Pinch)
                    # ==========================
                    elif active_gesture == "resize" and selected_index != -1:

                        tx, ty = thumb_positions[0]
                        d = np.hypot(tx - ix, ty - iy)
                        target_s.scale(np.interp(d, [20, 150], [0.5, 3.0]))

                        is_dragging = False

                    # ==========================
                    # ROTATE
                    # ==========================   
                    elif active_gesture == "rotate":

                        if rotate_start_pos is None:
                            rotate_start_pos = (ix, iy)
                            shape_start_ax = target_s.ax
                            shape_start_ay = target_s.ay

                        dx = ix - rotate_start_pos[0]
                        dy = iy - rotate_start_pos[1]

                        sensitivity = 0.005   # smaller = slower rotation

                        target_s.ay = shape_start_ay + dx * sensitivity
                        target_s.ax = shape_start_ax + dy * sensitivity

                    if active_gesture != "rotate":
                        rotate_start_angle = None
                        shape_start_angle = None
    
    # Reset rotate & drag when not active
    if active_gesture != "rotate":
        rotate_start_pos = None

    if active_gesture != "move":
        is_dragging = False

    # drawing (only when hand present and draw gesture)
    if landmarks_present and active_gesture == "draw":
        current_stroke.append([ix, iy])
    else:
        if len(current_stroke) > 5:
            s_new = get_perfect_shape(current_stroke)
            if s_new:
                shapes_list.append(s_new)
            # If not valid shape → DO NOTHING
        current_stroke = []

    if lock_cooldown > 0:
        lock_cooldown -= 1

    # Draw shapes
    for i, s in enumerate(shapes_list):
        is_active = (i == selected_index)
        s.draw(frame, is_selected=is_active)

    # Draw label ONLY if a shape is selected
    if selected_index != -1:
        active_shape = shapes_list[selected_index]
        cx, cy = active_shape.center.astype(int)

        frame = draw_text(
            frame,
            active_shape.label,
            (cx - 70, cy - 100),
            32,
            (255,255,255),
            "Montserrat-SemiBold.ttf"
        )

    for s in imploding_shapes[:]:
        s.scale_factor -= 0.25
        if s.scale_factor <= 0:
            imploding_shapes.remove(s)
        else:
            s.draw(frame, is_selected=True)

    if erase_progress > 0:
        draw_modern_eraser(frame, ix, iy, erase_progress)

    if len(current_stroke) > 1:
        cv2.polylines(frame, [np.array(current_stroke, np.int32)], False, (0, 255, 255), 2, cv2.LINE_AA)

    frame = draw_ui_accent(frame, active_gesture, target_depth_ui)

    frame = draw_text(
        frame,
        "Press B to return to menu",
        (20, h - 40),
        28,
        (180,180,180),
        "Montserrat-Medium.ttf"
    )

    frame = draw_mode_title(frame)

    # ==============================
    # FATIGUE WARNING UI
    # ==============================
    if fatigue_warning:

        # dark overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0,0), (w,h), (0,0,0), -1)
        overlay = cv2.GaussianBlur(frame.copy(), (35,35), 0)
        cv2.addWeighted(overlay, 0.80, frame, 0.20, 0, frame)

        center_y = h // 2

        # title
        frame = draw_text(
            frame,
            "ARM FATIGUE WARNING",
            (0, center_y - 60),
            50,
            (0,0,200),
            "Orbitron-Bold.ttf",
            center=True
        )

        # message
        frame = draw_text(
            frame,
            "Please rest your arm for 10 seconds",
            (0, center_y),
            32,
            (255,255,255),
            "Montserrat-Medium.ttf",
            center=True
        )

        rest_elapsed = time.time() - rest_start_time if rest_start_time else 0
        remaining = max(0, int(REST_DURATION - rest_elapsed))

        # countdown
        frame = draw_text(
            frame,
            f"Rest countdown: {remaining}s",
            (0, center_y + 60),
            36,
            (0,0,200),
            "Montserrat-SemiBold.ttf",
            center=True
        )

        if remaining == 0:
            fatigue_warning = False
            fatigue_active = False
            fatigue_start_time = None
            rest_start_time = None

    cv2.imshow(window_name, frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('b'):
        cv2.destroyWindow(window_name)
        break

    # Save session
    if key == ord('s'):

        if current_session_file is not None:
            save_session()

        else:
            name, ok = QInputDialog.getText(
                None,
                "Save Shapes Session",
                "Enter session name:"
            )

            if ok and name:
                save_session(name)

cap.release()
cv2.destroyAllWindows()
sys.exit(0)