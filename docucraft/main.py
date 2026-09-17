"""
DocuCraft — Offline AI-Powered Desktop Manuscript & Book Formatter
Main Application Entrypoint
"""

import sys
import os

# Ensure package root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette, QColor

from ui.main_window import MainWindow


def setup_light_palette(app: QApplication):
    """Enforces a crisp light theme palette regardless of OS dark mode settings."""
    app.setStyle("Fusion")

    palette = QPalette()
    # Base window & panel colors
    palette.setColor(QPalette.ColorRole.Window, QColor("#F4F6F8"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#1F2937"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#EEF1F5"))

    # Tooltips
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1F2937"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#FFFFFF"))

    # Text & Buttons
    palette.setColor(QPalette.ColorRole.Text, QColor("#1F2937"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1F2937"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#FFFFFF"))

    # Accents & Highlights
    palette.setColor(QPalette.ColorRole.Link, QColor("#168FE5"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#168FE5"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))

    app.setPalette(palette)


def load_stylesheet(app: QApplication):
    """Loads the mild professional light theme stylesheet."""
    qss_path = os.path.join(BASE_DIR, "styles", "theme.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            stylesheet = f.read()
            app.setStyleSheet(stylesheet)
    else:
        print(f"Warning: Stylesheet not found at {qss_path}")


def main():
    # High-DPI scaling configuration
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("DocuCraft")
    app.setApplicationDisplayName("DocuCraft — Intelligent Offline Document & Book Formatter")
    app.setOrganizationName("DocuCraft Publishing")

    # Set default system font with fallbacks
    default_font = QFont("Segoe UI", 10)
    default_font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(default_font)

    # Apply global light palette & stylesheet
    setup_light_palette(app)
    load_stylesheet(app)

    # Launch main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
