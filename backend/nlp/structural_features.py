"""
Deterministic Structural Pattern Matcher.

Identifies textual patterns characteristic of Parts, Chapters, Sections (H2), Subsections (H3),
Equations, Diagrams, Captions, Lists, References, and Front/Back Matter.

Patterns are aligned with the Book Publisher template element_rules specification.
"""

from __future__ import annotations
import re
from typing import Dict


class StructuralPatternMatcher:
    """
    High-precision regex-based structural indicator extractor.
    All patterns are aligned with Book Publisher, Academic, and Conference template specs.
    """

    # --- PART ---
    # Matches: "Part I", "PART 1", "Part IV: The Fall"
    PART_REGEX = re.compile(
        r"^part\s+[ivxlcdm0-9]+\b.*$",
        re.IGNORECASE,
    )

    # --- CHAPTER ---
    # Matches: "Chapter 1", "Chapter IV", "Chapter 1: Title", "Prologue", "Epilogue"
    CHAPTER_REGEX = re.compile(
        r"^(?:chapter\s+(?:[0-9]+|[ivxlcdm]+)(?:\s*[:.\-–—].*)?|prologue(?:\s*[:.\-–—].*)?|epilogue(?:\s*[:.\-–—].*)?)$",
        re.IGNORECASE,
    )

    # --- HEADING 2 (x.y numbered sections) ---
    # Matches: "1.1 Overview", "2.3 Results", "1.2. Method"
    HEADING_2_REGEX = re.compile(
        r"^[0-9]+\.[0-9]+\.?\s+[A-Za-z].+$",
    )

    # --- HEADING 3 (x.y.z numbered subsections) ---
    # Matches: "1.1.1 Background", "2.3.4 Analysis"
    HEADING_3_REGEX = re.compile(
        r"^[0-9]+\.[0-9]+\.[0-9]+\.?\s+[A-Za-z].+$",
    )

    # --- ABSTRACT & KEYWORDS ---
    ABSTRACT_REGEX = re.compile(
        r"^(?:abstract|summary)(?:\s*[:.\-–—].*)?$",
        re.IGNORECASE,
    )
    KEYWORDS_REGEX = re.compile(
        r"^(?:keywords?|index\s+terms?|key\s+words?)(?:\s*[:.\-–—].*)?$",
        re.IGNORECASE,
    )

    # --- SECTION KEYWORDS ---
    SECTION_KEYWORD_REGEX = re.compile(
        r"^(?:Introduction|Background|Related\s+Work|Literature\s+Review|Methodology|Methods?|"
        r"Materials\s+and\s+Methods|System\s+Architecture|System\s+Design|Experimental\s+Setup|"
        r"Experiments?|Experimental\s+Results|Results|Results\s+and\s+Discussion|Discussion|"
        r"Future\s+Work|Future\s+Directions|Conclusions?|Summary|Motivation|Overview|"
        r"Problem\s+Statement|Limitations|Contributions?|Abstract|References?|Appendix.*)$",
        re.IGNORECASE,
    )

    # --- MAJOR SECTION NUMBERING (HEADING 1) ---
    # Matches: "1. INTRODUCTION", "1. Introduction", "I. INTRODUCTION", "Section 1. Introduction"
    # Does NOT match "1.1" or "1.1.1" which are handled by H2/H3
    MAJOR_SECTION_NUM_REGEX = re.compile(
        r"^(?:(?:Section|Sec\.?)\s+)?(?:[0-9]+|[ivxlcdm]+)[\.:\)\s]\s*(.*)$",
        re.IGNORECASE,
    )

    # --- LEGACY SECTION (kept for academic/conference) ---
    SECTION_REGEX = re.compile(
        r"^(?:Section\s+)?\d+\.\d+(?:\s+|:|\.\s+)[A-Za-z0-9]|^\d+\.\d+\s+[A-Za-z0-9]",
        re.IGNORECASE,
    )
    SUBSECTION_REGEX = re.compile(
        r"^(?:Subsection\s+)?\d+\.\d+\.\d+(?:\s+|:|\.\s+)[A-Za-z0-9]|^\d+\.\d+\.\d+\s+[A-Za-z0-9]",
        re.IGNORECASE,
    )

    # --- FRONT / BACK MATTER ---
    FRONT_BACK_MATTER_REGEX = re.compile(
        r"^(?:Preface|Foreword|Acknowledgements?|Table of Contents|Contents|Title Page"
        r"|Copyright(?:\s+Page)?|Dedication|Appendix\s+[A-Z](?:[:\s].*)?"
        r"|Glossary|References?|Bibliography|Index|About the Author)$",
        re.IGNORECASE,
    )

    # --- UNNUMBERED HEADINGS (common structural words) ---
    UNNUMBERED_HEADING_REGEX = re.compile(
        r"^(?:Introduction|Background|Related Work|Methodology|Method|System Architecture"
        r"|Experimental Results|Experiments|Results and Discussion|Future Work"
        r"|Future Directions|Conclusion|Summary|Discussion|Motivation|Overview"
        r"|Problem Statement|Limitations|Contributions?)$",
        re.IGNORECASE,
    )

    # --- FIGURE CAPTION ---
    CAPTION_FIG_REGEX = re.compile(
        r"^(?:Figure|Fig\.?)\s*\d+(?:\.\d+)?[\s:.–—\-]",
        re.IGNORECASE,
    )

    # --- TABLE CAPTION ---
    CAPTION_TBL_REGEX = re.compile(
        r"^(?:Table|Tab\.?)\s*\d+(?:\.\d+)?[\s:.–—\-]",
        re.IGNORECASE,
    )

    # --- LIST (bullets, numbers, letters) ---
    LIST_BULLET_REGEX = re.compile(
        r"^[\u2022\u2023\u25E6\u2043\u2219\*\-\+]\s+"
        r"|^\(?\d+[.\)]\s+"
        r"|^\(?[a-zA-Z][.\)]\s+"
        r"|^\d+\.[a-zA-Z]\.\s+"
    )

    # --- REFERENCE (author-year, numeric bracket) ---
    # Matches: "[1] Smith...", "[Smith, 2023]", "Smith, J. (2020)..."
    # NOTE: Does NOT match "1. Some plain text" (that is a numbered list).
    # Requires either: [N] Lastname, [AuthorYear], or Lastname, I. (Year) form.
    REFERENCE_REGEX = re.compile(
        r"^\[\d+\]\s+[A-Z]"                  # [1] Lastname...
        r"|^\[\w+,?\s+\d{4}\]"               # [Smith, 2023] or [Smith2023]
        r"|^[A-Z][a-z]{1,20},\s+[A-Z]\.\s+\(",  # Smith, J. (Year)
    )

    # --- DIAGRAM ---
    DIAGRAM_REGEX = re.compile(
        r"(?:\+[-=]{3,}\+|\|[-=]{3,}\||-----?>|<-{3,}|\[.+\]\s*->\s*\[.+\]"
        r"|\b(?:Sensor ISR|NPU Task|Raw Sensor Input|Preempted)\b)"
    )

    # --- CODE ---
    CODE_REGEX = re.compile(
        r"(?:#include\s*<|std::memcpy|->version\(\)|namespace\s+\w+|class\s+\w+\s*\{"
        r"|void\s+\w+\(|int\s+main\()"
    )

    @classmethod
    def match_patterns(cls, text: str) -> Dict[str, float]:
        if not text:
            return {
                "is_part_pattern":           0.0,
                "is_chapter_pattern":        0.0,
                "is_section_pattern":        0.0,
                "is_subsection_pattern":     0.0,
                "is_heading_2_pattern":      0.0,
                "is_heading_3_pattern":      0.0,
                "is_front_back_matter":      0.0,
                "is_unnumbered_heading":     0.0,
                "is_equation_pattern":       0.0,
                "is_diagram_pattern":        0.0,
                "is_code_pattern":           0.0,
                "is_figure_caption_pattern": 0.0,
                "is_table_caption_pattern":  0.0,
                "is_list_pattern":           0.0,
                "is_numbered_heading":       0.0,
                "is_reference_pattern":      0.0,
                "has_quote_marks":           0.0,
                "is_short_title":            0.0,
            }

        s = text.strip()
        word_count = len(s.split())

        # --- Equation detection ---
        is_equation = (
            (s.startswith("$$") and s.endswith("$$"))
            or ("\\frac" in s)
            or ("\\sum" in s)
            or ("\\int" in s)
            or ("\\sigma" in s and ("=" in s or "^" in s or "_" in s))
            or ("\\leftarrow" in s)
        )

        is_part      = bool(cls.PART_REGEX.match(s))    and word_count <= 14
        is_chapter   = bool(cls.CHAPTER_REGEX.match(s)) and word_count <= 14

        # Book-specific numbered heading patterns
        is_h3        = bool(cls.HEADING_3_REGEX.match(s)) and word_count <= 18
        is_h2        = bool(cls.HEADING_2_REGEX.match(s)) and word_count <= 18 and not is_h3

        # Legacy academic section patterns
        is_subsection = bool(cls.SUBSECTION_REGEX.match(s)) and word_count <= 16
        is_section    = bool(cls.SECTION_REGEX.match(s))    and word_count <= 16 and not is_subsection

        is_front_back    = bool(cls.FRONT_BACK_MATTER_REGEX.match(s))
        is_unnum_heading = bool(cls.UNNUMBERED_HEADING_REGEX.match(s))

        is_abstract  = bool(cls.ABSTRACT_REGEX.match(s))
        is_keywords  = bool(cls.KEYWORDS_REGEX.match(s))

        # Check major section H1 candidate (e.g. "1. INTRODUCTION", "I. INTRODUCTION", "Section 1. Introduction")
        m_major = cls.MAJOR_SECTION_NUM_REGEX.match(s)
        is_major_section_candidate = False
        if m_major and not is_h2 and not is_h3 and not is_chapter and not is_part and word_count <= 14:
            heading_title_part = m_major.group(1).strip()
            is_all_caps_title = heading_title_part.isupper() and len(heading_title_part) > 2
            is_keyword = bool(cls.SECTION_KEYWORD_REGEX.match(heading_title_part.split(":")[0].strip()))
            is_roman = bool(re.match(r"^[ivxlcdm]+[\.:\)\s]", s, re.IGNORECASE))
            if is_all_caps_title or is_keyword or is_roman or s.lower().startswith("section "):
                is_major_section_candidate = True

        is_unnum_major = (
            bool(cls.SECTION_KEYWORD_REGEX.match(s.strip()))
            and not is_h2 and not is_h3 and not is_chapter and not is_part and not is_abstract and not is_keywords
            and word_count <= 6
        )

        is_h1 = (is_major_section_candidate or is_unnum_major) and not is_abstract and not is_keywords

        is_diagram   = bool(cls.DIAGRAM_REGEX.search(s))
        is_code      = bool(cls.CODE_REGEX.search(s))

        is_fig_caption = bool(cls.CAPTION_FIG_REGEX.match(s))
        is_tbl_caption = bool(cls.CAPTION_TBL_REGEX.match(s))
        is_reference   = bool(cls.REFERENCE_REGEX.match(s)) and word_count >= 4

        # List items: bullet or numeric prefix, strictly excluding headings, references, chapters
        is_list = (
            bool(cls.LIST_BULLET_REGEX.match(s))
            and not (is_h1 or is_h2 or is_h3 or is_section or is_subsection or is_chapter or is_part or is_abstract or is_keywords or is_reference)
        )

        # Composite: numbered heading means H1, H2, or H3 (or legacy)
        is_numbered = is_h1 or is_h2 or is_h3 or is_section or is_subsection

        return {
            "is_part_pattern":           1.0 if is_part            else 0.0,
            "is_chapter_pattern":        1.0 if is_chapter         else 0.0,
            "is_heading_1_pattern":      1.0 if is_h1              else 0.0,
            "is_section_pattern":        1.0 if is_section         else 0.0,
            "is_subsection_pattern":     1.0 if is_subsection      else 0.0,
            "is_heading_2_pattern":      1.0 if is_h2              else 0.0,
            "is_heading_3_pattern":      1.0 if is_h3              else 0.0,
            "is_abstract_pattern":       1.0 if is_abstract        else 0.0,
            "is_keywords_pattern":       1.0 if is_keywords        else 0.0,
            "is_front_back_matter":      1.0 if is_front_back      else 0.0,
            "is_unnumbered_heading":     1.0 if is_unnum_heading   else 0.0,
            "is_equation_pattern":       1.0 if is_equation        else 0.0,
            "is_diagram_pattern":        1.0 if is_diagram         else 0.0,
            "is_code_pattern":           1.0 if is_code            else 0.0,
            "is_figure_caption_pattern": 1.0 if is_fig_caption     else 0.0,
            "is_table_caption_pattern":  1.0 if is_tbl_caption     else 0.0,
            "is_list_pattern":           1.0 if is_list            else 0.0,
            "is_numbered_heading":       1.0 if is_numbered        else 0.0,
            "is_reference_pattern":      1.0 if is_reference       else 0.0,
            "has_quote_marks": 1.0 if (
                s.startswith(('"', "\u201c", "'", "\u00ab"))
                and s.endswith(('"', "\u201d", "'", "\u00bb"))
            ) else 0.0,
            "is_short_title":  1.0 if (1 <= word_count <= 8 and not s.endswith(".")) else 0.0,
        }
