"""
DocuCraft Canvas Components:
- InteractivePageCanvas (Template Studio design surface)
- CanvasElementWidget (Interactive draggable & selectable block on canvas)
- DocumentCanvas (Manuscript book page view with typography and margin guides)
"""

from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize
from PySide6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont, QCursor, QMouseEvent,
    QFontMetrics
)
from ui.components.icons import get_pixmap


class CanvasElementWidget(QFrame):
    """
    Selectable, movable component block representing an element on the Template Studio canvas.
    """
    selected = Signal(object)
    modified = Signal(object)

    def __init__(self, element_data: dict, parent=None):
        super().__init__(parent)
        self.element_data = element_data
        self.is_selected = False
        self._dragging = False
        self._drag_start_pos = QPoint()

        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.update_geometry_from_data()
        self.update_styling()

    def update_geometry_from_data(self):
        x = int(self.element_data.get("x", 40))
        y = int(self.element_data.get("y", 60))
        w = int(self.element_data.get("width", 320))
        h = int(self.element_data.get("height", 60))
        self.setGeometry(x, y, w, h)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_styling()
        self.update()

    def update_styling(self):
        # Update stylesheet based on selection state and element properties
        bg = self.element_data.get("bg_color", "transparent")
        if bg == "transparent" or not bg:
            bg_css = "background-color: transparent;"
        else:
            bg_css = f"background-color: {bg};"

        if self.is_selected:
            self.setStyleSheet(f"""
                CanvasElementWidget {{
                    {bg_css}
                    border: 2px solid #168FE5;
                    border-radius: 4px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                CanvasElementWidget {{
                    {bg_css}
                    border: 1px dashed #CBD5E1;
                    border-radius: 4px;
                }}
                CanvasElementWidget:hover {{
                    border: 1px dashed #168FE5;
                }}
            """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = self.rect()
        el_type = self.element_data.get("type", "Body Text Box")
        text = self.element_data.get("text", "")
        text_color = QColor(self.element_data.get("text_color", "#1F2937"))
        font_family = self.element_data.get("font_family", "Georgia")
        font_size = int(self.element_data.get("font_size", 12))
        font_weight = self.element_data.get("font_weight", "Regular")
        align_str = self.element_data.get("alignment", "Left")

        # Convert alignment
        if align_str == "Center":
            flags = Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap
        elif align_str == "Right":
            flags = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap
        else:
            flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap

        # Font setup
        font = QFont(font_family, font_size)
        if font_weight in ("Bold", "700"):
            font.setBold(True)
        elif font_weight in ("Medium", "500", "Semibold", "600"):
            font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(text_color)

        padding = int(self.element_data.get("padding", 6))
        inner_rect = rect.adjusted(padding, padding, -padding, -padding)

        if el_type == "Image Placeholder":
            painter.setBrush(QBrush(QColor("#F1F5F9")))
            painter.setPen(QPen(QColor("#CBD5E1"), 1, Qt.PenStyle.DashLine))
            painter.drawRect(rect.adjusted(2, 2, -2, -2))
            # Draw icon and label
            px = get_pixmap("image", color="#94A3B8", size=24)
            painter.drawPixmap(rect.center().x() - 12, rect.center().y() - 20, px)
            painter.setPen(QColor("#64748B"))
            f = QFont("Segoe UI", 10)
            painter.setFont(f)
            painter.drawText(rect.adjusted(0, 16, 0, 0), Qt.AlignmentFlag.AlignCenter, text or "Image Placeholder")

        elif el_type == "Table Grid":
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.setPen(QPen(QColor("#D9DEE7"), 1))
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
            # Draw sample table grid lines
            h = rect.height()
            w = rect.width()
            painter.drawLine(1, int(h * 0.35), w - 1, int(h * 0.35))
            painter.drawLine(int(w * 0.4), 1, int(w * 0.4), h - 1)
            painter.drawLine(int(w * 0.7), 1, int(w * 0.7), h - 1)
            painter.drawText(inner_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, text or "Table Grid (3x3)")

        elif el_type == "Divider Ornament":
            cy = rect.center().y()
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.drawLine(20, cy, rect.width() - 20, cy)
            # Center diamond
            painter.setBrush(QBrush(QColor("#168FE5")))
            painter.setPen(Qt.PenStyle.NoPen)
            cx = rect.center().x()
            painter.drawEllipse(cx - 3, cy - 3, 6, 6)

        elif el_type == "Blockquote":
            # Left accent bar
            painter.setBrush(QBrush(QColor("#5B6FE8")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(padding, padding, 4, rect.height() - padding * 2, 2, 2)
            font.setItalic(True)
            painter.setFont(font)
            painter.drawText(inner_rect.adjusted(12, 0, 0, 0), flags, text)

        else:
            painter.drawText(inner_rect, flags, text)

        # Draw resize/selection handles if selected
        if self.is_selected:
            painter.setBrush(QBrush(QColor("#168FE5")))
            painter.setPen(QPen(QColor("#FFFFFF"), 1))
            handle_size = 6
            # Corners
            corners = [
                rect.topLeft(),
                rect.topRight(),
                rect.bottomLeft(),
                rect.bottomRight(),
                QPoint(rect.center().x(), rect.top()),
                QPoint(rect.center().x(), rect.bottom()),
            ]
            for pt in corners:
                painter.drawRect(pt.x() - handle_size // 2, pt.y() - handle_size // 2, handle_size, handle_size)

            # Element type tag badge above
            tag_text = el_type
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.setBrush(QBrush(QColor("#168FE5")))
            painter.setPen(Qt.PenStyle.NoPen)
            tag_w = len(tag_text) * 6 + 10
            painter.drawRoundedRect(0, 0, tag_w, 16, 3, 3)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(QRect(0, 0, tag_w, 16), Qt.AlignmentFlag.AlignCenter, tag_text)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_global = event.globalPosition().toPoint()
            self._drag_start_widget_pos = self.pos()
            self.selected.emit(self)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            diff = event.globalPosition().toPoint() - self._drag_start_global
            new_pos = self._drag_start_widget_pos + diff
            # Snap to parent bounds
            p = self.parentWidget()
            if p:
                new_pos.setX(max(10, min(p.width() - self.width() - 10, new_pos.x())))
                new_pos.setY(max(10, min(p.height() - self.height() - 10, new_pos.y())))
            self.move(new_pos)
            self.element_data["x"] = new_pos.x()
            self.element_data["y"] = new_pos.y()
            self.modified.emit(self)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._dragging = False
        super().mouseReleaseEvent(event)


class PageCanvas(QWidget):
    """
    The white page area on the canvas where components live.
    Features subtle shadow and dotted margin guides.
    """
    def __init__(self, width: int = 440, height: int = 680, parent=None):
        super().__init__(parent)
        self.page_width = width
        self.page_height = height
        self.setFixedSize(width, height)
        self.margin_top = 40
        self.margin_bottom = 40
        self.margin_left = 40
        self.margin_right = 40

        self.setStyleSheet("""
            PageCanvas {
                background-color: #FFFFFF;
                border: 1px solid #D9DEE7;
                border-radius: 4px;
            }
        """)

        # Add drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw dotted inner margin guides (light blue)
        margin_pen = QPen(QColor("#93C5FD"), 1, Qt.PenStyle.DashLine)
        painter.setPen(margin_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        guide_rect = QRect(
            self.margin_left,
            self.margin_top,
            self.width() - self.margin_left - self.margin_right,
            self.height() - self.margin_top - self.margin_bottom
        )
        painter.drawRect(guide_rect)

        # Draw subtle margin label
        painter.setPen(QColor("#94A3B8"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(self.margin_left + 4, self.margin_top - 6, "Margin Guide (0.75 in)")

        painter.end()


class InteractivePageCanvas(QWidget):
    """
    Main centered canvas in Template Studio.
    Has a light-gray workspace, centered PageCanvas, and supports zooming.
    """
    element_selected = Signal(object)
    element_modified = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.zoom_factor = 1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.page = PageCanvas(440, 680, self)
        layout.addWidget(self.page, 0, Qt.AlignmentFlag.AlignCenter)

        self.elements = []
        self.selected_element = None

    def mousePressEvent(self, event: QMouseEvent):
        # Clicking blank canvas deselects
        self.deselect_all()
        super().mousePressEvent(event)

    def deselect_all(self):
        for el in self.elements:
            el.set_selected(False)
        self.selected_element = None
        self.element_selected.emit(None)

    def add_element(self, element_data: dict) -> CanvasElementWidget:
        widget = CanvasElementWidget(element_data, self.page)
        widget.selected.connect(self._on_element_selected)
        widget.modified.connect(self._on_element_modified)
        widget.show()
        self.elements.append(widget)
        self._on_element_selected(widget)
        return widget

    def _on_element_selected(self, widget: CanvasElementWidget):
        for el in self.elements:
            el.set_selected(el == widget)
        self.selected_element = widget
        self.element_selected.emit(widget)

    def _on_element_modified(self, widget: CanvasElementWidget):
        self.element_modified.emit(widget)

    def remove_element(self, widget: CanvasElementWidget):
        if widget in self.elements:
            self.elements.remove(widget)
            widget.deleteLater()
            if self.selected_element == widget:
                self.selected_element = None
                self.element_selected.emit(None)

    def clear_elements(self):
        for el in self.elements:
            el.deleteLater()
        self.elements.clear()
        self.selected_element = None
        self.element_selected.emit(None)

    def set_zoom(self, zoom_percent: int):
        self.zoom_factor = zoom_percent / 100.0
        new_w = int(440 * self.zoom_factor)
        new_h = int(680 * self.zoom_factor)
        self.page.setFixedSize(new_w, new_h)


class DocumentCanvas(QWidget):
    """
    Manuscript Workspace Document Page Canvas.
    Displays an authentic, beautifully formatted book page with realistic typography,
    running headers, drop caps, and page footers.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.zoom_factor = 1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Page Frame
        self.page_frame = QFrame()
        self.page_frame.setFixedSize(520, 760)
        self.page_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #D9DEE7;
                border-radius: 4px;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self.page_frame)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 18))
        shadow.setOffset(0, 4)
        self.page_frame.setGraphicsEffect(shadow)

        page_layout = QVBoxLayout(self.page_frame)
        page_layout.setContentsMargins(48, 44, 48, 44)
        page_layout.setSpacing(14)

        # Running Header
        header_widget = QWidget()
        h_lay = QHBoxLayout(header_widget)
        h_lay.setContentsMargins(0, 0, 0, 0)
        self.chapter_header_lbl = QLabel("CHAPTER ONE  •  THE FIRST STEP")
        self.chapter_header_lbl.setStyleSheet("""
            font-family: 'Segoe UI', 'Inter', sans-serif;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1.5px;
            color: #94A3B8;
        """)
        h_lay.addStretch()
        h_lay.addWidget(self.chapter_header_lbl)
        h_lay.addStretch()
        page_layout.addWidget(header_widget)

        # Subtle header divider
        h_line = QFrame()
        h_line.setFixedHeight(1)
        h_line.setStyleSheet("background-color: #E2E8F0;")
        page_layout.addWidget(h_line)
        page_layout.addSpacing(10)

        # Chapter Number & Title
        self.chapter_num_lbl = QLabel("CHAPTER 1")
        self.chapter_num_lbl.setStyleSheet("""
            font-family: 'Georgia', serif;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 2px;
            color: #64748B;
        """)
        self.chapter_num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_layout.addWidget(self.chapter_num_lbl)

        self.chapter_title_lbl = QLabel("The Silent Horizon")
        self.chapter_title_lbl.setStyleSheet("""
            font-family: 'Georgia', serif;
            font-size: 26px;
            font-weight: bold;
            color: #1F2937;
            margin-bottom: 12px;
        """)
        self.chapter_title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_layout.addWidget(self.chapter_title_lbl)

        # Section Subheading
        self.section_title_lbl = QLabel("I. The Dawn of the Journey")
        self.section_title_lbl.setStyleSheet("""
            font-family: 'Georgia', serif;
            font-size: 14px;
            font-weight: 600;
            font-style: italic;
            color: #4B5563;
        """)
        page_layout.addWidget(self.section_title_lbl)

        # First Paragraph with Drop Cap styling
        p1_text = (
            "<b><font size='+3' color='#168FE5'>I</font></b>t began in the quiet hush just before dawn, "
            "when the mist still clung like spider silk across the rolling valleys. Master Alden checked "
            "the brass latches on his leather folio one final time, knowing well that the road ahead would "
            "test every theory recorded within its parchment leaves."
        )
        self.p1_lbl = QLabel(p1_text)
        self.p1_lbl.setStyleSheet("font-family: 'Georgia', serif; font-size: 13px; line-height: 1.6; color: #2D3748;")
        self.p1_lbl.setWordWrap(True)
        page_layout.addWidget(self.p1_lbl)

        # Second Paragraph
        p2_text = (
            "The manuscript had survived three generations in the archives of Velmora. To the untrained eye, "
            "its margin notes appeared to be nothing more than astrological glyphs and botanical sketches. "
            "Yet to those schooled in the classical quadrivium, each curve and stroke encoded geometric ratios "
            "of extraordinary consequence."
        )
        self.p2_lbl = QLabel(p2_text)
        self.p2_lbl.setStyleSheet("font-family: 'Georgia', serif; font-size: 13px; line-height: 1.6; color: #2D3748;")
        self.p2_lbl.setWordWrap(True)
        page_layout.addWidget(self.p2_lbl)

        # Blockquote example
        quote_frame = QFrame()
        quote_frame.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border-left: 3px solid #168FE5;
                border-radius: 2px;
                padding: 10px 14px;
            }
        """)
        q_lay = QVBoxLayout(quote_frame)
        q_lay.setContentsMargins(6, 4, 6, 4)
        quote_lbl = QLabel(
            "“Order is not an imposition of will upon chaos, but the discovery of harmony already waiting to be seen.”"
        )
        quote_lbl.setStyleSheet("font-family: 'Georgia', serif; font-style: italic; font-size: 12px; color: #4A5568;")
        quote_lbl.setWordWrap(True)
        q_lay.addWidget(quote_lbl)
        quote_author = QLabel("— Treatises of Old Altera, Book IV")
        quote_author.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 10px; color: #718096; font-weight: 500;")
        quote_author.setAlignment(Qt.AlignmentFlag.AlignRight)
        q_lay.addWidget(quote_author)
        page_layout.addWidget(quote_frame)

        # Third paragraph
        p3_text = (
            "He closed the folio, slung the strap over his travel cloak, and stepped through the threshold. "
            "Behind him, the tower bells struck six times, rolling across the stone rooftops."
        )
        self.p3_lbl = QLabel(p3_text)
        self.p3_lbl.setStyleSheet("font-family: 'Georgia', serif; font-size: 13px; line-height: 1.6; color: #2D3748;")
        self.p3_lbl.setWordWrap(True)
        page_layout.addWidget(self.p3_lbl)

        page_layout.addStretch()

        # Running Footer with Page Number
        footer_widget = QWidget()
        f_lay = QHBoxLayout(footer_widget)
        f_lay.setContentsMargins(0, 0, 0, 0)
        self.footer_lbl = QLabel("1")
        self.footer_lbl.setStyleSheet("font-family: 'Georgia', serif; font-size: 12px; color: #94A3B8;")
        f_lay.addStretch()
        f_lay.addWidget(self.footer_lbl)
        f_lay.addStretch()
        page_layout.addWidget(footer_widget)

        self.page_layout = page_layout
        self.current_font_family = "Georgia"
        self.current_font_size = 13
        self.current_leading = 1.6

        layout.addWidget(self.page_frame, 0, Qt.AlignmentFlag.AlignCenter)

    def set_content(self, section_name: str, chapter_name: str = "Chapter 1", page_num: int = 1):
        self.chapter_header_lbl.setText(f"{chapter_name.upper()}  •  {section_name.upper()}")
        self.chapter_title_lbl.setText(section_name)
        self.footer_lbl.setText(str(page_num))

    def set_zoom(self, zoom_percent: int):
        self.zoom_factor = zoom_percent / 100.0
        w = int(520 * self.zoom_factor)
        h = int(760 * self.zoom_factor)
        self.page_frame.setFixedSize(w, h)

    def set_font_size(self, size_pt: int, leading: float = 1.6):
        self.current_font_size = size_pt
        self.current_leading = leading
        self._update_paragraph_styles()

    def set_font_family(self, font_family: str):
        self.current_font_family = font_family
        self.chapter_num_lbl.setStyleSheet(f"font-family: '{font_family}', serif; font-size: 13px; font-weight: 600; letter-spacing: 2px; color: #64748B;")
        self.chapter_title_lbl.setStyleSheet(f"font-family: '{font_family}', serif; font-size: 26px; font-weight: bold; color: #1F2937; margin-bottom: 12px;")
        self.section_title_lbl.setStyleSheet(f"font-family: '{font_family}', serif; font-size: 14px; font-weight: 600; font-style: italic; color: #4B5563;")
        self._update_paragraph_styles()

    def _update_paragraph_styles(self):
        style = f"font-family: '{self.current_font_family}', serif; font-size: {self.current_font_size}px; line-height: {self.current_leading}; color: #2D3748;"
        self.p1_lbl.setStyleSheet(style)
        self.p2_lbl.setStyleSheet(style)
        self.p3_lbl.setStyleSheet(style)

    def set_margins(self, gutter: float, outside: float, top: float, bottom: float):
        scale = 64
        self.page_layout.setContentsMargins(
            int(gutter * scale),
            int(top * scale),
            int(outside * scale),
            int(bottom * scale)
        )

    def set_drop_caps(self, enabled: bool):
        if enabled:
            p1_text = (
                "<b><font size='+3' color='#168FE5'>I</font></b>t began in the quiet hush just before dawn, "
                "when the mist still clung like spider silk across the rolling valleys. Master Alden checked "
                "the brass latches on his leather folio one final time, knowing well that the road ahead would "
                "test every theory recorded within its parchment leaves."
            )
        else:
            p1_text = (
                "It began in the quiet hush just before dawn, when the mist still clung like spider silk "
                "across the rolling valleys. Master Alden checked the brass latches on his leather folio "
                "one final time, knowing well that the road ahead would test every theory recorded within its parchment leaves."
            )
        self.p1_lbl.setText(p1_text)

    def set_running_headers(self, enabled: bool):
        self.chapter_header_lbl.setVisible(enabled)
        self.footer_lbl.setVisible(enabled)
