import sys
import os
import subprocess
import warnings
import json
import time
# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, 
                             QVBoxLayout, QTextEdit, QHBoxLayout, 
                             QFrame, QGraphicsDropShadowEffect, QListWidget,
                             QMessageBox, QInputDialog, QProgressDialog)
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve
from PyQt6.QtGui import QFont, QColor

class AnimatedButton(QPushButton):
    def __init__(self, text, accent_color, parent=None):
        super().__init__(text, parent)
        self.accent_color_hex = accent_color
        self.setFixedSize(480, 70) 
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.original_pos = None  

        # Modern Tech Style: Semi-transparent 'Glass' look
        self.default_style = f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-left: 4px solid {accent_color};
                border-radius: 15px;
                font-size: 11pt; font-weight: 600; color: #ffffff;
                text-align: center; letter-spacing: 2px;
            }}
        """
        self.hover_style = f"""
            QPushButton {{
                background-color: {accent_color};
                border: 1px solid {accent_color};
                border-radius: 15px;
                font-size: 11pt; font-weight: 800; color: #000000;
                text-align: center; letter-spacing: 2px;
            }}
        """
        self.setStyleSheet(self.default_style)
        
        # Glow Effect Logic
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(25)
        self.shadow.setColor(QColor(0, 0, 0, 0)) 
        self.shadow.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow)

    def enterEvent(self, event):
        if self.original_pos is None: 
            self.original_pos = self.pos()
            
        self.setStyleSheet(self.hover_style)
        
        glow_color = QColor(self.accent_color_hex)
        glow_color.setAlpha(150)
        self.shadow.setColor(glow_color)
        
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuint)
        self.anim.setEndValue(QPoint(self.original_pos.x(), self.original_pos.y() - 8))
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.default_style)
        self.shadow.setColor(QColor(0, 0, 0, 0))
        
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuint)
        if self.original_pos: 
            self.anim.setEndValue(self.original_pos)
        self.anim.start()
        super().leaveEvent(event)

class GuideWindow(QWidget):
    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.setWindowTitle("System Documentation")
        self.showFullScreen()
        self.setStyleSheet("background-color: #030305;")

        # Main layout for the entire screen
        master_v = QVBoxLayout(self)
        master_v.setContentsMargins(50, 50, 50, 50)
        
        # Expanded Frame to act as a large "Terminal" or "Dashboard"
        hud_frame = QFrame()
        # Removed setFixedWidth to allow it to expand
        hud_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 40px;
            }
        """)
        
        layout = QVBoxLayout(hud_frame)
        layout.setContentsMargins(60, 60, 60, 60)

        title = QLabel("SYSTEM DOCUMENTATION")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            color: #ffffff; 
            font-size: 28pt; 
            font-weight: 900; 
            letter-spacing: 15px; 
            border: none;
            margin-bottom: 20px;
        """)
        layout.addWidget(title)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        # Increased font sizes and line heights for a bigger feel
        self.text_area.setHtml("""
            <div style='color: rgba(255,255,255,0.8); font-size: 14pt; line-height: 180%;'>
                
                <table width='100%' cellpadding='20'>
                    <tr>
                        <td width='50%' valign='top' style='border-right: 1px solid rgba(255,255,255,0.1);'>
                            <p align='center'><b style='color:#6366f1; font-size: 18pt;'>✋ HAND ENGINE GESTURES</b></p>
                            <ul style='list-style-type: square; margin-top: 20px;'>
                                <li><b>✍️ DRAW:</b> Use index finger to sketch 3D primitives.</li>
                                <li><b>🔄 ROTATE:</b> Move hand to orbit the active object.</li>
                                <li><b>↔️ RESIZE:</b> Pinch thumb & index to scale dimensions.</li>
                                <li><b>📏 DEPTH:</b> Expand hand span to adjust Z-axis thickness.</li>
                                <li><b>✊ LOCK/UNLOCK:</b> Use fist gesture to freeze object state.</li>
                            </ul>
                        </td>
                        <td width='50%' valign='top'>
                            <p align='center'><b style='color:#06b6d4; font-size: 18pt;'>🎙️ VOICE ENGINE COMMANDS</b></p>
                            <div style='background: rgba(255,255,255,0.05); padding: 25px; border-radius: 20px; margin-top: 20px;'>
                                <p><b>SHAPES:</b> "Circle", "Square", "Triangle"</p>
                                <p><b>TRANSFORM:</b> "Bigger", "Smaller", "Rotate"</p>
                                <p><b>POSITION:</b> "Up", "Down", "Left", "Right"</p>
                                <p><b>DIMENSION:</b> "Three D", "Two D"</p>
                                <p><b>SYSTEM:</b> "Clear", "Reset", "Red", "Blue"</p>
                            </div>
                        </td>
                    </tr>
                </table>

                <p align='center' style='margin-top: 40px; color: rgba(255,255,255,0.4); font-size: 12pt;'>
                    <i>Selection Logic: The system auto-targets the object closest to your index finger landmark.</i>
                </p>
            </div>
        """)
        self.text_area.setStyleSheet("background: transparent; border: none;")
        # Increased height significantly
        self.text_area.setMinimumHeight(500)
        layout.addWidget(self.text_area)

        # Large Back Button
        dismiss_btn = QPushButton("RETURN TO COMMAND CENTER")
        dismiss_btn.setFixedHeight(80)
        dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dismiss_btn.clicked.connect(self.close)
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background: white; color: black; font-size: 14pt; font-weight: bold; 
                border-radius: 20px; letter-spacing: 3px; margin-top: 20px;
            }
            QPushButton:hover { background: #6366f1; color: white; }
        """)
        layout.addWidget(dismiss_btn)

        # Add the frame to the master layout
        master_v.addWidget(hud_frame)

    def closeEvent(self, event):
        self.parent_menu.show_desktop()
        event.accept()

class LoadingScreen(QWidget):
    def __init__(self, message="Loading..."):
        super().__init__()

        self.setWindowTitle("AirCanvas Loading")
        self.showFullScreen()
        self.setStyleSheet("background-color: #030305;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("AIR CANVAS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 70pt;
            font-weight: 900;
            color: white;
            letter-spacing: -2px;
        """)

        msg = QLabel(message)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("""
            font-size: 18pt;
            color: rgba(255,255,255,0.6);
            margin-top: 20px;
        """)

        loading = QLabel("Initializing system...")
        loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading.setStyleSheet("""
            font-size: 12pt;
            color: rgba(255,255,255,0.3);
            margin-top: 10px;
        """)

        layout.addWidget(title)
        layout.addWidget(msg)
        layout.addWidget(loading)

class MainMenuGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AirCanvas Interface")
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.setStyleSheet("background-color: #030305; font-family: 'Segoe UI', sans-serif;")

        self.master_layout = QVBoxLayout(self)
        self.master_layout.addStretch(1)

        title_label = QLabel("AIR CANVAS")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 80pt; font-weight: 900; color: white; letter-spacing: -2px;")
        
        glow_line = QFrame()
        glow_line.setFixedSize(400, 1)
        glow_line.setStyleSheet("background: rgba(255,255,255,0.1);")
        
        subtitle = QLabel("SMART CLASSROOM ASSISTANT")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 8pt; color: rgba(255,255,255,0.3); font-weight: bold; letter-spacing: 8px; margin-top: 20px; margin-bottom: 50px;")
        
        self.master_layout.addWidget(title_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.master_layout.addWidget(glow_line, 0, Qt.AlignmentFlag.AlignCenter)
        self.master_layout.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignCenter)

        self.btn_container = QVBoxLayout()
        self.btn_container.setSpacing(15)
        self.btn_container.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_hand = AnimatedButton("ACTIVATE HAND ENGINE", "#6366f1")
        self.btn_voice = AnimatedButton("ACTIVATE VOICE ENGINE", "#06b6d4")
        self.btn_guide = AnimatedButton("SYSTEM DOCUMENTATION", "#f43f5e")
        self.btn_sessions = AnimatedButton("MANAGE SAVED SESSIONS", "#22c55e")

        self.btn_hand.clicked.connect(self.start_hand_mode)
        self.btn_voice.clicked.connect(self.start_voice_mode)
        self.btn_guide.clicked.connect(self.show_guide)
        self.btn_sessions.clicked.connect(self.show_session_manager)

        for b in [self.btn_hand, self.btn_voice, self.btn_guide, self.btn_sessions]:
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
        script_path = os.path.join(self.base_path, "voice_mode", "voice_mode.py")

        if os.path.exists(script_path):
            loading = self.show_loading("Loading Voice Engine...")
            loading.showFullScreen()

            self.hide()
            QApplication.processEvents()

            subprocess.run([sys.executable, script_path])

            loading.close()
            self.show_desktop()

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

        title = QLabel("HAND ENGINE MODULES")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            color: white;
            font-size: 40pt;
            font-weight: 900;
            letter-spacing: 10px;
        """)
        layout.addWidget(title)

        self.btn_shapes = AnimatedButton("SHAPES MODULE", "#6366f1")
        self.btn_draw = AnimatedButton("FREE DRAW MODULE", "#06b6d4")
        self.btn_solar = AnimatedButton("SOLAR SYSTEM MODULE", "#22c55e")

        self.btn_shapes.clicked.connect(self.start_shapes_mode)
        self.btn_draw.clicked.connect(self.start_draw_mode)
        self.btn_solar.clicked.connect(self.start_solar_mode)

        for b in [self.btn_shapes, self.btn_draw, self.btn_solar]:
            layout.addWidget(b, 0, Qt.AlignmentFlag.AlignCenter)

        back_btn = QPushButton("RETURN TO MAIN MENU")
        back_btn.setFixedSize(300, 60)
        back_btn.clicked.connect(self.close)
        back_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: black;
                font-weight: bold;
                border-radius: 15px;
            }
            QPushButton:hover {
                background: #6366f1;
                color: white;
            }
        """)
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
            "hand_mode",
            filename
        )
        messages = {
            "shapes_mode.py": "Loading Shapes Engine...",
            "draw_mode.py": "Loading Free Draw Canvas...",
            "solar_mode.py": "Loading Solar System Simulation..."
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

class SessionManagerWindow(QWidget):
    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.setWindowTitle("Session Manager")
        self.showFullScreen()
        self.setStyleSheet("background-color: #030305; color: white;")

        self.session_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
        os.makedirs(self.session_folder, exist_ok=True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(120, 60, 120, 60)
        layout.setSpacing(30)

        # Title
        title = QLabel("SAVED SESSIONS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 42pt;
            font-weight: 900;
            letter-spacing: 10px;
            color: white;
        """)
        layout.addWidget(title)

        # Card container
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.04);
                border-radius: 25px;
                border: 1px solid rgba(255,255,255,0.08);
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(25)

        # Session list
        self.session_list = QListWidget()
        self.session_list.itemDoubleClicked.connect(self.load_session)
        self.session_list.setMinimumHeight(350)

        self.session_list.setStyleSheet("""
            QListWidget {
                background: rgba(255,255,255,0.03);
                border: none;
                border-radius: 15px;
                font-size: 13pt;
                padding: 12px;
            }

            QListWidget::item {
                padding: 10px;
                border-radius: 10px;
            }

            QListWidget::item:hover {
                background: rgba(255,255,255,0.08);
            }

            QListWidget::item:selected {
                background: #6366f1;
                color: white;
            }
        """)

        card_layout.addWidget(self.session_list)

        # Buttons row 1
        row1 = QHBoxLayout()

        self.btn_load = QPushButton("LOAD")
        self.btn_rename = QPushButton("RENAME")
        self.btn_delete = QPushButton("DELETE")

        for btn in [self.btn_load, self.btn_rename, self.btn_delete]:
            btn.setFixedHeight(45)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        row1.addWidget(self.btn_load)
        row1.addWidget(self.btn_rename)
        row1.addWidget(self.btn_delete)

        card_layout.addLayout(row1)

        # Buttons row 2
        row2 = QHBoxLayout()

        self.btn_refresh = QPushButton("REFRESH")
        self.btn_back = QPushButton("BACK")

        # Button cursor
        for btn in [self.btn_refresh, self.btn_back]:
            btn.setFixedHeight(45)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Connect buttons
        self.btn_load.clicked.connect(self.load_session)
        self.btn_rename.clicked.connect(self.rename_session)
        self.btn_delete.clicked.connect(self.delete_session)
        self.btn_refresh.clicked.connect(self.refresh_sessions)
        self.btn_back.clicked.connect(self.close)

        # Button styling
        self.btn_load.setStyleSheet("""
        QPushButton {
            background: #22c55e;
            color: white;
            border-radius: 12px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: #16a34a;
        }
        """)

        self.btn_rename.setStyleSheet("""
        QPushButton {
            background: #6366f1;
            color: white;
            border-radius: 12px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: #4f46e5;
        }
        """)

        self.btn_delete.setStyleSheet("""
        QPushButton {
            background: #ef4444;
            color: white;
            border-radius: 12px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: #dc2626;
        }
        """)

        self.btn_refresh.setStyleSheet("""
        QPushButton {
            background: rgba(255,255,255,0.1);
            color: white;
            border-radius: 12px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: rgba(255,255,255,0.2);
        }
        """)

        self.btn_back.setStyleSheet("""
        QPushButton {
            background: white;
            color: black;
            border-radius: 12px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: #6366f1;
            color: white;
        }
        """)

        row2.addWidget(self.btn_refresh)
        row2.addWidget(self.btn_back)

        card_layout.addLayout(row2)

        layout.addWidget(card)

        self.refresh_sessions()

    def refresh_sessions(self):
        self.session_list.clear()

        files = [f for f in os.listdir(self.session_folder) if f.endswith(".json")]
        files.sort()

        for f in files:
            filepath = os.path.join(self.session_folder, f)

            try:
                with open(filepath, "r") as file:
                    data = json.load(file)
                    mode = data.get("mode", "unknown")
            except:
                mode = "unknown"

            mode_label = mode.upper()

            display_text = f"{f}   [{mode_label}]"

            self.session_list.addItem(display_text)

    def delete_session(self):
        selected_item = self.session_list.currentItem()

        if not selected_item:
            return

        filename = selected_item.text().split("   ")[0]
        filepath = os.path.join(self.session_folder, filename)

        reply = QMessageBox.question(
            self,
            "Delete Session",
            f"Are you sure you want to delete:\n{filename}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if os.path.exists(filepath):
                os.remove(filepath)

        self.refresh_sessions()

    def rename_session(self):
        selected_item = self.session_list.currentItem()

        if not selected_item:
            return

        old_filename = selected_item.text().split("   ")[0]
        old_path = os.path.join(self.session_folder, old_filename)

        new_name, ok = QInputDialog.getText(self, "Rename Session", "Enter new session name:")

        if ok and new_name:
            new_filename = f"{new_name}.json"
            new_path = os.path.join(self.session_folder, new_filename)

            os.rename(old_path, new_path)

            self.refresh_sessions()

    def load_session(self):
        selected_item = self.session_list.currentItem()

        if not selected_item:
            return

        filename = selected_item.text().split("   ")[0]
        filepath = os.path.join(self.session_folder, filename)

        if not os.path.exists(filepath):
            return

        # read json
        with open(filepath, "r") as f:
            data = json.load(f)

        mode = data.get("mode")

        base_dir = os.path.dirname(os.path.abspath(__file__))

        if mode == "free_draw":
            script = os.path.join(base_dir, "hand_mode", "draw_mode.py")

        elif mode == "shapes":
            script = os.path.join(base_dir, "hand_mode", "shapes_mode.py")

        elif mode == "solar":
            script = os.path.join(base_dir, "hand_mode", "solar_mode.py")

        else:
            print("Unknown session mode")
            return
        
        # Show loading screen
        loading = LoadingScreen("Loading Saved Session...")
        loading.show()
        QApplication.processEvents()

        self.hide()

        subprocess.run([sys.executable, script, "--load", filename])

        loading.close()

        self.parent_menu.show_desktop()

    def closeEvent(self, event):
        self.parent_menu.show_desktop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainMenuGUI()
    window.show_desktop()
    sys.exit(app.exec())