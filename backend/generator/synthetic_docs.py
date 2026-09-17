"""
Synthetic Large Document Generator.

Generates realistic benchmark manuscripts from 100 to 10,000+ pages
containing chapters, headings, body text, tables, quotes, and captions
to rigorously validate system throughput, memory ceilings, and crash recovery.
"""

from __future__ import annotations
import argparse
import os
import random
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor


class SyntheticDocumentGenerator:
    """
    Generates scalable test manuscripts for performance profiling.
    """

    CHAPTER_TITLES = [
        "The Quantum Horizon",
        "Foundations of Machine Perception",
        "Deterministic Structural Grammars",
        "High-Throughput Parallelism",
        "The Architecture of Thought",
        "Linguistic Morphologies",
        "Dynamic Layout Synthesis",
        "Subatomic Resonances",
        "Cryptographic Enclaves",
        "The Singularity Epoch",
    ]

    LOREM_WORDS = [
        "quantum", "neural", "computation", "heuristic", "optimization", "gradient",
        "tensor", "distribution", "variance", "stochastic", "vector", "matrix",
        "convergence", "representation", "algorithmic", "processing", "pipeline",
        "structural", "analysis", "systematic", "architecture", "distributed",
        "memory", "throughput", "latency", "bandwidth", "scalability", "robustness",
    ]

    @classmethod
    def generate_paragraph(cls, min_words: int = 40, max_words: int = 90) -> str:
        count = random.randint(min_words, max_words)
        words = [random.choice(cls.LOREM_WORDS) for _ in range(count)]
        words[0] = words[0].capitalize()
        # Insert periodic sentence stops
        for i in range(12, count - 5, random.randint(10, 18)):
            words[i] = words[i] + "."
            if i + 1 < count:
                words[i + 1] = words[i + 1].capitalize()
        return " ".join(words) + "."

    @classmethod
    def create_document(
        cls,
        target_pages: int,
        output_path: str,
        words_per_page: int = 280,
    ) -> str:
        """
        Builds a multi-chapter document aiming for target_pages.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = docx.Document()
        total_target_words = target_pages * words_per_page
        accumulated_words = 0

        # Title Page
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        trun = title_p.add_run(f"Benchmark Manuscript ({target_pages} Pages)")
        trun.font.size = Pt(28)
        trun.bold = True
        doc.add_page_break()

        chap_num = 1
        sec_num = 1

        while accumulated_words < total_target_words:
            # Add Chapter Title
            chap_title_text = f"Chapter {chap_num}: {cls.CHAPTER_TITLES[(chap_num - 1) % len(cls.CHAPTER_TITLES)]}"
            cp = doc.add_paragraph()
            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            crun = cp.add_run(chap_title_text)
            crun.font.size = Pt(22)
            crun.bold = True
            accumulated_words += len(chap_title_text.split())

            # Chapter content: 3-5 sections
            sections_in_chap = random.randint(3, 5)
            for s in range(1, sections_in_chap + 1):
                # Heading 1
                h1_text = f"{chap_num}.{s} Theoretical Framework"
                h1p = doc.add_paragraph()
                h1run = h1p.add_run(h1_text)
                h1run.font.size = Pt(16)
                h1run.bold = True
                accumulated_words += len(h1_text.split())

                # Paragraphs under section
                p_count = random.randint(3, 6)
                for _ in range(p_count):
                    body_text = cls.generate_paragraph()
                    bp = doc.add_paragraph(body_text)
                    accumulated_words += len(body_text.split())

                # Occasional Block Quote
                if random.random() < 0.4:
                    q_text = f'"{cls.generate_paragraph(min_words=20, max_words=45)}"'
                    qp = doc.add_paragraph(q_text)
                    qp.paragraph_format.left_indent = Inches(0.4)
                    if qp.runs:
                        qp.runs[0].italic = True
                    accumulated_words += len(q_text.split())

                # Occasional Table
                if random.random() < 0.3:
                    tbl_caption = f"Table {chap_num}.{s}: Empirical Performance Metrics"
                    doc.add_paragraph(tbl_caption)
                    tbl = doc.add_table(rows=3, cols=3)
                    tbl.style = "Table Grid"
                    for r in range(3):
                        for c in range(3):
                            tbl.cell(r, c).text = f"Val {r},{c}"
                    accumulated_words += 25

            # Chapter page break
            doc.add_page_break()
            chap_num += 1

        doc.save(output_path)
        return output_path


def main():
    parser = argparse.ArgumentParser(description="Synthetic DOCX Generator")
    parser.add_argument("--pages", type=int, default=100, help="Target pages (100, 500, 1000, 5000, 10000)")
    parser.add_argument("--output", type=str, default="synthetic_sample.docx", help="Output path")
    args = parser.parse_args()

    print(f"Generating synthetic manuscript of ~{args.pages} pages...")
    path = SyntheticDocumentGenerator.create_document(args.pages, args.output)
    print(f"Done! Saved to: {path}")


if __name__ == "__main__":
    main()
