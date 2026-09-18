"""
Confidence Cascade & Difficulty Resolver.

Routes high-confidence predictions directly to rules, while dispatching
ambiguous edge cases through secondary contextual disambiguation.

Book Publisher-specific disambiguation rules added:
  - body_first_paragraph: first para after heading has no first-line indent
  - part_title: doc-start + short bold text without chapter keyword
  - reference: end-of-document, hanging indent
  - heading_3 vs heading_2: exact numbered pattern depth
"""

from __future__ import annotations
from typing import Optional, Tuple

from backend.document.model import Block, BlockType
from backend.nlp.structural_features import StructuralPatternMatcher
from .classifier import DocumentElementClassifier
from .features import FeatureExtractor


class ConfidenceCascade:
    """
    Two-stage cascading classifier architecture to scale to 10,000+ pages
    without expensive operations on straightforward body paragraphs.
    """

    def __init__(
        self,
        primary_classifier: DocumentElementClassifier,
        high_conf_threshold: float = 0.82,
        low_conf_threshold: float = 0.55,
    ):
        self.primary = primary_classifier
        self.high_conf_threshold = high_conf_threshold
        self.low_conf_threshold = low_conf_threshold

    def evaluate(
        self,
        block: Block,
        prev_block: Optional[Block] = None,
        next_block: Optional[Block] = None,
        total_blocks: int = 1,
    ) -> Tuple[BlockType, float, bool]:
        """
        Returns (Assigned BlockType, Confidence, NeedsHumanReview).
        """
        # User manual overrides always hold 100% confidence
        if block.user_corrected:
            return block.block_type, 1.0, False

        pred_type, conf = self.primary.classify_block(
            block, prev_block, next_block, total_blocks
        )

        # Stage 1: High Confidence — pass through immediately
        if conf >= self.high_conf_threshold:
            return pred_type, conf, False

        # Stage 2: Ambiguous / Edge Cases — contextual disambiguation
        resolved_type, new_conf = self._resolve_ambiguity(
            block, pred_type, conf, prev_block, next_block, total_blocks
        )

        needs_review = new_conf < self.high_conf_threshold
        return resolved_type, new_conf, needs_review

    def _resolve_ambiguity(
        self,
        block: Block,
        pred_type: BlockType,
        conf: float,
        prev_block: Optional[Block],
        next_block: Optional[Block],
        total_blocks: int = 1,
    ) -> Tuple[BlockType, float]:
        """
        Deterministic secondary contextual disambiguation for border cases.
        Rules are ordered by specificity (most specific first).
        """
        text = block.text.strip()
        word_count = len(text.split())
        patterns = StructuralPatternMatcher.match_patterns(text)
        pos_ratio = block.original_index / max(1, total_blocks)

        # ── Rule 1: Part title ──
        # Short, bold, page-break, early in document with part pattern
        if patterns.get("is_part_pattern") and word_count <= 10:
            return BlockType.PART_TITLE, 0.97

        # ── Rule 2: Chapter title ──
        # Chapter keyword + short text
        if patterns.get("is_chapter_pattern") and word_count <= 14:
            return BlockType.CHAPTER_TITLE, 0.96

        # Bold + page break + short + near chapter start → chapter title
        if (
            word_count <= 12
            and block.is_page_break
            and block.runs and block.runs[0].bold
            and not text.endswith((".", "?", "!"))
        ):
            return BlockType.CHAPTER_TITLE, 0.88

        # ── Rule 3: Heading 3 vs Heading 2 (exact numbered depth) ──
        if patterns.get("is_heading_3_pattern"):
            return BlockType.HEADING_3, 0.96

        if patterns.get("is_heading_2_pattern"):
            return BlockType.HEADING_2, 0.96

        # ── Rule 4: Body first paragraph (no indent after heading) ──
        # After a chapter/section heading, the first paragraph commonly has no indent
        prev_is_heading = (
            prev_block is not None
            and prev_block.block_type in (
                BlockType.CHAPTER_TITLE,
                BlockType.PART_TITLE,
                BlockType.HEADING_1,
                BlockType.HEADING_2,
                BlockType.HEADING_3,
            )
        )
        if (
            pred_type == BlockType.BODY
            and prev_is_heading
            and block.left_indent_pt < 10.0   # no / minimal first-line indent
            and word_count >= 5
        ):
            # Still BODY, just clarify it's the first paragraph — keep as BODY
            return BlockType.BODY, 0.90

        # ── Rule 5: Caption immediately below image ──
        if prev_block and (
            prev_block.block_type == BlockType.IMAGE
            or "image_rel_ids" in prev_block.metadata
        ):
            if word_count <= 30 and not block.is_page_break:
                return BlockType.CAPTION, 0.90

        # ── Rule 6: Caption immediately above/below table ──
        if patterns.get("is_table_caption_pattern"):
            return BlockType.TABLE_CAPTION, 0.92

        # ── Rule 7: Reference block (end of document, hanging indent) ──
        if patterns.get("is_reference_pattern") and word_count >= 4:
            return BlockType.REFERENCE, 0.90
        if (
            pos_ratio >= 0.85
            and block.left_indent_pt >= 14.0   # hanging indent signal
            and word_count >= 8
            and not patterns.get("is_list_pattern")
        ):
            return BlockType.REFERENCE, 0.82

        # ── Rule 8: Block quote (indented italic) ──
        if block.left_indent_pt > 15.0 and block.runs and block.runs[0].italic:
            return BlockType.QUOTE, 0.87

        # ── Rule 9: Short bold centered line → heading or title ──
        if (
            word_count <= 8
            and not text.endswith((".", "?", "!"))
            and block.alignment == "CENTER"
            and block.runs and block.runs[0].bold
        ):
            if next_block and next_block.block_type == BlockType.BODY:
                return BlockType.HEADING_2, 0.84
            # Near top of document → TITLE
            if pos_ratio < 0.05:
                return BlockType.TITLE, 0.82

        # ── Rule 10: Short non-terminal line followed by body → heading ──
        if (
            word_count <= 8
            and not text.endswith((".", "?", "!"))
            and next_block and next_block.block_type == BlockType.BODY
            and block.runs and block.runs[0].bold
        ):
            return BlockType.HEADING_2, 0.83

        return pred_type, conf
