"""
Central Job Manager.

Coordinates document analysis, chunking, parallel ML classification,
rule validation, and publication export with real-time telemetry and crash recovery.
"""

from __future__ import annotations
import os
import threading
import time
import uuid
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from backend.document.chunk_manager import ChunkManager
from backend.document.indexer import DocumentIndexer
from backend.document.model import Block, BlockType, DocumentModel
from backend.document.parser import DocumentParser
from backend.export.docx import DocxExporter
from backend.export.validator import DocumentQualityValidator
from backend.formatting.engine import FormattingEngine
from backend.ml.cascade import ConfidenceCascade
from backend.ml.classifier import DocumentElementClassifier
from backend.rules.structure_graph import DocumentStructureGraph
from backend.rules.validator import RuleEngine
from backend.storage.database import Database
from backend.templates.manager import TemplateManager
from .recovery import CheckpointManager
from .workers import DualExecutorPool


class JobState(str, Enum):
    QUEUED = "QUEUED"
    INDEXING = "INDEXING"
    CHUNKING = "CHUNKING"
    ANALYZING = "ANALYZING"
    VALIDATING = "VALIDATING"
    FORMATTING = "FORMATTING"
    ASSEMBLING = "ASSEMBLING"
    EXPORTING = "EXPORTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"


class JobManager:
    """
    State machine and asynchronous pipeline orchestrator.
    """

    def __init__(
        self,
        db: Database,
        executor_pool: DualExecutorPool,
        template_manager: TemplateManager,
    ):
        self.db = db
        self.pool = executor_pool
        self.template_manager = template_manager
        self.checkpoint_mgr = CheckpointManager(db)
        self.classifier = DocumentElementClassifier()
        self.cascade = ConfidenceCascade(self.classifier)
        self.rule_engine = RuleEngine()

        self._active_jobs: Dict[str, Dict[str, Any]] = {}
        self._cancel_flags: Dict[str, bool] = {}
        self._pause_flags: Dict[str, bool] = {}
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for live WebSocket broadcasts."""
        self._subscribers.append(callback)

    def _notify(self, job_data: Dict[str, Any]) -> None:
        metrics = self.pool.get_system_metrics()
        job_data["telemetry"] = metrics
        for sub in self._subscribers:
            try:
                sub(job_data)
            except Exception:
                pass

    def start_pipeline_job(
        self,
        project_id: str,
        input_docx: str,
        project_dir: str,
        template_id: str = "classic_novel",
        output_docx: Optional[str] = None,
    ) -> str:
        """Launches the complete asynchronous processing pipeline."""
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        out_file = output_docx or os.path.join(project_dir, "output", "formatted_book.docx")

        job_info: Dict[str, Any] = {
            "job_id": job_id,
            "project_id": project_id,
            "input_file": input_docx,
            "template_id": template_id,
            "status": JobState.QUEUED.value,
            "progress": 0.0,
            "current_stage": JobState.QUEUED.value,
            "current_chunk": 0,
            "total_chunks": 0,
            "errors": [],
            "warnings": [],
            "output_file": out_file,
            "project_dir": project_dir,
        }

        self._active_jobs[job_id] = job_info
        self._cancel_flags[job_id] = False
        self._pause_flags[job_id] = False
        self.db.create_or_update_job(job_info)
        self._notify(job_info)

        # Dispatch execution on background ThreadPool
        self.pool.submit_io(self._run_pipeline, job_id)
        return job_id

    def cancel_job(self, job_id: str) -> bool:
        if job_id in self._active_jobs:
            self._cancel_flags[job_id] = True
            self._active_jobs[job_id]["status"] = JobState.CANCELLED.value
            self.db.create_or_update_job(self._active_jobs[job_id])
            self._notify(self._active_jobs[job_id])
            return True
        return False

    def pause_job(self, job_id: str) -> bool:
        if job_id in self._active_jobs:
            self._pause_flags[job_id] = True
            self._active_jobs[job_id]["status"] = JobState.PAUSED.value
            self.db.create_or_update_job(self._active_jobs[job_id])
            self._notify(self._active_jobs[job_id])
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        if job_id in self._active_jobs:
            self._pause_flags[job_id] = False
            self.pool.submit_io(self._run_pipeline, job_id)
            return True
        return False

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        if job_id in self._active_jobs:
            status = dict(self._active_jobs[job_id])
            status["telemetry"] = self.pool.get_system_metrics()
            return status
        db_job = self.db.get_job(job_id)
        if db_job:
            db_job["telemetry"] = self.pool.get_system_metrics()
            return db_job
        return None

    # ----------------- Pipeline Execution Worker ----------------- #

    def _run_pipeline(self, job_id: str) -> None:
        job = self._active_jobs[job_id]
        project_dir = job["project_dir"]
        input_docx = job["input_file"]
        project_id = job["project_id"]
        template_id = job["template_id"]
        out_file = job["output_file"]

        try:
            # Stage 1: INDEXING
            job["current_stage"] = JobState.INDEXING.value
            job["status"] = JobState.INDEXING.value
            job["progress"] = 10.0
            self.db.create_or_update_job(job)
            self._notify(job)

            if self._check_control(job_id):
                return

            db_path = os.path.join(project_dir, "database", "project.db")
            indexer = DocumentIndexer(db_path)
            chunks_dir = os.path.join(project_dir, "chunks")
            chunk_mgr = ChunkManager(chunks_dir)

            parser = DocumentParser(input_docx)
            meta = parser.scan_and_index(
                document_id=project_id,
                indexer=indexer,
                chunk_manager=chunk_mgr,
            )

            # Stage 2: CHUNKING
            job["current_stage"] = JobState.CHUNKING.value
            job["status"] = JobState.CHUNKING.value
            job["progress"] = 25.0
            chunk_ids = chunk_mgr.list_chunk_ids()
            job["total_chunks"] = len(chunk_ids)
            self.db.create_or_update_job(job)
            self._notify(job)

            if self._check_control(job_id):
                return

            # Stage 3: ANALYZING (Chunked Parallel Processing & Checkpointing)
            job["current_stage"] = JobState.ANALYZING.value
            job["status"] = JobState.ANALYZING.value
            self.db.create_or_update_job(job)
            self._notify(job)

            completed_chunks = self.checkpoint_mgr.get_completed_chunk_ids(job_id, "ANALYZING")
            classified_blocks: List[Block] = []

            for idx, ch_id in enumerate(chunk_ids):
                if self._check_control(job_id):
                    return

                job["current_chunk"] = idx + 1
                job["progress"] = 25.0 + (35.0 * ((idx + 1) / max(1, len(chunk_ids))))
                self.db.create_or_update_job(job)
                self._notify(job)

                # Check if already processed in prior run (Crash Recovery per Section 22)
                if ch_id in completed_chunks:
                    cached_chunk = chunk_mgr.load_chunk(ch_id)
                    if cached_chunk:
                        classified_blocks.extend(cached_chunk.blocks)
                        continue

                chunk = chunk_mgr.load_chunk(ch_id)
                if not chunk:
                    continue

                # Classify blocks in this chunk with boundary awareness
                chunk_classified: List[Block] = []
                n_blocks = len(chunk.blocks)

                for b_idx, block in enumerate(chunk.blocks):
                    prev_b = chunk.blocks[b_idx - 1] if b_idx > 0 else (chunk.prev_context[-1] if chunk.prev_context else None)
                    next_b = chunk.blocks[b_idx + 1] if b_idx + 1 < n_blocks else (chunk.next_context[0] if chunk.next_context else None)

                    pred_type, conf, needs_review = self.cascade.evaluate(
                        block, prev_b, next_b, total_blocks=meta.total_paragraphs
                    )
                    block.predicted_type = pred_type
                    block.confidence = conf
                    if not block.user_corrected:
                        block.block_type = pred_type
                    chunk_classified.append(block)

                    # Update index with latest prediction & confidence
                    indexer.update_block_type(block.id, block.block_type, user_corrected=block.user_corrected)

                chunk.blocks = chunk_classified
                chunk.status = "COMPLETED"
                chunk_mgr.save_chunk(chunk)
                classified_blocks.extend(chunk_classified)

                # Record checkpoint
                self.checkpoint_mgr.record_chunk_completed(
                    job_id=job_id,
                    chunk_id=ch_id,
                    stage="ANALYZING",
                    result_payload={"block_count": len(chunk_classified)},
                )

            # Stage 4: VALIDATING (Deterministic Rule Engine)
            job["current_stage"] = JobState.VALIDATING.value
            job["status"] = JobState.VALIDATING.value
            job["progress"] = 65.0
            self.db.create_or_update_job(job)
            self._notify(job)

            if self._check_control(job_id):
                return

            validated_blocks, rule_report = self.rule_engine.validate_and_refine(classified_blocks)
            if rule_report.get("warnings"):
                job["warnings"].extend(rule_report["warnings"])

            # Build DocumentStructureGraph
            struct_tree = DocumentStructureGraph.build(validated_blocks, book_title=meta.title)
            analysis_dir = os.path.join(project_dir, "analysis")
            with open(os.path.join(analysis_dir, "structure_graph.json"), "w", encoding="utf-8") as f:
                f.write(struct_tree.model_dump_json(indent=2))

            # Assemble into DocumentModel
            doc_model = DocumentModel(
                metadata=meta,
                blocks=validated_blocks,
            )

            # Stage 5: FORMATTING (Smart Layout Engine)
            job["current_stage"] = JobState.FORMATTING.value
            job["status"] = JobState.FORMATTING.value
            job["progress"] = 80.0
            self.db.create_or_update_job(job)
            self._notify(job)

            if self._check_control(job_id):
                return

            template = self.template_manager.get_template(template_id)
            formatting_engine = FormattingEngine(template)
            doc_model, layout_pages = formatting_engine.format_document(doc_model)

            # Stage 6: EXPORTING (Quality Validation & DOCX Export)
            job["current_stage"] = JobState.EXPORTING.value
            job["status"] = JobState.EXPORTING.value
            job["progress"] = 90.0
            self.db.create_or_update_job(job)
            self._notify(job)

            if self._check_control(job_id):
                return

            # Pre-flight quality validation
            val_res = DocumentQualityValidator.validate(
                doc_model,
                expected_paragraphs=meta.total_paragraphs,
                expected_images=meta.total_images,
                expected_tables=meta.total_tables,
            )
            if val_res.warnings:
                job["warnings"].extend(val_res.warnings)
            if not val_res.is_valid:
                job["status"] = JobState.FAILED.value
                job["errors"].extend(val_res.errors)
                self.db.create_or_update_job(job)
                self._notify(job)
                return

            # Check for publisher logo in project assets
            logo_asset = self.db.get_logo_asset(project_id)
            logo_path = logo_asset["file_path"] if logo_asset and os.path.exists(logo_asset.get("file_path", "")) else None

            exporter = DocxExporter(template)
            exporter.export(doc_model, out_file, logo_path=logo_path)

            # Section 40: Content Preservation Validation & Certificate
            preservation_report = DocumentQualityValidator.compare_content_preservation(
                source_metrics={
                    "paragraphs": meta.total_paragraphs,
                    "words": meta.total_words,
                    "images": meta.total_images,
                    "tables": meta.total_tables,
                },
                formatted_doc=doc_model,
            )
            self.db.save_validation_report(
                job_id=job_id,
                project_id=project_id,
                pre_metrics=preservation_report["pre_metrics"],
                post_metrics=preservation_report["post_metrics"],
                is_preserved=preservation_report["is_preserved"],
                discrepancies=preservation_report["discrepancies"],
            )

            # Stage 7: COMPLETED
            job["current_stage"] = JobState.COMPLETED.value
            job["status"] = JobState.COMPLETED.value
            job["progress"] = 100.0
            job["output_file"] = out_file
            job["preservation"] = preservation_report
            self.db.create_or_update_job(job)
            self._notify(job)

        except Exception as e:
            job["status"] = JobState.FAILED.value
            job["errors"].append(str(e))
            self.db.create_or_update_job(job)
            self._notify(job)

    def _check_control(self, job_id: str) -> bool:
        """Returns True if task should halt (cancelled or paused)."""
        if self._cancel_flags.get(job_id, False):
            return True
        while self._pause_flags.get(job_id, False):
            time.sleep(0.5)
            if self._cancel_flags.get(job_id, False):
                return True
        return False
