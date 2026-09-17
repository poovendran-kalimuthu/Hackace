"""
DocuCraft Manuscript Workspace
3-panel desktop layout:
- LEFT: Document Structure tree (Front Matter, Chapters, Back Matter)
- CENTER: Document Page Canvas (realistic book page with typography, margins, zoom controls)
- RIGHT: Formatting Inspector (Trim, margins, typography presets, pagination)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QScrollArea,
    QTreeWidget, QTreeWidgetItem, QFrame, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QPushButton
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QCursor
from ui.components.buttons import PrimaryButton, SecondaryButton, IconButton, ZoomControl
from ui.components.canvas import DocumentCanvas
from ui.components.icons import get_icon, get_pixmap
from ui.components.sidebar import SidebarPanel


class ManuscriptView(QWidget):
    toast_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ------------------------------------------------------------
        # Top Workspace Toolbar
        # ------------------------------------------------------------
        top_bar = QFrame()
        top_bar.setFixedHeight(44)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-bottom: 1px solid #D9DEE7;
            }
        """)
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(16, 0, 16, 0)
        tb_lay.setSpacing(12)

        doc_icon = QLabel()
        doc_icon.setPixmap(get_pixmap("manuscript", color="#168FE5", size=16))
        tb_lay.addWidget(doc_icon)

        self.project_name_lbl = QLabel("The Obsidian Protocol — Manuscript Editor")
        self.project_name_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #1F2937;")
        tb_lay.addWidget(self.project_name_lbl)

        tb_lay.addStretch()

        # Zoom Controls
        self.zoom_ctrl = ZoomControl(default_zoom=100, min_zoom=60, max_zoom=180)
        self.zoom_ctrl.zoom_changed.connect(self._on_zoom_changed)
        tb_lay.addWidget(self.zoom_ctrl)

        fit_btn = SecondaryButton("Fit Width")
        fit_btn.setFixedHeight(28)
        fit_btn.clicked.connect(lambda: self.zoom_ctrl.set_zoom(115))
        tb_lay.addWidget(fit_btn)

        save_btn = PrimaryButton("Save Changes", icon_name="save")
        save_btn.setFixedHeight(28)
        save_btn.clicked.connect(self._save_manuscript)
        tb_lay.addWidget(save_btn)

        main_layout.addWidget(top_bar)

        # ------------------------------------------------------------
        # 3-Panel Splitter
        # ------------------------------------------------------------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #D9DEE7; }")

        # ------------------------------------------------------------
        # 1. Left Panel: DOCUMENT STRUCTURE
        # ------------------------------------------------------------
        self.left_sidebar = SidebarPanel(
            title="DOCUMENT STRUCTURE",
            subtitle="Outline & Chapter Navigation",
            side="left"
        )
        self.left_sidebar.setFixedWidth(260)

        # Tree Widget
        self.structure_tree = QTreeWidget()
        self.structure_tree.setHeaderHidden(True)
        self.structure_tree.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                border: none;
            }
            QTreeWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
                color: #1F2937;
            }
            QTreeWidget::item:hover {
                background-color: #E2E8F0;
            }
            QTreeWidget::item:selected {
                background-color: #EBF5FF;
                color: #168FE5;
                font-weight: 600;
            }
            QTreeWidget::branch:selected {
                background-color: transparent;
            }
            QTreeWidget::branch {
                background-color: transparent;
            }
        """)
        self.structure_tree.itemClicked.connect(self._on_tree_item_clicked)
        self._populate_structure_tree()
        self.left_sidebar.content_layout.addWidget(self.structure_tree)

        splitter.addWidget(self.left_sidebar)

        # ------------------------------------------------------------
        # 2. Center Workspace: Document Page Canvas
        # ------------------------------------------------------------
        center_scroll = QScrollArea()
        center_scroll.setWidgetResizable(True)
        center_scroll.setStyleSheet("background-color: #F4F6F8; border: none;")

        self.doc_canvas = DocumentCanvas()
        center_scroll.setWidget(self.doc_canvas)
        splitter.addWidget(center_scroll)

        # ------------------------------------------------------------
        # 3. Right Panel: FORMATTING INSPECTOR
        # ------------------------------------------------------------
        self.right_sidebar = SidebarPanel(
            title="FORMATTING INSPECTOR",
            subtitle="Global Book Typography & Margins",
            side="right"
        )
        self.right_sidebar.setFixedWidth(280)

        insp_scroll = QScrollArea()
        insp_scroll.setWidgetResizable(True)
        insp_scroll.setStyleSheet("border: none; background: transparent;")

        insp_content = QWidget()
        insp_lay = QVBoxLayout(insp_content)
        insp_lay.setContentsMargins(0, 0, 0, 0)
        insp_lay.setSpacing(12)

        # Trim Size
        insp_lay.addWidget(self._make_label("TRIM SIZE & ORIENTATION"))
        self.trim_combo = QComboBox()
        self.trim_combo.addItems([
            "5.5 × 8.5 in (Standard Trade)",
            "6.0 × 9.0 in (Royal Trade)",
            "5.0 × 8.0 in (Pocket Edition)",
            "7.0 × 10.0 in (Technical)"
        ])
        insp_lay.addWidget(self.trim_combo)

        # Typography Presets
        insp_lay.addWidget(self._make_label("TYPOGRAPHIC STYLE"))
        self.style_combo = QComboBox()
        self.style_combo.addItems([
            "Classical Garamond (Literary Fiction)",
            "Modern Caslon (Historical & Academic)",
            "Clean Georgia (General Non-Fiction)",
            "Contemporary Sans (Technical Manual)"
        ])
        insp_lay.addWidget(self.style_combo)

        # Body Font Size & Leading
        row_font = QWidget()
        rf_lay = QHBoxLayout(row_font)
        rf_lay.setContentsMargins(0, 0, 0, 0)
        rf_lay.setSpacing(8)

        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(9, 14)
        self.spin_font_size.setValue(11)
        self.spin_font_size.setPrefix("Size: ")
        self.spin_font_size.setSuffix(" pt")

        self.spin_leading = QDoubleSpinBox()
        self.spin_leading.setRange(1.1, 2.0)
        self.spin_leading.setSingleStep(0.05)
        self.spin_leading.setValue(1.25)
        self.spin_leading.setPrefix("Lead: ")

        rf_lay.addWidget(self.spin_font_size)
        rf_lay.addWidget(self.spin_leading)
        insp_lay.addWidget(row_font)

        # Margin Settings
        insp_lay.addWidget(self._make_label("PAGE MARGINS (INCHES)"))
        m_grid = QWidget()
        mg_lay = QVBoxLayout(m_grid)
        mg_lay.setContentsMargins(0, 0, 0, 0)
        mg_lay.setSpacing(6)

        # Gutter & Outside
        row_m1 = QWidget()
        rm1_lay = QHBoxLayout(row_m1)
        rm1_lay.setContentsMargins(0, 0, 0, 0)
        rm1_lay.setSpacing(8)

        self.spin_gutter = QDoubleSpinBox()
        self.spin_gutter.setRange(0.5, 1.5)
        self.spin_gutter.setSingleStep(0.05)
        self.spin_gutter.setValue(0.75)
        self.spin_gutter.setPrefix("Gutter: ")

        self.spin_outside = QDoubleSpinBox()
        self.spin_outside.setRange(0.4, 1.2)
        self.spin_outside.setSingleStep(0.05)
        self.spin_outside.setValue(0.60)
        self.spin_outside.setPrefix("Outer: ")

        rm1_lay.addWidget(self.spin_gutter)
        rm1_lay.addWidget(self.spin_outside)
        mg_lay.addWidget(row_m1)

        # Top & Bottom
        row_m2 = QWidget()
        rm2_lay = QHBoxLayout(row_m2)
        rm2_lay.setContentsMargins(0, 0, 0, 0)
        rm2_lay.setSpacing(8)

        self.spin_top = QDoubleSpinBox()
        self.spin_top.setRange(0.4, 1.5)
        self.spin_top.setSingleStep(0.05)
        self.spin_top.setValue(0.70)
        self.spin_top.setPrefix("Top: ")

        self.spin_bottom = QDoubleSpinBox()
        self.spin_bottom.setRange(0.4, 1.5)
        self.spin_bottom.setSingleStep(0.05)
        self.spin_bottom.setValue(0.70)
        self.spin_bottom.setPrefix("Bottom: ")

        rm2_lay.addWidget(self.spin_top)
        rm2_lay.addWidget(self.spin_bottom)
        mg_lay.addWidget(row_m2)
        insp_lay.addWidget(m_grid)

        # Formatting Toggles
        insp_lay.addWidget(self._make_label("ADVANCED FORMATTING RULES"))
        self.chk_drop_caps = QCheckBox("Enable Drop Caps on Chapter Openings")
        self.chk_drop_caps.setChecked(True)
        insp_lay.addWidget(self.chk_drop_caps)

        self.chk_indent = QCheckBox("First-line Paragraph Indentation")
        self.chk_indent.setChecked(True)
        insp_lay.addWidget(self.chk_indent)

        self.chk_running = QCheckBox("Running Headers && Alternate Footers")
        self.chk_running.setChecked(True)
        insp_lay.addWidget(self.chk_running)

        self.chk_hyphen = QCheckBox("Automatic Smart Hyphenation")
        self.chk_hyphen.setChecked(True)
        insp_lay.addWidget(self.chk_hyphen)

        insp_lay.addSpacing(10)

        # Repaginate button
        repag_btn = PrimaryButton("Re-paginate Manuscript", icon_name="refresh")
        repag_btn.clicked.connect(self._repaginate)
        insp_lay.addWidget(repag_btn)

        # Wire live formatting controls to canvas
        self.spin_font_size.valueChanged.connect(self._on_font_settings_changed)
        self.spin_leading.valueChanged.connect(self._on_font_settings_changed)
        self.style_combo.currentTextChanged.connect(self._on_style_preset_changed)
        self.spin_gutter.valueChanged.connect(self._on_margins_changed)
        self.spin_outside.valueChanged.connect(self._on_margins_changed)
        self.spin_top.valueChanged.connect(self._on_margins_changed)
        self.spin_bottom.valueChanged.connect(self._on_margins_changed)
        self.chk_drop_caps.toggled.connect(self.doc_canvas.set_drop_caps)
        self.chk_running.toggled.connect(self.doc_canvas.set_running_headers)

        insp_lay.addStretch()
        insp_scroll.setWidget(insp_content)
        self.right_sidebar.content_layout.addWidget(insp_scroll)

        splitter.addWidget(self.right_sidebar)

        # Set splitter proportions
        splitter.setSizes([260, 800, 280])
        main_layout.addWidget(splitter)

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B; letter-spacing: 0.8px; margin-top: 6px;")
        return lbl

    def _populate_structure_tree(self):
        self.structure_tree.clear()

        # Front Matter
        front_matter = QTreeWidgetItem(["Front Matter"])
        front_matter.setIcon(0, get_icon("book-open", color="#168FE5", size=15))
        for item_name in ["Title Page", "Copyright Page", "Dedication", "Table of Contents"]:
            child = QTreeWidgetItem([item_name])
            child.setIcon(0, get_icon("manuscript", color="#64748B", size=13))
            front_matter.addChild(child)
        self.structure_tree.addTopLevelItem(front_matter)

        # Chapter 1
        ch1 = QTreeWidgetItem(["Chapter 1: The Silent Horizon"])
        ch1.setIcon(0, get_icon("book-open", color="#168FE5", size=15))
        for sec in ["Section 1.1: The Dawn of the Journey", "Section 1.2: Threshold of Velmora"]:
            child = QTreeWidgetItem([sec])
            child.setIcon(0, get_icon("manuscript", color="#64748B", size=13))
            ch1.addChild(child)
        self.structure_tree.addTopLevelItem(ch1)

        # Chapter 2
        ch2 = QTreeWidgetItem(["Chapter 2: The Cartographer's Folio"])
        ch2.setIcon(0, get_icon("book-open", color="#168FE5", size=15))
        for sec in ["Section 2.1: The Astrological Glyphs", "Section 2.2: The Hidden Ratio"]:
            child = QTreeWidgetItem([sec])
            child.setIcon(0, get_icon("manuscript", color="#64748B", size=13))
            ch2.addChild(child)
        self.structure_tree.addTopLevelItem(ch2)

        # Chapter 3
        ch3 = QTreeWidgetItem(["Chapter 3: The Clockwork Gates"])
        ch3.setIcon(0, get_icon("book-open", color="#168FE5", size=15))
        for sec in ["Section 3.1: Gears in the Shadow"]:
            child = QTreeWidgetItem([sec])
            child.setIcon(0, get_icon("manuscript", color="#64748B", size=13))
            ch3.addChild(child)
        self.structure_tree.addTopLevelItem(ch3)

        # Back Matter
        back_matter = QTreeWidgetItem(["Back Matter"])
        back_matter.setIcon(0, get_icon("book-open", color="#168FE5", size=15))
        for item_name in ["Acknowledgments", "About the Author", "Colophon"]:
            child = QTreeWidgetItem([item_name])
            child.setIcon(0, get_icon("manuscript", color="#64748B", size=13))
            back_matter.addChild(child)
        self.structure_tree.addTopLevelItem(back_matter)

        self.structure_tree.expandAll()
        self.structure_tree.setCurrentItem(ch1.child(0))

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        text = item.text(0)
        parent = item.parent()
        parent_name = parent.text(0) if parent else "Front Matter"
        self.doc_canvas.set_content(text, parent_name)
        self.toast_requested.emit(f"Navigated to: {text}")

    def _on_zoom_changed(self, zoom: int):
        self.doc_canvas.set_zoom(zoom)

    def _repaginate(self):
        self.toast_requested.emit("✓ Offline pagination engine re-calculated 248 pages in 42ms.")

    def _save_manuscript(self):
        self.toast_requested.emit("✓ Manuscript changes saved to local project file.")

    def load_project(self, project_data: dict):
        name = project_data.get("name", "Manuscript")
        self.project_name_lbl.setText(f"{name} — Manuscript Editor")
        trim = project_data.get("trim", "")
        idx = self.trim_combo.findText(trim, Qt.MatchFlag.MatchContains)
        if idx >= 0:
            self.trim_combo.setCurrentIndex(idx)

    def _on_font_settings_changed(self):
        size = self.spin_font_size.value()
        lead = self.spin_leading.value()
        self.doc_canvas.set_font_size(size, lead)

    def _on_style_preset_changed(self, preset_text: str):
        if "Garamond" in preset_text:
            family = "Georgia"
        elif "Caslon" in preset_text:
            family = "Times New Roman"
        elif "Sans" in preset_text:
            family = "Segoe UI"
        else:
            family = "Georgia"
        self.doc_canvas.set_font_family(family)

    def _on_margins_changed(self):
        self.doc_canvas.set_margins(
            self.spin_gutter.value(),
            self.spin_outside.value(),
            self.spin_top.value(),
            self.spin_bottom.value()
        )
