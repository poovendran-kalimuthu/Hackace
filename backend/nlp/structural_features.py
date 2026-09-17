"""
Deterministic Structural Pattern Matcher.

Identifies textual patterns characteristic of Parts, Chapters, Sections, Subsections,
Equations, Diagrams, Captions, Lists, and Front/Back Matter.
"""

from __future__ import annotations
import re
from typing import Dict


class StructuralPatternMatcher:
    """
    High-precision regex-based structural indicator extractor.
    """

    PART_REGEX = re.compile(
        r"^PART\s+[IVXLCDM0-9]+[:\s].*$",
        re.IGNORECASE,
    )
    CHAPTER_REGEX = re.compile(
        r"^(?:Chapter\s+\d+|CHAPTER\s+\d+|Chapter\s+\d+\s*[/:]|Prologue|Epilogue)\b.*$",
        re.IGNORECASE,
    )
    SECTION_REGEX = re.compile(
        r"^(?:Section\s+)?\d+\.\d+(?:\s+|:|\.\s+)[A-Za-z0-9]|^\d+\.\d+\s+[A-Za-z0-9]",
        re.IGNORECASE,
    )
    SUBSECTION_REGEX = re.compile(
        r"^(?:Subsection\s+)?\d+\.\d+\.\d+(?:\s+|:|\.\s+)[A-Za-z0-9]|^\d+\.\d+\.\d+\s+[A-Za-z0-9]",
        re.IGNORECASE,
    )
    FRONT_BACK_MATTER_REGEX = re.compile(
        r"^(?:Preface|Acknowledgements|Table of Contents|Title Page|Copyright|Appendix\s+[A-Z](?:[:\s].*)?|Glossary|References)$",
        re.IGNORECASE,
    )
    UNNUMBERED_HEADING_REGEX = re.compile(
        r"^(?:Introduction|Background|System Architecture|Experimental Results|Future Directions|Conclusion|Summary)$",
        re.IGNORECASE,
    )
    CAPTION_FIG_REGEX = re.compile(
        r"^(?:Figure|Fig\.)\s*\d+(?:\.\d+)?[\s:.\-—]",
        re.IGNORECASE,
    )
    CAPTION_TBL_REGEX = re.compile(
        r"^(?:Table|Tab\.)\s*\d+(?:\.\d+)?[\s:.\-—]",
        re.IGNORECASE,
    )
    LIST_BULLET_REGEX = re.compile(
        r"^[\u2022\u2023\u25E6\u2043\u2219\*\-\+]\s+|^\(?\d+[\.\)]\s+|^\(?[a-zA-Z][\.\)]\s+|^\d+\.[a-zA-Z]\.\s+"
    )
    DIAGRAM_REGEX = re.compile(
        r"(?:\+[-=]{3,}\+|\|[-=]{3,}\||\b(?:Sensor ISR|NPU Task|Raw Sensor Input|Preempted)\b|----->|<-{3,}|\[.+\]\s*->\s*\[.+\])"
    )
    CODE_REGEX = re.compile(
        r"(?:#include\s*<|std::memcpy|->version\(\)|namespace\s+\w+|class\s+\w+\s*\{|void\s+\w+\(|int\s+main\()"
    )

    @classmethod
    def match_patterns(cls, text: str) -> Dict[str, float]:
        if not text:
            return {
                "is_part_pattern": 0.0,
                "is_chapter_pattern": 0.0,
                "is_section_pattern": 0.0,
                "is_subsection_pattern": 0.0,
                "is_front_back_matter": 0.0,
                "is_unnumbered_heading": 0.0,
                "is_equation_pattern": 0.0,
                "is_diagram_pattern": 0.0,
                "is_code_pattern": 0.0,
                "is_figure_caption_pattern": 0.0,
                "is_table_caption_pattern": 0.0,
                "is_list_pattern": 0.0,
                "is_numbered_heading": 0.0,
                "has_quote_marks": 0.0,
                "is_short_title": 0.0,
            }

        s = text.strip()
        word_count = len(s.split())

        # Equation detection: $$...$$ or contains common LaTeX math macros
        is_equation = (
            (s.startswith("$$") and s.endswith("$$"))
            or ("\\frac" in s)
            or ("\\sum" in s)
            or ("\\int" in s)
            or ("\\sigma" in s and ("=" in s or "^" in s or "_" in s))
            or ("\\leftarrow" in s)
        )

        is_part = bool(cls.PART_REGEX.match(s)) and word_count <= 14
        is_chapter = bool(cls.CHAPTER_REGEX.match(s)) and word_count <= 14
        is_section = bool(cls.SECTION_REGEX.match(s)) and word_count <= 16
        is_subsection = bool(cls.SUBSECTION_REGEX.match(s)) and word_count <= 16
        is_front_back = bool(cls.FRONT_BACK_MATTER_REGEX.match(s))
        is_unnum_heading = bool(cls.UNNUMBERED_HEADING_REGEX.match(s))

        is_diagram = bool(cls.DIAGRAM_REGEX.search(s))
        is_code = bool(cls.CODE_REGEX.search(s))

        is_fig_caption = bool(cls.CAPTION_FIG_REGEX.match(s))
        is_tbl_caption = bool(cls.CAPTION_TBL_REGEX.match(s))
        is_list = bool(cls.LIST_BULLET_REGEX.match(s))

        return {
            "is_part_pattern": 1.0 if is_part else 0.0,
            "is_chapter_pattern": 1.0 if is_chapter else 0.0,
            "is_section_pattern": 1.0 if is_section else 0.0,
            "is_subsection_pattern": 1.0 if is_subsection else 0.0,
            "is_front_back_matter": 1.0 if is_front_back else 0.0,
            "is_unnumbered_heading": 1.0 if is_unnum_heading else 0.0,
            "is_equation_pattern": 1.0 if is_equation else 0.0,
            "is_diagram_pattern": 1.0 if is_diagram else 0.0,
            "is_code_pattern": 1.0 if is_code else 0.0,
            "is_figure_caption_pattern": 1.0 if is_fig_caption else 0.0,
            "is_table_caption_pattern": 1.0 if is_tbl_caption else 0.0,
            "is_list_pattern": 1.0 if is_list else 0.0,
            "is_numbered_heading": 1.0 if (is_section or is_subsection) else 0.0,
            "has_quote_marks": 1.0 if (s.startswith(('"', "“", "'", "«")) and s.endswith(('"', "”", "'", "»"))) else 0.0,
            "is_short_title": 1.0 if (1 <= word_count <= 8 and not s.endswith(".")) else 0.0,
        }
