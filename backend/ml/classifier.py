"""
Hybrid Structural ML Classifier.

Employs XGBoost with multi-category feature extraction and decision explanation
for robust zero-dependency offline classification of document structural roles.
"""

from __future__ import annotations
import os
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

from backend.document.model import Block, BlockType
from backend.nlp.structural_features import StructuralPatternMatcher
from .features import FeatureExtractor


class DocumentElementClassifier:
    """
    Primary structural ML classifier for document understanding.
    Combines XGBoost with 36 typographic, linguistic, layout, and contextual features.
    """

    TARGET_CLASSES = [
        BlockType.TITLE.value,
        BlockType.AUTHOR.value,
        BlockType.PART_TITLE.value,
        BlockType.CHAPTER_TITLE.value,
        BlockType.HEADING_1.value,
        BlockType.HEADING_2.value,
        BlockType.HEADING_3.value,
        BlockType.BODY.value,
        BlockType.QUOTE.value,
        BlockType.CAPTION.value,
        BlockType.TABLE_CAPTION.value,
        BlockType.LIST.value,
        BlockType.EQUATION.value,
        BlockType.DIAGRAM.value,
        BlockType.CODE.value,
        BlockType.REFERENCE.value,
    ]

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.feature_extractor = FeatureExtractor()
        self.label_encoder = LabelEncoder()
        self.use_xgboost = HAS_XGBOOST
        self.is_trained = False

        if self.use_xgboost:
            self.classifier = XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                eval_metric="mlogloss",
                random_state=42,
            )
        else:
            self.classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=12,
                random_state=42,
                class_weight="balanced",
            )

        if model_path and os.path.exists(model_path):
            self.load(model_path)
        else:
            self._train_seed_baseline()

    def _train_seed_baseline(self) -> None:
        """
        Trains initial baseline weights from synthetic exemplar profiles
        to ensure immediate zero-dependency offline classification.
        """
        X_samples: List[List[float]] = []
        y_samples: List[str] = []

        def make_profile(overrides: Dict[str, float], label: str, repeat: int = 30):
            base = {name: 0.0 for name in FeatureExtractor.FEATURE_NAMES}
            base["relative_font_size"] = 1.0
            base["font_size_pt"] = 12.0
            base["word_count"] = 35.0
            base["char_count"] = 180.0
            base.update(overrides)
            for _ in range(repeat):
                row = []
                for n in FeatureExtractor.FEATURE_NAMES:
                    v = base[n]
                    if v > 0:
                        row.append(max(0.0, float(v + np.random.normal(0, 0.03 * v))))
                    else:
                        row.append(0.0)
                X_samples.append(row)
                y_samples.append(label)

        # 1. TITLE
        make_profile(
            {
                "relative_font_size": 2.5,
                "font_size_pt": 28.0,
                "is_all_bold": 1.0,
                "bold_ratio": 1.0,
                "align_center": 1.0,
                "word_count": 4.0,
                "is_short_title": 1.0,
                "space_before_pt": 40.0,
            },
            BlockType.TITLE.value,
            repeat=30,
        )

        # 2. AUTHOR
        make_profile(
            {
                "relative_font_size": 1.2,
                "font_size_pt": 14.0,
                "italic_ratio": 0.8,
                "align_center": 1.0,
                "word_count": 3.0,
                "space_after_pt": 24.0,
            },
            BlockType.AUTHOR.value,
            repeat=30,
        )

        # 3. CHAPTER_TITLE (Variations with/without center alignment, with/without page break)
        make_profile(
            {
                "is_chapter_pattern": 1.0,
                "relative_font_size": 2.0,
                "font_size_pt": 22.0,
                "is_all_bold": 1.0,
                "bold_ratio": 1.0,
                "word_count": 4.0,
                "align_center": 1.0,
                "is_short_title": 1.0,
            },
            BlockType.CHAPTER_TITLE.value,
            repeat=35,
        )
        make_profile(
            {
                "is_chapter_pattern": 1.0,
                "relative_font_size": 1.8,
                "font_size_pt": 20.0,
                "is_all_bold": 1.0,
                "bold_ratio": 1.0,
                "word_count": 5.0,
                "align_center": 0.0,
                "is_short_title": 1.0,
            },
            BlockType.CHAPTER_TITLE.value,
            repeat=35,
        )

        # 4. HEADING_1
        make_profile(
            {
                "is_numbered_heading": 1.0,
                "relative_font_size": 1.5,
                "font_size_pt": 16.0,
                "bold_ratio": 1.0,
                "is_all_bold": 1.0,
                "word_count": 5.0,
                "is_short_title": 1.0,
                "space_before_pt": 18.0,
            },
            BlockType.HEADING_1.value,
            repeat=35,
        )

        # 5. HEADING_2
        make_profile(
            {
                "is_numbered_heading": 1.0,
                "relative_font_size": 1.2,
                "font_size_pt": 13.0,
                "bold_ratio": 1.0,
                "is_all_bold": 1.0,
                "word_count": 6.0,
                "is_short_title": 1.0,
                "space_before_pt": 12.0,
            },
            BlockType.HEADING_2.value,
            repeat=35,
        )

        # 6. HEADING_3
        make_profile(
            {
                "relative_font_size": 1.05,
                "font_size_pt": 12.0,
                "bold_ratio": 1.0,
                "word_count": 5.0,
                "italic_ratio": 1.0,
                "is_short_title": 1.0,
            },
            BlockType.HEADING_3.value,
            repeat=30,
        )

        # 7. BODY
        make_profile(
            {
                "relative_font_size": 1.0,
                "font_size_pt": 12.0,
                "word_count": 60.0,
                "char_count": 340.0,
                "bold_ratio": 0.0,
                "align_justify": 1.0,
                "avg_sentence_len": 18.0,
            },
            BlockType.BODY.value,
            repeat=40,
        )
        make_profile(
            {
                "relative_font_size": 1.0,
                "font_size_pt": 11.0,
                "word_count": 45.0,
                "char_count": 260.0,
                "bold_ratio": 0.0,
                "align_justify": 0.0,
                "avg_sentence_len": 15.0,
            },
            BlockType.BODY.value,
            repeat=40,
        )

        # 8. QUOTE
        make_profile(
            {
                "has_quote_marks": 1.0,
                "italic_ratio": 0.9,
                "left_indent_pt": 36.0,
                "right_indent_pt": 36.0,
                "relative_font_size": 0.95,
                "word_count": 28.0,
            },
            BlockType.QUOTE.value,
            repeat=30,
        )

        # 9. CAPTION
        make_profile(
            {
                "is_figure_caption_pattern": 1.0,
                "prev_is_image": 1.0,
                "relative_font_size": 0.85,
                "font_size_pt": 10.0,
                "word_count": 8.0,
                "italic_ratio": 0.7,
                "align_center": 1.0,
            },
            BlockType.CAPTION.value,
            repeat=30,
        )

        # 10. LIST
        make_profile(
            {
                "is_list_pattern": 1.0,
                "left_indent_pt": 18.0,
                "relative_font_size": 1.0,
                "word_count": 14.0,
            },
            BlockType.LIST.value,
            repeat=30,
        )

        # 11. REFERENCE
        make_profile(
            {
                "relative_font_size": 0.9,
                "font_size_pt": 11.0,
                "word_count": 24.0,
                "left_indent_pt": 24.0,
                "is_single_sentence": 0.0,
            },
            BlockType.REFERENCE.value,
            repeat=30,
        )

        X = np.array(X_samples, dtype=np.float32)
        y_encoded = self.label_encoder.fit_transform(y_samples)

        self.classifier.fit(X, y_encoded)
        self.is_trained = True

    def classify_block(
        self,
        block: Block,
        prev_block: Optional[Block] = None,
        next_block: Optional[Block] = None,
        total_blocks: int = 1,
    ) -> Tuple[BlockType, float]:
        """
        Classifies a block and returns (Predicted BlockType, confidence score 0.0-1.0).
        """
        pred_type, conf, _ = self.classify_with_evidence(block, prev_block, next_block, total_blocks)
        return pred_type, conf

    def classify_with_evidence(
        self,
        block: Block,
        prev_block: Optional[Block] = None,
        next_block: Optional[Block] = None,
        total_blocks: int = 1,
    ) -> Tuple[BlockType, float, List[str]]:
        """
        Returns (predicted_type, confidence, evidence_list).
        Follows Section 22: Three-tier Decision System (Level 1 Rules -> Level 2 ML -> Level 3 Context).
        """
        evidence: List[str] = []

        # Level 1: Deterministic container preservation
        if block.block_type in (BlockType.TABLE, BlockType.IMAGE):
            return block.block_type, 1.0, ["Native DOCX container preservation"]
        if "table_data" in block.metadata:
            return BlockType.TABLE, 1.0, ["Embedded table cell structures"]
        if "image_rel_ids" in block.metadata and not block.text:
            return BlockType.IMAGE, 1.0, ["Embedded image relationship reference"]

        # Level 1: Deterministic publication rules
        text_strip = block.text.strip()
        words = text_strip.split()
        word_count = len(words)

        patterns = StructuralPatternMatcher.match_patterns(text_strip)

        if patterns.get("is_equation_pattern"):
            return BlockType.EQUATION, 1.0, ["Mathematical equation syntax"]

        if patterns.get("is_diagram_pattern"):
            return BlockType.DIAGRAM, 1.0, ["ASCII architecture diagram"]

        if patterns.get("is_code_pattern"):
            return BlockType.CODE, 1.0, ["Code listing syntax"]

        if patterns.get("is_figure_caption_pattern"):
            return BlockType.CAPTION, 1.0, ["Figure caption pattern"]

        if patterns.get("is_table_caption_pattern"):
            return BlockType.TABLE_CAPTION, 1.0, ["Table caption pattern"]

        if patterns.get("is_part_pattern"):
            return BlockType.PART_TITLE, 1.0, ["Part structural header"]

        if patterns.get("is_chapter_pattern"):
            return BlockType.CHAPTER_TITLE, 0.98, ["Chapter structural keyword"]

        if patterns.get("is_subsection_pattern"):
            return BlockType.HEADING_2, 0.95, ["Subsection numbered header"]

        if patterns.get("is_section_pattern"):
            return BlockType.HEADING_1, 0.95, ["Section numbered header"]

        if patterns.get("is_front_back_matter") or patterns.get("is_unnumbered_heading"):
            return BlockType.HEADING_1, 0.95, ["Structural section heading"]

        if patterns.get("is_list_pattern"):
            return BlockType.LIST, 0.95, ["List bullet or alphanumeric prefix"]

        if word_count > 30 and not patterns.get("is_list_pattern"):
            return BlockType.BODY, 0.95, ["Substantial body paragraph"]

        vec = self.feature_extractor.extract_vector(
            block, prev_block, next_block, total_blocks
        ).reshape(1, -1)

        probas = self.classifier.predict_proba(vec)[0]
        max_idx = int(np.argmax(probas))
        conf = float(probas[max_idx])
        pred_label = str(self.label_encoder.classes_[max_idx])

        # Evidence generation
        if block.runs and any(r.bold for r in block.runs):
            evidence.append("Bold typography formatting")
        if block.alignment == "CENTER":
            evidence.append("Centered document alignment")
        if any(w in block.text.lower() for w in ("chapter", "prologue", "epilogue")):
            evidence.append("Chapter structural keyword")
        if block.text and block.text[:3].strip().replace(".", "").isdigit():
            evidence.append("Numbered hierarchical heading pattern")
        if len(block.text.split()) > 40:
            evidence.append("Substantial paragraph word count")

        try:
            predicted_type = BlockType(pred_label)
        except ValueError:
            predicted_type = BlockType.UNKNOWN

        return predicted_type, round(conf, 3), evidence

    def save(self, file_path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        joblib.dump({"clf": self.classifier, "encoder": self.label_encoder}, file_path)

    def load(self, file_path: str) -> None:
        bundle = joblib.load(file_path)
        self.classifier = bundle["clf"]
        self.label_encoder = bundle["encoder"]
        self.is_trained = True
