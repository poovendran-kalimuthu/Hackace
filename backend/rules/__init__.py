"""
Deterministic Rule Engine & Document Structure Graph.

Validates structural integrity, heading hierarchy, caption associations,
and builds the semantic document tree.
"""

from .validator import RuleEngine
from .heading_rules import HeadingHierarchyRule
from .chapter_rules import ChapterBoundaryRule
from .layout_rules import LayoutAssociationRule
from .structure_graph import DocumentStructureGraph

__all__ = [
    "RuleEngine",
    "HeadingHierarchyRule",
    "ChapterBoundaryRule",
    "LayoutAssociationRule",
    "DocumentStructureGraph",
]
