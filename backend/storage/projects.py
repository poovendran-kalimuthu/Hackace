"""
Project Workspace Manager.

Manages commercial desktop project directories, project metadata, SQLite project databases,
lifecycle actions, and local backup/restore archives.
"""

from __future__ import annotations
import json
import os
import shutil
import uuid
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .database import Database


class ProjectRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    source_filename: str = ""
    source_path: str = ""
    output_path: str = ""
    template_id: str = "book"
    page_count: int = 0
    word_count: int = 0
    chapter_count: int = 0
    status: str = "DRAFT"  # DRAFT, ANALYZING, FORMATTED, EXPORTED
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    root_dir: str = ""


class ProjectManager:
    """
    Orchestrates filesystem workspaces and project-level databases.
    """

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        os.makedirs(self.workspace_root, exist_ok=True)
        self.global_db_path = os.path.join(self.workspace_root, "platform_meta.db")
        self.global_db = Database(self.global_db_path)

    def create_project(
        self,
        name: str,
        description: str = "",
        template_id: str = "book",
    ) -> ProjectRecord:
        """Initializes standard project directory structure and SQLite store."""
        proj_id = str(uuid.uuid4())[:8]
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name).strip()
        proj_folder_name = f"{safe_name}_{proj_id}"
        proj_dir = os.path.join(self.workspace_root, proj_folder_name)

        # Standard subdirectories per specification Section 9 & 39
        for sub in ("source", "database", "chunks", "analysis", "cache", "previews", "templates", "output", "logs", os.path.join("assets", "logo")):
            os.makedirs(os.path.join(proj_dir, sub), exist_ok=True)

        record = ProjectRecord(
            id=proj_id,
            name=name,
            description=description,
            template_id=template_id,
            root_dir=proj_dir,
        )

        # Save in global DB
        with self.global_db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    id, name, description, source_filename, source_path,
                    output_path, template_id, page_count, word_count,
                    chapter_count, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.name,
                    record.description,
                    record.source_filename,
                    record.source_path,
                    record.output_path,
                    record.template_id,
                    record.page_count,
                    record.word_count,
                    record.chapter_count,
                    record.status,
                    record.created_at,
                    record.updated_at,
                ),
            )

        # Save metadata manifest inside project directory
        manifest_path = os.path.join(proj_dir, "project_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(record.model_dump_json(indent=2))

        return record

    def list_projects(self) -> List[Dict[str, Any]]:
        with self.global_db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC")
            projects: List[Dict[str, Any]] = []
            for row in cursor.fetchall():
                p = dict(row)
                p["root_dir"] = self.get_project_dir(p["id"])
                projects.append(p)
            return projects

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self.global_db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            if not row:
                return None
            p = dict(row)
            p["root_dir"] = self.get_project_dir(project_id)
            return p

    def get_project_dir(self, project_id: str) -> str:
        # Locate project directory by prefix or manifest
        for item in os.listdir(self.workspace_root):
            full_path = os.path.join(self.workspace_root, item)
            if os.path.isdir(full_path):
                manifest = os.path.join(full_path, "project_manifest.json")
                if os.path.exists(manifest):
                    try:
                        with open(manifest, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if data.get("id") == project_id:
                                return full_path
                    except Exception:
                        pass
                if item.endswith(f"_{project_id}"):
                    return full_path
        return os.path.join(self.workspace_root, f"project_{project_id}")

    def update_project(self, project_id: str, updates: Dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        updates["updated_at"] = now
        set_clauses = [f"{k} = ?" for k in updates.keys() if k != "id"]
        values = [updates[k] for k in updates.keys() if k != "id"]
        values.append(project_id)

        with self.global_db.get_connection() as conn:
            conn.execute(
                f"UPDATE projects SET {', '.join(set_clauses)} WHERE id = ?",
                values,
            )

        proj_dir = self.get_project_dir(project_id)
        manifest_path = os.path.join(proj_dir, "project_manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.update(updates)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def duplicate_project(self, project_id: str, new_name: str) -> ProjectRecord:
        src = self.get_project(project_id)
        if not src:
            raise ValueError(f"Project not found: {project_id}")
        new_proj = self.create_project(
            name=new_name,
            description=src.get("description", "") + " (Copy)",
            template_id=src.get("template_id", "book"),
        )
        src_dir = self.get_project_dir(project_id)
        dst_dir = new_proj.root_dir

        # Copy source manuscript and templates
        for sub in ("source", "templates", "analysis"):
            s = os.path.join(src_dir, sub)
            d = os.path.join(dst_dir, sub)
            if os.path.exists(s):
                shutil.copytree(s, d, dirs_exist_ok=True)

        return new_proj

    def delete_project(self, project_id: str) -> bool:
        proj_dir = self.get_project_dir(project_id)
        if os.path.exists(proj_dir):
            shutil.rmtree(proj_dir, ignore_errors=True)
        with self.global_db.get_connection() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        return True

    def backup_project(self, project_id: str, backup_zip_path: str) -> str:
        """Create a portable zip backup excluding temporary chunks/caches."""
        proj_dir = self.get_project_dir(project_id)
        if not os.path.exists(proj_dir):
            raise FileNotFoundError(f"Project directory not found: {proj_dir}")

        os.makedirs(os.path.dirname(os.path.abspath(backup_zip_path)), exist_ok=True)
        with zipfile.ZipFile(backup_zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(proj_dir):
                # Exclude transient cache to keep backup compact
                if "cache" in root or "chunks" in root:
                    continue
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, proj_dir)
                    z.write(full_path, arcname=rel_path)
        return backup_zip_path

    def restore_backup(self, backup_zip_path: str, new_name: Optional[str] = None) -> ProjectRecord:
        """Restore project from zip archive."""
        if not os.path.exists(backup_zip_path):
            raise FileNotFoundError(f"Backup archive not found: {backup_zip_path}")

        temp_extract = os.path.join(self.workspace_root, f"restore_{uuid.uuid4().hex[:6]}")
        with zipfile.ZipFile(backup_zip_path, "r") as z:
            z.extractall(temp_extract)

        manifest_file = os.path.join(temp_extract, "project_manifest.json")
        name = new_name or "Restored Project"
        template_id = "classic_novel"
        desc = ""
        if os.path.exists(manifest_file):
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    name = new_name or data.get("name", name)
                    template_id = data.get("template_id", template_id)
                    desc = data.get("description", desc)
            except Exception:
                pass

        proj = self.create_project(name=name, description=desc, template_id=template_id)
        shutil.copytree(temp_extract, proj.root_dir, dirs_exist_ok=True)
        shutil.rmtree(temp_extract, ignore_errors=True)
        return proj
