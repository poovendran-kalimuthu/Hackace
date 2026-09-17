"""
Unit Tests for Document Core Models, Readers, and Parsers.
"""

import os
import tempfile
import pytest
import docx

from backend.document.model import Block, BlockType, DocumentModel, Run
from backend.document.parser import DocumentParser
from backend.document.reader import DocxReader
from backend.generator.synthetic_docs import SyntheticDocumentGenerator


@pytest.fixture
def sample_docx(tmp_path):
    docx_path = str(tmp_path / "test_manuscript.docx")
    SyntheticDocumentGenerator.create_document(target_pages=5, output_path=docx_path)
    return docx_path


def test_docx_reader_metadata(sample_docx):
    reader = DocxReader(sample_docx)
    meta = reader.extract_metadata()
    assert meta.source_filename == "test_manuscript.docx"
    assert meta.file_size_bytes > 0


def test_docx_reader_streaming(sample_docx):
    reader = DocxReader(sample_docx)
    blocks = list(reader.stream_raw_blocks())
    assert len(blocks) > 10

    # Ensure paragraph properties extracted
    has_text = any(len(b.text) > 0 for b in blocks)
    assert has_text

    # Ensure runs are present
    has_runs = any(len(b.runs) > 0 for b in blocks)
    assert has_runs


def test_document_parser_full_model(sample_docx):
    parser = DocumentParser(sample_docx)
    doc_model = parser.parse_full_model()

    assert doc_model.metadata.total_paragraphs > 0
    assert doc_model.metadata.total_words > 0
    assert len(doc_model.chapters) > 0
    assert len(doc_model.blocks) > 0
