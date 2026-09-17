"""
Deterministic Layout & Semantic Association Rules.

Associates captions to images and tables, groups multi-paragraph blockquotes,
and attaches keep-with-next rules to prevent orphan headings.
"""

from __future__ import annotations
import uuid
from typing import List
from backend.document.model import Block, BlockType


class LayoutAssociationRule:
    """Associates related elements and attaches layout constraints."""

    @classmethod
    def apply(cls, blocks: List[Block]) -> List[Block]:
        n = len(blocks)
        current_quote_group: List[Block] = []

        for i in range(n):
            b = blocks[i]

            # 1. Heading Keep-With-Next constraint
            if b.block_type in (
                BlockType.CHAPTER_TITLE,
                BlockType.HEADING_1,
                BlockType.HEADING_2,
                BlockType.HEADING_3,
            ):
                b.metadata["keep_with_next"] = True

            # 2. Image Caption Association
            if b.block_type == BlockType.CAPTION:
                # Check previous block (bottom caption)
                if i > 0:
                    prev_b = blocks[i - 1]
                    if prev_b.block_type == BlockType.IMAGE or "image_rel_ids" in prev_b.metadata:
                        b.metadata["associated_element_id"] = prev_b.id
                        prev_b.metadata["caption_id"] = b.id
                    elif prev_b.block_type == BlockType.TABLE or "table_data" in prev_b.metadata:
                        b.metadata["associated_element_id"] = prev_b.id
                        prev_b.metadata["caption_id"] = b.id
                # Check next block (top table caption)
                if i + 1 < n and "associated_element_id" not in b.metadata:
                    nxt_b = blocks[i + 1]
                    if nxt_b.block_type == BlockType.TABLE or "table_data" in nxt_b.metadata:
                        b.metadata["associated_element_id"] = nxt_b.id
                        nxt_b.metadata["caption_id"] = b.id

            # 3. Quote Grouping
            if b.block_type == BlockType.QUOTE:
                current_quote_group.append(b)
            else:
                if current_quote_group:
                    group_id = str(uuid.uuid4())[:8]
                    for qb in current_quote_group:
                        qb.metadata["quote_group_id"] = group_id
                    current_quote_group = []

        if current_quote_group:
            group_id = str(uuid.uuid4())[:8]
            for qb in current_quote_group:
                qb.metadata["quote_group_id"] = group_id

        return blocks
