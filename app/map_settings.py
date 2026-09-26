import json
import os
import re

# Per-world custom live-map textures. The uploaded image must cover the same
# area as the bundled default (see live_map.py's MAP_IMAGE_* constants); it
# is stretched onto the same 1400x1386 frame the player dots are placed in,
# so any resolution works.

DEFAULT_MAP_URL = "/static/map-overview.webp"
MAP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_MAP_BYTES = 40 * 1024 * 1024

_MAPS_FILENAME = "maps.json"
_FILE_RE = re.compile(r"^[A-Za-z0-9._-]{1,200}$")


def _override_dir() -> str:
    return os.environ.get("CONTENT_OVERRIDE_DIR", "/data/content")


def maps_dir() -> str:
    return os.path.join(_override_dir(), "maps")


def _load() -> dict:
    try:
        with open(os.path.join(_override_dir(), _MAPS_FILENAME), "r", errors="replace") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str) and _FILE_RE.match(v)}


def _store(data: dict) -> None:
    path = os.path.join(_override_dir(), _MAPS_FILENAME)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def get_custom(slug: str) -> str:
    """Filename of the world's custom map, or "" when it uses the default
    (including when the file has gone missing)."""
    name = _load().get(slug, "")
    if name and os.path.isfile(os.path.join(maps_dir(), name)):
        return name
    return ""


def map_url(slug: str) -> str:
    name = get_custom(slug)
    return f"/maps/{name}" if name else DEFAULT_MAP_URL


def _set(slug: str, name: str) -> None:
    data = _load()
    old = data.pop(slug, "")
    if name:
        data[slug] = name
    _store(data)
    # Drop the replaced file unless another world still uses it.
    if old and old != name and old not in data.values():
        try:
            os.remove(os.path.join(maps_dir(), old))
        except OSError:
            pass


def set_custom(slug: str, name: str) -> None:
    _set(slug, name)


def clear_custom(slug: str) -> None:
    _set(slug, "")
