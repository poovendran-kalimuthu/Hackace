"""
DocuCraft Main Window
Top-level application window integrating:
- AppHeader (Fixed 56px navigation bar)
- QStackedWidget (5 primary views: Dashboard, Manuscript, Review Queue, Template Studio, Book Preview)
- Toast Notifications overlay
- Global Modals (NewProjectDialog, BenchmarkDialog)
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QIcon
from ui.components.header import AppHeader
from ui.components.dialogs import NewProjectDialog, BenchmarkDialog, ToastNotification
from ui.dashboard import DashboardView
from ui.manuscript import ManuscriptView
from ui.review_queue import ReviewQueueView
from ui.template_studio import TemplateStudioView
from ui.book_preview import BookPreviewView
from ui.components.icons import get_icon


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DocuCraft — Intelligent Offline Manuscript & Book Formatter (PRO)")
        self.resize(1440, 900)
        self.setMinimumSize(1120, 720)
        self.setWindowIcon(get_icon("book-open", color="#168FE5", size=32))

        # Central Widget & Root Layout
        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)

        self.root_layout = QVBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # ------------------------------------------------------------
        # 1. Top Navigation Header (56px)
        # ------------------------------------------------------------
        self.header = AppHeader(self)
        self.header.navigation_requested.connect(self.switch_view)
        self.root_layout.addWidget(self.header)

        # ------------------------------------------------------------
        # 2. Workspace Views (QStackedWidget)
        # ------------------------------------------------------------
        self.stacked_widget = QStackedWidget(self)

        self.dashboard_view = DashboardView(self)
        self.manuscript_view = ManuscriptView(self)
        self.review_queue_view = ReviewQueueView(self)
        self.template_studio_view = TemplateStudioView(self)
        self.book_preview_view = BookPreviewView(self)

        self.view_indices = {
            "dashboard": self.stacked_widget.addWidget(self.dashboard_view),
            "manuscript": self.stacked_widget.addWidget(self.manuscript_view),
            "review_queue": self.stacked_widget.addWidget(self.review_queue_view),
            "template_studio": self.stacked_widget.addWidget(self.template_studio_view),
            "book_preview": self.stacked_widget.addWidget(self.book_preview_view),
        }

        self.root_layout.addWidget(self.stacked_widget, 1)

        # ------------------------------------------------------------
        # 3. Inter-view Signal Connections
        # ------------------------------------------------------------
        # Dashboard signals
        self.dashboard_view.open_project_requested.connect(self._on_open_project)
        self.dashboard_view.new_project_requested.connect(self._on_new_project)
        self.dashboard_view.open_studio_requested.connect(self._on_open_studio)
        self.dashboard_view.benchmark_requested.connect(self._on_run_benchmark)

        # Manuscript signals
        self.manuscript_view.toast_requested.connect(self.show_toast)

        # Review queue signals
        self.review_queue_view.toast_requested.connect(self.show_toast)
        self.review_queue_view.navigate_editor_requested.connect(self._on_review_navigate)

        # Template studio signals
        self.template_studio_view.toast_requested.connect(self.show_toast)

        # Book preview signals
        self.book_preview_view.toast_requested.connect(self.show_toast)

        # Start on dashboard
        self.switch_view("dashboard")

    def switch_view(self, view_id: str):
        if view_id in self.view_indices:
            idx = self.view_indices[view_id]
            self.stacked_widget.setCurrentIndex(idx)
            self.header.set_active_view(view_id)

    def _on_open_project(self, project_data: dict):
        self.manuscript_view.load_project(project_data)
        self.switch_view("manuscript")
        self.show_toast(f"Opened project: {project_data.get('name')}")

    def _on_new_project(self):
        dlg = NewProjectDialog(self)
        dlg.project_created.connect(self._on_project_created)
        dlg.exec()

    def _on_project_created(self, project_data: dict):
        self.dashboard_view.add_project(project_data)
        self.manuscript_view.load_project(project_data)
        self.switch_view("manuscript")
        self.show_toast(f"✓ Project created: {project_data.get('name')}")

    def _on_open_studio(self, template_data: dict):
        self.switch_view("template_studio")
        self.show_toast(f"Loaded template: {template_data.get('name')}")

    def _on_run_benchmark(self):
        dlg = BenchmarkDialog(self)
        dlg.exec()

    def _on_review_navigate(self, issue_data: dict):
        self.switch_view("manuscript")

    def show_toast(self, message: str, icon_name: str = "check-circle"):
        """Displays floating non-blocking notification in bottom right corner."""
        toast = ToastNotification(message, icon_name=icon_name, duration_ms=3000, parent=self)
        toast.adjustSize()
        # Position 20px from bottom right
        x = self.width() - toast.width() - 24
        y = self.height() - toast.height() - 24
        toast.move(x, y)
        toast.show()
