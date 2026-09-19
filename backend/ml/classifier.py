"""
Hybrid Structural ML Classifier.

Employs XGBoost with multi-category feature extraction and decision explanation
for robust zero-dependency offline classification of document structural roles.

Training profiles are aligned with the Book Publisher template specification:
  - Body: 12pt TNR, justified, 1.5 spacing, 1.27cm first-line indent
  - Chapter: 16pt TNR, bold, left-aligned, page break before
  - Heading_2: 12pt TNR, bold, left-aligned (x.y numbered)
  - Heading_3: 12pt TNR, bold, left-aligned (x.y.z numbered)
  - Caption: 10pt TNR, center, small space
  - Reference: 10pt TNR, left, hanging indent
  - Quote: 11pt TNR, italic, both-side indented
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
    Combines XGBoost with 40 typographic, linguistic, layout, and contextual features.
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
        self.feature_extractor = FeatureExtractor(median_body_font_size=12.0)
        self.label_encoder = LabelEncoder()
        self.use_xgboost = HAS_XGBOOST
        self.is_trained = False

        if self.use_xgboost:
            self.classifier = XGBClassifier(
                n_estimators=200,
                max_depth=8,
                learning_rate=0.08,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_weight=2,
                gamma=0.1,
                eval_metric="mlogloss",
                random_state=42,

            )
        else:
            self.classifier = RandomForestClassifier(
                n_estimators=200,
                max_depth=16,
                min_samples_leaf=2,
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
        aligned with the Book Publisher template specification.
        """
        X_samples: List[List[float]] = []
        y_samples: List[str] = []

        def make_profile(overrides: Dict[str, float], label: str, repeat: int = 40):
            base = {name: 0.0 for name in FeatureExtractor.FEATURE_NAMES}
            # Sensible body defaults (book template: 12pt TNR, justified)
            base["relative_font_size"] = 1.0
            base["font_size_pt"] = 12.0
            base["word_count"] = 40.0
            base["char_count"] = 220.0
            base["align_justify"] = 1.0
            base.update(overrides)
            for _ in range(repeat):
                row = []
                for n in FeatureExtractor.FEATURE_NAMES:
                    v = base[n]
                    if v > 0:
                        # Small Gaussian noise for variance
                        row.append(max(0.0, float(v + np.random.normal(0, 0.04 * v))))
                    else:
                        row.append(0.0)
                X_samples.append(row)
                y_samples.append(label)

        # ─────────────────────────────────────────────
        # 1. TITLE (book: 22pt, bold, center, title page)
        # ─────────────────────────────────────────────
        make_profile(
            {
                "relative_font_size": 1.83,   # 22/12
                "font_size_pt": 22.0,
                "is_all_bold": 1.0,
                "bold_ratio": 1.0,
                "align_center": 1.0,
                "align_justify": 0.0,
                "word_count": 4.0,
                "char_count": 28.0,
                "is_short_title": 1.0,
                "space_after_pt": 8.0,
                "document_position_ratio": 0.01,
            },
            BlockType.TITLE.value,
            repeat=40,
        )

        # ─────────────────────────────────────────────
        # 2. AUTHOR (book: 14pt, bold, center, title page)
        # ─────────────────────────────────────────────
        make_profile(
            {
                "relative_font_size": 1.17,   # 14/12
                "font_size_pt": 14.0,
                "is_all_bold": 1.0,
                "bold_ratio": 1.0,
                "align_center": 1.0,
                "align_justify": 0.0,
                "word_count": 3.0,
                "char_count": 22.0,
                "is_short_title": 1.0,
                "space_before_pt": 12.0,
                "space_after_pt": 6.0,
                "document_position_ratio": 0.02,
            },
            BlockType.AUTHOR.value,
            repeat=35,
        )

        # ─────────────────────────────────────────────
        # 3. PART_TITLE (book: 18pt, bold, center, new page)
        # ─────────────────────────────────────────────
        make_profile(
            {
                "is_part_pattern": 1.0,
                "relative_font_size": 1.5,    # 18/12
                "font_size_pt": 18.0,
                "is_all_bold": 1.0,
                "bold_ratio": 1.0,
                "align_center": 1.0,
                "align_justify": 0.0,
                "word_count": 3.0,
                "char_count": 16.0,
                "is_short_title": 1.0,
                "is_page_break": 1.0,
                "space_after_pt": 18.0,
            },
            BlockType.PART_TITLE.value,
            repeat=35,
        )

        # ─────────────────────────────────────────────
        # 4. CHAPTER_TITLE (book: 16pt, bold, left OR center, new page)
        # ─────────────────────────────────────────────
        # Variation A — center-aligned (common in fiction books)
        make_profile(
            {
                "is_chapter_pattern": 1.0,
                "relative_font_size": 1.33,   # 16/12
                "font_size_pt": 16.0,
                "is_all_bold": 1.0,
                "bold_ratio": 1.0,
                "align_center": 1.0,
                "align_justify": 0.0,
                "word_count": 4.0,
                "char_count": 30.0,
                "is_short_title": 1.0,
                "is_page_break": 1.0,
                "space_after_pt": 14.0,
            },
            BlockType.CHAPTER_TITLE.value,
            repeat=50,
        )
        # Variation B — left-aligned (common in academic books)
        make_profile(
            {
                "is_chapter_pattern": 1.0,
                "relative_font_size": 1.33,
                "font_size_pt": 16.0,
                "is_all_bold": 1.0,
                "bold_ratio": 1.0,
                "align_center": 0.0,
                "align_justify": 0.0,
                "word_count": 5.0,
                "char_count": 38.0,
                "is_short_title": 1.0,
                "is_page_break": 1.0,
            },
            BlockType.CHAPTER_TITLE.value,
            repeat=50,
        )
        # Variation C — roman numeral chapter, no "Chapter" prefix sometimes
        make_profile(
            {
                "is_chapter_pattern": 1.0,
                "is_short_title": 1.0,
                "relative_font_size": 1.33,
                "font_size_pt": 16.0,
                "bold_ratio": 1.0,
                "is_all_bold": 1.0,
                "word_count": 3.0,
                "is_page_break": 1.0,
                "document_position_ratio": 0.1,
            },
            BlockType.CHAPTER_TITLE.value,
            repeat=30,
        )

        # ─────────────────────────────────────────────
        # 5. HEADING_1 (unnumbered section headings, academic books)
        # ─────────────────────────────────────────────
        make_profile(
            {
                "is_unnumbered_heading": 1.0,
                "relative_font_size": 1.33,
                "font_size_pt": 16.0,
                "bold_ratio": 1.0,
                "is_all_bold": 1.0,
                "align_center": 0.0,
                "align_justify": 0.0,
                "word_count": 4.0,
                "is_short_title": 1.0,
                "space_before_pt": 0.0,
                "space_after_pt": 14.0,
                "is_page_break": 1.0,
            },
            BlockType.HEADING_1.value,
            repeat=40,
        )

        # ─────────────────────────────────────────────
        # 6. HEADING_2 (book: x.y numbered, 12pt bold, left)
        # ─────────────────────────────────────────────
        make_profile(
            {
                "is_heading_2_pattern": 1.0,
                "is_numbered_heading": 1.0,
                "relative_font_size": 1.0,
                "font_size_pt": 12.0,
                "bold_ratio": 1.0,
                "is_all_bold": 1.0,
                "align_center": 0.0,
                "align_justify": 0.0,
                "word_count": 5.0,
                "char_count": 36.0,
                "is_short_title": 1.0,
                "space_before_pt": 12.0,
                "space_after_pt": 6.0,
            },
            BlockType.HEADING_2.value,
            repeat=50,
        )

        # ─────────────────────────────────────────────
        # 7. HEADING_3 (book: x.y.z numbered, 12pt bold, left)
        # ─────────────────────────────────────────────
        make_profile(
            {
                "is_heading_3_pattern": 1.0,
                "is_numbered_heading": 1.0,
                "relative_font_size": 1.0,
                "font_size_pt": 12.0,
                "bold_ratio": 1.0,
                "is_all_bold": 1.0,
                "align_center": 0.0,
                "align_justify": 0.0,
                "word_count": 5.0,
                "char_count": 36.0,
                "is_short_title": 1.0,
                "space_before_pt": 8.0,
                "space_after_pt": 4.0,
            },
            BlockType.HEADING_3.value,
            repeat=50,
        )

        # ─────────────────────────────────────────────
        # 8. BODY (book: 12pt, justified, 1.5 spacing, 1.27cm indent)
        #    first_line_indent_pt ≈ 36pt (1.27cm)
        # ─────────────────────────────────────────────
        make_profile(
            {
                "relative_font_size": 1.0,
                "font_size_pt": 12.0,
                "word_count": 65.0,
                "char_count": 380.0,
                "bold_ratio": 0.0,
                "italic_ratio": 0.0,
                "align_justify": 1.0,
                "align_center": 0.0,
                "avg_sentence_len": 20.0,
                "space_before_pt": 0.0,
                "space_after_pt": 0.0,
                "left_indent_pt": 36.0,   # 1.27cm ≈ 36pt first-line indent
            },
            BlockType.BODY.value,
            repeat=60,
        )
        # Shorter body paragraphs
        make_profile(
            {
                "relative_font_size": 1.0,
                "font_size_pt": 12.0,
                "word_count": 30.0,
                "char_count": 175.0,
                "bold_ratio": 0.0,
                "align_justify": 1.0,
                "avg_sentence_len": 15.0,
                "left_indent_pt": 36.0,
            },
            BlockType.BODY.value,
            repeat=40,
        )
        # Very long body paragraphs (10k+ page documents)
        make_profile(
            {
                "relative_font_size": 1.0,
                "font_size_pt": 12.0,
                "word_count": 120.0,
                "char_count": 720.0,
                "bold_ratio": 0.0,
                "align_justify": 1.0,
                "avg_sentence_len": 22.0,
            },
            BlockType.BODY.value,
            repeat=30,
        )

        # ─────────────────────────────────────────────
        # 9. QUOTE (book: 11pt italic, both-side 1cm indent)
        #    1cm = ~28.35pt indent on each side
        # ─────────────────────────────────────────────
        make_profile(
            {
                "has_quote_marks": 1.0,
                "italic_ratio": 0.9,
                "is_all_italic": 1.0,
                "left_indent_pt": 28.0,
                "right_indent_pt": 28.0,
                "relative_font_size": 0.917,  # 11/12
                "font_size_pt": 11.0,
                "word_count": 30.0,
                "char_count": 175.0,
                "space_before_pt": 6.0,
                "space_after_pt": 6.0,
                "align_justify": 1.0,
            },
            BlockType.QUOTE.value,
            repeat=35,
        )
        # Block quotes without explicit quote marks
        make_profile(
            {
                "italic_ratio": 0.85,
                "left_indent_pt": 28.0,
                "right_indent_pt": 28.0,
                "relative_font_size": 0.917,
                "font_size_pt": 11.0,
                "word_count": 25.0,
            },
            BlockType.QUOTE.value,
            repeat=25,
        )

        # ─────────────────────────────────────────────
        # 10. CAPTION (Figure caption: 10pt, center, below image)
        # ─────────────────────────────────────────────
        make_profile(
            {
                "is_figure_caption_pattern": 1.0,
                "prev_is_image": 1.0,
                "relative_font_size": 0.833,  # 10/12
                "font_size_pt": 10.0,
                "word_count": 9.0,
                "char_count": 58.0,
                "italic_ratio": 0.0,
                "align_center": 1.0,
                "align_justify": 0.0,
                "space_before_pt": 4.0,
                "space_after_pt": 8.0,
            },
            BlockType.CAPTION.value,
            repeat=35,
        )

        # ─────────────────────────────────────────────
        # 11. TABLE_CAPTION (Table caption: 10pt, center, above table)
        # ─────────────────────────────────────────────
        make_profile(
            {
                "is_table_caption_pattern": 1.0,
                "prev_is_table": 1.0,
                "relative_font_size": 0.833,
                "font_size_pt": 10.0,
                "word_count": 8.0,
                "char_count": 52.0,
                "align_center": 1.0,
                "align_justify": 0.0,
                "space_before_pt": 4.0,
                "space_after_pt": 8.0,
            },
            BlockType.TABLE_CAPTION.value,
            repeat=30,
        )

        # ─────────────────────────────────────────────
        # 12. LIST (book: 12pt, left-aligned, 0.63cm left indent)
        # ─────────────────────────────────────────────
        make_profile(
            {
                "is_list_pattern": 1.0,
                "left_indent_pt": 18.0,   # 0.63cm ≈ 17.9pt
                "relative_font_size": 1.0,
                "font_size_pt": 12.0,
                "word_count": 12.0,
                "char_count": 70.0,
                "align_justify": 0.0,
            },
            BlockType.LIST.value,
            repeat=35,
        )

        # ─────────────────────────────────────────────
        # 13. REFERENCE (book: 10pt, hanging indent 0.63cm)
        # ─────────────────────────────────────────────
        make_profile(
            {
                "is_reference_pattern": 1.0,
                "relative_font_size": 0.833,  # 10/12
                "font_size_pt": 10.0,
                "word_count": 22.0,
                "char_count": 150.0,
                "left_indent_pt": 18.0,   # hanging indent
                "document_position_ratio": 0.92,  # near end of document
                "space_after_pt": 4.0,
            },
            BlockType.REFERENCE.value,
            repeat=35,
        )
        # Variation: long references
        make_profile(
            {
                "is_reference_pattern": 1.0,
                "relative_font_size": 0.833,
                "font_size_pt": 10.0,
                "word_count": 35.0,
                "char_count": 240.0,
                "left_indent_pt": 18.0,
                "document_position_ratio": 0.95,
            },
            BlockType.REFERENCE.value,
            repeat=25,
        )

        X = np.array(X_samples, dtype=np.float32)
        y_encoded = self.label_encoder.fit_transform(y_samples)

        if self.use_xgboost:
            self.classifier.fit(X, y_encoded)
        else:
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
        Three-tier Decision System: Level 1 Rules → Level 2 ML → Level 3 Context.
        """
        evidence: List[str] = []

        # ── Level 1: Container / native DOCX type preservation ──
        if block.block_type in (BlockType.TABLE, BlockType.IMAGE):
            return block.block_type, 1.0, ["Native DOCX container preservation"]
        if "table_data" in block.metadata:
            return BlockType.TABLE, 1.0, ["Embedded table cell structures"]
        if "image_rel_ids" in block.metadata and not block.text:
            return BlockType.IMAGE, 1.0, ["Embedded image relationship reference"]

        # ── Level 1: High-confidence deterministic publication rules ──
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
            return BlockType.CAPTION, 1.0, ["Figure caption pattern (Figure N)"]

        if patterns.get("is_table_caption_pattern"):
            return BlockType.TABLE_CAPTION, 1.0, ["Table caption pattern (Table N)"]

        if patterns.get("is_part_pattern"):
            return BlockType.PART_TITLE, 1.0, ["Part structural header (Part I/II)"]

        if patterns.get("is_chapter_pattern"):
            return BlockType.CHAPTER_TITLE, 0.98, ["Chapter structural keyword"]

        # Book template: exact H3 before H2 check (x.y.z wins over x.y)
        if patterns.get("is_heading_3_pattern"):
            return BlockType.HEADING_3, 0.97, ["Subsection x.y.z numbered heading"]

        if patterns.get("is_heading_2_pattern"):
            return BlockType.HEADING_2, 0.97, ["Section x.y numbered heading"]

        if patterns.get("is_abstract_pattern"):
            return BlockType.ABSTRACT, 0.98, ["Abstract section pattern"]

        if patterns.get("is_keywords_pattern"):
            return BlockType.KEYWORDS, 0.98, ["Keywords pattern"]

        if patterns.get("is_heading_1_pattern"):
            return BlockType.HEADING_1, 0.98, ["Major section numbered heading"]

        # Legacy academic section patterns
        if patterns.get("is_subsection_pattern"):
            return BlockType.HEADING_2, 0.95, ["Subsection numbered header (legacy)"]

        if patterns.get("is_section_pattern"):
            return BlockType.HEADING_1, 0.95, ["Section numbered header (legacy)"]

        if patterns.get("is_front_back_matter") or patterns.get("is_unnumbered_heading"):
            return BlockType.HEADING_1, 0.95, ["Structural section heading"]

        if patterns.get("is_reference_pattern") and word_count >= 4:
            return BlockType.REFERENCE, 0.93, ["Reference entry pattern"]

        if patterns.get("is_list_pattern"):
            return BlockType.LIST, 0.95, ["List bullet or alphanumeric prefix"]

        if word_count > 30 and not patterns.get("is_list_pattern"):
            return BlockType.BODY, 0.95, ["Substantial body paragraph (>30 words)"]

        # ── Level 2: XGBoost / RandomForest ML ──
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
        if block.left_indent_pt > 15:
            evidence.append(f"Left indent signal ({block.left_indent_pt:.0f}pt)")

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
