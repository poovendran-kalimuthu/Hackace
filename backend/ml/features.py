"""
Typographical, Structural, and Syntactic Feature Extractor.

Extracts over 30 numerical and normalized features per block for
high-accuracy classification with Random Forest.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np

from backend.document.model import Block, BlockType
from backend.nlp.structural_features import StructuralPatternMatcher
from backend.nlp.tokenizer import OfflineTokenizer


class FeatureExtractor:
    """
    Computes normalized feature vectors from Block elements and surrounding context.
    """

    FEATURE_NAMES = [
        # Typography (7)
        "font_size_pt",
        "relative_font_size",
        "bold_ratio",
        "italic_ratio",
        "underline_ratio",
        "is_all_bold",
        "is_all_italic",
        # Layout & Geometry (8)
        "align_center",
        "align_right",
        "align_justify",
        "left_indent_pt",
        "right_indent_pt",
        "space_before_pt",
        "space_after_pt",
        "is_page_break",
        # Text & Linguistics (9)
        "word_count",
        "char_count",
        "uppercase_ratio",
        "digit_ratio",
        "punctuation_density",
        "avg_sentence_len",
        "is_single_sentence",
        "ends_with_colon",
        "ends_with_question",
        # Structural Patterns (7)
        "is_chapter_pattern",
        "is_numbered_heading",
        "is_figure_caption_pattern",
        "is_table_caption_pattern",
        "is_list_pattern",
        "has_quote_marks",
        "is_short_title",
        # Contextual Signals (5)
        "prev_is_heading",
        "prev_is_image",
        "prev_is_table",
        "next_is_body",
        "document_position_ratio",
    ]

    def __init__(self, median_body_font_size: float = 11.0):
        self.median_font_size = median_body_font_size

    def extract_features(
        self,
        block: Block,
        prev_block: Optional[Block] = None,
        next_block: Optional[Block] = None,
        total_blocks: int = 1,
    ) -> Dict[str, float]:
        """Extract named feature dictionary for a single block."""
        text = block.text.strip()
        text_len = len(text)

        # 1. Typography
        total_run_chars = 0
        bold_chars = 0
        italic_chars = 0
        underline_chars = 0
        max_font_size = 0.0

        for r in block.runs:
            r_len = len(r.text)
            total_run_chars += r_len
            if r.bold:
                bold_chars += r_len
            if r.italic:
                italic_chars += r_len
            if r.underline:
                underline_chars += r_len
            if r.font_size_pt and r.font_size_pt > max_font_size:
                max_font_size = r.font_size_pt

        effective_font_size = max_font_size if max_font_size > 0 else self.median_font_size
        rel_font_size = effective_font_size / max(1.0, self.median_font_size)

        divisor = max(1, total_run_chars)
        bold_ratio = bold_chars / divisor
        italic_ratio = italic_chars / divisor
        underline_ratio = underline_chars / divisor

        # 2. Layout
        align_center = 1.0 if block.alignment == "CENTER" else 0.0
        align_right = 1.0 if block.alignment == "RIGHT" else 0.0
        align_justify = 1.0 if block.alignment == "JUSTIFY" else 0.0

        # 3. Linguistics
        ling = OfflineTokenizer.extract_linguistic_stats(text)

        # 4. Pattern matches
        patterns = StructuralPatternMatcher.match_patterns(text)

        # 5. Context
        prev_is_heading = 0.0
        prev_is_img = 0.0
        prev_is_tbl = 0.0
        if prev_block:
            if prev_block.block_type in (
                BlockType.CHAPTER_TITLE,
                BlockType.HEADING_1,
                BlockType.HEADING_2,
                BlockType.HEADING_3,
            ):
                prev_is_heading = 1.0
            if prev_block.block_type == BlockType.IMAGE or "image_rel_ids" in prev_block.metadata:
                prev_is_img = 1.0
            if prev_block.block_type == BlockType.TABLE or "table_data" in prev_block.metadata:
                prev_is_tbl = 1.0

        next_is_body = 0.0
        if next_block and next_block.block_type == BlockType.BODY:
            next_is_body = 1.0

        pos_ratio = block.original_index / max(1, total_blocks)

        feat: Dict[str, float] = {
            "font_size_pt": float(effective_font_size),
            "relative_font_size": float(rel_font_size),
            "bold_ratio": float(bold_ratio),
            "italic_ratio": float(italic_ratio),
            "underline_ratio": float(underline_ratio),
            "is_all_bold": 1.0 if bold_ratio > 0.9 and text_len > 0 else 0.0,
            "is_all_italic": 1.0 if italic_ratio > 0.9 and text_len > 0 else 0.0,
            "align_center": align_center,
            "align_right": align_right,
            "align_justify": align_justify,
            "left_indent_pt": float(block.left_indent_pt),
            "right_indent_pt": float(block.right_indent_pt),
            "space_before_pt": float(block.space_before_pt),
            "space_after_pt": float(block.space_after_pt),
            "is_page_break": 1.0 if block.is_page_break else 0.0,
            "word_count": ling["word_count"],
            "char_count": ling["char_count"],
            "uppercase_ratio": ling["uppercase_ratio"],
            "digit_ratio": ling["digit_ratio"],
            "punctuation_density": ling["punctuation_density"],
            "avg_sentence_len": ling["avg_sentence_len"],
            "is_single_sentence": ling["is_single_sentence"],
            "ends_with_colon": ling["ends_with_colon"],
            "ends_with_question": ling["ends_with_question"],
            "is_chapter_pattern": patterns["is_chapter_pattern"],
            "is_numbered_heading": patterns["is_numbered_heading"],
            "is_figure_caption_pattern": patterns["is_figure_caption_pattern"],
            "is_table_caption_pattern": patterns["is_table_caption_pattern"],
            "is_list_pattern": patterns["is_list_pattern"],
            "has_quote_marks": patterns["has_quote_marks"],
            "is_short_title": patterns["is_short_title"],
            "prev_is_heading": prev_is_heading,
            "prev_is_image": prev_is_img,
            "prev_is_table": prev_is_tbl,
            "next_is_body": next_is_body,
            "document_position_ratio": float(pos_ratio),
        }
        return feat

    def extract_vector(
        self,
        block: Block,
        prev_block: Optional[Block] = None,
        next_block: Optional[Block] = None,
        total_blocks: int = 1,
    ) -> np.ndarray:
        """Extract ordered feature vector for scikit-learn model."""
        f_dict = self.extract_features(block, prev_block, next_block, total_blocks)
        return np.array([f_dict[name] for name in self.FEATURE_NAMES], dtype=np.float32)
