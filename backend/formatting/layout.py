"""
Smart Layout & Pagination Engine.

Calculates printable page geometry, handles orphan headings, manages widow/orphan text,
and coordinates chapter openings with alternate verso/recto headers.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.document.model import Block, BlockType
from backend.templates.schema import BookTemplate


class LayoutPage(BaseModel):
    page_number: int
    page_type: str = "Normal Page"  # Chapter Opening, Normal Page, Title Page, etc.
    is_recto: bool = True  # True for odd/right pages, False for even/left pages
    header_text: str = ""
    footer_text: str = ""
    blocks: List[Block] = Field(default_factory=list)
    total_height_pt: float = 0.0
    capacity_pt: float = 540.0


class SmartLayoutEngine:
    """
    Simulates physical page capacity and pagination geometry to format documents
    up to 10,000+ pages without orphan headings.
    """

    def __init__(self, template: BookTemplate):
        self.template = template
        # Calculate printable vertical area in points (72 pt per inch)
        page_h_pt = template.page.height * 72.0
        m_top_pt = template.page.margin_top_in * 72.0
        m_bot_pt = template.page.margin_bottom_in * 72.0
        self.printable_height_pt = page_h_pt - (m_top_pt + m_bot_pt)

    def estimate_block_height_pt(self, block: Block) -> float:
        """Estimates vertical footprint of a block including line spacing and margins."""
        if block.block_type == BlockType.PAGE_BREAK:
            return self.printable_height_pt

        # Estimated words per line based on trim size (~10 words per line on 5.5x8.5)
        words_per_line = max(7, int(self.template.page.width * 1.8))
        word_count = max(1, block.word_count())
        lines = math.ceil(word_count / words_per_line)

        # Base font height
        font_size = 11.0
        if block.runs and block.runs[0].font_size_pt:
            font_size = block.runs[0].font_size_pt
        elif block.block_type == BlockType.PART_TITLE:
            font_size = 18.0
        elif block.block_type == BlockType.CHAPTER_TITLE:
            font_size = 20.0
        elif block.block_type == BlockType.HEADING_1:
            font_size = 14.0
        elif block.block_type == BlockType.TOC_ENTRY:
            font_size = 10.0

        if block.block_type == BlockType.TOC_ENTRY:
            return 14.0

        if block.block_type in (BlockType.DIAGRAM, BlockType.CODE):
            line_count = max(1, len(block.text.splitlines()))
            return float(line_count * 12.0)

        if block.block_type == BlockType.EQUATION:
            return 36.0

        line_height_pt = font_size * block.line_spacing
        text_height = lines * line_height_pt
        total_height = text_height + block.space_before_pt + block.space_after_pt

        # Table or image bonus
        if block.block_type == BlockType.TABLE:
            rows = block.metadata.get("row_count", 3)
            total_height += rows * 20.0
        elif block.block_type == BlockType.IMAGE:
            total_height += 180.0

        return max(14.0, total_height)

    def paginate(self, blocks: List[Block], book_title: str = "") -> List[LayoutPage]:
        """
        Executes smart pagination with orphan prevention and chapter opening logic.
        """
        pages: List[LayoutPage] = []
        current_page_num = 1

        def new_page(is_chapter_opening: bool = False, chapter_name: str = "") -> LayoutPage:
            nonlocal current_page_num
            is_recto = (current_page_num % 2 != 0)
            page_type = "Chapter Opening" if is_chapter_opening else "Normal Page"
            tpl_pt = self.template.page_types.get(page_type)

            header = ""
            if tpl_pt and tpl_pt.show_header and not is_chapter_opening:
                header = chapter_name if is_recto else book_title

            show_pnum = True
            if tpl_pt:
                show_pnum = tpl_pt.show_page_number
            elif isinstance(self.template.footers, dict):
                p_cfg = self.template.footers.get("page_number", {})
                show_pnum = self.template.footers.get("enabled", True) and (p_cfg.get("enabled", True) if isinstance(p_cfg, dict) else True)

            p = LayoutPage(
                page_number=current_page_num,
                page_type=page_type,
                is_recto=is_recto,
                header_text=header,
                footer_text=str(current_page_num) if show_pnum else "",
                capacity_pt=self.printable_height_pt,
            )
            current_page_num += 1
            return p

        current_page = new_page(is_chapter_opening=False)
        pages.append(current_page)
        current_chapter_title = ""

        n = len(blocks)
        i = 0
        while i < n:
            b = blocks[i]
            block_h = self.estimate_block_height_pt(b)

            # Rule 1: Part and Chapter title starts a new page
            if b.block_type in (BlockType.CHAPTER_TITLE, BlockType.PART_TITLE):
                if current_page.blocks:
                    # If Part is immediately followed by Chapter, let them share the page
                    prev_is_part = len(current_page.blocks) == 1 and current_page.blocks[0].block_type == BlockType.PART_TITLE
                    if not (prev_is_part and b.block_type == BlockType.CHAPTER_TITLE):
                        current_chapter_title = b.text
                        current_page = new_page(is_chapter_opening=True, chapter_name=current_chapter_title)
                        pages.append(current_page)
                else:
                    current_page.page_type = "Chapter Opening"
                    current_chapter_title = b.text
            elif b.is_page_break and b.text.strip():
                if current_page.blocks:
                    current_page = new_page(is_chapter_opening=False, chapter_name=current_chapter_title)
                    pages.append(current_page)

            # Rule 2: Heading Orphan Guard (Keep-With-Next)
            # If a heading doesn't have room for itself PLUS at least 2 lines of text (approx 36pt), move to next page
            is_heading = b.block_type in (
                BlockType.HEADING_1,
                BlockType.HEADING_2,
                BlockType.HEADING_3,
            )
            if is_heading:
                needed_room = block_h + 36.0
                if (current_page.total_height_pt + needed_room) > current_page.capacity_pt:
                    if current_page.blocks:
                        current_page = new_page(is_chapter_opening=False, chapter_name=current_chapter_title)
                        pages.append(current_page)

            # Rule 3: Overflow to next page
            if (current_page.total_height_pt + block_h) > current_page.capacity_pt and current_page.blocks:
                current_page = new_page(is_chapter_opening=False, chapter_name=current_chapter_title)
                pages.append(current_page)

            current_page.blocks.append(b)
            current_page.total_height_pt += block_h
            i += 1

        return pages
