"""
DocuCraft Template Studio Toolbox & Layers Panel
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QListWidget, QListWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QCursor, QIcon
from ui.components.icons import get_icon, get_pixmap
from ui.components.buttons import IconButton


class ComponentToolbox(QWidget):
    """
    Left panel component for Template Studio:
    - Reusable element toolbox buttons
    - Layers list showing canvas elements
    """
    component_add_requested = Signal(dict)
    layer_selected = Signal(object)
    layer_deleted = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.elements_map = {}  # list_item -> canvas_element

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(14)

        # ------------------------------------------------------------
        # 1. Toolbox Header & Description
        # ------------------------------------------------------------
        header_box = QWidget()
        h_lay = QVBoxLayout(header_box)
        h_lay.setContentsMargins(0, 0, 0, 0)
        h_lay.setSpacing(4)

        title_lbl = QLabel("COMPONENTS TOOLBOX")
        title_lbl.setObjectName("panelTitle")
        h_lay.addWidget(title_lbl)

        desc_lbl = QLabel("Click to add reusable elements to the Normal Page canvas.")
        desc_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        desc_lbl.setWordWrap(True)
        h_lay.addWidget(desc_lbl)
        main_layout.addWidget(header_box)

        # ------------------------------------------------------------
        # 2. Components Button Grid / List
        # ------------------------------------------------------------
        tools = [
            ("Chapter Title", "title", {
                "type": "Chapter Title",
                "text": "Chapter 1: The Odyssey",
                "font_family": "Georgia",
                "font_size": 22,
                "font_weight": "Bold",
                "alignment": "Center",
                "height": 45,
                "width": 360,
                "text_color": "#1F2937",
                "bg_color": "transparent"
            }),
            ("Section Heading", "heading", {
                "type": "Section Heading",
                "text": "1.1 The Awakening",
                "font_family": "Georgia",
                "font_size": 15,
                "font_weight": "Semibold",
                "alignment": "Left",
                "height": 34,
                "width": 360,
                "text_color": "#334155",
                "bg_color": "transparent"
            }),
            ("Body Text Box", "text", {
                "type": "Body Text Box",
                "text": "Enter manuscript paragraph text here. Formatting settings will flow according to your page trim and typography specs.",
                "font_family": "Georgia",
                "font_size": 11,
                "font_weight": "Regular",
                "alignment": "Left",
                "height": 80,
                "width": 360,
                "text_color": "#1F2937",
                "bg_color": "transparent"
            }),
            ("Blockquote", "quote", {
                "type": "Blockquote",
                "text": "“The unexamined manuscript is not worth publishing.”",
                "font_family": "Georgia",
                "font_size": 11,
                "font_weight": "Regular",
                "alignment": "Left",
                "height": 55,
                "width": 360,
                "text_color": "#475569",
                "bg_color": "#F8FAFC"
            }),
            ("Image Placeholder", "image", {
                "type": "Image Placeholder",
                "text": "Figure 1: Illustration",
                "font_family": "Segoe UI",
                "font_size": 10,
                "font_weight": "Regular",
                "alignment": "Center",
                "height": 130,
                "width": 360,
                "text_color": "#64748B",
                "bg_color": "#F1F5F9"
            }),
            ("Table Grid", "table", {
                "type": "Table Grid",
                "text": "Table 1: Dataset Summary",
                "font_family": "Segoe UI",
                "font_size": 10,
                "font_weight": "Regular",
                "alignment": "Left",
                "height": 90,
                "width": 360,
                "text_color": "#1F2937",
                "bg_color": "#FFFFFF"
            }),
            ("Page Number", "hash", {
                "type": "Page Number",
                "text": "— 1 —",
                "font_family": "Georgia",
                "font_size": 11,
                "font_weight": "Regular",
                "alignment": "Center",
                "height": 28,
                "width": 360,
                "text_color": "#94A3B8",
                "bg_color": "transparent"
            }),
            ("Divider Ornament", "divider", {
                "type": "Divider Ornament",
                "text": "◆",
                "font_family": "Segoe UI",
                "font_size": 12,
                "font_weight": "Regular",
                "alignment": "Center",
                "height": 24,
                "width": 360,
                "text_color": "#168FE5",
                "bg_color": "transparent"
            }),
        ]

        buttons_container = QWidget()
        btn_layout = QVBoxLayout(buttons_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(6)

        for label, icon_name, template_data in tools:
            btn = QPushButton(f"  {label}")
            btn.setObjectName("toolButton")
            btn.setIcon(get_icon(icon_name, color="#168FE5", size=16))
            btn.setIconSize(QSize(16, 16))
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked=False, data=template_data: self._on_add_clicked(data))
            btn_layout.addWidget(btn)

        main_layout.addWidget(buttons_container)

        # ------------------------------------------------------------
        # 3. Divider
        # ------------------------------------------------------------
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #D9DEE7;")
        main_layout.addWidget(line)

        # ------------------------------------------------------------
        # 4. Layers Section
        # ------------------------------------------------------------
        self.layers_header = QLabel("LAYERS (0)")
        self.layers_header.setObjectName("panelTitle")
        main_layout.addWidget(self.layers_header)

        # Layers List
        self.layers_list = QListWidget()
        self.layers_list.setStyleSheet("""
            QListWidget {
                background-color: #FFFFFF;
                border: 1px solid #D9DEE7;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #F1F5F9;
            }
            QListWidget::item:selected {
                background-color: #EBF5FF;
                color: #168FE5;
            }
        """)
        self.layers_list.itemClicked.connect(self._on_layer_item_clicked)
        main_layout.addWidget(self.layers_list, 1)

        # Empty layers label
        self.empty_layers_lbl = QLabel("No components on this page.")
        self.empty_layers_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-style: italic; padding: 6px;")
        self.empty_layers_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.empty_layers_lbl)

    def _on_add_clicked(self, template_data: dict):
        # Create a copy so multiple adds have separate dict instances
        data_copy = dict(template_data)
        self.component_add_requested.emit(data_copy)

    def sync_layers(self, canvas_elements: list, selected_element=None):
        self.layers_list.clear()
        count = len(canvas_elements)
        self.layers_header.setText(f"LAYERS ({count})")
        self.empty_layers_lbl.setVisible(count == 0)
        self.layers_list.setVisible(count > 0)

        for el in reversed(canvas_elements):  # Topmost first
            el_type = el.element_data.get("type", "Element")
            text_snippet = el.element_data.get("text", "")[:24]
            display_text = f"{el_type}: {text_snippet}" if text_snippet else el_type

            icon_name = "title" if "Title" in el_type else ("heading" if "Heading" in el_type else "text")
            item = QListWidgetItem(get_icon(icon_name, color="#168FE5", size=14), display_text)
            item.setData(Qt.ItemDataRole.UserRole, el)
            self.layers_list.addItem(item)

            if el == selected_element:
                self.layers_list.setCurrentItem(item)

    def _on_layer_item_clicked(self, item: QListWidgetItem):
        el = item.data(Qt.ItemDataRole.UserRole)
        if el:
            self.layer_selected.emit(el)
