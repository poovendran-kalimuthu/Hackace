"""
DocuCraft Reusable Sidebar Panel Component
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt


class SidebarPanel(QFrame):
    """
    Standardized sidebar panel with consistent header, border, and layout.
    side: 'left' or 'right'
    """
    def __init__(self, title: str = "", subtitle: str = "", side: str = "left", parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarPanel" if side == "left" else "rightPanel")
        border_side = "border-right" if side == "left" else "border-left"
        self.setStyleSheet(f"QFrame {{ background-color: #EEF1F5; {border_side}: 1px solid #D9DEE7; }}")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header area
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #EEF1F5;
                border-bottom: 1px solid #D9DEE7;
                padding: 10px 14px;
            }
        """)
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(3)

        self.top_row = QWidget()
        top_row_layout = QHBoxLayout(self.top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(8)

        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("panelTitle")
        top_row_layout.addWidget(self.title_label)

        top_row_layout.addStretch()
        self.header_action_container = QWidget()
        self.header_action_layout = QHBoxLayout(self.header_action_container)
        self.header_action_layout.setContentsMargins(0, 0, 0, 0)
        self.header_action_layout.setSpacing(4)
        top_row_layout.addWidget(self.header_action_container)

        header_layout.addWidget(self.top_row)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("color: #64748B; font-size: 11px;")
        if not subtitle:
            self.subtitle_label.hide()
        header_layout.addWidget(self.subtitle_label)

        self.main_layout.addWidget(self.header_frame)

        # Content area
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(10)
        self.main_layout.addWidget(self.content_area, 1)

    def set_title(self, title: str):
        self.title_label.setText(title.upper())

    def set_subtitle(self, subtitle: str):
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))

    def add_header_action(self, widget: QWidget):
        self.header_action_layout.addWidget(widget)
