import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from PyQt6.QtWidgets import ( QWidget, QPushButton, QLabel, QVBoxLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve
from PyQt6.QtGui import QColor

class AnimatedButton(QPushButton):
    def __init__(self, text, accent_color, parent=None):
        super().__init__(text, parent)
        self.accent_color_hex = accent_color
        self.setFixedSize(480, 70) 
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.original_pos = None  

        self.default_style = f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-left: 4px solid {accent_color};
                border-radius: 15px;
                font-family: 'Montserrat';
                font-size: 11pt;
                font-weight: 600;
                color: #ffffff;
                text-align: center; letter-spacing: 2px;
            }}
        """
        self.hover_style = f"""
            QPushButton {{
                background-color: {accent_color};
                border: 1px solid {accent_color};
                border-radius: 15px;
                font-family: 'Montserrat';
                font-size: 11pt;
                font-weight: 800;
                color: #000000;
                text-align: center; letter-spacing: 2px;
            }}
        """
        self.setStyleSheet(self.default_style)
        
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(70)
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
        self.anim.setEndValue(QPoint(self.original_pos.x(), self.original_pos.y() - 5))
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

def create_back_button(text="Back"):
    btn = QPushButton(text)
    btn.setFixedSize(220, 50)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)

    btn.setStyleSheet("""
        QPushButton {
            font-family: 'Montserrat';
            font-size: 11pt;
            font-weight: 600;

            color: white;
            background-color: rgba(255, 255, 255, 0.06);

            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 12px;
        }

        QPushButton:hover {
            background-color: rgba(239, 68, 68, 0.25);
            border: 1px solid #ef4444;
        }

        QPushButton:pressed {
            background-color: rgba(239, 68, 68, 0.4);
        }
    """)

    return btn

class LoadingScreen(QWidget):
    def __init__(self, message="Loading..."):
        super().__init__()

        self.setWindowTitle("AirCanvas Loading")
        self.showFullScreen()

        self.setStyleSheet("""
            QWidget {
                background-color: #0a0a0f;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        layout.addStretch()

        title = QLabel("AIR CANVAS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-family: 'Orbitron';
            font-size: 72pt;
            font-weight: 900;
            color: white;
            letter-spacing: -1px;
        """)

        msg = QLabel(message)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("""
            font-family: 'Montserrat';
            font-size: 16pt;
            color: rgba(255,255,255,0.7);
            margin-top: 10px;
        """)

        status = QLabel("Please wait...")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setStyleSheet("""
            font-family: 'Montserrat';
            font-size: 12pt;
            color: rgba(255,255,255,0.4);
            margin-top: 5px;
        """)

        layout.addWidget(title)
        layout.addWidget(msg)
        layout.addSpacing(10)
        layout.addWidget(status)

        layout.addStretch()