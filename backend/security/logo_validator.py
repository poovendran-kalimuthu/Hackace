"""
Publisher & Book Logo Validator.

Enforces Section 5 strict logo requirements:
- Supported types: PNG, JPG, JPEG
- Magic byte file signature validation (prevents renamed malicious files)
- Dimension checks (min 100x100, max 4000x4000)
- File size check (max 5 MB, reject empty)
- Filename sanitization & path traversal defense
- SHA-256 calculation
- Normalized project asset storage
"""

from __future__ import annotations
import hashlib
import io
import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple
from PIL import Image


@dataclass
class LogoValidationResult:
    is_valid: bool
    error_message: str = ""
    mime_type: str = ""
    width: int = 0
    height: int = 0
    file_size_bytes: int = 0
    sha256_hash: str = ""
    sanitized_filename: str = ""
    normalized_path: str = ""


class LogoValidator:
    """
    Validates publisher / book logo assets against strict publication specifications.
    """

    ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    MIN_WIDTH = 100
    MIN_HEIGHT = 100
    MAX_WIDTH = 4000
    MAX_HEIGHT = 4000

    # Magic byte signatures for true MIME validation
    MAGIC_SIGNATURES = {
        b"\x89PNG\r\n\x1a\n": "image/png",
        b"\xff\xd8\xff": "image/jpeg",
    }

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitizes filename and strips path traversal attempts."""
        basename = os.path.basename(filename)
        clean = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", basename)
        return clean or "publisher_logo.png"

    @classmethod
    def detect_mime_by_signature(cls, data: bytes) -> Optional[str]:
        """Validates real file header magic bytes."""
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        return None

    @classmethod
    def validate_and_save(
        cls,
        raw_bytes: bytes,
        original_filename: str,
        project_assets_logo_dir: str,
    ) -> LogoValidationResult:
        """
        Executes end-to-end validation and writes a normalized copy into the project workspace.
        """
        file_size = len(raw_bytes)

        # 1. Empty check
        if file_size == 0:
            return LogoValidationResult(
                is_valid=False,
                error_message="Uploaded logo file is empty (0 bytes).",
            )

        # 2. Maximum file size check
        if file_size > cls.MAX_FILE_SIZE:
            return LogoValidationResult(
                is_valid=False,
                error_message=f"Logo file exceeds maximum size of 5 MB ({file_size / (1024*1024):.1f} MB).",
                file_size_bytes=file_size,
            )

        # 3. Extension check
        ext = os.path.splitext(original_filename.lower())[1]
        if ext not in cls.ALLOWED_EXTENSIONS:
            return LogoValidationResult(
                is_valid=False,
                error_message=f"Unsupported file extension '{ext}'. Only PNG, JPG, and JPEG are allowed.",
                file_size_bytes=file_size,
            )

        # 4. File signature / Magic byte verification
        detected_mime = cls.detect_mime_by_signature(raw_bytes)
        if not detected_mime:
            return LogoValidationResult(
                is_valid=False,
                error_message="File header signature does not match a valid PNG or JPEG image.",
                file_size_bytes=file_size,
            )

        # 5. Image integrity & dimension checks via Pillow
        try:
            with Image.open(io.BytesIO(raw_bytes)) as img:
                img.verify()  # Detect corruption

            # Reopen for metadata inspection
            with Image.open(io.BytesIO(raw_bytes)) as img:
                width, height = img.size
                format_name = img.format

            if format_name not in ("PNG", "JPEG"):
                return LogoValidationResult(
                    is_valid=False,
                    error_message=f"Corrupted or unsupported image encoding ({format_name}).",
                    file_size_bytes=file_size,
                )

            if width < cls.MIN_WIDTH or height < cls.MIN_HEIGHT:
                return LogoValidationResult(
                    is_valid=False,
                    error_message=f"Logo resolution {width}x{height} is too low. Minimum required is {cls.MIN_WIDTH}x{cls.MIN_HEIGHT}px.",
                    width=width,
                    height=height,
                    file_size_bytes=file_size,
                )

            if width > cls.MAX_WIDTH or height > cls.MAX_HEIGHT:
                return LogoValidationResult(
                    is_valid=False,
                    error_message=f"Logo resolution {width}x{height} exceeds safe publication limits ({cls.MAX_WIDTH}x{cls.MAX_HEIGHT}px).",
                    width=width,
                    height=height,
                    file_size_bytes=file_size,
                )

        except Exception as e:
            return LogoValidationResult(
                is_valid=False,
                error_message=f"Corrupted image file: {str(e)}",
                file_size_bytes=file_size,
            )

        # 6. Compute SHA-256 Hash
        sha256 = hashlib.sha256(raw_bytes).hexdigest()

        # 7. Write normalized copy to project assets/logo directory
        os.makedirs(project_assets_logo_dir, exist_ok=True)
        sanitized = cls.sanitize_filename(original_filename)
        normalized_name = f"publisher_logo{ext}"
        target_path = os.path.join(project_assets_logo_dir, normalized_name)

        # Ensure single logo rule: remove any previous logos
        for existing in os.listdir(project_assets_logo_dir):
            try:
                os.remove(os.path.join(project_assets_logo_dir, existing))
            except Exception:
                pass

        with open(target_path, "wb") as f:
            f.write(raw_bytes)

        return LogoValidationResult(
            is_valid=True,
            error_message="",
            mime_type=detected_mime,
            width=width,
            height=height,
            file_size_bytes=file_size,
            sha256_hash=sha256,
            sanitized_filename=sanitized,
            normalized_path=target_path,
        )
