"""
Unit tests for the Perfected Document Formatting & Equation Engine.
"""

import os
import pytest
import docx
from lxml import etree
import zipfile

from backend.formatting.equations import latex_to_omml, render_paragraph_content, is_equation_text
from backend.document.model import Block, BlockType, DocumentModel, DocumentMetadata
from backend.templates.manager import TemplateManager
from backend.export.docx import DocxExporter


def test_latex_to_omml_display_and_inline():
    # Test display equation
    latex_display = r"\sigma^2 = \mathbb{E}[e^2] = \int_{-\frac{S}{2}}^{+\frac{S}{2}} e^2 \cdot \frac{1}{S} , de"
    omml_elem = latex_to_omml(latex_display, display=True)
    assert omml_elem is not None
    xml_str = etree.tostring(omml_elem, encoding="utf-8").decode("utf-8")
    assert "oMath" in xml_str

    # Test inline equation
    latex_inline = r"S"
    omml_inline = latex_to_omml(latex_inline, display=False)
    assert omml_inline is not None
    xml_inline = etree.tostring(omml_inline, encoding="utf-8").decode("utf-8")
    assert "oMath" in xml_inline


def test_render_paragraph_content_equations():
    doc = docx.Document()
    p = doc.add_paragraph()
    render_paragraph_content(p, "Scale factor ($S$) and zero-point ($Z$) are computed.")
    xml_p = p._p.xml
    assert "oMath" in xml_p
    # Zero raw LaTeX remains
    assert r"$S$" not in p.text
    assert r"$Z$" not in p.text


def test_docx_export_table_and_breaks(tmp_path):
    tpl_mgr = TemplateManager()
    template = tpl_mgr.get_template("book_publisher")

    blocks = [
        Block(original_index=0, block_type=BlockType.TITLE, text="Intelligent Edge Systems: Test Title"),
        Block(original_index=1, block_type=BlockType.AUTHOR, text="Dr. Arun Kumar"),
        Block(original_index=2, block_type=BlockType.PART_TITLE, text="PART I: TEST FOUNDATIONS"),
        Block(original_index=3, block_type=BlockType.CHAPTER_TITLE, text="Chapter 1: Test Intro"),
        Block(original_index=4, block_type=BlockType.HEADING_1, text="Section 1.1: Background"),
        Block(original_index=5, block_type=BlockType.BODY, text="This is standard body paragraph text."),
        Block(
            original_index=6,
            block_type=BlockType.TABLE,
            text="Table Data",
            metadata={"table_data": [["Col A", "Col B"], ["1", "2"]]},
        ),
        Block(original_index=7, block_type=BlockType.EQUATION, text=r"$$w_{t+1} \leftarrow w_t - \eta g$$"),
    ]
    doc_model = DocumentModel(metadata=DocumentMetadata(title="Test Title"), blocks=blocks)

    out_file = str(tmp_path / "test_export.docx")
    exporter = DocxExporter(template)
    exporter.export(doc_model, out_file)

    assert os.path.exists(out_file)
    with zipfile.ZipFile(out_file) as z:
        xml = z.read("word/document.xml")
        tree = etree.fromstring(xml)
        ns = {
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
            "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
        }
        # Verify table header repeat and cantSplit
        assert len(tree.xpath(".//w:tblHeader", namespaces=ns)) == 1
        assert len(tree.xpath(".//w:cantSplit", namespaces=ns)) == 2
        # Verify OMML math
        assert len(tree.xpath(".//m:oMath", namespaces=ns)) >= 1
