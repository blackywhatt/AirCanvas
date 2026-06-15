import cv2
import numpy as np
import time
import json
import os
import sys
# from datetime import datetime
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.dirname(BASE_DIR))
from gesture_engine import get_gesture
from PIL import ImageFont, ImageDraw, Image

FONT_DIR = os.path.join(BASE_DIR, "fonts")

FONT_CACHE = {}

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

two_hand_frames = 0
zoom_mode = False
smooth_distance = None
hud_badge_text = ""
hud_badge_timer = 0
# ==============================
# SESSION STORAGE
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# SESSION_FOLDER = os.path.join(BASE_DIR, "sessions")
# os.makedirs(SESSION_FOLDER, exist_ok=True)

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

def get_cached_font(font_name, size):
    key = (font_name, size)
    if key not in FONT_CACHE:
        font_path = os.path.join(FONT_DIR, font_name)
        try:
            FONT_CACHE[key] = ImageFont.truetype(font_path, size)
        except Exception:
            FONT_CACHE[key] = ImageFont.load_default()
    return FONT_CACHE[key]


def draw_text(frame, text, pos, size=40, color=(255,255,255),
              font_name="Montserrat-Medium.ttf", center=False):

    font = get_cached_font(font_name, size)
    img_pil = Image.fromarray(frame)
    draw = ImageDraw.Draw(img_pil)

    if center:
        w = frame.shape[1]
        bbox = draw.textbbox((0,0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (w - text_w)//2
        draw.text((x, pos[1]), text, font=font, fill=color)
    else:
        draw.text(pos, text, font=font, fill=color)

    return np.array(img_pil)


def draw_hud_panel(frame, lines, x, y, width, padding=14, bg_color=(20, 20, 40), alpha=0.55):
    h, w, _ = frame.shape
    height = padding * 2 + len(lines) * 22

    x2 = min(w - 10, x + width)
    y2 = min(h - 10, y + height)

    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x2, y2), bg_color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    line_y = y + padding
    for i, line in enumerate(lines):
        size = 20 if i == 0 else 16
        font_name = "Orbitron-Bold.ttf" if i == 0 else "Montserrat-Medium.ttf"
        frame = draw_text(frame, line, (x + 16, line_y), size, (245,245,255), font_name)
        line_y += 28

    # left accent line
    cv2.rectangle(frame, (x + 6, y + 10), (x + 10, y2 - 10), (80, 190, 255), -1)

    return frame


def draw_floating_badge(frame, text, alpha=1.0):
    if not text:
        return frame

    # place pill in top-right corner to avoid overlapping title
    h, w, _ = frame.shape
    badge_w, badge_h = 200, 36
    x = max(10, w - 220)
    y = 20

    overlay = frame.copy()
    # pill background
    cv2.rectangle(overlay, (x, y), (x + badge_w, y + badge_h), (18, 28, 38), -1)
    cv2.addWeighted(overlay, 0.7 * alpha, frame, 1 - 0.7 * alpha, 0, frame)
    # subtle border
    cv2.rectangle(frame, (x, y), (x + badge_w, y + badge_h), (85, 190, 255), 1, cv2.LINE_AA)
    # text
    frame = draw_text(frame, text, (x + 14, y + 6), 16, (225, 235, 255), "Orbitron-Bold.ttf")
    return frame

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
                  (14, 18, 28), -1)

    cv2.addWeighted(overlay, 0.68, frame, 0.32, 0, frame)

    # subtle border
    cv2.rectangle(frame, (panel_x, panel_y), (panel_x + width, panel_y + height), (80, 180, 255), 1, cv2.LINE_AA)

    # draw text
    y_offset = panel_y + 26
    for i, line in enumerate(lines):

        size = 24 if i == 0 else 18
        font_name = "Orbitron-Bold.ttf" if i == 0 else "Montserrat-Medium.ttf"

        frame = draw_text(
            frame,
            line,
            (panel_x + 14, y_offset),
            size,
            (235,235,245),
            font_name
        )

        y_offset += 30

    return frame


def draw_info_card_fixed(frame, planet):
    # fixed right-side info card to avoid overlapping planets
    h, w, _ = frame.shape
    card_w = 260
    card_x = max(20, w - 280)
    card_y = 20

    lines = [
        planet.get("name", ""),
        f"Type: {planet.get('info', {}).get('type', '')}",
        f"Moons: {planet.get('info', {}).get('moons', '')}",
        f"Orbit: {planet.get('orbit', '')}",
        f"Speed: {planet.get('speed', ''):.3f}" if 'speed' in planet else "",
        planet.get('info', {}).get('fact', '')
    ]

    padding = 18
    height = padding * 2 + len(lines) * 26

    overlay = frame.copy()
    cv2.rectangle(overlay, (card_x, card_y), (card_x + card_w, card_y + height), (12, 18, 30), -1)
    cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)

    cv2.rectangle(frame, (card_x, card_y), (card_x + card_w, card_y + height), (85, 190, 255), 1, cv2.LINE_AA)

    y = card_y + 18
    for i, line in enumerate(lines):
        if not line:
            continue
        size = 20 if i == 0 else 14
        font = "Orbitron-Bold.ttf" if i == 0 else "Montserrat-Medium.ttf"
        frame = draw_text(frame, line, (card_x + 14, y), size, (240,240,245), font)
        y += 26

    return frame


def draw_left_status_panel(frame, selected_name, gesture, simulation_speed, zoom_mode):
    # compact left status panel (top-left)
    h, w, _ = frame.shape
    panel_x, panel_y = 20, 20
    panel_w = 180

    # determine height dynamically
    lines = ["SELECTED", selected_name]

    if zoom_mode:

        lines += ["ACTION", "ZOOM"]

    elif gesture not in ["none", "idle"]:

        display_gesture = {
            "draw": "SELECT",
            "resize": "ORBIT SPEED",
            "erase": "RESET",
            "rotate": "ROTATE"
        }.get(gesture, gesture.upper())

        lines += ["ACTION", display_gesture]

        if gesture == "resize":
            lines += ["ORBIT SPEED", f"{simulation_speed:.1f}x"]

    padding = 12
    height = padding * 2 + len(lines) * 28

    overlay = frame.copy()
    cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + height), (12, 16, 24), -1)
    cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)

    # left accent
    cv2.rectangle(frame, (panel_x + 6, panel_y + 10), (panel_x + 10, panel_y + height - 10), (80, 190, 255), -1)

    # render lines: label small, value large
    y = panel_y + padding
    i = 0
    while i < len(lines):
        label = lines[i]
        value = lines[i+1] if i+1 < len(lines) else ""

        frame = draw_text(frame, label, (panel_x + 16, y), 14, (180, 200, 220), "Montserrat-Medium.ttf")
        y += 20
        frame = draw_text(frame, value, (panel_x + 16, y), 18, (245, 245, 255), "Orbitron-Bold.ttf")
        y += 34
        i += 2

    return frame

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # better quality on Windows
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
        if hand_count == 2 and len(index_positions) >= 2:

            (x1, y1), (x2, y2) = index_positions[:2]

            distance = np.hypot(x1 - x2, y1 - y2)

            if smooth_distance is None:
                smooth_distance = distance
            else:
                smooth_distance = smooth_distance * 0.9 + distance * 0.1

            two_hand_frames += 1
            if two_hand_frames >= 15:
                zoom_mode = True
                target_scale = np.interp(smooth_distance, [80, 400], [0.6, 2.5])
        else:
            two_hand_frames = 0
            zoom_mode = False
            smooth_distance = None

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

            frame = draw_text(
                frame,
                f"Hold to reset: {int(progress*100)}%",
                (20, 165),
                24,
                (0,150,255),
                "Montserrat-SemiBold.ttf"
            )

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
    # Floating Badge / Status Indicator
    badge_text = None
    if zoom_mode:
        badge_text = "ZOOM MODE"
    elif gesture != "none":
        if gesture == "draw":
            badge_text = "SELECT"
        elif gesture == "erase":
            badge_text = "RESET"
        elif gesture == "resize":
            badge_text = "ORBIT SPEED"
        elif gesture == "rotate":
            badge_text = "ROTATE"
        else:
            badge_text = gesture.upper()

    if badge_text:
        hud_badge_text = badge_text
        hud_badge_timer = 30
    elif hud_badge_timer > 0:
        hud_badge_timer -= 1

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

            # Highlight selected orbit (soft cyan)
            if i == selected_index:
                color = (100, 220, 200)   # soft cyan
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

        display_radius = radius + 4 if i == selected_index else radius
        if i == selected_index:
            glow_radius = radius + 10
            overlay = frame.copy()
            # reduced glow opacity for subtle highlight
            cv2.circle(overlay, (px, py), glow_radius, (70, 175, 240), -1)
            cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)

        # Draw orbit trail
        for trail_angle in orbit_trails[i]:

            trail_orbit = p["orbit"] * solar_scale

            tx = np.cos(trail_angle) * trail_orbit
            ty = np.sin(trail_angle) * trail_orbit

            tpx, tpy, _ = project_3d(tx + w // 2, ty + h // 2, 0, w, h, ax, ay)

            alpha = orbit_trails[i].index(trail_angle) / MAX_TRAIL_LENGTH
            brightness = int(50 + 150 * alpha)

            cv2.circle(frame, (tpx, tpy), 2, (brightness,brightness,brightness), -1)

        cv2.circle(frame, (px, py), display_radius, color, -1, cv2.LINE_AA)

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

        # selected planet actions: draw fixed info card on the right (avoid floating labels)
        if i == selected_index:
            frame = draw_info_card_fixed(frame, p)
    # ==============================
    # HUD
    # ==============================
    hud_lines = [
        f"Selected: {planets[selected_index]['name']}"
    ]
    if gesture != "none":
        display_gesture = {
            "draw": "SELECT",
            "erase": "RESET",
            "resize": "ORBIT SPEED",
            "rotate": "ROTATE"
        }.get(gesture, gesture.upper())
        hud_lines.append(f"Gesture: {display_gesture}")
        if gesture == "resize":
            hud_lines.append(f"Orbit Speed: {simulation_speed:.1f}x")

    frame = draw_left_status_panel(frame, planets[selected_index]['name'], gesture, simulation_speed, zoom_mode)

    # compact top-center title
    frame = draw_text(
        frame,
        "SOLAR SYSTEM",
        (w // 2, 20),
        30,
        (245, 245, 245),
        "Orbitron-Bold.ttf",
        center=True
    )

    # frame = draw_floating_badge(frame, hud_badge_text, min(1.0, hud_badge_timer / 30.0))

    # ==============================
    # Show Frame
    # ==============================
    cv2.imshow(window_name, frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('b'):
        break

    # Save session
    # if key == ord('s'):

    #     if current_session_file is not None:
    #         save_session()

    #     else:
    #         name = input("Enter session name: ")
    #         if name:
    #             save_session(name)

cap.release()
cv2.destroyAllWindows()