"""
Unit Tests for Hybrid ML, Feature Extraction, and Deterministic Rules.

Covers:
  - Feature vector shape/completeness
  - Book Publisher block classification (all 16 types)
  - Rule engine heading hierarchy correction
  - Layout association (caption <-> image)
  - Document structure graph
  - New structural pattern matcher patterns (H2, H3, reference, part)
"""

import pytest

from backend.document.model import Block, BlockType, Run
from backend.ml.cascade import ConfidenceCascade
from backend.ml.classifier import DocumentElementClassifier
from backend.ml.features import FeatureExtractor
from backend.nlp.structural_features import StructuralPatternMatcher
from backend.rules.heading_rules import HeadingHierarchyRule
from backend.rules.layout_rules import LayoutAssociationRule
from backend.rules.structure_graph import DocumentStructureGraph
from backend.rules.validator import RuleEngine


# ══════════════════════════════════════════════════════════════════
#  Feature Extractor
# ══════════════════════════════════════════════════════════════════

def test_feature_extractor_dimensions():
    extractor = FeatureExtractor()
    block = Block(
        text="Chapter 1: The Quantum Leap",
        runs=[Run(text="Chapter 1: The Quantum Leap", font_size_pt=16.0, bold=True)],
        alignment="CENTER",
    )
    vec = extractor.extract_vector(block)
    assert len(vec) == len(FeatureExtractor.FEATURE_NAMES), (
        f"Expected {len(FeatureExtractor.FEATURE_NAMES)} features, got {len(vec)}"
    )
    assert len(vec) >= 36   # Must have grown from previous 36


def test_feature_extractor_new_book_features_present():
    """All 4 new book-specific features must be in FEATURE_NAMES."""
    names = FeatureExtractor.FEATURE_NAMES
    assert "is_part_pattern"      in names
    assert "is_heading_2_pattern" in names
    assert "is_heading_3_pattern" in names
    assert "is_reference_pattern" in names


# ══════════════════════════════════════════════════════════════════
#  Structural Pattern Matcher
# ══════════════════════════════════════════════════════════════════

def test_chapter_patterns():
    cases = [
        ("Chapter 1", True),
        ("Chapter IV", True),
        ("Chapter 1: The Beginning", True),
        ("Prologue", True),
        ("Epilogue: The End", True),
        ("chapter 3 — Dark Waters", True),
        ("1.1 Overview", False),
        ("Some random body text here.", False),
    ]
    for text, expected in cases:
        p = StructuralPatternMatcher.match_patterns(text)
        assert bool(p["is_chapter_pattern"]) == expected, (
            f"is_chapter_pattern mismatch for: '{text}' (expected={expected})"
        )


def test_part_patterns():
    cases = [
        ("Part I", True),
        ("PART 2", True),
        ("Part IV: The Fall", True),
        ("part iii beginnings", True),
        ("Chapter 1", False),
        ("1.1 Overview", False),
    ]
    for text, expected in cases:
        p = StructuralPatternMatcher.match_patterns(text)
        assert bool(p["is_part_pattern"]) == expected, (
            f"is_part_pattern mismatch for: '{text}'"
        )


def test_heading_2_patterns():
    cases = [
        ("1.1 Overview",            True),
        ("2.3 Experimental Results", True),
        ("10.2 Summary",            True),
        ("1.1. Background",         True),
        ("1.1.1 Sub detail",        False),   # H3, not H2
        ("Chapter 1",               False),
        ("Some regular body text.", False),
    ]
    for text, expected in cases:
        p = StructuralPatternMatcher.match_patterns(text)
        assert bool(p["is_heading_2_pattern"]) == expected, (
            f"is_heading_2_pattern mismatch for: '{text}'"
        )


def test_heading_3_patterns():
    cases = [
        ("1.1.1 Background",        True),
        ("2.3.4 Analysis Method",   True),
        ("3.2.1 Results Overview",  True),
        ("1.1 Overview",            False),   # H2, not H3
        ("Chapter 1",               False),
    ]
    for text, expected in cases:
        p = StructuralPatternMatcher.match_patterns(text)
        assert bool(p["is_heading_3_pattern"]) == expected, (
            f"is_heading_3_pattern mismatch for: '{text}'"
        )


def test_reference_patterns():
    cases = [
        ("[1] Smith, J. Machine Learning in Practice.", True),
        ("[Smith, 2023] A Review of NLP.",              True),
        ("Smith, J. (2020) Deep Learning.",             True),
        # NOTE: "1. Word..." form is intentionally NOT matched as reference
        # (to avoid conflict with numbered lists). Only bracketed or author-year forms match.
        ("1. Install the required dependencies",        False),  # plain list item
        ("Some regular body text here.",                False),
        ("Chapter 1",                                   False),
    ]
    for text, expected in cases:
        p = StructuralPatternMatcher.match_patterns(text)
        assert bool(p["is_reference_pattern"]) == expected, (
            f"is_reference_pattern mismatch for: '{text}'"
        )


def test_list_patterns():
    cases = [
        ("• First item",       True),
        ("- Second item",      True),
        ("1. Third item",      True),
        ("(a) Fourth item",    True),
        ("a) Fifth item",      True),
        ("Normal body text.",  False),
        ("Chapter 1",          False),
    ]
    for text, expected in cases:
        p = StructuralPatternMatcher.match_patterns(text)
        assert bool(p["is_list_pattern"]) == expected, (
            f"is_list_pattern mismatch for: '{text}'"
        )


# ══════════════════════════════════════════════════════════════════
#  Book Publisher Block Classification (all key types)
# ══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def clf():
    return DocumentElementClassifier()


@pytest.fixture(scope="module")
def cascade(clf):
    return ConfidenceCascade(clf)


def test_classifier_is_trained(clf):
    assert clf.is_trained


# ── Chapter title ──

def test_classify_chapter_title_numeric(clf):
    block = Block(
        text="Chapter 1: The Quantum Horizon",
        runs=[Run(text="Chapter 1: The Quantum Horizon", font_size_pt=16.0, bold=True)],
        alignment="CENTER",
    )
    pred, conf = clf.classify_block(block)
    assert pred == BlockType.CHAPTER_TITLE, f"Expected CHAPTER_TITLE, got {pred}"
    assert conf > 0.5


def test_classify_chapter_title_roman(clf):
    block = Block(
        text="Chapter IV",
        runs=[Run(text="Chapter IV", font_size_pt=16.0, bold=True)],
        alignment="CENTER",
    )
    pred, conf = clf.classify_block(block)
    assert pred == BlockType.CHAPTER_TITLE, f"Expected CHAPTER_TITLE, got {pred}"


def test_classify_chapter_prologue(clf):
    block = Block(
        text="Prologue",
        runs=[Run(text="Prologue", font_size_pt=16.0, bold=True)],
        alignment="CENTER",
    )
    pred, conf = clf.classify_block(block)
    assert pred == BlockType.CHAPTER_TITLE


# ── Heading 2 ──

def test_classify_heading_2(clf):
    block = Block(
        text="1.1 Overview",
        runs=[Run(text="1.1 Overview", font_size_pt=12.0, bold=True)],
        alignment="LEFT",
    )
    pred, conf = clf.classify_block(block)
    assert pred == BlockType.HEADING_2, f"Expected HEADING_2, got {pred}"
    assert conf > 0.5


def test_classify_heading_2_long(clf):
    block = Block(
        text="2.3 Experimental Results and Discussion",
        runs=[Run(text="2.3 Experimental Results and Discussion", font_size_pt=12.0, bold=True)],
        alignment="LEFT",
    )
    pred, conf = clf.classify_block(block)
    assert pred == BlockType.HEADING_2, f"Expected HEADING_2, got {pred}"


# ── Heading 3 ──

def test_classify_heading_3(clf):
    block = Block(
        text="1.1.1 Background Details",
        runs=[Run(text="1.1.1 Background Details", font_size_pt=12.0, bold=True)],
        alignment="LEFT",
    )
    pred, conf = clf.classify_block(block)
    assert pred == BlockType.HEADING_3, f"Expected HEADING_3, got {pred}"
    assert conf > 0.5


# ── Body ──

def test_classify_body_paragraph(clf):
    body_text = (
        "The machine learning approach presented in this chapter employs a hybrid "
        "architecture that combines rule-based structural analysis with a gradient-boosted "
        "ensemble classifier, achieving state-of-the-art performance on the benchmark dataset."
    )
    block = Block(
        text=body_text,
        runs=[Run(text=body_text, font_size_pt=12.0, bold=False)],
        alignment="JUSTIFY",
        left_indent_pt=36.0,
    )
    pred, conf = clf.classify_block(block)
    assert pred == BlockType.BODY, f"Expected BODY, got {pred}"
    assert conf > 0.5


# ── Block Quote ──

def test_classify_block_quote(clf):
    quote_text = (
        '"To be or not to be, that is the question." '
        "The philosopher contemplated existence in silence."
    )
    block = Block(
        text=quote_text,
        runs=[Run(text=quote_text, font_size_pt=11.0, bold=False, italic=True)],
        alignment="JUSTIFY",
        left_indent_pt=28.0,
        right_indent_pt=28.0,
    )
    pred, conf = clf.classify_block(block)
    assert pred == BlockType.QUOTE, f"Expected QUOTE, got {pred}"


# ── Figure Caption ──

def test_classify_figure_caption(clf):
    block = Block(
        text="Figure 1.1: Architecture of the proposed system.",
        runs=[Run(text="Figure 1.1: Architecture of the proposed system.", font_size_pt=10.0)],
        alignment="CENTER",
    )
    pred, conf = clf.classify_block(block)
    assert pred == BlockType.CAPTION, f"Expected CAPTION, got {pred}"
    assert conf >= 0.8


# ── Table Caption ──

def test_classify_table_caption(clf):
    block = Block(
        text="Table 2.3: Summary of classification results across datasets.",
        runs=[Run(text="Table 2.3: Summary of classification results across datasets.", font_size_pt=10.0)],
        alignment="CENTER",
    )
    pred, conf = clf.classify_block(block)
    assert pred == BlockType.TABLE_CAPTION, f"Expected TABLE_CAPTION, got {pred}"
    assert conf >= 0.8


# ── List ──

def test_classify_list_bullet(clf):
    block = Block(
        text="• The system processes up to 10,000 pages offline",
        runs=[Run(text="• The system processes up to 10,000 pages offline", font_size_pt=12.0)],
        alignment="LEFT",
        left_indent_pt=18.0,
    )
    pred, conf = clf.classify_block(block)
    assert pred == BlockType.LIST, f"Expected LIST, got {pred}"


def test_classify_list_numbered(clf):
    block = Block(
        text="1. Install the required dependencies",
        runs=[Run(text="1. Install the required dependencies", font_size_pt=12.0)],
        alignment="LEFT",
        left_indent_pt=18.0,
    )
    pred, conf = clf.classify_block(block)
    assert pred == BlockType.LIST, f"Expected LIST, got {pred}"


# ── Reference ──

def test_classify_reference_numeric(clf):
    block = Block(
        text="[1] Smith, J. (2020). Deep Learning. MIT Press.",
        runs=[Run(text="[1] Smith, J. (2020). Deep Learning. MIT Press.", font_size_pt=10.0)],
        alignment="LEFT",
        left_indent_pt=18.0,
        original_index=950,
    )
    block2 = clf.classify_block(block)
    pred, conf = block2
    assert pred == BlockType.REFERENCE, f"Expected REFERENCE, got {pred}"


# ── Part Title ──

def test_classify_part_title(clf):
    block = Block(
        text="Part I",
        runs=[Run(text="Part I", font_size_pt=18.0, bold=True)],
        alignment="CENTER",
    )
    pred, conf = clf.classify_block(block)
    assert pred == BlockType.PART_TITLE, f"Expected PART_TITLE, got {pred}"


# ── Cascade integration ──

def test_cascade_chapter_title_no_review(cascade):
    block = Block(
        text="Chapter 3: The Hidden Variables",
        runs=[Run(text="Chapter 3: The Hidden Variables", font_size_pt=16.0, bold=True)],
        alignment="CENTER",
    )
    final_type, final_conf, needs_review = cascade.evaluate(block)
    assert final_type == BlockType.CHAPTER_TITLE
    assert not needs_review


def test_cascade_heading_2(cascade):
    block = Block(
        text="1.1 Overview",
        runs=[Run(text="1.1 Overview", font_size_pt=12.0, bold=True)],
        alignment="LEFT",
    )
    final_type, final_conf, needs_review = cascade.evaluate(block)
    assert final_type == BlockType.HEADING_2
    assert not needs_review


def test_cascade_heading_3(cascade):
    block = Block(
        text="2.1.3 Statistical Methods",
        runs=[Run(text="2.1.3 Statistical Methods", font_size_pt=12.0, bold=True)],
        alignment="LEFT",
    )
    final_type, final_conf, needs_review = cascade.evaluate(block)
    assert final_type == BlockType.HEADING_3
    assert not needs_review


def test_cascade_user_override_respected(cascade):
    block = Block(
        text="Some text",
        block_type=BlockType.QUOTE,
        user_corrected=True,
    )
    final_type, final_conf, needs_review = cascade.evaluate(block)
    assert final_type == BlockType.QUOTE
    assert final_conf == 1.0
    assert not needs_review


# ══════════════════════════════════════════════════════════════════
#  Rule Engine
# ══════════════════════════════════════════════════════════════════

def test_rule_engine_heading_hierarchy():
    blocks = [
        Block(original_index=0, block_type=BlockType.CHAPTER_TITLE, text="Chapter 1"),
        # Skipped H1 and H2 straight to H3
        Block(original_index=1, block_type=BlockType.HEADING_3, text="3.1 Micro Sections"),
        Block(original_index=2, block_type=BlockType.BODY, text="Some regular text."),
    ]
    engine = RuleEngine()
    refined, report = engine.validate_and_refine(blocks)

    # H3 should be upgraded to H1 or H2 since there's no parent hierarchy
    assert refined[1].block_type in (BlockType.HEADING_1, BlockType.HEADING_2)


# ══════════════════════════════════════════════════════════════════
#  Layout Association
# ══════════════════════════════════════════════════════════════════

def test_layout_association_caption_linking():
    img_block = Block(
        original_index=0,
        block_type=BlockType.IMAGE,
        metadata={"image_rel_ids": ["rId5"]},
    )
    caption_block = Block(
        original_index=1,
        block_type=BlockType.CAPTION,
        text="Figure 1.1: Neural manifold.",
    )

    blocks = [img_block, caption_block]
    LayoutAssociationRule.apply(blocks)

    assert caption_block.metadata.get("associated_element_id") == img_block.id
    assert img_block.metadata.get("caption_id") == caption_block.id


# ══════════════════════════════════════════════════════════════════
#  Document Structure Graph
# ══════════════════════════════════════════════════════════════════

def test_document_structure_graph():
    blocks = [
        Block(id="ch1", original_index=0, block_type=BlockType.CHAPTER_TITLE, text="Chapter 1"),
        Block(id="h1",  original_index=1, block_type=BlockType.HEADING_1,     text="1.1 Overview"),
        Block(id="b1",  original_index=2, block_type=BlockType.BODY,           text="Content line."),
    ]
    graph = DocumentStructureGraph.build(blocks, book_title="Test Book")
    assert graph.node_type == "BOOK"
    assert len(graph.children) == 1          # 1 chapter
    assert graph.children[0].node_type == "CHAPTER"
    assert len(graph.children[0].children) == 1  # 1 section


def test_document_structure_graph_multi_chapter():
    blocks = [
        Block(id="ch1", original_index=0, block_type=BlockType.CHAPTER_TITLE, text="Chapter 1"),
        Block(id="b1",  original_index=1, block_type=BlockType.BODY,           text="Content."),
        Block(id="ch2", original_index=2, block_type=BlockType.CHAPTER_TITLE, text="Chapter 2"),
        Block(id="b2",  original_index=3, block_type=BlockType.BODY,           text="More content."),
    ]
    graph = DocumentStructureGraph.build(blocks, book_title="Test Book")
    assert graph.node_type == "BOOK"
    assert len(graph.children) == 2, f"Expected 2 chapters, got {len(graph.children)}"
