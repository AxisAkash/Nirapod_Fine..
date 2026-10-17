"""Receipt file storage on local disk. File type is decided from the bytes, never from the client's claim."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.core.hashing import sha256_bytes

SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
    "application/pdf": (b"%PDF-", ".pdf"),
}


class UploadError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class StoredFile:
    relative_path: str
    file_type: str
    sha256: str
    size: int


def sniff_type(content: bytes) -> str | None:
    for mime, (magic, _) in SIGNATURES.items():
        if content.startswith(magic):
            return mime
    return None


def save_upload(user_id: uuid.UUID, content: bytes) -> StoredFile:
    settings = get_settings()
    if not content:
        raise UploadError("The file is empty.")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise UploadError(f"The file is larger than {settings.max_upload_mb} MB.", 413)
    mime = sniff_type(content)
    if mime is None:
        raise UploadError("Unsupported file type. Upload a JPG, PNG or PDF.", 415)
    relative = Path(str(user_id)) / f"{uuid.uuid4().hex}{SIGNATURES[mime][1]}"
    target = settings.storage_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    tmp.write_bytes(content)
    tmp.replace(target)
    return StoredFile(relative.as_posix(), mime, sha256_bytes(content), len(content))


def resolve_path(relative: str) -> Path:
    """Absolute path of a stored file; refuses anything that escapes the storage directory."""
    root = get_settings().storage_dir.resolve()
    path = (root / relative).resolve()
    if root not in path.parents:
        raise UploadError("Invalid file path.", 400)
    return path
