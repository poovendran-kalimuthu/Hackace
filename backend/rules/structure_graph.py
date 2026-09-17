"""
Document Structure Graph.

Constructs an interactive hierarchical tree (Book -> Chapter -> Section -> Block)
that serves as the structural bridge between classification and layout.
"""

from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.document.model import Block, BlockType


class StructureNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    node_type: str = "BLOCK"  # BOOK, CHAPTER, SECTION, SUBSECTION, BLOCK
    block_type: Optional[str] = None
    level: int = 0
    estimated_page: int = 1
    word_count: int = 0
    children: List[StructureNode] = Field(default_factory=list)
    block_id: Optional[str] = None
    preview_text: str = ""


class DocumentStructureGraph:
    """
    Transforms validated flat block streams into an explicit, navigable hierarchy.
    """

    @classmethod
    def build(cls, blocks: List[Block], book_title: str = "Book Manuscript") -> StructureNode:
        root = StructureNode(
            title=book_title,
            node_type="BOOK",
            level=0,
        )

        current_chapter: Optional[StructureNode] = None
        current_section: Optional[StructureNode] = None
        current_sub: Optional[StructureNode] = None

        chap_counter = 0

        for b in blocks:
            text_strip = b.text.strip()
            preview = (text_strip[:80] + "...") if len(text_strip) > 80 else text_strip

            # CHAPTER_TITLE
            if b.block_type == BlockType.CHAPTER_TITLE:
                chap_counter += 1
                title = text_strip if text_strip else f"Chapter {chap_counter}"
                current_chapter = StructureNode(
                    id=b.id,
                    title=title,
                    node_type="CHAPTER",
                    block_type=b.block_type.value,
                    level=1,
                    block_id=b.id,
                    preview_text=preview,
                )
                root.children.append(current_chapter)
                current_section = None
                current_sub = None
                continue

            # HEADING_1
            if b.block_type == BlockType.HEADING_1:
                current_section = StructureNode(
                    id=b.id,
                    title=text_strip,
                    node_type="SECTION",
                    block_type=b.block_type.value,
                    level=2,
                    block_id=b.id,
                    preview_text=preview,
                )
                if current_chapter is not None:
                    current_chapter.children.append(current_section)
                else:
                    root.children.append(current_section)
                current_sub = None
                continue

            # HEADING_2 or HEADING_3
            if b.block_type in (BlockType.HEADING_2, BlockType.HEADING_3):
                current_sub = StructureNode(
                    id=b.id,
                    title=text_strip,
                    node_type="SUBSECTION",
                    block_type=b.block_type.value,
                    level=3 if b.block_type == BlockType.HEADING_2 else 4,
                    block_id=b.id,
                    preview_text=preview,
                )
                if current_section is not None:
                    current_section.children.append(current_sub)
                elif current_chapter is not None:
                    current_chapter.children.append(current_sub)
                else:
                    root.children.append(current_sub)
                continue

            # Regular Block
            leaf = StructureNode(
                id=b.id,
                title=b.block_type.value,
                node_type="BLOCK",
                block_type=b.block_type.value,
                level=5,
                block_id=b.id,
                preview_text=preview,
                word_count=b.word_count(),
            )

            if current_sub is not None:
                current_sub.children.append(leaf)
            elif current_section is not None:
                current_section.children.append(leaf)
            elif current_chapter is not None:
                current_chapter.children.append(leaf)
            else:
                root.children.append(leaf)

        return root

    @classmethod
    def get_toc(cls, root: StructureNode) -> List[Dict[str, Any]]:
        """Extract Table of Contents items (Chapters and Major Sections)."""
        toc: List[Dict[str, Any]] = []

        def recurse(node: StructureNode, depth: int):
            if node.node_type in ("CHAPTER", "SECTION", "SUBSECTION"):
                toc.append({
                    "id": node.id,
                    "title": node.title,
                    "type": node.node_type,
                    "level": node.level,
                    "estimated_page": node.estimated_page,
                })
            for ch in node.children:
                recurse(ch, depth + 1)

        recurse(root, 0)
        return toc
