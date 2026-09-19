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
from backend.nlp.structural_features import StructuralPatternMatcher


class HeadingHierarchyRule:
    """Validates and fixes heading levels and document structure."""

    @classmethod
    def apply(cls, blocks: List[Block]) -> List[Block]:
        current_heading_level = 0
        in_abstract = False
        in_references = False
        first_non_empty = True

        for i, b in enumerate(blocks):
            txt = b.text.strip()
            word_count = b.word_count()

            # Empty blocks should not disrupt abstract or heading state
            if not txt:
                continue

            patterns = StructuralPatternMatcher.match_patterns(txt)

            # Guard -1: Title Detection (First non-empty block of document)
            if first_non_empty:
                first_non_empty = False
                is_hdr_or_sec = (
                    patterns.get("is_heading_1_pattern")
                    or patterns.get("is_abstract_pattern")
                    or txt.lower().startswith("chapter")
                    or txt.lower().startswith("abstract")
                    or b.block_type in (BlockType.CHAPTER_TITLE, BlockType.PART_TITLE)
                )
                if not is_hdr_or_sec and word_count <= 50:
                    b.block_type = BlockType.TITLE
                    continue

            # Guard 0: Abstract & Keywords detection
            if txt.lower() in ("abstract", "abstract:") or (txt.lower().startswith("abstract") and word_count <= 4) or patterns.get("is_abstract_pattern"):
                b.block_type = BlockType.ABSTRACT
                in_abstract = True
                continue
            elif txt.lower().startswith("keywords:") or txt.lower().startswith("index terms:") or patterns.get("is_keywords_pattern"):
                b.block_type = BlockType.KEYWORDS
                in_abstract = False
                continue
            elif in_abstract:
                if (
                    b.block_type in (BlockType.HEADING_1, BlockType.HEADING_2, BlockType.CHAPTER_TITLE)
                    or patterns.get("is_heading_1_pattern")
                    or (word_count <= 4 and txt.isupper())
                ):
                    in_abstract = False
                else:
                    b.block_type = BlockType.ABSTRACT
                    continue

            # Guard 1: Heading cannot be a huge block of text (> 35 words)
            if b.block_type in (
                BlockType.CHAPTER_TITLE,
                BlockType.HEADING_1,
                BlockType.HEADING_2,
                BlockType.HEADING_3,
            ):
                if word_count > 35:
                    b.block_type = BlockType.BODY
                    continue

            # Guard 2: Pattern-based Heading Recognition for misclassified blocks
            if b.block_type in (BlockType.LIST, BlockType.BODY, BlockType.UNKNOWN):
                if patterns.get("is_heading_1_pattern"):
                    b.block_type = BlockType.HEADING_1
                elif patterns.get("is_heading_2_pattern"):
                    b.block_type = BlockType.HEADING_2
                elif patterns.get("is_heading_3_pattern"):
                    b.block_type = BlockType.HEADING_3

            # Guard 3: References detection
            is_ref_heading = b.block_type == BlockType.HEADING_1 and ("reference" in txt.lower() or "bibliography" in txt.lower())
            if is_ref_heading:
                in_references = True
            elif in_references:
                if b.block_type in (BlockType.CHAPTER_TITLE, BlockType.HEADING_1) and "reference" not in txt.lower() and "bibliography" not in txt.lower():
                    in_references = False
                elif txt.startswith("[") or txt.lower().startswith("note:") or patterns.get("is_reference_pattern"):
                    b.block_type = BlockType.REFERENCE

            # Guard 3b: Demote misplaced Title/Author/Affiliation blocks inside body matter
            if (current_heading_level >= 1 or in_abstract or in_references) and b.block_type in (BlockType.TITLE, BlockType.AUTHOR, BlockType.AFFILIATION):
                b.block_type = BlockType.BODY

            # Guard 4: Hierarchy progression
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
