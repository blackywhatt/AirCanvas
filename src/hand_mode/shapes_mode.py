import cv2
import numpy as np
import time
import json
import os
import sys
from gesture_engine import get_gesture
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QInputDialog

qt_app = QApplication.instance()
if not qt_app:
    qt_app = QApplication(sys.argv)

rotate_start_angle = None
shape_start_angle = None

hand_missing_frames = 0
HAND_LOST_TOLERANCE = 3
active_gesture = "none"
gesture_memory = "none"
gesture_hold_frames = 0
GESTURE_STABILITY = 3
last_ix, last_iy = 640, 360

#erase indicator
erase_progress = 0
imploding_shapes = []

#lerp constant
lerp_factor = 0.1

SELECTION_RADIUS = 100

#drag variables
drag_offset = np.array([0, 0])
is_dragging = False

#gorilla arm effect
fatigue_start_time = None
fatigue_active = False
FATIGUE_LIMIT = 60  # seconds to test
fatigue_warning = False
rest_start_time = None
REST_DURATION = 10  # seconds to rest

rotate_start_pos = None
shape_start_ax = 0
shape_start_ay = 0

# ==============================
# SESSION STORAGE
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FOLDER = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSION_FOLDER, exist_ok=True)

current_session_file = None

def draw_modern_eraser(frame, x, y, progress):
    cv2.circle(frame, (x, y), 25, (100, 100, 100), 2, cv2.LINE_AA)
    angle = int((progress / 100) * 360)
    cv2.ellipse(frame, (x, y), (25, 25), -90, 0, angle, (0, 0, 255), 3, cv2.LINE_AA)

def draw_ui_accent(img, active_gesture, depth_val):
    h, w = img.shape[:2]
    overlay = img.copy()
    cv2.rectangle(overlay, (20, 20), (320, 80), (20, 20, 20), -1)
    cv2.rectangle(overlay, (w-50, 150), (w-20, h-150), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)

    cv2.putText(img, active_gesture.upper(), (40, 70),
                cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)

    fill_h = int((h - 300) * depth_val)
    cv2.rectangle(img, (w-45, h-155), (w-25, h-155-fill_h), (0, 255, 255), -1)

def draw_mode_title(frame):
    h, w = frame.shape[:2]
    cv2.putText(frame, "SHAPES MODE",
                (w//2 - 180, 50),
                cv2.FONT_HERSHEY_DUPLEX,
                1.2,
                (255, 255, 255),
                2,
                cv2.LINE_AA)

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

        if self.label == "SQUARE":
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
            return Polygon(approx.reshape(-1, 2), "triangle")
        elif len(approx) == 4:
            x, y, w, h = cv2.boundingRect(cnt)
            return Polygon(np.array([[x, y], [x+w, y], [x+w, y+h], [x, y+h]]), "square")
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
maximized = False

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
    
    cv2.putText(frame, f"HAND: {'YES' if landmarks_present else 'NO'}",
            (20, 180),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2)

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
        cv2.putText(frame,
                    f"Active: {active_time}s",
                    (20, 220),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2)

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

        cv2.putText(
            frame,
            active_shape.label,
            (cx - 60, cy - 80),
            cv2.FONT_HERSHEY_DUPLEX,
            0.9,
            (255, 255, 255),
            2,
            cv2.LINE_AA
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

    draw_ui_accent(frame, active_gesture, target_depth_ui)

    cv2.putText(frame, "Press B to return to menu",
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (180, 180, 180),
            1,
            cv2.LINE_AA)

    draw_mode_title(frame)

    # ==============================
    # FATIGUE WARNING UI
    # ==============================
    if fatigue_warning:
        overlay = frame.copy()
        cv2.rectangle(overlay, (200, 200), (w-200, h-200), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        cv2.putText(frame,
                    "ARM FATIGUE WARNING",
                    (w//2 - 220, h//2 - 40),
                    cv2.FONT_HERSHEY_DUPLEX,
                    1.0,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA)

        cv2.putText(frame,
                    "Please rest your arm for 5 seconds",
                    (w//2 - 260, h//2 + 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA)

        rest_elapsed = time.time() - rest_start_time if rest_start_time else 0
        remaining = max(0, int(REST_DURATION - rest_elapsed))

        cv2.putText(frame,
                    f"Rest countdown: {remaining}s",
                    (w//2 - 120, h//2 + 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA)

        if remaining == 0:
            fatigue_warning = False
            fatigue_active = False
            fatigue_start_time = None
            rest_start_time = None

    cv2.imshow(window_name, frame)

    if not maximized:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
        maximized = True

    key = cv2.waitKey(1) & 0xFF

    if key == ord('b'):
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