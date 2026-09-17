"""
Integration Tests for FastAPI Backend Endpoints.
Verifies project lifecycle, mandatory logo validation, 3 templates, job execution, and comparison.
"""

import io
import pytest
from PIL import Image
from starlette.testclient import TestClient
from backend.api.server import create_app


def create_test_image(format="PNG", size=(300, 200)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=(0, 120, 215))
    img.save(buf, format=format)
    return buf.getvalue()


@pytest.fixture
def client(tmp_path):
    workspace = str(tmp_path / "api_workspace")
    app = create_app(workspace_root=workspace)
    return TestClient(app)


def test_health_and_diagnostics(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ONLINE"

    res = client.get("/api/diagnostics")
    assert res.status_code == 200
    assert "cpu_percent" in res.json()
    assert "ram_used_gb" in res.json()


def test_three_templates_endpoints(client):
    res = client.get("/api/templates")
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) == 3
    t_ids = [t["id"] for t in templates]
    assert "book" in t_ids
    assert any(x in t_ids for x in ("academic_research", "journal", "academic"))
    assert any(x in t_ids for x in ("conference_paper", "technical", "conference"))


def test_project_lifecycle_mandatory_logo_and_formatting(client):
    # 1. Create project
    create_res = client.post(
        "/api/projects",
        json={"name": "API Test Project", "description": "Test description", "template_id": "book"},
    )
    assert create_res.status_code == 200
    proj = create_res.json()
    proj_id = proj["id"]

    # 2. List projects
    list_res = client.get("/api/projects")
    assert list_res.status_code == 200
    assert any(p["id"] == proj_id for p in list_res.json())

    # 3. Generate synthetic sample document inside project
    gen_res = client.post(
        "/api/generator/sample",
        json={"pages": 5, "project_id": proj_id},
    )
    assert gen_res.status_code == 200
    assert gen_res.json()["success"]

    # 4. Check updated project stats
    p_res = client.get(f"/api/projects/{proj_id}")
    assert p_res.status_code == 200
    updated_p = p_res.json()
    assert updated_p["page_count"] > 0
    assert updated_p["word_count"] > 0

    # 5. Enforce Section 5: Starting job without logo MUST fail
    failed_job_res = client.post(
        f"/api/projects/{proj_id}/jobs",
        json={"template_id": "book"},
    )
    assert failed_job_res.status_code == 400
    assert "mandatory" in failed_job_res.json()["detail"].lower()

    # 6. Upload valid publisher logo
    logo_bytes = create_test_image(format="PNG", size=(350, 250))
    upload_logo_res = client.post(
        f"/api/projects/{proj_id}/logo",
        files={"file": ("publisher_logo.png", logo_bytes, "image/png")},
    )
    assert upload_logo_res.status_code == 200
    assert upload_logo_res.json()["success"] is True

    # Check logo status
    logo_status_res = client.get(f"/api/projects/{proj_id}/logo")
    assert logo_status_res.status_code == 200
    assert logo_status_res.json()["has_logo"] is True

    # 7. Start Formatting Job with valid logo now succeeds
    job_res = client.post(
        f"/api/projects/{proj_id}/jobs",
        json={"template_id": "book"},
    )
    assert job_res.status_code == 200
    job_id = job_res.json()["job_id"]

    # 8. Check Job Status
    status_res = client.get(f"/api/jobs/{job_id}")
    assert status_res.status_code == 200
    assert status_res.json()["job_id"] == job_id

    # 9. Check Search
    search_res = client.get(f"/api/projects/{proj_id}/search?q=Quantum")
    assert search_res.status_code == 200
    assert isinstance(search_res.json(), list)

    # 10. Check Page Preview
    prev_res = client.get(f"/api/projects/{proj_id}/preview/page/1")
    assert prev_res.status_code == 200
    assert prev_res.json()["page_number"] == 1
    assert "blocks" in prev_res.json()

    # 11. Check Comparison Endpoint
    comp_res = client.get(f"/api/projects/{proj_id}/comparison")
    assert comp_res.status_code == 200
    assert comp_res.json()["project_id"] == proj_id
    assert comp_res.json()["logo_asset"] is not None
