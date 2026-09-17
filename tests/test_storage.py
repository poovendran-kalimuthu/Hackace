"""
Unit and Integration Tests for MySQL and Resilient SQLite Storage Layer.
Verifies MySQL operations, parameter translation (? -> %s), job lifecycle,
checkpoints, logo assets, validation reports, and offline SQLite fallback.
"""

import os
import pytest
from backend.storage.database import Database


def test_database_engine_info():
    db = Database()
    info = db.get_engine_info()
    assert "engine" in info
    assert "connected" in info
    assert info["connected"] is True
    # If MySQL is running locally, engine should be MySQL
    assert info["engine"] in ("MySQL", "SQLite")


def test_connection_wrapper_execution():
    db = Database()
    with db.get_connection() as conn:
        cursor = conn.execute("SELECT 1 AS col_test")
        row = cursor.fetchone()
        assert dict(row)["col_test"] == 1


def test_job_crud_lifecycle():
    db = Database()
    job_id = "test_job_mysql_crud_101"
    project_id = "test_proj_mysql_crud_101"

    # 1. Create Job
    job_payload = {
        "job_id": job_id,
        "project_id": project_id,
        "status": "QUEUED",
        "progress": 0.0,
        "current_stage": "QUEUED",
        "current_chunk": 0,
        "total_chunks": 5,
        "errors": [],
        "warnings": ["initial warning"],
    }
    db.create_or_update_job(job_payload)

    fetched = db.get_job(job_id)
    assert fetched is not None
    assert fetched["status"] == "QUEUED"
    assert fetched["warnings"] == ["initial warning"]

    # 2. Update Job
    job_payload["status"] = "COMPLETED"
    job_payload["progress"] = 100.0
    job_payload["output_file"] = "/output/result.docx"
    db.create_or_update_job(job_payload)

    updated = db.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "COMPLETED"
    assert updated["progress"] == 100.0
    assert updated["output_file"] == "/output/result.docx"

    # 3. Checkpoints
    db.save_checkpoint(job_id, "chunk_0", "ANALYZING", "COMPLETED", {"entities": 12})
    cps = db.get_checkpoints(job_id)
    assert any(c["chunk_id"] == "chunk_0" for c in cps)

    # 4. Corrections
    db.record_correction(
        project_id=project_id,
        block_id="block_123",
        original_text="Chapter 1: The Beginning",
        predicted_type="BODY",
        corrected_type="CHAPTER_TITLE",
        confidence=0.88,
        features={"is_heading": True},
    )
    corrections = db.get_corrections(project_id)
    assert len(corrections) >= 1
    assert corrections[0]["predicted_type"] == "BODY"
    assert corrections[0]["corrected_type"] == "CHAPTER_TITLE"

    # Cleanup
    with db.get_connection() as conn:
        conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM job_checkpoints WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM corrections WHERE project_id = ?", (project_id,))


def test_logo_asset_and_validation_storage():
    db = Database()
    project_id = "test_proj_mysql_logo_202"

    # Test Logo Metadata
    db.save_logo_asset(
        project_id=project_id,
        logo_data={
            "filename": "publisher_logo.png",
            "file_path": "/workspace/proj/assets/logo/publisher_logo.png",
            "sha256": "abc123hash",
            "mime_type": "image/png",
            "width": 800,
            "height": 400,
            "file_size": 45000,
            "is_valid": True,
            "validation_message": "Verified",
        },
    )

    logo = db.get_logo_asset(project_id)
    assert logo is not None
    assert logo["filename"] == "publisher_logo.png"
    assert logo["width"] == 800
    assert logo["height"] == 400

    # Test Validation Report Storage
    db.save_validation_report(
        job_id="job_val_mysql_1",
        project_id=project_id,
        pre_metrics={"words": 5000, "paragraphs": 120},
        post_metrics={"words": 5000, "paragraphs": 120},
        is_preserved=True,
        discrepancies=[],
    )

    report = db.get_validation_report("job_val_mysql_1")
    assert report is not None
    assert report["is_preserved"] is True
    assert report["pre_metrics"]["words"] == 5000
    assert report["post_metrics"]["words"] == 5000

    # Test Delete Logo
    db.delete_logo_asset(project_id)
    assert db.get_logo_asset(project_id) is None

    # Cleanup report
    with db.get_connection() as conn:
        conn.execute("DELETE FROM validation_reports WHERE job_id = ?", ("job_val_mysql_1",))


def test_sqlite_fallback_mode(tmp_path):
    """Explicitly verifies offline SQLite fallback when db_type='sqlite'."""
    sqlite_db_file = str(tmp_path / "offline_fallback.db")
    db = Database(db_path=sqlite_db_file, db_type="sqlite")
    assert db.using_mysql is False
    assert db.get_engine_info()["engine"] == "SQLite"
    assert os.path.exists(sqlite_db_file)

    job_id = "test_sqlite_fallback_job"
    db.create_or_update_job({"job_id": job_id, "status": "QUEUED"})
    j = db.get_job(job_id)
    assert j is not None
    assert j["status"] == "QUEUED"
