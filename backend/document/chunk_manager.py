"""
Context-Aware Chunk Manager.

Partitions large documents along logical boundaries (Chapters, Sections)
rather than blind page cuts, attaching boundary context for ML classification.
"""

from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .model import Block, BlockType


class Chunk(BaseModel):
    chunk_id: str
    chapter_index: int = 0
    chapter_title: str = ""
    start_index: int
    end_index: int
    blocks: List[Block] = Field(default_factory=list)
    prev_context: List[Block] = Field(default_factory=list)
    next_context: List[Block] = Field(default_factory=list)
    status: str = "PENDING"  # PENDING, PROCESSING, COMPLETED, FAILED
    retry_count: int = 0
    error_message: Optional[str] = None

    def total_words(self) -> int:
        return sum(b.word_count() for b in self.blocks)


class ChunkManager:
    """
    Manages generation, disk caching, and boundary preservation for
    high-throughput parallel processing.
    """

    def __init__(self, chunk_dir: str):
        self.chunk_dir = chunk_dir
        os.makedirs(chunk_dir, exist_ok=True)

    def partition(
        self,
        blocks: List[Block],
        target_size: int = 150,
        context_window: int = 3,
    ) -> List[Chunk]:
        """
        Partitions a flat block stream into semantic chunks, favoring chapter
        boundaries and section dividers over arbitrary cutoffs.
        """
        if not blocks:
            return []

        chunks: List[Chunk] = []
        current_chunk_blocks: List[Block] = []
        current_chapter_idx = 0
        current_chapter_title = "Front Matter"
        chunk_counter = 0

        for i, b in enumerate(blocks):
            # Check if block is a natural boundary
            is_new_chapter = (
                b.block_type == BlockType.CHAPTER_TITLE
                or "chapter" in b.text.lower()[:15]
            )

            # Trigger split if we hit a chapter boundary OR exceeded target_size
            should_split = False
            if current_chunk_blocks:
                if is_new_chapter:
                    should_split = True
                elif len(current_chunk_blocks) >= target_size and b.block_type in (
                    BlockType.HEADING_1,
                    BlockType.HEADING_2,
                    BlockType.PAGE_BREAK,
                ):
                    should_split = True
                elif len(current_chunk_blocks) >= target_size * 1.5:
                    should_split = True

            if should_split and current_chunk_blocks:
                chunk_id = f"chunk_{chunk_counter:04d}"
                start_idx = current_chunk_blocks[0].original_index
                end_idx = current_chunk_blocks[-1].original_index

                # Extract context windows
                prev_start = max(0, start_idx - context_window)
                prev_ctx = blocks[prev_start:start_idx]

                next_end = min(len(blocks), end_idx + 1 + context_window)
                next_ctx = blocks[end_idx + 1:next_end]

                chunk = Chunk(
                    chunk_id=chunk_id,
                    chapter_index=current_chapter_idx,
                    chapter_title=current_chapter_title,
                    start_index=start_idx,
                    end_index=end_idx,
                    blocks=current_chunk_blocks,
                    prev_context=prev_ctx,
                    next_context=next_ctx,
                )
                chunks.append(chunk)
                chunk_counter += 1
                current_chunk_blocks = []

            if is_new_chapter:
                current_chapter_idx += 1
                current_chapter_title = b.text if b.text else f"Chapter {current_chapter_idx}"

            current_chunk_blocks.append(b)

        # Append remaining blocks
        if current_chunk_blocks:
            chunk_id = f"chunk_{chunk_counter:04d}"
            start_idx = current_chunk_blocks[0].original_index
            end_idx = current_chunk_blocks[-1].original_index

            prev_start = max(0, start_idx - context_window)
            prev_ctx = blocks[prev_start:start_idx]

            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    chapter_index=current_chapter_idx,
                    chapter_title=current_chapter_title,
                    start_index=start_idx,
                    end_index=end_idx,
                    blocks=current_chunk_blocks,
                    prev_context=prev_ctx,
                    next_context=[],
                )
            )

        return chunks

    def save_chunk(self, chunk: Chunk) -> str:
        """Persist chunk to disk for crash resilience and worker retrieval."""
        file_path = os.path.join(self.chunk_dir, f"{chunk.chunk_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(chunk.model_dump_json(indent=2))
        return file_path

    def load_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Load chunk from disk."""
        file_path = os.path.join(self.chunk_dir, f"{chunk_id}.json")
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Chunk.model_validate(data)

    def list_chunk_ids(self) -> List[str]:
        """List all saved chunk IDs in order."""
        files = [
            f[:-5]
            for f in os.listdir(self.chunk_dir)
            if f.startswith("chunk_") and f.endswith(".json")
        ]
        files.sort()
        return files
