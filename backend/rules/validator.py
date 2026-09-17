"""
Deterministic Rule Engine.

Orchestrates all structural, grammatical, and layout validation rules,
ensuring publication-standard document consistency before formatting.
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple

from backend.document.model import Block, BlockType
from .chapter_rules import ChapterBoundaryRule
from .heading_rules import HeadingHierarchyRule
from .layout_rules import LayoutAssociationRule


class RuleEngine:
    """
    Deterministic rule engine that validates and refines ML predictions.
    """

    def __init__(self):
        self.rules = [
            ("Chapter Boundaries", ChapterBoundaryRule.apply),
            ("Heading Hierarchy", HeadingHierarchyRule.apply),
            ("Layout & Caption Associations", LayoutAssociationRule.apply),
        ]

    def validate_and_refine(self, blocks: List[Block]) -> Tuple[List[Block], Dict[str, Any]]:
        """
        Runs the rule cascade over a sequence of classified blocks.
        Returns refined blocks and a validation summary report.
        """
        report: Dict[str, Any] = {
            "rules_applied": [],
            "warnings": [],
            "adjustments_count": 0,
        }

        # Track initial types to detect adjustments
        initial_types = [b.block_type for b in blocks]

        processed = blocks
        for rule_name, rule_fn in self.rules:
            processed = rule_fn(processed)
            report["rules_applied"].append(rule_name)

        # Count modifications
        adjustments = 0
        for i, (orig, final_b) in enumerate(zip(initial_types, processed)):
            if orig != final_b.block_type:
                adjustments += 1

        report["adjustments_count"] = adjustments

        # Check for lingering warnings
        has_chapters = any(b.block_type == BlockType.CHAPTER_TITLE for b in processed)
        if not has_chapters and len(processed) > 50:
            report["warnings"].append("No distinct chapter titles detected; document treated as single unified body.")

        return processed, report
