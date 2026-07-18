"""Optional ClamAV malware scan (validation lives in ``src.validation``)."""

from __future__ import annotations

import socket

from src.config import get_settings
from src.logging_config import logger
from src.validation.file_upload import UploadValidationError

settings = get_settings()


def scan_bytes(content: bytes, filename: str) -> None:
    """Scan with ClamAV if configured; otherwise no-op beyond logging."""
    if not settings.ENABLE_UPLOAD_SCAN:
        return
    if not settings.CLAMAV_HOST:
        logger.debug("ClamAV not configured — skipping malware scan for %s", filename)
        return

    try:
        with socket.create_connection(
            (settings.CLAMAV_HOST, settings.CLAMAV_PORT),
            timeout=settings.CLAMAV_TIMEOUT,
        ) as sock:
            sock.sendall(b"zINSTREAM\0")
            chunk_size = 2048
            for i in range(0, len(content), chunk_size):
                chunk = content[i : i + chunk_size]
                sock.sendall(len(chunk).to_bytes(4, "big") + chunk)
            sock.sendall((0).to_bytes(4, "big"))
            response = b""
            while True:
                part = sock.recv(4096)
                if not part:
                    break
                response += part
                if b"\0" in response:
                    break
        text = response.decode("utf-8", errors="ignore")
        if "FOUND" in text:
            logger.warning("ClamAV detected malware in %s: %s", filename, text)
            raise UploadValidationError(
                "MALWARE_DETECTED",
                "Upload rejected: malware detected",
            )
        logger.info("ClamAV clean: %s (%s)", filename, text.strip())
    except UploadValidationError:
        raise
    except Exception as exc:
        logger.warning("ClamAV scan failed (allowing file): %s", exc)
