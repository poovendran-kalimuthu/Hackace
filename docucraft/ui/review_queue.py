"""
DocuCraft Review Queue Workspace
Displays offline automated QA inspection findings:
- Summary metrics banner (Critical, Warning, Suggestion)
- Filter tabs (All, Critical, Warning, Suggestion)
- Batch actions: [ Accept All Safe Fixes ], [ Export Report ]
- Interactive ReviewCards with [ Review in Editor ], [ Auto-Fix ], [ Ignore ]
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QPushButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from ui.components.buttons import PrimaryButton, SecondaryButton, StatusBadge
from ui.components.cards import ReviewCard, StatCard
from ui.components.icons import get_pixmap, get_icon


class ReviewQueueView(QWidget):
    toast_requested = Signal(str)
    navigate_editor_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_filter = "all"

        # Mock issues list
        self.issues_data = [
            {
                "id": "ISSUE-101",
                "severity": "Critical",
                "location": "Chapter 3 • Page 42",
                "rule": "Heading Hierarchy",
                "title": "Heading hierarchy inconsistency detected",
                "description": "Chapter 3 uses a Subsection Heading (H3) immediately following a Chapter Title (H1) without an intervening Section Heading (H2). This breaks standard publishing table-of-contents indexing.",
                "suggestion": "Promote 'The Astrological Glyphs' from H3 to H2."
            },
            {
                "id": "ISSUE-102",
                "severity": "Critical",
                "location": "Front Matter • Page 2",
                "rule": "Metadata Completeness",
                "title": "Missing copyright notice & ISBN placeholder",
                "description": "The copyright page contains author name and year but lacks publisher imprint, ISBN block, and cataloging-in-publication notice required for distribution.",
                "suggestion": "Insert standard trade paperback copyright boilerplate."
            },
            {
                "id": "ISSUE-103",
                "severity": "Warning",
                "location": "Chapter 2 • Pages 48–52",
                "rule": "Line Spacing Consistency",
                "title": "Inconsistent paragraph line spacing",
                "description": "Paragraphs across pages 48 through 52 exhibit 1.5x line height while the master template specifies 1.25x leading. This causes uneven bottom page baselines.",
                "suggestion": "Normalize paragraph leading across pages 48–52 to 1.25x."
            },
            {
                "id": "ISSUE-104",
                "severity": "Warning",
                "location": "Chapter 4 • Page 72",
                "rule": "Orphan & Widow Control",
                "title": "Orphaned single-line heading at page bottom",
                "description": "Section 4.2 heading is positioned on the last baseline of page 72 with its accompanying body paragraph starting on page 73.",
                "suggestion": "Insert soft page break before Section 4.2 heading."
            },
            {
                "id": "ISSUE-105",
                "severity": "Warning",
                "location": "Chapter 1 • Page 18",
                "rule": "Quote Formatting",
                "title": "Blockquote left margin indentation mismatch",
                "description": "Epigraph quote on page 18 uses 0.35 inch indent instead of standard 0.50 inch blockquote style.",
                "suggestion": "Standardize blockquote left margin to 0.50 in."
            },
            {
                "id": "ISSUE-106",
                "severity": "Suggestion",
                "location": "Chapter 2 • Section 2.3",
                "rule": "Text Justification",
                "title": "Unjustified body text detected",
                "description": "Three consecutive paragraphs in Section 2.3 are ragged-right aligned whereas the rest of the manuscript is fully justified.",
                "suggestion": "Convert paragraphs to full justification with hyphenation."
            },
            {
                "id": "ISSUE-107",
                "severity": "Suggestion",
                "location": "Back Matter • Page 246",
                "rule": "Typographic Polish",
                "title": "Straight double quotes found instead of typographic curly quotes",
                "description": "Found 8 occurrences of straight typewriter quotation marks (\"\") instead of typographic curly quotes (“”).",
                "suggestion": "Convert straight quotes to curly smart quotes."
            }
        ]

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area for review queue
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: #F4F6F8; border: none;")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 32, 40, 40)
        content_layout.setSpacing(20)

        # ------------------------------------------------------------
        # 1. Header Section
        # ------------------------------------------------------------
        header_row = QWidget()
        h_lay = QHBoxLayout(header_row)
        h_lay.setContentsMargins(0, 0, 0, 0)
        h_lay.setSpacing(16)

        title_block = QWidget()
        tb_lay = QVBoxLayout(title_block)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.setSpacing(4)

        main_title = QLabel("Manuscript Review Queue")
        main_title.setStyleSheet("font-size: 24px; font-weight: 700; color: #1F2937; letter-spacing: -0.4px;")
        tb_lay.addWidget(main_title)

        subtitle = QLabel("Offline automated inspection found 7 structural and typographic layout anomalies.")
        subtitle.setStyleSheet("font-size: 13px; color: #64748B;")
        tb_lay.addWidget(subtitle)
        h_lay.addWidget(title_block, 1)

        # Bulk Actions
        actions_box = QWidget()
        ab_lay = QHBoxLayout(actions_box)
        ab_lay.setContentsMargins(0, 0, 0, 0)
        ab_lay.setSpacing(10)

        report_btn = SecondaryButton("Export Issue Report", icon_name="download")
        report_btn.clicked.connect(self._export_report)
        ab_lay.addWidget(report_btn)

        accept_all_btn = PrimaryButton("Accept All Safe Fixes", icon_name="check-circle")
        accept_all_btn.clicked.connect(self._accept_all_fixes)
        ab_lay.addWidget(accept_all_btn)

        h_lay.addWidget(actions_box)
        content_layout.addWidget(header_row)

        # ------------------------------------------------------------
        # 2. Issue Metrics Summary Banner
        # ------------------------------------------------------------
        stats_row = QWidget()
        s_lay = QHBoxLayout(stats_row)
        s_lay.setContentsMargins(0, 0, 0, 0)
        s_lay.setSpacing(16)

        self.stat_total = StatCard(str(len(self.issues_data)), "Total Anomalies", "alert-circle")
        self.stat_critical = StatCard("2", "Critical Formatting Issues", "alert-triangle")
        self.stat_warning = StatCard("3", "Typographic Warnings", "info")
        self.stat_suggestion = StatCard("2", "Aesthetic Suggestions", "sliders")
        s_lay.addWidget(self.stat_total)
        s_lay.addWidget(self.stat_critical)
        s_lay.addWidget(self.stat_warning)
        s_lay.addWidget(self.stat_suggestion)
        content_layout.addWidget(stats_row)

        # ------------------------------------------------------------
        # 3. Filter Tabs Bar
        # ------------------------------------------------------------
        filter_bar = QFrame()
        filter_bar.setStyleSheet("background-color: transparent;")
        fb_lay = QHBoxLayout(filter_bar)
        fb_lay.setContentsMargins(0, 0, 0, 0)
        fb_lay.setSpacing(8)

        self.filter_buttons = {}
        filters = [
            ("all", "All Issues (7)"),
            ("critical", "Critical (2)"),
            ("warning", "Warnings (3)"),
            ("suggestion", "Suggestions (2)")
        ]

        for fid, flabel in filters:
            btn = QPushButton(flabel)
            btn.setObjectName("pageTypeTab")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            is_active = (fid == "all")
            btn.setProperty("active", "true" if is_active else "false")
            btn.clicked.connect(lambda checked=False, f=fid: self._set_filter(f))
            fb_lay.addWidget(btn)
            self.filter_buttons[fid] = btn

        fb_lay.addStretch()
        content_layout.addWidget(filter_bar)

        # ------------------------------------------------------------
        # 4. Issue Cards Container
        # ------------------------------------------------------------
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(14)
        content_layout.addWidget(self.cards_container)

        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        self._render_issue_cards()

    def _set_filter(self, filter_id: str):
        self.current_filter = filter_id
        for fid, btn in self.filter_buttons.items():
            is_act = (fid == filter_id)
            btn.setProperty("active", "true" if is_act else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._render_issue_cards()

    def _update_counts(self):
        total = len(self.issues_data)
        critical = sum(1 for i in self.issues_data if i["severity"].lower() == "critical")
        warning = sum(1 for i in self.issues_data if i["severity"].lower() == "warning")
        suggestion = sum(1 for i in self.issues_data if i["severity"].lower() == "suggestion")

        if hasattr(self, "stat_total"):
            self.stat_total.set_value(str(total))
        if hasattr(self, "stat_critical"):
            self.stat_critical.set_value(str(critical))
        if hasattr(self, "stat_warning"):
            self.stat_warning.set_value(str(warning))
        if hasattr(self, "stat_suggestion"):
            self.stat_suggestion.set_value(str(suggestion))

        if hasattr(self, "filter_buttons"):
            if "all" in self.filter_buttons:
                self.filter_buttons["all"].setText(f"All Issues ({total})")
            if "critical" in self.filter_buttons:
                self.filter_buttons["critical"].setText(f"Critical ({critical})")
            if "warning" in self.filter_buttons:
                self.filter_buttons["warning"].setText(f"Warnings ({warning})")
            if "suggestion" in self.filter_buttons:
                self.filter_buttons["suggestion"].setText(f"Suggestions ({suggestion})")

    def _render_issue_cards(self):
        self._update_counts()
        # Clear existing cards
        while self.cards_layout.count():
            child = self.cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        filtered = [
            issue for issue in self.issues_data
            if self.current_filter == "all" or issue["severity"].lower() == self.current_filter
        ]

        if not filtered:
            empty_lbl = QLabel("No issues found for this filter category.")
            empty_lbl.setStyleSheet("color: #64748B; font-size: 13px; padding: 20px;")
            self.cards_layout.addWidget(empty_lbl)
            return

        for issue in filtered:
            card = ReviewCard(issue)
            card.review_clicked.connect(self._on_review_issue)
            card.fix_clicked.connect(self._on_fix_issue)
            card.ignore_clicked.connect(self._on_ignore_issue)
            self.cards_layout.addWidget(card)

    def _on_review_issue(self, issue: dict):
        self.navigate_editor_requested.emit(issue)
        self.toast_requested.emit(f"Opening {issue['location']} in Manuscript Editor...")

    def _on_fix_issue(self, issue: dict):
        if issue in self.issues_data:
            self.issues_data.remove(issue)
            self._render_issue_cards()
            self.toast_requested.emit(f"✓ Fixed: {issue['title']}")

    def _on_ignore_issue(self, issue: dict):
        if issue in self.issues_data:
            self.issues_data.remove(issue)
            self._render_issue_cards()
            self.toast_requested.emit(f"Ignored: {issue['title']}")

    def _accept_all_fixes(self):
        fixed_count = len(self.issues_data)
        self.issues_data.clear()
        self._render_issue_cards()
        self.toast_requested.emit(f"✓ Successfully auto-fixed {fixed_count} formatting anomalies.")

    def _export_report(self):
        self.toast_requested.emit("✓ Offline QA report exported to project directory.")
