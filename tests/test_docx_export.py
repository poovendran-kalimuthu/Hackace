"""
Unit Tests for Document Quality Validation and DOCX Export.
"""

import os
import pytest
import docx

from backend.document.model import Block, BlockType, DocumentModel
from backend.export.docx import DocxExporter
from backend.export.validator import DocumentQualityValidator
from backend.templates.manager import TemplateManager


@pytest.fixture
def classic_template():
    mgr = TemplateManager()
    return mgr.get_template("classic_novel")


def test_quality_validator_passes():
    doc = DocumentModel(
        blocks=[
            Block(block_type=BlockType.CHAPTER_TITLE, text="Chapter 1"),
            Block(block_type=BlockType.BODY, text="A valid body paragraph."),
        ]
    )
    result = DocumentQualityValidator.validate(doc)
    assert result.is_valid
    assert len(result.errors) == 0


def test_docx_exporter_creates_valid_file(tmp_path, classic_template):
    out_file = str(tmp_path / "published_book.docx")
    exporter = DocxExporter(classic_template)

    doc_model = DocumentModel(
        blocks=[
            Block(block_type=BlockType.CHAPTER_TITLE, text="Chapter 1: The First Step"),
            Block(block_type=BlockType.HEADING_1, text="1.1 Overview"),
            Block(block_type=BlockType.BODY, text="It was a bright cold day in April, and the clocks were striking thirteen."),
            Block(
                block_type=BlockType.TABLE,
                metadata={"table_data": [["Col 1", "Col 2"], ["Val A", "Val B"]]},
            ),
        ]
    )

    result_path = exporter.export(doc_model, out_file)
    assert os.path.exists(result_path)
    assert os.path.getsize(result_path) > 1000

    # Verify readable in python-docx
    read_back = docx.Document(result_path)
    assert len(read_back.paragraphs) >= 3
    assert len(read_back.tables) >= 1
