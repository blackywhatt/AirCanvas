import sys
import os
import cv2
import numpy as np
import json
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from datetime import datetime

# ==============================
# VOICE SETUP
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "model")

vosk_model = Model(MODEL_PATH)

voice_commands = """
[
"rotate left","rotate right","tilt up","tilt down",
"zoom in","zoom out",
"faster","slower",
"reset system",
"select mercury","select venus","select earth","select mars",
"select jupiter","select saturn","select uranus","select neptune",
"[unk]"
]
"""

rec = KaldiRecognizer(vosk_model, 16000, voice_commands)

audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    audio_queue.put(bytes(indata))

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

planet_lookup = {
    "mercury":1,
    "venus":2,
    "earth":3,
    "mars":4,
    "jupiter":5,
    "saturn":6,
    "uranus":7,
    "neptune":8
}

solar_scale = 1.0
target_scale = 1.0

ax, ay = 0.0, 0.0

simulation_speed = 1.0
selected_index = 0

# ==============================
# 3D Projection
# ==============================
def project_3d(x,y,z,w,h,ax,ay):

    cx, cy = x-w//2, y-h//2

    rx = cx*np.cos(ay)+z*np.sin(ay)
    rz = -cx*np.sin(ay)+z*np.cos(ay)

    ry = cy*np.cos(ax)-rz*np.sin(ax)
    rz = cy*np.sin(ax)+rz*np.cos(ax)

    focal = 500
    factor = focal/(rz+focal+300)

    return (int(rx*factor)+w//2,int(ry*factor)+h//2)

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

    width = 200
    height = 20 + len(lines) * 22

    panel_x = px + 20
    panel_y = py - height // 2

    h, w, _ = frame.shape

    if panel_x + width > w:
        panel_x = px - width - 20

    if panel_y < 0:
        panel_y = 10

    if panel_y + height > h:
        panel_y = h - height - 10

    overlay = frame.copy()

    cv2.rectangle(
        overlay,
        (panel_x, panel_y),
        (panel_x + width, panel_y + height),
        (30, 30, 30),
        -1
    )

    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    y_offset = panel_y + 25

    for i, line in enumerate(lines):

        font_scale = 0.6 if i == 0 else 0.5
        thickness = 2 if i == 0 else 1

        cv2.putText(
            frame,
            line,
            (panel_x + 10, y_offset),
            cv2.FONT_HERSHEY_DUPLEX,
            font_scale,
            (255,255,255),
            thickness,
            cv2.LINE_AA
        )

        y_offset += 22

# ==============================
# Camera
# ==============================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

window_name = "Voice Solar System"
cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

# ==============================
# AUDIO STREAM
# ==============================
with sd.RawInputStream(
    samplerate=16000,
    blocksize=8000,
    dtype="int16",
    channels=1,
    callback=audio_callback):

    while cap.isOpened():

        ret,frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame,1)
        frame = cv2.resize(frame,(1280,720))
        h,w,_ = frame.shape

        # ==============================
        # VOICE COMMAND PROCESSING
        # ==============================
        while not audio_queue.empty():

            data = audio_queue.get()

            if rec.AcceptWaveform(data):

                result = json.loads(rec.Result())
                command = result["text"]

                if command:

                    print("Voice:",command)

                    if "rotate left" in command:
                        ay -= 0.15

                    elif "rotate right" in command:
                        ay += 0.15

                    elif "tilt up" in command:
                        ax -= 0.15

                    elif "tilt down" in command:
                        ax += 0.15

                    elif "zoom in" in command:
                        target_scale = min(target_scale+0.2,3)

                    elif "zoom out" in command:
                        target_scale = max(target_scale-0.2,0.5)

                    elif "faster" in command:
                        simulation_speed = min(simulation_speed+0.2,5)

                    elif "slower" in command:
                        simulation_speed = max(simulation_speed-0.2,0.2)

                    elif "reset system" in command:
                        ax, ay = 0,0
                        solar_scale = 1

                    else:
                        for p in planet_lookup:
                            if p in command:
                                selected_index = planet_lookup[p]

        # ==============================
        # Orbit Animation
        # ==============================
        for p in planets:

            p["angle"] += p["speed"]*simulation_speed

            if "moon" in p:
                p["moon"]["angle"] += p["moon"]["speed"]*simulation_speed

        # ==============================
        # Smooth Zoom
        # ==============================
        solar_scale += (target_scale-solar_scale)*0.12

        # ==============================
        # Draw Orbits
        # ==============================
        for i,p in enumerate(planets):

            if p["orbit"]>0:

                orbit = p["orbit"]*solar_scale
                orbit_pts=[]

                for deg in range(0,360,5):

                    rad=np.radians(deg)

                    x=np.cos(rad)*orbit
                    y=np.sin(rad)*orbit

                    px,py=project_3d(x+w//2,y+h//2,0,w,h,ax,ay)

                    orbit_pts.append((px,py))

                color=(0,255,255) if i==selected_index else (80,80,80)
                thickness=2 if i==selected_index else 1

                cv2.polylines(frame,[np.array(orbit_pts)],True,color,thickness)

        # ==============================
        # Draw Planets
        # ==============================
        for i,p in enumerate(planets):

            orbit=p["orbit"]*solar_scale

            if orbit==0:
                x,y=0,0
            else:
                x=np.cos(p["angle"])*orbit
                y=np.sin(p["angle"])*orbit

            px,py=project_3d(x+w//2,y+h//2,0,w,h,ax,ay)

            color=(255,255,255) if i==selected_index else p["color"]

            cv2.circle(frame,(px,py),p["radius"],color,-1)

            if i==selected_index:
                cv2.putText(frame,p["name"],(px-40,py-40),
                            cv2.FONT_HERSHEY_DUPLEX,0.7,(255,255,255),2)
                draw_info_panel(frame, p, px, py)
                
        # ==============================
        # UI
        # ==============================
        cv2.putText(frame,"VOICE SOLAR SYSTEM",(40,50),
                    cv2.FONT_HERSHEY_DUPLEX,1,(255,255,255),2)

        cv2.putText(frame,f"SELECTED: {planets[selected_index]['name']}",(40,90),
                    cv2.FONT_HERSHEY_DUPLEX,0.7,(200,200,200),1)

        cv2.putText(frame,f"TIME SCALE: {simulation_speed:.1f}x",(40,120),
                    cv2.FONT_HERSHEY_DUPLEX,0.6,(0,255,255),1)

        cv2.putText(frame,
        "Voice: rotate left/right | tilt up/down | zoom in/out | faster/slower | select planet",
        (40,h-20),cv2.FONT_HERSHEY_SIMPLEX,0.5,(180,180,180),1)

        cv2.imshow(window_name,frame)

        if cv2.waitKey(1)&0xFF==ord("b"):
            break

cap.release()
cv2.destroyAllWindows()