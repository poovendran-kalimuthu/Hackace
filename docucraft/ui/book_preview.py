"""
DocuCraft Book Preview Workspace
- LEFT: Scrollable Page Thumbnails
- CENTER: Realistic Book Page / Two-Page Spread Preview
- RIGHT: Preview Controls (Zoom, Page Navigation, Spread View Toggle, Export)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QScrollArea,
    QFrame, QPushButton, QSlider, QSpinBox, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QCursor, QColor, QPainter, QFont
from ui.components.buttons import PrimaryButton, SecondaryButton, IconButton, ZoomControl
from ui.components.icons import get_pixmap, get_icon
from ui.components.sidebar import SidebarPanel


class PageThumbnailWidget(QFrame):
    clicked = Signal(int)

    def __init__(self, page_num: int, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.page_num = page_num
        self.is_active = is_active
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(120)
        self.update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mini page sketch
        mini_page = QFrame()
        mini_page.setFixedSize(56, 80)
        mini_page.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 2px;")
        mp_lay = QVBoxLayout(mini_page)
        mp_lay.setContentsMargins(6, 6, 6, 6)
        mp_lay.setSpacing(3)

        # Lines representing text on thumbnail
        for _ in range(5):
            line = QFrame()
            line.setFixedHeight(2)
            line.setStyleSheet("background-color: #E2E8F0; border-radius: 1px;")
            mp_lay.addWidget(line)
        mp_lay.addStretch()

        layout.addWidget(mini_page, 0, Qt.AlignmentFlag.AlignCenter)

        num_lbl = QLabel(f"Page {page_num}")
        num_lbl.setStyleSheet("font-size: 11px; font-weight: 500; color: #64748B;")
        num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(num_lbl)

    def update_style(self):
        if self.is_active:
            self.setStyleSheet("""
                QFrame {
                    background-color: #EBF5FF;
                    border: 1px solid #168FE5;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #FFFFFF;
                    border: 1px solid #D9DEE7;
                    border-radius: 6px;
                }
                QFrame:hover {
                    border-color: #94A3B8;
                }
            """)

    def mousePressEvent(self, event):
        self.clicked.emit(self.page_num)
        super().mousePressEvent(event)


class BookPreviewView(QWidget):
    toast_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 12
        self.total_pages = 184
        self.zoom_factor = 1.0
        self.two_page_spread = True

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ------------------------------------------------------------
        # Top Toolbar
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

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_pixmap("preview", color="#168FE5", size=16))
        tb_lay.addWidget(icon_lbl)

        title_lbl = QLabel("Book Preview — Realistic Print & Reader Emulation")
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #1F2937;")
        tb_lay.addWidget(title_lbl)

        tb_lay.addStretch()

        # View mode toggle: Single vs Spread
        self.btn_toggle_spread = SecondaryButton("Spread View (2 Pages)")
        self.btn_toggle_spread.setFixedHeight(28)
        self.btn_toggle_spread.clicked.connect(self._toggle_spread_mode)
        tb_lay.addWidget(self.btn_toggle_spread)

        export_pdf_btn = PrimaryButton("Export PDF", icon_name="download")
        export_pdf_btn.setFixedHeight(28)
        export_pdf_btn.clicked.connect(lambda: self.toast_requested.emit("✓ High-resolution print-ready PDF generated."))
        tb_lay.addWidget(export_pdf_btn)

        main_layout.addWidget(top_bar)

        # ------------------------------------------------------------
        # 3-Panel Splitter
        # ------------------------------------------------------------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #D9DEE7; }")

        # ------------------------------------------------------------
        # 1. Left Panel: PAGE THUMBNAILS
        # ------------------------------------------------------------
        self.left_sidebar = SidebarPanel(
            title="PAGE THUMBNAILS",
            subtitle=f"{self.total_pages} Formatted Pages",
            side="left"
        )
        self.left_sidebar.setFixedWidth(200)

        thumb_scroll = QScrollArea()
        thumb_scroll.setWidgetResizable(True)
        thumb_scroll.setStyleSheet("border: none; background: transparent;")

        self.thumb_container = QWidget()
        self.tc_layout = QVBoxLayout(self.thumb_container)
        self.tc_layout.setContentsMargins(0, 0, 0, 0)
        self.tc_layout.setSpacing(8)

        self.thumbnail_widgets = []
        for p in range(1, 25):  # First 24 pages for fast smooth browsing
            tw = PageThumbnailWidget(p, is_active=(p == self.current_page))
            tw.clicked.connect(self._jump_to_page)
            self.tc_layout.addWidget(tw)
            self.thumbnail_widgets.append(tw)

        self.tc_layout.addStretch()
        thumb_scroll.setWidget(self.thumb_container)
        self.left_sidebar.content_layout.addWidget(thumb_scroll)
        splitter.addWidget(self.left_sidebar)

        # ------------------------------------------------------------
        # 2. Center: Large Book Preview Area
        # ------------------------------------------------------------
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setStyleSheet("background-color: #F4F6F8; border: none;")

        self.preview_surface = QWidget()
        self.ps_layout = QHBoxLayout(self.preview_surface)
        self.ps_layout.setContentsMargins(30, 30, 30, 30)
        self.ps_layout.setSpacing(16)
        self.ps_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Left Page
        self.left_page = self._create_book_page(is_verso=True)
        self.ps_layout.addWidget(self.left_page)

        # Right Page
        self.right_page = self._create_book_page(is_verso=False)
        self.ps_layout.addWidget(self.right_page)

        preview_scroll.setWidget(self.preview_surface)
        splitter.addWidget(preview_scroll)

        # ------------------------------------------------------------
        # 3. Right Panel: PREVIEW CONTROLS
        # ------------------------------------------------------------
        self.right_sidebar = SidebarPanel(
            title="PREVIEW CONTROLS",
            subtitle="Navigation & Print Specs",
            side="right"
        )
        self.right_sidebar.setFixedWidth(260)

        ctrl_scroll = QScrollArea()
        ctrl_scroll.setWidgetResizable(True)
        ctrl_scroll.setStyleSheet("border: none; background: transparent;")

        ctrl_content = QWidget()
        c_lay = QVBoxLayout(ctrl_content)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(14)

        # Page Navigator Section
        c_lay.addWidget(self._make_label("PAGE NAVIGATION"))
        nav_box = QFrame()
        nav_box.setStyleSheet("background-color: #FFFFFF; border: 1px solid #D9DEE7; border-radius: 6px; padding: 12px;")
        nb_lay = QVBoxLayout(nav_box)
        nb_lay.setSpacing(10)

        self.page_status_lbl = QLabel(f"Page {self.current_page} / {self.total_pages}")
        self.page_status_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #1F2937;")
        self.page_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nb_lay.addWidget(self.page_status_lbl)

        btn_row = QWidget()
        br_lay = QHBoxLayout(btn_row)
        br_lay.setContentsMargins(0, 0, 0, 0)
        br_lay.setSpacing(8)

        self.prev_btn = SecondaryButton("‹ Previous")
        self.prev_btn.clicked.connect(self._prev_page)
        br_lay.addWidget(self.prev_btn)

        self.next_btn = PrimaryButton("Next ›")
        self.next_btn.clicked.connect(self._next_page)
        br_lay.addWidget(self.next_btn)
        nb_lay.addWidget(btn_row)
        c_lay.addWidget(nav_box)

        # Zoom Controls
        c_lay.addWidget(self._make_label("ZOOM & VIEW"))
        zoom_box = QFrame()
        zoom_box.setStyleSheet("background-color: #FFFFFF; border: 1px solid #D9DEE7; border-radius: 6px; padding: 12px;")
        zb_lay = QVBoxLayout(zoom_box)
        zb_lay.setSpacing(8)

        self.zoom_ctrl = ZoomControl(default_zoom=100, min_zoom=60, max_zoom=160)
        self.zoom_ctrl.zoom_changed.connect(self._on_zoom_changed)
        zb_lay.addWidget(self.zoom_ctrl)

        fit_w_btn = SecondaryButton("Fit Width")
        fit_w_btn.clicked.connect(lambda: self.zoom_ctrl.set_zoom(110))
        zb_lay.addWidget(fit_w_btn)

        fit_p_btn = SecondaryButton("Fit Page")
        fit_p_btn.clicked.connect(lambda: self.zoom_ctrl.set_zoom(90))
        zb_lay.addWidget(fit_p_btn)
        c_lay.addWidget(zoom_box)

        # Specifications Callout
        c_lay.addWidget(self._make_label("PRINT PUBLISHING SPECS"))
        spec_box = QFrame()
        spec_box.setStyleSheet("background-color: #FFFFFF; border: 1px solid #D9DEE7; border-radius: 6px; padding: 12px;")
        sb_lay = QVBoxLayout(spec_box)
        sb_lay.setSpacing(6)

        specs = [
            ("Trim Size", "5.5 × 8.5 in"),
            ("Bleed", "0.125 in"),
            ("Color Space", "Grayscale / CMYK"),
            ("Target DPI", "300 DPI (Print standard)"),
            ("Binding", "Perfect Bound (Paperback)"),
        ]
        for k, v in specs:
            row = QWidget()
            r_lay = QHBoxLayout(row)
            r_lay.setContentsMargins(0, 0, 0, 0)
            klbl = QLabel(k)
            klbl.setStyleSheet("font-size: 11px; color: #64748B;")
            vlbl = QLabel(v)
            vlbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #1F2937;")
            r_lay.addWidget(klbl)
            r_lay.addStretch()
            r_lay.addWidget(vlbl)
            sb_lay.addWidget(row)

        c_lay.addWidget(spec_box)
        c_lay.addStretch()

        ctrl_scroll.setWidget(ctrl_content)
        self.right_sidebar.content_layout.addWidget(ctrl_scroll)
        splitter.addWidget(self.right_sidebar)

        splitter.setSizes([200, 860, 260])
        main_layout.addWidget(splitter)

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B; letter-spacing: 0.8px;")
        return lbl

    def _create_book_page(self, is_verso: bool = True) -> QFrame:
        page = QFrame()
        page.setFixedSize(380, 560)
        page.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #D9DEE7;
                border-radius: 3px;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(page)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(2 if is_verso else -2, 4)
        page.setGraphicsEffect(shadow)

        layout = QVBoxLayout(page)
        # Asymmetric gutter margins (left page has larger right margin, right page has larger left margin)
        left_m = 32 if is_verso else 44
        right_m = 44 if is_verso else 32
        layout.setContentsMargins(left_m, 32, right_m, 32)
        layout.setSpacing(10)

        # Header
        h_lbl = QLabel("DOCUCRAFT  •  THE OBSIDIAN PROTOCOL" if is_verso else "CHAPTER TWO  •  THE CROSSING")
        h_lbl.setStyleSheet("font-family: 'Georgia', serif; font-size: 9px; font-weight: 600; color: #94A3B8; letter-spacing: 1px;")
        h_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft if is_verso else Qt.AlignmentFlag.AlignRight)
        layout.addWidget(h_lbl)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #F1F5F9;")
        layout.addWidget(line)

        # Body Text paragraphs
        body_text_1 = (
            "The ancient archives did not reveal their secrets willingly. Alden spent forty days "
            "cross-referencing astronomical charts with the navigation journals of Captain Vel."
        )
        p1 = QLabel(body_text_1)
        p1.setStyleSheet("font-family: 'Georgia', serif; font-size: 11px; line-height: 1.5; color: #1E293B;")
        p1.setWordWrap(True)
        layout.addWidget(p1)

        body_text_2 = (
            "Every notation was signed with an alchemical seal indicating lunar cycles. When overlaid against "
            "the topographic surveys of the northern coastline, an unexpected correlation emerged between tidal "
            "shifts and magnetic deviations."
        )
        p2 = QLabel(body_text_2)
        p2.setStyleSheet("font-family: 'Georgia', serif; font-size: 11px; line-height: 1.5; color: #1E293B;")
        p2.setWordWrap(True)
        layout.addWidget(p2)

        body_text_3 = (
            "“There is no horizon so distant,” Vel had written, “that careful calculation cannot bring it into view.” "
            "Alden transcribed the passage into his journal with deliberate, steady strokes."
        )
        p3 = QLabel(body_text_3)
        p3.setStyleSheet("font-family: 'Georgia', serif; font-size: 11px; line-height: 1.5; color: #1E293B;")
        p3.setWordWrap(True)
        layout.addWidget(p3)

        layout.addStretch()

        # Footer Page Number
        page_num_str = str(self.current_page if is_verso else self.current_page + 1)
        f_lbl = QLabel(page_num_str)
        f_lbl.setStyleSheet("font-family: 'Georgia', serif; font-size: 11px; color: #94A3B8;")
        f_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft if is_verso else Qt.AlignmentFlag.AlignRight)
        layout.addWidget(f_lbl)

        return page

    def _toggle_spread_mode(self):
        self.two_page_spread = not self.two_page_spread
        self.left_page.setVisible(self.two_page_spread)
        self.btn_toggle_spread.setText("Spread View (2 Pages)" if self.two_page_spread else "Single Page View")
        self.toast_requested.emit("Switched to Spread View" if self.two_page_spread else "Switched to Single Page View")

    def _jump_to_page(self, page_num: int):
        self.current_page = page_num
        self.page_status_lbl.setText(f"Page {self.current_page} / {self.total_pages}")
        for tw in self.thumbnail_widgets:
            tw.is_active = (tw.page_num == page_num)
            tw.update_style()
        self.toast_requested.emit(f"Navigated to Page {page_num}")

    def _prev_page(self):
        if self.current_page > 1:
            target = max(1, self.current_page - (2 if self.two_page_spread else 1))
            self._jump_to_page(target)

    def _next_page(self):
        if self.current_page < self.total_pages:
            target = min(self.total_pages, self.current_page + (2 if self.two_page_spread else 1))
            self._jump_to_page(target)

    def _on_zoom_changed(self, zoom: int):
        factor = zoom / 100.0
        w = int(380 * factor)
        h = int(560 * factor)
        self.left_page.setFixedSize(w, h)
        self.right_page.setFixedSize(w, h)
