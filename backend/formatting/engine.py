"""
Formatting Engine.

Coordinates template style application, smart pagination, and layout generation
to produce a publication-ready Formatted Document Model.
"""

from __future__ import annotations
from typing import List, Tuple

from backend.document.model import DocumentModel
from backend.templates.schema import BookTemplate
from .layout import LayoutPage, SmartLayoutEngine
from .styles import StyleResolver


class FormattingEngine:
    """
    Transforms raw or classified DocumentModel into a formatted layout stream.
    """

    def __init__(self, template: BookTemplate):
        self.template = template
        self.style_resolver = StyleResolver(template)
        self.layout_engine = SmartLayoutEngine(template)

    def format_document(self, doc: DocumentModel) -> Tuple[DocumentModel, List[LayoutPage]]:
        """
        Applies typography, margins, and pagination to the entire DocumentModel.
        """
        raw_blocks = doc.flatten_blocks()

        # Step 1: Apply template styles to each block
        formatted_blocks = [self.style_resolver.apply_to_block(b) for b in raw_blocks]
        doc.blocks = formatted_blocks

        # Step 2: Run Smart Layout & Pagination Engine
        book_title = doc.metadata.title or "Book"
        pages = self.layout_engine.paginate(formatted_blocks, book_title=book_title)

        # Step 3: Update Document Metadata
        doc.metadata.estimated_pages = len(pages)
        doc.styles = {k: v.model_dump() for k, v in self.template.styles.items()}

        return doc, pages
