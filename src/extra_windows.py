import sys
import os
import subprocess
import warnings
import json
warnings.filterwarnings("ignore", category=DeprecationWarning)
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QTextEdit, QHBoxLayout, QFrame, QListWidget, 
                             QMessageBox, QInputDialog, QListWidgetItem)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor
from ui_components import AnimatedButton, LoadingScreen

class BackgroundWindow(QWidget):

    def __init__(self, background_image="default_bg.png"):
        super().__init__()

        self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.background_image = background_image

        self.bg_label = QLabel(self)
        self.bg_label.lower()

    def resizeEvent(self, event):

        pixmap = QPixmap(os.path.join(
            self.base_path,
            "..",
            "assets",
            self.background_image
        ))

        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )

        x = (scaled.width() - self.width()) // 2
        y = (scaled.height() - self.height()) // 2

        cropped = scaled.copy(
            x,
            y,
            self.width(),
            self.height()
        )

        dark_pixmap = QPixmap(self.size())
        dark_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(dark_pixmap)

        painter.drawPixmap(0, 0, cropped)

        painter.fillRect(
            dark_pixmap.rect(),
            QColor(0, 0, 0, 120)
        )

        painter.end()

        self.bg_label.setPixmap(dark_pixmap)
        self.bg_label.setGeometry(0, 0, self.width(), self.height())
        self.bg_label.lower()

        super().resizeEvent(event)

class GuideWindow(BackgroundWindow):
    def __init__(self, parent_menu):
        super().__init__("canva1.png")
        self.parent_menu = parent_menu

        self.setWindowTitle("System Guide")
        self.showFullScreen()

        self.setStyleSheet("""
            QWidget {
                color: white;
                font-family: 'Montserrat';
            }
            QLabel {
                background: transparent;
            }
            QListWidget {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 22px;
                padding: 10px;
                font-size: 12pt;
            }
            QListWidget::item {
                padding: 14px;
                border-radius: 12px;
                margin: 4px;
            }
            QListWidget::item:selected {
                background: rgba(255,255,255,0.08);
                color: white;
            }
            QListWidget::item:hover {
                background: rgba(255,255,255,0.05);
            }
            QTextEdit {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 22px;
                padding: 35px;
                font-size: 14pt;
                line-height: 180%;
                color: rgba(255,255,255,0.85);
            }
        """)

        main = QVBoxLayout(self)
        main.setContentsMargins(45, 60, 45, 35)
        main.setSpacing(20)

        # HEADER
        title = QLabel("SYSTEM GUIDE")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-family: 'Orbitron';
            font-size: 36pt;
            font-weight: 900;
            letter-spacing: 6px;
        """)

        subtitle = QLabel("How to use AirCanvas effectively")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            color: rgba(255,255,255,0.45);
            font-size: 11pt;
            letter-spacing: 3px;
        """)

        main.addWidget(title)
        main.addWidget(subtitle)
        main.addSpacing(15)

        # CENTER PANEL
        center = QHBoxLayout()
        center.setSpacing(20)

        self.menu_list = QListWidget()
        self.menu_list.setFixedWidth(260)

        topics = [
            "Overview",
            "Hand Mode",
            "Voice Mode",
            "Learning Games",
            "My Progress",
            "Troubleshooting"
        ]

        self.menu_list.addItems(topics)

        self.content = QTextEdit()
        self.content.setReadOnly(True)

        center.addWidget(self.menu_list)
        center.addWidget(self.content, 1)

        main.addLayout(center)

        # BUTTON
        back_btn = AnimatedButton("BACK TO MAIN MENU", "#f43f5e")
        back_btn.clicked.connect(self.close)

        main.addWidget(back_btn, 0, Qt.AlignmentFlag.AlignCenter)

        # EVENTS
        self.menu_list.currentRowChanged.connect(self.change_topic)
        self.menu_list.setCurrentRow(0)

    def change_topic(self, index):
        pages = []

        # ================= OVERVIEW =================
        pages.append("""
        <h1 style='font-size:28pt;'>Overview</h1>

        <p style='line-height:180%; margin-top:15px;'>
        AirCanvas is an interactive smart classroom platform that combines
        gesture recognition and voice control to create a modern learning experience.
        </p>

        <p style='margin-top:25px; font-weight:bold;'>Key Objectives</p>

        <ul style='line-height:190%; margin-top:10px;'>
            <li>Increase classroom engagement</li>
            <li>Enable touchless interaction</li>
            <li>Support creative learning activities</li>
            <li>Provide fun educational modules</li>
            <li>Save and continue learning sessions</li>
        </ul>

        <p style='margin-top:25px; color:rgba(255,255,255,0.55);'>
        Recommended for students, teachers and smart classroom demonstrations.
        </p>
        """)

        # ================= HAND MODE =================
        pages.append("""
        <h1 style='font-size:28pt;'>Hand Mode</h1>

        <p style='line-height:180%; margin-top:15px;'>
        Use real-time hand tracking to control objects and draw directly in the air.
        </p>

        <p style='margin-top:20px; font-weight:bold;'>How to Use</p>

        <ol style='line-height:190%; margin-top:10px;'>
            <li>Stand clearly in front of the camera</li>
            <li>Raise one hand into camera view</li>
            <li>Use index finger to draw</li>
            <li>Use pinch gesture to resize or select</li>
            <li>Move hand naturally to reposition objects</li>
        </ol>

        <p style='margin-top:25px; font-weight:bold;'>Tips</p>

        <ul style='line-height:190%;'>
            <li>Use bright lighting</li>
            <li>Keep camera stable</li>
            <li>Avoid crowded background</li>
        </ul>
        """)

        # ================= VOICE MODE =================
        pages.append("""
        <h1 style='font-size:28pt;'>Voice Mode</h1>

        <p style='line-height:180%; margin-top:15px;'>
        Control AirCanvas using spoken commands for faster hands-free interaction.
        </p>

        <p style='margin-top:20px; font-weight:bold;'>Available Commands</p>

        <table width='100%' cellspacing='10' style='margin-top:10px;'>
            <tr>
                <td><b>Shapes</b><br>Circle, Square, Triangle</td>
                <td><b>Colors</b><br>Red, Blue, Green</td>
            </tr>
            <tr>
                <td><b>Actions</b><br>Bigger, Smaller, Rotate</td>
                <td><b>System</b><br>Clear, Delete, Reset</td>
            </tr>
        </table>

        <p style='margin-top:25px; font-weight:bold;'>Tips</p>

        <ul style='line-height:190%;'>
            <li>Speak clearly and naturally</li>
            <li>Reduce surrounding noise</li>
            <li>Pause briefly between commands</li>
        </ul>
        """)

        # ================= LEARNING GAMES =================
        pages.append("""
        <h1 style='font-size:28pt;'>Learning Games</h1>

        <p style='line-height:180%; margin-top:15px;'>
        Interactive educational modules designed to improve understanding through play.
        </p>

        <p style='margin-top:20px; font-weight:bold;'>Available Modules</p>

        <ul style='line-height:190%; margin-top:10px;'>
            <li>Shape Recognition</li>
            <li>Counting Activities</li>
            <li>Basic Mathematics</li>
            <li>Planet Learning</li>
            <li>Creative Drawing Exercises</li>
        </ul>

        <p style='margin-top:25px; color:rgba(255,255,255,0.55);'>
        Suitable for primary school and beginner learners.
        </p>
        """)

        # ================= MY PROGRESS =================
        pages.append("""
        <h1 style='font-size:28pt;'>My Progress</h1>

        <p style='line-height:180%; margin-top:15px;'>
        Manage saved learning sessions and continue work later.
        </p>

        <p style='margin-top:20px; font-weight:bold;'>Functions</p>

        <ul style='line-height:190%; margin-top:10px;'>
            <li>Save current session progress</li>
            <li>Load previous sessions</li>
            <li>Rename saved sessions</li>
            <li>Delete old files</li>
            <li>Track learning continuity</li>
        </ul>

        <p style='margin-top:25px; color:rgba(255,255,255,0.55);'>
        Useful for repeated practice and lesson continuation.
        </p>
        """)

        # ================= TROUBLESHOOTING =================
        pages.append("""
        <h1 style='font-size:28pt;'>Troubleshooting</h1>

        <p style='margin-top:20px; font-weight:bold;'>Camera Not Detected</p>
        <ul style='line-height:180%;'>
            <li>Reconnect webcam</li>
            <li>Close other camera apps</li>
            <li>Restart AirCanvas</li>
        </ul>

        <p style='margin-top:20px; font-weight:bold;'>Voice Not Responding</p>
        <ul style='line-height:180%;'>
            <li>Check microphone device</li>
            <li>Speak clearly</li>
            <li>Reduce background noise</li>
        </ul>

        <p style='margin-top:20px; font-weight:bold;'>Slow Performance</p>
        <ul style='line-height:180%;'>
            <li>Close unused applications</li>
            <li>Use better lighting</li>
            <li>Reduce background processes</li>
        </ul>
        """)

        self.content.setHtml(pages[index])

    def closeEvent(self, event):
        self.parent_menu.show_desktop()
        event.accept()

class SessionManagerWindow(BackgroundWindow):
    def __init__(self, parent_menu):
        super().__init__("canva.png")
        self.parent_menu = parent_menu

        self.setWindowTitle("Session Manager")
        self.showFullScreen()
        self.setStyleSheet("""
            QWidget {
                color: white;
                font-family: 'Montserrat';
            }
        """)

        self.session_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "sessions"
        )
        os.makedirs(self.session_folder, exist_ok=True)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setSpacing(18)

        # TITLE
        title = QLabel("MY PROGRESS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-family: 'Orbitron';
            font-size: 48pt;
            font-weight: 900;
            color: white;
            letter-spacing: 8px;
        """)

        line = QFrame()
        line.setFixedSize(320, 1)
        line.setStyleSheet("background: rgba(255,255,255,0.12);")

        subtitle = QLabel("SAVED LEARNING SESSIONS")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            color: rgba(255,255,255,0.35);
            font-size: 10pt;
            font-weight: bold;
            letter-spacing: 6px;
            margin-bottom: 20px;
        """)

        main_layout.addWidget(title)
        main_layout.addWidget(line, 0, Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle)

        # LIST BOX
        self.session_list = QListWidget()
        self.session_list.setFixedSize(760, 420)
        self.session_list.itemDoubleClicked.connect(self.load_session)

        self.session_list.setStyleSheet("""
            QListWidget {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 20px;
                padding: 14px;
                font-size: 13pt;
            }

            QListWidget::item {
                padding: 12px;
                margin: 4px;
                border-radius: 10px;
            }

            QListWidget::item:hover {
                background: rgba(255,255,255,0.06);
            }

            QListWidget::item:selected {
                background: #22c55e;
                color: white;
            }
        """)

        main_layout.addWidget(self.session_list, 0, Qt.AlignmentFlag.AlignCenter)

        # BUTTONS
        self.btn_load = AnimatedButton("LOAD SESSION", "#22c55e")
        self.btn_rename = AnimatedButton("RENAME SESSION", "#6366f1")
        self.btn_delete = AnimatedButton("DELETE SESSION", "#ef4444")
        self.btn_back = AnimatedButton("BACK TO MAIN MENU", "#f43f5e")

        self.btn_load.clicked.connect(self.load_session)
        self.btn_rename.clicked.connect(self.rename_session)
        self.btn_delete.clicked.connect(self.delete_session)
        self.btn_back.clicked.connect(self.close)

        # Make buttons smaller
        for btn in [
            self.btn_load,
            self.btn_rename,
            self.btn_delete,
            self.btn_back
        ]:
            btn.setFixedSize(320, 65)

        # Row 1
        row1 = QHBoxLayout()
        row1.setSpacing(18)
        row1.setAlignment(Qt.AlignmentFlag.AlignCenter)

        row1.addWidget(self.btn_load)
        row1.addWidget(self.btn_rename)

        # Row 2
        row2 = QHBoxLayout()
        row2.setSpacing(18)
        row2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        row2.addWidget(self.btn_delete)
        row2.addWidget(self.btn_back)

        main_layout.addLayout(row1)
        main_layout.addLayout(row2)

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

            clean_name = f.replace(".json", "")
            parts = clean_name.rsplit("_", 2)

            if len(parts) == 3:
                name = parts[0]
                date = parts[1]
            else:
                name = clean_name
                date = "Unknown"

            name = name.replace("_", " ").upper()

            try:
                y, m, d = date.split("-")

                months = {
                    "01":"JAN","02":"FEB","03":"MAR","04":"APR",
                    "05":"MAY","06":"JUN","07":"JUL","08":"AUG",
                    "09":"SEP","10":"OCT","11":"NOV","12":"DEC"
                }

                date_text = f"{d} {months[m]} {y}"

            except:
                date_text = date

            mode_text = mode.replace("_", " ").upper()

            display = f"{name}   •   {date_text}   •   {mode_text}"

            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, f)

            self.session_list.addItem(item)

    def delete_session(self):
        selected_item = self.session_list.currentItem()

        if not selected_item:
            return

        filename = selected_item.data(Qt.ItemDataRole.UserRole)
        filepath = os.path.join(self.session_folder, filename)

        reply = QMessageBox.question(
            self,
            "Delete Session",
            f"Delete {filename} ?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if os.path.exists(filepath):
                os.remove(filepath)

        self.refresh_sessions()

    def rename_session(self):
        selected_item = self.session_list.currentItem()

        if not selected_item:
            return

        old_filename = selected_item.data(Qt.ItemDataRole.UserRole)
        old_path = os.path.join(self.session_folder, old_filename)

        clean_name = old_filename.replace(".json", "")
        parts = clean_name.rsplit("_", 2)

        if len(parts) == 3:
            suffix = f"_{parts[1]}_{parts[2]}"
        else:
            suffix = ""

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Session",
            "Enter new session name:"
        )

        if ok and new_name:
            new_filename = new_name + suffix + ".json"
            new_path = os.path.join(self.session_folder, new_filename)

            os.rename(old_path, new_path)

        self.refresh_sessions()

    def load_session(self):
        selected_item = self.session_list.currentItem()

        if not selected_item:
            return

        filename = selected_item.data(Qt.ItemDataRole.UserRole)
        filepath = os.path.join(self.session_folder, filename)

        with open(filepath, "r") as f:
            data = json.load(f)

        mode = data.get("mode")
        base_dir = os.path.dirname(os.path.abspath(__file__))

        if mode == "free_draw":
            script = os.path.join(base_dir, "draw_mode.py")
        elif mode == "shapes":
            script = os.path.join(base_dir, "shapes_mode.py")
        elif mode == "solar":
            script = os.path.join(base_dir, "solar_mode.py")
        else:
            return

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