"""
Unit and Security Tests for Publisher Logo Validation (Section 5).
Verifies strict magic byte validation, dimensions, size limits, and path traversal security.
"""

import io
import os
import pytest
from PIL import Image
from backend.security.logo_validator import LogoValidator, LogoValidationResult


def create_test_image(format="PNG", size=(300, 200), color=(0, 120, 215)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


def test_valid_png_logo(tmp_path):
    target_dir = str(tmp_path / "logo_dir")
    png_bytes = create_test_image(format="PNG", size=(400, 300))

    result = LogoValidator.validate_and_save(
        raw_bytes=png_bytes,
        original_filename="publisher_brand.png",
        project_assets_logo_dir=target_dir,
    )

    assert result.is_valid is True
    assert result.mime_type == "image/png"
    assert result.width == 400
    assert result.height == 300
    assert result.sanitized_filename == "publisher_brand.png"
    assert os.path.exists(result.normalized_path)
    assert len(result.sha256_hash) == 64


def test_valid_jpeg_logo(tmp_path):
    target_dir = str(tmp_path / "logo_dir")
    jpeg_bytes = create_test_image(format="JPEG", size=(500, 500))

    result = LogoValidator.validate_and_save(
        raw_bytes=jpeg_bytes,
        original_filename="book_cover_logo.jpg",
        project_assets_logo_dir=target_dir,
    )

    assert result.is_valid is True
    assert result.mime_type == "image/jpeg"
    assert result.width == 500
    assert result.height == 500
    assert os.path.exists(result.normalized_path)


def test_reject_empty_file(tmp_path):
    target_dir = str(tmp_path / "logo_dir")
    result = LogoValidator.validate_and_save(
        raw_bytes=b"",
        original_filename="logo.png",
        project_assets_logo_dir=target_dir,
    )
    assert result.is_valid is False
    assert "empty" in result.error_message.lower()


def test_reject_oversized_file(tmp_path):
    target_dir = str(tmp_path / "logo_dir")
    oversized_bytes = b"0" * (6 * 1024 * 1024)  # 6MB (max is 5MB)
    result = LogoValidator.validate_and_save(
        raw_bytes=oversized_bytes,
        original_filename="giant_logo.png",
        project_assets_logo_dir=target_dir,
    )
    assert result.is_valid is False
    assert "exceeds maximum" in result.error_message.lower()


def test_reject_unsupported_extension(tmp_path):
    target_dir = str(tmp_path / "logo_dir")
    result = LogoValidator.validate_and_save(
        raw_bytes=b"sample content",
        original_filename="malicious.exe",
        project_assets_logo_dir=target_dir,
    )
    assert result.is_valid is False
    assert "unsupported" in result.error_message.lower()


def test_reject_spoofed_mime_type(tmp_path):
    """Text file disguised as .png must be rejected by magic bytes."""
    target_dir = str(tmp_path / "logo_dir")
    fake_png_bytes = b"Hello, this is just plain text masquerading as PNG."
    result = LogoValidator.validate_and_save(
        raw_bytes=fake_png_bytes,
        original_filename="fake_image.png",
        project_assets_logo_dir=target_dir,
    )
    assert result.is_valid is False
    assert "signature" in result.error_message.lower() or "header" in result.error_message.lower()


def test_reject_too_small_dimensions(tmp_path):
    """Image below minimum dimensions (100x100) must be rejected."""
    target_dir = str(tmp_path / "logo_dir")
    small_bytes = create_test_image(format="PNG", size=(64, 64))
    result = LogoValidator.validate_and_save(
        raw_bytes=small_bytes,
        original_filename="tiny_logo.png",
        project_assets_logo_dir=target_dir,
    )
    assert result.is_valid is False
    assert "dimension" in result.error_message.lower() or "minimum" in result.error_message.lower()


def test_path_traversal_sanitization(tmp_path):
    """Attacking filename with ../../ must be safely sanitized."""
    target_dir = str(tmp_path / "logo_dir")
    png_bytes = create_test_image(format="PNG", size=(200, 200))

    result = LogoValidator.validate_and_save(
        raw_bytes=png_bytes,
        original_filename="../../../etc/evil_logo.png",
        project_assets_logo_dir=target_dir,
    )

    assert result.is_valid is True
    assert "evil_logo.png" in result.sanitized_filename
    assert "../" not in result.normalized_path
    assert result.normalized_path.startswith(os.path.abspath(target_dir))
