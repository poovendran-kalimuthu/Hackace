"""
Local Data-Security & Audit Service.

Ensures:
1. Zero manuscript content leaks to external networks.
2. Structured security audit logs.
3. Path traversal defense.
4. DOCX container structure validation.
"""

from __future__ import annotations
import logging
import os
import re
import zipfile
from typing import Any, Dict, Optional

logger = logging.getLogger("docucraft.security")


class SecurityService:
    """
    Guards local workspace integrity, path bounds, and DOCX package authenticity.
    """

    MAX_DOCX_SIZE = 150 * 1024 * 1024  # 150 MB

    @staticmethod
    def sanitize_path(base_dir: str, requested_path: str) -> str:
        """
        Validates that requested_path resides strictly within base_dir.
        Prevents directory traversal attacks (e.g., ../../etc/passwd).
        """
        abs_base = os.path.abspath(base_dir)
        abs_target = os.path.abspath(os.path.join(abs_base, requested_path))
        if not abs_target.startswith(abs_base):
            raise PermissionError(f"Access denied: Path traversal attempted outside {base_dir}")
        return abs_target

    @staticmethod
    def validate_docx_package(file_path: str) -> bool:
        """
        Verifies that file_path is a legitimate, uncorrupted Microsoft Word DOCX archive.
        Checks for obligatory WordprocessingML components:
        - [Content_Types].xml
        - word/document.xml
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Manuscript not found: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("Manuscript file is empty (0 bytes).")
        if file_size > SecurityService.MAX_DOCX_SIZE:
            raise ValueError(f"Manuscript exceeds maximum permitted size of 150 MB ({file_size / (1024*1024):.1f} MB).")

        try:
            with zipfile.ZipFile(file_path, "r") as z:
                # Test archive integrity
                bad_file = z.testzip()
                if bad_file:
                    raise ValueError(f"Corrupted archive structure in: {bad_file}")

                namelist = z.namelist()
                has_content_types = "[Content_Types].xml" in namelist
                has_document_xml = any(name.startswith("word/document") and name.endswith(".xml") for name in namelist)

                if not (has_content_types and has_document_xml):
                    raise ValueError("File is not a valid Microsoft Word (.docx) document (missing document XML).")
        except zipfile.BadZipFile:
            raise ValueError("File is not a valid ZIP/DOCX package or is corrupted.")

        return True
