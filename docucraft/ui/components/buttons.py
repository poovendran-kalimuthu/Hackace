"""
DocuCraft Reusable Button and Control Components
"""

from PySide6.QtWidgets import QPushButton, QLabel, QFrame, QHBoxLayout, QWidget
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QCursor
from ui.components.icons import get_icon


class PrimaryButton(QPushButton):
    def __init__(self, text: str, icon_name: str = None, parent=None):
        super().__init__(text, parent)
        self.setObjectName("primaryButton")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            QPushButton#primaryButton {
                background-color: #168FE5;
                color: #FFFFFF;
                border: 1px solid #1480CE;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#primaryButton:hover {
                background-color: #0E7AC9;
                border-color: #0B65A8;
            }
            QPushButton#primaryButton:pressed {
                background-color: #0B65A8;
            }
            QPushButton#primaryButton:disabled {
                background-color: #E2E8F0;
                color: #94A3B8;
                border-color: #CBD5E1;
            }
        """)
        if icon_name:
            self.setIcon(get_icon(icon_name, color="#FFFFFF", size=15))
            self.setIconSize(QSize(15, 15))


class SecondaryButton(QPushButton):
    def __init__(self, text: str, icon_name: str = None, parent=None):
        super().__init__(text, parent)
        self.setObjectName("secondaryButton")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            QPushButton#secondaryButton {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #D9DEE7;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton#secondaryButton:hover {
                background-color: #F8FAFC;
                border-color: #CBD5E1;
                color: #0F172A;
            }
            QPushButton#secondaryButton:pressed {
                background-color: #F1F5F9;
            }
            QPushButton#secondaryButton:disabled {
                background-color: #F8FAFC;
                color: #94A3B8;
                border-color: #E2E8F0;
            }
        """)
        if icon_name:
            self.setIcon(get_icon(icon_name, color="#1F2937", size=15))
            self.setIconSize(QSize(15, 15))


class AccentButton(QPushButton):
    def __init__(self, text: str, icon_name: str = None, parent=None):
        super().__init__(text, parent)
        self.setObjectName("accentButton")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            QPushButton#accentButton {
                background-color: #5B6FE8;
                color: #FFFFFF;
                border: 1px solid #4B5ED3;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#accentButton:hover {
                background-color: #4B5ED3;
            }
        """)
        if icon_name:
            self.setIcon(get_icon(icon_name, color="#FFFFFF", size=15))
            self.setIconSize(QSize(15, 15))


class IconButton(QPushButton):
    def __init__(self, icon_name: str, color: str = "#64748B", tooltip: str = "", size: int = 16, parent=None):
        super().__init__(parent)
        self.setObjectName("iconButton")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            QPushButton#iconButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton#iconButton:hover {
                background-color: #E2E8F0;
            }
        """)
        self.setIcon(get_icon(icon_name, color=color, size=size))
        self.setIconSize(QSize(size, size))
        self.setFixedSize(size + 14, size + 14)
        if tooltip:
            self.setToolTip(tooltip)


class NavigationButton(QPushButton):
    """Navigation button used in top fixed header."""
    def __init__(self, text: str, icon_name: str, view_id: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("navButton")
        self.view_id = view_id
        self.icon_name = icon_name
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setIconSize(QSize(16, 16))
        self.update_appearance(False)

    def update_appearance(self, is_active: bool):
        color = "#168FE5" if is_active else "#64748B"
        self.setIcon(get_icon(self.icon_name, color=color, size=16))
        if is_active:
            self.setStyleSheet("""
                QPushButton#navButton {
                    background-color: #EBF5FF;
                    color: #168FE5;
                    border: 1px solid #BAE0FD;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-size: 13px;
                    font-weight: 600;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton#navButton {
                    background-color: transparent;
                    color: #64748B;
                    border: 1px solid transparent;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton#navButton:hover {
                    background-color: #F1F5F9;
                    color: #1F2937;
                }
            """)


class StatusBadge(QLabel):
    """Clean badge component for severity and statuses (Critical, Warning, Suggestion, Success)."""
    def __init__(self, text: str, variant: str = "suggestion", parent=None):
        super().__init__(text, parent)
        var = variant.lower()
        if var == "critical":
            self.setStyleSheet("background-color: #FDEDEC; color: #E74C3C; border: 1px solid #FADBD8; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600;")
        elif var == "warning":
            self.setStyleSheet("background-color: #FEF9E7; color: #D68910; border: 1px solid #FCF3CF; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600;")
        elif var == "success":
            self.setStyleSheet("background-color: #E8F8F5; color: #16A085; border: 1px solid #A2E2D4; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600;")
        else:
            self.setStyleSheet("background-color: #EBF5FF; color: #168FE5; border: 1px solid #D4E6F1; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class ZoomControl(QWidget):
    """Reusable zoom control widget: [-] 100% [+]"""
    zoom_changed = Signal(int)

    def __init__(self, default_zoom: int = 100, min_zoom: int = 50, max_zoom: int = 200, parent=None):
        super().__init__(parent)
        self.current_zoom = default_zoom
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.btn_minus = QPushButton("-")
        self.btn_minus.setFixedSize(26, 26)
        self.btn_minus.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_minus.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #D9DEE7;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 600;
                color: #64748B;
            }
            QPushButton:hover {
                background-color: #F8FAFC;
                color: #1F2937;
                border-color: #CBD5E1;
            }
        """)
        self.btn_minus.clicked.connect(self.zoom_out)

        self.label = QLabel(f"{self.current_zoom}%")
        self.label.setFixedWidth(46)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #1F2937; font-weight: 600; font-size: 12px;")

        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedSize(26, 26)
        self.btn_plus.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_plus.setStyleSheet(self.btn_minus.styleSheet())
        self.btn_plus.clicked.connect(self.zoom_in)

        layout.addWidget(self.btn_minus)
        layout.addWidget(self.label)
        layout.addWidget(self.btn_plus)

    def zoom_in(self):
        if self.current_zoom < self.max_zoom:
            self.set_zoom(self.current_zoom + 10)

    def zoom_out(self):
        if self.current_zoom > self.min_zoom:
            self.set_zoom(self.current_zoom - 10)

    def set_zoom(self, zoom: int):
        self.current_zoom = max(self.min_zoom, min(self.max_zoom, zoom))
        self.label.setText(f"{self.current_zoom}%")
        self.zoom_changed.emit(self.current_zoom)
