"""
Template JSON Schema & Pydantic Specifications.

Defines reusable page layouts, typographic rules, and semantic component styles
for the Book Publisher, Academic Research Paper, and Conference Paper publication standards.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator


class PageSizeUnit(str, Enum):
    INCH = "inch"
    MM = "mm"
    PT = "pt"


class Margins(BaseModel):
    top: float = 0.75
    bottom: float = 0.75
    left: Optional[float] = None
    right: Optional[float] = None
    inside: Optional[float] = None
    outside: Optional[float] = None
    unit: str = "inch"


class PageSetup(BaseModel):
    size: str = "A5"
    orientation: str = "portrait"
    margins: Optional[Union[Margins, Dict[str, Any]]] = None
    mirror_margins: bool = False

    # Resolved geometry metrics in inches
    width: float = 5.83
    height: float = 8.27
    unit: str = "inch"
    margin_top_in: float = 0.75
    margin_bottom_in: float = 0.75
    margin_inside_in: float = 0.85
    margin_outside_in: float = 0.70
    gutter_in: float = 0.0
    bleed_in: float = 0.125

    @model_validator(mode="before")
    @classmethod
    def resolve_geometry(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        size = str(data.get("size", "A5")).upper()
        # Dimensions in inches: A5 is 5.83x8.27, A4 is 8.27x11.69, Letter is 8.5x11
        size_map = {
            "A5": (5.83, 8.27),
            "A4": (8.27, 11.69),
            "LETTER": (8.5, 11.0),
        }
        def_w, def_h = size_map.get(size, (5.83, 8.27))

        if "width" not in data:
            data["width"] = def_w
        if "height" not in data:
            data["height"] = def_h

        # Orientation
        if data.get("orientation") == "landscape":
            data["width"], data["height"] = data["height"], data["width"]

        # Parse margins
        raw_m = data.get("margins")
        if isinstance(raw_m, dict):
            unit = raw_m.get("unit", "inch")
            factor = (1.0 / 2.54) if unit == "cm" else (1.0 / 25.4 if unit == "mm" else 1.0)
            top = float(raw_m.get("top", 0.75)) * factor
            bottom = float(raw_m.get("bottom", 0.75)) * factor
            inside = raw_m.get("inside")
            outside = raw_m.get("outside")
            left = raw_m.get("left")
            right = raw_m.get("right")

            data["margin_top_in"] = top
            data["margin_bottom_in"] = bottom
            data["margin_inside_in"] = (float(inside) * factor) if inside is not None else ((float(left) * factor) if left is not None else 0.85)
            data["margin_outside_in"] = (float(outside) * factor) if outside is not None else ((float(right) * factor) if right is not None else 0.70)
        else:
            if "margin_top_in" not in data:
                data["margin_top_in"] = 0.75
            if "margin_bottom_in" not in data:
                data["margin_bottom_in"] = 0.75
            if "margin_inside_in" not in data:
                data["margin_inside_in"] = 0.85
            if "margin_outside_in" not in data:
                data["margin_outside_in"] = 0.70

        return data


class LayoutSetup(BaseModel):
    columns: int = 1
    gutter: float = 0.0
    column_gap: float = 0.25
    unit: str = "inch"
    widow_control: bool = True
    orphan_control: bool = True


class ElementStyle(BaseModel):
    font_family: str = "Times New Roman"
    font_size_pt: float = 11.0
    line_spacing: float = 1.15
    bold: bool = False
    italic: bool = False
    alignment: str = "JUSTIFY"  # LEFT, CENTER, RIGHT, JUSTIFY
    color: str = "#000000"
    space_before_pt: float = 0.0
    space_after_pt: float = 0.0
    first_line_indent_pt: float = 0.0
    left_indent_pt: float = 0.0
    right_indent_pt: float = 0.0
    drop_cap: bool = False
    span_columns: bool = False
    page_break_before: bool = False


class TemplateComponent(BaseModel):
    id: str
    name: str = "Component"
    component_type: str = "TEXT"
    x_percent: float = 0.0
    y_percent: float = 0.0
    width_percent: float = 100.0
    height_percent: float = 10.0
    style: ElementStyle = Field(default_factory=ElementStyle)
    locked: bool = False
    visible: bool = True
    z_index: int = 1
    content_placeholder: str = ""


class PageTypeLayout(BaseModel):
    page_type: str
    header_text: str = ""
    footer_text: str = ""
    show_header: bool = True
    show_footer: bool = True
    show_page_number: bool = True
    page_number_position: str = "bottom-center"
    components: List[TemplateComponent] = Field(default_factory=list)


class LogoRules(BaseModel):
    required: bool = True
    allowed_locations: List[str] = Field(default_factory=lambda: ["cover", "title_page"])
    position: str = "title_top"
    max_width_in: float = 2.2
    max_height_in: float = 1.5
    alignment: str = "CENTER"
    space_after_pt: float = 24.0


class BookTemplate(BaseModel):
    id: str = ""
    name: str = ""
    profile_name: str = ""
    profile_version: str = "1.0"
    document_type: str = "book"
    description: str = ""
    category: str = ""

    page: PageSetup = Field(default_factory=PageSetup)
    layout: LayoutSetup = Field(default_factory=LayoutSetup)
    default_font: Dict[str, Any] = Field(default_factory=dict)

    front_matter: Dict[str, Any] = Field(default_factory=dict)
    chapter: Dict[str, Any] = Field(default_factory=dict)
    elements: Dict[str, Any] = Field(default_factory=dict)
    paragraph_rules: Dict[str, Any] = Field(default_factory=dict)
    structure: Dict[str, Any] = Field(default_factory=dict)
    numbering: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, Any] = Field(default_factory=dict)
    footers: Dict[str, Any] = Field(default_factory=dict)
    page_numbering: Dict[str, Any] = Field(default_factory=dict)
    references: Dict[str, Any] = Field(default_factory=dict)
    appendices: Dict[str, Any] = Field(default_factory=dict)
    validation: Dict[str, Any] = Field(default_factory=dict)

    logo: LogoRules = Field(default_factory=LogoRules)
    styles: Dict[str, ElementStyle] = Field(default_factory=dict)
    page_types: Dict[str, PageTypeLayout] = Field(default_factory=dict)
    is_builtin: bool = False
    created_at: str = ""
    updated_at: str = ""

    @model_validator(mode="after")
    def populate_defaults_and_styles(self) -> "BookTemplate":
        # Resolve ID and Name from profile metadata
        if not self.id:
            self.id = self.document_type or "book"
        if not self.name:
            self.name = self.profile_name or self.id.replace("_", " ").title()
        if not self.category:
            self.category = self.name.upper()

        if not self.description:
            if self.document_type == "book":
                self.description = "Standard commercial book publication format. A5, mirror margins, odd page chapters, Times New Roman 11pt."
            elif self.document_type == "academic_research":
                self.description = "Academic research paper format. A4, single-column, structured abstract, numbered headings, Times New Roman 11pt."
            elif self.document_type == "conference_paper":
                self.description = "Conference proceedings format. A4, two-column layout (0.25\" gap), compact typography, numeric references."
            else:
                self.description = f"{self.name} publication layout."

        # Synchronize gutter from layout to page
        if self.layout and self.layout.gutter > 0:
            self.page.gutter_in = self.layout.gutter

        # Populate styles dict from elements if elements provided
        if self.elements:
            for el_name, el_spec in self.elements.items():
                if isinstance(el_spec, dict):
                    f_size = el_spec.get("font_size", el_spec.get("size", 11.0))
                    try:
                        f_size_pt = float(f_size) if f_size else 11.0
                    except Exception:
                        f_size_pt = 11.0

                    indent = el_spec.get("first_line_indent", 0.0)
                    indent_unit = el_spec.get("indent_unit", "inch")
                    try:
                        f_indent = float(indent) if indent else 0.0
                    except Exception:
                        f_indent = 0.0
                    if indent_unit == "cm":
                        indent_pt = f_indent * 72.0 / 2.54
                    elif f_indent < 5.0:
                        indent_pt = f_indent * 72.0
                    else:
                        indent_pt = f_indent

                    left_in = el_spec.get("left_indent", 0.0)
                    try:
                        f_left = float(left_in) if left_in else 0.0
                    except Exception:
                        f_left = 0.0
                    left_pt = f_left * 72.0 if f_left < 5.0 else f_left

                    right_in = el_spec.get("right_indent", 0.0)
                    try:
                        f_right = float(right_in) if right_in else 0.0
                    except Exception:
                        f_right = 0.0
                    right_pt = f_right * 72.0 if f_right < 5.0 else f_right

                    l_spacing = el_spec.get("line_spacing", 1.15)
                    try:
                        f_lspacing = float(l_spacing) if l_spacing else 1.15
                    except Exception:
                        f_lspacing = 1.15

                    style_obj = ElementStyle(
                        font_family=el_spec.get("font") or "Times New Roman",
                        font_size_pt=f_size_pt,
                        bold=bool(el_spec.get("bold", False)),
                        italic=bool(el_spec.get("italic", False)),
                        alignment=str(el_spec.get("alignment", "JUSTIFY")).upper() or "JUSTIFY",
                        line_spacing=f_lspacing,
                        space_before_pt=float(el_spec.get("space_before", 0.0) or 0.0),
                        space_after_pt=float(el_spec.get("space_after", 0.0) or 0.0),
                        first_line_indent_pt=indent_pt,
                        left_indent_pt=left_pt,
                        right_indent_pt=right_pt,
                        span_columns=bool(el_spec.get("span_columns", False)),
                        page_break_before=bool(el_spec.get("page_break_before", False)),
                    )
                    self.styles[el_name.lower()] = style_obj
                    if el_name.lower() == "subheading":
                        self.styles["heading_2"] = style_obj
                        self.styles["heading_3"] = style_obj

            # Chapter title styling from chapter section if present
            if self.chapter and isinstance(self.chapter, dict) and "chapter_title" in self.chapter:
                ct = self.chapter["chapter_title"]
                self.styles["chapter_title"] = ElementStyle(
                    font_family=ct.get("font", "Times New Roman"),
                    font_size_pt=float(ct.get("size", 20.0)),
                    bold=bool(ct.get("bold", True)),
                    italic=bool(ct.get("italic", False)),
                    alignment=str(ct.get("alignment", "CENTER")).upper(),
                    line_spacing=1.15,
                    space_before_pt=float(ct.get("space_before", 12.0)),
                    space_after_pt=float(ct.get("space_after", 24.0)),
                    page_break_before=True,
                )

        return self

    def get_style_for_element(self, element_type: str) -> ElementStyle:
        """Fetch style fallback chain."""
        key_lower = element_type.lower()
        if key_lower in self.styles:
            return self.styles[key_lower]

        key_upper = element_type.upper()
        if self.elements:
            if key_upper in self.elements:
                el_spec = self.elements[key_upper]
            elif key_upper in ("HEADING_2", "HEADING_3") and "SUBHEADING" in self.elements:
                el_spec = self.elements["SUBHEADING"]
            else:
                el_spec = None

            if isinstance(el_spec, dict):
                f_size = el_spec.get("font_size", el_spec.get("size", 11.0))
                try:
                    f_size_pt = float(f_size) if f_size else 11.0
                except Exception:
                    f_size_pt = 11.0

                indent = el_spec.get("first_line_indent", 0.0)
                indent_unit = el_spec.get("indent_unit", "inch")
                try:
                    f_indent = float(indent) if indent else 0.0
                except Exception:
                    f_indent = 0.0
                indent_pt = (f_indent * 72.0 / 2.54) if indent_unit == "cm" else (f_indent * 72.0 if f_indent < 5.0 else f_indent)

                l_spacing = el_spec.get("line_spacing", 1.15)
                try:
                    f_lspacing = float(l_spacing) if l_spacing else 1.15
                except Exception:
                    f_lspacing = 1.15

                return ElementStyle(
                    font_family=el_spec.get("font") or "Times New Roman",
                    font_size_pt=f_size_pt,
                    bold=bool(el_spec.get("bold", False)),
                    italic=bool(el_spec.get("italic", False)),
                    alignment=str(el_spec.get("alignment", "JUSTIFY")).upper() or "JUSTIFY",
                    line_spacing=f_lspacing,
                    space_before_pt=float(el_spec.get("space_before", 0.0) or 0.0),
                    space_after_pt=float(el_spec.get("space_after", 0.0) or 0.0),
                    first_line_indent_pt=indent_pt,
                    span_columns=bool(el_spec.get("span_columns", False)),
                )

        if key_lower in ("chapter_title", "part_title"):
            return ElementStyle(
                font_family="Times New Roman",
                font_size_pt=20.0,
                bold=True,
                alignment="CENTER",
                space_before_pt=18.0,
                space_after_pt=24.0,
                page_break_before=True,
            )

        if key_lower == "title":
            return ElementStyle(
                font_family="Times New Roman",
                font_size_pt=22.0,
                bold=True,
                alignment="CENTER",
                space_before_pt=24.0,
                space_after_pt=18.0,
            )

        if key_lower in ("heading_1", "heading_2", "heading_3", "subheading"):
            return ElementStyle(
                font_family="Times New Roman",
                font_size_pt=14.0 if "1" in key_lower else 12.0,
                bold=True,
                alignment="LEFT",
                space_before_pt=12.0,
                space_after_pt=6.0,
            )

        if "body" in self.styles:
            return self.styles["body"]

        return ElementStyle()
