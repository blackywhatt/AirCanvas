import cv2
import sys
import os
import numpy as np
import json
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import math
from PIL import ImageFont, ImageDraw, Image

# --- Setup Vosk ---
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_PATH, "model")
vosk_model = Model(MODEL_PATH)
FONT_DIR = os.path.join(BASE_PATH, "fonts")

list_of_commands = '["circle", "square", "triangle", "diamond", "pentagon", "star", "select circle", "select square", "select triangle", "red", "green", "blue", "clear", "reset", "delete shape", "bigger", "smaller", "left", "right", "up", "down", "three d", "two d", "rotate", "next shape", "previous shape", "[unk]"]'
rec = KaldiRecognizer(vosk_model, 16000, list_of_commands)
audio_queue = queue.Queue()

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

def audio_callback(indata, frames, time, status):
    audio_queue.put(np.frombuffer(indata, dtype=np.int16).tobytes())

class liveShape:
    def __init__(self, w, h):
        self.type = None
        self.size = 100
        self.draw_progress = 0
        self.is_animating = True
        self.x = w // 2
        self.y = h // 2
        self.color = (255, 0, 0)
        self.color_name = "Blue"
        self.step = 100 
        self.is_3d = False 
        self.angle = 0.5 
        self.is_rotating = False
        self.W, self.H = w, h

    def reset(self):
        self.type = None
        self.size = 100
        self.x, self.y = self.W // 2, self.H // 2
        self.is_3d = False
        self.is_rotating = False
        self.angle = 0.5

def project_3d(x, y, z, cx, cy, angle):
    rad = angle
    nx = x * math.cos(rad) + z * math.sin(rad)
    nz = -x * math.sin(rad) + z * math.cos(rad)
    factor = 600 / (nz + 600) 
    px = int(nx * factor + cx)
    py = int(y * factor + cy)
    return (px, py)

def start_voice_mode():
    # Resolution for Desktop Scaling
    W, H = 1280, 720 
    shapes = []
    current_shape = None
    selected_index = -1
    pulse = 0 
    last_command = ""
    assistant_message = ""
    assistant_timer = 0
    command_timer = 0
    THICKNESS_SELECTED = 8
    THICKNESS_NORMAL = 2

    # --- DESKTOP MAXIMIZED UI SETUP ---
    window_name = "AirCanvas Voice Studio"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=audio_callback):
        
        while True:
            pulse += 1
            for shape in shapes:

                if shape.is_animating:

                    shape.draw_progress += 5

                    if shape.draw_progress >= 100:
                        shape.draw_progress = 100
                        shape.is_animating = False

            for shape in shapes:

                if shape.is_rotating:
                    shape.angle += 0.010

            while not audio_queue.empty():
                data = audio_queue.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    command = result['text'].lower()
                    if command:
                        last_command = command.upper()
                        command_timer = 60
                    
                    if command:
                        if command in ["circle", "square", "triangle", "diamond", "pentagon", "star"]:
                            new_shape = liveShape(W, H)
                            new_shape.type = command
                            shapes.append(new_shape)
                            selected_index = len(shapes) - 1
                            current_shape = shapes[selected_index]
                            assistant_message = f"{command.title()} Created"
                            assistant_timer = 60
                        elif "three d" in command and current_shape:
                            current_shape.is_3d = True
                            assistant_message = "3D Mode Enabled"
                            assistant_timer = 60
                        elif "two d" in command and current_shape:
                            current_shape.is_3d = False
                            assistant_message = "2D Mode Enabled"
                            assistant_timer = 60
                        elif "rotate" in command and current_shape:
                            current_shape.is_rotating = not current_shape.is_rotating
                            assistant_message = (
                                "Rotation Enabled"
                                if current_shape.is_rotating
                                else "Rotation Disabled"
                            )

                            assistant_timer = 60
                        elif "bigger" in command and current_shape:
                            current_shape.size = min(current_shape.size + 40, 400)
                        elif "smaller" in command and current_shape:
                            current_shape.size = max(current_shape.size - 40, 30)
                        elif "select circle" in command:
                            circle_indices = [i for i, s in enumerate(shapes) if s.type == "circle"]
                            if circle_indices:
                                if selected_index in circle_indices:
                                    pos = circle_indices.index(selected_index)
                                    pos = (pos + 1) % len(circle_indices)
                                    selected_index = circle_indices[pos]
                                else:
                                    selected_index = circle_indices[0]
                                current_shape = shapes[selected_index]

                        elif "select square" in command:
                            square_indices = [i for i, s in enumerate(shapes) if s.type == "square"]
                            if square_indices:
                                if selected_index in square_indices:
                                    pos = square_indices.index(selected_index)
                                    pos = (pos + 1) % len(square_indices)
                                    selected_index = square_indices[pos]
                                else:
                                    selected_index = square_indices[0]
                                current_shape = shapes[selected_index]

                        elif "select triangle" in command:
                            triangle_indices = [i for i, s in enumerate(shapes) if s.type == "triangle"]
                            if triangle_indices:
                                if selected_index in triangle_indices:
                                    pos = triangle_indices.index(selected_index)
                                    pos = (pos + 1) % len(triangle_indices)
                                    selected_index = triangle_indices[pos]
                                else:
                                    selected_index = triangle_indices[0]
                                current_shape = shapes[selected_index]
                        elif "left" in command and current_shape:
                            current_shape.x = max(current_shape.x - current_shape.step, 0)
                        elif "right" in command and current_shape:
                            current_shape.x = min(current_shape.x + current_shape.step, W)
                        elif "up" in command and current_shape:
                            current_shape.y = max(current_shape.y - current_shape.step, 0)
                        elif "down" in command and current_shape:
                            current_shape.y = min(current_shape.y + current_shape.step, H)
                        elif "red" in command and current_shape:
                            current_shape.color = (0,0,255)
                        elif "green" in command and current_shape:
                            current_shape.color = (0,255,0)
                        elif "blue" in command and current_shape:
                            current_shape.color = (255,0,0)
                        elif "next shape" in command and shapes:
                            selected_index = (selected_index + 1) % len(shapes)
                            current_shape = shapes[selected_index]
                        elif "previous shape" in command and shapes:
                            selected_index = (selected_index - 1) % len(shapes)
                            current_shape = shapes[selected_index]
                        elif "delete shape" in command and shapes:
                            shapes.pop(selected_index)
                            if shapes:
                                selected_index = selected_index % len(shapes)
                                current_shape = shapes[selected_index]
                            else:
                                selected_index = -1
                                current_shape = None
                        elif "clear" in command or "reset" in command:
                            shapes.clear()
                            current_shape = None

            # --- RENDER CANVAS ---
            frame = np.zeros((H, W, 3), dtype=np.uint8)
            
            # Subtle grid
            for i in range(0, W, 60): cv2.line(frame, (i, 0), (i, H), (25, 25, 25), 1)
            for i in range(0, H, 60): cv2.line(frame, (0, i), (W, i), (25, 25, 25), 1)
            
            for i, shape in enumerate(shapes):
                thickness = THICKNESS_SELECTED if i == selected_index else THICKNESS_NORMAL
                s = shape.size
                cx, cy = shape.x, shape.y

                if shape.type:
                    if not shape.is_3d:
                        if shape.type == "circle":
                            if shape.is_animating:
                                angle = int(360 * shape.draw_progress / 100)

                                cv2.ellipse(
                                    frame,
                                    (cx, cy),
                                    (s, s),
                                    0,
                                    0,
                                    angle,
                                    shape.color,
                                    thickness,
                                    cv2.LINE_AA
                                )

                            else:
                                cv2.circle(frame, (cx, cy), s, shape.color, thickness)
                                
                        elif shape.type == "square":
                            if shape.is_animating:
                                p = shape.draw_progress
                                x1 = cx - s
                                y1 = cy - s
                                x2 = cx + s
                                y2 = cy + s
                                # Top edge
                                if p > 0:
                                    end_x = int(x1 + (x2 - x1) * min(p, 25) / 25)
                                    cv2.line(
                                        frame,
                                        (x1, y1),
                                        (end_x, y1),
                                        shape.color,
                                        thickness
                                    )
                                # Right edge
                                if p > 25:
                                    end_y = int(y1 + (y2 - y1) * min(p-25, 25) / 25)
                                    cv2.line(
                                        frame,
                                        (x2, y1),
                                        (x2, end_y),
                                        shape.color,
                                        thickness
                                    )
                                # Bottom edge
                                if p > 50:
                                    start_x = int(x2 - (x2 - x1) * min(p-50, 25) / 25)
                                    cv2.line(
                                        frame,
                                        (x2, y2),
                                        (start_x, y2),
                                        shape.color,
                                        thickness
                                    )
                                # Left edge
                                if p > 75:
                                    start_y = int(y2 - (y2 - y1) * min(p-75, 25) / 25)
                                    cv2.line(
                                        frame,
                                        (x1, y2),
                                        (x1, start_y),
                                        shape.color,
                                        thickness
                                    )
                            else:
                                cv2.rectangle(
                                    frame,
                                    (cx-s, cy-s),
                                    (cx+s, cy+s),
                                    shape.color,
                                    thickness
                                )

                        elif shape.type == "triangle":

                            if shape.is_animating:

                                p = shape.draw_progress

                                top = (cx, cy - s)
                                left = (cx - s, cy + s)
                                right = (cx + s, cy + s)

                                # Edge 1: top -> left
                                if p > 0:

                                    progress = min(p, 33) / 33

                                    end_x = int(top[0] + (left[0] - top[0]) * progress)
                                    end_y = int(top[1] + (left[1] - top[1]) * progress)

                                    cv2.line(
                                        frame,
                                        top,
                                        (end_x, end_y),
                                        shape.color,
                                        thickness
                                    )

                                # Edge 2: left -> right
                                if p > 33:

                                    progress = min(p - 33, 33) / 33

                                    end_x = int(left[0] + (right[0] - left[0]) * progress)
                                    end_y = int(left[1] + (right[1] - left[1]) * progress)

                                    cv2.line(
                                        frame,
                                        left,
                                        (end_x, end_y),
                                        shape.color,
                                        thickness
                                    )

                                # Edge 3: right -> top
                                if p > 66:

                                    progress = min(p - 66, 34) / 34

                                    end_x = int(right[0] + (top[0] - right[0]) * progress)
                                    end_y = int(right[1] + (top[1] - right[1]) * progress)

                                    cv2.line(
                                        frame,
                                        right,
                                        (end_x, end_y),
                                        shape.color,
                                        thickness
                                    )

                            else:

                                pts = np.array([
                                    [cx, cy-s],
                                    [cx-s, cy+s],
                                    [cx+s, cy+s]
                                ], np.int32)

                                cv2.polylines(
                                    frame,
                                    [pts],
                                    True,
                                    shape.color,
                                    thickness
                                )
                        elif shape.type == "diamond":

                            pts = [
                                (cx, cy - s),   # top
                                (cx + s, cy),   # right
                                (cx, cy + s),   # bottom
                                (cx - s, cy)    # left
                            ]

                            if shape.is_animating:

                                p = shape.draw_progress

                                edges_to_draw = int((p / 100) * 4)

                                for edge in range(edges_to_draw):

                                    start = pts[edge]
                                    end = pts[(edge + 1) % 4]

                                    cv2.line(
                                        frame,
                                        start,
                                        end,
                                        shape.color,
                                        thickness
                                    )

                            else:

                                cv2.polylines(
                                    frame,
                                    [np.array(pts)],
                                    True,
                                    shape.color,
                                    thickness
                                )
                        
                        elif shape.type == "pentagon":

                            pts = []

                            for k in range(5):

                                angle = np.radians(-90 + k * 72)

                                x = int(cx + s * np.cos(angle))
                                y = int(cy + s * np.sin(angle))

                                pts.append((x, y))

                            if shape.is_animating:

                                p = shape.draw_progress

                                edges_to_draw = int((p / 100) * 5)

                                for edge in range(edges_to_draw):

                                    start = pts[edge]
                                    end = pts[(edge + 1) % 5]

                                    cv2.line(
                                        frame,
                                        start,
                                        end,
                                        shape.color,
                                        thickness
                                    )

                            else:

                                cv2.polylines(
                                    frame,
                                    [np.array(pts)],
                                    True,
                                    shape.color,
                                    thickness
                                )

                        elif shape.type == "star":

                            pts = []

                            for k in range(10):

                                angle = np.radians(-90 + k * 36)

                                r = s if k % 2 == 0 else s * 0.45

                                x = int(cx + r * np.cos(angle))
                                y = int(cy + r * np.sin(angle))

                                pts.append((x, y))

                            if shape.is_animating:

                                p = shape.draw_progress

                                edges_to_draw = int((p / 100) * 10)

                                for edge in range(edges_to_draw):

                                    start = pts[edge]
                                    end = pts[(edge + 1) % 10]

                                    cv2.line(
                                        frame,
                                        start,
                                        end,
                                        shape.color,
                                        thickness
                                    )

                            else:

                                cv2.polylines(
                                    frame,
                                    [np.array(pts)],
                                    True,
                                    shape.color,
                                    thickness
                                )

                    else:
                        if shape.type == "circle":

                            # Outer sphere
                            cv2.circle(
                                frame,
                                (cx, cy),
                                s,
                                shape.color,
                                2,
                                cv2.LINE_AA
                            )

                            # Rotating vertical rings
                            for i in range(0, 180, 45):

                                rad = math.radians(i)

                                w_factor = abs(math.cos(shape.angle + rad))

                                cv2.ellipse(
                                    frame,
                                    (cx, cy),
                                    (max(1, int(s * w_factor)), s),
                                    0,
                                    0,
                                    360,
                                    shape.color,
                                    1,
                                    cv2.LINE_AA
                                )

                            # Moving equator
                            tilt = int(25 * math.sin(shape.angle))

                            cv2.ellipse(
                                frame,
                                (cx, cy),
                                (s, max(3, abs(tilt))),
                                0,
                                0,
                                360,
                                shape.color,
                                2,
                                cv2.LINE_AA
                            )
                        elif shape.type == "square": 
                            nodes = [(-s,-s,-s), (s,-s,-s), (s,s,-s), (-s,s,-s), (-s,-s,s), (s,-s,s), (s,s,s), (-s,s,s)]
                            p = [project_3d(n[0], n[1], n[2], cx, cy, shape.angle) for n in nodes]
                            for i in range(4):
                                cv2.line(frame, p[i], p[(i+1)%4], shape.color, 3) 
                                cv2.line(frame, p[i+4], p[((i+1)%4)+4], shape.color, 1) 
                                cv2.line(frame, p[i], p[i+4], shape.color, 2) 
                        elif shape.type == "triangle": 
                            tip = project_3d(0, -s, 0, cx, cy, shape.angle)
                            base = [project_3d(-s, s, -s, cx, cy, shape.angle), project_3d(s, s, -s, cx, cy, shape.angle),
                                    project_3d(s, s, s, cx, cy, shape.angle), project_3d(-s, s, s, cx, cy, shape.angle)]
                            for i in range(4):
                                cv2.line(frame, base[i], base[(i+1)%4], shape.color, 2)
                                cv2.line(frame, tip, base[i], shape.color, 3)
                        elif shape.type == "diamond":

                            nodes = [
                                (-s, -s//3, -s//2),
                                ( s, -s//3, -s//2),
                                ( s, -s//3,  s//2),
                                (-s, -s//3,  s//2),
                                (-s*1.3, 0, -s*0.7),
                                ( s*1.3, 0, -s*0.7),
                                ( s*1.3, 0,  s*0.7),
                                (-s*1.3, 0,  s*0.7),
                                (0, int(s*1.8), 0)
                            ]

                            p = [
                                project_3d(
                                    n[0], n[1], n[2],
                                    cx, cy,
                                    shape.angle
                                )
                                for n in nodes
                            ]

                            edges = [
                                (0,1),(1,2),(2,3),(3,0),
                                (0,4),(1,5),(2,6),(3,7),
                                (4,5),(5,6),(6,7),(7,4),
                                (4,8),
                                (5,8),
                                (6,8),
                                (7,8)
                            ]

                            for a, b in edges:
                                cv2.line(
                                    frame,
                                    p[a],
                                    p[b],
                                    shape.color,
                                    2
                                )
                        
                        elif shape.type == "pentagon":

                            front = []
                            back = []

                            depth = int(s * 0.6)

                            for k in range(5):

                                angle = np.radians(-90 + k * 72)

                                x = int(s * np.cos(angle))
                                y = int(s * np.sin(angle))

                                front.append(
                                    project_3d(
                                        x, y, depth,
                                        cx, cy,
                                        shape.angle
                                    )
                                )

                                back.append(
                                    project_3d(
                                        x, y, -depth,
                                        cx, cy,
                                        shape.angle
                                    )
                                )

                            # Front face
                            cv2.polylines(
                                frame,
                                [np.array(front)],
                                True,
                                shape.color,
                                2
                            )

                            # Back face
                            cv2.polylines(
                                frame,
                                [np.array(back)],
                                True,
                                shape.color,
                                1
                            )

                            # Connect faces
                            for i in range(5):

                                cv2.line(
                                    frame,
                                    front[i],
                                    back[i],
                                    shape.color,
                                    2
                                )

                        elif shape.type == "star":

                            front = []
                            back = []

                            depth = int(s * 0.5)

                            for k in range(10):

                                angle = np.radians(-90 + k * 36)

                                r = s if k % 2 == 0 else s * 0.45

                                x = int(r * np.cos(angle))
                                y = int(r * np.sin(angle))

                                front.append(
                                    project_3d(
                                        x, y, depth,
                                        cx, cy,
                                        shape.angle
                                    )
                                )

                                back.append(
                                    project_3d(
                                        x, y, -depth,
                                        cx, cy,
                                        shape.angle
                                    )
                                )

                            cv2.polylines(
                                frame,
                                [np.array(front)],
                                True,
                                shape.color,
                                2
                            )

                            cv2.polylines(
                                frame,
                                [np.array(back)],
                                True,
                                shape.color,
                                1
                            )

                            for i in range(10):

                                cv2.line(
                                    frame,
                                    front[i],
                                    back[i],
                                    shape.color,
                                    2
                                )

            # --- GUI OVERLAY ---
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (W, 80), (40, 40, 40), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
            
            mic_color = (0, 255, 0) if (pulse // 15) % 2 == 0 else (0, 100, 0)
            cv2.circle(frame, (40, 40), 12, mic_color, -1)
            frame = draw_text(
                frame,
                "LISTENING",
                (70, 25),
                24,
                (255,255,255),
                "Montserrat-SemiBold.ttf"
            )

            if command_timer > 0:

                frame = draw_text(
                    frame,
                    "LAST COMMAND",
                    (20, 95),
                    16,
                    (150, 180, 220),
                    "Montserrat-Medium.ttf"
                )

                frame = draw_text(
                    frame,
                    f'"{last_command}"',
                    (20, 120),
                    24,
                    (0,255,255),
                    "Orbitron-Bold.ttf"
                )

                command_timer -= 1

            if assistant_timer > 0:

                frame = draw_text(
                    frame,
                    f"{assistant_message}",
                    (20, 170),
                    22,
                    (0,255,120),
                    "Montserrat-SemiBold.ttf"
                )

                assistant_timer -= 1

            if current_shape:
                view_mode = "3D" if current_shape.is_3d else "2D"
                shape_name = str(current_shape.type).upper()
                rotate_status = "ON" if current_shape.is_rotating else "OFF"
            else:
                view_mode = "-"
                shape_name = "NONE"
                rotate_status = "OFF"

            status = f"MODE: {view_mode} | SHAPE: {shape_name} | ROTATE: {rotate_status}"
            frame = draw_text(
                frame,
                status,
                (0, 25),
                28,
                (0,255,255),
                "Orbitron-Bold.ttf",
                center=True
            )            
            cv2.imshow(window_name, frame)

            if cv2.waitKey(1) & 0xFF == ord('b'): break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_voice_mode()