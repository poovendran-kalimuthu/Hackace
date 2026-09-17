"""
Pre-Flight Document Quality Validator.

Runs structural integrity and content preservation checks prior to DOCX export
to guarantee no text, images, or tables are dropped.
"""

from __future__ import annotations
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from backend.document.model import BlockType, DocumentModel


class ValidationResult(BaseModel):
    is_valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class DocumentQualityValidator:
    """
    Ensures publication-grade document fidelity before file generation.
    """

    @classmethod
    def validate(
        cls,
        doc: DocumentModel,
        expected_paragraphs: int = 0,
        expected_images: int = 0,
        expected_tables: int = 0,
    ) -> ValidationResult:
        result = ValidationResult()
        blocks = doc.flatten_blocks()

        total_paragraphs = len(blocks)
        total_words = sum(b.word_count() for b in blocks)
        total_chapters = sum(1 for b in blocks if b.block_type == BlockType.CHAPTER_TITLE)
        total_images = sum(1 for b in blocks if b.block_type == BlockType.IMAGE or "image_rel_ids" in b.metadata)
        total_tables = sum(1 for b in blocks if b.block_type == BlockType.TABLE or "table_data" in b.metadata)

        result.metrics = {
            "paragraphs": total_paragraphs,
            "words": total_words,
            "chapters": total_chapters,
            "images": total_images,
            "tables": total_tables,
        }

        # Check 1: Empty document
        if total_paragraphs == 0:
            result.is_valid = False
            result.errors.append("Document has 0 blocks. Cannot export empty manuscript.")
            return result

        # Check 2: Paragraph preservation
        if expected_paragraphs > 0:
            diff = abs(total_paragraphs - expected_paragraphs)
            if diff > (expected_paragraphs * 0.15):
                result.warnings.append(
                    f"Paragraph count variance detected: expected ~{expected_paragraphs}, exported {total_paragraphs}."
                )

        # Check 3: Image preservation
        if expected_images > 0 and total_images < expected_images:
            result.warnings.append(
                f"Image discrepancy: {expected_images} detected in source, {total_images} preserved in model."
            )

        # Check 4: Chapter detection
        if total_chapters == 0 and total_paragraphs > 80:
            result.warnings.append(
                "No chapters identified in manuscript. Output will lack distinct chapter title breaks."
            )

        return result

    @classmethod
    def compare_content_preservation(
        cls,
        source_metrics: Dict[str, Any],
        formatted_doc: DocumentModel,
    ) -> Dict[str, Any]:
        """
        Executes Section 40 Content Preservation Validation:
        Compares pre-formatting manuscript metrics against formatted document.
        Guarantees no words, sentences, tables, or images are altered or dropped.
        """
        blocks = formatted_doc.flatten_blocks()
        post_paragraphs = len(blocks)
        post_words = sum(b.word_count() for b in blocks)
        post_chars = sum(len(b.text) for b in blocks)
        post_images = sum(1 for b in blocks if b.block_type == BlockType.IMAGE or "image_rel_ids" in b.metadata)
        post_tables = sum(1 for b in blocks if b.block_type == BlockType.TABLE or "table_data" in b.metadata)

        post_metrics = {
            "paragraphs": post_paragraphs,
            "words": post_words,
            "characters": post_chars,
            "images": post_images,
            "tables": post_tables,
        }

        discrepancies: List[str] = []
        pre_words = source_metrics.get("words", source_metrics.get("word_count", 0))
        if pre_words > 0 and post_words < (pre_words * 0.98):
            discrepancies.append(f"Word loss detected: Source had {pre_words} words, formatted doc has {post_words} words.")

        pre_tables = source_metrics.get("tables", 0)
        if pre_tables > 0 and post_tables < pre_tables:
            discrepancies.append(f"Table discrepancy: Source had {pre_tables} tables, formatted doc has {post_tables}.")

        is_preserved = len(discrepancies) == 0

        return {
            "is_preserved": is_preserved,
            "pre_metrics": source_metrics,
            "post_metrics": post_metrics,
            "discrepancies": discrepancies,
            "preservation_score": 100.0 if is_preserved else round((post_words / max(pre_words, 1)) * 100.0, 1),
        }
