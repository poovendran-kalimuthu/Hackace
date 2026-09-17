"""
DocuCraft Project Dashboard
Matches the primary reference dashboard layout:
- Header: "Intelligent Document & Book Formatter" + Subtitle
- Top Action Buttons: [ Generate Benchmark ] and [ + New Project ]
- "Recent Projects" with count, search filter, and cards or empty state
- "Built-in Formatting Templates" with [ Open Studio → ] and template cards
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QLineEdit, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from ui.components.buttons import PrimaryButton, SecondaryButton, IconButton
from ui.components.cards import ProjectCard, EmptyState, TemplateCard, StatCard
from ui.components.icons import get_pixmap, get_icon


class DashboardView(QWidget):
    open_project_requested = Signal(dict)
    new_project_requested = Signal()
    open_studio_requested = Signal(dict)
    benchmark_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_empty_state = False

        # Mock projects list
        self.projects_data = [
            {
                "name": "The Obsidian Protocol",
                "category": "Sci-Fi Fiction",
                "trim": "5.5 × 8.5 in",
                "words": "84,500",
                "pages": "318",
                "status": "Formatted",
                "progress": 100,
                "updated": "2 hours ago"
            },
            {
                "name": "Chronicles of Aethelgard",
                "category": "High Fantasy",
                "trim": "6.0 × 9.0 in",
                "words": "112,300",
                "pages": "442",
                "status": "In Review",
                "progress": 78,
                "updated": "Yesterday"
            },
            {
                "name": "Deep Learning Systems & Compilers",
                "category": "Technical Non-Fiction",
                "trim": "7.0 × 10.0 in",
                "words": "94,200",
                "pages": "380",
                "status": "Draft",
                "progress": 45,
                "updated": "3 days ago"
            }
        ]

        # Mock templates list
        self.templates_data = [
            {
                "name": "Standard Trade Fiction",
                "trim": "5.5 × 8.5 in",
                "font_name": "EB Garamond",
                "font_family": "Georgia",
                "font_sample": "Chapter 1: The Threshold",
                "snippet": "The evening settled over the ridge as the ancient bells sounded across the valley."
            },
            {
                "name": "Academic & Non-Fiction",
                "trim": "6.0 × 9.0 in",
                "font_name": "Caslon Classic",
                "font_family": "Times New Roman",
                "font_sample": "Section 2.4: Analysis",
                "snippet": "Empirical observations demonstrated consistent variance across discrete control samples."
            },
            {
                "name": "Poetry & Anthology",
                "trim": "5.0 × 8.0 in",
                "font_name": "Baskerville",
                "font_family": "Georgia",
                "font_sample": "Stanza IV: Solitude",
                "snippet": "Between the shadow and the flame, / A silence born without a name."
            },
            {
                "name": "Technical Manual",
                "trim": "7.0 × 10.0 in",
                "font_name": "Modern Sans",
                "font_family": "Segoe UI",
                "font_sample": "Module 3: Architecture",
                "snippet": "High-throughput asynchronous event handlers with sub-millisecond execution guarantees."
            }
        ]

        # Main scrollable structure
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none; background-color: #F4F6F8;")

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(40, 32, 40, 40)
        self.content_layout.setSpacing(28)

        # ------------------------------------------------------------
        # 1. Dashboard Header Section
        # ------------------------------------------------------------
        header_widget = QWidget()
        h_lay = QHBoxLayout(header_widget)
        h_lay.setContentsMargins(0, 0, 0, 0)
        h_lay.setSpacing(16)

        text_block = QWidget()
        tb_lay = QVBoxLayout(text_block)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.setSpacing(4)

        main_title = QLabel("Intelligent Document & Book Formatter")
        main_title.setStyleSheet("font-size: 24px; font-weight: 700; color: #1F2937; letter-spacing: -0.4px;")
        tb_lay.addWidget(main_title)

        subtitle = QLabel("Offline structural manuscript analysis, smart pagination, and professional layout automation.")
        subtitle.setStyleSheet("font-size: 13px; color: #64748B;")
        tb_lay.addWidget(subtitle)
        h_lay.addWidget(text_block, 1)

        # Action Buttons
        btn_container = QWidget()
        bc_lay = QHBoxLayout(btn_container)
        bc_lay.setContentsMargins(0, 0, 0, 0)
        bc_lay.setSpacing(10)

        benchmark_btn = SecondaryButton("Generate Benchmark", icon_name="sliders")
        benchmark_btn.clicked.connect(self.benchmark_requested.emit)
        bc_lay.addWidget(benchmark_btn)

        new_project_btn = PrimaryButton("+ New Project", icon_name="plus")
        new_project_btn.clicked.connect(self.new_project_requested.emit)
        bc_lay.addWidget(new_project_btn)

        h_lay.addWidget(btn_container)
        self.content_layout.addWidget(header_widget)

        # ------------------------------------------------------------
        # 2. Quick Metrics Row
        # ------------------------------------------------------------
        metrics_row = QWidget()
        m_lay = QHBoxLayout(metrics_row)
        m_lay.setContentsMargins(0, 0, 0, 0)
        m_lay.setSpacing(16)

        m_lay.addWidget(StatCard("3", "Active Projects", "projects"))
        m_lay.addWidget(StatCard("291,000", "Words Formatted", "manuscript"))
        m_lay.addWidget(StatCard("100%", "Offline Verification", "check-circle"))
        m_lay.addWidget(StatCard("0.75 in", "Standard Gutter Margin", "template"))
        self.content_layout.addWidget(metrics_row)

        # ------------------------------------------------------------
        # 3. Recent Projects Section
        # ------------------------------------------------------------
        self.projects_container = QWidget()
        self.proj_sec_layout = QVBoxLayout(self.projects_container)
        self.proj_sec_layout.setContentsMargins(0, 0, 0, 0)
        self.proj_sec_layout.setSpacing(14)

        # Title row
        p_header = QWidget()
        ph_lay = QHBoxLayout(p_header)
        ph_lay.setContentsMargins(0, 0, 0, 0)
        ph_lay.setSpacing(12)

        sec_title = QLabel("Recent Projects")
        sec_title.setObjectName("sectionHeading")
        ph_lay.addWidget(sec_title)

        self.count_badge = QLabel("3 Projects")
        self.count_badge.setStyleSheet("""
            background-color: #E2E8F0;
            color: #475569;
            font-size: 11px;
            font-weight: 600;
            border-radius: 10px;
            padding: 2px 8px;
        """)
        ph_lay.addWidget(self.count_badge)

        ph_lay.addStretch()

        # Demo toggle to switch between projects cards and empty state
        self.toggle_empty_btn = SecondaryButton("Preview Empty State")
        self.toggle_empty_btn.setFixedHeight(28)
        self.toggle_empty_btn.setStyleSheet("font-size: 11px; padding: 2px 10px;")
        self.toggle_empty_btn.clicked.connect(self._toggle_empty_state)
        ph_lay.addWidget(self.toggle_empty_btn)

        self.proj_sec_layout.addWidget(p_header)

        # Dynamic Projects Area
        self.projects_content_area = QWidget()
        self.projects_area_layout = QVBoxLayout(self.projects_content_area)
        self.projects_area_layout.setContentsMargins(0, 0, 0, 0)
        self.projects_area_layout.setSpacing(12)
        self.proj_sec_layout.addWidget(self.projects_content_area)

        self.content_layout.addWidget(self.projects_container)

        # ------------------------------------------------------------
        # 4. Built-in Formatting Templates Section
        # ------------------------------------------------------------
        templates_section = QWidget()
        t_sec_layout = QVBoxLayout(templates_section)
        t_sec_layout.setContentsMargins(0, 0, 0, 0)
        t_sec_layout.setSpacing(14)

        t_header = QWidget()
        th_lay = QHBoxLayout(t_header)
        th_lay.setContentsMargins(0, 0, 0, 0)
        th_lay.setSpacing(12)

        t_title = QLabel("Built-in Formatting Templates")
        t_title.setObjectName("sectionHeading")
        th_lay.addWidget(t_title)

        th_lay.addStretch()

        open_studio_btn = SecondaryButton("Open Studio →", icon_name="template")
        open_studio_btn.clicked.connect(lambda: self.open_studio_requested.emit(self.templates_data[0]))
        th_lay.addWidget(open_studio_btn)
        t_sec_layout.addWidget(t_header)

        # Template Cards Grid
        t_grid = QWidget()
        grid_lay = QGridLayout(t_grid)
        grid_lay.setContentsMargins(0, 0, 0, 0)
        grid_lay.setSpacing(16)

        for i, t_data in enumerate(self.templates_data):
            card = TemplateCard(t_data)
            card.use_template.connect(self.open_studio_requested.emit)
            row = i // 4
            col = i % 4
            grid_lay.addWidget(card, row, col)

        t_sec_layout.addWidget(t_grid)
        self.content_layout.addWidget(templates_section)

        self.content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        root_layout.addWidget(scroll_area)

        # Render initial project cards
        self._render_projects()

    def _render_projects(self):
        # Clear current area
        while self.projects_area_layout.count():
            item = self.projects_area_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.show_empty_state or not self.projects_data:
            empty_card = EmptyState(
                title="No Projects Found",
                message="Create a new project to begin formatting your manuscript.",
                button_text="+ Create Your First Project",
                icon_name="book-open"
            )
            empty_card.action_clicked.connect(self.new_project_requested.emit)
            self.projects_area_layout.addWidget(empty_card)
            self.count_badge.setText("0 Projects")
        else:
            cards_grid = QWidget()
            c_lay = QGridLayout(cards_grid)
            c_lay.setContentsMargins(0, 0, 0, 0)
            c_lay.setSpacing(16)

            for i, p_data in enumerate(self.projects_data):
                card = ProjectCard(p_data)
                card.open_requested.connect(self.open_project_requested.emit)
                card.duplicate_requested.connect(self._on_duplicate_project)
                card.export_requested.connect(self._on_export_project)
                row = i // 3
                col = i % 3
                c_lay.addWidget(card, row, col)

            self.projects_area_layout.addWidget(cards_grid)
            self.count_badge.setText(f"{len(self.projects_data)} Projects")

    def _toggle_empty_state(self):
        self.show_empty_state = not self.show_empty_state
        self.toggle_empty_btn.setText("Show Project Cards" if self.show_empty_state else "Preview Empty State")
        self._render_projects()

    def add_project(self, project_data: dict):
        self.projects_data.insert(0, project_data)
        self.show_empty_state = False
        self.toggle_empty_btn.setText("Preview Empty State")
        self._render_projects()

    def _on_duplicate_project(self, data: dict):
        dup = dict(data)
        dup["name"] = f"{data['name']} (Copy)"
        dup["updated"] = "Just now"
        self.add_project(dup)

    def _on_export_project(self, data: dict):
        # Notify via signal or direct handler
        self.open_project_requested.emit(data)
