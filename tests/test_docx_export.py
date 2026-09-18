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


def test_tabulation_and_table_preservation_roundtrip(tmp_path, classic_template):
    from backend.document.reader import DocxReader

    # 1. Create a DOCX with a table and a tabbed line
    src_file = str(tmp_path / "source_tab_doc.docx")
    src_doc = docx.Document()
    src_doc.add_paragraph("Preamble before table")
    tbl = src_doc.add_table(rows=2, cols=3)
    tbl.cell(0, 0).text = "Item"
    tbl.cell(0, 1).text = "Quantity"
    tbl.cell(0, 2).text = "Cost"
    tbl.cell(1, 0).text = "Notebook"
    tbl.cell(1, 1).text = "10"
    tbl.cell(1, 2).text = "$45.00"

    p_tab = src_doc.add_paragraph()
    p_tab.add_run("Col A")
    p_tab.add_run().add_tab()
    p_tab.add_run("Col B")
    src_doc.save(src_file)

    # 2. Ingest via DocxReader
    reader = DocxReader(src_file)
    blocks = list(reader.stream_raw_blocks())

    # Ensure table cells were NOT emitted as rogue body blocks
    body_texts = [b.text for b in blocks if b.block_type == BlockType.BODY]
    assert "Item" not in body_texts
    assert "Notebook" not in body_texts

    # Ensure table block was extracted with complete grid data
    tbl_blocks = [b for b in blocks if b.block_type == BlockType.TABLE]
    assert len(tbl_blocks) == 1
    table_data = tbl_blocks[0].metadata.get("table_data")
    assert table_data == [
        ["Item", "Quantity", "Cost"],
        ["Notebook", "10", "$45.00"],
    ]

    # Ensure tab character was preserved
    tab_p = [b for b in blocks if "Col A" in b.text][0]
    assert "\t" in tab_p.text

    # 3. Export via DocxExporter
    out_file = str(tmp_path / "exported_tab.docx")
    exporter = DocxExporter(classic_template)
    doc_model = DocumentModel(blocks=blocks)
    exporter.export(doc_model, out_file)

    # 4. Verify exported document has table with values
    exp_doc = docx.Document(out_file)
    assert len(exp_doc.tables) >= 1
    exp_cells = [[c.text for c in r.cells] for r in exp_doc.tables[0].rows]
    assert exp_cells == [
        ["Item", "Quantity", "Cost"],
        ["Notebook", "10", "$45.00"],
    ]

