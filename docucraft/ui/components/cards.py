"""
DocuCraft Card Components:
- ProjectCard
- EmptyState
- TemplateCard
- ReviewCard
- StatCard
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QProgressBar, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QCursor, QColor, QPainter, QPixmap
from ui.components.buttons import PrimaryButton, SecondaryButton, StatusBadge, IconButton
from ui.components.icons import get_pixmap, get_icon


class ProjectCard(QFrame):
    open_requested = Signal(dict)
    duplicate_requested = Signal(dict)
    export_requested = Signal(dict)

    def __init__(self, project_data: dict, parent=None):
        super().__init__(parent)
        self.project_data = project_data
        self.setObjectName("cardFrame")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            QFrame#cardFrame {
                background-color: #FFFFFF;
                border: 1px solid #D9DEE7;
                border-radius: 8px;
            }
            QFrame#cardFrame:hover {
                border-color: #168FE5;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Top row: icon, title, format badge
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        # Book icon thumbnail box
        thumb = QLabel()
        thumb.setFixedSize(40, 48)
        thumb.setStyleSheet("""
            background-color: #F1F5F9;
            border: 1px solid #E2E8F0;
            border-radius: 4px;
        """)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setPixmap(get_pixmap("manuscript", color="#168FE5", size=20))
        top_layout.addWidget(thumb)

        # Title & Subtitle
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.title_label = QLabel(project_data.get("name", "Untitled Project"))
        self.title_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #1F2937;")
        text_layout.addWidget(self.title_label)

        sub_text = f"{project_data.get('category', 'Fiction')} • Trim: {project_data.get('trim', '5.5 × 8.5 in')}"
        sub_label = QLabel(sub_text)
        sub_label.setStyleSheet("font-size: 12px; color: #64748B;")
        text_layout.addWidget(sub_label)
        top_layout.addWidget(text_widget, 1)

        # Status badge
        status = project_data.get("status", "Formatted")
        status_variant = "success" if status == "Formatted" else "suggestion"
        badge = StatusBadge(status, variant=status_variant)
        top_layout.addWidget(badge)

        layout.addWidget(top_row)

        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #F1F5F9;")
        layout.addWidget(divider)

        # Metadata Row
        meta_row = QWidget()
        meta_layout = QHBoxLayout(meta_row)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(16)

        words = QLabel(f"<b>{project_data.get('words', '0')}</b> words")
        words.setStyleSheet("font-size: 12px; color: #475569;")
        pages = QLabel(f"<b>{project_data.get('pages', '0')}</b> pages")
        pages.setStyleSheet("font-size: 12px; color: #475569;")
        updated = QLabel(f"Updated {project_data.get('updated', 'Recently')}")
        updated.setStyleSheet("font-size: 11px; color: #94A3B8;")

        meta_layout.addWidget(words)
        meta_layout.addWidget(pages)
        meta_layout.addStretch()
        meta_layout.addWidget(updated)
        layout.addWidget(meta_row)

        # Progress bar
        progress_val = project_data.get("progress", 100)
        prog_bar = QProgressBar()
        prog_bar.setFixedHeight(4)
        prog_bar.setRange(0, 100)
        prog_bar.setValue(progress_val)
        prog_bar.setTextVisible(False)
        layout.addWidget(prog_bar)

        # Actions row
        actions_row = QWidget()
        act_layout = QHBoxLayout(actions_row)
        act_layout.setContentsMargins(0, 4, 0, 0)
        act_layout.setSpacing(8)

        open_btn = PrimaryButton("Open Project", icon_name="book-open")
        open_btn.setFixedHeight(32)
        open_btn.clicked.connect(lambda: self.open_requested.emit(self.project_data))
        act_layout.addWidget(open_btn)

        dup_btn = SecondaryButton("Duplicate")
        dup_btn.setFixedHeight(32)
        dup_btn.clicked.connect(lambda: self.duplicate_requested.emit(self.project_data))
        act_layout.addWidget(dup_btn)

        act_layout.addStretch()

        export_btn = IconButton("download", tooltip="Export Book (PDF/ePub)", size=16)
        export_btn.clicked.connect(lambda: self.export_requested.emit(self.project_data))
        act_layout.addWidget(export_btn)

        layout.addWidget(actions_row)


class EmptyState(QFrame):
    action_clicked = Signal()

    def __init__(self, title: str = "No Projects Found",
                 message: str = "Create a new project to begin formatting your manuscript.",
                 button_text: str = "+ Create Your First Project",
                 icon_name: str = "book-open",
                 parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("""
            QFrame#cardFrame {
                background-color: #FFFFFF;
                border: 2px dashed #D9DEE7;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 48, 32, 48)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Big icon in soft circle
        icon_box = QLabel()
        icon_box.setFixedSize(64, 64)
        icon_box.setStyleSheet("""
            background-color: #EBF5FF;
            border-radius: 32px;
        """)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setPixmap(get_pixmap(icon_name, color="#168FE5", size=28))
        layout.addWidget(icon_box, 0, Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 600; color: #1F2937;")
        layout.addWidget(title_lbl, 0, Qt.AlignmentFlag.AlignCenter)

        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet("font-size: 13px; color: #64748B; max-width: 380px;")
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(6)

        action_btn = PrimaryButton(button_text)
        action_btn.setMinimumHeight(38)
        action_btn.clicked.connect(self.action_clicked.emit)
        layout.addWidget(action_btn, 0, Qt.AlignmentFlag.AlignCenter)


class TemplateCard(QFrame):
    use_template = Signal(dict)

    def __init__(self, template_data: dict, parent=None):
        super().__init__(parent)
        self.template_data = template_data
        self.setObjectName("cardFrame")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            QFrame#cardFrame {
                background-color: #FFFFFF;
                border: 1px solid #D9DEE7;
                border-radius: 8px;
            }
            QFrame#cardFrame:hover {
                border-color: #168FE5;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Preview snippet block resembling mini book page
        preview_box = QFrame()
        preview_box.setFixedHeight(80)
        preview_box.setStyleSheet("""
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 4px;
        """)
        prev_layout = QVBoxLayout(preview_box)
        prev_layout.setContentsMargins(12, 10, 12, 10)
        prev_layout.setSpacing(4)

        prev_title = QLabel(template_data.get("font_sample", "Chapter Title"))
        prev_title.setStyleSheet(f"font-family: {template_data.get('font_family', 'Garamond')}; font-size: 13px; font-weight: bold; color: #1E293B;")
        prev_layout.addWidget(prev_title)

        prev_body = QLabel(template_data.get("snippet", "The morning light crept through the quiet room..."))
        prev_body.setStyleSheet(f"font-family: {template_data.get('font_family', 'Garamond')}; font-size: 10px; color: #64748B;")
        prev_body.setWordWrap(True)
        prev_layout.addWidget(prev_body)
        layout.addWidget(preview_box)

        # Title & details
        name_lbl = QLabel(template_data.get("name", "Standard Template"))
        name_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #1F2937;")
        layout.addWidget(name_lbl)

        spec_lbl = QLabel(f"Trim: {template_data.get('trim', '5.5 × 8.5')} • {template_data.get('font_name', 'Garamond')}")
        spec_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        layout.addWidget(spec_lbl)

        btn = SecondaryButton("Use Template", icon_name="template")
        btn.setFixedHeight(30)
        btn.clicked.connect(lambda: self.use_template.emit(self.template_data))
        layout.addWidget(btn)


class ReviewCard(QFrame):
    review_clicked = Signal(dict)
    fix_clicked = Signal(dict)
    ignore_clicked = Signal(dict)

    def __init__(self, issue_data: dict, parent=None):
        super().__init__(parent)
        self.issue_data = issue_data
        self.setObjectName("cardFrame")

        sev = issue_data.get("severity", "Warning").lower()
        border_color = "#FADBD8" if sev == "critical" else ("#FCF3CF" if sev == "warning" else "#D4E6F1")
        self.setStyleSheet(f"""
            QFrame#cardFrame {{
                background-color: #FFFFFF;
                border: 1px solid #D9DEE7;
                border-left: 4px solid {border_color};
                border-radius: 6px;
            }}
            QFrame#cardFrame:hover {{
                border-color: #168FE5;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Top row: severity badge + location
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        badge = StatusBadge(issue_data.get("severity", "Warning"), variant=sev)
        top_layout.addWidget(badge)

        loc = QLabel(issue_data.get("location", "Page 1"))
        loc.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748B;")
        top_layout.addWidget(loc)

        top_layout.addStretch()

        type_tag = QLabel(issue_data.get("rule", "Layout Check"))
        type_tag.setStyleSheet("font-size: 11px; color: #94A3B8;")
        top_layout.addWidget(type_tag)
        layout.addWidget(top_row)

        # Title
        title = QLabel(issue_data.get("title", "Formatting anomaly detected"))
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #1F2937;")
        layout.addWidget(title)

        # Description
        desc = QLabel(issue_data.get("description", "Review formatting rule violation."))
        desc.setStyleSheet("font-size: 12px; color: #4B5563; line-height: 1.4;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Suggestion callout
        if "suggestion" in issue_data:
            sug_frame = QFrame()
            sug_frame.setStyleSheet("background-color: #F8FAFC; border-radius: 4px; padding: 6px 10px;")
            sug_layout = QHBoxLayout(sug_frame)
            sug_layout.setContentsMargins(4, 2, 4, 2)
            sug_layout.setSpacing(6)
            sug_icon = QLabel()
            sug_icon.setPixmap(get_pixmap("info", color="#168FE5", size=14))
            sug_layout.addWidget(sug_icon)
            sug_text = QLabel(f"<b>Proposed Fix:</b> {issue_data['suggestion']}")
            sug_text.setStyleSheet("font-size: 11px; color: #334155;")
            sug_layout.addWidget(sug_text, 1)
            layout.addWidget(sug_frame)

        # Action Buttons
        act_row = QWidget()
        act_layout = QHBoxLayout(act_row)
        act_layout.setContentsMargins(0, 4, 0, 0)
        act_layout.setSpacing(8)

        rev_btn = PrimaryButton("Review in Editor", icon_name="manuscript")
        rev_btn.setFixedHeight(30)
        rev_btn.clicked.connect(lambda: self.review_clicked.emit(self.issue_data))
        act_layout.addWidget(rev_btn)

        fix_btn = SecondaryButton("Auto-Fix", icon_name="check-circle")
        fix_btn.setFixedHeight(30)
        fix_btn.clicked.connect(lambda: self.fix_clicked.emit(self.issue_data))
        act_layout.addWidget(fix_btn)

        ignore_btn = IconButton("trash", tooltip="Ignore Issue", size=14)
        ignore_btn.clicked.connect(lambda: self.ignore_clicked.emit(self.issue_data))
        act_layout.addWidget(ignore_btn)

        act_layout.addStretch()
        layout.addWidget(act_row)


class StatCard(QFrame):
    def __init__(self, value: str, label: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setFixedHeight(72)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        icon_box = QLabel()
        icon_box.setFixedSize(40, 40)
        icon_box.setStyleSheet("background-color: #EBF5FF; border-radius: 6px;")
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setPixmap(get_pixmap(icon_name, color="#168FE5", size=20))
        layout.addWidget(icon_box)

        text_widget = QWidget()
        t_lay = QVBoxLayout(text_widget)
        t_lay.setContentsMargins(0, 0, 0, 0)
        t_lay.setSpacing(2)

        self.val_lbl = QLabel(value)
        self.val_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #1F2937;")
        t_lay.addWidget(self.val_lbl)

        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 500;")
        t_lay.addWidget(lbl)
        layout.addWidget(text_widget, 1)

    def set_value(self, value: str):
        self.val_lbl.setText(value)
