"""
Automated PySide6 Unit Tests for DocuCraft Frontend
"""

import sys
import os
import unittest

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docucraft")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication, QLabel
from ui.main_window import MainWindow
from ui.components.dialogs import NewProjectDialog, BenchmarkDialog
from ui.components.icons import get_icon, get_pixmap


class TestDocuCraft(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        self.window.close()

    def test_navigation_views(self):
        """Verify all 5 primary views switch without errors."""
        views = ["dashboard", "manuscript", "review_queue", "template_studio", "book_preview"]
        for v in views:
            self.window.switch_view(v)
            self.assertEqual(self.window.header.buttons[v].isChecked(), True)

    def test_template_studio_component_addition(self):
        """Verify adding, selecting, and removing components in Template Studio."""
        studio = self.window.template_studio_view
        initial_count = len(studio.canvas.elements)

        # Add mock chapter title
        studio._on_add_component({
            "type": "Chapter Title",
            "text": "Unit Test Title",
            "font_family": "Georgia",
            "font_size": 22,
            "font_weight": "Bold",
            "alignment": "Center",
            "x": 40, "y": 60, "width": 360, "height": 45,
            "text_color": "#1F2937", "bg_color": "transparent"
        })

        self.assertEqual(len(studio.canvas.elements), initial_count + 1)
        added_widget = studio.canvas.selected_element
        self.assertIsNotNone(added_widget)
        self.assertEqual(added_widget.element_data["text"], "Unit Test Title")

        # Test inspector inspection
        self.assertEqual(studio.inspector.text_input.toPlainText(), "Unit Test Title")

        # Test element deletion
        studio._on_delete_selected_element()
        self.assertEqual(len(studio.canvas.elements), initial_count)

    def test_review_queue_filters_and_fix(self):
        """Verify Review Queue issue filtering and auto-fix behavior."""
        rq = self.window.review_queue_view
        initial_issues = len(rq.issues_data)
        self.assertGreater(initial_issues, 0)

        # Filter by critical
        rq._set_filter("critical")
        self.assertEqual(rq.current_filter, "critical")

        # Auto-fix one issue
        first_issue = rq.issues_data[0]
        rq._on_fix_issue(first_issue)
        self.assertEqual(len(rq.issues_data), initial_issues - 1)

    def test_new_project_dialog_initialization(self):
        """Verify NewProjectDialog elements and fields."""
        dlg = NewProjectDialog(self.window)
        self.assertIn(".docx", dlg.file_name_lbl.text())
        dlg.name_input.setText("Test Novel")
        self.assertEqual(dlg.name_input.text(), "Test Novel")

    def test_benchmark_dialog_initialization(self):
        """Verify BenchmarkDialog initializes cleanly."""
        dlg = BenchmarkDialog(self.window)
        self.assertIsNotNone(dlg)

    def test_icon_generation(self):
        """Verify crisp SVG pixmaps generate correctly."""
        px = get_pixmap("book-open", color="#168FE5", size=24)
        self.assertFalse(px.isNull())
        icon = get_icon("template", color="#1F2937", size=18)
        self.assertFalse(icon.isNull())


if __name__ == "__main__":
    unittest.main()
