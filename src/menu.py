import sys
import os
import subprocess
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QFrame,
                             QProgressDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QPixmap, QPainter, QColor
from ui_components import AnimatedButton, create_back_button, LoadingScreen
from extra_windows import GuideWindow, SessionManagerWindow

class MainMenuGUI(QWidget):
    def resizeEvent(self, event):
        pixmap = QPixmap(os.path.join(
            self.base_path,
            "..",
            "assets",
            "background.jpg"
        ))

        scaled = pixmap.scaled(
            self.width(),
            self.height(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )

        dark_pixmap = QPixmap(scaled.size())
        dark_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(dark_pixmap)
        painter.drawPixmap(0, 0, scaled)
        painter.fillRect(dark_pixmap.rect(), QColor(0, 0, 0, 120))
        painter.end()

        self.bg_label.setPixmap(dark_pixmap)
        self.bg_label.setGeometry(0, 0, self.width(), self.height())
        self.bg_label.lower()

        super().resizeEvent(event)

    def __init__(self):
        super().__init__()
        self.setAutoFillBackground(True)
        self.setWindowTitle("AirCanvas Interface")
        self.setStyleSheet("""
            background-color: #0a0a0f;
            font-family: 'Montserrat';
        """)

        self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.setStyleSheet("""
            QWidget {
                font-family: 'Montserrat';
            }
        """)

        self.bg_label = QLabel(self)
        self.bg_label.lower()

        # self.overlay = QWidget(self)
        # self.overlay.setGeometry(0, 0, 1920, 1080)
        # self.overlay.setStyleSheet("""
        #     background-color: rgba(0, 0, 0, 120);
        # """)
        # self.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        # self.bg_label.lower()
        # self.overlay.raise_()

        FONT_DIR = os.path.join(self.base_path, "fonts")
        QFontDatabase.addApplicationFont(os.path.join(FONT_DIR, "Orbitron-Bold.ttf"))
        QFontDatabase.addApplicationFont(os.path.join(FONT_DIR, "Montserrat-Medium.ttf"))
        QFontDatabase.addApplicationFont(os.path.join(FONT_DIR, "Montserrat-SemiBold.ttf"))

        self.master_layout = QVBoxLayout(self)
        self.master_layout.addStretch(1)
        
        title_label = QLabel("AIR CANVAS")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            background: transparent;
            font-family: 'Orbitron';
            font-size: 80pt;
            font-weight: 900;
            color: white;
            letter-spacing: -1px;
        """)
        
        glow_line = QFrame()
        glow_line.setFixedSize(400, 1)
        glow_line.setStyleSheet("background: rgba(255,255,255,0.1);")
        
        subtitle = QLabel("SMART CLASSROOM ASSISTANT")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            background: transparent;
            font-family: 'Montserrat';
            font-size: 10pt;
            color: rgba(255,255,255,0.3);
            font-weight: bold;
            letter-spacing: 8px;
            margin-top: 20px;
            margin-bottom: 50px;
        """)
        
        self.master_layout.addWidget(title_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.master_layout.addWidget(glow_line, 0, Qt.AlignmentFlag.AlignCenter)
        self.master_layout.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignCenter)

        self.btn_container = QVBoxLayout()
        self.btn_container.setSpacing(15)
        self.btn_container.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_hand = AnimatedButton("HAND TEACHING MODE", "#6366f1")
        self.btn_voice = AnimatedButton("VOICE TEACHING MODE", "#06b6d4")
        self.btn_accessibility = AnimatedButton("SMART ASSIST MODE", "#a855f7")
        self.btn_lessons = AnimatedButton("LEARNING GAMES", "#fbbf24")
        self.btn_guide = AnimatedButton("HELP / GUIDE", "#f43f5e")
        self.btn_sessions = AnimatedButton("MY PROGRESS", "#22c55e")

        self.btn_hand.clicked.connect(self.start_hand_mode)
        self.btn_voice.clicked.connect(self.start_voice_mode)
        self.btn_accessibility.clicked.connect(self.start_accessibility_mode)
        self.btn_lessons.clicked.connect(self.open_lessons_menu)
        self.btn_guide.clicked.connect(self.show_guide)
        self.btn_sessions.clicked.connect(self.show_session_manager)

        for b in [self.btn_hand, self.btn_voice, self.btn_accessibility, self.btn_lessons, self.btn_guide, self.btn_sessions]:
            self.btn_container.addWidget(b, 0, Qt.AlignmentFlag.AlignCenter)

        self.master_layout.addLayout(self.btn_container)
        self.master_layout.addStretch(1)

        self.exit_btn = QPushButton("TERMINATE SESSION")
        self.exit_btn.setFixedSize(200, 40)
        self.exit_btn.clicked.connect(self.close)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: rgba(255,255,255,0.1); font-weight: bold;
                border: none; font-size: 7pt; letter-spacing: 2px;
            }
            QPushButton:hover { color: #f43f5e; }
        """)
        self.master_layout.addWidget(self.exit_btn, 0, Qt.AlignmentFlag.AlignCenter)
        self.master_layout.addSpacing(30)

        self.bg_label.lower()
        # self.overlay.lower()

    def show_desktop(self):
        self.showFullScreen()

    def show_loading(self, message="Loading Module..."):
        loading = QProgressDialog(message, None, 0, 0, self)
        loading.setWindowTitle("AirCanvas")
        loading.setWindowModality(Qt.WindowModality.ApplicationModal)
        loading.setCancelButton(None)
        loading.setMinimumDuration(0)
        loading.setStyleSheet("""
            QProgressDialog {
                background-color: #030305;
                color: white;
                font-size: 14pt;
            }
        """)
        loading.show()
        QApplication.processEvents()
        return loading

    def start_hand_mode(self):
        self.hide()
        self.hand_module_window = HandModuleWindow(self)
        self.hand_module_window.show()

    def start_voice_mode(self):
        self.hide()
        self.voice_module_window = VoiceModuleWindow(self)
        self.voice_module_window.show()

    def start_accessibility_mode(self):
        script_path = os.path.join(self.base_path, "accessibility_mode.py")

        if os.path.exists(script_path):
            loading = LoadingScreen("Loading Accessibility Mode...")
            loading.show()
            QApplication.processEvents()
            self.hide()
            subprocess.run([sys.executable, script_path])
            loading.close()
            self.show_desktop()

    def open_lessons_menu(self):
        self.hide()
        self.lesson_menu = LessonMenuWindow(self)
        self.lesson_menu.show()

    def show_guide(self):
        self.hide()
        self.guide_window = GuideWindow(self)
        self.guide_window.show()

    def show_session_manager(self):
        self.hide()
        self.session_window = SessionManagerWindow(self)
        self.session_window.show()

class HandModuleWindow(QWidget):
    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.setWindowTitle("Hand Engine Modules")
        self.showFullScreen()
        self.setStyleSheet("background-color: #030305;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("HAND TEACHING TOOLS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(""" font-family: 'Orbitron'; color: white; font-size: 40pt; font-weight: 900; letter-spacing: 10px; """)
        layout.addWidget(title)
        layout.addSpacing(20)

        self.btn_shapes = AnimatedButton("SHAPES ADVENTURE", "#6366f1")
        self.btn_draw = AnimatedButton("CREATIVE DRAWING BOARD", "#06b6d4")
        self.btn_solar = AnimatedButton("SPACE EXPLORATION", "#22c55e")

        self.btn_shapes.clicked.connect(self.start_shapes_mode)
        self.btn_draw.clicked.connect(self.start_draw_mode)
        self.btn_solar.clicked.connect(self.start_solar_mode)

        for b in [self.btn_shapes, self.btn_draw, self.btn_solar]:
            layout.addWidget(b, 0, Qt.AlignmentFlag.AlignCenter)

        back_btn = create_back_button("Back to Main Menu")
        back_btn.clicked.connect(self.close)
        layout.addWidget(back_btn, 0, Qt.AlignmentFlag.AlignCenter)

    def start_shapes_mode(self):
        self.launch_module("shapes_mode.py")

    def start_draw_mode(self):
        self.launch_module("draw_mode.py")

    def start_solar_mode(self):
        self.launch_module("solar_mode.py")

    def launch_module(self, filename):
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            filename
        )
        messages = {
            "shapes_mode.py": "Entering Shape Adventure...",
            "draw_mode.py": "Opening Creative Drawing Studio...",
            "solar_mode.py": "Launching Space Adventure..."
        }
        message = messages.get(filename, "Loading Module...")
        if os.path.exists(script_path):
            loading = LoadingScreen(message)
            loading.show()
            QApplication.processEvents()
            self.hide()
            subprocess.run([sys.executable, script_path])
            loading.close()
            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().geometry()
            self.setGeometry(screen)
            self.show()
            self.showFullScreen()
            self.activateWindow()
            self.raise_()

    def closeEvent(self, event):
        self.parent_menu.show_desktop()
        event.accept()

class VoiceModuleWindow(QWidget):
    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.setWindowTitle("Voice Engine Modules")
        self.showFullScreen()
        self.setStyleSheet("background-color: #030305;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("VOICE TEACHING TOOLS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-family: 'Orbitron';
            color: white;
            font-size: 40pt;
            font-weight: 900;
            letter-spacing: 10px;
        """)
        layout.addWidget(title)
        layout.addSpacing(20)

        # Buttons
        self.btn_draw = AnimatedButton("VOICE DRAWING BOARD", "#06b6d4")
        self.btn_shapes = AnimatedButton("VOICE SHAPE ADVENTURE", "#6366f1")
        self.btn_solar = AnimatedButton("VOICE SPACE EXPLORER", "#22c55e")

        self.btn_draw.clicked.connect(self.start_voice_draw)
        self.btn_shapes.clicked.connect(self.start_voice_shapes)
        self.btn_solar.clicked.connect(self.start_voice_solar)

        for b in [self.btn_draw, self.btn_shapes, self.btn_solar]:
            layout.addWidget(b, 0, Qt.AlignmentFlag.AlignCenter)

        # Back button
        back_btn = create_back_button("Back to Main Menu")
        back_btn.clicked.connect(self.close)
        layout.addWidget(back_btn, 0, Qt.AlignmentFlag.AlignCenter)

    def start_voice_draw(self):
        self.launch_module("voice_draw.py")

    def start_voice_shapes(self):
        self.launch_module("voice_shapes.py")

    def start_voice_solar(self):
        self.launch_module("voice_solar.py")

    def launch_module(self, filename):
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            filename
        )

        messages = {
            "voice_draw.py": "Opening Voice Art Studio...",
            "voice_shapes.py": "Starting Voice Shape Adventure...",
            "voice_solar.py": "Launching Voice Space Explorer..."
        }

        message = messages.get(filename, "Loading Voice Module...")

        if os.path.exists(script_path):
            loading = LoadingScreen(message)
            loading.show()
            QApplication.processEvents()

            self.hide()
            subprocess.run([sys.executable, script_path])

            loading.close()

            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().geometry()
            self.setGeometry(screen)

            self.show()
            self.showFullScreen()
            self.activateWindow()
            self.raise_()

    def closeEvent(self, event):
        self.parent_menu.show_desktop()
        event.accept()

class LessonMenuWindow(QWidget):
    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.setWindowTitle("Lessons")
        self.showFullScreen()
        self.setStyleSheet("background-color: #030305;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("GAMES / ACTIVITY")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-family: "Orbitron";                
            color: white;
            font-size: 40pt;
            font-weight: 900;
            letter-spacing: 10px;
        """)
        layout.addWidget(title)
        layout.addSpacing(20)

        self.btn_geo = AnimatedButton("SHAPE LEARNING", "#6366f1")
        self.btn_math = AnimatedButton("NUMBER LEARNING", "#06b6d4")
        self.btn_sci = AnimatedButton("PLANET LEARNING", "#22c55e")
        self.btn_creative = AnimatedButton("CREATIVE LEARNING", "#f59e0b")

        self.btn_geo.clicked.connect(self.open_geometry)
        self.btn_math.clicked.connect(self.open_math)
        self.btn_sci.clicked.connect(self.open_science)
        self.btn_creative.clicked.connect(self.open_creative)

        for b in [self.btn_geo, self.btn_math, self.btn_sci, self.btn_creative]:
            layout.addWidget(b, 0, Qt.AlignmentFlag.AlignCenter)

        back_btn = create_back_button("Back to Main Menu")
        back_btn.clicked.connect(self.close)
        layout.addWidget(back_btn, 0, Qt.AlignmentFlag.AlignCenter)

    def open_geometry(self):
        self.hide()
        self.geo_menu = GeometryLessonWindow(self)
        self.geo_menu.showFullScreen()

    def open_math(self):
        self.hide()
        self.math_menu = MathLessonWindow(self)
        self.math_menu.showFullScreen()

    def open_science(self):
        self.hide()
        self.sci_menu = ScienceLessonWindow(self)
        self.sci_menu.showFullScreen()

    def open_creative(self):
        self.hide()
        self.creative_menu = CreativeLessonWindow(self)
        self.creative_menu.showFullScreen()

    def closeEvent(self, event):
        self.parent_menu.show_desktop()
        event.accept()

class GeometryLessonWindow(QWidget):
    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.setWindowTitle("Geometry Lessons")
        self.showFullScreen()
        self.setStyleSheet("background-color: #030305;")

        self.base_path = os.path.dirname(os.path.abspath(__file__))

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("SHAPE LEARNING")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-family: "Orbitron";
            color: white;
            font-size: 40pt;
            font-weight: 900;
            letter-spacing: 10px;
        """)
        layout.addWidget(title)
        layout.addSpacing(20)

        lessons = [
            ("Find the Shape", "lesson_shape_recognition.py"),
            ("Draw Shapes", "lesson_shape_drawing.py"),
            ("Match Shapes", "lesson_shape_matching.py"),
            ("Count Shapes", "lesson_shape_counting.py"),
            ("Compare Shapes", "lesson_shape_comparison.py"),
        ]

        for name, file in lessons:
            btn = AnimatedButton(name.upper(), "#6366f1")
            btn.clicked.connect(lambda _, f=file: self.run_script(f))
            layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)

        back_btn = create_back_button("Back")
        back_btn.clicked.connect(self.go_back)  
        layout.addWidget(back_btn, 0, Qt.AlignmentFlag.AlignCenter)

    def run_script(self, filename):
        script_path = os.path.join(self.base_path, filename)

        if os.path.exists(script_path):
            loading = LoadingScreen("Loading Lesson...")
            loading.show()
            QApplication.processEvents()

            self.hide()
            subprocess.run([sys.executable, script_path])

            loading.close()

            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().geometry()
            self.setGeometry(screen)

            self.show()
            self.showFullScreen()
            self.activateWindow()
            self.raise_()

    def go_back(self):
        from PyQt6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen().geometry()

        self.parent_menu.setGeometry(screen)
        self.parent_menu.show()
        self.parent_menu.showFullScreen()
        self.parent_menu.activateWindow()
        self.parent_menu.raise_()
        self.hide()

    def closeEvent(self, event):
        event.accept()

class MathLessonWindow(QWidget):
    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.setWindowTitle("Mathematics Lessons")
        self.showFullScreen()
        self.setStyleSheet("background-color: #030305;")

        self.base_path = os.path.dirname(os.path.abspath(__file__))

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("MATHEMATICS LESSONS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-family: "Orbitron";
            color: white;
            font-size: 40pt;
            font-weight: 900;
            letter-spacing: 10px;
        """)
        layout.addWidget(title)
        layout.addSpacing(20)

        lessons = [
            ("Find the Number", "lesson_mathematics_numrecognition.py"),
            ("Count Objects", "lesson_mathematics_countingobjects.py"),
            ("Fill Missing Number", "lesson_mathematics_missingnum.py"),
            ("Add Numbers", "lesson_mathematics_basicadd.py"),
            ("Arrange Numbers", "lesson_mathematics_numordering.py"),
        ]

        for name, file in lessons:
            btn = AnimatedButton(name.upper(), "#06b6d4")
            btn.clicked.connect(lambda _, f=file: self.run_script(f))
            layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)

        back_btn = create_back_button("Back")
        back_btn.clicked.connect(self.go_back)
        layout.addWidget(back_btn, 0, Qt.AlignmentFlag.AlignCenter)

    def run_script(self, filename):
        script_path = os.path.join(self.base_path, filename)

        if os.path.exists(script_path):
            loading = LoadingScreen("Loading Lesson...")
            loading.show()
            QApplication.processEvents()

            self.hide()
            subprocess.run([sys.executable, script_path])

            loading.close()

            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().geometry()
            self.setGeometry(screen)

            self.show()
            self.showFullScreen()
            self.activateWindow()
            self.raise_()

    def go_back(self):
        from PyQt6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen().geometry()

        self.parent_menu.setGeometry(screen)
        self.parent_menu.show()
        self.parent_menu.showFullScreen()
        self.parent_menu.activateWindow()
        self.parent_menu.raise_()

        self.hide()

    def closeEvent(self, event):
        event.accept()

class ScienceLessonWindow(QWidget):
    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.setWindowTitle("Science Lessons")
        self.showFullScreen()
        self.setStyleSheet("background-color: #030305;")

        self.base_path = os.path.dirname(os.path.abspath(__file__))

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("SCIENCE LESSONS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-family: "Orbitron";
            color: white;
            font-size: 40pt;
            font-weight: 900;
            letter-spacing: 10px;
        """)
        layout.addWidget(title)
        layout.addSpacing(20)

        lessons = [
            ("Find the Planet", "lesson_planet_identification.py"),
            ("Compare Planets", "lesson_planet_comparison.py"),
            ("Planet Order Game", "lesson_planet_order.py"),
            ("Learn About Planets", "lesson_planet_information.py"),
        ]

        for name, file in lessons:
            btn = AnimatedButton(name.upper(), "#22c55e")
            btn.clicked.connect(lambda _, f=file: self.run_script(f))
            layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)

        back_btn = create_back_button("Back")
        back_btn.clicked.connect(self.go_back)  
        layout.addWidget(back_btn, 0, Qt.AlignmentFlag.AlignCenter)

    def run_script(self, filename):
        script_path = os.path.join(self.base_path, filename)

        if os.path.exists(script_path):
            loading = LoadingScreen("Loading Lesson...")
            loading.show()
            QApplication.processEvents()

            self.hide()
            subprocess.run([sys.executable, script_path])

            loading.close()

            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().geometry()
            self.setGeometry(screen)

            self.show()
            self.showFullScreen()
            self.activateWindow()
            self.raise_()

    def go_back(self):
        from PyQt6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen().geometry()

        self.parent_menu.setGeometry(screen)
        self.parent_menu.show()
        self.parent_menu.showFullScreen()
        self.parent_menu.activateWindow()
        self.parent_menu.raise_()

        self.hide()

    def closeEvent(self, event):
        event.accept()

class CreativeLessonWindow(QWidget):
    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.setWindowTitle("Creative Lessons")
        self.showFullScreen()
        self.setStyleSheet("background-color: #030305;")

        self.base_path = os.path.dirname(os.path.abspath(__file__))

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("CREATIVE LEARNING")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-family: "Orbitron";
            color: white;
            font-size: 40pt;
            font-weight: 900;
            letter-spacing: 10px;
        """)
        layout.addWidget(title)
        layout.addSpacing(20)

        lessons = [
            ("Free Drawing", "lesson_creative_freedrawing.py"),
            ("Learn Colors", "lesson_creative_colourlearning.py"),
            ("Draw Patterns", "lesson_creative_patterndrawing.py"),
        ]

        for name, file in lessons:
            btn = AnimatedButton(name.upper(), "#f59e0b")
            btn.clicked.connect(lambda _, f=file: self.run_script(f))
            layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)

        back_btn = create_back_button("Back")
        back_btn.clicked.connect(self.go_back)
        layout.addWidget(back_btn, 0, Qt.AlignmentFlag.AlignCenter)

    def run_script(self, filename):
        script_path = os.path.join(self.base_path, filename)

        if os.path.exists(script_path):
            loading = LoadingScreen("Loading Lesson...")
            loading.show()
            QApplication.processEvents()

            self.hide()
            subprocess.run([sys.executable, script_path])

            loading.close()

            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().geometry()
            self.setGeometry(screen)

            self.show()
            self.showFullScreen()
            self.activateWindow()
            self.raise_()

    def go_back(self):
        from PyQt6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen().geometry()

        self.parent_menu.setGeometry(screen)
        self.parent_menu.show()
        self.parent_menu.showFullScreen()
        self.parent_menu.activateWindow()
        self.parent_menu.raise_()

        self.hide()

    def closeEvent(self, event):
        event.accept()    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainMenuGUI()
    window.show_desktop()
    sys.exit(app.exec())