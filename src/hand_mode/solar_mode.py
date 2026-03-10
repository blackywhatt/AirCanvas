import cv2
import numpy as np
import time
import json
import os
import sys
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QInputDialog
from gesture_engine import get_gesture

qt_app = QApplication.instance()
if not qt_app:
    qt_app = QApplication(sys.argv)

prev_ix = None
prev_iy = None

last_gesture = "none"
gesture_cooldown = 0
COOLDOWN_FRAMES = 8

gesture_history = []
GESTURE_STABLE_FRAMES = 6
confirmed_gesture = "none"

erase_start_time = None
RESET_HOLD_TIME = 1.5

select_cooldown = 0
SELECT_DELAY = 15   # frames between selections

# ==============================
# SESSION STORAGE
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FOLDER = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSION_FOLDER, exist_ok=True)

current_session_file = None

# ==============================
# Solar System Data
# ==============================
planets = [
    {"name": "SUN", "orbit": 0, "radius": 30, "color": (0, 255, 255), "angle": 0, "speed": 0},
    {"name": "MERCURY", "orbit": 90,  "radius": 6,  "color": (200, 200, 200), "angle": 0, "speed": 0.04  ,  "info": {"type": "Terrestrial", "moons": "0", "fact": "Closest to Sun"}},
    {"name": "VENUS",   "orbit": 130, "radius": 8,  "color": (0, 180, 255),   "angle": 0, "speed": 0.03  ,  "info": {"type": "Terrestrial", "moons": "0", "fact": "Hottest planet"}},

    {
        "name": "EARTH", "orbit": 180, "radius": 10, "color": (255, 100, 100), "angle": 0, "speed": 0.02,
        "moon": {"radius": 3, "orbit": 20, "angle": 0, "speed": 0.08, "color": (200, 200, 200)}, "info": {"type": "Terrestrial", "moons": "1", "fact": "Supports life"}
    },

    {"name": "MARS",    "orbit": 230, "radius": 9,  "color": (0, 100, 255),   "angle": 0, "speed": 0.016  , "info": {"type": "Terrestrial", "moons": "2", "fact": "Red planet"}},
    {"name": "JUPITER", "orbit": 300, "radius": 18, "color": (0, 165, 255),   "angle": 0, "speed": 0.01  , "info": {"type": "Gas Giant", "moons": "79+", "fact": "Largest planet"}},
    {"name": "SATURN", "orbit": 380, "radius": 16, "color": (150, 200, 255),  "angle": 0, "speed": 0.008, "ring": True  , "info": {"type": "Gas Giant", "moons": "80+", "fact": "Has rings"}},
    {"name": "URANUS",  "orbit": 450, "radius": 14, "color": (255, 255, 0),   "angle": 0, "speed": 0.006  , "info": {"type": "Ice Giant", "moons": "27", "fact": "Rotates sideways"}},
    {"name": "NEPTUNE", "orbit": 520, "radius": 14, "color": (255, 100, 0),   "angle": 0, "speed": 0.005  , "info": {"type": "Ice Giant", "moons": "14", "fact": "Strongest winds"}},
]

solar_scale = 1.0
target_scale = 1.0
ax, ay = 0.0, 0.0
selected_index = 0
vx, vy = 0.0, 0.0   # rotation velocity
rotation_damping = 0.85
# Simulation speed
simulation_speed = 1.0
# Orbit trails
orbit_trails = {i: [] for i in range(len(planets))}
MAX_TRAIL_LENGTH = 60

# ==============================
# 3D Projection
# ==============================
def project_3d(x, y, z, w, h, ax, ay):
    cx, cy = x - w // 2, y - h // 2

    rx = cx * np.cos(ay) + z * np.sin(ay)
    rz = -cx * np.sin(ay) + z * np.cos(ay)

    ry = cy * np.cos(ax) - rz * np.sin(ax)
    rz = cy * np.sin(ax) + rz * np.cos(ax)

    focal = 500
    factor = focal / (rz + focal + 300)

    return (int(rx * factor) + w // 2, int(ry * factor) + h // 2, rz)

# ==============================
# Planet Info Panel
# ==============================
def draw_info_panel(frame, planet, px, py):
    info = planet.get("info", None)
    if not info:
        return

    lines = [
        planet["name"],
        f"Type: {info['type']}",
        f"Moons: {info['moons']}",
        f"Orbit: {planet['orbit']}",
        f"Speed: {planet['speed']:.3f}",
        f"{info['fact']}"
    ]

    # panel size
    width = 200
    height = 20 + len(lines) * 22

    # auto position near planet
    panel_x = px + 20
    panel_y = py - height // 2

    h, w, _ = frame.shape

    # keep panel inside screen
    if panel_x + width > w:
        panel_x = px - width - 20
    if panel_y < 0:
        panel_y = 10
    if panel_y + height > h:
        panel_y = h - height - 10

    # semi-transparent background
    overlay = frame.copy()
    cv2.rectangle(overlay,
                  (panel_x, panel_y),
                  (panel_x + width, panel_y + height),
                  (30, 30, 30), -1)

    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    # draw text
    y_offset = panel_y + 25
    for i, line in enumerate(lines):
        font_scale = 0.6 if i == 0 else 0.5
        thickness = 2 if i == 0 else 1

        cv2.putText(frame, line,
                    (panel_x + 10, y_offset),
                    cv2.FONT_HERSHEY_DUPLEX,
                    font_scale,
                    (255, 255, 255),
                    thickness,
                    cv2.LINE_AA)

        y_offset += 22

# ==============================
# Save Function
# ==============================
def save_session(session_name=None):
    global current_session_file

    if current_session_file is not None:
        filename = current_session_file
    else:
        if not session_name:
            session_name = "solar_session"

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"{session_name}_{timestamp}.json"
        current_session_file = filename

    path = os.path.join(SESSION_FOLDER, filename)

    planets_data = []

    for p in planets:
        planet_data = {
            "name": p["name"],
            "orbit": p["orbit"],
            "radius": p["radius"],
            "color": p["color"],
            "angle": p["angle"],
            "speed": p["speed"]
        }

        if "moon" in p:
            planet_data["moon"] = p["moon"]

        if "ring" in p:
            planet_data["ring"] = True

        if "info" in p:
            planet_data["info"] = p["info"]

        planets_data.append(planet_data)

    data = {
        "mode": "solar",
        "planets": planets_data,
        "solar_scale": solar_scale,
        "ax": ax,
        "ay": ay,
        "selected_index": selected_index,
        "simulation_speed": simulation_speed
    }

    with open(path, "w") as f:
        json.dump(data, f)

    print(f"[INFO] Solar session saved: {filename}")

# ==============================
# Load Function
# ==============================
def load_session(filename):
    global planets, solar_scale, ax, ay, selected_index, simulation_speed, current_session_file

    path = os.path.join(SESSION_FOLDER, filename)

    if not os.path.exists(path):
        return

    with open(path, "r") as f:
        data = json.load(f)

    planets = data.get("planets", planets)
    solar_scale = data.get("solar_scale", 1.0)
    ax = data.get("ax", 0.0)
    ay = data.get("ay", 0.0)
    
    selected_index = data.get("selected_index", 0)
    simulation_speed = data.get("simulation_speed", 1.0)

    current_session_file = filename

    print(f"[INFO] Solar session loaded: {filename}")

# ==============================
# Camera
# ==============================
# auto-load session if launched from menu
if len(sys.argv) > 2 and sys.argv[1] == "--load":
    load_session(sys.argv[2])

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # better quality on Windows
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)

window_name = "Solar System Module"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# ==============================
# Main Loop
# ==============================
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (1280, 720))
    h, w, _ = frame.shape

    gesture, index_positions, thumb_positions, hand_count, frame = get_gesture(frame)

    # ==============================
    # Gesture Stability Filter
    # ==============================
    gesture_history.append(gesture)

    if len(gesture_history) > GESTURE_STABLE_FRAMES:
        gesture_history.pop(0)

    # check if gesture stable
    if gesture_history.count(gesture_history[-1]) == GESTURE_STABLE_FRAMES:
        confirmed_gesture = gesture_history[-1]
    else:
        confirmed_gesture = "none"

    trigger = False
    if confirmed_gesture != last_gesture and gesture_cooldown == 0:
        trigger = True
        gesture_cooldown = COOLDOWN_FRAMES

    last_gesture = confirmed_gesture
    gesture = confirmed_gesture

    if gesture_cooldown > 0:
        gesture_cooldown -= 1

    # ==============================
    # Auto Orbit Animation
    # ==============================
    for p in planets:
        p["angle"] += p["speed"] * simulation_speed

        if "moon" in p:
            p["moon"]["angle"] += p["moon"]["speed"] * simulation_speed

    # ==============================
    # Gesture Controls
    # ==============================
    if hand_count > 0 and len(index_positions) > 0:

        # ================= ROTATE =================
        if gesture == "rotate":
            ix, iy = index_positions[0]

            if prev_ix is not None and prev_iy is not None:
                dx = ix - prev_ix
                dy = iy - prev_iy

                sensitivity = 0.004

                vx = dx * sensitivity
                vy = dy * sensitivity

            prev_ix = ix
            prev_iy = iy

        else:
            # reset previous finger when not rotating
            prev_ix = None
            prev_iy = None

        # ================= TWO HAND ZOOM =================
        if hand_count == 2:

            (x1, y1), (x2, y2) = index_positions

            distance = np.hypot(x1 - x2, y1 - y2)

            target_scale = np.interp(distance, [80, 400], [0.6, 2.5])

        # ================= SPEED CONTROL (PINCH) =================
        if gesture == "resize" and len(thumb_positions) > 0:
            ix, iy = index_positions[0]
            tx, ty = thumb_positions[0]

            d = np.hypot(tx - ix, ty - iy) / w

            # Pinch controls simulation speed
            simulation_speed = np.clip(np.interp(d, [0.03, 0.25], [0.2, 5.0]), 0.2, 4.0)

        # ================= DRAW =================
        if gesture == "draw":

            if select_cooldown == 0:

                min_dist = 80
                ix, iy = index_positions[0]

                for i, p in enumerate(planets):
                    orbit = p["orbit"] * solar_scale
                    x = np.cos(p["angle"]) * orbit
                    y = np.sin(p["angle"]) * orbit
                    
                    px, py, _ = project_3d(x + w // 2, y + h // 2, 0, w, h, ax, ay)

                    dist = np.hypot(ix - px, iy - py)

                    if dist < min_dist:
                        min_dist = dist
                        selected_index = i
                        select_cooldown = SELECT_DELAY

        # ================= ERASE (Hold 2 Seconds) =================
        if gesture == "erase":

            if erase_start_time is None:
                erase_start_time = time.time()

            hold_time = time.time() - erase_start_time

            progress = min(hold_time / RESET_HOLD_TIME, 1)

            cv2.putText(frame,
                        f"Hold to reset: {int(progress*100)}%",
                        (40, 130),
                        cv2.FONT_HERSHEY_DUPLEX,
                        0.7,
                        (0, 150, 255),
                        2,
                        cv2.LINE_AA)

            if hold_time >= RESET_HOLD_TIME:
                ax, ay = 0.0, 0.0
                solar_scale = 1.0

                # Clear orbit trails
                for k in orbit_trails:
                    orbit_trails[k].clear()

                erase_start_time = None

        else:
            erase_start_time = None

    if select_cooldown > 0:
        select_cooldown -= 1

    # ==============================
    # Smooth Zoom (LERP)
    # ==============================
    zoom_smooth = 0.12
    solar_scale += (target_scale - solar_scale) * zoom_smooth

    # ==============================
    # Inertial Rotation
    # ==============================
    ay += vx
    ax += vy

    vx *= rotation_damping
    vy *= rotation_damping

    # ==============================
    # Draw Orbits (WORLD SPACE → PROJECT)
    # ==============================
    # for p in planets:
    #     if p["orbit"] > 0:
    #         orbit = p["orbit"] * solar_scale

    #         orbit_pts = []
    #         for deg in range(0, 360, 5):
    #             rad = np.radians(deg)

    #             x = np.cos(rad) * orbit
    #             y = np.sin(rad) * orbit

    #             px, py, _ = project_3d(x + w // 2, y + h // 2, 0, w, h, ax, ay)
    #             orbit_pts.append((px, py))

    #         cv2.polylines(frame, [np.array(orbit_pts)], True, (80, 80, 80), 1, cv2.LINE_AA)

    for i, p in enumerate(planets):

        if p["orbit"] > 0:

            orbit = p["orbit"] * solar_scale

            orbit_pts = []
            for deg in range(0, 360, 5):

                rad = np.radians(deg)

                x = np.cos(rad) * orbit
                y = np.sin(rad) * orbit

                px, py, _ = project_3d(x + w // 2, y + h // 2, 0, w, h, ax, ay)
                orbit_pts.append((px, py))

            # Highlight selected orbit
            if i == selected_index:
                color = (0, 255, 255)   # bright yellow
                thickness = 2
            else:
                color = (80, 80, 80)
                thickness = 1

            cv2.polylines(frame, [np.array(orbit_pts)], True, color, thickness, cv2.LINE_AA)

    # ==============================
    # Draw Planets + Moon
    # ==============================
    render_planets = []

    # collect planets
    for i, p in enumerate(planets):

        orbit = p["orbit"] * solar_scale

        if orbit == 0:
            x, y = 0, 0
        else:
            x = np.cos(p["angle"]) * orbit
            y = np.sin(p["angle"]) * orbit

        px, py, depth = project_3d(x + w // 2, y + h // 2, 0, w, h, ax, ay)

        if p["name"] == "SUN":
            sun_px, sun_py = px, py

        render_planets.append((depth, i, p, x, y, px, py))

        # Store trail positions
        if p["orbit"] > 0:
            orbit_trails[i].append(p["angle"])

        if len(orbit_trails[i]) > MAX_TRAIL_LENGTH:
            orbit_trails[i].pop(0)

    # sort planets (far → near)
    render_planets.sort(reverse=True)


    # draw planets
    for depth, i, p, x, y, px, py in render_planets:

        depth_factor = np.clip(1 - depth / 600, 0.4, 1.0)

        radius = int(p["radius"] * solar_scale * (0.7 + 0.3 * depth_factor))

        base_color = (255, 255, 255) if i == selected_index else p["color"]

        dx = sun_px - px
        dy = sun_py - py
        dist = np.hypot(dx, dy) + 1

        light_dir_x = dx / dist
        light_dir_y = dy / dist

        light_strength = 0.7 + 0.3 * light_dir_x
        light_strength = np.clip(light_strength, 0.6, 1.3)

        if p["name"] == "SUN":
            color = (0, 255, 255)
            cv2.circle(frame, (px, py), radius+2, (0,180,255), -1, cv2.LINE_AA)
            cv2.circle(frame, (px, py), radius, color, -1, cv2.LINE_AA)
            continue

        brightness = depth_factor * light_strength

        color = (
            int(base_color[0] * brightness),
            int(base_color[1] * brightness),
            int(base_color[2] * brightness)
        )

        # Draw orbit trail
        for trail_angle in orbit_trails[i]:

            trail_orbit = p["orbit"] * solar_scale

            tx = np.cos(trail_angle) * trail_orbit
            ty = np.sin(trail_angle) * trail_orbit

            tpx, tpy, _ = project_3d(tx + w // 2, ty + h // 2, 0, w, h, ax, ay)

            alpha = orbit_trails[i].index(trail_angle) / MAX_TRAIL_LENGTH
            brightness = int(50 + 150 * alpha)

            cv2.circle(frame, (tpx, tpy), 2, (brightness,brightness,brightness), -1)

        cv2.circle(frame, (px, py), radius, color, -1, cv2.LINE_AA)

        # 🪐 SATURN RING
        if "ring" in p:
            ring_radius_outer = radius + 10
            ring_radius_inner = radius + 5

            outer_pts = []
            inner_pts = []

            for deg in range(0, 360, 10):
                rad = np.radians(deg)

                # outer ring world position
                rx_outer = x + np.cos(rad) * ring_radius_outer
                ry_outer = y + np.sin(rad) * ring_radius_outer

                # inner ring world position
                rx_inner = x + np.cos(rad) * ring_radius_inner
                ry_inner = y + np.sin(rad) * ring_radius_inner

                opx, opy, _ = project_3d(rx_outer + w // 2, ry_outer + h // 2, 0, w, h, ax, ay)
                ipx, ipy, _ = project_3d(rx_inner + w // 2, ry_inner + h // 2, 0, w, h, ax, ay)

                outer_pts.append((opx, opy))
                inner_pts.append((ipx, ipy))

            cv2.polylines(frame, [np.array(outer_pts)], True, (200, 200, 200), 2, cv2.LINE_AA)
            cv2.polylines(frame, [np.array(inner_pts)], True, (120, 120, 120), 1, cv2.LINE_AA)

        # 🌙 MOON (WORLD SPACE — FIXED)
        if "moon" in p:
            moon = p["moon"]
            moon_orbit = moon["orbit"] * solar_scale

            # draw moon orbit around Earth
            moon_orbit_pts = []
            for deg in range(0, 360, 10):
                rad = np.radians(deg)

                mx_world = x + np.cos(rad) * moon_orbit
                my_world = y + np.sin(rad) * moon_orbit

                mpx, mpy, _ = project_3d(mx_world + w // 2,
                                        my_world + h // 2,
                                        0, w, h, ax, ay)

                moon_orbit_pts.append((mpx, mpy))

            cv2.polylines(frame, [np.array(moon_orbit_pts)], True, (120, 120, 120), 1, cv2.LINE_AA)

            # moon position (world → project)
            mx_world = x + np.cos(moon["angle"]) * moon_orbit
            my_world = y + np.sin(moon["angle"]) * moon_orbit

            mpx, mpy, _ = project_3d(mx_world + w // 2,
                                  my_world + h // 2,
                                  0, w, h, ax, ay)

            cv2.circle(frame, (mpx, mpy), moon["radius"], moon["color"], -1)

        # label selected planet
        if i == selected_index:
            cv2.putText(frame, p["name"],
                        (px - 40, py - radius - 10),
                        cv2.FONT_HERSHEY_DUPLEX,
                        0.8,
                        (255, 255, 255),
                        2,
                        cv2.LINE_AA)

        if i == selected_index:
            draw_info_panel(frame, p, px, py)
    # ==============================
    # HUD
    # ==============================
    cv2.putText(frame, "SOLAR SYSTEM MODE",
                (40, 50),
                cv2.FONT_HERSHEY_DUPLEX,
                1,
                (255, 255, 255),
                2,
                cv2.LINE_AA)

    cv2.putText(frame, f"SELECTED: {planets[selected_index]['name']}",
                (40, 90),
                cv2.FONT_HERSHEY_DUPLEX,
                0.7,
                (200, 200, 200),
                1,
                cv2.LINE_AA)

    cv2.putText(frame,
            f"TIME SCALE: {simulation_speed:.1f}x",
            (40, 120),
            cv2.FONT_HERSHEY_DUPLEX,
            0.6,
            (0, 255, 255),
            1,
            cv2.LINE_AA)

    cv2.putText(frame, "Gestures: Rotate | Two Hands = Zoom | Draw = Select | Erase = Reset | Resize = Speed",
                (40, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (180, 180, 180),
                1,
                cv2.LINE_AA)

    # ==============================
    # Show Frame
    # ==============================
    cv2.imshow(window_name, frame)

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
                "Save Solar Session",
                "Enter session name:"
            )

            if ok and name:
                save_session(name)

cap.release()
cv2.destroyAllWindows()