"""
Persistent SQLite-backed Document Indexer.

Enables instant random access, chapter jumping, page location,
and high-speed search across 10,000+ page manuscripts.
"""

from __future__ import annotations
import math
import sqlite3
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

from .model import Block, BlockType


class DocumentIndexer:
    """
    Manages indexing, pagination estimation, chapter hierarchy mapping,
    and full-text lookup in SQLite.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS document_index (
                    document_id TEXT NOT NULL,
                    block_id TEXT NOT NULL PRIMARY KEY,
                    original_index INTEGER NOT NULL,
                    chapter_id TEXT,
                    chapter_title TEXT,
                    section_id TEXT,
                    block_type TEXT NOT NULL,
                    text_preview TEXT,
                    full_text TEXT,
                    word_count INTEGER NOT NULL,
                    char_count INTEGER NOT NULL,
                    has_images INTEGER DEFAULT 0,
                    has_tables INTEGER DEFAULT 0,
                    is_heading INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 1.0,
                    estimated_page INTEGER NOT NULL,
                    raw_json TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_doc_orig ON document_index (document_id, original_index)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_doc_page ON document_index (document_id, estimated_page)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_doc_chap ON document_index (document_id, chapter_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_doc_type ON document_index (document_id, block_type)"
            )

    def index_blocks(
        self,
        document_id: str,
        blocks: Iterable[Block],
        words_per_page: int = 280,
    ) -> Dict[str, Any]:
        """
        Streamingly index blocks, tracking running word counts to compute
        estimated pagination, chapter boundaries, and structural metrics.
        """
        records: List[Tuple] = []
        running_words = 0
        current_chapter_id: Optional[str] = None
        current_chapter_title: str = "Front Matter"
        total_chapters = 0
        total_images = 0
        total_tables = 0

        type_counts: Dict[str, int] = {}

        for b in blocks:
            w_count = b.word_count()
            c_count = b.char_count()
            running_words += max(w_count, 1 if b.text else 0)
            page_num = max(1, math.ceil(running_words / words_per_page))

            # Detect chapter transitions (either by block_type or regex/text pattern)
            is_chap = (
                b.block_type == BlockType.CHAPTER_TITLE
                or b.text.strip().lower().startswith("chapter ")
                or b.text.strip().lower().startswith("chapter:")
            )
            if is_chap:
                total_chapters += 1
                current_chapter_id = b.id
                current_chapter_title = b.text if b.text else f"Chapter {total_chapters}"

            has_img = 1 if (b.block_type == BlockType.IMAGE or "image_rel_ids" in b.metadata) else 0
            has_tbl = 1 if (b.block_type == BlockType.TABLE or "table_data" in b.metadata) else 0

            if has_img:
                total_images += 1
            if has_tbl:
                total_tables += 1

            is_hd = 1 if b.block_type in (
                BlockType.CHAPTER_TITLE,
                BlockType.HEADING_1,
                BlockType.HEADING_2,
                BlockType.HEADING_3,
            ) else 0

            type_counts[b.block_type.value] = type_counts.get(b.block_type.value, 0) + 1

            preview = (b.text[:120] + "...") if len(b.text) > 120 else b.text
            raw_json = b.model_dump_json()

            records.append(
                (
                    document_id,
                    b.id,
                    b.original_index,
                    current_chapter_id,
                    current_chapter_title,
                    None,  # section_id
                    b.block_type.value,
                    preview,
                    b.text,
                    w_count,
                    c_count,
                    has_img,
                    has_tbl,
                    is_hd,
                    b.confidence,
                    page_num,
                    raw_json,
                )
            )

        with self._get_conn() as conn:
            # Clear previous index for this document
            conn.execute("DELETE FROM document_index WHERE document_id = ?", (document_id,))
            conn.executemany(
                """
                INSERT OR REPLACE INTO document_index (
                    document_id, block_id, original_index, chapter_id, chapter_title,
                    section_id, block_type, text_preview, full_text, word_count,
                    char_count, has_images, has_tables, is_heading, confidence,
                    estimated_page, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )

        total_pages = max(1, math.ceil(running_words / words_per_page))
        return {
            "total_blocks": len(records),
            "total_words": running_words,
            "estimated_pages": total_pages,
            "total_chapters": total_chapters,
            "total_images": total_images,
            "total_tables": total_tables,
            "type_counts": type_counts,
        }

    def get_document_stats(self, document_id: str) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT 
                    COUNT(*) as total_blocks,
                    COALESCE(SUM(word_count), 0) as total_words,
                    COALESCE(SUM(char_count), 0) as total_chars,
                    COALESCE(MAX(estimated_page), 1) as total_pages,
                    COALESCE(SUM(has_images), 0) as total_images,
                    COALESCE(SUM(has_tables), 0) as total_tables
                FROM document_index
                WHERE document_id = ?
                """,
                (document_id,),
            )
            row = cursor.fetchone()
            if not row:
                return {}

            stats = dict(row)

            # Get counts by block_type
            type_cursor = conn.execute(
                "SELECT block_type, COUNT(*) as cnt FROM document_index WHERE document_id = ? GROUP BY block_type",
                (document_id,),
            )
            stats["types"] = {r["block_type"]: r["cnt"] for r in type_cursor.fetchall()}
            return stats

    def get_chapters(self, document_id: str) -> List[Dict[str, Any]]:
        """Retrieve chapter list with start block index, title, and page."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT chapter_id, chapter_title, MIN(original_index) as start_idx, MIN(estimated_page) as start_page, COUNT(*) as block_count
                FROM document_index
                WHERE document_id = ? AND chapter_id IS NOT NULL
                GROUP BY chapter_id, chapter_title
                ORDER BY start_idx ASC
                """,
                (document_id,),
            )
            return [dict(r) for r in cursor.fetchall()]

    def get_blocks_for_page(self, document_id: str, page_number: int) -> List[Block]:
        """Lazy load blocks for a specific page without loading the entire document."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT raw_json FROM document_index WHERE document_id = ? AND estimated_page = ? ORDER BY original_index ASC",
                (document_id, page_number),
            )
            return [Block.model_validate_json(r["raw_json"]) for r in cursor.fetchall()]

    def get_blocks_range(self, document_id: str, start_index: int, limit: int = 100) -> List[Block]:
        """Retrieve a specific range of blocks by original index."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT raw_json FROM document_index 
                WHERE document_id = ? AND original_index >= ? 
                ORDER BY original_index ASC 
                LIMIT ?
                """,
                (document_id, start_index, limit),
            )
            return [Block.model_validate_json(r["raw_json"]) for r in cursor.fetchall()]

    def update_block_type(self, block_id: str, new_type: BlockType, user_corrected: bool = True) -> bool:
        """Update block type when user or rule engine corrects it."""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT raw_json FROM document_index WHERE block_id = ?", (block_id,))
            row = cursor.fetchone()
            if not row:
                return False
            block = Block.model_validate_json(row["raw_json"])
            block.block_type = new_type
            block.user_corrected = user_corrected
            updated_json = block.model_dump_json()

            is_hd = 1 if new_type in (
                BlockType.CHAPTER_TITLE,
                BlockType.HEADING_1,
                BlockType.HEADING_2,
                BlockType.HEADING_3,
            ) else 0

            conn.execute(
                """
                UPDATE document_index 
                SET block_type = ?, is_heading = ?, confidence = 1.0, raw_json = ? 
                WHERE block_id = ?
                """,
                (new_type.value, is_hd, updated_json, block_id),
            )
            return True

    def search(self, document_id: str, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Instant search across full text with chapter context and page offsets."""
        with self._get_conn() as conn:
            like_query = f"%{query}%"
            cursor = conn.execute(
                """
                SELECT block_id, original_index, chapter_title, block_type, text_preview, estimated_page
                FROM document_index
                WHERE document_id = ? AND full_text LIKE ?
                ORDER BY original_index ASC
                LIMIT ?
                """,
                (document_id, like_query, limit),
            )
            return [dict(r) for r in cursor.fetchall()]
