"""
Crash Recovery & Checkpointing Manager.

Persists incremental chunk processing milestones in SQLite to enable
frictionless resumption of interrupted jobs on 10,000+ page manuscripts.
"""

from __future__ import annotations
import os
from typing import Any, Dict, List, Set

from backend.storage.database import Database


class CheckpointManager:
    """
    Tracks and retrieves persistent chunk progress.
    """

    def __init__(self, db: Database):
        self.db = db

    def record_chunk_completed(
        self,
        job_id: str,
        chunk_id: str,
        stage: str,
        result_payload: Any,
    ) -> None:
        """Saves milestone for a single chunk."""
        self.db.save_checkpoint(
            job_id=job_id,
            chunk_id=chunk_id,
            stage=stage,
            status="COMPLETED",
            result=result_payload,
        )

    def get_completed_chunk_ids(self, job_id: str, stage: str) -> Set[str]:
        """Returns set of all chunk IDs already completed for this job & stage."""
        checkpoints = self.db.get_checkpoints(job_id=job_id, stage=stage)
        return {cp["chunk_id"] for cp in checkpoints if cp["status"] == "COMPLETED"}

    def get_checkpoint_results(self, job_id: str, stage: str) -> Dict[str, Any]:
        """Loads results for all completed checkpoints in order."""
        checkpoints = self.db.get_checkpoints(job_id=job_id, stage=stage)
        res: Dict[str, Any] = {}
        for cp in checkpoints:
            res[cp["chunk_id"]] = cp.get("result")
        return res
