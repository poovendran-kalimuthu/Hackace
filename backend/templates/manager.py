"""
Template Lifecycle & Preset Manager.

Loads built-in publication presets (Book Publisher, Academic Research Paper, Conference Paper)
and coordinates custom templates with JSON validation and persistence.
"""

from __future__ import annotations
import json
import os
import shutil
from typing import Dict, List, Optional
from datetime import datetime

from .schema import BookTemplate


class TemplateManager:
    """
    Handles template storage, validation, duplication, and import/export.
    """

    def __init__(self, custom_templates_dir: Optional[str] = None):
        self.root_templates_dir = os.path.join(os.getcwd(), "templates")
        self.defaults_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "defaults")
        self.custom_dir = custom_templates_dir or os.path.join(os.getcwd(), "custom_templates")
        os.makedirs(self.custom_dir, exist_ok=True)
        self._cache: Dict[str, BookTemplate] = {}
        self.refresh()

    def refresh(self) -> None:
        """Scan reference template directories and custom template directories."""
        self._cache.clear()

        # 1. Load built-ins from templates/ or defaults/
        for directory in (self.root_templates_dir, self.defaults_dir):
            if os.path.exists(directory):
                for fname in sorted(os.listdir(directory)):
                    if fname.endswith(".json") and fname != "schema.json":
                        fpath = os.path.join(directory, fname)
                        try:
                            with open(fpath, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                if "id" not in data:
                                    data["id"] = data.get("document_type") or os.path.splitext(fname)[0]
                                tpl = BookTemplate.model_validate(data)
                                tpl.is_builtin = True
                                if tpl.id not in self._cache:
                                    self._cache[tpl.id] = tpl
                        except Exception:
                            pass

        # 2. Load custom user templates
        if os.path.exists(self.custom_dir):
            for fname in sorted(os.listdir(self.custom_dir)):
                if fname.endswith(".json"):
                    fpath = os.path.join(self.custom_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if "id" not in data:
                                data["id"] = data.get("document_type") or os.path.splitext(fname)[0]
                            tpl = BookTemplate.model_validate(data)
                            tpl.is_builtin = False
                            self._cache[tpl.id] = tpl
                    except Exception:
                        pass

    def list_templates(self) -> List[BookTemplate]:
        return list(self._cache.values())

    def get_template(self, template_id: str) -> BookTemplate:
        tid = (template_id or "").lower().strip()
        if tid in self._cache:
            return self._cache[tid]

        # Support aliases for academic research paper
        if tid in ("journal", "academic", "academic_report", "academic_research", "academic_paper", "academic research paper", "academic report"):
            for k in ("academic", "academic_report", "academic_research", "journal"):
                if k in self._cache:
                    return self._cache[k]

        # Support aliases for conference paper
        if tid in ("technical", "conference", "conference_paper", "conference paper"):
            for k in ("conference_paper", "conference", "technical"):
                if k in self._cache:
                    return self._cache[k]

        if "book" in self._cache:
            return self._cache["book"]
        if self._cache:
            return next(iter(self._cache.values()))
        return BookTemplate(id="book", name="Book Publisher", profile_name="Book Publisher", document_type="book")

    def save_template(self, template: BookTemplate) -> str:
        """Saves custom template to custom_templates folder."""
        template.updated_at = datetime.utcnow().isoformat()
        if not template.created_at:
            template.created_at = template.updated_at
        template.is_builtin = False

        file_path = os.path.join(self.custom_dir, f"{template.id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(template.model_dump_json(indent=2))

        self._cache[template.id] = template
        return file_path

    def duplicate_template(self, template_id: str, new_name: str, new_id: str) -> BookTemplate:
        original = self.get_template(template_id)
        dup_data = original.model_dump()
        dup_data["id"] = new_id
        dup_data["name"] = new_name
        dup_data["profile_name"] = new_name
        dup_data["is_builtin"] = False
        dup_data["created_at"] = datetime.utcnow().isoformat()
        dup_data["updated_at"] = dup_data["created_at"]

        new_tpl = BookTemplate.model_validate(dup_data)
        self.save_template(new_tpl)
        return new_tpl

    def export_template(self, template_id: str, dest_path: str) -> str:
        tpl = self.get_template(template_id)
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(tpl.model_dump_json(indent=2))
        return dest_path

    def import_template(self, src_path: str) -> BookTemplate:
        with open(src_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tpl = BookTemplate.model_validate(data)
        self.save_template(tpl)
        return tpl
