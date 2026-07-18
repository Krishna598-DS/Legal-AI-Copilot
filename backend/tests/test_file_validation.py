"""Unit tests for production upload validation (all failure modes)."""

from __future__ import annotations

import os
import tempfile

import pytest

# Isolate settings before importing app modules that cache Settings
_tmp = tempfile.mkdtemp()
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-at-least-32-chars")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ["MAX_UPLOAD_BYTES"] = str(1024 * 1024)  # 1 MB for size tests
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-long-enough-for-health")
os.environ.setdefault("LOG_TO_CONSOLE", "false")
os.environ.setdefault("LOG_TO_FILE", "false")

from src.config import clear_settings_cache

clear_settings_cache()

from src.validation.file_upload import (
    UploadValidationError,
    ensure_path_within,
    safe_storage_filename,
    validate_upload,
)


def _pdf_bytes(text: str = "Contract clause one.") -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def _encrypted_pdf_bytes() -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Secret clause")
    # PyMuPDF encrypt on save to buffer via write with encryption
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    try:
        doc.save(
            tmp.name,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw="secret",
            owner_pw="owner",
        )
        doc.close()
        with open(tmp.name, "rb") as fh:
            return fh.read()
    finally:
        os.unlink(tmp.name)


def _assert_code(exc_info, code: str):
    err = exc_info.value
    assert isinstance(err, UploadValidationError)
    assert err.code == code
    assert err.status_code == 400
    body = err.to_dict()
    assert body["error"]["code"] == code
    assert body["error"]["message"]


def test_valid_txt():
    result = validate_upload(
        filename="notes.txt",
        content=b"Hello legal world\n",
        content_type="text/plain",
    )
    assert result.extension == ".txt"
    assert result.safe_filename == "notes.txt"
    assert result.size_bytes > 0


def test_valid_pdf():
    content = _pdf_bytes()
    result = validate_upload(
        filename="contract.pdf",
        content=content,
        content_type="application/pdf",
    )
    assert result.extension == ".pdf"
    assert result.safe_filename == "contract.pdf"


def test_filename_required():
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(filename=None, content=b"x")
    _assert_code(ei, "FILENAME_REQUIRED")


def test_empty_file():
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(filename="a.txt", content=b"")
    _assert_code(ei, "EMPTY_FILE")


def test_empty_text_document():
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="blank.txt",
            content=b"   \n\t  ",
            content_type="text/plain",
        )
    _assert_code(ei, "EMPTY_DOCUMENT")


def test_unsupported_extension():
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="malware.exe",
            content=b"MZ\x90\x00fake",
            content_type="application/octet-stream",
        )
    _assert_code(ei, "UNSUPPORTED_EXTENSION")


def test_unsupported_mime_for_pdf():
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="doc.pdf",
            content=_pdf_bytes(),
            content_type="image/png",
        )
    _assert_code(ei, "UNSUPPORTED_MIME")


def test_mime_mismatch_pdf_extension_but_text_body():
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="fake.pdf",
            content=b"this is not a pdf",
            content_type="application/pdf",
        )
    _assert_code(ei, "MIME_MISMATCH")


def test_file_too_large():
    big = b"a" * (1024 * 1024 + 1)
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="big.txt",
            content=big,
            content_type="text/plain",
        )
    _assert_code(ei, "FILE_TOO_LARGE")


def test_invalid_text_null_bytes():
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="bin.txt",
            content=b"hello\x00world",
            content_type="text/plain",
        )
    # Sniff fails first → MIME_MISMATCH (null bytes)
    assert ei.value.code in {"MIME_MISMATCH", "INVALID_TEXT"}


def test_invalid_text_non_utf8():
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="latin.txt",
            content=b"\xff\xfe not utf8 text content here",
            content_type="text/plain",
        )
    assert ei.value.code in {"MIME_MISMATCH", "INVALID_TEXT"}


def test_corrupted_pdf():
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="broken.pdf",
            content=b"%PDF-1.4\n% corrupted junk \x00\x01\x02",
            content_type="application/pdf",
        )
    _assert_code(ei, "CORRUPTED_PDF")


def test_encrypted_pdf():
    content = _encrypted_pdf_bytes()
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="locked.pdf",
            content=content,
            content_type="application/pdf",
        )
    _assert_code(ei, "ENCRYPTED_PDF")


def test_empty_pdf_no_pages():
    import fitz

    doc = fitz.open()
    # Newer PyMuPDF cannot serialize a 0-page document via tobytes().
    try:
        data = doc.tobytes()
    except ValueError:
        data = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    finally:
        doc.close()
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="empty.pdf",
            content=data,
            content_type="application/pdf",
        )
    assert ei.value.code in {"EMPTY_DOCUMENT", "CORRUPTED_PDF"}


def test_empty_pdf_blank_page():
    import fitz

    doc = fitz.open()
    doc.new_page()  # blank — no text/images
    data = doc.tobytes()
    doc.close()
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="blank.pdf",
            content=data,
            content_type="application/pdf",
        )
    _assert_code(ei, "EMPTY_DOCUMENT")


def test_path_traversal_rejected():
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="../../etc/passwd.txt",
            content=b"secret\n",
            content_type="text/plain",
        )
    _assert_code(ei, "PATH_TRAVERSAL")


def test_path_traversal_absolute():
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="/etc/hosts.txt",
            content=b"secret\n",
            content_type="text/plain",
        )
    _assert_code(ei, "PATH_TRAVERSAL")


def test_null_byte_in_filename():
    with pytest.raises(UploadValidationError) as ei:
        validate_upload(
            filename="evil\x00.pdf",
            content=_pdf_bytes(),
            content_type="application/pdf",
        )
    _assert_code(ei, "PATH_TRAVERSAL")


def test_safe_storage_filename_strips_directories():
    # After reject_path_traversal, basename-only names are sanitized
    name = safe_storage_filename("contract (final).pdf")
    assert name == "contract_final.pdf"
    assert "/" not in name
    assert "\\" not in name


def test_ensure_path_within_allows_child(tmp_path):
    base = tmp_path / "uploads"
    base.mkdir()
    target = base / "user1" / "doc.pdf"
    target.parent.mkdir()
    resolved = ensure_path_within(str(base), str(target))
    assert resolved.endswith("doc.pdf")


def test_ensure_path_within_blocks_escape(tmp_path):
    base = tmp_path / "uploads"
    base.mkdir()
    outside = tmp_path / "other" / "secret.txt"
    outside.parent.mkdir()
    outside.write_text("x")
    with pytest.raises(UploadValidationError) as ei:
        ensure_path_within(str(base), str(outside))
    _assert_code(ei, "PATH_TRAVERSAL")


def test_txt_allows_octet_stream_mime():
    result = validate_upload(
        filename="notes.txt",
        content=b"plain text body\n",
        content_type="application/octet-stream",
    )
    assert result.extension == ".txt"
