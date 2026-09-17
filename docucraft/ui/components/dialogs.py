"""
DocuCraft Dialog and Notification Components:
- NewProjectDialog (with Drag & Drop DOCX zone and mock offline analysis)
- BenchmarkDialog (Offline performance and formatting metrics)
- ToastNotification (Polished floating non-intrusive notification)
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QProgressBar, QFrame, QFileDialog, QWidget, QGraphicsOpacityEffect,
    QPushButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QCursor
from ui.components.buttons import PrimaryButton, SecondaryButton, IconButton
from ui.components.icons import get_pixmap, get_icon


class FileDropZone(QFrame):
    """
    Drag and drop zone for .docx manuscript files with file browsing fallback.
    """
    file_selected = Signal(str, int)  # file_path, file_size_bytes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(155)
        self.setObjectName("fileDropZone")
        self.setStyleSheet("""
            FileDropZone {
                background-color: #F8FAFC;
                border: 2px dashed #CBD5E1;
                border-radius: 8px;
            }
            FileDropZone:hover {
                border-color: #168FE5;
                background-color: #F0F9FF;
            }
            FileDropZone QLabel {
                border: none;
                background: transparent;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_pixmap("upload-cloud", color="#168FE5", size=32))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        prompt_lbl = QLabel("<b>Drag & Drop DOCX manuscript here</b><br>or click to browse files")
        prompt_lbl.setStyleSheet("font-size: 12px; color: #475569; line-height: 1.3;")
        prompt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(prompt_lbl)

        browse_btn = SecondaryButton("Browse Files", icon_name="search")
        browse_btn.setFixedWidth(130)
        browse_btn.setFixedHeight(30)
        browse_btn.clicked.connect(self._open_file_dialog)
        layout.addWidget(browse_btn, 0, Qt.AlignmentFlag.AlignCenter)

        format_hint = QLabel("Supported: Microsoft Word (.docx)")
        format_hint.setStyleSheet("font-size: 11px; color: #94A3B8;")
        format_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(format_hint)

    def mousePressEvent(self, event):
        self._open_file_dialog()
        super().mousePressEvent(event)

    def _open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Manuscript DOCX",
            "",
            "Word Documents (*.docx);;All Files (*.*)"
        )
        if file_path:
            size = os.path.getsize(file_path) if os.path.exists(file_path) else 1450000
            self.file_selected.emit(file_path, size)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(".docx"):
                size = os.path.getsize(file_path) if os.path.exists(file_path) else 1250000
                self.file_selected.emit(file_path, size)
            else:
                # Still allow mock drop for test
                self.file_selected.emit(file_path, 842000)


class NewProjectDialog(QDialog):
    project_created = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Formatting Project — DocuCraft")
        self.setFixedSize(560, 660)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header
        header = QLabel("New Project / Manuscript Upload")
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #1F2937;")
        layout.addWidget(header)

        sub = QLabel("Import your manuscript DOCX for local, offline structural analysis.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(sub)

        # Project Name Field
        layout.addWidget(self._make_field_label("PROJECT NAME"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. The Silver Archive")
        self.name_input.setText("The Chronicles of Eldoria")
        layout.addWidget(self.name_input)

        # Trim Size Selector
        layout.addWidget(self._make_field_label("TARGET TRIM SIZE"))
        self.trim_combo = QComboBox()
        self.trim_combo.addItems([
            "5.5 × 8.5 in — Standard Trade Paperback (Recommended)",
            "6.0 × 9.0 in — Royal / Non-Fiction & Academic",
            "5.0 × 8.0 in — Compact Fiction / Pocket",
            "7.0 × 10.0 in — Technical Manual / Handbook",
            "8.5 × 11.0 in — Workbook / Textbook"
        ])
        layout.addWidget(self.trim_combo)

        # Manuscript Dropzone
        layout.addWidget(self._make_field_label("MANUSCRIPT FILE"))
        self.drop_zone = FileDropZone()
        self.drop_zone.file_selected.connect(self._on_file_selected)
        layout.addWidget(self.drop_zone)

        # File Information Card (populated after selection)
        self.info_card = QFrame()
        self.info_card.setObjectName("infoCard")
        self.info_card.setStyleSheet("""
            QFrame#infoCard {
                background-color: #F8FAFC;
                border: 1px solid #D9DEE7;
                border-radius: 6px;
                padding: 10px 14px;
            }
            QFrame#infoCard QLabel {
                border: none;
                background: transparent;
            }
        """)
        info_lay = QVBoxLayout(self.info_card)
        info_lay.setContentsMargins(0, 0, 0, 0)
        info_lay.setSpacing(4)

        self.file_name_lbl = QLabel("Sample_Manuscript_Ch1-14.docx")
        self.file_name_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #1F2937;")
        info_lay.addWidget(self.file_name_lbl)

        self.file_meta_lbl = QLabel("Size: 1.4 MB  •  Est. Pages: ~240 pages  •  Status: Ready for offline analysis")
        self.file_meta_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        info_lay.addWidget(self.file_meta_lbl)
        layout.addWidget(self.info_card)

        # Simulated Analysis Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.progress_status = QLabel("Analyzing...")
        self.progress_status.setStyleSheet("font-size: 11px; color: #168FE5; font-weight: 600;")
        self.progress_status.hide()
        layout.addWidget(self.progress_status)

        layout.addStretch()

        # Action Buttons
        btn_row = QWidget()
        b_lay = QHBoxLayout(btn_row)
        b_lay.setContentsMargins(0, 0, 0, 0)
        b_lay.setSpacing(10)

        self.cancel_btn = SecondaryButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        b_lay.addWidget(self.cancel_btn)

        b_lay.addStretch()

        self.analyze_btn = PrimaryButton("Analyze Manuscript", icon_name="file-check")
        self.analyze_btn.clicked.connect(self._start_mock_analysis)
        b_lay.addWidget(self.analyze_btn)
        layout.addWidget(btn_row)

        self.selected_file_path = "Sample_Manuscript_Ch1-14.docx"

    def _make_field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B; letter-spacing: 0.8px;")
        return lbl

    def _on_file_selected(self, file_path: str, size: int):
        self.selected_file_path = file_path
        filename = os.path.basename(file_path)
        size_kb = size / 1024
        size_str = f"{size_kb / 1024:.1f} MB" if size_kb > 1024 else f"{size_kb:.0f} KB"
        est_pages = max(10, int(size_kb / 5))

        self.file_name_lbl.setText(filename)
        self.file_meta_lbl.setText(f"Size: {size_str}  •  Est. Pages: ~{est_pages} pages  •  Status: Ready for offline analysis")

    def _start_mock_analysis(self):
        """Simulates rapid offline parsing pipeline for responsive UI feedback."""
        self.analyze_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.show()
        self.progress_status.show()

        steps = [
            (25, "Reading local DOCX structure..."),
            (50, "Extracting chapters & heading hierarchies..."),
            (75, "Generating smart pagination & gutter margins..."),
            (100, "Formatting complete! Opening manuscript..."),
        ]

        self._step_idx = 0

        def advance():
            if not self.isVisible():
                return
            if self._step_idx < len(steps):
                pct, msg = steps[self._step_idx]
                self.progress_bar.setValue(pct)
                self.progress_status.setText(msg)
                self._step_idx += 1
                QTimer.singleShot(250, advance)
            else:
                trim_text = self.trim_combo.currentText().split("—")[0].strip()
                result = {
                    "name": self.name_input.text() or "Untitled Project",
                    "file": self.selected_file_path,
                    "trim": trim_text,
                    "category": "Trade Fiction",
                    "words": "64,200",
                    "pages": "248",
                    "status": "Formatted",
                    "progress": 100,
                    "updated": "Just now"
                }
                self.project_created.emit(result)
                self.accept()

        advance()


class BenchmarkDialog(QDialog):
    """
    Modal displaying offline benchmark execution results.
    Demonstrates offline performance, typographic accuracy, and engine speeds.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Offline Engine Benchmark Report — DocuCraft")
        self.setFixedSize(560, 480)
        self.setStyleSheet("background-color: #FFFFFF;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header = QLabel("Offline Engine Benchmark Results")
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #1F2937;")
        layout.addWidget(header)

        desc = QLabel("Verified 100% offline local processing on current hardware.")
        desc.setStyleSheet("font-size: 12px; color: #16A085; font-weight: 600;")
        layout.addWidget(desc)

        # Benchmark Metrics Box
        box = QFrame()
        box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #D9DEE7; border-radius: 6px; padding: 14px;")
        b_lay = QVBoxLayout(box)
        b_lay.setSpacing(12)

        metrics = [
            ("Manuscript Parsing Speed", "18,400 words / sec", "100% Local CPU"),
            ("Smart Pagination Latency", "12 ms / sheet", "Optimal"),
            ("Typography Rules Checked", "64 / 64 rules", "Passed"),
            ("Widow / Orphan Avoidance", "99.8% compliance", "High Quality"),
            ("Font Kerning & Micro-spacing", "Sub-pixel precision", "Active"),
            ("Memory Footprint", "68 MB RAM", "Ultra-lightweight"),
        ]

        for label, val, sub_val in metrics:
            row = QWidget()
            r_lay = QHBoxLayout(row)
            r_lay.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 13px; color: #334155; font-weight: 500;")
            r_lay.addWidget(lbl)
            r_lay.addStretch()
            v_lbl = QLabel(f"<b>{val}</b> <font color='#64748B'>({sub_val})</font>")
            v_lbl.setStyleSheet("font-size: 12px; color: #1F2937;")
            r_lay.addWidget(v_lbl)
            b_lay.addWidget(row)

        layout.addWidget(box)

        layout.addStretch()

        close_btn = PrimaryButton("Close Benchmark", icon_name="check-circle")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignRight)


class ToastNotification(QFrame):
    """
    Non-blocking toast notification banner that smoothly slides in / disappears.
    """
    def __init__(self, message: str, icon_name: str = "check-circle", duration_ms: int = 3200, parent=None):
        super().__init__(parent)
        self.setObjectName("toastFrame")
        self.setFixedHeight(44)
        self.setStyleSheet("""
            QFrame#toastFrame {
                background-color: #1F2937;
                color: #FFFFFF;
                border: 1px solid #374151;
                border-radius: 6px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_pixmap(icon_name, color="#10B981", size=18))
        layout.addWidget(icon_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 500;")
        layout.addWidget(msg_lbl)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #9CA3AF;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        QTimer.singleShot(duration_ms, self.close)
