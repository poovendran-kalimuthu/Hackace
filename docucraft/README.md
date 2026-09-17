# DocuCraft — Intelligent Offline Manuscript & Book Formatter

**DocuCraft** is a desktop publishing frontend for offline, privacy-first manuscript-to-book formatting. Built with Python and **PySide6**, it offers a modern, mild light professional theme tailored for authors, editors, and book designers.

---

## Key Features

1. **100% Offline & Private by Design**:
   - Zero cloud connectivity, remote APIs, CDNs, or external telemetry.
   - All document analysis, pagination, and styling operate locally on the user's workstation.
   - Distinctive green `"✓ 100% Offline & Private"` badge in the fixed top navigation.

2. **Project Dashboard**:
   - Central hub for recent book projects, status progress, word counts, and trim sizes.
   - Built-in formatting templates for Standard Trade Fiction (5.5" × 8.5"), Academic / Non-Fiction (6.0" × 9.0"), Poetry (5.0" × 8.0"), and Technical Manuals (7.0" × 10.0").
   - Interactive empty-state demonstration toggle.
   - Offline Engine Benchmark report generator.

3. **Manuscript Upload & New Project Workflow**:
   - Drag & Drop DOCX upload zone with native file browser fallback.
   - Real-time file metadata display (size, estimated page count, offline readiness).
   - Fast simulated offline parsing and pagination pipeline.

4. **Manuscript Workspace**:
   - **Document Structure**: Expandable tree outline for Front Matter, Chapters, Sections, and Back Matter.
   - **Document Page Canvas**: Centered book page with authentic typography, running headers, drop caps, stylized body text, blockquotes, and page number footers.
   - **Formatting Inspector**: Global typography styles, trim size selection, asymmetric gutter margins, running head toggles, and re-pagination action.

5. **Template Studio**:
   - **Components Toolbox**: Click-to-add reusable elements:
     - Chapter Title
     - Section Heading
     - Body Text Box
     - Blockquote
     - Image Placeholder
     - Table Grid
     - Page Number
     - Divider Ornament
   - **Dynamic Layers Panel**: Real-time layer listing synchronized with canvas elements.
   - **Interactive Design Surface**: Draggable, selectable canvas blocks with margin guides and resize handles.
   - **Properties Inspector**: Live bi-directional attribute editor (Position, Size, Typography, Spacing, and Colors).
   - **Page Types Bar**: Fast switching between Cover, Title Page, Copyright Page, Chapter Opening, Normal Page, Quote Page, etc.

6. **Review Queue**:
   - Automated offline QA report highlighting structural anomalies (Critical, Warning, Suggestion).
   - Instant "Auto-Fix" actions and "Review in Editor" transitions.

7. **Book Preview**:
   - High-fidelity print preview with single page and two-page spread (facing pages) modes.
   - Thumbnail sidebar, zoom controls, and export options.

---

## Design System & Color Palette

- **Main Application Background**: `#F4F6F8` (Very light cool blue-gray)
- **Sidebars & Panels**: `#EEF1F5`
- **Cards & Page Canvas**: `#FFFFFF`
- **Borders**: `#D9DEE7`
- **Primary Accent**: `#168FE5` (DocuCraft Blue)
- **Secondary Accent**: `#5B6FE8` (Soft Indigo)
- **Success / Offline**: `#16A085`
- **Text Primary**: `#1F2937`
- **Text Secondary**: `#64748B`
- **Disabled Text**: `#94A3B8`

---

## Directory Structure

```
docucraft/
├── main.py
│
├── ui/
│   ├── main_window.py
│   ├── dashboard.py
│   ├── manuscript.py
│   ├── review_queue.py
│   ├── template_studio.py
│   ├── book_preview.py
│   │
│   └── components/
│       ├── header.py
│       ├── sidebar.py
│       ├── buttons.py
│       ├── cards.py
│       ├── canvas.py
│       ├── toolbox.py
│       ├── inspector.py
│       ├── dialogs.py
│       └── icons.py
│
├── styles/
│   └── theme.qss
│
├── assets/
│   ├── icons/
│   └── images/
│
└── README.md
```

---

## Requirements & Running Locally

### Prerequisites
- Python 3.10+ (tested on Python 3.11)
- PySide6 6.5+ (tested on PySide6 6.11.2)

### Running the Application

```powershell
# From the repository root
py -3.11 docucraft/main.py

# Or within the docucraft directory
cd docucraft
py -3.11 main.py
```

---

## Backend / ML Pipeline Integration Guide

DocuCraft's frontend is architecturally decoupled from any backend processing logic:

- **Manuscript Parsing**: In `ui/components/dialogs.py` (`NewProjectDialog._start_mock_analysis`), replace the step timer with calls to a local Python document parser (e.g. using `python-docx` or a local ONNX model).
- **Structure Tree**: In `ui/manuscript.py` (`_populate_structure_tree`), accept structured JSON/dictionary output from your heading detection pipeline.
- **Review Queue Rules**: In `ui/review_queue.py` (`self.issues_data`), bind output from your offline rule-checking / ML validation engine.
- **Template Engine**: Elements on `InteractivePageCanvas` serialize into standard dictionary definitions ready for PDF renderers (e.g. ReportLab or Weasyprint).
