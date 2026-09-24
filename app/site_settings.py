import json
import os

_SETTINGS_FILENAME = "settings.json"

SECTION_MODES = ("collapsed", "expanded", "always")
SECTION_DEFAULTS = {
    "section_join": "collapsed",
    "section_news": "expanded",
    "section_lore": "collapsed",
}

DEFAULTS = {
    "brand_title": "My Zomboid Server",
    "brand_subtitle_text": "Edit this in the admin panel's Site Content editor",
    "brand_subtitle_url": "https://www.projectzomboid.com",
    **SECTION_DEFAULTS,
}

_ALLOWED_KEYS = set(DEFAULTS)


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
                if k in SECTION_DEFAULTS and v not in SECTION_MODES:
                    continue
                settings[k] = v
    return settings


def save_settings(partial: dict) -> dict:
    current = get_settings()
    for k, v in partial.items():
        if k in _ALLOWED_KEYS and isinstance(v, str):
            if k in SECTION_DEFAULTS and v.strip() not in SECTION_MODES:
                continue
            current[k] = v.strip()
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(current, f)
    return current
