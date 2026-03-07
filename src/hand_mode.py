import cv2
import mediapipe as mp
import numpy as np
import tensorflow as tf
import pickle
import os
import time

# --- Configuration & Paths ---
MODEL_PATH = "aircanvas_model.h5"
LABEL_PATH = "labels.pickle"

if not os.path.exists(MODEL_PATH) or not os.path.exists(LABEL_PATH):
    print("Error: Model or Label file not found!")
    exit()

model = tf.keras.models.load_model(MODEL_PATH)
with open(LABEL_PATH, 'rb') as f:
    label_map = pickle.load(f)

# --- Modern Erase Animation System ---
erase_progress = 0  # 0 to 100
erasing_index = -1
erasing_type = "none" # "shape" or "ink"
imploding_shapes = [] # Stores shapes currently "shrinking" out of existence

def draw_modern_eraser(frame, x, y, progress):
    # Draw an outer ring
    cv2.circle(frame, (x, y), 25, (100, 100, 100), 2, cv2.LINE_AA)
    # Draw the progress arc
    angle = int((progress / 100) * 360)
    cv2.ellipse(frame, (x, y), (25, 25), -90, 0, angle, (0, 0, 255), 3, cv2.LINE_AA)
    if progress > 0:
        cv2.putText(frame, f"{progress}%", (x+30, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

# --- Modern UI Helpers ---
def draw_ui_accent(img, active_gesture, depth_val):
    h, w = img.shape[:2]
    overlay = img.copy()
    cv2.rectangle(overlay, (20, 20), (320, 80), (20, 20, 20), -1)
    cv2.rectangle(overlay, (w-50, 150), (w-20, h-150), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)

    cv2.line(img, (20, 20), (50, 20), (0, 0, 255), 2)
    cv2.line(img, (20, 20), (20, 50), (0, 0, 255), 2)

    cv2.putText(img, "SYSTEM ACTIVE", (40, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1, cv2.LINE_AA)
    cv2.putText(img, active_gesture.upper(), (40, 70), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)

    fill_h = int((h - 300) * depth_val)
    cv2.rectangle(img, (w-45, h-155), (w-25, h-155-fill_h), (0, 255, 255), -1)
    cv2.putText(img, "DEPTH", (w-65, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

def project_3d(x, y, z, w, h, ax, ay):
    cx, cy = x - w//2, y - h//2
    rx = cx * np.cos(ay) + z * np.sin(ay)
    rz = -cx * np.sin(ay) + z * np.cos(ay)
    ry = cy * np.cos(ax) - rz * np.sin(ax)
    rz = cy * np.sin(ax) + rz * np.cos(ax)
    focal = 500
    factor = focal / (rz + focal + 250)
    return (int(rx * factor) + w//2, int(ry * factor) + h//2)

class GeometricShape:
    def __init__(self, color=(0, 0, 255), thickness=2):
        self.color = color
        self.thickness = thickness
        self.base_size = 1.0
        self.current_depth = 0.0  
        self.ax, self.ay = 0.0, 0.0
        self.center = np.array([0, 0])
        self.is_locked = False
        self.scale_factor = 1.0 

    def is_hovered(self, tx, ty):
        dist = np.hypot(self.center[0] - tx, self.center[1] - ty)
        return dist < 100 

class Circle(GeometricShape):
    def __init__(self, center, radius):
        super().__init__((255, 255, 0))
        self.center = np.array(center)
        self.original_radius = radius
        self.current_radius = radius
    def scale(self, factor): self.current_radius = int(self.original_radius * factor)
    def draw(self, frame, is_selected=False):
        h, w, _ = frame.shape
        draw_color = (0, 0, 255) if self.is_locked else ((255, 255, 255) if is_selected else self.color)
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
            cv2.polylines(frame, [np.array(pts)], True, draw_color, thick, cv2.LINE_AA)

class Polygon(GeometricShape):
    def __init__(self, points, label):
        super().__init__((0, 100, 255))
        self.label = label
        self.original_points = np.array(points, dtype=np.float32)
        self.center = np.mean(self.original_points, axis=0)
        self.current_points = self.original_points.astype(np.int32)
    def scale(self, factor):
        new_pts = self.center + (self.original_points - self.center) * factor
        self.current_points = new_pts.astype(np.int32)
    def draw(self, frame, is_selected=False):
        h, w, _ = frame.shape
        draw_color = (0, 0, 255) if self.is_locked else ((255, 255, 255) if is_selected else self.color)
        thick = 4 if is_selected else 2
        z_val = (self.current_points[1][0] - self.current_points[0][0]) * 0.5 * self.current_depth
        current_pts = self.center + (self.current_points.astype(np.float32) - self.center) * self.scale_factor
        f_pts = [project_3d(p[0], p[1], -z_val * self.scale_factor, w, h, self.ax, self.ay) for p in current_pts]
        
        def draw_glow_line(p1, p2, col, th):
            cv2.line(frame, p1, p2, col, th+2, cv2.LINE_AA)
            cv2.line(frame, p1, p2, (255, 255, 255), 1, cv2.LINE_AA)

        if self.label == "square":
            b_pts = [project_3d(p[0], p[1], z_val * self.scale_factor, w, h, self.ax, self.ay) for p in current_pts]
            for i in range(4):
                draw_glow_line(f_pts[i], f_pts[(i+1)%4], draw_color, thick)
                if self.current_depth > 0.1:
                    draw_glow_line(b_pts[i], b_pts[(i+1)%4], draw_color, thick)
                    cv2.line(frame, f_pts[i], b_pts[i], (200, 200, 200), 1, cv2.LINE_AA)
        else:
            tip = project_3d(self.center[0], self.center[1], z_val * 2 * self.scale_factor, w, h, self.ax, self.ay)
            for i in range(len(f_pts)):
                draw_glow_line(f_pts[i], f_pts[(i+1)%len(f_pts)], draw_color, thick)
                if self.current_depth > 0.1:
                    cv2.line(frame, f_pts[i], tip, (200, 200, 200), 1, cv2.LINE_AA)

def get_perfect_shape(points):
    # CHANGED: Allow short strokes for lines, but require more for shapes
    if len(points) < 5: return None
    
    start_pt = np.array(points[0])
    end_pt = np.array(points[-1])
    dist_start_end = np.linalg.norm(start_pt - end_pt)

    # Only attempt shape recognition if the drawing is "closed"
    if dist_start_end < 70:
        cnt = np.array(points).reshape((-1, 1, 2)).astype(np.int32)
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        
        if len(approx) == 3: return Polygon(approx.reshape(-1, 2), "triangle")
        elif len(approx) == 4:
            x, y, w, h = cv2.boundingRect(cnt)
            return Polygon(np.array([[x, y], [x+w, y], [x+w, y+h], [x, y+h]]), "square")
        else:
            area = cv2.contourArea(cnt)
            if peri > 0:
                circularity = (4 * np.pi * area) / (peri * peri)
                if circularity > 0.6: # Relaxed from 0.8 to 0.6 to make circles easier
                    (x, y), r = cv2.minEnclosingCircle(cnt)
                    return Circle((int(x), int(y)), int(r))
    return None

# --- Main App ---
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils 
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.8)
cap = cv2.VideoCapture(0)

shapes_list, current_stroke = [], []
permanent_ink = [] 
target_depth_ui = 0.0 
selected_index = -1
lock_cooldown = 0

window_name = "Spatial Canvas Pro"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
maximized = False 
lerp_factor = 0.1  

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (1280, 720)) 
    h, w, _ = frame.shape
    
    res = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    active_gesture = "none"
    ix, iy = 0, 0

    if res.multi_hand_landmarks:
        for hl in res.multi_hand_landmarks:
            for idx in [4, 8, 12, 16, 20]:
                px, py = int(hl.landmark[idx].x * w), int(hl.landmark[idx].y * h)
                cv2.circle(frame, (px, py), 4, (0, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(frame, (px, py), 8, (0, 255, 255), 1, cv2.LINE_AA)
            
            ix, iy = int(hl.landmark[8].x * w), int(hl.landmark[8].y * h)
            cv2.line(frame, (ix - 15, iy), (ix + 15, iy), (255, 255, 255), 1)
            cv2.line(frame, (ix, iy - 15), (ix, iy + 15), (255, 255, 255), 1)
            
            bx, by = hl.landmark[0].x, hl.landmark[0].y
            lm_input = []
            for lm in hl.landmark: lm_input.extend([lm.x - bx, lm.y - by])
            
            pred = model.predict([lm_input], verbose=0)
            active_gesture = label_map[np.argmax(pred)]

            closest_dist = 150 
            temp_idx = -1
            target_type = "shape"
            
            for i, s in enumerate(shapes_list):
                dist = np.hypot(s.center[0] - ix, s.center[1] - iy)
                if dist < closest_dist:
                    closest_dist = dist
                    temp_idx = i
                    target_type = "shape"
            
            if temp_idx == -1:
                for i, ink in enumerate(permanent_ink):
                    dists = np.linalg.norm(ink - [ix, iy], axis=1)
                    if np.min(dists) < 40:
                        temp_idx = i
                        target_type = "ink"
                        break

            selected_index = temp_idx
            active_idx = selected_index if selected_index != -1 else len(shapes_list) - 1

            if active_gesture == "erase" and selected_index != -1:
                erase_progress += 6 
                if erase_progress >= 100:
                    if target_type == "shape":
                        target_s = shapes_list.pop(selected_index)
                        imploding_shapes.append(target_s)
                    else:
                        permanent_ink.pop(selected_index)
                    erase_progress = 0
                    selected_index = -1
            else:
                erase_progress = max(0, erase_progress - 8)

            if active_gesture == "draw":
                current_stroke.append([ix, iy])
            else:
                # FIXED: Threshold is set to 3 to catch 'l', but get_perfect_shape 
                # handles the logic of whether it's a shape or just ink.
                if len(current_stroke) > 3:
                    s_new = get_perfect_shape(current_stroke)
                    if s_new:
                        shapes_list.append(s_new)
                    else:
                        permanent_ink.append(np.array(current_stroke, np.int32))
                current_stroke = []

            if active_idx >= 0 and active_gesture not in ["erase", "draw", "none"]:
                if selected_index != -1 and target_type == "shape":
                    target_s = shapes_list[selected_index]
                    target_depth_ui = target_s.current_depth
                    if active_gesture == "clear" and lock_cooldown == 0:
                        target_s.is_locked = not target_s.is_locked
                        lock_cooldown = 20 
                    
                    if not target_s.is_locked:
                        if active_gesture == "resize":
                            d = np.hypot(hl.landmark[4].x - hl.landmark[8].x, hl.landmark[4].y - hl.landmark[8].y)
                            target_s.scale(np.interp(d, [0.05, 0.30], [0.5, 3.0]))
                        elif active_gesture == "depth":
                            span = np.hypot(hl.landmark[12].x - hl.landmark[0].x, hl.landmark[12].y - hl.landmark[0].y)
                            target_s.current_depth += (np.clip(np.interp(span, [0.2, 0.45], [0.0, 1.0]), 0, 1) - target_s.current_depth) * 0.1
                            target_depth_ui = target_s.current_depth
                        elif active_gesture == "rotate":
                            target_s.ax += (-(iy - h//2) / 150.0 - target_s.ax) * 0.3
                            target_s.ay += ((ix - w//2) / 150.0 - target_s.ay) * 0.3

    if lock_cooldown > 0: lock_cooldown -= 1

    for ink in permanent_ink:
        cv2.polylines(frame, [ink], False, (220, 220, 220), 2, cv2.LINE_AA)

    for i, s in enumerate(shapes_list):
        is_active = (i == selected_index) or (selected_index == -1 and i == len(shapes_list)-1)
        s.draw(frame, is_selected=is_active)
    
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
    cv2.imshow(window_name, frame)
    if not maximized:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
        maximized = True
    if cv2.waitKey(1) & 0xFF == ord('b'): break

cap.release()
cv2.destroyAllWindows()