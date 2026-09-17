"""
Unit Tests for SQLite Document Indexing and Semantic Chunking.
"""

import os
import pytest

from backend.document.chunk_manager import ChunkManager
from backend.document.indexer import DocumentIndexer
from backend.document.model import Block, BlockType
from backend.generator.synthetic_docs import SyntheticDocumentGenerator
from backend.document.parser import DocumentParser


@pytest.fixture
def sample_docx(tmp_path):
    docx_path = str(tmp_path / "index_test.docx")
    SyntheticDocumentGenerator.create_document(target_pages=8, output_path=docx_path)
    return docx_path


def test_document_indexer_stats_and_search(tmp_path, sample_docx):
    db_path = str(tmp_path / "test_index.db")
    indexer = DocumentIndexer(db_path)
    parser = DocumentParser(sample_docx)

    doc_id = "doc_123"
    meta = parser.scan_and_index(document_id=doc_id, indexer=indexer)

    assert meta.total_paragraphs > 0
    assert meta.total_words > 0
    assert meta.estimated_pages >= 5

    # Test stats retrieval
    stats = indexer.get_document_stats(doc_id)
    assert stats["total_blocks"] == meta.total_paragraphs
    assert stats["total_words"] == meta.total_words

    # Test chapter retrieval
    chapters = indexer.get_chapters(doc_id)
    assert len(chapters) > 0
    assert "start_page" in chapters[0]

    # Test lazy page block retrieval
    page_1_blocks = indexer.get_blocks_for_page(doc_id, page_number=1)
    assert len(page_1_blocks) > 0

    # Test fast full-text search
    results = indexer.search(doc_id, "Quantum")
    assert isinstance(results, list)


def test_chunk_manager_boundaries(tmp_path):
    chunks_dir = str(tmp_path / "chunks")
    mgr = ChunkManager(chunks_dir)

    # Synthetic block sequence: Chapter + Headings + Body
    blocks = [
        Block(original_index=0, block_type=BlockType.CHAPTER_TITLE, text="Chapter 1: The Beginning"),
        Block(original_index=1, block_type=BlockType.HEADING_1, text="1.1 Overview"),
        Block(original_index=2, block_type=BlockType.BODY, text="Lorem ipsum dolor sit amet."),
        Block(original_index=3, block_type=BlockType.BODY, text="Consectetur adipiscing elit."),
        Block(original_index=4, block_type=BlockType.CHAPTER_TITLE, text="Chapter 2: The Return"),
        Block(original_index=5, block_type=BlockType.BODY, text="Sed do eiusmod tempor."),
    ]

    chunks = mgr.partition(blocks, target_size=2, context_window=1)
    assert len(chunks) >= 2

    # Save and reload test
    for ch in chunks:
        mgr.save_chunk(ch)

    loaded = mgr.load_chunk("chunk_0000")
    assert loaded is not None
    assert loaded.chapter_index >= 0
    assert len(loaded.blocks) > 0
