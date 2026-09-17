"""
DocuCraft Properties Inspector Component
Provides real-time inspection and styling editing for selected elements on the canvas.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QPushButton, QScrollArea, QFrame,
    QStackedWidget, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from ui.components.buttons import PrimaryButton, SecondaryButton, IconButton
from ui.components.icons import get_pixmap, get_icon


class PropertiesInspector(QWidget):
    """
    Right sidebar panel in Template Studio:
    - Shows empty placeholder when no element is selected.
    - Shows full interactive typography, geometry, spacing, and color controls when an element is active.
    """
    apply_requested = Signal(dict)
    reset_requested = Signal()
    delete_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_element = None
        self._initial_data = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Header
        header_row = QWidget()
        h_lay = QHBoxLayout(header_row)
        h_lay.setContentsMargins(0, 0, 0, 0)
        title_lbl = QLabel("PROPERTIES INSPECTOR")
        title_lbl.setObjectName("panelTitle")
        h_lay.addWidget(title_lbl)
        h_lay.addStretch()

        self.delete_btn = IconButton("trash", color="#EF4444", tooltip="Delete Element", size=14)
        self.delete_btn.clicked.connect(self.delete_requested.emit)
        self.delete_btn.hide()
        h_lay.addWidget(self.delete_btn)
        main_layout.addWidget(header_row)

        # Stacked Container: Empty State vs Inspector Form
        self.stacked = QStackedWidget()
        main_layout.addWidget(self.stacked, 1)

        # ------------------------------------------------------------
        # Page 0: Empty State
        # ------------------------------------------------------------
        self.empty_page = QWidget()
        e_lay = QVBoxLayout(self.empty_page)
        e_lay.setContentsMargins(10, 40, 10, 10)
        e_lay.setSpacing(10)
        e_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_pixmap("sliders", color="#94A3B8", size=32))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e_lay.addWidget(icon_lbl)

        e_title = QLabel("No element selected.")
        e_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #475569;")
        e_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e_lay.addWidget(e_title)

        e_desc = QLabel("Click any element on the page canvas or select a layer to inspect its styling.")
        e_desc.setStyleSheet("font-size: 11px; color: #94A3B8; text-align: center;")
        e_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e_desc.setWordWrap(True)
        e_lay.addWidget(e_desc)
        e_lay.addStretch()
        self.stacked.addWidget(self.empty_page)

        # ------------------------------------------------------------
        # Page 1: Inspector Form
        # ------------------------------------------------------------
        self.form_page = QWidget()
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setStyleSheet("border: none; background: transparent;")

        form_content = QWidget()
        f_lay = QVBoxLayout(form_content)
        f_lay.setContentsMargins(0, 0, 0, 0)
        f_lay.setSpacing(12)

        # Element type tag banner
        self.type_banner = QLabel("Element Type")
        self.type_banner.setStyleSheet("""
            background-color: #EBF5FF;
            color: #168FE5;
            border: 1px solid #BAE0FD;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 8px;
        """)
        f_lay.addWidget(self.type_banner)

        # Content Text Edit
        f_lay.addWidget(self._make_section_label("CONTENT / TEXT"))
        self.text_input = QTextEdit()
        self.text_input.setFixedHeight(60)
        self.text_input.setStyleSheet("font-size: 12px;")
        f_lay.addWidget(self.text_input)

        # Geometry Section (Position X, Y & Size Width, Height)
        f_lay.addWidget(self._make_section_label("POSITION & SIZE"))
        geom_grid = QWidget()
        g_lay = QVBoxLayout(geom_grid)
        g_lay.setContentsMargins(0, 0, 0, 0)
        g_lay.setSpacing(6)

        # Row 1: X & Y
        pos_row = QWidget()
        pos_lay = QHBoxLayout(pos_row)
        pos_lay.setContentsMargins(0, 0, 0, 0)
        pos_lay.setSpacing(8)

        self.spin_x = self._make_spinbox(0, 1000, "X: ")
        self.spin_y = self._make_spinbox(0, 1000, "Y: ")
        pos_lay.addWidget(self.spin_x)
        pos_lay.addWidget(self.spin_y)
        g_lay.addWidget(pos_row)

        # Row 2: Width & Height
        size_row = QWidget()
        size_lay = QHBoxLayout(size_row)
        size_lay.setContentsMargins(0, 0, 0, 0)
        size_lay.setSpacing(8)

        self.spin_w = self._make_spinbox(20, 1000, "W: ")
        self.spin_h = self._make_spinbox(10, 800, "H: ")
        size_lay.addWidget(self.spin_w)
        size_lay.addWidget(self.spin_h)
        g_lay.addWidget(size_row)
        f_lay.addWidget(geom_grid)

        # Typography Section
        f_lay.addWidget(self._make_section_label("TYPOGRAPHY"))

        # Font family
        f_row1 = QWidget()
        f_lay1 = QHBoxLayout(f_row1)
        f_lay1.setContentsMargins(0, 0, 0, 0)
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems([
            "Georgia", "Garamond", "Times New Roman", "Palatino Linotype",
            "Segoe UI", "Inter", "Helvetica Neue", "Courier New"
        ])
        f_lay1.addWidget(self.font_family_combo)
        f_lay.addWidget(f_row1)

        # Font size & weight
        f_row2 = QWidget()
        f_lay2 = QHBoxLayout(f_row2)
        f_lay2.setContentsMargins(0, 0, 0, 0)
        f_lay2.setSpacing(8)

        self.spin_font_size = self._make_spinbox(8, 72, "Size: ")
        self.combo_font_weight = QComboBox()
        self.combo_font_weight.addItems(["Regular", "Medium", "Semibold", "Bold"])

        f_lay2.addWidget(self.spin_font_size)
        f_lay2.addWidget(self.combo_font_weight)
        f_lay.addWidget(f_row2)

        # Alignment & Line Height
        f_row3 = QWidget()
        f_lay3 = QHBoxLayout(f_row3)
        f_lay3.setContentsMargins(0, 0, 0, 0)
        f_lay3.setSpacing(8)

        self.combo_align = QComboBox()
        self.combo_align.addItems(["Left", "Center", "Right"])

        self.spin_line_height = QDoubleSpinBox()
        self.spin_line_height.setRange(1.0, 3.0)
        self.spin_line_height.setSingleStep(0.05)
        self.spin_line_height.setPrefix("Leading: ")
        self.spin_line_height.setValue(1.25)

        f_lay3.addWidget(self.combo_align)
        f_lay3.addWidget(self.spin_line_height)
        f_lay.addWidget(f_row3)

        # Spacing Section
        f_lay.addWidget(self._make_section_label("SPACING"))
        sp_row = QWidget()
        sp_lay = QHBoxLayout(sp_row)
        sp_lay.setContentsMargins(0, 0, 0, 0)
        sp_lay.setSpacing(8)

        self.spin_margin = self._make_spinbox(0, 100, "Margin: ")
        self.spin_padding = self._make_spinbox(0, 100, "Padding: ")
        sp_lay.addWidget(self.spin_margin)
        sp_lay.addWidget(self.spin_padding)
        f_lay.addWidget(sp_row)

        # Color Section
        f_lay.addWidget(self._make_section_label("COLORS"))
        col_row = QWidget()
        col_lay = QHBoxLayout(col_row)
        col_lay.setContentsMargins(0, 0, 0, 0)
        col_lay.setSpacing(8)

        self.combo_text_color = QComboBox()
        self.combo_text_color.addItems(["#1F2937", "#475569", "#168FE5", "#5B6FE8", "#16A085", "#000000"])

        self.combo_bg_color = QComboBox()
        self.combo_bg_color.addItems(["transparent", "#FFFFFF", "#F8FAFC", "#F1F5F9", "#EBF5FF"])

        col_lay.addWidget(self.combo_text_color)
        col_lay.addWidget(self.combo_bg_color)
        f_lay.addWidget(col_row)

        # Action Buttons: [ Apply ] [ Reset ]
        act_row = QWidget()
        act_lay = QHBoxLayout(act_row)
        act_lay.setContentsMargins(0, 8, 0, 0)
        act_lay.setSpacing(8)

        self.btn_apply = PrimaryButton("Apply Changes", icon_name="check-circle")
        self.btn_apply.clicked.connect(self._apply_changes)
        act_lay.addWidget(self.btn_apply)

        self.btn_reset = SecondaryButton("Reset")
        self.btn_reset.clicked.connect(self._reset_changes)
        act_lay.addWidget(self.btn_reset)
        f_lay.addWidget(act_row)

        f_lay.addStretch()
        form_scroll.setWidget(form_content)

        page_lay = QVBoxLayout(self.form_page)
        page_lay.setContentsMargins(0, 0, 0, 0)
        page_lay.addWidget(form_scroll)
        self.stacked.addWidget(self.form_page)

    def _make_section_label(self, title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px; margin-top: 4px;")
        return lbl

    def _make_spinbox(self, min_val: int, max_val: int, prefix: str) -> QSpinBox:
        sb = QSpinBox()
        sb.setRange(min_val, max_val)
        sb.setPrefix(prefix)
        return sb

    def inspect_element(self, canvas_element):
        self.current_element = canvas_element
        if not canvas_element:
            self.stacked.setCurrentIndex(0)
            self.delete_btn.hide()
            return

        self._initial_data = dict(canvas_element.element_data)
        d = canvas_element.element_data

        self.type_banner.setText(d.get("type", "Component Block").upper())
        self.text_input.setPlainText(d.get("text", ""))

        self.spin_x.setValue(int(d.get("x", 40)))
        self.spin_y.setValue(int(d.get("y", 60)))
        self.spin_w.setValue(int(d.get("width", 320)))
        self.spin_h.setValue(int(d.get("height", 60)))

        # Font
        font_name = d.get("font_family", "Georgia")
        idx_font = self.font_family_combo.findText(font_name)
        if idx_font >= 0:
            self.font_family_combo.setCurrentIndex(idx_font)
        else:
            self.font_family_combo.addItem(font_name)
            self.font_family_combo.setCurrentIndex(self.font_family_combo.count() - 1)

        self.spin_font_size.setValue(int(d.get("font_size", 12)))

        weight_name = d.get("font_weight", "Regular")
        idx_weight = self.combo_font_weight.findText(weight_name)
        if idx_weight >= 0:
            self.combo_font_weight.setCurrentIndex(idx_weight)
        else:
            self.combo_font_weight.addItem(weight_name)
            self.combo_font_weight.setCurrentIndex(self.combo_font_weight.count() - 1)

        align_name = d.get("alignment", "Left")
        idx_align = self.combo_align.findText(align_name)
        if idx_align >= 0:
            self.combo_align.setCurrentIndex(idx_align)
        else:
            self.combo_align.addItem(align_name)
            self.combo_align.setCurrentIndex(self.combo_align.count() - 1)

        self.spin_line_height.setValue(float(d.get("line_height", 1.25)))
        self.spin_margin.setValue(int(d.get("margin", 0)))
        self.spin_padding.setValue(int(d.get("padding", 6)))

        # Colors
        tc = d.get("text_color", "#1F2937")
        idx_tc = self.combo_text_color.findText(tc)
        if idx_tc >= 0:
            self.combo_text_color.setCurrentIndex(idx_tc)
        else:
            self.combo_text_color.addItem(tc)
            self.combo_text_color.setCurrentIndex(self.combo_text_color.count() - 1)

        bg = d.get("bg_color", "transparent")
        idx_bg = self.combo_bg_color.findText(bg)
        if idx_bg >= 0:
            self.combo_bg_color.setCurrentIndex(idx_bg)
        else:
            self.combo_bg_color.addItem(bg)
            self.combo_bg_color.setCurrentIndex(self.combo_bg_color.count() - 1)

        self.delete_btn.show()
        self.stacked.setCurrentIndex(1)

    def _apply_changes(self):
        if not self.current_element:
            return

        d = self.current_element.element_data
        d["text"] = self.text_input.toPlainText()
        d["x"] = self.spin_x.value()
        d["y"] = self.spin_y.value()
        d["width"] = self.spin_w.value()
        d["height"] = self.spin_h.value()
        d["font_family"] = self.font_family_combo.currentText()
        d["font_size"] = self.spin_font_size.value()
        d["font_weight"] = self.combo_font_weight.currentText()
        d["alignment"] = self.combo_align.currentText()
        d["line_height"] = self.spin_line_height.value()
        d["margin"] = self.spin_margin.value()
        d["padding"] = self.spin_padding.value()
        d["text_color"] = self.combo_text_color.currentText()
        d["bg_color"] = self.combo_bg_color.currentText()

        self.current_element.update_geometry_from_data()
        self.current_element.update_styling()
        self.current_element.update()
        self.apply_requested.emit(d)

    def _reset_changes(self):
        if not self.current_element:
            return
        self.current_element.element_data = dict(self._initial_data)
        self.inspect_element(self.current_element)
        self.current_element.update_geometry_from_data()
        self.current_element.update_styling()
        self.current_element.update()
        self.reset_requested.emit()
