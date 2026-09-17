"""
Unit Tests for Hybrid ML, Feature Extraction, and Deterministic Rules.
"""

import pytest

from backend.document.model import Block, BlockType, Run
from backend.ml.cascade import ConfidenceCascade
from backend.ml.classifier import DocumentElementClassifier
from backend.ml.features import FeatureExtractor
from backend.rules.heading_rules import HeadingHierarchyRule
from backend.rules.layout_rules import LayoutAssociationRule
from backend.rules.structure_graph import DocumentStructureGraph
from backend.rules.validator import RuleEngine


def test_feature_extractor_dimensions():
    extractor = FeatureExtractor()
    block = Block(
        text="Chapter 1: The Quantum Leap",
        runs=[Run(text="Chapter 1: The Quantum Leap", font_size_pt=24.0, bold=True)],
        alignment="CENTER",
    )
    vec = extractor.extract_vector(block)
    assert len(vec) == len(FeatureExtractor.FEATURE_NAMES)
    assert len(vec) >= 30


def test_classifier_and_cascade():
    clf = DocumentElementClassifier()
    assert clf.is_trained

    # Test Chapter block
    chap_block = Block(
        text="Chapter 1: The Quantum Horizon",
        runs=[Run(text="Chapter 1: The Quantum Horizon", font_size_pt=24.0, bold=True)],
        alignment="CENTER",
    )
    pred_type, conf = clf.classify_block(chap_block)
    assert pred_type == BlockType.CHAPTER_TITLE
    assert conf > 0.5

    # Test Cascade
    cascade = ConfidenceCascade(clf)
    final_type, final_conf, needs_review = cascade.evaluate(chap_block)
    assert final_type == BlockType.CHAPTER_TITLE
    assert not needs_review


def test_rule_engine_heading_hierarchy():
    blocks = [
        Block(original_index=0, block_type=BlockType.CHAPTER_TITLE, text="Chapter 1"),
        # Skipped H1 and H2 straight to H3
        Block(original_index=1, block_type=BlockType.HEADING_3, text="3.1 Micro Sections"),
        Block(original_index=2, block_type=BlockType.BODY, text="Some regular text."),
    ]
    engine = RuleEngine()
    refined, report = engine.validate_and_refine(blocks)

    # H3 should be upgraded to H1 or H2
    assert refined[1].block_type in (BlockType.HEADING_1, BlockType.HEADING_2)


def test_layout_association_caption_linking():
    img_block = Block(original_index=0, block_type=BlockType.IMAGE, metadata={"image_rel_ids": ["rId5"]})
    caption_block = Block(original_index=1, block_type=BlockType.CAPTION, text="Figure 1.1: Neural manifold.")

    blocks = [img_block, caption_block]
    LayoutAssociationRule.apply(blocks)

    assert caption_block.metadata.get("associated_element_id") == img_block.id
    assert img_block.metadata.get("caption_id") == caption_block.id


def test_document_structure_graph():
    blocks = [
        Block(id="ch1", original_index=0, block_type=BlockType.CHAPTER_TITLE, text="Chapter 1"),
        Block(id="h1", original_index=1, block_type=BlockType.HEADING_1, text="1.1 Overview"),
        Block(id="b1", original_index=2, block_type=BlockType.BODY, text="Content line."),
    ]
    graph = DocumentStructureGraph.build(blocks, book_title="Test Book")
    assert graph.node_type == "BOOK"
    assert len(graph.children) == 1  # 1 chapter
    assert graph.children[0].node_type == "CHAPTER"
    assert len(graph.children[0].children) == 1  # 1 section
