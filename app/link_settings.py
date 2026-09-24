import json
import os
import re

_LINKS_FILENAME = "links.json"

DEFAULT_LINKS = [
    {"label": "Example Link", "url": "https://example.com", "color": "good", "group": "Community"},
]

COLOR_CHOICES = {"good", "accent", "purple", "warn", "bad"}

_URL_RE = re.compile(r"^https?://\S+$")
_ICON_RE = re.compile(r"^[A-Za-z0-9._-]{1,200}$")


def _path() -> str:
    override_dir = os.environ.get("CONTENT_OVERRIDE_DIR", "/data/content")
    return os.path.join(override_dir, _LINKS_FILENAME)


def icons_dir() -> str:
    override_dir = os.environ.get("CONTENT_OVERRIDE_DIR", "/data/content")
    return os.path.join(override_dir, "icons")


def _valid_entry(e) -> bool:
    if not isinstance(e, dict):
        return False
    if not isinstance(e.get("label"), str) or not (1 <= len(e["label"]) <= 60):
        return False
    if not isinstance(e.get("url"), str) or not _URL_RE.match(e["url"]):
        return False
    if e.get("color") not in COLOR_CHOICES:
        return False
    if not isinstance(e.get("group"), str) or not (1 <= len(e["group"]) <= 40):
        return False
    icon = e.get("icon", "")
    if icon and not (isinstance(icon, str) and _ICON_RE.match(icon)):
        return False
    return True


def _valid(data) -> bool:
    return isinstance(data, list) and all(_valid_entry(e) for e in data)


def get_links() -> list[dict]:
    try:
        with open(_path(), "r", errors="replace") as f:
            saved = json.load(f)
    except (OSError, ValueError):
        return [dict(e) for e in DEFAULT_LINKS]
    if not _valid(saved):
        return [dict(e) for e in DEFAULT_LINKS]
    return saved


def grouped(items: list[dict]) -> list[dict]:
    """Cluster a flat list of link entries by their `group` field, preserving
    first-seen group order (not alphabetical -- admin-controlled ordering)."""
    order = []
    by_group: dict[str, list[dict]] = {}
    for e in items:
        g = e["group"]
        if g not in by_group:
            by_group[g] = []
            order.append(g)
        by_group[g].append(e)
    return [{"group": g, "links": by_group[g]} for g in order]


def save_links(items: list[dict]) -> list[dict]:
    if not isinstance(items, list):
        raise ValueError("links must be a list")

    cleaned = []
    for e in items:
        label = (e.get("label") or "").strip()
        if not label or len(label) > 60:
            raise ValueError(f"link label must be 1-60 characters (got: {label!r})")
        url = (e.get("url") or "").strip()
        if not _URL_RE.match(url):
            raise ValueError(f"invalid url: {url!r} (must start with http:// or https://)")
        color = e.get("color")
        if color not in COLOR_CHOICES:
            raise ValueError(f"invalid color: {color!r} (choices: {sorted(COLOR_CHOICES)})")
        group = (e.get("group") or "").strip()
        if not group or len(group) > 40:
            raise ValueError(f"group label must be 1-40 characters (got: {group!r})")
        icon = (e.get("icon") or "").strip()
        if icon and not _ICON_RE.match(icon):
            raise ValueError(f"invalid icon filename: {icon!r} (letters/numbers/./-/_ only, no slashes)")
        cleaned.append({"label": label, "url": url, "color": color, "group": group, "icon": icon})

    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(cleaned, f)
    return cleaned
