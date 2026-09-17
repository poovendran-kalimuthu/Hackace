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
        indexer = DocumentIndexer(db_path)
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

    @app.get("/api/projects/{project_id}/export")
    def export_project_docx(project_id: str):
        """Streams the publication-ready formatted DOCX file for local download."""
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        proj_dir = project_mgr.get_project_dir(project_id)
        out_dir = os.path.join(proj_dir, "output")
        source_name = p.get("source_filename") or p.get("name", "manuscript")
        base_source = os.path.splitext(source_name)[0]
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in base_source).strip() or "manuscript"
        download_filename = f"{safe_name}_formatted.docx"

        out_file = os.path.join(out_dir, f"{p.get('name', 'manuscript')}_formatted.docx")
        if not os.path.exists(out_file):
            docx_candidates = [f for f in os.listdir(out_dir) if f.endswith(".docx")] if os.path.exists(out_dir) else []
            if docx_candidates:
                out_file = os.path.join(out_dir, docx_candidates[0])
            else:
                raise HTTPException(
                    status_code=404,
                    detail="Formatted publication DOCX not found. Please complete the formatting job first."
                )

        global_db.log_audit_event(project_id, "DOCX_EXPORTED", {"filename": os.path.basename(out_file)})
        return FileResponse(
            path=out_file,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=download_filename,
        )

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
        if not os.path.exists(db_path):
            return []

        indexer = DocumentIndexer(db_path)
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
        indexer = DocumentIndexer(db_path)

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
        if not os.path.exists(db_path):
            raise HTTPException(status_code=400, detail="Document not indexed yet.")

        indexer = DocumentIndexer(db_path)
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
        if os.path.exists(db_path):
            indexer = DocumentIndexer(db_path)
            return {"chapters": indexer.get_chapters(project_id)}

        return {}

    @app.get("/api/projects/{project_id}/search")
    def search_document(project_id: str, q: str = Query(...), limit: int = 50):
        p = project_mgr.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        db_path = os.path.join(p["root_dir"], "database", "project.db")
        if not os.path.exists(db_path):
            return []

        indexer = DocumentIndexer(db_path)
        return indexer.search(project_id, q, limit=limit)

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
                indexer = DocumentIndexer(db_path)
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

    # ------------------ WebSocket Live Telemetry ------------------ #

    @app.websocket("/ws/telemetry")
    async def websocket_telemetry(websocket: WebSocket):
        await websocket.accept()
        active_connections.append(websocket)
        try:
            while True:
                # Keep connection alive & respond to client ping
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
        except WebSocketDisconnect:
            if websocket in active_connections:
                active_connections.remove(websocket)

    return app


# Default instance for uvicorn
app = create_app()
