"""
DocuCraft Fixed Top Navigation Bar
Height: ~56px
Includes:
- App logo (blue rounded square with open book), title, PRO badge
- 5 Center navigation buttons with icons and active states
- Right-aligned offline status pill: "✓ 100% Offline & Private"
"""

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QWidget, QButtonGroup, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor
from ui.components.buttons import NavigationButton
from ui.components.icons import get_pixmap


class AppHeader(QFrame):
    navigation_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topNavHeader")
        self.setFixedHeight(56)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(18, 0, 18, 0)
        main_layout.setSpacing(12)

        # ------------------------------------------------------------
        # 1. Left: Brand Logo & Title & PRO badge
        # ------------------------------------------------------------
        brand_widget = QWidget()
        brand_layout = QHBoxLayout(brand_widget)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(10)

        # Blue rounded-square icon
        logo_label = QLabel()
        logo_label.setFixedSize(32, 32)
        logo_pixmap = QPixmap(32 * 2, 32 * 2)
        logo_pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(logo_pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#168FE5"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, 64, 64, 14, 14)
        # Draw book icon in white inside
        book_px = get_pixmap("book-open", color="#FFFFFF", size=18)
        p.drawPixmap(14, 14, book_px)
        p.end()
        logo_pixmap.setDevicePixelRatio(2.0)
        logo_label.setPixmap(logo_pixmap)
        brand_layout.addWidget(logo_label)

        # Title
        title_label = QLabel("DocuCraft")
        title_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #1F2937; letter-spacing: -0.2px;")
        brand_layout.addWidget(title_label)

        # PRO badge
        pro_badge = QLabel("PRO")
        pro_badge.setStyleSheet("""
            background-color: #EBF5FF;
            color: #168FE5;
            border: 1px solid #BAE0FD;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            padding: 1px 6px;
        """)
        brand_layout.addWidget(pro_badge)

        main_layout.addWidget(brand_widget)
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # ------------------------------------------------------------
        # 2. Center: Navigation Items
        # ------------------------------------------------------------
        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.nav_items = [
            ("Projects", "projects", "dashboard"),
            ("Manuscript", "manuscript", "manuscript"),
            ("Review Queue", "review", "review_queue"),
            ("Template Studio", "template", "template_studio"),
            ("Book Preview", "preview", "book_preview"),
        ]

        self.buttons = {}
        for text, icon_name, view_id in self.nav_items:
            btn = NavigationButton(text, icon_name, view_id, self)
            btn.clicked.connect(lambda checked=False, vid=view_id: self._on_nav_clicked(vid))
            self.btn_group.addButton(btn)
            nav_layout.addWidget(btn)
            self.buttons[view_id] = btn

        main_layout.addWidget(nav_widget)
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # ------------------------------------------------------------
        # 3. Right: Green outlined offline status pill
        # ------------------------------------------------------------
        offline_pill = QFrame()
        offline_pill.setObjectName("offlinePill")
        pill_layout = QHBoxLayout(offline_pill)
        pill_layout.setContentsMargins(10, 4, 12, 4)
        pill_layout.setSpacing(6)

        pill_text = QLabel("✓ 100% Offline & Private")
        pill_text.setObjectName("offlinePillText")
        pill_layout.addWidget(pill_text)

        main_layout.addWidget(offline_pill)

        # Set default active navigation item
        self.set_active_view("dashboard")

    def _on_nav_clicked(self, view_id: str):
        self.set_active_view(view_id)
        self.navigation_requested.emit(view_id)

    def set_active_view(self, view_id: str):
        for vid, btn in self.buttons.items():
            is_active = (vid == view_id)
            btn.setChecked(is_active)
            btn.update_appearance(is_active)
