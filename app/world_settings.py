import json
import os
import re

_WORLDS_FILENAME = "worlds.json"

DEFAULT_WORLDS = [
    {"slug": "main", "label": "My World", "color": "good", "primary": True, "image": ""},
]

COLOR_CHOICES = {"good", "accent", "purple", "warn", "bad"}

_SLUG_RE = re.compile(r"^[a-z0-9-]{1,40}$")
_IMAGE_RE = re.compile(r"^[A-Za-z0-9._-]{1,200}$")


def _path() -> str:
    override_dir = os.environ.get("CONTENT_OVERRIDE_DIR", "/data/content")
    return os.path.join(override_dir, _WORLDS_FILENAME)


def slugify(label: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", label.strip().lower()).strip("-")
    return s[:40] or "world"


def _valid(worlds) -> bool:
    if not isinstance(worlds, list) or not worlds:
        return False
    seen_slugs = set()
    primaries = 0
    for w in worlds:
        if not isinstance(w, dict):
            return False
        if not isinstance(w.get("label"), str) or not (1 <= len(w["label"]) <= 60):
            return False
        if not isinstance(w.get("slug"), str) or not _SLUG_RE.match(w["slug"]):
            return False
        if w["slug"] in seen_slugs:
            return False
        seen_slugs.add(w["slug"])
        if w.get("color") not in COLOR_CHOICES:
            return False
        image = w.get("image", "")
        if image and not (isinstance(image, str) and _IMAGE_RE.match(image)):
            return False
        if w.get("primary"):
            primaries += 1
    return primaries == 1


def get_worlds() -> list[dict]:
    try:
        with open(_path(), "r", errors="replace") as f:
            saved = json.load(f)
    except (OSError, ValueError):
        return [dict(w) for w in DEFAULT_WORLDS]
    if not _valid(saved):
        return [dict(w) for w in DEFAULT_WORLDS]
    return saved


def primary_slug(worlds: list[dict] | None = None) -> str:
    worlds = worlds if worlds is not None else get_worlds()
    for w in worlds:
        if w.get("primary"):
            return w["slug"]
    return worlds[0]["slug"]


def save_worlds(worlds: list[dict]) -> list[dict]:
    current = get_worlds()
    current_primary = primary_slug(current)

    cleaned = []
    seen_slugs = set()
    for w in worlds:
        label = (w.get("label") or "").strip()
        if not label or len(label) > 60:
            raise ValueError(f"world label must be 1-60 characters (got: {label!r})")
        slug = (w.get("slug") or "").strip().lower()
        if not _SLUG_RE.match(slug):
            raise ValueError(f"invalid slug: {slug!r} (lowercase letters/numbers/hyphens only, max 40 chars)")
        if slug in seen_slugs:
            raise ValueError(f"duplicate slug: {slug!r}")
        seen_slugs.add(slug)
        color = w.get("color")
        if color not in COLOR_CHOICES:
            raise ValueError(f"invalid color: {color!r} (choices: {sorted(COLOR_CHOICES)})")
        image = (w.get("image") or "").strip()
        if image and not _IMAGE_RE.match(image):
            raise ValueError(f"invalid image filename: {image!r} (letters/numbers/./-/_ only, no slashes)")
        cleaned.append({"slug": slug, "label": label, "color": color, "primary": bool(w.get("primary")), "image": image})

    if not cleaned:
        raise ValueError("at least one world is required")

    primaries = [w for w in cleaned if w["primary"]]
    if len(primaries) != 1:
        raise ValueError("exactly one world must be primary")
    if primaries[0]["slug"] != current_primary:
        raise ValueError(
            f"the primary world can't be changed here (currently {current_primary!r}) "
            "-- it's the one this app has real RCON/status data for"
        )

    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(cleaned, f)
    return cleaned
