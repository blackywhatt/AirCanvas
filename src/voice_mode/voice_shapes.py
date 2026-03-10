import cv2
import sys
import os
import numpy as np
import json
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import math

# --- Setup Vosk ---
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_PATH, "..", "model")
vosk_model = Model(MODEL_PATH)

list_of_commands = '["circle", "square", "triangle", "select circle", "select square", "select triangle", "red", "green", "blue", "clear", "reset", "delete shape", "bigger", "smaller", "left", "right", "up", "down", "three d", "two d", "rotate", "next shape", "previous shape", "[unk]"]'
rec = KaldiRecognizer(vosk_model, 16000, list_of_commands)
audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    audio_queue.put(np.frombuffer(indata, dtype=np.int16).tobytes())

class liveShape:
    def __init__(self, w, h):
        self.type = None
        self.size = 100
        self.x = w // 2
        self.y = h // 2
        self.color = (255, 0, 0)
        self.color_name = "Blue"
        self.step = 80 
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
    THICKNESS_SELECTED = 6
    THICKNESS_NORMAL = 2

    # --- DESKTOP MAXIMIZED UI SETUP ---
    window_name = "AirCanvas Voice Studio"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=audio_callback):
        
        while True:
            pulse += 1
            if current_shape and current_shape.is_rotating:
                current_shape.angle += 0.008

            while not audio_queue.empty():
                data = audio_queue.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    command = result['text'].lower()
                    
                    if command:
                        if command in ["circle", "square", "triangle"]:
                            new_shape = liveShape(W, H)
                            new_shape.type = command
                            shapes.append(new_shape)
                            selected_index = len(shapes) - 1
                            current_shape = shapes[selected_index]
                        elif "three d" in command and current_shape:
                            current_shape.is_3d = True
                        elif "two d" in command and current_shape:
                            current_shape.is_3d = False
                        elif "rotate" in command and current_shape:
                            current_shape.is_rotating = not current_shape.is_rotating
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
                            cv2.circle(frame, (cx, cy), s, shape.color, thickness)
                        elif shape.type == "square":
                            cv2.rectangle(frame, (cx-s, cy-s), (cx+s, cy+s), shape.color, thickness)
                        elif shape.type == "triangle":
                            pts = np.array([[cx, cy-s], [cx-s, cy+s], [cx+s, cy+s]], np.int32)
                            cv2.polylines(frame, [pts], True, shape.color, thickness)
                    else:
                        if shape.type == "circle":
                            # Draw vertical 'longitude' loops
                            for i in range(0, 180, 30):
                                rad = math.radians(i)
                                # The width of the ellipse changes based on rotation + loop angle
                                w_factor = abs(math.cos(shape.angle + rad))
                                cv2.ellipse(frame, (cx, cy), (int(s * w_factor), s), 0, 0, 360, shape.color, 2, cv2.LINE_AA)
                            
                            # Draw horizontal 'latitude' loops
                            for i in range(-s, s, s//3):
                                if i == 0: continue # Skip the middle one if you want
                                # Calculate the width of the sphere at this height
                                h_dist = abs(i)
                                lat_w = int(math.sqrt(max(0, s**2 - h_dist**2)))
                                # Perspective tilt for the horizontal loops
                                lat_h = int(lat_w * 0.2 * math.sin(shape.angle))
                                cv2.ellipse(frame, (cx, cy + i), (lat_w, abs(lat_h)), 0, 0, 360, shape.color, 1, cv2.LINE_AA)
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

            # --- GUI OVERLAY ---
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (W, 80), (40, 40, 40), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
            
            mic_color = (0, 255, 0) if (pulse // 15) % 2 == 0 else (0, 100, 0)
            cv2.circle(frame, (40, 40), 12, mic_color, -1)
            cv2.putText(frame, "LISTENING", (70, 52), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)

            if current_shape:
                view_mode = "3D" if current_shape.is_3d else "2D"
                shape_name = str(current_shape.type).upper()
                rotate_status = "ON" if current_shape.is_rotating else "OFF"
            else:
                view_mode = "-"
                shape_name = "NONE"
                rotate_status = "OFF"

            status = f"MODE: {view_mode} | SHAPE: {shape_name} | ROTATE: {rotate_status}"
            cv2.putText(frame, status, (W//2 - 250, 52), cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 255, 255), 1)
            
            cv2.imshow(window_name, frame)

            if cv2.waitKey(1) & 0xFF == ord('b'): break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_voice_mode()