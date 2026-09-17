"""
Template Style Resolver.

Maps semantic block types (CHAPTER_TITLE, HEADING_1, BODY, QUOTE, CAPTION, REFERENCE, LIST)
to exact typography, spacing, indentation, and color properties.
"""

from __future__ import annotations
from typing import Dict
from backend.document.model import Block, BlockType
from backend.templates.schema import BookTemplate, ElementStyle


class StyleResolver:
    """Resolves typography, colors, and margins from a BookTemplate."""

    def __init__(self, template: BookTemplate):
        self.template = template

    def get_style(self, block_type: BlockType) -> ElementStyle:
        mapping: Dict[BlockType, str] = {
            BlockType.TITLE: "title",
            BlockType.AUTHOR: "author",
            BlockType.AFFILIATION: "author",
            BlockType.PART_TITLE: "chapter_title",
            BlockType.CHAPTER_TITLE: "chapter_title",
            BlockType.HEADING_1: "heading_1",
            BlockType.HEADING_2: "heading_2",
            BlockType.HEADING_3: "heading_3",
            BlockType.BODY: "body",
            BlockType.ABSTRACT: "abstract",
            BlockType.KEYWORDS: "body",
            BlockType.QUOTE: "quote",
            BlockType.CAPTION: "caption",
            BlockType.TABLE_CAPTION: "table_caption",
            BlockType.LIST: "list",
            BlockType.TABLE: "table",
            BlockType.IMAGE: "figure",
            BlockType.EQUATION: "equation",
            BlockType.DIAGRAM: "body",
            BlockType.CODE: "body",
            BlockType.REFERENCE: "reference",
            BlockType.TOC: "heading_1",
            BlockType.TOC_ENTRY: "list",
            BlockType.FRONT_MATTER: "heading_1",
            BlockType.BACK_MATTER: "appendix",
        }
        key = mapping.get(block_type, "body")
        return self.template.get_style_for_element(key)

    def apply_to_block(self, block: Block) -> Block:
        """Applies template typography and metrics directly onto Block attributes."""
        style = self.get_style(block.block_type)
        block.alignment = style.alignment
        block.line_spacing = style.line_spacing
        block.space_before_pt = style.space_before_pt
        block.space_after_pt = style.space_after_pt
        block.left_indent_pt = style.left_indent_pt
        block.right_indent_pt = style.right_indent_pt

        # Update runs with font properties
        for r in block.runs:
            r.font_name = style.font_family
            r.font_size_pt = style.font_size_pt
            if style.bold:
                r.bold = True
            if style.italic:
                r.italic = True
            r.color = style.color

        return block
