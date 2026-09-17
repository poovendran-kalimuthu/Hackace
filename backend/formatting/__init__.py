"""
Formatting and Smart Layout Engine.

Applies semantic templates, pagination geometry, orphan/widow guards, and headers/footers.
"""

from .styles import StyleResolver
from .layout import SmartLayoutEngine, LayoutPage
from .engine import FormattingEngine

__all__ = ["StyleResolver", "SmartLayoutEngine", "LayoutPage", "FormattingEngine"]
