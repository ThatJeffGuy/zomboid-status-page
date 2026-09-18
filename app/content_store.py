import os

import markdown

_CONTENT_DIR = os.path.join(os.path.dirname(__file__), "content")

_MARKDOWN_EXTENSIONS = ["fenced_code", "sane_lists"]

_KEYS = {
    "patchnotes": "patchnotes.md",
    "lore": "lore.md",
    "faq": "faq.md",
}


def _override_dir() -> str:
    return os.environ.get("CONTENT_OVERRIDE_DIR", "/data/content")


def _default_path(key: str) -> str:
    return os.path.join(_CONTENT_DIR, _KEYS[key])


def _override_path(key: str) -> str:
    return os.path.join(_override_dir(), _KEYS[key])


def _read(path: str) -> str:
    try:
        with open(path, "r", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _active_path(key: str) -> str:
    override_path = _override_path(key)
    return override_path if os.path.exists(override_path) else _default_path(key)


def get_raw(key: str) -> dict:
    if key not in _KEYS:
        raise KeyError(key)
    overridden = os.path.exists(_override_path(key))
    path = _override_path(key) if overridden else _default_path(key)
    return {"text": _read(path), "overridden": overridden}


def save_raw(key: str, text: str) -> None:
    if key not in _KEYS:
        raise KeyError(key)
    os.makedirs(_override_dir(), exist_ok=True)
    with open(_override_path(key), "w") as f:
        f.write(text)


def revert(key: str) -> None:
    if key not in _KEYS:
        raise KeyError(key)
    try:
        os.remove(_override_path(key))
    except OSError:
        pass


def _render_markdown(text: str) -> str:
    return markdown.markdown(text, extensions=_MARKDOWN_EXTENSIONS)


def _strip_wrapping_p(html: str) -> str:
    html = html.strip()
    if html.startswith("<p>") and html.endswith("</p>") and "<p>" not in html[3:-4]:
        return html[3:-4]
    return html


def _split_top_level(text: str) -> list[tuple[bool, str]]:
    pieces: list[tuple[bool, str]] = []
    i, n = 0, len(text)
    piece_start = 0
    while i < n:
        if text.startswith(">>", i):
            if i > piece_start:
                pieces.append((False, text[piece_start:i]))
            depth = 1
            j = i + 2
            while j < n and depth > 0:
                if text.startswith(">>", j):
                    depth += 1
                    j += 2
                elif text.startswith("<<", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            pieces.append((True, text[i + 2:j - 2] if depth == 0 else text[i + 2:j]))
            i = piece_start = j
        else:
            i += 1
    if piece_start < n:
        pieces.append((False, text[piece_start:]))
    return pieces


def _render_segments(text: str, nested: bool = False) -> str:
    rendered = []
    for is_collapsible, piece in _split_top_level(text):
        if is_collapsible:
            rendered.append(_render_collapsible(piece, nested))
        elif piece.strip():
            rendered.append(_render_markdown(piece.strip()))
    return "\n".join(part for part in rendered if part)


def _render_collapsible(raw: str, nested: bool = False) -> str:
    content = raw.strip()
    if not content:
        return ""
    header, _, body = content.partition("\n")
    header_html = _strip_wrapping_p(_render_markdown(header.strip()))
    body_html = _render_segments(body.strip(), nested=True) if body.strip() else ""
    css_class = "collapsible collapsible-nested" if nested else "collapsible"
    return (
        f'<details class="{css_class}">'
        f"<summary>{header_html}</summary>"
        f'<div class="collapsible-body">{body_html}</div>'
        "</details>"
    )


def _render(key: str) -> str:
    text = _read(_active_path(key)).strip()
    if not text:
        return ""
    html = _render_segments(text)
    return html.replace('<a href="http', '<a target="_blank" rel="noopener" href="http')


def get_world_content() -> dict:
    return {key: _render(key) for key in _KEYS}
