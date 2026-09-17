"""
Unit Tests for Templates and Formatting Engines.
Verifies the exactly 3 publication templates (Book Publisher, Academic Research Paper, Conference Paper) and styling pipeline.
"""

import pytest

from backend.document.model import Block, BlockType, DocumentModel
from backend.formatting.engine import FormattingEngine
from backend.formatting.layout import SmartLayoutEngine
from backend.formatting.styles import StyleResolver
from backend.templates.manager import TemplateManager


@pytest.fixture
def template_mgr(tmp_path):
    custom_dir = str(tmp_path / "custom_templates")
    return TemplateManager(custom_dir)


def test_builtin_three_templates_loaded(template_mgr):
    templates = template_mgr.list_templates()
    ids = [t.id for t in templates]
    assert "book" in ids
    assert any(x in ids for x in ("academic_research", "journal", "academic"))
    assert any(x in ids for x in ("conference_paper", "technical", "conference"))
    assert len(ids) == 3


def test_style_resolver(template_mgr):
    tpl = template_mgr.get_template("book")
    resolver = StyleResolver(tpl)

    b = Block(block_type=BlockType.CHAPTER_TITLE, text="Chapter 1")
    styled_b = resolver.apply_to_block(b)
    assert styled_b.alignment in ("CENTER", "LEFT")
    assert styled_b.space_before_pt > 0


def test_smart_layout_pagination(template_mgr):
    tpl = template_mgr.get_template("book")
    layout = SmartLayoutEngine(tpl)

    blocks = [
        Block(block_type=BlockType.CHAPTER_TITLE, text="Chapter 1"),
        Block(block_type=BlockType.BODY, text="First paragraph of the book."),
        Block(block_type=BlockType.BODY, text="Second paragraph of the book."),
    ]
    pages = layout.paginate(blocks, book_title="Test Novel")
    assert len(pages) >= 1
    assert pages[0].page_type == "Chapter Opening"


def test_formatting_engine_full_flow(template_mgr):
    tpl = template_mgr.get_template("academic_research")
    assert tpl.profile_name == "Academic Research Paper"

    # Also verify backward-compatible aliases work
    tpl_alias = template_mgr.get_template("journal")
    assert tpl_alias.profile_name == "Academic Research Paper"

    tpl_conf = template_mgr.get_template("technical")
    assert tpl_conf.profile_name == "Conference Paper"

    engine = FormattingEngine(tpl)
    doc = DocumentModel(
        blocks=[
            Block(block_type=BlockType.CHAPTER_TITLE, text="Chapter 1: Dawn"),
            Block(block_type=BlockType.BODY, text="The sun rose over the hills."),
        ]
    )
    formatted_doc, pages = engine.format_document(doc)
    assert len(pages) > 0
    assert formatted_doc.metadata.estimated_pages == len(pages)
