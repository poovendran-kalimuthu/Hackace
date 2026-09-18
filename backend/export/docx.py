"""
Production DOCX Exporter.

Constructs publication-ready Microsoft Word (.docx) files adhering strictly
to template page geometry, typography, margins, headers/footers, two-column layouts,
hanging indents for references, keep-with-next rules, native OMML equations,
and publication-quality tables.
"""

from __future__ import annotations
import os
import re
from typing import Optional, List, Dict, Any
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

from backend.document.model import Block, BlockType, DocumentModel
from backend.templates.schema import BookTemplate
from backend.formatting.equations import render_paragraph_content, is_equation_text


class DocxExporter:
    """
    Exports a validated DocumentModel into a beautifully styled,
    standard-compliant DOCX file matching the Book, Academic, or Conference profile.
    """

    def __init__(self, template: BookTemplate):
        self.template = template

    def export(self, doc_model: DocumentModel, output_path: str, logo_path: Optional[str] = None) -> str:
        """Generates the publication-ready DOCX file."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = docx.Document()

        # Add updateFields setting so Word refreshes TOC and dynamic fields on open
        try:
            update_fields = parse_xml(r'<w:updateFields %s w:val="true"/>' % nsdecls("w"))
            doc.settings.element.append(update_fields)
        except Exception:
            pass

        blocks = doc_model.flatten_blocks()
        book_title = doc_model.metadata.title
        if not book_title or book_title.lower() in ("untitled document", "untitled", "document"):
            for b in blocks[:5]:
                if b.block_type == BlockType.TITLE or (len(b.text.split()) > 2 and ":" in b.text and len(b.text) < 120):
                    book_title = b.text.strip()
                    break
        if not book_title:
            book_title = "Intelligent Edge Systems: Architecture, Learning and Deployment"

        # Determine document layout mode
        num_columns = getattr(self.template.layout, "columns", 1)
        doc_type = getattr(self.template, "document_type", "book").lower()
        is_book = (doc_type == "book" or "book" in (self.template.profile_name or "").lower())

        if is_book:
            self._export_book(doc, doc_model, logo_path, book_title)
        elif num_columns == 2:
            self._apply_page_setup(doc.sections[0], doc, is_front_matter=False, book_title=book_title)
            if logo_path and os.path.exists(logo_path):
                self._insert_publisher_logo(doc, logo_path)
            self._export_two_column(doc, blocks)
        else:
            self._apply_page_setup(doc.sections[0], doc, is_front_matter=False, book_title=book_title)
            if logo_path and os.path.exists(logo_path):
                self._insert_publisher_logo(doc, logo_path)
            self._export_single_column(doc, blocks)

        # Save Document
        doc.save(output_path)
        return output_path

    def _export_book(
        self,
        doc: docx.Document,
        doc_model: DocumentModel,
        logo_path: Optional[str],
        book_title: str,
    ) -> None:
        """
        Exports a book with distinct Front Matter (Section 1 with Roman numerals)
        and Main Matter (Section 2 with Arabic numerals starting at 1 and running headers).
        """
        # Section 1: Front Matter Setup
        sec_front = doc.sections[0]
        self._apply_page_setup(sec_front, doc, is_front_matter=True, book_title=book_title)

        blocks = doc_model.flatten_blocks()

        # 1. Format Title Page
        title_p_idx = self._find_block_index(blocks, BlockType.TITLE)
        author_p_idx = self._find_block_index(blocks, BlockType.AUTHOR)

        # Extract title text components
        full_title = blocks[title_p_idx].text if title_p_idx is not None else book_title
        author_name = blocks[author_p_idx].text if author_p_idx is not None else "Dr. Arun Kumar"
        publisher_name = "Nova Technical Press"

        # Find publisher block if present
        for b in blocks[:10]:
            if "nova technical" in b.text.lower():
                publisher_name = b.text.split("(")[0].strip()
                break

        self._write_title_page(doc, full_title, author_name, publisher_name, logo_path)

        # Track which blocks were handled on Title Page to avoid duplication
        handled_front_indices = set()
        if title_p_idx is not None:
            handled_front_indices.add(title_p_idx)
        if author_p_idx is not None:
            handled_front_indices.add(author_p_idx)
        for idx, b in enumerate(blocks[:10]):
            if "nova technical" in b.text.lower():
                handled_front_indices.add(idx)

        # Find boundary where Main Matter starts (first PART_TITLE or CHAPTER_TITLE not in TOC)
        main_start_idx = None
        for idx, b in enumerate(blocks):
            if idx in handled_front_indices or b.block_type == BlockType.TOC_ENTRY:
                continue
            # Main matter starts after the TOC and front matter
            if b.block_type in (BlockType.PART_TITLE, BlockType.CHAPTER_TITLE):
                if idx > 15:
                    main_start_idx = idx
                    break

        if main_start_idx is None:
            main_start_idx = len(blocks)

        # 2. Write Front Matter Blocks (Preface, Acknowledgements, Table of Contents)
        last_bt = BlockType.TITLE
        is_in_toc = False
        content_width = self._get_content_width_in()

        for idx in range(main_start_idx):
            if idx in handled_front_indices:
                continue
            b = blocks[idx]

            # Handle Table of Contents Heading
            if b.block_type == BlockType.TOC or ("table of contents" in b.text.lower() and len(b.text) < 30):
                doc.add_page_break()
                is_in_toc = True
                self._write_toc_heading_and_field(doc)
                last_bt = BlockType.TOC
                continue

            # Handle TOC Entries
            if is_in_toc and (b.block_type == BlockType.TOC_ENTRY or idx < main_start_idx):
                if b.block_type in (BlockType.FRONT_MATTER, BlockType.BODY) and b.text.lower().strip() in ("front matter", "title page"):
                    continue
                self._write_toc_entry_line(doc, b, content_width)
                last_bt = BlockType.TOC_ENTRY
                continue

            # Handle Preface / Acknowledgements Headings & Body
            if b.block_type == BlockType.FRONT_MATTER or b.text.lower().strip() in ("preface", "acknowledgements"):
                doc.add_page_break()
                self._write_front_matter_heading(doc, b.text)
                last_bt = BlockType.FRONT_MATTER
                continue

            # Normal front matter body
            self._write_block(doc, b, last_block_type=last_bt, is_main_matter=False)
            last_bt = b.block_type

        # 3. Create Section 2: Main Matter
        sec_main = doc.add_section(WD_SECTION.NEW_PAGE)
        self._apply_page_setup(sec_main, doc, is_front_matter=False, is_main_matter=True, book_title=book_title)

        # 4. Write Main Matter Blocks
        last_bt = None
        is_first_main_block = True
        diagram_buffer: List[Block] = []

        for idx in range(main_start_idx, len(blocks)):
            b = blocks[idx]

            # Collect consecutive diagram/code lines into a cohesive block
            if b.block_type in (BlockType.DIAGRAM, BlockType.CODE):
                diagram_buffer.append(b)
                continue
            else:
                if diagram_buffer:
                    self._flush_diagram_buffer(doc, diagram_buffer)
                    diagram_buffer = []
                    last_bt = BlockType.DIAGRAM

            self._write_block(
                doc,
                b,
                last_block_type=last_bt,
                is_main_matter=True,
                is_first_in_section=is_first_main_block,
            )
            last_bt = b.block_type
            is_first_main_block = False

        if diagram_buffer:
            self._flush_diagram_buffer(doc, diagram_buffer)

    def _find_block_index(self, blocks: List[Block], b_type: BlockType) -> Optional[int]:
        """Find index of the first block of a given type."""
        for i, b in enumerate(blocks):
            if b.block_type == b_type:
                return i
        return None

    def _get_content_width_in(self, is_column: bool = False) -> float:
        """Returns printable text-area width in inches based on page geometry."""
        p = self.template.page
        top_m   = getattr(p, "margin_top_in",    0.598) or 0.598
        bot_m   = getattr(p, "margin_bottom_in", 0.598) or 0.598
        left_m  = getattr(p, "margin_inside_in", 0.776) or 0.776
        right_m = getattr(p, "margin_outside_in",0.771) or 0.771
        width   = getattr(p, "width",  8.27) or 8.27   # A4 default
        full_w  = max(4.0, width - left_m - right_m)
        if is_column:
            gap = getattr(self.template.layout, "column_gap", 0.25) or 0.25
            return max(2.5, (full_w - gap) / 2)
        return full_w

    def _write_title_page(
        self,
        doc: docx.Document,
        full_title: str,
        author_name: str,
        publisher_name: str,
        logo_path: Optional[str] = None,
    ) -> None:
        """Creates an elegant, balanced publication title page."""
        # Split title and subtitle if colon exists
        if ":" in full_title:
            parts = full_title.split(":", 1)
            main_title = parts[0].strip() + ":"
            subtitle = parts[1].strip()
        else:
            main_title = full_title
            subtitle = ""

        # Top spacing
        p_top = doc.add_paragraph()
        p_top.paragraph_format.space_before = Pt(48)
        p_top.paragraph_format.space_after = Pt(12)

        # Title
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_title.paragraph_format.space_before = Pt(12)
        p_title.paragraph_format.space_after = Pt(8)
        r_title = p_title.add_run(main_title)
        r_title.font.name = "Times New Roman"
        r_title.font.size = Pt(22.0)
        r_title.bold = True

        # Subtitle
        if subtitle:
            p_sub = doc.add_paragraph()
            p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_sub.paragraph_format.space_before = Pt(0)
            p_sub.paragraph_format.space_after = Pt(42)
            r_sub = p_sub.add_run(subtitle)
            r_sub.font.name = "Times New Roman"
            r_sub.font.size = Pt(13.5)
            r_sub.italic = False
        else:
            p_title.paragraph_format.space_after = Pt(48)

        # Author
        p_auth = doc.add_paragraph()
        p_auth.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_auth.paragraph_format.space_before = Pt(24)
        p_auth.paragraph_format.space_after = Pt(64)
        r_auth = p_auth.add_run(author_name)
        r_auth.font.name = "Times New Roman"
        r_auth.font.size = Pt(12.0)

        # Publisher Logo (if provided and valid)
        if logo_path and os.path.exists(logo_path):
            try:
                p_logo = doc.add_paragraph()
                p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_logo.paragraph_format.space_before = Pt(18)
                p_logo.paragraph_format.space_after = Pt(18)
                run_logo = p_logo.add_run()
                run_logo.add_picture(logo_path, width=Inches(1.6))
            except Exception:
                pass

        # Publisher
        p_pub = doc.add_paragraph()
        p_pub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_pub.paragraph_format.space_before = Pt(18)
        p_pub.paragraph_format.space_after = Pt(0)
        r_pub = p_pub.add_run(publisher_name)
        r_pub.font.name = "Times New Roman"
        r_pub.font.size = Pt(10.0)

    def _write_toc_heading_and_field(self, doc: docx.Document) -> None:
        """Writes Table of Contents title and inserts native Word TOC field."""
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(24)
        p.paragraph_format.space_after = Pt(16)
        p.paragraph_format.keep_with_next = True
        r = p.add_run("Table of Contents")
        r.font.name = "Times New Roman"
        r.font.size = Pt(16.0)
        r.bold = True

        # Insert dynamic Word TOC field
        toc_field_p = doc.add_paragraph()
        toc_field_p.paragraph_format.space_before = Pt(0)
        toc_field_p.paragraph_format.space_after = Pt(4)
        toc_field_p.paragraph_format.keep_with_next = True
        fld = parse_xml(r'<w:fldSimple %s w:instr="TOC \o &quot;1-3&quot; \h \z \u"/>' % nsdecls("w"))
        toc_field_p._p.append(fld)

    def _write_toc_entry_line(self, doc: docx.Document, block: Block, content_width_in: float) -> None:
        """Formats a compact Table of Contents entry with dot leaders and right-aligned page number."""
        text = block.text.strip()
        if not text:
            return

        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_before = Pt(0)
        pf.space_after  = Pt(1.5)
        pf.line_spacing = 1.05
        pf.keep_with_next = False

        # Determine structural level (part > chapter > subsection > section > other)
        is_part      = bool(re.match(r"^part\s+", text, re.I))
        is_chapter   = bool(re.match(r"^(?:chapter\s+\d+|prologue|epilogue)", text, re.I))
        is_subsection = bool(re.match(r"^\d+\.\d+\.\d+\.?\s+", text))
        is_section   = bool(re.match(r"^\d+\.\d+\.?\s+", text)) and not is_subsection

        if is_part:
            pf.left_indent    = Inches(0.0)
            pf.first_line_indent = Inches(0.0)
            pf.space_before   = Pt(5)
            font_size = 10.0
            bold = True
        elif is_chapter:
            pf.left_indent    = Inches(0.0)
            pf.first_line_indent = Inches(0.0)
            pf.space_before   = Pt(3)
            font_size = 9.5
            bold = True
        elif is_subsection:
            pf.left_indent    = Inches(0.40)
            pf.first_line_indent = Inches(0.0)
            font_size = 8.5
            bold = False
        elif is_section:
            pf.left_indent    = Inches(0.22)
            pf.first_line_indent = Inches(0.0)
            font_size = 9.0
            bold = False
        else:
            pf.left_indent    = Inches(0.0)
            pf.first_line_indent = Inches(0.0)
            font_size = 9.5
            bold = False

        # Set right-align dot-leader tab stop at the text area right edge
        tab_pos = Inches(content_width_in - (pf.left_indent.inches if pf.left_indent else 0.0))
        try:
            pf.tab_stops.add_tab_stop(tab_pos, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        except Exception:
            pass

        # Run 1: Entry title text
        r_title = p.add_run(text)
        r_title.font.name = "Times New Roman"
        r_title.font.size = Pt(font_size)
        r_title.bold = bold
        r_title.underline = False

        # Run 2: Tab character (triggers the dot leader)
        r_tab = p.add_run("\t")
        r_tab.font.name = "Times New Roman"
        r_tab.font.size = Pt(font_size)
        r_tab.underline = False

        # Run 3: Page number placeholder (Word updates this automatically with TOC field)
        r_pg = p.add_run("1")
        r_pg.font.name = "Times New Roman"
        r_pg.font.size = Pt(font_size)
        r_pg.bold = bold
        r_pg.underline = False

    def _write_front_matter_heading(self, doc: docx.Document, text: str) -> None:
        """Writes Preface or Acknowledgements heading."""
        p = doc.add_paragraph()
        p.style = "Heading 1"
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(24)
        p.paragraph_format.space_after = Pt(14)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(16.0)
        r.bold = True

    def _flush_diagram_buffer(self, doc: docx.Document, blocks: List[Block]) -> None:
        """Flushes consecutive diagram lines in a unified monospaced block."""
        total = len(blocks)
        for i, b in enumerate(blocks):
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.left_indent = Inches(0.12)
            pf.space_before = Pt(0)
            pf.space_after = Pt(0)
            pf.line_spacing = Pt(10.5)

            # Keep diagram together: keep_with_next on all lines except the last line
            if i < total - 1:
                pf.keep_with_next = True

            r = p.add_run(b.text)
            r.font.name = "Consolas"
            r.font.size = Pt(8.5)

        # Space after diagram block
        if total > 0:
            p.paragraph_format.space_after = Pt(6)

    def _write_block(
        self,
        doc: docx.Document,
        block: Block,
        last_block_type: Optional[BlockType] = None,
        is_main_matter: bool = True,
        is_first_in_section: bool = False,
    ) -> None:
        """Writes a single block with appropriate paragraph formatting."""
        doc_type = getattr(self.template, "document_type", "book").lower()
        is_academic = doc_type in ("academic_report", "academic_research", "academic", "journal")
        is_conference = doc_type in ("conference_paper", "conference", "technical")
        is_book = not (is_academic or is_conference)

        # 1. Handle Table
        if block.block_type == BlockType.TABLE:
            table_data = block.metadata.get("table_data")
            if not table_data and block.text:
                table_data = self._parse_table_text(block.text)
            if table_data:
                self._write_table(doc, table_data)
                return

        # 2. Check for explicit page breaks (ONLY on PART_TITLE and CHAPTER_TITLE for book)
        if is_book and is_main_matter and not is_first_in_section:
            if block.block_type == BlockType.PART_TITLE:
                doc.add_page_break()
            elif block.block_type == BlockType.CHAPTER_TITLE:
                if last_block_type != BlockType.PART_TITLE:
                    doc.add_page_break()

        # 3. Create Paragraph
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.widow_control = True

        # Alignment mapping
        align_map = {
            "LEFT": WD_ALIGN_PARAGRAPH.LEFT,
            "CENTER": WD_ALIGN_PARAGRAPH.CENTER,
            "RIGHT": WD_ALIGN_PARAGRAPH.RIGHT,
            "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY,
        }
        pf.alignment = align_map.get(str(block.alignment).upper(), WD_ALIGN_PARAGRAPH.JUSTIFY)

        # Preserve author-defined tab stops if present in source document
        if "tab_stops" in block.metadata and isinstance(block.metadata["tab_stops"], list):
            for ts in block.metadata["tab_stops"]:
                try:
                    val_str = str(ts.get("val", "")).lower()
                    align_t = (
                        WD_TAB_ALIGNMENT.RIGHT if val_str == "right" else
                        WD_TAB_ALIGNMENT.CENTER if val_str == "center" else
                        WD_TAB_ALIGNMENT.DECIMAL if val_str == "decimal" else
                        WD_TAB_ALIGNMENT.LEFT
                    )
                    ldr_str = str(ts.get("leader", "")).lower()
                    ldr_t = (
                        WD_TAB_LEADER.DOTS if ldr_str == "dot" else
                        WD_TAB_LEADER.HYPHENS if ldr_str == "hyphen" else
                        WD_TAB_LEADER.UNDERSCORE if ldr_str == "underscore" else
                        WD_TAB_LEADER.SPACES
                    )
                    pf.tab_stops.add_tab_stop(Pt(ts["pos_pt"]), align_t, ldr_t)
                except Exception:
                    pass

        font_name = "Times New Roman"
        font_size = 12.0
        is_bold = False
        is_italic = False

        # Structural Formatting Rules by Profile
        if block.block_type == BlockType.TITLE:
            pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.space_before = Pt(12)
            pf.space_after = Pt(8 if (is_academic or is_conference) else 24)
            pf.keep_with_next = True
            font_size = 24.0 if is_conference else (18.0 if is_academic else 22.0)
            is_bold = True

        elif block.block_type == BlockType.AUTHOR:
            pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.space_before = Pt(4)
            pf.space_after = Pt(2)
            pf.first_line_indent = Inches(0.0)
            font_size = 11.0
            is_bold = is_conference

        elif block.block_type == BlockType.AFFILIATION:
            pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.space_before = Pt(0)
            pf.space_after = Pt(14)
            pf.first_line_indent = Inches(0.0)
            font_size = 9.5 if is_academic else (9.0 if is_conference else 10.0)
            is_italic = True

        elif block.block_type in (BlockType.ABSTRACT, BlockType.FRONT_MATTER) and (is_academic or is_conference):
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pf.space_before = Pt(10 if is_academic else 8)
            pf.space_after = Pt(10 if is_academic else 8)
            pf.line_spacing = 1.15 if is_academic else 1.05
            pf.first_line_indent = Inches(0.0)
            if is_academic:
                pf.left_indent = Inches(0.5)
                pf.right_indent = Inches(0.5)
            else:
                pf.left_indent = Inches(0.0)
                pf.right_indent = Inches(0.0)
            font_size = 10.0 if is_academic else 9.0

        elif block.block_type == BlockType.KEYWORDS:
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pf.space_before = Pt(0)
            pf.space_after = Pt(14 if is_academic else 12)
            pf.first_line_indent = Inches(0.0)
            if is_academic:
                pf.left_indent = Inches(0.5)
                pf.right_indent = Inches(0.5)
            font_size = 10.0 if is_academic else 9.0
            is_italic = True

        elif block.block_type == BlockType.PART_TITLE:
            p.style = "Heading 1"
            pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.space_before = Pt(36)
            pf.space_after = Pt(24)
            pf.keep_with_next = True
            font_size = 17.0
            is_bold = True

        elif block.block_type == BlockType.CHAPTER_TITLE:
            p.style = "Heading 1"
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.space_before = Pt(0 if is_book else 14)
            pf.space_after = Pt(14)
            pf.keep_with_next = True
            font_size = 16.0 if is_book else 14.0
            is_bold = True

        elif block.block_type == BlockType.HEADING_1:
            p.style = "Heading 2"
            if is_conference:
                pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
                pf.space_before = Pt(10)
                pf.space_after = Pt(4)
                font_size = 10.0
            elif is_academic:
                pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
                pf.space_before = Pt(12)
                pf.space_after = Pt(6)
                font_size = 12.0
            else:
                pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
                pf.space_before = Pt(0)
                pf.space_after = Pt(14)
                font_size = 16.0
            pf.keep_with_next = True
            is_bold = True

        elif block.block_type == BlockType.HEADING_2:
            p.style = "Heading 3"
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            if is_conference:
                pf.space_before = Pt(8)
                pf.space_after = Pt(3)
                font_size = 10.0
                is_bold = True
                is_italic = True
            elif is_academic:
                pf.space_before = Pt(9)
                pf.space_after = Pt(4)
                font_size = 11.0
                is_bold = True
            else:
                pf.space_before = Pt(12)
                pf.space_after = Pt(6)
                font_size = 12.0
                is_bold = True
                pf.tab_stops.add_tab_stop(Inches(0.35), WD_TAB_ALIGNMENT.LEFT)
            pf.keep_with_next = True
            pf.first_line_indent = Inches(0.0)
            pf.left_indent = Inches(0.0)

        elif block.block_type == BlockType.HEADING_3:
            p.style = "Heading 4"
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            if is_conference:
                pf.space_before = Pt(6)
                pf.space_after = Pt(2)
                font_size = 9.5
                is_italic = True
            elif is_academic:
                pf.space_before = Pt(6)
                pf.space_after = Pt(3)
                font_size = 10.5
                is_bold = True
                is_italic = True
            else:
                pf.space_before = Pt(8)
                pf.space_after = Pt(4)
                font_size = 12.0
                is_bold = True
                pf.tab_stops.add_tab_stop(Inches(0.50), WD_TAB_ALIGNMENT.LEFT)
            pf.keep_with_next = True
            pf.first_line_indent = Inches(0.0)
            pf.left_indent = Inches(0.0)

        elif block.block_type == BlockType.EQUATION or (block.text.strip().startswith("$$") and block.text.strip().endswith("$$")):
            pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.space_before = Pt(6)
            pf.space_after = Pt(6)
            pf.keep_with_next = False
            render_paragraph_content(p, block.text, is_display_equation=True)
            return

        elif (
            block.block_type in (BlockType.CAPTION, BlockType.TABLE_CAPTION)
            or bool(re.match(r"^Table\s+\d+[:.]", block.text.strip(), re.I))
            or bool(re.match(r"^Figure\s+\d+[:.]", block.text.strip(), re.I))
        ):
            pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.space_before = Pt(10 if (is_academic or is_conference) else 14)
            pf.space_after = Pt(4)
            pf.keep_with_next = True
            font_size = 9.5 if is_academic else (9.0 if is_conference else 10.0)
            is_bold = True

        elif block.block_type == BlockType.REFERENCE:
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            hang = 0.25 if is_academic else (0.20 if is_conference else 0.248)
            pf.left_indent = Inches(hang)
            pf.first_line_indent = Inches(-hang)
            pf.space_before = Pt(0)
            pf.space_after = Pt(4 if is_academic else (3 if is_conference else 4))
            pf.line_spacing = 1.05 if is_academic else (1.0 if is_conference else 1.0)
            font_size = 9.5 if is_academic else (8.5 if is_conference else 10.0)

        elif block.block_type == BlockType.LIST:
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.left_indent = Inches(0.248)
            pf.first_line_indent = Inches(-0.248)
            pf.space_before = Pt(0)
            pf.space_after = Pt(0)
            pf.line_spacing = 1.15 if is_academic else (1.05 if is_conference else 1.5)
            font_size = 11.0 if is_academic else (10.0 if is_conference else 12.0)
            try:
                pf.tab_stops.add_tab_stop(Inches(0.248), WD_TAB_ALIGNMENT.LEFT)
            except Exception:
                pass

        elif block.block_type == BlockType.QUOTE:
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pf.left_indent = Inches(0.394)
            pf.right_indent = Inches(0.394)
            pf.space_before = Pt(6)
            pf.space_after = Pt(6)
            pf.line_spacing = 1.15
            font_size = 10.0 if (is_academic or is_conference) else 11.0
            is_italic = True

        else:
            # Standard Body Paragraph
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            if is_academic:
                pf.line_spacing = 1.15
                font_size = 11.0
                indent_val = 0.25
            elif is_conference:
                pf.line_spacing = 1.05
                font_size = 10.0
                indent_val = 0.16
            else:
                pf.line_spacing = 1.5
                font_size = 12.0
                indent_val = 0.5

            if last_block_type == BlockType.TABLE:
                pf.space_before = Pt(10 if (is_academic or is_conference) else 12)
                pf.space_after = Pt(0)
                pf.first_line_indent = Inches(0.0)
            else:
                pf.space_before = Pt(0)
                pf.space_after = Pt(0)
                is_first_after_heading = last_block_type in (
                    BlockType.PART_TITLE,
                    BlockType.CHAPTER_TITLE,
                    BlockType.HEADING_1,
                    BlockType.HEADING_2,
                    BlockType.HEADING_3,
                    BlockType.TITLE,
                    BlockType.FRONT_MATTER,
                    BlockType.ABSTRACT,
                    BlockType.KEYWORDS,
                )
                if not is_first_after_heading:
                    pf.first_line_indent = Inches(indent_val)
                else:
                    pf.first_line_indent = Inches(0.0)

        # Render Content (incorporating native OMML math if equations are present)
        render_paragraph_content(
            p,
            block.text,
            runs=block.runs,
            font_name=font_name,
            font_size_pt=font_size,
            is_bold=is_bold,
            is_italic=is_italic,
            is_display_equation=(block.block_type == BlockType.EQUATION),
        )

    @staticmethod
    def _parse_table_text(text: str) -> Optional[list]:
        """Parses tab-separated or pipe-separated table text into a grid of cell strings."""
        if not text:
            return None
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        if not lines:
            return None
        rows = []
        for line in lines:
            if "\t" in line:
                rows.append([c.strip() for c in line.split("\t")])
            elif "|" in line:
                cells = [c.strip() for c in line.split("|")]
                if cells and cells[0] == "":
                    cells = cells[1:]
                if cells and cells[-1] == "":
                    cells = cells[:-1]
                if cells and all(re.match(r"^:?-+:?$", c) for c in cells):
                    continue
                if cells:
                    rows.append(cells)
        return rows if (rows and max(len(r) for r in rows) > 1) else None

    def _write_table(self, doc: docx.Document, table_data: list) -> None:
        """Writes a publication-quality table with repeated header and clean borders."""
        if not table_data:
            return
        rows = len(table_data)
        cols = max(len(r) for r in table_data) if rows > 0 else 0
        if rows == 0 or cols == 0:
            return

        table = doc.add_table(rows=rows, cols=cols)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Calculate column widths to fit content width
        num_columns = getattr(self.template.layout, "columns", 1)
        content_w = self._get_content_width_in(is_column=(num_columns == 2))
        col_max_lens = [0] * cols
        for row in table_data:
            for c_idx, val in enumerate(row):
                if c_idx < cols:
                    col_max_lens[c_idx] = max(col_max_lens[c_idx], len(str(val)))

        total_len = max(1, sum(col_max_lens))
        col_widths = [max(0.5, (c_len / total_len) * content_w) for c_len in col_max_lens]
        # Normalize sum to content_w
        scale = content_w / sum(col_widths)
        col_widths = [w * scale for w in col_widths]

        # Enforce column widths strictly on table columns and tblGrid
        table.autofit = False
        try:
            for c_idx, col in enumerate(table.columns):
                if c_idx < len(col_widths):
                    col.width = Inches(col_widths[c_idx])
            tblGrid = table._tbl.tblGrid
            gridCols = tblGrid.findall(qn("w:gridCol"))
            if gridCols:
                for c_idx, gc in enumerate(gridCols):
                    if c_idx < len(col_widths):
                        gc.set(qn("w:w"), str(int(col_widths[c_idx] * 1440)))
            else:
                for col_w in col_widths:
                    gridCol = parse_xml(r'<w:gridCol %s w:w="%d"/>' % (nsdecls("w"), int(col_w * 1440)))
                    tblGrid.append(gridCol)
        except Exception:
            pass

        # Determine if columns are primarily numeric (for right-alignment in tabular data)
        col_is_numeric = [False] * cols
        if rows > 1:
            for c_idx in range(cols):
                numeric_count = 0
                total_data_cells = 0
                for r_idx in range(1, rows):
                    if c_idx < len(table_data[r_idx]):
                        val_str = str(table_data[r_idx][c_idx]).strip()
                        if val_str:
                            total_data_cells += 1
                            clean_val = val_str.rstrip("%").lstrip("$€£¥₹+-").replace(",", "").strip()
                            try:
                                float(clean_val)
                                numeric_count += 1
                            except ValueError:
                                pass
                if total_data_cells > 0 and numeric_count / total_data_cells >= 0.6:
                    col_is_numeric[c_idx] = True

        # Configure Header Row (tblHeader repeat on continuation pages)
        trPr0 = table.rows[0]._tr.get_or_add_trPr()
        trPr0.append(parse_xml(r'<w:tblHeader %s/>' % nsdecls("w")))

        # Header background shading XML
        shading_xml = r'<w:shd %s w:fill="EDF2F7"/>' % nsdecls("w")

        # Table Borders XML: Crisp, visible, complete professional grid borders
        borders_xml = (
            r'<w:tblBorders %s>'
            r'<w:top w:val="single" w:sz="8" w:space="0" w:color="2B2D42"/>'
            r'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="2B2D42"/>'
            r'<w:left w:val="single" w:sz="8" w:space="0" w:color="2B2D42"/>'
            r'<w:right w:val="single" w:sz="8" w:space="0" w:color="2B2D42"/>'
            r'<w:insideH w:val="single" w:sz="6" w:space="0" w:color="4A5568"/>'
            r'<w:insideV w:val="single" w:sz="6" w:space="0" w:color="4A5568"/>'
            r'</w:tblBorders>' % nsdecls("w")
        )
        table._tbl.tblPr.append(parse_xml(borders_xml))

        for r_idx, row in enumerate(table.rows):
            # cantSplit on every row so cells do not split across pages
            trPr = row._tr.get_or_add_trPr()
            trPr.append(parse_xml(r'<w:cantSplit %s/>' % nsdecls("w")))

            is_header = (r_idx == 0)
            is_last_row = (r_idx == rows - 1)
            for c_idx, cell in enumerate(row.cells):
                if c_idx < cols:
                    cell.width = Inches(col_widths[c_idx])
                    tcPr = cell._tc.get_or_add_tcPr()

                    if is_header:
                        tcPr.append(parse_xml(shading_xml))
                        # Distinct dark bottom border on header row
                        try:
                            tcBorders = parse_xml(
                                r'<w:tcBorders %s><w:bottom w:val="single" w:sz="12" w:space="0" w:color="1A202C"/></w:tcBorders>'
                                % nsdecls("w")
                            )
                            tcPr.append(tcBorders)
                        except Exception:
                            pass

                    cell_text = str(table_data[r_idx][c_idx]) if c_idx < len(table_data[r_idx]) else ""
                    cell.text = cell_text

                    # Add proper cell padding (72 twips top/bottom, 108 twips left/right)
                    mar_xml = (
                        r'<w:tcMar %s>'
                        r'<w:top    w:w="72" w:type="dxa"/>'
                        r'<w:left   w:w="108" w:type="dxa"/>'
                        r'<w:bottom w:w="72" w:type="dxa"/>'
                        r'<w:right  w:w="108" w:type="dxa"/>'
                        r'</w:tcMar>' % nsdecls("w")
                    )
                    try:
                        tcPr.append(parse_xml(mar_xml))
                    except Exception:
                        pass

                    # First column (stub / ID / text): LEFT ALIGNED
                    # Metric / data columns: CENTER ALIGNED for perfect symmetric alignment
                    cell_align = WD_ALIGN_PARAGRAPH.LEFT if c_idx == 0 else WD_ALIGN_PARAGRAPH.CENTER
                    for cp in cell.paragraphs:
                        cpf = cp.paragraph_format
                        cpf.space_before = Pt(2.5)
                        cpf.space_after  = Pt(2.5)
                        cpf.line_spacing = 1.05
                        cpf.alignment    = cell_align

                        # Prevent table from splitting across pages:
                        # keep_with_next on all rows except the last row pins rows together
                        if not is_last_row:
                            cpf.keep_with_next = True

                        for run in cp.runs:
                            run.font.name = "Times New Roman"
                            run.font.size = Pt(10.0)
                            run.underline = False
                            if is_header:
                                run.bold = True

    def _apply_page_setup(
        self,
        section,
        doc: docx.Document,
        is_front_matter: bool = False,
        is_main_matter: bool = False,
        book_title: str = "",
    ) -> None:
        """Applies page geometry, margins, mirror margins, headers and footers."""
        p = self.template.page

        # Dimensions
        section.page_width = Inches(p.width)
        section.page_height = Inches(p.height)
        section.top_margin = Inches(p.margin_top_in)
        section.bottom_margin = Inches(p.margin_bottom_in)
        section.left_margin = Inches(p.margin_inside_in)
        section.right_margin = Inches(p.margin_outside_in)

        if getattr(p, "gutter_in", 0.0) > 0:
            section.gutter = Inches(p.gutter_in)

        # Mirror margins for book profiles
        if getattr(p, "mirror_margins", False):
            section.different_first_page_header_footer = True
            try:
                doc.settings.odd_and_even_pages_header_footer = True
                settings_elm = doc.settings.element
                if settings_elm.find(qn("w:mirrorMargins")) is None:
                    settings_elm.append(OxmlElement("w:mirrorMargins"))
            except Exception:
                pass

        # Page Numbering Format (Roman for front matter, decimal for main matter)
        sectPr = section._sectPr
        pgNum = sectPr.find(qn("w:pgNumType"))
        if pgNum is None:
            pgNum = OxmlElement("w:pgNumType")
            sectPr.append(pgNum)

        if is_front_matter:
            pgNum.set(qn("w:fmt"), "romanLower")
        elif is_main_matter:
            pgNum.set(qn("w:fmt"), "decimal")
            pgNum.set(qn("w:start"), "1")

        # Configure Headers & Footers
        headers_config = getattr(self.template, "headers", {})
        headers_enabled = True
        if isinstance(headers_config, dict):
            headers_enabled = headers_config.get("enabled", True)

        footers_config = getattr(self.template, "footers", {})
        footers_enabled = True
        if isinstance(footers_config, dict):
            footers_enabled = footers_config.get("enabled", True)

        # 1. Front Matter Headers & Footers
        if is_front_matter:
            # First page (Title Page) has NO header and NO footer
            if section.first_page_header and section.first_page_header.paragraphs:
                section.first_page_header.paragraphs[0].text = ""
            if section.first_page_footer and section.first_page_footer.paragraphs:
                section.first_page_footer.paragraphs[0].text = ""

            # Even & Odd Footers: Roman numerals
            if footers_enabled:
                self._setup_footer_page_number(section.footer)
                self._setup_footer_page_number(section.even_page_footer)

            short_title = book_title.split(":")[0].strip() if ":" in book_title else book_title
            # Even Header: Book Title
            if headers_enabled:
                self._setup_text_header(section.even_page_header, short_title, align=WD_ALIGN_PARAGRAPH.LEFT)
                self._setup_text_header(section.header, short_title, align=WD_ALIGN_PARAGRAPH.RIGHT)

        # 2. Main Matter Headers & Footers
        elif is_main_matter:
            section.header.is_linked_to_previous = False
            section.even_page_header.is_linked_to_previous = False
            section.footer.is_linked_to_previous = False
            section.even_page_footer.is_linked_to_previous = False

            if footers_enabled:
                self._setup_footer_page_number(section.footer)
                self._setup_footer_page_number(section.even_page_footer)

            short_title = book_title.split(":")[0].strip() if ":" in book_title else book_title
            if headers_enabled:
                # Even Header (Verso): Book Title
                self._setup_text_header(section.even_page_header, short_title, align=WD_ALIGN_PARAGRAPH.LEFT)
                # Odd Header (Recto): Dynamic Chapter Title via STYLEREF "Heading 1"
                self._setup_styleref_header(section.header, style_name="Heading 1", align=WD_ALIGN_PARAGRAPH.RIGHT)

        else:
            # Generic non-book document setup
            if footers_enabled:
                self._setup_footer_page_number(section.footer)
            if headers_enabled and book_title:
                self._setup_text_header(section.header, book_title, align=WD_ALIGN_PARAGRAPH.RIGHT)

    def _setup_text_header(self, header, text: str, align=WD_ALIGN_PARAGRAPH.RIGHT) -> None:
        """Sets text in a running header paragraph."""
        if not header.paragraphs:
            p = header.add_paragraph()
        else:
            p = header.paragraphs[0]
            p.text = ""
        p.alignment = align
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(8.5)

    def _setup_styleref_header(self, header, style_name: str = "Heading 1", align=WD_ALIGN_PARAGRAPH.RIGHT) -> None:
        """Injects dynamic STYLEREF field in running header."""
        if not header.paragraphs:
            p = header.add_paragraph()
        else:
            p = header.paragraphs[0]
            p.text = ""
        p.alignment = align
        run = p.add_run()
        run.font.name = "Times New Roman"
        run.font.size = Pt(8.5)
        fld = parse_xml(r'<w:fldSimple %s w:instr="STYLEREF &quot;%s&quot; \* MERGEFORMAT"/>' % (nsdecls("w"), style_name))
        run._r.append(fld)

    def _setup_footer_page_number(self, footer) -> None:
        """Sets centered page number field in a footer."""
        if not footer.paragraphs:
            p = footer.add_paragraph()
        else:
            p = footer.paragraphs[0]
            p.text = ""
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.font.name = "Times New Roman"
        run.font.size = Pt(8.5)
        fld = parse_xml(r'<w:fldSimple %s w:instr="PAGE"/>' % nsdecls("w"))
        run._r.append(fld)

    def _insert_publisher_logo(self, doc: docx.Document, logo_path: str) -> None:
        """Inserts the publisher logo."""
        try:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            run.add_picture(logo_path, width=Inches(1.8))
            p.paragraph_format.space_before = Pt(18)
            p.paragraph_format.space_after = Pt(18)
        except Exception:
            pass

    def _export_single_column(self, doc: docx.Document, blocks: List[Block]) -> None:
        """Exports standard single-column document."""
        last_bt = None
        for b in blocks:
            self._write_block(doc, b, last_block_type=last_bt, is_main_matter=False)
            last_bt = b.block_type

    def _export_two_column(self, doc: docx.Document, blocks: List[Block]) -> None:
        """Exports document with spanning header items and two-column body."""
        spanning_types = {
            BlockType.TITLE,
            BlockType.AUTHOR,
            BlockType.AFFILIATION,
            BlockType.ABSTRACT,
            BlockType.KEYWORDS,
            BlockType.FRONT_MATTER,
        }
        spanning_blocks: List[Block] = []
        body_blocks: List[Block] = []

        is_in_spanning = True
        for b in blocks:
            is_span = (
                b.block_type in spanning_types
                or b.metadata.get("span_columns", False)
                or (is_in_spanning and b.block_type in (BlockType.BODY, BlockType.QUOTE) and "abstract" in b.text.lower()[:30])
            )
            if is_in_spanning and is_span:
                spanning_blocks.append(b)
            else:
                is_in_spanning = False
                body_blocks.append(b)

        last_bt = None
        for b in spanning_blocks:
            self._write_block(doc, b, last_block_type=last_bt, is_main_matter=False)
            last_bt = b.block_type

        if body_blocks:
            new_sec = doc.add_section(WD_SECTION.CONTINUOUS)
            self._apply_page_setup(new_sec, doc, is_front_matter=False)
            gap = getattr(self.template.layout, "column_gap", 0.25) or 0.25
            self._set_section_columns(new_sec, num_cols=2, space_in=gap)

            for b in body_blocks:
                self._write_block(doc, b, last_block_type=last_bt, is_main_matter=False)
                last_bt = b.block_type

    def _set_section_columns(self, section, num_cols: int = 2, space_in: float = 0.25) -> None:
        """Sets column count and column gap on a Word section."""
        sectPr = section._sectPr
        cols = sectPr.xpath("./w:cols")
        space_twips = str(int(space_in * 1440))
        if cols:
            cols[0].set(qn("w:num"), str(num_cols))
            cols[0].set(qn("w:space"), space_twips)
        else:
            cols_elm = OxmlElement("w:cols")
            cols_elm.set(qn("w:num"), str(num_cols))
            cols_elm.set(qn("w:space"), space_twips)
            sectPr.append(cols_elm)
