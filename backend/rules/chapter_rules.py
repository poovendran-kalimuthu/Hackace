"""
Deterministic Chapter and Part Boundary Rules.

Ensures parts and chapters begin on clean pages, identifies Table of Contents sections
to prevent false chapter breaks, and guarantees sections and body flow naturally on the page.
"""

from __future__ import annotations
from typing import List
from backend.document.model import Block, BlockType


class ChapterBoundaryRule:
    """Validates part and chapter structures, TOC boundaries, and page-break triggers."""

    @classmethod
    def apply(cls, blocks: List[Block]) -> List[Block]:
        n = len(blocks)

        # Step 1: Detect Table of Contents block sequence
        in_toc = False
        for i in range(n):
            b = blocks[i]
            txt_clean = b.text.strip()
            txt_lower = txt_clean.lower()

            if txt_lower == "table of contents":
                b.block_type = BlockType.TOC
                b.is_page_break = True
                in_toc = True
                continue

            if in_toc:
                # The manual TOC sequence ends when the actual manuscript body begins:
                # either PART I repeats after block 30, or a block is followed by a long body paragraph (> 25 words)
                is_real_body_start = (
                    (i > 30 and txt_clean.upper().startswith("PART I:") and "FOUNDATIONS" in txt_clean.upper())
                    or (i + 1 < n and len(blocks[i + 1].text.strip().split()) > 25 and not any(blocks[i + 1].text.lower().strip().startswith(h) for h in ["chapter", "section", "part ", "subsection"]))
                )
                if is_real_body_start:
                    in_toc = False

            if in_toc:
                b.block_type = BlockType.TOC_ENTRY
                b.is_page_break = False
                continue

            # Step 2: Part titles (PART I, PART II, etc.)
            txt_upper = txt_clean.upper()
            if b.block_type == BlockType.PART_TITLE or (
                txt_upper.startswith("PART ")
                and any(txt_upper.startswith(f"PART {r}") for r in ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "1", "2", "3", "4", "5", "6"])
                and len(txt_clean.split()) <= 14
            ):
                b.block_type = BlockType.PART_TITLE
                b.is_page_break = True
                continue

            # Step 3: Chapter titles (Chapter 1, Chapter 2, etc.)
            if b.block_type == BlockType.CHAPTER_TITLE or (
                (txt_lower.startswith("chapter ") or txt_lower.startswith("prologue") or txt_lower.startswith("epilogue"))
                and len(txt_clean.split()) <= 16
            ):
                b.block_type = BlockType.CHAPTER_TITLE
                b.is_page_break = True
                continue

            # Step 4: Standalone Front/Back Matter Openings (Preface, Acknowledgements, Appendix)
            if txt_lower in ("preface", "acknowledgements") or txt_lower.startswith("appendix "):
                b.block_type = BlockType.HEADING_1
                b.is_page_break = True
                continue

            # Step 5: Sections, Subsections, Paragraphs, Equations, Tables flow naturally
            b.is_page_break = False

        return blocks
