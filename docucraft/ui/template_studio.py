"""
DocuCraft Template Studio Workspace
Matches the second reference screenshot layout:
- Top Toolbar: "Template Studio", "Trim: 5.5 × 8.5", Zoom [-] 100% [+], [ Save Template ]
- 3-Panel Studio:
  - LEFT: Components Toolbox & Layers list
  - CENTER: Interactive Page Canvas with margin guides and selectable blocks
  - RIGHT: Properties Inspector with live attribute binding
- BOTTOM: "PAGE TYPES" horizontal selector bar (Cover, Normal Page, Chapter Opening, etc.)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QScrollArea,
    QFrame, QPushButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from ui.components.buttons import PrimaryButton, SecondaryButton, ZoomControl
from ui.components.canvas import InteractivePageCanvas
from ui.components.toolbox import ComponentToolbox
from ui.components.inspector import PropertiesInspector
from ui.components.icons import get_pixmap, get_icon


class TemplateStudioView(QWidget):
    toast_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page_type = "Normal Page"

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ------------------------------------------------------------
        # 1. Top Toolbar
        # ------------------------------------------------------------
        top_toolbar = QFrame()
        top_toolbar.setFixedHeight(48)
        top_toolbar.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-bottom: 1px solid #D9DEE7;
            }
        """)
        tt_lay = QHBoxLayout(top_toolbar)
        tt_lay.setContentsMargins(18, 0, 18, 0)
        tt_lay.setSpacing(16)

        # Title and Trim Pill
        title_box = QWidget()
        tb_lay = QHBoxLayout(title_box)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.setSpacing(10)

        studio_icon = QLabel()
        studio_icon.setPixmap(get_pixmap("template", color="#168FE5", size=18))
        tb_lay.addWidget(studio_icon)

        studio_lbl = QLabel("Template Studio")
        studio_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #1F2937;")
        tb_lay.addWidget(studio_lbl)

        self.trim_badge = QLabel("Trim: 5.5 × 8.5 in")
        self.trim_badge.setStyleSheet("""
            background-color: #F1F5F9;
            color: #475569;
            border: 1px solid #E2E8F0;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
        """)
        tb_lay.addWidget(self.trim_badge)

        self.page_type_indicator = QLabel("Active: Normal Page")
        self.page_type_indicator.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 500;")
        tb_lay.addWidget(self.page_type_indicator)

        tt_lay.addWidget(title_box)
        tt_lay.addStretch()

        # Zoom Controls
        self.zoom_ctrl = ZoomControl(default_zoom=100, min_zoom=50, max_zoom=170)
        self.zoom_ctrl.zoom_changed.connect(self._on_zoom_changed)
        tt_lay.addWidget(self.zoom_ctrl)

        # Save Template Button
        save_btn = PrimaryButton("Save Template", icon_name="save")
        save_btn.setFixedHeight(30)
        save_btn.clicked.connect(self._on_save_template)
        tt_lay.addWidget(save_btn)

        main_layout.addWidget(top_toolbar)

        # ------------------------------------------------------------
        # 2. Main 3-Panel Workspace (QSplitter)
        # ------------------------------------------------------------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #D9DEE7; }")

        # Left: Components Toolbox & Layers
        left_container = QFrame()
        left_container.setObjectName("sidebarPanel")
        left_container.setStyleSheet("QFrame#sidebarPanel { background-color: #EEF1F5; border-right: 1px solid #D9DEE7; }")
        left_container.setFixedWidth(260)
        l_lay = QVBoxLayout(left_container)
        l_lay.setContentsMargins(0, 0, 0, 0)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setStyleSheet("border: none; background: transparent;")

        self.toolbox = ComponentToolbox()
        self.toolbox.component_add_requested.connect(self._on_add_component)
        self.toolbox.layer_selected.connect(self._on_layer_selected)
        left_scroll.setWidget(self.toolbox)
        l_lay.addWidget(left_scroll)
        splitter.addWidget(left_container)

        # Center: Interactive Page Canvas
        center_scroll = QScrollArea()
        center_scroll.setWidgetResizable(True)
        center_scroll.setStyleSheet("background-color: #F4F6F8; border: none;")

        self.canvas = InteractivePageCanvas()
        self.canvas.element_selected.connect(self._on_canvas_element_selected)
        self.canvas.element_modified.connect(self._on_canvas_element_modified)
        center_scroll.setWidget(self.canvas)
        splitter.addWidget(center_scroll)

        # Right: Properties Inspector
        right_container = QFrame()
        right_container.setObjectName("rightPanel")
        right_container.setStyleSheet("QFrame#rightPanel { background-color: #EEF1F5; border-left: 1px solid #D9DEE7; }")
        right_container.setFixedWidth(280)
        r_lay = QVBoxLayout(right_container)
        r_lay.setContentsMargins(0, 0, 0, 0)

        self.inspector = PropertiesInspector()
        self.inspector.apply_requested.connect(self._on_inspector_apply)
        self.inspector.reset_requested.connect(self._on_inspector_reset)
        self.inspector.delete_requested.connect(self._on_delete_selected_element)
        r_lay.addWidget(self.inspector)
        splitter.addWidget(right_container)

        splitter.setSizes([260, 800, 280])
        main_layout.addWidget(splitter, 1)

        # ------------------------------------------------------------
        # 3. Bottom Page Type Bar
        # ------------------------------------------------------------
        bottom_bar = QFrame()
        bottom_bar.setFixedHeight(50)
        bottom_bar.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-top: 1px solid #D9DEE7;
            }
        """)
        bb_lay = QHBoxLayout(bottom_bar)
        bb_lay.setContentsMargins(16, 6, 16, 6)
        bb_lay.setSpacing(12)

        pt_title = QLabel("PAGE TYPES")
        pt_title.setObjectName("panelTitle")
        bb_lay.addWidget(pt_title)

        # Scrollable / horizontal list of page type buttons
        types_scroll = QScrollArea()
        types_scroll.setWidgetResizable(True)
        types_scroll.setFixedHeight(38)
        types_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        types_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        types_scroll.setStyleSheet("border: none; background: transparent;")

        types_widget = QWidget()
        tw_lay = QHBoxLayout(types_widget)
        tw_lay.setContentsMargins(0, 0, 0, 0)
        tw_lay.setSpacing(6)

        self.page_types = [
            "Cover", "Title Page", "Copyright Page", "Dedication",
            "Table of Contents", "Chapter Opening", "Normal Page",
            "Quote Page", "Image Page", "Table Page", "Appendix"
        ]

        self.page_type_buttons = {}
        for ptype in self.page_types:
            btn = QPushButton(ptype)
            btn.setObjectName("pageTypeTab")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            is_active = (ptype == "Normal Page")
            btn.setProperty("active", "true" if is_active else "false")
            btn.clicked.connect(lambda checked=False, pt=ptype: self._switch_page_type(pt))
            tw_lay.addWidget(btn)
            self.page_type_buttons[ptype] = btn

        types_scroll.setWidget(types_widget)
        bb_lay.addWidget(types_scroll, 1)

        main_layout.addWidget(bottom_bar)

        # Load initial mock components for Normal Page
        self._load_page_type_template("Normal Page")

    def _on_zoom_changed(self, zoom: int):
        self.canvas.set_zoom(zoom)

    def _on_save_template(self):
        self.toast_requested.emit(f"✓ Template '{self.current_page_type}' saved locally.")

    def _on_add_component(self, template_data: dict):
        # Position new component with stagger if coordinates not explicitly set
        if "x" not in template_data:
            template_data["x"] = 40
        if "y" not in template_data:
            existing_count = len(self.canvas.elements)
            template_data["y"] = 60 + (existing_count * 50) % 450

        widget = self.canvas.add_element(template_data)
        self.toolbox.sync_layers(self.canvas.elements, widget)
        self.inspector.inspect_element(widget)
        self.toast_requested.emit(f"Added '{template_data.get('type')}' to canvas.")

    def _on_canvas_element_selected(self, widget):
        self.inspector.inspect_element(widget)
        self.toolbox.sync_layers(self.canvas.elements, widget)

    def _on_canvas_element_modified(self, widget):
        self.inspector.inspect_element(widget)

    def _on_layer_selected(self, widget):
        if widget:
            self.canvas._on_element_selected(widget)

    def _on_delete_selected_element(self):
        if self.canvas.selected_element:
            name = self.canvas.selected_element.element_data.get("type", "Element")
            self.canvas.remove_element(self.canvas.selected_element)
            self.toolbox.sync_layers(self.canvas.elements, None)
            self.toast_requested.emit(f"Removed '{name}' from page.")

    def _on_inspector_apply(self, updated_data: dict):
        self.toolbox.sync_layers(self.canvas.elements, self.canvas.selected_element)
        self.toast_requested.emit("Applied element properties.")

    def _on_inspector_reset(self):
        self.toolbox.sync_layers(self.canvas.elements, self.canvas.selected_element)

    def _switch_page_type(self, ptype: str):
        self.current_page_type = ptype
        self.page_type_indicator.setText(f"Active: {ptype}")

        for name, btn in self.page_type_buttons.items():
            is_act = (name == ptype)
            btn.setProperty("active", "true" if is_act else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._load_page_type_template(ptype)
        self.toast_requested.emit(f"Switched page type: {ptype}")

    def _load_page_type_template(self, ptype: str):
        self.canvas.clear_elements()

        if ptype == "Normal Page":
            # Running header
            self.canvas.add_element({
                "type": "Section Heading",
                "text": "THE CHRONICLES OF ELDORIA",
                "font_family": "Segoe UI",
                "font_size": 9,
                "font_weight": "Semibold",
                "alignment": "Center",
                "x": 40, "y": 45, "width": 360, "height": 20,
                "text_color": "#94A3B8", "bg_color": "transparent"
            })
            # Body Paragraph 1
            self.canvas.add_element({
                "type": "Body Text Box",
                "text": "The wind howled across the high crags as darkness settled. Master Caleb checked the seals on his leather folio one final time before the descent.",
                "font_family": "Georgia",
                "font_size": 11,
                "font_weight": "Regular",
                "alignment": "Left",
                "x": 40, "y": 80, "width": 360, "height": 90,
                "text_color": "#1F2937", "bg_color": "transparent"
            })
            # Blockquote
            self.canvas.add_element({
                "type": "Blockquote",
                "text": "“Every path begins with the silence of the first unwritten step.”",
                "font_family": "Georgia",
                "font_size": 11,
                "font_weight": "Regular",
                "alignment": "Left",
                "x": 40, "y": 190, "width": 360, "height": 55,
                "text_color": "#475569", "bg_color": "#F8FAFC"
            })
            # Body Paragraph 2
            self.canvas.add_element({
                "type": "Body Text Box",
                "text": "Beneath them, the ruins of the observatory lay half-buried in blue frost, waiting for the equinox alignment.",
                "font_family": "Georgia",
                "font_size": 11,
                "font_weight": "Regular",
                "alignment": "Left",
                "x": 40, "y": 260, "width": 360, "height": 70,
                "text_color": "#1F2937", "bg_color": "transparent"
            })
            # Page Number Footer
            self.canvas.add_element({
                "type": "Page Number",
                "text": "14",
                "font_family": "Georgia",
                "font_size": 11,
                "font_weight": "Regular",
                "alignment": "Center",
                "x": 40, "y": 620, "width": 360, "height": 24,
                "text_color": "#94A3B8", "bg_color": "transparent"
            })

        elif ptype == "Chapter Opening":
            self.canvas.add_element({
                "type": "Chapter Title",
                "text": "CHAPTER 1",
                "font_family": "Georgia",
                "font_size": 13,
                "font_weight": "Semibold",
                "alignment": "Center",
                "x": 40, "y": 90, "width": 360, "height": 24,
                "text_color": "#64748B", "bg_color": "transparent"
            })
            self.canvas.add_element({
                "type": "Chapter Title",
                "text": "The Silent Horizon",
                "font_family": "Georgia",
                "font_size": 24,
                "font_weight": "Bold",
                "alignment": "Center",
                "x": 40, "y": 120, "width": 360, "height": 40,
                "text_color": "#1F2937", "bg_color": "transparent"
            })
            self.canvas.add_element({
                "type": "Divider Ornament",
                "text": "◆",
                "font_family": "Segoe UI",
                "font_size": 12,
                "font_weight": "Regular",
                "alignment": "Center",
                "x": 40, "y": 170, "width": 360, "height": 20,
                "text_color": "#168FE5", "bg_color": "transparent"
            })
            self.canvas.add_element({
                "type": "Body Text Box",
                "text": "It began in the quiet hush just before dawn, when the mist still clung like spider silk across the valleys.",
                "font_family": "Georgia",
                "font_size": 11,
                "font_weight": "Regular",
                "alignment": "Left",
                "x": 40, "y": 210, "width": 360, "height": 100,
                "text_color": "#1F2937", "bg_color": "transparent"
            })

        elif ptype == "Title Page":
            self.canvas.add_element({
                "type": "Chapter Title",
                "text": "THE CHRONICLES OF ELDORIA",
                "font_family": "Georgia",
                "font_size": 24,
                "font_weight": "Bold",
                "alignment": "Center",
                "x": 40, "y": 180, "width": 360, "height": 60,
                "text_color": "#1F2937", "bg_color": "transparent"
            })
            self.canvas.add_element({
                "type": "Section Heading",
                "text": "A Historical Record of the Third Age",
                "font_family": "Georgia",
                "font_size": 13,
                "font_weight": "Regular",
                "alignment": "Center",
                "x": 40, "y": 250, "width": 360, "height": 30,
                "text_color": "#64748B", "bg_color": "transparent"
            })
            self.canvas.add_element({
                "type": "Divider Ornament",
                "text": "◆",
                "font_family": "Segoe UI",
                "font_size": 12,
                "font_weight": "Regular",
                "alignment": "Center",
                "x": 40, "y": 300, "width": 360, "height": 20,
                "text_color": "#168FE5", "bg_color": "transparent"
            })
            self.canvas.add_element({
                "type": "Section Heading",
                "text": "EDWARD V. ASHFORD",
                "font_family": "Georgia",
                "font_size": 14,
                "font_weight": "Semibold",
                "alignment": "Center",
                "x": 40, "y": 480, "width": 360, "height": 30,
                "text_color": "#334155", "bg_color": "transparent"
            })

        # Sync layers list and inspector
        first_el = self.canvas.elements[0] if self.canvas.elements else None
        self.toolbox.sync_layers(self.canvas.elements, first_el)
        self.inspector.inspect_element(first_el)
