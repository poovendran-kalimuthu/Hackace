"""
Structural Document Parser.

Coordinates reader streams into the custom hierarchical DocumentModel,
performing metadata aggregation and initial section grouping.
"""

from __future__ import annotations
import os
from typing import List, Optional

from .chunk_manager import Chunk, ChunkManager
from .indexer import DocumentIndexer
from .model import (
    Block,
    BlockType,
    Chapter,
    DocumentMetadata,
    DocumentModel,
    Section,
)
from .reader import DocxReader


class DocumentParser:
    """
    Parses DOCX files into internal DocumentModel structures, supporting both
    in-memory representation for standard files and indexed streaming for 10,000+ page files.
    """

    def __init__(self, docx_path: str):
        self.docx_path = docx_path
        self.reader = DocxReader(docx_path)

    def scan_and_index(
        self,
        document_id: str,
        indexer: DocumentIndexer,
        chunk_manager: Optional[ChunkManager] = None,
    ) -> DocumentMetadata:
        """
        Streaming pipeline: streams OOXML blocks directly into the SQLite indexer
        and optional ChunkManager without holding millions of tokens in RAM.
        """
        meta = self.reader.extract_metadata()
        rels = self.reader.extract_relationships()

        all_blocks: List[Block] = []
        for block in self.reader.stream_raw_blocks():
            all_blocks.append(block)

        stats = indexer.index_blocks(document_id, all_blocks)

        meta.total_paragraphs = stats.get("total_blocks", 0)
        meta.total_words = stats.get("total_words", 0)
        meta.estimated_pages = stats.get("estimated_pages", 1)
        meta.total_chapters = stats.get("total_chapters", 0)
        meta.total_images = stats.get("total_images", 0)
        meta.total_tables = stats.get("total_tables", 0)
        meta.detected_types_summary = stats.get("type_counts", {})

        if chunk_manager is not None:
            chunks = chunk_manager.partition(all_blocks)
            for ch in chunks:
                chunk_manager.save_chunk(ch)

        return meta

    def parse_full_model(self) -> DocumentModel:
        """
        Builds complete hierarchical DocumentModel with Chapters, Sections, and Blocks.
        Ideal for document sizes up to ~1,000 pages or post-aggregation pipelines.
        """
        meta = self.reader.extract_metadata()
        rels = self.reader.extract_relationships()

        blocks = list(self.reader.stream_raw_blocks())
        meta.total_paragraphs = len(blocks)
        meta.total_words = sum(b.word_count() for b in blocks)
        meta.estimated_pages = max(1, meta.total_words // 280)

        chapters: List[Chapter] = []
        current_chapter = Chapter(title="Front Matter", blocks=[])
        current_section = Section(title="General", blocks=[])

        chap_num = 0
        for block in blocks:
            if block.block_type == BlockType.CHAPTER_TITLE or "chapter" in block.text.lower()[:15]:
                chap_num += 1
                if current_chapter.blocks or current_chapter.sections:
                    if current_section.blocks:
                        current_chapter.sections.append(current_section)
                        current_section = Section(title="", blocks=[])
                    chapters.append(current_chapter)

                current_chapter = Chapter(
                    title=block.text if block.text else f"Chapter {chap_num}",
                    number=chap_num,
                    blocks=[block],
                )
                meta.total_chapters += 1
            elif block.block_type in (BlockType.HEADING_1, BlockType.HEADING_2):
                if current_section.blocks:
                    current_chapter.sections.append(current_section)
                current_section = Section(title=block.text, blocks=[block])
            else:
                if current_section.blocks or current_section.title:
                    current_section.blocks.append(block)
                else:
                    current_chapter.blocks.append(block)

        if current_section.blocks:
            current_chapter.sections.append(current_section)
        if current_chapter.blocks or current_chapter.sections:
            chapters.append(current_chapter)

        return DocumentModel(
            metadata=meta,
            chapters=chapters,
            blocks=blocks,
            relationships=rels,
        )
