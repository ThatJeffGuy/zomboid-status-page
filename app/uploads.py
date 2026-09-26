import os
import re

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def save_image(directory: str, original_name: str, data: bytes,
               extensions: set[str] = IMAGE_EXTENSIONS, max_bytes: int = MAX_IMAGE_BYTES) -> str:
    """Store an admin-uploaded image in `directory` and return its filename.
    The name is sanitized to letters/numbers/-/_ plus the extension, and never
    overwrites an existing file (something else may be using it) -- a -2,
    -3... suffix is added instead."""
    stem, ext = os.path.splitext(os.path.basename(original_name or ""))
    ext = ext.lower()
    if ext not in extensions:
        raise ValueError(f"unsupported image type {ext or '(none)'!r} (allowed: {', '.join(sorted(extensions))})")
    if not data:
        raise ValueError("uploaded file is empty")
    if len(data) > max_bytes:
        raise ValueError(f"image too large ({max_bytes // (1024 * 1024)} MB max)")

    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-")[:80] or "image"
    os.makedirs(directory, exist_ok=True)
    name, n = stem + ext, 2
    while os.path.exists(os.path.join(directory, name)):
        name = f"{stem}-{n}{ext}"
        n += 1

    tmp = os.path.join(directory, f".upload-{os.getpid()}-{name}")
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, os.path.join(directory, name))
    return name
