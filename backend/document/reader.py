"""
Streaming OOXML Document Reader.

Handles both high-level python-docx extraction and low-level lxml streaming
via zipfile and iterparse to scan 10,000+ page documents without loading
the complete XML tree into RAM.
"""

from __future__ import annotations
import os
import zipfile
from typing import Any, Dict, Generator, List, Optional, Tuple
from lxml import etree
import docx
from docx.shared import Pt, Inches

from .model import Block, BlockType, DocumentMetadata, Run

# WordprocessingML XML Namespaces
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"

NAMESPACES = {
    "w": W_NS,
    "r": R_NS,
    "cp": CP_NS,
    "dc": DC_NS,
    "dcterms": DCTERMS_NS,
}


class DocxReader:
    """
    High-performance, memory-efficient DOCX reader capable of streaming
    manuscripts containing tens of thousands of paragraphs.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        self.file_size = os.path.getsize(file_path)

    def extract_metadata(self) -> DocumentMetadata:
        """Extract core document metadata without loading document body."""
        meta = DocumentMetadata(
            source_filename=os.path.basename(self.file_path),
            file_size_bytes=self.file_size,
        )

        try:
            with zipfile.ZipFile(self.file_path, "r") as z:
                if "docProps/core.xml" in z.namelist():
                    with z.open("docProps/core.xml") as f:
                        tree = etree.parse(f)
                        root = tree.getroot()
                        title_el = root.find(f"{{{DC_NS}}}title")
                        creator_el = root.find(f"{{{DC_NS}}}creator")
                        created_el = root.find(f"{{{DCTERMS_NS}}}created")

                        if title_el is not None and title_el.text:
                            meta.title = title_el.text
                        if creator_el is not None and creator_el.text:
                            meta.author = creator_el.text
                        if created_el is not None and created_el.text:
                            meta.created_date = created_el.text
        except Exception:
            # Fallback if core.xml is corrupted or absent
            pass

        return meta

    def extract_relationships(self) -> Dict[str, Dict[str, str]]:
        """Extract media and hyperlink relationships from document.xml.rels."""
        rels: Dict[str, Dict[str, str]] = {}
        try:
            with zipfile.ZipFile(self.file_path, "r") as z:
                rel_path = "word/_rels/document.xml.rels"
                if rel_path in z.namelist():
                    with z.open(rel_path) as f:
                        tree = etree.parse(f)
                        for elem in tree.getroot():
                            r_id = elem.get("Id")
                            r_type = elem.get("Type")
                            target = elem.get("Target")
                            if r_id:
                                rels[r_id] = {
                                    "type": r_type or "",
                                    "target": target or "",
                                }
        except Exception:
            pass
        return rels

    def stream_raw_blocks(self) -> Generator[Block, None, None]:
        """
        Stream paragraphs, tables, and section breaks via iterparse.
        Clears XML elements as they are read to guarantee O(1) memory consumption
        even on 10,000+ page files.
        """
        try:
            with zipfile.ZipFile(self.file_path, "r") as z:
                if "word/document.xml" not in z.namelist():
                    return

                with z.open("word/document.xml") as xml_file:
                    # Stream over paragraphs (w:p) and tables (w:tbl)
                    context = etree.iterparse(
                        xml_file,
                        events=("end",),
                        tag=(f"{{{W_NS}}}p", f"{{{W_NS}}}tbl"),
                    )

                    idx = 0
                    for event, elem in context:
                        # Skip paragraphs inside table cells so they are not yielded as separate body blocks
                        # and not cleared before the table itself is parsed!
                        if elem.tag == f"{{{W_NS}}}p" and self._is_inside_table(elem):
                            continue

                        block = self._parse_element(elem, idx)
                        if block:
                            yield block
                            idx += 1

                        # Crucial for 10,000+ pages: free memory in lxml tree
                        elem.clear()
                        while elem.getprevious() is not None:
                            del elem.getparent()[0]
        except Exception as e:
            # If iterparse fails (e.g. malformed low-level XML), fallback to python-docx
            yield from self._fallback_python_docx_stream()

    @staticmethod
    def _is_inside_table(elem: etree._Element) -> bool:
        """Returns True if the element is inside a w:tbl (table)."""
        curr = elem.getparent()
        while curr is not None:
            if curr.tag == f"{{{W_NS}}}tbl":
                return True
            if curr.tag == f"{{{W_NS}}}body":
                return False
            curr = curr.getparent()
        return False

    def _parse_element(self, elem: etree._Element, index: int) -> Optional[Block]:
        tag = elem.tag
        if tag == f"{{{W_NS}}}p":
            return self._parse_paragraph_element(elem, index)
        elif tag == f"{{{W_NS}}}tbl":
            return self._parse_table_element(elem, index)
        return None

    def _parse_paragraph_element(self, elem: etree._Element, index: int) -> Block:
        runs: List[Run] = []
        p_text_parts: List[str] = []
        is_page_break = False

        # Extract paragraph properties
        style_name = "Normal"
        alignment = "LEFT"
        pPr = elem.find(f"{{{W_NS}}}pPr")
        left_indent = 0.0
        right_indent = 0.0
        space_before = 0.0
        space_after = 0.0
        line_spacing = 1.15

        if pPr is not None:
            pStyle = pPr.find(f"{{{W_NS}}}pStyle")
            if pStyle is not None:
                style_name = pStyle.get(f"{{{W_NS}}}val", "Normal")

            jc = pPr.find(f"{{{W_NS}}}jc")
            if jc is not None:
                val = jc.get(f"{{{W_NS}}}val", "left").upper()
                alignment = val if val in ("LEFT", "CENTER", "RIGHT", "BOTH", "JUSTIFY") else "LEFT"
                if alignment == "BOTH":
                    alignment = "JUSTIFY"

            spacing = pPr.find(f"{{{W_NS}}}spacing")
            if spacing is not None:
                before = spacing.get(f"{{{W_NS}}}before")
                after = spacing.get(f"{{{W_NS}}}after")
                line = spacing.get(f"{{{W_NS}}}line")
                if before and before.isdigit():
                    space_before = float(before) / 20.0  # dxa to pt
                if after and after.isdigit():
                    space_after = float(after) / 20.0
                if line and line.isdigit():
                    line_spacing = round(float(line) / 240.0, 2)

            ind = pPr.find(f"{{{W_NS}}}ind")
            if ind is not None:
                left = ind.get(f"{{{W_NS}}}left")
                right = ind.get(f"{{{W_NS}}}right")
                if left and left.isdigit():
                    left_indent = float(left) / 20.0
                if right and right.isdigit():
                    right_indent = float(right) / 20.0

            # Extract tab stops if defined on paragraph
            tabs_el = pPr.find(f"{{{W_NS}}}tabs")
            tab_stops = []
            if tabs_el is not None:
                for tab in tabs_el.findall(f"{{{W_NS}}}tab"):
                    val = tab.get(f"{{{W_NS}}}val", "left")
                    leader = tab.get(f"{{{W_NS}}}leader", "none")
                    pos = tab.get(f"{{{W_NS}}}pos")
                    if pos and pos.lstrip("-").isdigit():
                        tab_stops.append({
                            "val": val,
                            "leader": leader,
                            "pos_pt": float(pos) / 20.0,
                        })

            # Check for page break before
            if pPr.find(f"{{{W_NS}}}pageBreakBefore") is not None:
                is_page_break = True
        else:
            tab_stops = []

        # Extract runs
        images_found: List[str] = []
        for r_elem in elem.findall(f"{{{W_NS}}}r"):
            r_text_parts: List[str] = []

            # Check for explicit page break inside run
            for br in r_elem.findall(f"{{{W_NS}}}br"):
                if br.get(f"{{{W_NS}}}type") == "page":
                    is_page_break = True

            # Preserve all text and tabulation characters in order of appearance
            for child in r_elem:
                c_tag = child.tag
                if c_tag == f"{{{W_NS}}}t":
                    if child.text:
                        r_text_parts.append(child.text)
                elif c_tag == f"{{{W_NS}}}tab":
                    r_text_parts.append("\t")
                elif c_tag == f"{{{W_NS}}}br":
                    if child.get(f"{{{W_NS}}}type") != "page":
                        r_text_parts.append("\n")
                elif c_tag == f"{{{W_NS}}}cr":
                    r_text_parts.append("\n")

            r_text = "".join(r_text_parts)

            # Check for embedded drawings/images
            drawings = r_elem.findall(f".//{{{W_NS}}}drawing")
            if drawings:
                for drawing in drawings:
                    blips = drawing.findall(f".//{{{R_NS}}}blip", namespaces=NAMESPACES)
                    if not blips:
                        # try without namespace prefix
                        blips = drawing.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip")
                    for blip in blips:
                        embed_id = blip.get(f"{{{R_NS}}}embed")
                        if embed_id:
                            images_found.append(embed_id)

            bold = False
            italic = False
            underline = False
            font_size: Optional[float] = None
            font_name: Optional[str] = None
            color: Optional[str] = None

            rPr = r_elem.find(f"{{{W_NS}}}rPr")
            if rPr is not None:
                if rPr.find(f"{{{W_NS}}}b") is not None:
                    bold = True
                if rPr.find(f"{{{W_NS}}}i") is not None:
                    italic = True
                if rPr.find(f"{{{W_NS}}}u") is not None:
                    underline = True
                sz = rPr.find(f"{{{W_NS}}}sz")
                if sz is not None:
                    sz_val = sz.get(f"{{{W_NS}}}val")
                    if sz_val and sz_val.isdigit():
                        font_size = float(sz_val) / 2.0  # half-points to pt
                rFonts = rPr.find(f"{{{W_NS}}}rFonts")
                if rFonts is not None:
                    font_name = rFonts.get(f"{{{W_NS}}}ascii") or rFonts.get(f"{{{W_NS}}}hAnsi")
                col = rPr.find(f"{{{W_NS}}}color")
                if col is not None:
                    color = col.get(f"{{{W_NS}}}val")

            if r_text or images_found:
                runs.append(
                    Run(
                        text=r_text,
                        font_name=font_name,
                        font_size_pt=font_size,
                        bold=bold,
                        italic=italic,
                        underline=underline,
                        color=color,
                    )
                )
                if r_text:
                    p_text_parts.append(r_text)

        full_text = "".join(p_text_parts).strip()
        if not full_text:
            # Fallback to itertext in case text was in Office Math or field codes
            iter_txt = "".join(elem.itertext()).strip()
            if iter_txt:
                full_text = iter_txt

        metadata: Dict[str, Any] = {}
        if images_found:
            metadata["image_rel_ids"] = images_found
        if tab_stops:
            metadata["tab_stops"] = tab_stops

        # CRITICAL: Ignore page breaks on empty/whitespace-only paragraphs to prevent ghost blank pages
        if not full_text and not images_found:
            is_page_break = False

        return Block(
            original_index=index,
            block_type=BlockType.IMAGE if (not full_text and images_found) else BlockType.BODY,
            text=full_text,
            runs=runs,
            source_style=style_name,
            alignment=alignment,
            left_indent_pt=left_indent,
            right_indent_pt=right_indent,
            space_before_pt=space_before,
            space_after_pt=space_after,
            line_spacing=line_spacing,
            is_page_break=is_page_break,
            metadata=metadata,
        )

    def _parse_table_element(self, elem: etree._Element, index: int) -> Block:
        """Extract table grid structure as tabular data."""
        table_data: List[List[str]] = []
        for row in elem.findall(f"{{{W_NS}}}tr"):
            row_cells: List[str] = []
            for cell in row.findall(f"{{{W_NS}}}tc"):
                cell_text_parts: List[str] = []
                for p in cell.findall(f"{{{W_NS}}}p"):
                    p_runs: List[str] = []
                    for r in p.findall(f"{{{W_NS}}}r"):
                        for child in r:
                            c_tag = child.tag
                            if c_tag == f"{{{W_NS}}}t" and child.text:
                                p_runs.append(child.text)
                            elif c_tag == f"{{{W_NS}}}tab":
                                p_runs.append("\t")
                    if not p_runs:
                        fallback_txt = "".join(p.itertext()).strip()
                        if fallback_txt:
                            p_runs.append(fallback_txt)
                    p_str = "".join(p_runs).strip()
                    if p_str:
                        cell_text_parts.append(p_str)
                row_cells.append("\n".join(cell_text_parts).strip())
            table_data.append(row_cells)

        text_representation = "\n".join(" | ".join(r) for r in table_data)
        return Block(
            original_index=index,
            block_type=BlockType.TABLE,
            text=text_representation,
            runs=[Run(text=text_representation)],
            source_style="TableGrid",
            metadata={"table_data": table_data, "row_count": len(table_data), "col_count": len(table_data[0]) if table_data else 0},
        )

    def _fallback_python_docx_stream(self) -> Generator[Block, None, None]:
        """Fallback to python-docx if raw OOXML iterparse hits an edge case."""
        doc = docx.Document(self.file_path)
        idx = 0
        for p in doc.paragraphs:
            runs = [
                Run(
                    text=r.text,
                    font_name=r.font.name if r.font else None,
                    font_size_pt=r.font.size.pt if r.font and r.font.size else None,
                    bold=bool(r.bold),
                    italic=bool(r.italic),
                    underline=bool(r.underline),
                )
                for r in p.runs
            ]
            align_str = "LEFT"
            if p.alignment:
                align_str = str(p.alignment).split(".")[-1]
            yield Block(
                original_index=idx,
                block_type=BlockType.BODY,
                text=p.text.strip(),
                runs=runs,
                source_style=p.style.name if p.style else "Normal",
                alignment=align_str,
            )
            idx += 1
