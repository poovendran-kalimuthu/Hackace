"""
Confidence Cascade & Difficulty Resolver.

Routes high-confidence predictions directly to rules, while dispatching
ambiguous edge cases through secondary contextual disambiguation.
"""

from __future__ import annotations
from typing import Optional, Tuple

from backend.document.model import Block, BlockType
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
        low_conf_threshold: float = 0.60,
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

        # Stage 1: High Confidence
        if conf >= self.high_conf_threshold:
            return pred_type, conf, False

        # Stage 2: Ambiguous / Edge Cases
        resolved_type, new_conf = self._resolve_ambiguity(
            block, pred_type, conf, prev_block, next_block
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
    ) -> Tuple[BlockType, float]:
        """
        Deterministic secondary contextual disambiguation for border cases.
        """
        text = block.text.strip()
        word_count = len(text.split())

        # Disambiguation Case 1: Chapter title with chapter pattern or bold/centered styling
        if pred_type == BlockType.CHAPTER_TITLE or "chapter" in text.lower()[:15]:
            if word_count <= 10:
                return BlockType.CHAPTER_TITLE, 0.95

        # Disambiguation Case 2: Short capitalized line followed by regular body
        if (
            word_count <= 8
            and not text.endswith((".", "?", "!"))
            and (next_block and next_block.block_type == BlockType.BODY)
            and (block.alignment == "CENTER" or block.runs and block.runs[0].bold)
        ):
            return BlockType.HEADING_2, 0.85

        # Disambiguation Case 2: Short line immediately beneath an image
        if prev_block and (
            prev_block.block_type == BlockType.IMAGE
            or "image_rel_ids" in prev_block.metadata
        ):
            if word_count <= 25 and not block.is_page_break:
                return BlockType.CAPTION, 0.88

        # Disambiguation Case 3: Indented short italic block
        if block.left_indent_pt > 15.0 and (
            block.runs and block.runs[0].italic
        ):
            return BlockType.QUOTE, 0.84

        return pred_type, conf
