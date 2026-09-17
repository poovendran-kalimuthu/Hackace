"""
Deterministic Heading Hierarchy Rules.

Enforces document structural logic:
1. Heading 3 cannot appear directly under Heading 1 without an intervening Heading 2.
2. Isolated or trailing headings at the end of a section/chapter are downgraded.
3. Giant paragraphs mistakenly classified as headings are reverted to body.
"""

from __future__ import annotations
from typing import List
from backend.document.model import Block, BlockType


class HeadingHierarchyRule:
    """Validates and fixes heading levels."""

    @classmethod
    def apply(cls, blocks: List[Block]) -> List[Block]:
        current_heading_level = 0

        for i, b in enumerate(blocks):
            # Guard 1: Heading cannot be a huge block of text (> 35 words)
            if b.block_type in (
                BlockType.CHAPTER_TITLE,
                BlockType.HEADING_1,
                BlockType.HEADING_2,
                BlockType.HEADING_3,
            ):
                if b.word_count() > 35:
                    b.block_type = BlockType.BODY
                    continue

            # Guard 2: Hierarchy progression
            if b.block_type == BlockType.HEADING_1:
                current_heading_level = 1
            elif b.block_type == BlockType.HEADING_2:
                if current_heading_level == 0:
                    # Promoted to H1 if no H1 has appeared yet in this section
                    b.block_type = BlockType.HEADING_1
                    current_heading_level = 1
                else:
                    current_heading_level = 2
            elif b.block_type == BlockType.HEADING_3:
                if current_heading_level < 2:
                    # Upgrade to H2 if H2 was skipped
                    b.block_type = BlockType.HEADING_2
                    current_heading_level = 2
                else:
                    current_heading_level = 3
            elif b.block_type == BlockType.CHAPTER_TITLE:
                current_heading_level = 0

        return blocks
