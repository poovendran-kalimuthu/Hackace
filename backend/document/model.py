"""
Internal Document Model.

Independent of python-docx internal representations, designed for memory-efficient
streaming, chunking, structural graph representation, and template transformation.
"""

from __future__ import annotations
import json
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BlockType(str, Enum):
    TITLE = "TITLE"
    AUTHOR = "AUTHOR"
    AFFILIATION = "AFFILIATION"
    ABSTRACT = "ABSTRACT"
    KEYWORDS = "KEYWORDS"
    PART_TITLE = "PART_TITLE"
    CHAPTER_TITLE = "CHAPTER_TITLE"
    HEADING_1 = "HEADING_1"
    HEADING_2 = "HEADING_2"
    HEADING_3 = "HEADING_3"
    BODY = "BODY"
    QUOTE = "QUOTE"
    CAPTION = "CAPTION"
    TABLE_CAPTION = "TABLE_CAPTION"
    LIST = "LIST"
    TABLE = "TABLE"
    IMAGE = "IMAGE"
    EQUATION = "EQUATION"
    DIAGRAM = "DIAGRAM"
    CODE = "CODE"
    TOC = "TOC"
    TOC_ENTRY = "TOC_ENTRY"
    REFERENCE = "REFERENCE"
    FRONT_MATTER = "FRONT_MATTER"
    BACK_MATTER = "BACK_MATTER"
    PAGE_BREAK = "PAGE_BREAK"
    UNKNOWN = "UNKNOWN"


class Run(BaseModel):
    text: str = ""
    font_name: Optional[str] = None
    font_size_pt: Optional[float] = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: Optional[str] = None
    strikethrough: bool = False


class Block(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    block_type: BlockType = BlockType.BODY
    text: str = ""
    runs: List[Run] = Field(default_factory=list)
    confidence: float = 1.0
    source_style: str = "Normal"
    alignment: str = "LEFT"  # LEFT, CENTER, RIGHT, JUSTIFY
    left_indent_pt: float = 0.0
    right_indent_pt: float = 0.0
    space_before_pt: float = 0.0
    space_after_pt: float = 0.0
    line_spacing: float = 1.15
    is_page_break: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    user_corrected: bool = False
    predicted_type: Optional[BlockType] = None
    original_index: int = 0

    def word_count(self) -> int:
        return len(self.text.split())

    def char_count(self) -> int:
        return len(self.text)


class Section(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    level: int = 1
    blocks: List[Block] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Chapter(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    number: Optional[int] = None
    sections: List[Section] = Field(default_factory=list)
    blocks: List[Block] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentMetadata(BaseModel):
    title: str = "Untitled Document"
    author: str = "Unknown Author"
    created_date: Optional[str] = None
    source_filename: str = ""
    file_size_bytes: int = 0
    estimated_pages: int = 1
    total_words: int = 0
    total_paragraphs: int = 0
    total_chapters: int = 0
    total_images: int = 0
    total_tables: int = 0
    detected_types_summary: Dict[str, int] = Field(default_factory=dict)


class DocumentModel(BaseModel):
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    chapters: List[Chapter] = Field(default_factory=list)
    blocks: List[Block] = Field(default_factory=list)
    styles: Dict[str, Any] = Field(default_factory=dict)
    relationships: Dict[str, Any] = Field(default_factory=dict)

    def to_json(self, indent: Optional[int] = None) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> DocumentModel:
        data = json.loads(json_str)
        return cls.model_validate(data)

    def flatten_blocks(self) -> List[Block]:
        """Returns all blocks in sequence."""
        if self.blocks:
            return self.blocks
        result: List[Block] = []
        for ch in self.chapters:
            result.extend(ch.blocks)
            for sec in ch.sections:
                result.extend(sec.blocks)
        return result
