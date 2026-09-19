"""
FastAPI Desktop Server.

Exposes REST and WebSocket endpoints for project management, streaming job execution,
human-in-the-loop review triage, virtualized preview rendering, and visual template editing.
"""

import asyncio
import json
import os
import shutil
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.document.indexer import DocumentIndexer
from backend.document.model import BlockType
from backend.document.parser import DocumentParser
from backend.generator.synthetic_docs import SyntheticDocumentGenerator
from backend.jobs.manager import JobManager
from backend.jobs.workers import DualExecutorPool
from backend.security.logo_validator import LogoValidator
from backend.security.security_service import SecurityService
from backend.storage.database import Database
from backend.storage.projects import ProjectManager
from backend.templates.manager import TemplateManager
from backend.templates.schema import BookTemplate


# Request DTOs
class ProjectCreateReq(BaseModel):
    name: str
    description: str = ""
    template_id: str = "book"


class ProjectUpdateReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_id: Optional[str] = None


class StartJobReq(BaseModel):
    template_id: Optional[str] = "book"


class CorrectionReq(BaseModel):
    block_id: str
    corrected_type: str
    predicted_type: str
    original_text: str = ""


class GenerateSampleReq(BaseModel):
    pages: int = 100
    project_id: Optional[str] = None


def create_app(workspace_root: Optional[str] = None) -> FastAPI:
    root_dir = workspace_root or os.path.join(os.getcwd(), "workspaces")
    os.makedirs(root_dir, exist_ok=True)

    app = FastAPI(
        title="Intelligent Offline Document & Book Formatting Platform",
        version="1.0.0",
        description="Local desktop backend for large document understanding and publication formatting.",
    )

    # Local Desktop Security: Restrict CORS to local origins
    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "tauri://localhost",
        "http://tauri.localhost",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Shared singletons
    project_mgr = ProjectManager(root_dir)
    template_mgr = TemplateManager(os.path.join(root_dir, "custom_templates"))
    executor_pool = DualExecutorPool()
    global_db = project_mgr.global_db
    job_mgr = JobManager(global_db, executor_pool, template_mgr)

    # Connected WebSocket clients for telemetry streaming
    active_connections: List[WebSocket] = []
    main_loop: Optional[asyncio.AbstractEventLoop] = None

    @app.on_event("startup")
    async def on_startup():
        nonlocal main_loop
        main_loop = asyncio.get_running_loop()

    def broadcast_telemetry(payload: Dict[str, Any]):
        msg = json.dumps(payload)
        dead = []
        for ws in list(active_connections):
            try:
                if main_loop and main_loop.is_running():
                    asyncio.run_coroutine_threadsafe(ws.send_text(msg), main_loop)
            except Exception:
                dead.append(ws)
        for d in dead:
            if d in active_connections:
                active_connections.remove(d)

    job_mgr.subscribe(broadcast_telemetry)

    @app.websocket("/ws/telemetry")
    async def websocket_telemetry(websocket: WebSocket):
        await websocket.accept()
        active_connections.append(websocket)
        try:
            while True:
                # Keep connection alive, listen for any client heartbeat
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            if websocket in active_connections:
                active_connections.remove(websocket)

    # ------------------ System & Diagnostics ------------------ #

    @app.get("/api/health")
    def health_check():
        return {"status": "ONLINE", "mode": "OFFLINE_LOCAL", "version": "1.0.0"}

    @app.get("/api/diagnostics")
    def get_diagnostics():
        metrics = executor_pool.get_system_metrics()
        metrics["db"] = global_db.get_engine_info()
        return metrics

    @app.get("/api/storage/status")
    def get_storage_status():
        return global_db.get_storage_stats()

    # ------------------ Projects Endpoints ------------------ #

    @app.get("/api/projects")
    def list_projects():
        return project_mgr.list_projects()

    @app.post("/api/projects")
    def create_project(req: ProjectCreateReq):
        record = project_mgr.create_project(
            name=req.name,
            description=req.description,
            template_id=req.template_id,
        )
        return record.model_dump()

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str):
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")
        return p

    @app.patch("/api/projects/{project_id}")
    def update_project(project_id: str, req: ProjectUpdateReq):
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        project_mgr.update_project(project_id, updates)
        return project_mgr.get_project(project_id)

    @app.delete("/api/projects/{project_id}")
    def delete_project(project_id: str):
        success = project_mgr.delete_project(project_id)
        return {"success": success}

    @app.post("/api/projects/{project_id}/duplicate")
    def duplicate_project(project_id: str, new_name: str = Query(...)):
        new_proj = project_mgr.duplicate_project(project_id, new_name)
        return new_proj.model_dump()

    @app.post("/api/projects/{project_id}/upload")
    async def upload_manuscript(project_id: str, file: UploadFile = File(...)):
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        source_dir = os.path.join(p["root_dir"], "source")
        clean_name = LogoValidator.sanitize_filename(file.filename or "manuscript.docx")
        dest_path = os.path.join(source_dir, clean_name)

        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Security validation for DOCX archive structure
        try:
            SecurityService.validate_docx_package(dest_path)
        except Exception as e:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            raise HTTPException(status_code=400, detail=f"Invalid manuscript package: {str(e)}")

        # Initial scan to populate metadata
        db_path = os.path.join(p["root_dir"], "database", "project.db")
        indexer = DocumentIndexer(db_path, db=global_db)
        parser = DocumentParser(dest_path)
        meta = parser.scan_and_index(document_id=project_id, indexer=indexer)

        project_mgr.update_project(
            project_id,
            {
                "source_filename": file.filename,
                "source_path": dest_path,
                "page_count": meta.estimated_pages,
                "word_count": meta.total_words,
                "chapter_count": meta.total_chapters,
                "status": "ANALYZED",
            },
        )

        global_db.log_audit_event(
            project_id,
            "MANUSCRIPT_UPLOADED",
            {"filename": file.filename, "pages": meta.estimated_pages, "words": meta.total_words},
        )

        return {
            "source_filename": file.filename,
            "source_path": dest_path,
            "metadata": meta.model_dump(),
        }

    # ------------------ Mandatory Publisher Logo Endpoints ------------------ #

    @app.post("/api/projects/{project_id}/logo")
    async def upload_publisher_logo(project_id: str, file: UploadFile = File(...)):
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        raw_bytes = await file.read()
        logo_dir = os.path.join(p["root_dir"], "assets", "logo")
        val_res = LogoValidator.validate_and_save(raw_bytes, file.filename or "logo.png", logo_dir)

        if not val_res.is_valid:
            raise HTTPException(status_code=400, detail=val_res.error_message)

        logo_record = {
            "filename": val_res.sanitized_filename,
            "file_path": val_res.normalized_path,
            "mime_type": val_res.mime_type,
            "sha256": val_res.sha256_hash,
            "width": val_res.width,
            "height": val_res.height,
            "file_size_bytes": val_res.file_size_bytes,
            "is_valid": True,
            "validation_message": "✓ Valid logo",
        }
        global_db.save_logo_asset(project_id, logo_record)
        global_db.log_audit_event(
            project_id,
            "LOGO_UPLOADED",
            {"sha256": val_res.sha256_hash, "size": val_res.file_size_bytes, "dimensions": f"{val_res.width}x{val_res.height}"},
        )

        return {"success": True, "logo": logo_record}

    @app.get("/api/projects/{project_id}/logo")
    def get_publisher_logo(project_id: str):
        logo = global_db.get_logo_asset(project_id)
        if not logo:
            return {"has_logo": False, "logo": None}
        return {"has_logo": True, "logo": logo}

    @app.delete("/api/projects/{project_id}/logo")
    def delete_publisher_logo(project_id: str):
        p = project_mgr.get_project(project_id)
        if p:
            logo_dir = os.path.join(p["root_dir"], "assets", "logo")
            if os.path.exists(logo_dir):
                shutil.rmtree(logo_dir, ignore_errors=True)
                os.makedirs(logo_dir, exist_ok=True)
        global_db.delete_logo_asset(project_id)
        return {"success": True}

    # ------------------ Job Execution Endpoints ------------------ #

    @app.post("/api/projects/{project_id}/jobs")
    def start_job(project_id: str, req: StartJobReq):
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")
        if not p.get("source_path") or not os.path.exists(p["source_path"]):
            raise HTTPException(status_code=400, detail="No source manuscript found in project.")

        # Section 5: Mandatory Publisher / Book Logo Check
        logo_asset = global_db.get_logo_asset(project_id)
        if not logo_asset or not logo_asset.get("is_valid") or not os.path.exists(logo_asset.get("file_path", "")):
            raise HTTPException(
                status_code=400,
                detail="Publisher / Book Logo is mandatory. Please upload a valid publisher logo before formatting.",
            )

        template_choice = req.template_id or p.get("template_id", "book")
        job_id = job_mgr.start_pipeline_job(
            project_id=project_id,
            input_docx=p["source_path"],
            project_dir=p["root_dir"],
            template_id=template_choice,
        )
        global_db.log_audit_event(
            project_id, "JOB_STARTED", {"job_id": job_id, "template_id": template_choice}
        )
        return {"job_id": job_id, "status": "QUEUED"}

    @app.get("/api/projects/{project_id}/comparison")
    def get_project_comparison(project_id: str):
        """Returns Before / After comparison & Content Preservation report."""
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        latest_job = None
        with global_db.get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM jobs WHERE project_id = ? ORDER BY updated_at DESC LIMIT 1",
                (project_id,),
            )
            row = cur.fetchone()
            if row:
                latest_job = dict(row)

        report = None
        if latest_job:
            report = global_db.get_validation_report(latest_job["job_id"])

        return {
            "project_id": project_id,
            "project_name": p["name"],
            "source_filename": p.get("source_filename"),
            "page_count": p.get("page_count", 0),
            "word_count": p.get("word_count", 0),
            "chapter_count": p.get("chapter_count", 0),
            "template_id": p.get("template_id", "book"),
            "validation_report": report,
            "logo_asset": global_db.get_logo_asset(project_id),
        }



    @app.get("/api/jobs/{job_id}")
    def get_job_status(job_id: str):
        status = job_mgr.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        return status

    @app.post("/api/jobs/{job_id}/pause")
    def pause_job(job_id: str):
        return {"success": job_mgr.pause_job(job_id)}

    @app.post("/api/jobs/{job_id}/resume")
    def resume_job(job_id: str):
        return {"success": job_mgr.resume_job(job_id)}

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str):
        return {"success": job_mgr.cancel_job(job_id)}

    # ------------------ Review Queue & Corrections ------------------ #

    @app.get("/api/projects/{project_id}/review")
    def get_review_queue(project_id: str, max_items: int = 50):
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        db_path = os.path.join(p["root_dir"], "database", "project.db")
        if not global_db.using_mysql and not os.path.exists(db_path):
            return []

        indexer = DocumentIndexer(db_path, db=global_db)
        with indexer._get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT block_id, original_index, block_type, text_preview, full_text, confidence, estimated_page
                FROM document_index
                WHERE document_id = ? AND confidence < 0.85
                ORDER BY confidence ASC
                LIMIT ?
                """,
                (project_id, max_items),
            )
            return [dict(r) for r in cursor.fetchall()]

    @app.post("/api/projects/{project_id}/review/correct")
    def submit_correction(project_id: str, req: CorrectionReq):
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        db_path = os.path.join(p["root_dir"], "database", "project.db")
        indexer = DocumentIndexer(db_path, db=global_db)

        new_type = BlockType(req.corrected_type)
        indexer.update_block_type(req.block_id, new_type, user_corrected=True)

        # Store in learning dataset
        global_db.record_correction(
            project_id=project_id,
            block_id=req.block_id,
            original_text=req.original_text,
            predicted_type=req.predicted_type,
            corrected_type=req.corrected_type,
        )

        return {"success": True, "block_id": req.block_id, "new_type": req.corrected_type}

    # ------------------ Virtualized Preview & Search ------------------ #

    @app.get("/api/projects/{project_id}/preview/page/{page_number}")
    def get_page_preview(project_id: str, page_number: int):
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        db_path = os.path.join(p["root_dir"], "database", "project.db")
        if not global_db.using_mysql and not os.path.exists(db_path):
            raise HTTPException(status_code=400, detail="Document not indexed yet.")

        indexer = DocumentIndexer(db_path, db=global_db)
        blocks = indexer.get_blocks_for_page(project_id, page_number)
        stats = indexer.get_document_stats(project_id)

        return {
            "page_number": page_number,
            "total_pages": stats.get("total_pages", 1),
            "blocks": [b.model_dump() for b in blocks],
        }

    @app.get("/api/projects/{project_id}/structure")
    def get_structure(project_id: str):
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        graph_path = os.path.join(p["root_dir"], "analysis", "structure_graph.json")
        if os.path.exists(graph_path):
            with open(graph_path, "r", encoding="utf-8") as f:
                return json.load(f)

        # Fallback to index chapters
        db_path = os.path.join(p["root_dir"], "database", "project.db")
        if global_db.using_mysql or os.path.exists(db_path):
            indexer = DocumentIndexer(db_path, db=global_db)
            return {"chapters": indexer.get_chapters(project_id)}

        return {}

    @app.get("/api/projects/{project_id}/search")
    def search_document(project_id: str, q: str = Query(...), limit: int = 50):
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        db_path = os.path.join(p["root_dir"], "database", "project.db")
        if not global_db.using_mysql and not os.path.exists(db_path):
            return []

        indexer = DocumentIndexer(db_path, db=global_db)
        return indexer.search(project_id, q, limit=limit)

    @app.get("/api/projects/{project_id}/export")
    def export_project_document(project_id: str):
        """Streams the publication-ready formatted DOCX for local download."""
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        root_dir: str = p["root_dir"]
        out_dir = os.path.join(root_dir, "output")

        # Build the expected filename candidates (most-specific first)
        proj_name_safe = "".join(
            c if c.isalnum() or c in ("-", "_") else "_"
            for c in p.get("name", "manuscript")
        ).strip() or "manuscript"
        source_name = p.get("source_filename") or ""
        base_source_safe = "".join(
            c if c.isalnum() or c in ("-", "_") else "_"
            for c in os.path.splitext(source_name)[0]
        ).strip() or proj_name_safe

        # Search output directory for any DOCX
        out_path: str | None = None
        if os.path.exists(out_dir):
            # Prefer files that contain "formatted"
            all_docx = [f for f in os.listdir(out_dir) if f.lower().endswith(".docx")]
            formatted = [f for f in all_docx if "formatted" in f.lower()]
            chosen = formatted[0] if formatted else (all_docx[0] if all_docx else None)
            if chosen:
                out_path = os.path.join(out_dir, chosen)

        if not out_path or not os.path.exists(out_path):
            raise HTTPException(
                status_code=404,
                detail=(
                    "Formatted output DOCX not found. "
                    "Please run a formatting job first."
                ),
            )

        download_name = f"{base_source_safe}_formatted.docx"
        global_db.log_audit_event(
            project_id, "DOCX_EXPORTED", {"filename": os.path.basename(out_path)}
        )
        return FileResponse(
            path=out_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{download_name}"',
                "Cache-Control": "no-cache",
            },
        )

    # ------------------ Performance Analytics Endpoints ------------------ #

    @app.get("/api/analytics/performance")
    def get_performance_analytics():
        """
        Aggregated performance dashboard analytics across all projects and jobs.
        Returns KPI totals, per-job throughput, block-type distribution, and ML confidence.
        """
        try:
            projects = project_mgr.list_projects()
            total_docs = len(projects)
            total_pages = sum(p.get("page_count", 0) for p in projects)
            total_words = sum(p.get("word_count", 0) for p in projects)
            total_chapters = sum(p.get("chapter_count", 0) for p in projects)

            # Pull all jobs
            with global_db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC"
                )
                all_jobs = [dict(r) for r in cursor.fetchall()]

            completed_jobs = [j for j in all_jobs if j.get("status") == "COMPLETED"]
            failed_jobs = [j for j in all_jobs if j.get("status") == "FAILED"]
            total_jobs = len(all_jobs)
            total_completed = len(completed_jobs)

            # Compute per-job durations from timestamps
            job_metrics = []
            for j in all_jobs:
                try:
                    created = j.get("created_at", "")
                    updated = j.get("updated_at", "")
                    if created and updated:
                        from datetime import datetime
                        fmt = "%Y-%m-%dT%H:%M:%S.%f" if "." in created else "%Y-%m-%dT%H:%M:%S"
                        fmt2 = "%Y-%m-%dT%H:%M:%S.%f" if "." in updated else "%Y-%m-%dT%H:%M:%S"
                        t_start = datetime.fromisoformat(created.split("+")[0])
                        t_end = datetime.fromisoformat(updated.split("+")[0])
                        duration_sec = max(0.0, (t_end - t_start).total_seconds())
                    else:
                        duration_sec = 0.0
                except Exception:
                    duration_sec = 0.0

                # Match project to get page/word counts
                proj = next((p for p in projects if p.get("id") == j.get("project_id")), {})
                pages = proj.get("page_count", 0)
                words = proj.get("word_count", 0)

                job_metrics.append({
                    "job_id": j.get("job_id"),
                    "project_id": j.get("project_id"),
                    "project_name": proj.get("name", "Unknown"),
                    "template_id": j.get("template_id", "book"),
                    "status": j.get("status", "UNKNOWN"),
                    "progress": j.get("progress", 0.0),
                    "total_chunks": j.get("total_chunks", 0),
                    "current_chunk": j.get("current_chunk", 0),
                    "pages": pages,
                    "words": words,
                    "duration_seconds": round(duration_sec, 2),
                    "pages_per_second": round(pages / duration_sec, 2) if duration_sec > 0 else 0,
                    "words_per_second": round(words / duration_sec, 1) if duration_sec > 0 else 0,
                    "created_at": j.get("created_at", ""),
                    "updated_at": j.get("updated_at", ""),
                })

            # Average processing time across completed jobs
            completed_durations = [m["duration_seconds"] for m in job_metrics if m["status"] == "COMPLETED"]
            avg_duration = round(sum(completed_durations) / len(completed_durations), 2) if completed_durations else 0

            # Block-type distribution across all documents (from global document_index)
            block_type_stats = {}
            try:
                with global_db.get_connection() as conn:
                    cursor = conn.execute(
                        """
                        SELECT block_type,
                               COUNT(*) as count,
                               AVG(confidence) as avg_confidence,
                               SUM(word_count) as total_words
                        FROM document_index
                        GROUP BY block_type
                        ORDER BY count DESC
                        """
                    )
                    for row in cursor.fetchall():
                        r = dict(row)
                        block_type_stats[r["block_type"]] = {
                            "count": r["count"],
                            "avg_confidence": round(float(r["avg_confidence"] or 0), 3),
                            "total_words": r["total_words"] or 0,
                        }
            except Exception:
                pass

            # System metrics snapshot
            system_metrics = executor_pool.get_system_metrics()

            # Recent audit activity
            recent_events = []
            try:
                with global_db.get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT event_type, project_id, details_json, created_at FROM audit_logs ORDER BY created_at DESC LIMIT 20"
                    )
                    for row in cursor.fetchall():
                        r = dict(row)
                        try:
                            r["details"] = json.loads(r.get("details_json", "{}"))
                        except Exception:
                            r["details"] = {}
                        recent_events.append(r)
            except Exception:
                pass

            # ── 5 Key Quality & Performance Metrics ──────────────────────────
            quality_metrics = {}

            try:
                # 1. FORMATTING ACCURACY
                # Weighted avg confidence across all blocks in document_index
                # Penalise for each FAILED job
                with global_db.get_connection() as conn:
                    cur = conn.execute(
                        "SELECT AVG(confidence) as avg_conf, COUNT(*) as total FROM document_index"
                    )
                    row = cur.fetchone()
                    overall_conf = float(dict(row).get("avg_conf") or 0.0) if row else 0.0
                    total_idx_blocks = int(dict(row).get("total") or 0) if row else 0

                fail_penalty = (len(failed_jobs) / total_jobs * 0.10) if total_jobs > 0 else 0
                formatting_accuracy = max(0.0, round((overall_conf - fail_penalty) * 100, 1))
                quality_metrics["formatting_accuracy"] = {
                    "score": formatting_accuracy,
                    "label": "Formatting Accuracy",
                    "description": "Weighted ML confidence across all classified blocks, adjusted for failed jobs",
                    "unit": "%",
                    "detail": {
                        "avg_block_confidence": round(overall_conf * 100, 1),
                        "total_blocks_indexed": total_idx_blocks,
                        "fail_penalty_applied": round(fail_penalty * 100, 1),
                    },
                    "rating": "Excellent" if formatting_accuracy >= 92 else "Good" if formatting_accuracy >= 80 else "Fair" if formatting_accuracy >= 65 else "Poor",
                }

                # 2. STRUCTURE RECOGNITION ACCURACY
                # % of blocks classified with high confidence (≥ 0.85) across all docs
                with global_db.get_connection() as conn:
                    cur = conn.execute(
                        """
                        SELECT
                            SUM(CASE WHEN confidence >= 0.85 THEN 1 ELSE 0 END) as high_conf,
                            COUNT(*) as total,
                            COUNT(DISTINCT block_type) as unique_types
                        FROM document_index
                        """
                    )
                    row = cur.fetchone()
                    sr = dict(row) if row else {}
                    high_conf_blocks = int(sr.get("high_conf") or 0)
                    total_sr_blocks = int(sr.get("total") or 1)
                    unique_types = int(sr.get("unique_types") or 0)

                structure_recognition = round((high_conf_blocks / max(total_sr_blocks, 1)) * 100, 1)
                quality_metrics["structure_recognition_accuracy"] = {
                    "score": structure_recognition,
                    "label": "Structure Recognition Accuracy",
                    "description": "% of document blocks classified with ≥85% ML confidence",
                    "unit": "%",
                    "detail": {
                        "high_confidence_blocks": high_conf_blocks,
                        "total_blocks": total_sr_blocks,
                        "unique_block_types_detected": unique_types,
                    },
                    "rating": "Excellent" if structure_recognition >= 90 else "Good" if structure_recognition >= 75 else "Fair" if structure_recognition >= 60 else "Poor",
                }

                # 3. CONTENT PRESERVATION
                # % of completed jobs where content was 100% preserved
                preserved_count = 0
                total_validation = 0
                try:
                    with global_db.get_connection() as conn:
                        cur = conn.execute(
                            "SELECT COUNT(*) as total, SUM(CASE WHEN is_preserved THEN 1 ELSE 0 END) as preserved FROM validation_reports"
                        )
                        row = cur.fetchone()
                        if row:
                            vr = dict(row)
                            total_validation = int(vr.get("total") or 0)
                            preserved_count = int(vr.get("preserved") or 0)
                except Exception:
                    pass

                if total_validation > 0:
                    content_preservation = round((preserved_count / total_validation) * 100, 1)
                elif total_completed > 0:
                    # Fallback: use success rate as proxy
                    content_preservation = round((total_completed / total_jobs) * 100, 1) if total_jobs > 0 else 0.0
                else:
                    content_preservation = 0.0

                quality_metrics["content_preservation"] = {
                    "score": content_preservation,
                    "label": "Content Preservation",
                    "description": "% of formatted documents with 100% paragraph/word/image/table fidelity",
                    "unit": "%",
                    "detail": {
                        "validated_jobs": total_validation,
                        "preserved_jobs": preserved_count,
                        "unvalidated_completed": max(0, total_completed - total_validation),
                    },
                    "rating": "Excellent" if content_preservation >= 98 else "Good" if content_preservation >= 90 else "Fair" if content_preservation >= 75 else "Poor",
                }

                # 4. PROCESSING EFFICIENCY
                # Composite: avg throughput (pages/sec & words/sec) normalised
                completed_metrics = [m for m in job_metrics if m["status"] == "COMPLETED" and m["duration_seconds"] > 0]
                avg_pages_sec = round(sum(m["pages_per_second"] for m in completed_metrics) / len(completed_metrics), 2) if completed_metrics else 0
                avg_words_sec = round(sum(m["words_per_second"] for m in completed_metrics) / len(completed_metrics), 1) if completed_metrics else 0
                avg_chunks = round(sum(m["total_chunks"] for m in completed_metrics) / len(completed_metrics), 1) if completed_metrics else 0

                # Score: normalise pages/sec on scale 0–5 → 0–100%
                efficiency_score = min(100.0, round(avg_pages_sec * 20, 1)) if avg_pages_sec > 0 else (
                    min(100.0, round(avg_duration * 2, 1)) if avg_duration > 0 else 0.0
                )
                quality_metrics["processing_efficiency"] = {
                    "score": efficiency_score,
                    "label": "Processing Efficiency",
                    "description": "Composite throughput score based on pages/sec and words/sec across completed jobs",
                    "unit": "%",
                    "detail": {
                        "avg_pages_per_second": avg_pages_sec,
                        "avg_words_per_second": avg_words_sec,
                        "avg_processing_seconds": avg_duration,
                        "avg_chunks_per_job": avg_chunks,
                        "completed_jobs_measured": len(completed_metrics),
                    },
                    "rating": "Excellent" if efficiency_score >= 80 else "Good" if efficiency_score >= 50 else "Fair" if efficiency_score >= 25 else "Poor",
                }

                # 5. SCALABILITY
                # How linearly processing time scales with document size
                # Compare small (<50 pages) vs large (≥50 pages) job durations
                small_jobs = [m for m in completed_metrics if m["pages"] > 0 and m["pages"] < 50]
                large_jobs = [m for m in completed_metrics if m["pages"] >= 50]
                avg_small_sec = sum(m["duration_seconds"] for m in small_jobs) / len(small_jobs) if small_jobs else None
                avg_large_sec = sum(m["duration_seconds"] for m in large_jobs) / len(large_jobs) if large_jobs else None

                # Ideal linear scale factor (large docs should be ~proportionally longer)
                if avg_small_sec and avg_large_sec and avg_small_sec > 0:
                    scale_ratio = avg_large_sec / avg_small_sec
                    # If ratio is close to page ratio → linear (good). Score = proximity to 1.0 on log scale.
                    scalability_score = min(100.0, round(max(0.0, 100 - abs(scale_ratio - 2.5) * 15), 1))
                elif len(completed_metrics) >= 2:
                    # Fallback: consistency — low variance in pages/sec is good
                    pps_values = [m["pages_per_second"] for m in completed_metrics if m["pages_per_second"] > 0]
                    if pps_values and len(pps_values) > 1:
                        import statistics
                        cv = statistics.stdev(pps_values) / (statistics.mean(pps_values) or 1)
                        scalability_score = min(100.0, round(max(0.0, 100 - cv * 100), 1))
                    else:
                        scalability_score = 75.0
                else:
                    scalability_score = 0.0  # Not enough data

                quality_metrics["scalability"] = {
                    "score": scalability_score,
                    "label": "Scalability",
                    "description": "How consistently the pipeline performs as document size grows",
                    "unit": "%",
                    "detail": {
                        "small_doc_jobs": len(small_jobs),
                        "large_doc_jobs": len(large_jobs),
                        "avg_small_doc_seconds": round(avg_small_sec, 2) if avg_small_sec else None,
                        "avg_large_doc_seconds": round(avg_large_sec, 2) if avg_large_sec else None,
                        "total_completed": total_completed,
                    },
                    "rating": "Excellent" if scalability_score >= 85 else "Good" if scalability_score >= 65 else "Fair" if scalability_score >= 40 else "Poor" if completed_metrics else "No Data",
                }

            except Exception as e:
                quality_metrics["_error"] = str(e)

            return {
                "summary": {
                    "total_documents": total_docs,
                    "total_pages": total_pages,
                    "total_words": total_words,
                    "total_chapters": total_chapters,
                    "total_jobs": total_jobs,
                    "completed_jobs": total_completed,
                    "failed_jobs": len(failed_jobs),
                    "avg_processing_seconds": avg_duration,
                    "success_rate": round((total_completed / total_jobs) * 100, 1) if total_jobs > 0 else 0,
                },
                "quality_metrics": quality_metrics,
                "job_metrics": job_metrics,
                "block_type_stats": block_type_stats,
                "system_metrics": system_metrics,
                "recent_audit_events": recent_events,
                "storage": global_db.get_storage_stats(),
            }

        except Exception as e:
            import traceback
            raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")

    @app.get("/api/projects/{project_id}/technical-details")
    def get_project_technical_details(project_id: str):
        """
        Returns rich technical details for a single document/project:
        block-type breakdown, ML confidence, structural analysis, processing metrics,
        logo info, and storage info.
        """
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        # Latest job info
        latest_job = None
        job_duration_sec = 0.0
        try:
            with global_db.get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM jobs WHERE project_id = ? ORDER BY updated_at DESC LIMIT 1",
                    (project_id,),
                )
                row = cur.fetchone()
                if row:
                    latest_job = dict(row)
                    try:
                        from datetime import datetime
                        created = latest_job.get("created_at", "")
                        updated = latest_job.get("updated_at", "")
                        if created and updated:
                            t_start = datetime.fromisoformat(created.split("+")[0])
                            t_end = datetime.fromisoformat(updated.split("+")[0])
                            job_duration_sec = max(0.0, (t_end - t_start).total_seconds())
                    except Exception:
                        pass
        except Exception:
            pass

        # Block-type breakdown from document_index
        block_type_breakdown = {}
        total_blocks = 0
        overall_avg_confidence = 0.0
        low_confidence_blocks = 0
        high_confidence_blocks = 0
        try:
            with global_db.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT block_type,
                           COUNT(*) as count,
                           AVG(confidence) as avg_confidence,
                           MIN(confidence) as min_confidence,
                           MAX(confidence) as max_confidence,
                           SUM(word_count) as total_words,
                           SUM(has_images) as image_count,
                           SUM(has_tables) as table_count
                    FROM document_index
                    WHERE document_id = ?
                    GROUP BY block_type
                    ORDER BY count DESC
                    """,
                    (project_id,),
                )
                for row in cursor.fetchall():
                    r = dict(row)
                    bt = r["block_type"]
                    block_type_breakdown[bt] = {
                        "count": r["count"],
                        "avg_confidence": round(float(r["avg_confidence"] or 1.0), 3),
                        "min_confidence": round(float(r["min_confidence"] or 1.0), 3),
                        "max_confidence": round(float(r["max_confidence"] or 1.0), 3),
                        "total_words": r["total_words"] or 0,
                        "image_count": r["image_count"] or 0,
                        "table_count": r["table_count"] or 0,
                    }
                    total_blocks += r["count"]

                # Overall confidence stats
                cursor2 = conn.execute(
                    """
                    SELECT AVG(confidence) as avg_conf,
                           SUM(CASE WHEN confidence < 0.75 THEN 1 ELSE 0 END) as low_conf,
                           SUM(CASE WHEN confidence >= 0.90 THEN 1 ELSE 0 END) as high_conf
                    FROM document_index
                    WHERE document_id = ?
                    """,
                    (project_id,),
                )
                conf_row = cursor2.fetchone()
                if conf_row:
                    cr = dict(conf_row)
                    overall_avg_confidence = round(float(cr.get("avg_conf") or 1.0), 3)
                    low_confidence_blocks = int(cr.get("low_conf") or 0)
                    high_confidence_blocks = int(cr.get("high_conf") or 0)
        except Exception:
            pass

        # Validation report
        validation_report = None
        if latest_job:
            try:
                validation_report = global_db.get_validation_report(latest_job["job_id"])
            except Exception:
                pass

        # Logo asset
        logo_asset = global_db.get_logo_asset(project_id)

        # Storage info
        root_dir = p.get("root_dir", "")
        db_path = os.path.join(root_dir, "database", "project.db")
        source_path = p.get("source_path", "")
        output_path = p.get("output_path", "")

        def get_file_size(path):
            try:
                return os.path.getsize(path) if path and os.path.exists(path) else 0
            except Exception:
                return 0

        def format_bytes(b):
            if b == 0:
                return "0 B"
            for unit in ["B", "KB", "MB", "GB"]:
                if b < 1024:
                    return f"{b:.1f} {unit}"
                b /= 1024
            return f"{b:.1f} TB"

        # Recent corrections for this project
        corrections_count = 0
        try:
            with global_db.get_connection() as conn:
                cur = conn.execute(
                    "SELECT COUNT(*) as cnt FROM corrections WHERE project_id = ?",
                    (project_id,),
                )
                row = cur.fetchone()
                if row:
                    corrections_count = dict(row).get("cnt", 0)
        except Exception:
            pass

        return {
            "project": {
                "id": project_id,
                "name": p.get("name", ""),
                "description": p.get("description", ""),
                "status": p.get("status", "DRAFT"),
                "template_id": p.get("template_id", "book"),
                "source_filename": p.get("source_filename", ""),
                "created_at": p.get("created_at", ""),
                "updated_at": p.get("updated_at", ""),
            },
            "document_metrics": {
                "page_count": p.get("page_count", 0),
                "word_count": p.get("word_count", 0),
                "chapter_count": p.get("chapter_count", 0),
                "total_blocks": total_blocks,
                "overall_avg_confidence": overall_avg_confidence,
                "low_confidence_blocks": low_confidence_blocks,
                "high_confidence_blocks": high_confidence_blocks,
                "human_corrections": corrections_count,
            },
            "block_type_breakdown": block_type_breakdown,
            "processing": {
                "job_id": latest_job.get("job_id") if latest_job else None,
                "status": latest_job.get("status") if latest_job else None,
                "template_id": latest_job.get("template_id") if latest_job else p.get("template_id"),
                "total_chunks": latest_job.get("total_chunks", 0) if latest_job else 0,
                "duration_seconds": round(job_duration_sec, 2),
                "pages_per_second": round(p.get("page_count", 0) / job_duration_sec, 2) if job_duration_sec > 0 else 0,
                "words_per_second": round(p.get("word_count", 0) / job_duration_sec, 1) if job_duration_sec > 0 else 0,
                "started_at": latest_job.get("created_at") if latest_job else None,
                "completed_at": latest_job.get("updated_at") if latest_job else None,
                "errors": json.loads(latest_job.get("errors_json", "[]")) if latest_job else [],
                "warnings": json.loads(latest_job.get("warnings_json", "[]")) if latest_job else [],
            },
            "validation_report": validation_report,
            "logo_asset": {
                "filename": logo_asset.get("filename") if logo_asset else None,
                "dimensions": f"{logo_asset.get('width')}×{logo_asset.get('height')} px" if logo_asset else None,
                "file_size": format_bytes(logo_asset.get("file_size_bytes", 0)) if logo_asset else None,
                "sha256_short": logo_asset.get("sha256", "")[:12] + "..." if logo_asset else None,
                "mime_type": logo_asset.get("mime_type") if logo_asset else None,
                "is_valid": logo_asset.get("is_valid", False) if logo_asset else False,
            } if logo_asset else None,
            "storage": {
                "source_file_size": format_bytes(get_file_size(source_path)),
                "source_file_size_bytes": get_file_size(source_path),
                "db_file_size": format_bytes(get_file_size(db_path)),
                "db_path": db_path if os.path.exists(db_path) else None,
                "output_exists": os.path.exists(output_path) if output_path else False,
            },
        }

    # ------------------ Templates Endpoints ------------------ #

    @app.get("/api/templates")
    def list_templates():
        return [t.model_dump() for t in template_mgr.list_templates()]

    @app.get("/api/templates/{template_id}")
    def get_template(template_id: str):
        return template_mgr.get_template(template_id).model_dump()

    @app.post("/api/templates")
    def save_template(template: BookTemplate):
        template_mgr.save_template(template)
        return template.model_dump()

    @app.post("/api/templates/{template_id}/duplicate")
    def duplicate_template(template_id: str, new_name: str = Query(...), new_id: str = Query(...)):
        new_tpl = template_mgr.duplicate_template(template_id, new_name, new_id)
        return new_tpl.model_dump()

    # ------------------ Synthetic Test Generator ------------------ #

    @app.post("/api/generator/sample")
    def generate_sample_docx(req: GenerateSampleReq):
        out_dir = os.path.join(root_dir, "samples")
        os.makedirs(out_dir, exist_ok=True)
        fname = f"synthetic_{req.pages}_pages.docx"
        out_path = os.path.join(out_dir, fname)

        # Generate sample
        SyntheticDocumentGenerator.create_document(req.pages, out_path)

        # If project_id provided, attach to project source
        if req.project_id:
            p = project_mgr.get_project(req.project_id)
            if p:
                proj_src = os.path.join(p["root_dir"], "source", fname)
                shutil.copyfile(out_path, proj_src)
                db_path = os.path.join(p["root_dir"], "database", "project.db")
                indexer = DocumentIndexer(db_path, db=global_db)
                parser = DocumentParser(proj_src)
                meta = parser.scan_and_index(document_id=req.project_id, indexer=indexer)
                project_mgr.update_project(
                    req.project_id,
                    {
                        "source_filename": fname,
                        "source_path": proj_src,
                        "page_count": meta.estimated_pages,
                        "word_count": meta.total_words,
                        "chapter_count": meta.total_chapters,
                        "status": "ANALYZED",
                    },
                )

        return {
            "success": True,
            "pages": req.pages,
            "output_path": out_path,
        }

    return app


# Default instance for uvicorn
app = create_app()
