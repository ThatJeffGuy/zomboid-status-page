import json
import os
import re

_SETTINGS_FILENAME = "settings.json"

# How each collapsible section on the world pages starts out: "collapsed",
# "expanded" (open, but can be closed), or "always" (open, no toggle).
SECTION_MODES = ("collapsed", "expanded", "always")
SECTION_DEFAULTS = {
    "section_join": "collapsed",
    "section_news": "expanded",
    "section_lore": "collapsed",
}

DEFAULTS = {
    "brand_title": "My Zomboid Server",
    # Optional middle header line; blank hides it.
    "brand_tagline": "",
    "brand_subtitle_text": "Edit this in the admin panel's Site Content editor",
    "brand_subtitle_url": "https://www.projectzomboid.com",
    # Optional header logo (filename in the icons dir); replaces the title text.
    "brand_logo": "",
    # Front page (world picker) heading and the line under it.
    "picker_heading": "Pick a world",
    "picker_text": "Choose a server to see its live map, player status, and patch notes.",
    **SECTION_DEFAULTS,
}

_ALLOWED_KEYS = set(DEFAULTS)
_LOGO_RE = re.compile(r"^[A-Za-z0-9._-]{1,200}$")


def _acceptable(k: str, v: str) -> bool:
    if k in SECTION_DEFAULTS and v not in SECTION_MODES:
        return False
    if k == "brand_logo" and v and not _LOGO_RE.match(v):
        return False
    return True


def _path() -> str:
    override_dir = os.environ.get("CONTENT_OVERRIDE_DIR", "/data/content")
    return os.path.join(override_dir, _SETTINGS_FILENAME)


def get_settings() -> dict:
    settings = dict(DEFAULTS)
    try:
        with open(_path(), "r", errors="replace") as f:
            saved = json.load(f)
    except (OSError, ValueError):
        return settings
    if isinstance(saved, dict):
        for k, v in saved.items():
            if k in _ALLOWED_KEYS and isinstance(v, str) and v.strip():
                if not _acceptable(k, v):
                    continue
                settings[k] = v
    return settings


def save_settings(partial: dict) -> dict:
    current = get_settings()
    for k, v in partial.items():
        if k in _ALLOWED_KEYS and isinstance(v, str):
            if not _acceptable(k, v.strip()):
                continue
            current[k] = v.strip()
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(current, f)
    return current
