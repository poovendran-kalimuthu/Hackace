"""
Semantic Template System: JSON Schema definitions, template manager, and default presets.
"""

from .schema import (
    PageSizeUnit,
    PageSetup,
    ElementStyle,
    TemplateComponent,
    PageTypeLayout,
    BookTemplate,
)
from .manager import TemplateManager

__all__ = [
    "PageSizeUnit",
    "PageSetup",
    "ElementStyle",
    "TemplateComponent",
    "PageTypeLayout",
    "BookTemplate",
    "TemplateManager",
]
