"""
Production-grade upload validation (single source of truth).

Checks: extension, MIME, size, emptiness, PDF encryption/corruption,
path traversal. Callers must not re-implement these rules.
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from src.config import get_settings
from src.errors.exceptions import UploadError

PDF_MAGIC = b"%PDF"

# Declared Content-Type values accepted per extension (case-insensitive).
ALLOWED_MIME_BY_EXTENSION: dict[str, frozenset[str]] = {
    ".pdf": frozenset({"application/pdf"}),
    ".txt": frozenset(
        {
            "text/plain",
            "text/csv",
            "application/octet-stream",  # browsers sometimes omit text/plain
        }
    ),
}

# Magic / sniffed types that must match the extension.
SNIFFED_MIME_BY_EXTENSION: dict[str, frozenset[str]] = {
    ".pdf": frozenset({"application/pdf"}),
    ".txt": frozenset({"text/plain"}),
}


class UploadValidationError(UploadError):
    """Raised for any rejected upload (handled by centralized error handlers)."""

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(message, code=code, details=details)


@dataclass(frozen=True)
class UploadValidationResult:
    filename: str
    safe_filename: str
    extension: str
    size_bytes: int
    content_type: str | None


def _normalize_mime(content_type: str | None) -> str | None:
    if not content_type:
        return None
    # Strip parameters: "text/plain; charset=utf-8" -> "text/plain"
    return content_type.split(";", 1)[0].strip().lower() or None


def sniff_mime(content: bytes, extension: str) -> str | None:
    """Best-effort content sniffing (no external magic library)."""
    if not content:
        return None
    head = content.lstrip()[:8]
    if head.startswith(PDF_MAGIC):
        return "application/pdf"
    if extension == ".txt":
        sample = content[:8192]
        if b"\x00" in sample:
            return None
        try:
            sample.decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            return None
    return None


def reject_path_traversal(filename: str) -> None:
    """Reject null bytes and path-segment traversal in the original name."""
    if "\x00" in filename:
        raise UploadValidationError(
            "PATH_TRAVERSAL",
            "Filename contains illegal characters",
        )
    normalized = filename.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p not in ("", ".")]
    if ".." in parts:
        raise UploadValidationError(
            "PATH_TRAVERSAL",
            "Filename must not contain path traversal sequences",
        )
    # Absolute / drive-like paths
    if normalized.startswith("/") or (
        len(normalized) >= 2 and normalized[1] == ":"
    ):
        raise UploadValidationError(
            "PATH_TRAVERSAL",
            "Filename must not be an absolute path",
        )


def safe_storage_filename(original: str) -> str:
    """
    Produce a safe basename for disk storage.
    Strips directories and non-safe characters (path-traversal safe).
    """
    reject_path_traversal(original)
    name = Path(original.replace("\\", "/")).name
    name = name.replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9._-]", "", name)
    if not name or name.startswith(".") or name in {".", ".."}:
        name = f"document_{uuid.uuid4().hex[:8]}"
    return name[:200]


def ensure_path_within(base_dir: str, target_path: str) -> str:
    """Ensure ``target_path`` resolves inside ``base_dir``."""
    base_real = os.path.realpath(base_dir)
    target_real = os.path.realpath(target_path)
    if target_real != base_real and not target_real.startswith(
        base_real + os.sep
    ):
        raise UploadValidationError(
            "PATH_TRAVERSAL",
            "Resolved file path escapes the upload directory",
        )
    return target_real


def validate_extension(filename: str) -> str:
    settings = get_settings()
    extension = Path(filename.replace("\\", "/")).suffix.lower()
    allowed = settings.ALLOWED_EXTENSIONS
    if extension not in allowed:
        allowed_list = ", ".join(sorted(allowed)) or ".pdf, .txt"
        raise UploadValidationError(
            "UNSUPPORTED_EXTENSION",
            f"File type {extension or '(none)'} is not supported. "
            f"Allowed: {allowed_list}",
        )
    return extension


def validate_mime_type(
    extension: str,
    content: bytes,
    content_type: str | None,
) -> str | None:
    declared = _normalize_mime(content_type)
    allowed_declared = ALLOWED_MIME_BY_EXTENSION.get(extension, frozenset())
    if declared and declared not in allowed_declared:
        raise UploadValidationError(
            "UNSUPPORTED_MIME",
            f"MIME type '{declared}' is not allowed for {extension} files",
        )

    sniffed = sniff_mime(content, extension)
    expected = SNIFFED_MIME_BY_EXTENSION.get(extension, frozenset())
    if sniffed is None or sniffed not in expected:
        raise UploadValidationError(
            "MIME_MISMATCH",
            f"File content does not match the {extension} type",
        )
    return declared or sniffed


def validate_size(content: bytes) -> None:
    settings = get_settings()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        max_mb = max(1, settings.MAX_UPLOAD_BYTES // (1024 * 1024))
        raise UploadValidationError(
            "FILE_TOO_LARGE",
            f"File too large. Maximum size is {max_mb} MB",
        )


def validate_not_empty_bytes(content: bytes) -> None:
    if not content:
        raise UploadValidationError("EMPTY_FILE", "Uploaded file is empty")


def validate_txt_content(content: bytes) -> None:
    if not content.strip():
        raise UploadValidationError(
            "EMPTY_DOCUMENT",
            "Text document has no content",
        )
    sample = content[:8192]
    if b"\x00" in sample:
        raise UploadValidationError(
            "INVALID_TEXT",
            "File content is not valid text",
        )
    try:
        sample.decode("utf-8")
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UploadValidationError(
            "INVALID_TEXT",
            "Text file must be UTF-8 encoded",
        ) from exc


def validate_pdf_content(content: bytes) -> None:
    """Validate PDF magic, encryption, corruption, and emptiness."""
    if not content.lstrip().startswith(PDF_MAGIC):
        raise UploadValidationError(
            "INVALID_PDF",
            "File content is not a valid PDF",
        )

    try:
        import fitz
    except ImportError as exc:
        raise UploadValidationError(
            "CORRUPTED_PDF",
            "PDF validation unavailable on this server",
        ) from exc

    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise UploadValidationError(
            "CORRUPTED_PDF",
            "PDF file is corrupted or unreadable",
        ) from exc

    try:
        if doc.needs_pass:
            try:
                unlocked = bool(doc.authenticate(""))
            except Exception:
                unlocked = False
            if not unlocked:
                raise UploadValidationError(
                    "ENCRYPTED_PDF",
                    "Encrypted PDFs are not supported. "
                    "Upload an unencrypted PDF",
                )

        if doc.page_count <= 0:
            raise UploadValidationError(
                "EMPTY_DOCUMENT",
                "PDF has no pages",
            )

        # Force-parse first page — catches many truncated/corrupt files
        try:
            page = doc.load_page(0)
            _ = page.get_text("text")
        except Exception as exc:
            raise UploadValidationError(
                "CORRUPTED_PDF",
                "PDF file is corrupted or unreadable",
            ) from exc

        # Reject PDFs that open but contain no extractable content
        has_content = False
        for i in range(min(doc.page_count, 5)):
            page = doc.load_page(i)
            if (page.get_text("text") or "").strip():
                has_content = True
                break
            if page.get_images():
                has_content = True
                break
        if not has_content:
            raise UploadValidationError(
                "EMPTY_DOCUMENT",
                "PDF document has no extractable content",
            )
    finally:
        doc.close()


def validate_upload(
    *,
    filename: str | None,
    content: bytes,
    content_type: str | None = None,
) -> UploadValidationResult:
    """
    Run the full upload validation pipeline.

    Raises ``UploadValidationError`` on any failure.
    """
    if not filename or not str(filename).strip():
        raise UploadValidationError(
            "FILENAME_REQUIRED",
            "Filename is required",
        )

    filename = str(filename).strip()
    reject_path_traversal(filename)
    extension = validate_extension(filename)
    validate_not_empty_bytes(content)
    validate_size(content)
    resolved_mime = validate_mime_type(extension, content, content_type)

    if extension == ".pdf":
        validate_pdf_content(content)
    elif extension == ".txt":
        validate_txt_content(content)
    else:
        raise UploadValidationError(
            "UNSUPPORTED_EXTENSION",
            f"File type {extension} is not supported",
        )

    return UploadValidationResult(
        filename=filename,
        safe_filename=safe_storage_filename(filename),
        extension=extension,
        size_bytes=len(content),
        content_type=resolved_mime,
    )
