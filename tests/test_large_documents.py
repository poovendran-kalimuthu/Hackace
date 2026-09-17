"""
Integration Test for End-to-End Pipeline on Large Document Benchmarks.
"""

import os
import time
import pytest

from backend.generator.synthetic_docs import SyntheticDocumentGenerator
from backend.jobs.manager import JobManager
from backend.jobs.workers import DualExecutorPool
from backend.storage.database import Database
from backend.storage.projects import ProjectManager
from backend.templates.manager import TemplateManager


def test_end_to_end_job_pipeline(tmp_path):
    workspace = str(tmp_path / "workspace")
    proj_mgr = ProjectManager(workspace)
    tpl_mgr = TemplateManager()
    db = proj_mgr.global_db
    pool = DualExecutorPool(io_workers=2, cpu_workers=2)
    job_mgr = JobManager(db, pool, tpl_mgr)

    # 1. Create Project
    proj = proj_mgr.create_project(name="Pipeline Benchmark Project")

    # 2. Generate benchmark manuscript (20 pages)
    doc_path = os.path.join(proj.root_dir, "source", "benchmark.docx")
    SyntheticDocumentGenerator.create_document(target_pages=20, output_path=doc_path)
    assert os.path.exists(doc_path)

    # 3. Launch pipeline job
    job_id = job_mgr.start_pipeline_job(
        project_id=proj.id,
        input_docx=doc_path,
        project_dir=proj.root_dir,
        template_id="classic_novel",
    )
    assert job_id.startswith("job_")

    # 4. Wait for job completion
    max_wait = 30
    start_time = time.time()
    final_status = None

    while time.time() - start_time < max_wait:
        status = job_mgr.get_job_status(job_id)
        if status and status["status"] in ("COMPLETED", "FAILED"):
            final_status = status
            break
        time.sleep(0.5)

    pool.shutdown(wait=False)

    assert final_status is not None, "Pipeline timed out"
    assert final_status["status"] == "COMPLETED", f"Pipeline failed: {final_status.get('errors')}"
    assert os.path.exists(final_status["output_file"])
    assert os.path.getsize(final_status["output_file"]) > 5000
